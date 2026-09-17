"""Make THIS checkout importable as the ``cowork_local`` package during tests.

Why this is not just a ``sys.path`` insert
------------------------------------------
Test modules import the app in two different styles:

* top-level (``from providers.base import ...``) — resolved by the repository
  root already sitting on ``sys.path`` when pytest is launched from it;
* fully qualified (``from cowork_local.core.routing.service import ...``) —
  which only resolves when a directory literally named ``cowork_local`` is
  importable.

Simply appending the repository's PARENT directory to ``sys.path`` (the previous
behaviour) makes the second style resolve against *whatever* sibling folder
happens to be called ``cowork_local`` — on a developer machine that is often an
unrelated older checkout, so the whole suite silently exercises the wrong code
while still reporting green. Instead we bind the name ``cowork_local`` in
``sys.modules`` to the package rooted at THIS repository, so both import styles
always reach the working copy under test regardless of the checkout's directory
name.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# .../<checkout>/tests/conftest.py -> .../<checkout>
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "cowork_local"

# The repository root must stay importable so the top-level import style
# (``providers``/``domain``/``application``/``tests``) keeps working.
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))


def _bind_checkout_as_package() -> None:
    """Register this checkout in ``sys.modules`` under the canonical package name.

    Executed at import time of the conftest (i.e. before any test module is
    imported) so that a stale same-named directory elsewhere on ``sys.path`` can
    never win the lookup. A no-op when the package is already bound to this very
    directory, which keeps repeated conftest loads (pytest-xdist, sub-sessions)
    idempotent.
    """
    existing = sys.modules.get(PACKAGE_NAME)
    if existing is not None:
        # Already bound. Only rebind when it points at a DIFFERENT checkout,
        # otherwise re-executing the package __init__ would duplicate module
        # state that tests may already hold references to.
        origin = getattr(existing, "__file__", "") or ""
        if Path(origin).resolve().parent == PACKAGE_ROOT:
            return

    spec = importlib.util.spec_from_file_location(
        PACKAGE_NAME,
        PACKAGE_ROOT / "__init__.py",
        # Declaring the search locations is what turns the module into a real
        # package, so ``cowork_local.core.routing`` and friends resolve as
        # sub-modules of this directory.
        submodule_search_locations=[str(PACKAGE_ROOT)],
    )
    if spec is None or spec.loader is None:  # pragma: no cover — defensive
        return
    module = importlib.util.module_from_spec(spec)
    # Insert BEFORE executing so that a circular ``import cowork_local`` from
    # inside the package body resolves to the partially-initialised module
    # instead of restarting the import (standard CPython import semantics).
    sys.modules[PACKAGE_NAME] = module
    spec.loader.exec_module(module)


_bind_checkout_as_package()


import pytest  # noqa: E402 - after the package binding above


@pytest.fixture(autouse=True)
def _reset_network_guard():
    """``build_context()`` binds the process-wide "Block network" gate to that
    context's config (default: blocked). Unbind after every test so one test
    that built a real context cannot silently block the network for the rest."""
    yield
    from cowork_local.application.network import network_guard

    network_guard.bind(None)
