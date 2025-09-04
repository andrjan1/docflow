from pathlib import Path
from typing import Dict, Any
from ..config import load_config
from ..core.context import ExecutionContext
from ..ai.factory import make_ai_client
from ..core.workflow import execute_workflow
from ..adapters.docx_adapter import DocxAdapter
from ..adapters.pptx_adapter import PptxAdapter
from ..logging_lib import setup_logger, json_log_entry, reconfigure_log_level
import time


logger = setup_logger(__name__)


ADAPTERS = {'docx': DocxAdapter, 'pptx': PptxAdapter}


def run_config(path: str, verbose: bool = False) -> Dict[str, Any]:
    cfg = load_config(path)
    
    # Configure logging level - use DEBUG if verbose
    log_level = 'DEBUG' if verbose else (cfg.project.log_level or 'INFO')
    reconfigure_log_level(log_level)
    logger.info({'event': 'log_level_configured', 'level': log_level, 'verbose': verbose})
    ai = make_ai_client(cfg.ai.model and {'provider': cfg.ai.provider, 'model': cfg.ai.model, 'api_key_envvar': cfg.ai.api_key_envvar} or {'provider': cfg.ai.provider})
    ctx = ExecutionContext()
    ctx.ai_client = ai
    # populate context paths from configuration (normalize relative to base_dir)
    # assets_dir -> project.output_dir / assets
    outdir = Path(cfg.project.output_dir)
    if not outdir.is_absolute():
        outdir = (Path(cfg.project.base_dir) / outdir).resolve()
    assets_dir = outdir / 'assets'
    assets_dir.mkdir(parents=True, exist_ok=True)
    ctx.assets_dir = assets_dir
    # kb_cache_dir -> project.temp_dir / kb
    tmpdir = Path(cfg.project.temp_dir)
    if not tmpdir.is_absolute():
        tmpdir = (Path(cfg.project.base_dir) / tmpdir).resolve()
    kb_cache = tmpdir / 'kb'
    kb_cache.mkdir(parents=True, exist_ok=True)
    ctx.kb_cache_dir = kb_cache

    # execute workflow
    # Prefer Pydantic V2 `model_dump()` when available; fall back to `.dict()` for older versions
    def _dump(a):
        if hasattr(a, 'model_dump'):
            return a.model_dump()
        if hasattr(a, 'dict'):
            return a.dict()
        return a

    actions = [_dump(a) for a in cfg.workflow.actions]
    start_all = time.time()
    # capture per-action results so we can map them into template placeholders
    logger.info({'event': 'workflow_start', 'actions': len(actions), 'verbose': verbose})
    
    # Pass verbose flag to execution context for more detailed logging
    ctx.verbose = verbose
    
    action_results = execute_workflow(actions, ctx)
    logger.info({'event': 'workflow_end', 'actions': len(action_results), 'verbose': verbose})
    total_time = time.time() - start_all

    # render templates
    outdir = Path(cfg.project.output_dir)
    if not outdir.is_absolute():
        outdir = (Path(cfg.project.base_dir) / outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    # Before rendering templates, materialize placeholder_map entries pointing
    # to action ids (e.g. placeholder 'immagine_prodotto' => action 'genera_immagine').
    # We inject these into ctx.global_vars so adapters can resolve {{var}} or {{image:var}}.
    for t in cfg.workflow.templates:
        placeholder_map = getattr(t, 'placeholder_map', {}) if hasattr(t, 'placeholder_map') else t.get('placeholder_map', {})
        for ph_name, action_id in (placeholder_map or {}).items():
            if ph_name in ctx.global_vars:
                continue  # already provided (e.g. via VARS_JSON)
            ar = action_results.get(action_id) if action_results else None
            if ar is None:
                continue
            # For images we store the file path (str); for text just the text; for bytes keep bytes
            ctx.global_vars[ph_name] = ar.data or ''

    results = {}
    for t in cfg.workflow.templates:
        adapter_cls = ADAPTERS.get(t.adapter if hasattr(t, 'adapter') else t['adapter'])
        template_path = Path(t.path) if hasattr(t, 'path') else Path(t['path'])
        if not template_path.is_absolute():
            template_path = (Path(cfg.project.base_dir) / template_path).resolve()
        out_name = template_path.name.replace('_template', '')
        out_path = outdir / out_name
        if adapter_cls:
            adapter = adapter_cls(str(template_path))
            adapter.apply(mapping=ctx.global_vars, global_vars=ctx.global_vars)
            adapter.save(str(out_path))
            results[str(out_path)] = True

    # telemetry summary
    summary = {'total_time_s': total_time, 'files': list(results.keys()), 'actions': getattr(ctx, 'telemetry', {})}
    if verbose:
        json_log_entry(logger, summary)
    return results
