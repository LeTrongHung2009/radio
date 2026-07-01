"""
Test configuration.

We import specific modules directly to avoid triggering __init__.py files
that pull in heavy dependencies (pydantic_settings, twitchio, etc.).
"""

import sys
import os
import importlib

# Paths for both codebases
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPANION_DIR = os.path.join(REPO_ROOT, "companion")
MY_COMPANION_DIR = os.path.join(REPO_ROOT, "MyCompanion")


def import_module_directly(module_path, module_name):
    """Import a Python module file directly, bypassing package __init__.py."""
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod
