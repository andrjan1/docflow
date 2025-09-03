
"""Top-level package marker for the project's src directory.

This file makes the `src` directory an importable package so imports like
`src.docflow.logging_lib` work during tests. We expose the `docflow`
subpackage (if present) as an attribute on the `src` package to keep
backwards-compatible imports working.
"""

from importlib import import_module
from types import ModuleType
from typing import Optional

__all__ = ["docflow"]


def _load_docflow() -> Optional[ModuleType]:
	"""Attempt to import the `src.docflow` subpackage and return it.

	If import fails (e.g., running from an environment where the package
	layout is different), return None and allow normal import errors to
	surface later.
	"""
	try:
		# Import as a submodule of src so that `src.docflow...` works
		mod = import_module("src.docflow")
		return mod
	except Exception:
		return None


# Try to load the docflow subpackage lazily at import time.
docflow = _load_docflow()

