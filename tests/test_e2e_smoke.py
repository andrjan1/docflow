from pathlib import Path
from importlib import import_module


def test_docflow_cli_smoke():
    # import the package and call init/run
    cli = import_module('docflow.cli')
    # create example config and templates
    cli.init()
    cfg_path = Path('config/example.config.yaml')
    assert cfg_path.exists()
    # dry run
    cli.dry_run(str(cfg_path))
    # run
    cli.run(str(cfg_path))
    assert Path('build/output/demo.docx').exists()
    assert Path('build/output/demo.pptx').exists()
