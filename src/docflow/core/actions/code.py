from typing import Dict, Any, List
import subprocess
import sys
import json
import tempfile
from pathlib import Path
from ..results import ActionResult
from ..context import ExecutionContext
from ...logging_lib import setup_logger

logger = setup_logger(__name__)


ALLOWED_MODULES = {'math', 'statistics', 'json', 'matplotlib', 'pandas', 'numpy'}


def _make_runner_script(code: str) -> str:
    # wrapper that reads stdin JSON (vars) and executes user code
    # The user code is expected to define a `run(vars)` function that returns a dict.
    # We will call it and then print back any VARS_JSON=... lines and the image path
    header = """
import sys, json, os
vars = json.load(sys.stdin)
# expose some common modules to user code
import math, statistics, json as _json
from matplotlib import pyplot as plt

"""
    footer = """

result = None
# Try different function names for entry point
if 'run' in globals():
    try:
        result = run(vars)
    except Exception as e:
        print('ERROR_IN_USER_CODE:' + str(e), file=sys.stderr)
        sys.exit(1)
elif 'main' in globals():
    try:
        # Create a context-like object
        class Context:
            def __init__(self, vars_data):
                for k, v in vars_data.items():
                    setattr(self, k, v)
        
        ctx = Context(vars)
        result = main(ctx)
    except Exception as e:
        print('ERROR_IN_USER_CODE:' + str(e), file=sys.stderr)
        sys.exit(1)
else:
    # if the user didn't define run or main, try to use a top-level result variable
    result = globals().get('result', None)

# Handle different result types
if isinstance(result, tuple):
    # Multiple outputs case - encode as special JSON structure
    print('MULTIPLE_OUTPUTS=' + json.dumps({
        'is_tuple': True,
        'items': [
            {'type': 'dict', 'data': item} if isinstance(item, dict) 
            else {'type': 'str', 'data': str(item)} if isinstance(item, str)
            else {'type': 'other', 'data': str(item)}
            for item in result
        ]
    }))
elif isinstance(result, dict):
    # emit vars as JSON on a predictable line
    v = result.get('vars', {})
    try:
        print('VARS_JSON=' + json.dumps(v))
    except Exception:
        pass
    # if an image path is present, print it as the last line
    img = None
    for k, val in result.items():
        if k.startswith('image') and isinstance(val, str):
            img = val
            break
    if img:
        print(img)
    elif any(k.startswith('image') and isinstance(v, (bytes, bytearray)) for k, v in result.items()):
        # cannot transfer raw bytes via stdout here; rely on path
        pass
    # also, if there's a textual result
    if 'result_text' in result and result.get('result_text'):
        print(result.get('result_text'))
elif result is not None:
    # Single value result
    print(str(result))
"""
    return header + code + footer


class CodeAction:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg or {}

    def execute(self, ctx: ExecutionContext) -> ActionResult:
        # gather input vars
        vars_in = ctx.global_vars if ctx is not None else {}
        code = self.cfg.get('code')
        if not code and self.cfg.get('code_file'):
            p = Path(self.cfg.get('code_file'))
            code = p.read_text(encoding='utf-8')
        if not code:
            logger.info({'event': 'code_action_no_code', 'id': self.cfg.get('id')})
            return ActionResult(kind='text', data='', meta={'error': 'no_code'}, vars={})

        script = _make_runner_script(code)
        with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(script)
            script_path = f.name
        try:
            logger.info({'event': 'code_action_start', 'id': self.cfg.get('id'), 'timeout': self.cfg.get('timeout', 10)})
            proc = subprocess.run([sys.executable, script_path], input=json.dumps(vars_in), text=True, capture_output=True, timeout=self.cfg.get('timeout', 10))
        except subprocess.TimeoutExpired:
            logger.info({'event': 'code_action_timeout', 'id': self.cfg.get('id')})
            return ActionResult(kind='text', data='', meta={'error': 'timeout', 'timeout': True}, vars={})

        stdout = proc.stdout or ''
        stderr = proc.stderr or ''
        if proc.returncode != 0:
            logger.info({'event': 'code_action_nonzero', 'id': self.cfg.get('id'), 'returncode': proc.returncode})
            return ActionResult(kind='text', data='', meta={'error': 'nonzero_exit', 'returncode': proc.returncode, 'stderr': stderr}, vars={})

        vars_out: Dict[str, Any] = {}
        image_path: str | None = None
        text_lines: List[str] = []
        multiple_outputs_result = None
        
        for line in stdout.splitlines():
            if line.startswith('VARS_JSON='):
                try:
                    j = json.loads(line[len('VARS_JSON='):])
                    if isinstance(j, dict):
                        vars_out.update(j)
                except Exception:
                    pass
            elif line.startswith('MULTIPLE_OUTPUTS='):
                try:
                    multiple_outputs_result = json.loads(line[len('MULTIPLE_OUTPUTS='):])
                except Exception:
                    pass
            else:
                candidate = line.strip()
                if candidate and (candidate.endswith('.png') or candidate.endswith('.jpg') or candidate.endswith('.jpeg')):
                    image_path = candidate
                else:
                    text_lines.append(candidate)

        text = '\n'.join([line for line in text_lines if line])
        logger.info({'event': 'code_action_text_success', 'id': self.cfg.get('id'), 'chars': len(text)})
        
        # Check if we have multiple outputs from the code execution
        returns = self.cfg.get('returns', 'text')
        if multiple_outputs_result and isinstance(returns, list) and len(returns) > 1:
            # Parse the multiple outputs result
            items = multiple_outputs_result.get('items', [])
            outputs = []
            
            for i, return_type in enumerate(returns):
                if i < len(items):
                    item = items[i]
                    if return_type == 'vars' and item['type'] == 'dict':
                        outputs.append(item['data'])
                    elif return_type == 'text' and item['type'] in ['str', 'other']:
                        outputs.append(item['data'])
                    elif return_type == 'image' and item['type'] in ['str', 'other']:
                        outputs.append(item['data'])
                    else:
                        outputs.append(item['data'])
                else:
                    outputs.append(None)
            
            return tuple(outputs)
        elif isinstance(returns, list) and len(returns) > 1:
            # Handle multiple outputs with existing vars_out logic
            outputs = []
            for return_type in returns:
                if return_type == 'vars':
                    outputs.append(vars_out)
                elif return_type == 'image' and image_path:
                    outputs.append(image_path)
                elif return_type == 'text':
                    outputs.append(text)
                else:
                    outputs.append(None)  # Placeholder for unsupported types
            
            return tuple(outputs)
        else:
            # Single output (existing behavior)
            if self.cfg.get('returns') == 'image' and image_path:
                p = Path(image_path)
                if p.exists():
                    logger.info({'event': 'code_action_image_success', 'id': self.cfg.get('id'), 'image_path': str(p)})
                    return ActionResult(kind='image', data=str(p), meta={'returncode': proc.returncode}, vars=vars_out)
            
            return ActionResult(kind='text', data=text, meta={'returncode': proc.returncode}, vars=vars_out)
