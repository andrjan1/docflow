from typing import Optional, Dict, Any, List
from pathlib import Path
from .loader import collect_files, read_kb_texts, concat_and_truncate


def strategy_inline(cfg: Dict[str, Any], vars: Dict[str, Any]) -> Optional[str]:
    paths = [Path(p) for p in cfg.get('paths', [])]
    files = collect_files(paths, cfg.get('include_glob', '**/*.md'))
    texts = read_kb_texts(files)
    # Supporta max_chars dinamico basato su variabili
    max_chars = cfg.get('max_chars', 10000)
    if isinstance(max_chars, str) and max_chars.startswith('{{'):
        # Supporto per template Jinja nei parametri (es: '{{max_length}}')
        from jinja2 import Template
        try:
            max_chars = int(Template(max_chars).render(**vars))
        except:
            max_chars = 10000
    txt = concat_and_truncate(texts, max_chars)
    return txt or None


def strategy_summarize(cfg: Dict[str, Any], vars: Dict[str, Any]) -> Optional[str]:
    # mock heuristic summarizer: take first N chars of each doc and join
    paths = [Path(p) for p in cfg.get('paths', [])]
    files = collect_files(paths, cfg.get('include_glob', '**/*.md'))
    texts = read_kb_texts(files)
    snippets = [t[: min(300, len(t))] for t in texts if t]
    summary = '\n\n'.join(snippets)
    return summary or None


def strategy_retrieve_mock(cfg: Dict[str, Any], vars: Dict[str, Any]) -> Optional[str]:
    # naive keyword match: if any input_var present in doc text, return matching snippets
    paths = [Path(p) for p in cfg.get('paths', [])]
    files = collect_files(paths, cfg.get('include_glob', '**/*.md'))
    texts = read_kb_texts(files)
    queries = vars.keys()
    matches: List[str] = []
    for t in texts:
        for q in queries:
            if q and q.lower() in t.lower():
                idx = t.lower().index(q.lower())
                start = max(0, idx - 100)
                matches.append(t[start: start + 400])
                break
    return '\n\n'.join(matches) if matches else None


def prepare_kb_for_action(action_cfg: Dict[str, Any], vars: Dict[str, Any]) -> Optional[str]:
    # action_cfg may be the full action dict, or already the kb dict, or None
    if not action_cfg:
        return None
    # if caller passed the full action dict, extract 'kb'
    if isinstance(action_cfg, dict) and 'kb' in action_cfg:
        kb = action_cfg.get('kb') or {}
    else:
        # assume it's already the kb config (or a mapping-like)
        kb = action_cfg or {}
    if not kb.get('enabled'):
        return None
    strategy = kb.get('strategy', 'inline')
    if strategy == 'inline':
        return strategy_inline(kb, vars)
    if strategy == 'summarize':
        return strategy_summarize(kb, vars)
    if strategy == 'retrieve-mock':
        return strategy_retrieve_mock(kb, vars)
    return None
