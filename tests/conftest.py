"""Shared pytest helpers. Scripts in scripts/ start with digits (e.g.
06_build_vote_deltas.py), so they can't be imported as normal Python
modules — this loads them directly from their file path instead."""

import importlib.util
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


def load_script(module_name: str, filename: str):
    path = SCRIPTS_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
