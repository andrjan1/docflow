from typing import Any, Dict, Optional
from pathlib import Path
import importlib
import importlib.util
from jinja2 import Template


def _load_module_from_path(path: Path, name: str = 'prompt_module'):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def build_prompt_for_action(action: Any, global_vars: Dict[str, Any], kb_text: Optional[str] = None) -> Optional[str]:
    """Resolve a prompt for an action using priority:
    prompt_fn > prompt_file > prompt (inline)

    action may be a pydantic model or dict; we access attributes accordingly.
    """
    def getattr_any(obj, name, default=None):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    # 1) prompt_fn: module:function or path/to/file.py[:func]
    prompt_fn = getattr_any(action, 'prompt_fn')
    if prompt_fn:
        # parse module:path (use rsplit to be Windows-drive safe)
        if isinstance(prompt_fn, str) and ':' in prompt_fn:
            mod_part, func_name = prompt_fn.rsplit(':', 1)
        else:
            mod_part, func_name = prompt_fn, 'build_prompt'

        # try file path first
        p = Path(mod_part)
        try:
            if p.exists():
                mod = _load_module_from_path(p, name='prompt_builder')
            else:
                mod = importlib.import_module(mod_part)
            fn = getattr(mod, func_name)
            return fn(global_vars, kb_text)
        except Exception:
            return None

    # helper to compute context: pass global vars + selected input_vars keys
    input_vars = getattr_any(action, 'input_vars', []) or []
    ctx = dict(global_vars)
    for k in input_vars:
        if k not in ctx:
            ctx[k] = global_vars.get(k)
    # add kb as 'kb' key
    # avoid rendering 'None' in templates when KB not available
    ctx['kb'] = kb_text or ''

    # 2) prompt_file (.j2)
    prompt_file = getattr_any(action, 'prompt_file')
    if prompt_file:
        try:
            path = Path(prompt_file)
            if not path.exists():
                # maybe it's relative to current working dir
                path = Path.cwd() / prompt_file
            text = path.read_text(encoding='utf-8')
            tpl = Template(text)
            return tpl.render(**ctx)
        except Exception:
            return None

    # 3) inline prompt (Jinja2)
    prompt = getattr_any(action, 'prompt')
    if prompt:
        try:
            tpl = Template(str(prompt))
            return tpl.render(**ctx)
        except Exception:
            return None

    return None
