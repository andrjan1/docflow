from importlib import import_module


def test_module_help():
    mod = import_module('docflow.cli')
    # ensure help command exists
    assert hasattr(mod, 'app')
