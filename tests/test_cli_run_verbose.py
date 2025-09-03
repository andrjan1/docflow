from docflow.runtime.orchestrator import run_config
from docflow.cli import init as cli_init


def test_cli_run_verbose():
    # ensure init has been run
    cli_init('config/example.config.yaml')
    run_config('config/example.config.yaml', verbose=True)
