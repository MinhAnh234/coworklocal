"""Tiny opt-in performance tracing helpers.

Tracing is disabled by default and emits only timings/counts, never prompts,
credentials, file contents, or provider payloads.
"""
from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager

_LOG = logging.getLogger("cowork.performance")


def enabled() -> bool:
    return os.environ.get("COWORK_PERF_TRACE", "").strip().lower() in {"1", "true", "yes"}


@contextmanager
def span(name: str, **fields):
    if not enabled():
        yield
        return
    started = time.perf_counter()
    try:
        yield
    finally:
        elapsed = (time.perf_counter() - started) * 1000.0
        safe = " ".join(f"{k}={v}" for k, v in fields.items())
        _LOG.info("perf %s %.1fms%s", name, elapsed, f" {safe}" if safe else "")
