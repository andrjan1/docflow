from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from pathlib import Path
import yaml


class ProjectConfig(BaseModel):
    base_dir: Path = Path('.')
    output_dir: Path = Path('build/output')
    temp_dir: Path = Path('build/tmp')
    log_level: str = 'INFO'


class AIConfig(BaseModel):
    provider: Literal['mock', 'openai', 'gemini', 'azure-openai'] = 'mock'
    api_base: Optional[str] = None
    model: Optional[str] = None
    img_model: Optional[str] = None
    api_key_envvar: Optional[str] = None
    timeout_s: int = 30
    retries: int = 1


class KBConfig(BaseModel):
    """Unified Knowledge Base configuration supporting text extraction and file upload"""
    enabled: bool = False
    paths: List[Path] = Field(default_factory=list)
    include_glob: str = '**/*'
    
    # Processing strategy - UNIFIED
    strategy: Literal['inline', 'upload', 'hybrid', 'summarize', 'retrieve'] = 'inline'
    max_chars: int = 10000
    
    # Upload options (formerly attachments)
    upload: bool = False
    mime_type: Optional[str] = None
    
    # Text extraction options
    as_text: bool = True
    
    # Advanced chunking
    chunk_size: int = 2000
    chunk_overlap: int = 200


class ExportRule(BaseModel):
    name: str
    source: Literal['result_text', 'result_meta'] = 'result_text'
    jinja: str


class ActionConfig(BaseModel):
    id: str
    type: Literal['generative', 'code']
    returns: Literal['text', 'image', 'bytes'] = 'text'
    deps: List[str] = Field(default_factory=list)
    input_vars: List[str] = Field(default_factory=list)
    prompt: Optional[str] = None
    prompt_file: Optional[Path] = None
    prompt_fn: Optional[str] = None
    kb: Optional[KBConfig] = None
    code: Optional[str] = None
    code_file: Optional[Path] = None
    exports: List[ExportRule] = Field(default_factory=list)
    # attachments field removed - now unified in kb


class TemplateConfig(BaseModel):
    path: Path
    adapter: Literal['docx', 'pptx']
    placeholder_map: Dict[str, str] = Field(default_factory=dict)


class WorkflowConfig(BaseModel):
    actions: List[ActionConfig]
    templates: List[TemplateConfig]


class AppConfig(BaseModel):
    project: ProjectConfig
    ai: AIConfig
    workflow: WorkflowConfig


def _load_yaml(path: Path) -> dict:
    with path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def load_config(path: str) -> AppConfig:
    """Load config YAML, apply env and normalize relative paths to base_dir.

    - Loads .env if present in same dir as config
    - Expands relative paths against base_dir
    """
    cfg_path = Path(path)
    data = _load_yaml(cfg_path)

    # load .env if exists
    env_path = cfg_path.parent / '.env'
    if env_path.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(env_path)
        except Exception:
            pass

    # build AppConfig dict defaults
    project = data.get('project', {})
    # default base_dir relative to config
    base_dir = Path(project.get('base_dir', '.'))
    if not base_dir.is_absolute():
        # if base_dir is '.' default to parent of config file (repo root)
        if str(base_dir) == '.':
            base_dir = cfg_path.parent.resolve()
        else:
            base_dir = (cfg_path.parent / base_dir).resolve()
    project['base_dir'] = base_dir

    # normalize template paths and code_file/prompt_file relative to base_dir
    workflow = data.get('workflow', {})
    templates = workflow.get('templates', [])
    for t in templates:
        if 'path' in t:
            p = Path(t['path'])
            if not p.is_absolute():
                t['path'] = str((base_dir / p).resolve())

    actions = workflow.get('actions', [])
    for a in actions:
        if a.get('prompt_file'):
            pf = Path(a['prompt_file'])
            if not pf.is_absolute():
                a['prompt_file'] = str((base_dir / pf).resolve())
        if a.get('code_file'):
            cf = Path(a['code_file'])
            if not cf.is_absolute():
                a['code_file'] = str((base_dir / cf).resolve())
        # normalize kb paths
        if a.get('kb') and isinstance(a.get('kb'), dict):
            kb_cfg = a['kb']
            paths_norm = []
            for pth in kb_cfg.get('paths', []) or []:
                p_obj = Path(pth)
                if not p_obj.is_absolute():
                    p_obj = (base_dir / p_obj).resolve()
                paths_norm.append(str(p_obj))
            kb_cfg['paths'] = paths_norm

    # assemble final dict
    final = {
        'project': project,
        'ai': data.get('ai', {}),
        'workflow': {'actions': actions, 'templates': templates},
    }

    return AppConfig(**final)
