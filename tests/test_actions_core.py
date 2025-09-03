from pathlib import Path
from docflow.core.actions.generative import GenerativeAction
from docflow.core.actions.code import CodeAction
from docflow.core.context import ExecutionContext


def test_generative_text_mode(tmp_path):
    cfg = {'prompt': 'Say hi to {{name}}', 'vars': {}, 'mode': 'text'}
    ga = GenerativeAction(cfg)
    ctx = ExecutionContext(global_vars={'name': 'Tester'}, assets_dir=str(tmp_path))
    out = ga.execute(ctx)
    assert out.kind == 'text'
    assert 'Tester' in out.data or 'Echo' in out.data


def test_generative_image_mode(tmp_path):
    cfg = {'prompt': 'Image prompt', 'mode': 'image', 'export_path_var': 'hero_path'}
    ga = GenerativeAction(cfg)
    ctx = ExecutionContext(assets_dir=str(tmp_path))
    out = ga.execute(ctx)
    assert out.kind == 'image'
    p = Path(out.data)
    assert p.exists()
    assert out.vars.get('hero_path') == str(p)


def test_code_action_emits_vars_and_image(tmp_path):
    # code: create a matplotlib plot, save to a temp file, print its path, and emit VARS_JSON
    out_path = tmp_path / 'out.png'
    code = f'''
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
fpath = r'{out_path}'
fig, ax = plt.subplots()
ax.plot([1,2,3],[1,4,9])
fig.savefig(fpath)
print('VARS_JSON=' + json.dumps({{"plot_ready": True}}))
print(fpath)
'''

    cfg = {'code': code, 'returns': 'image', 'timeout': 5}
    ca = CodeAction(cfg)
    ctx = ExecutionContext()
    out = ca.execute(ctx)
    assert out.kind == 'image'
    p = Path(out.data)
    assert p.exists()
    assert out.vars.get('plot_ready') is True
