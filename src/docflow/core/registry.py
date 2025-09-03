from typing import Dict, Any


def make_action(cfg: Dict[str, Any], ctx=None):
    # lazy import to avoid cycles
    t = cfg.get('type')
    if t == 'generative':
        from .actions.generative import GenerativeAction

        return GenerativeAction(cfg)
    if t == 'code':
        from .actions.code import CodeAction

        return CodeAction(cfg)
    raise ValueError('unknown action type')
