"""docflow.cli package - re-export CLI commands from app.py

This package exposes `app` (Typer app) and the top-level command functions used by
tests and by python -m docflow.cli.
"""
from .app import app, init, run, dry_run, inspect_template, config_validate

__all__ = ['app', 'init', 'run', 'dry_run', 'inspect_template', 'config_validate']
