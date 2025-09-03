from pathlib import Path
from docflow.cli import init as cli_init
from docflow.runtime.orchestrator import run_config


def test_orchestrator_runs(tmp_path, monkeypatch):
    # run init to create example config and templates in repo
    cli_init('config/example.config.yaml')
    res = run_config('config/example.config.yaml')
    assert isinstance(res, dict)
    # ensure outputs were written
    outdir = Path('build/output')
    assert outdir.exists()
    files = list(outdir.iterdir())
    assert len(files) >= 1
