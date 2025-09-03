"""Compatibility shim re-exporting CLI commands from `docflow.cli.app`.

This module exists so existing imports like `from docflow.cli import init` used in
tests continue to work after consolidating CLI logic in `docflow.cli.app`.
"""
from .app import app, init, run, dry_run, inspect_template, config_validate

__all__ = ['app', 'init', 'run', 'dry_run', 'inspect_template', 'config_validate']
