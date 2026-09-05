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
from uuid import uuid4

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
          agent_role: str = "", correlation_id: str = "") -> None:
    """Append one audit event. Never raises — audit logging must never break
    a chat turn, a permission decision, or a tool call."""
    try:
        now = datetime.now()
        if kind == "mcp_call":
            safe_code = detail.removeprefix("code=")
            detail = (
                detail
                if detail in {"completed", "failed"}
                or (detail.startswith("code=") and safe_code.replace("_", "").isalnum())
                else ("completed" if ok else "failed")
            )
            correlation_id = correlation_id or str(uuid4())
        event = {
            "ts": now.isoformat(timespec="seconds"),
            "kind": kind,
            "agent_role": agent_role or "",
            "name": name or "",
            "ok": bool(ok),
            "detail": (detail or "")[:2000],   # bounded — never let a huge blob bloat the log
            "correlation_id": correlation_id or "",
            "account": _identity_account,
            "role": _identity_role,
            "machine": _identity_machine,
        }
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        path = AUDIT_DIR / f"{now.strftime('%Y-%m-%d')}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        _write_shared(event, now)
    except Exception:  # noqa: BLE001
        pass


def _write_shared(event: Dict[str, Any], now: datetime) -> None:
    """Best-effort mirror of ``event`` into the shared cross-machine store —
    one file PER MACHINE per day, so no two machines ever write the same
    file. Never raises."""
    if not _identity_shared_dir or not _identity_machine:
        return
    try:
        shared = Path(_identity_shared_dir).expanduser() / "telemetry" / "audit"
        shared.mkdir(parents=True, exist_ok=True)
        path = shared / f"{_identity_machine}-{now.strftime('%Y-%m-%d')}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass

def load_events(start: Optional[date] = None, end: Optional[date] = None,
                kind: Optional[Kind] = None,
                directory: Path = None) -> List[Dict[str, Any]]:
    """Events between ``start``/``end`` (inclusive; None = unbounded),
    optionally filtered to one ``kind`` — this IS how each Monitoring
    Dashboard panel gets its own slice of the same underlying log."""
    events = _logger.load_events(start=start, end=end, kind=kind, directory=directory)
    return [e.to_dict() for e in events]
