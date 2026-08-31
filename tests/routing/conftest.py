"""Pytest fixtures/shared helpers for the routing test suite.

Package importability is handled once and for all by ``tests/conftest.py``,
which binds THIS checkout to the ``cowork_local`` name in ``sys.modules``.
This file used to push the checkout's PARENT directory onto ``sys.path``, which
let an unrelated sibling folder named ``cowork_local`` shadow the working copy —
so that logic is intentionally gone; keep it that way.
"""
from __future__ import annotations
