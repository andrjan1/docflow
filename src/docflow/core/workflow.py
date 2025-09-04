from typing import List, Dict, Any
from .context import ExecutionContext
from .results import ActionResult
from .registry import make_action
from jinja2 import Template
from ..logging_lib import setup_logger
import time

logger = setup_logger(__name__)


def _as_dict(a: Any) -> Dict[str, Any]:
    # support pydantic models or plain dicts
    try:
        return dict(a)
    except Exception:
        try:
            return a.__dict__
        except Exception:
            return a


def toposort_actions(actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # simplistic Kahn's algorithm; actions are dicts with 'id' and optional 'deps'
    id_map = {a['id']: a for a in actions}
    deps = {a['id']: set(a.get('deps', [])) for a in actions}
    result = []
    ready = [i for i, d in deps.items() if not d]
    while ready:
        n = ready.pop(0)
        result.append(id_map[n])
        for m in list(deps.keys()):
            if n in deps[m]:
                deps[m].remove(n)
                if not deps[m]:
                    ready.append(m)
    if any(deps[k] for k in deps):
        raise ValueError('cycle detected in actions deps')
    return result


def apply_exports(result: ActionResult, exports: List[Dict[str, Any]], ctx: ExecutionContext):
    for ex in exports:
        name = ex['name']
        source = ex.get('source', 'result_text')
        jinja_tpl = ex['jinja']
        if source == 'result_text':
            text = result.data if isinstance(result.data, str) else ''
            tpl = Template(jinja_tpl)
            out = tpl.render(text=text, meta=result.meta, vars=ctx.global_vars)
            ctx.global_vars[name] = out
        elif source == 'result_meta':
            tpl = Template(jinja_tpl)
            out = tpl.render(text='', meta=result.meta, vars=ctx.global_vars)
            ctx.global_vars[name] = out


def execute_workflow(actions: List[Dict[str, Any]], ctx: ExecutionContext) -> Dict[str, ActionResult]:
    order = toposort_actions(actions)
    mapping: Dict[str, ActionResult] = {}
    # telemetry per action
    if getattr(ctx, 'telemetry', None) is None:
        ctx.telemetry = {}
    for a in order:
        ad = _as_dict(a)
        act = make_action(ad, ctx)
        
        # Start timing
        action_start_time = time.time()
        
        logger.info({'event': 'action_start', 'id': ad.get('id'), 'type': ad.get('type')})
        
        # Log current context variables if verbose
        if getattr(ctx, 'verbose', False):
            ctx_vars = {k: str(v)[:100] + '...' if len(str(v)) > 100 else str(v) 
                       for k, v in ctx.global_vars.items()}
            logger.info({'event': 'action_context_vars', 'id': ad.get('id'), 'vars': ctx_vars})
        
        # call the standardized execute(ctx) method on actions
        res = act.execute(ctx)
        
        # Calculate timing
        action_duration = time.time() - action_start_time
        
        # Log action result if verbose
        if getattr(ctx, 'verbose', False) and res:
            if isinstance(res, (list, tuple)):
                # Multiple outputs
                result_preview = f"Multiple outputs: {len(res)} items"
            else:
                # Single output
                result_preview = str(res.data)[:200] + '...' if res.data and len(str(res.data)) > 200 else str(res.data)
            logger.info({'event': 'action_result', 'id': ad.get('id'), 'result_type': type(res).__name__, 'preview': result_preview})
        
        logger.info({'event': 'action_end', 'id': ad.get('id'), 'duration_s': round(action_duration, 3)})
        
        # Handle multiple outputs or single output
        ar = None
        if isinstance(res, (list, tuple)) and len(res) > 1:
            # Multiple outputs - handle each according to returns specification
            returns_spec = ad.get('returns', 'text')
            if isinstance(returns_spec, list):
                # Process multiple outputs
                results = []
                vars_combined = {}
                
                for i, (output, return_type) in enumerate(zip(res, returns_spec)):
                    if return_type == 'vars' and isinstance(output, dict):
                        # Variables go into combined vars
                        vars_combined.update(output)
                        results.append(ActionResult(kind='vars', data=output, vars=output))
                    elif return_type in ['text', 'image', 'bytes']:
                        results.append(ActionResult(kind=return_type, data=output))
                
                # Create combined result with primary data from first non-vars result
                primary_result = next((r for r in results if r.kind != 'vars'), results[0] if results else None)
                if primary_result:
                    ar = ActionResult(
                        kind=primary_result.kind,
                        data=primary_result.data,
                        vars=vars_combined,
                        meta={'multiple_outputs': True, 'output_count': len(results)}
                    )
                else:
                    ar = ActionResult(kind='vars', data={}, vars=vars_combined)
            else:
                # Single return type expected but got multiple - use first
                ar = ActionResult(kind=returns_spec, data=res[0], vars={})
        
        # Single output (existing logic)
        elif isinstance(res, dict):
            # prefer explicit keys
            if 'result_text' in res:
                kind = 'text'
                data = res.get('result_text') or ''
            elif 'image' in res:
                kind = 'image'
                data = res.get('image')
            elif 'result' in res:
                # ambiguous: if result is str -> text else bytes
                r = res.get('result')
                if isinstance(r, str):
                    kind = 'text'
                    data = r
                else:
                    kind = 'bytes'
                    data = r
            else:
                declared = ad.get('returns') if isinstance(ad, dict) else None
                raise ValueError(f"Action '{ad.get('id')}' returned unexpected structure and no explicit keys; declared returns={declared}")
            ar = ActionResult(kind=kind, data=data, meta=res.get('meta', {}), vars=res.get('vars', {}))
        elif isinstance(res, ActionResult):
            ar = res
        else:
            ar = ActionResult(kind='text', data=str(res), meta={}, vars={})
            
        # update global vars
        ctx.global_vars.update(ar.vars)
        # apply exports
        for ex in a.get('exports', []):
            apply_exports(ar, [ex], ctx)
        mapping[a['id']] = ar
        # collect telemetry if present in meta
        try:
            meta = ar.meta or {}
            ctx.telemetry[a['id']] = {
                'latency': meta.get('latency') or meta.get('latency_ms') or meta.get('latency_s') or meta.get('latency', 0),
                'out_bytes': len(str(ar.data)) if ar.data else 0,
                'vars_emitted': len(ar.vars or {}),
            }
        except Exception:
            ctx.telemetry[a['id']] = {}
    return mapping
