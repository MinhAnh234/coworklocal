"""Qt-backed adapters for pure interfaces used elsewhere in the app (EPIC R07).

Note: the original plan (``docs/refactor/Feature_Architecture_Proposal.md``)
placed this adapter at a new top-level ``platform/qt/`` package. That name
was dropped after it was shown to actually shadow the stdlib ``platform``
module (used by ``core/windows_sandbox_vm.py``/``core/appcontainer_sandbox.
py``) whenever the repo root ends up on ``sys.path`` directly - e.g. running
``python -c "..."`` (or any script) with the repo root as the working
directory, which resolves a bare ``import platform`` to this package instead
of the standard library one. ``infrastructure/`` already exists as a layer
for exactly this kind of toolkit-specific implementation
(``infrastructure/filesystem/``, ``infrastructure/mcp/``, ...), so the
adapter lives here instead - same content, safer location.
"""

from .qt_scheduler_clock import QtSchedulerClock

__all__ = ["QtSchedulerClock"]
