"""Centralized audit log — the single source of truth behind the Monitoring
Dashboard's "Security Events", "MCP Call History", and "Action Logs" panels
(each is just a filtered VIEW of this one log by ``kind``, not 3 separate
storage systems).

One JSON line per event, one file per day under ``~/.cowork_local/audit/`` —
same on-disk shape as ``usage_tracker.py`` (day-sharded ``.jsonl``, append-only,
``record()`` never raises so audit logging can never break a chat turn).

This module is now a thin, backward-compatible wrapper around
:class:`infrastructure.telemetry.audit_logger.CanonicalAuditLogger` — every
existing call site (``agent_security.py``, ``chat_agent.py``, ``tools.py``,
``ext_connectors.py``, ``mcp_client.py``, ``ms365_local.py``,
``permissions.py``, ``ui/structure_graph_view.py``, ``app.py``) keeps calling
``audit_log.set_identity``/``record``/``load_events`` exactly as before; only
the implementation moved.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import CONFIG_DIR
from ..infrastructure.telemetry.audit_logger import CanonicalAuditLogger

AUDIT_DIR = CONFIG_DIR / "audit"

# One of: "tool_call" (a built-in file/command tool ran), "permission" (a
# PermissionGate decision), "security_block" (Agent Security refused an
# action), "mcp_call" (a call to an external MCP server's tool).
Kind = str

_logger = CanonicalAuditLogger(AUDIT_DIR)


def set_identity(account: str, machine: str, role: str = "", shared_dir: str = "") -> None:
    """Called once after login succeeds. ``shared_dir``, when reachable,
    makes every subsequent :func:`record` ALSO best-effort-append to the
    shared cross-machine telemetry store (see :mod:`telemetry_shared`)."""
    _logger.set_identity(account, machine, role=role, shared_dir=shared_dir)


def record(kind: Kind, name: str, ok: bool, detail: str = "",
          agent_role: str = "") -> None:
    """Append one audit event. Never raises — audit logging must never break
    a chat turn, a permission decision, or a tool call."""
    _logger.record(kind, name, ok, detail=detail, agent_role=agent_role)


def load_events(start: Optional[date] = None, end: Optional[date] = None,
                kind: Optional[Kind] = None,
                directory: Path = None) -> List[Dict[str, Any]]:
    """Events between ``start``/``end`` (inclusive; None = unbounded),
    optionally filtered to one ``kind`` — this IS how each Monitoring
    Dashboard panel gets its own slice of the same underlying log."""
    events = _logger.load_events(start=start, end=end, kind=kind, directory=directory)
    return [e.to_dict() for e in events]
