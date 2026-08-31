"""Root pytest conftest — loaded before ``tests/conftest.py``.

This checkout lives on disk as ``Refactor`` (not ``cowork_local``), while
``tests/`` imports everything as ``from cowork_local... import ...`` and
``tests/conftest.py`` makes that resolve by putting this repo's *parent*
directory on ``sys.path`` (expecting the repo root itself to be named
``cowork_local``). A sibling folder literally named ``cowork_local`` (an
unrelated, older checkout) already exists next to this one, so without this
file Python would silently import THAT folder instead of this repository
whenever a test does ``import cowork_local``.

Registering the alias here — before ``tests/conftest.py`` touches
``sys.path`` — caches this repository in ``sys.modules['cowork_local']``
first, so the later ``sys.path`` mutation has nothing left to do (imports
are cached by name; the first successful import of a given name wins for
the rest of the process).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent

if "cowork_local" not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        "cowork_local", _ROOT / "__init__.py", submodule_search_locations=[str(_ROOT)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["cowork_local"] = module
    spec.loader.exec_module(module)
