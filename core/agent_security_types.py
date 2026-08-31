"""Shared value types for the Agent Security guardrails.

``SecurityVerdict``/``SecurityBlocked`` used to be defined in
``agent_security.py``, which forced ``agent_security_alert.py`` (which only
needs the *type*, to annotate/read ``notify_admin``'s ``verdict`` argument) to
import from it — while ``agent_security.py`` itself needed to call
``agent_security_alert.notify_admin()``, an architectural cycle only avoided
at runtime by deferring that second import inside a function body.

Hoisting the shared type into this dependency-free leaf module lets both
sides import it directly, so ``agent_security.py`` can import
``agent_security_alert`` at module top level too — no cycle, no deferred
imports needed for this pair.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SecurityVerdict:
    """Kết quả một lớp kiểm an toàn: cho qua hay không, lý do, và lớp nào ra phán quyết."""
    allowed: bool
    reason: str = ""
    layer: str = ""   # "prompt" | "attachment" | "command"


class SecurityBlocked(RuntimeError):
    """A guardrail refused an action. ``verdict`` carries the full detail for
    the admin alert; ``str(exc)`` is the short, user-facing reason."""

    def __init__(self, verdict: SecurityVerdict):
        """Lấy lý do trong phán quyết làm thông điệp; không có lý do thì ghi rõ lớp nào chặn."""
        super().__init__(verdict.reason or f"Blocked by agent security ({verdict.layer}).")
        self.verdict = verdict
