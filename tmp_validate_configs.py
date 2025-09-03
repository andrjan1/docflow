from pathlib import Path
import sys
import traceback
sys.path.insert(0, str(Path('.').resolve()))
from src.docflow.config import load_config

paths = ['config/example.config.yaml', 'config/ci_demo.yaml']
for p in paths:
    print('---', p)
    try:
        cfg = load_config(p)
        print(p, 'OK ->', type(cfg))
    except Exception as e:
        print(p, 'FAILED ->', e)
        traceback.print_exc()
