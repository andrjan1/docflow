import os
from pathlib import Path
from docflow.cli import run, init

def test_init_and_run(tmp_path):
    # copy example config to tmp and run init to create templates
    cfg_path = tmp_path / 'example.config.yaml'
    # call init to create templates and config in cwd
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        init()
        cfg_path = Path('config/example.config.yaml')
        assert cfg_path.exists()
        run(str(cfg_path))
        out1 = Path('build/output/demo.docx')
        out2 = Path('build/output/demo.pptx')
        assert out1.exists()
        assert out2.exists()
    finally:
        os.chdir(cwd)
