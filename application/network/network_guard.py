"""One gate for every outbound connection the app makes on its own.

The "Block network" switch (``agent_security.block_network``) used to be read
only where agent tools run, so Microsoft 365, Teams, connector test buttons,
scheduled task scripts, pip auto-installs and HTML previews still reached the
internet while Monitoring said "Network: blocked". Each of those now asks
this module first.

The AI provider path (chat, model list, model test) deliberately does NOT go
through here: with the switch on the user still talks to the model, but the
app fetches nothing else on the model's or its own behalf.

The module holds a *reader*, not a copy of the flag: the Composition Root
binds it to the live config once (``presentation/shell/bootstrap.py``), so a
change saved in Settings takes effect on the very next call. Nothing bound
(unit tests, helper subprocesses) means "not blocked", the pre-switch default.
"""
from __future__ import annotations

import threading
from typing import Callable, Optional

_lock = threading.Lock()
_reader: Optional[Callable[[], bool]] = None


class NetworkBlockedError(PermissionError):
    """Raised by :func:`ensure_allowed` while the switch is on."""


def bind(reader: Optional[Callable[[], bool]]) -> None:
    """Install the callable that says whether the network is blocked right now."""
    global _reader
    with _lock:
        _reader = reader


def is_blocked() -> bool:
    """True while "Block network" is on. A failing reader counts as blocked."""
    reader = _reader
    if reader is None:
        return False
    try:
        return bool(reader())
    except Exception:  # noqa: BLE001 - fail closed: an unreadable switch must not open the network
        return True


def refusal(purpose: str) -> str:
    """The message shown (to the user or the model) when ``purpose`` is refused."""
    return (f"{purpose}: network access is blocked by the Sandbox Security Layer "
            "(\"Block network\" is on in Settings). Only the AI provider may be reached.")


def ensure_allowed(purpose: str) -> None:
    """Raise :class:`NetworkBlockedError` if ``purpose`` may not go online now."""
    if is_blocked():
        raise NetworkBlockedError(refusal(purpose))


__all__ = ["NetworkBlockedError", "bind", "ensure_allowed", "is_blocked", "refusal"]
