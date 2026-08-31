"""Canonical audit event logging — the infrastructure behind
``core/audit_log.py``'s ``set_identity``/``record``/``load_events`` free
functions (kept as thin wrappers over a module-level singleton for backward
compatibility with every existing call site).

Same on-disk shape as before: one JSON line per event, one file per day
under ``~/.cowork_local/audit/`` (plus a best-effort mirror into a shared
cross-machine folder when an identity's ``shared_dir`` is set). ``record()``
never raises — audit logging must never break a chat turn, a permission
decision, or a tool call.

The event schema is unchanged (same field names, same order) so every
``.jsonl`` file written before this refactor remains fully readable. New
event kinds can be added by defining another ``KIND_*`` constant — nothing
about the schema itself needs to change to support one.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Known kinds today. ``kind`` stays a plain str (not an enum) so a caller can
# always pass a new value without editing this module — these constants are
# just the documented, current vocabulary.
KIND_TOOL_CALL = "tool_call"
KIND_PERMISSION = "permission"
KIND_SECURITY_BLOCK = "security_block"
KIND_MCP_CALL = "mcp_call"


@dataclass(frozen=True)
class CanonicalAuditEvent:
    """One audit log entry. Field order matches the pre-refactor
    ``core/audit_log.py`` schema exactly, for byte-compatible JSON output."""

    ts: str
    kind: str
    agent_role: str
    name: str
    ok: bool
    detail: str
    account: str
    role: str
    machine: str

    def to_dict(self) -> Dict[str, Any]:
        """Bản ghi dưới dạng dict để ghi JSONL."""
        return {
            "ts": self.ts,
            "kind": self.kind,
            "agent_role": self.agent_role,
            "name": self.name,
            "ok": self.ok,
            "detail": self.detail,
            "account": self.account,
            "role": self.role,
            "machine": self.machine,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "CanonicalAuditEvent":
        """Tolerant of missing keys, so old/partial rows never fail to load."""
        return cls(
            ts=str(raw.get("ts", "")),
            kind=str(raw.get("kind", "")),
            agent_role=str(raw.get("agent_role", "")),
            name=str(raw.get("name", "")),
            ok=bool(raw.get("ok", False)),
            detail=str(raw.get("detail", "")),
            account=str(raw.get("account", "")),
            role=str(raw.get("role", "")),
            machine=str(raw.get("machine", "")),
        )


@dataclass
class _Identity:
    """Danh tính gắn vào mọi bản ghi: tài khoản, vai trò, máy và thư mục chia sẻ."""
    account: str = ""
    role: str = ""
    machine: str = ""
    shared_dir: str = ""


class CanonicalAuditLogger:
    """Day-sharded JSONL audit writer/reader. Process identity (who's logged
    in, this machine's name) is set once via :meth:`set_identity`, mirroring
    the pre-refactor module-global pattern but held as instance state so this
    class can be constructed/injected instead of relying on globals."""

    def __init__(self, audit_dir: Path):
        """Danh tính (người dùng, máy) được lấy một lần lúc dựng: nó không đổi trong
        một phiên, và mỗi dòng nhật ký đều cần tới.
        """
        self.audit_dir = Path(audit_dir)
        self._identity = _Identity()

    def set_identity(self, account: str, machine: str, role: str = "",
                     shared_dir: str = "") -> None:
        """Called once after login succeeds. ``shared_dir``, when reachable,
        makes every subsequent :meth:`record` ALSO best-effort-append to the
        shared cross-machine telemetry store."""
        self._identity = _Identity(account=account or "", role=role or "",
                                   machine=machine or "", shared_dir=shared_dir or "")

    def record(self, kind: str, name: str, ok: bool, detail: str = "",
              agent_role: str = "") -> None:
        """Append one audit event. Never raises."""
        try:
            now = datetime.now()
            event = CanonicalAuditEvent(
                ts=now.isoformat(timespec="seconds"),
                kind=kind,
                agent_role=agent_role or "",
                name=name or "",
                ok=bool(ok),
                detail=(detail or "")[:2000],
                account=self._identity.account,
                role=self._identity.role,
                machine=self._identity.machine,
            )
            self.audit_dir.mkdir(parents=True, exist_ok=True)
            path = self.audit_dir / f"{now.strftime('%Y-%m-%d')}.jsonl"
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
            self._write_shared(event, now)
        except Exception:  # noqa: BLE001
            pass

    def _write_shared(self, event: CanonicalAuditEvent, now: datetime) -> None:
        """Ghi thêm một bản sao vào thư mục chia sẻ của đội, nếu có cấu hình.

        Thiếu thư mục chia sẻ hoặc thiếu tên máy thì bỏ qua — bản ghi cục bộ vẫn có,
        và một lỗi ghi mạng không được làm hỏng lượt chạy.
        """
        identity = self._identity
        if not identity.shared_dir or not identity.machine:
            return
        try:
            shared = Path(identity.shared_dir).expanduser() / "telemetry" / "audit"
            shared.mkdir(parents=True, exist_ok=True)
            path = shared / f"{identity.machine}-{now.strftime('%Y-%m-%d')}.jsonl"
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        except Exception:  # noqa: BLE001
            pass

    def load_events(self, start: Optional[date] = None, end: Optional[date] = None,
                    kind: Optional[str] = None,
                    directory: Optional[Path] = None) -> List[CanonicalAuditEvent]:
        """Events between ``start``/``end`` (inclusive; None = unbounded),
        optionally filtered to one ``kind``."""
        directory = directory or self.audit_dir
        if not directory.exists():
            return []
        events: List[CanonicalAuditEvent] = []
        for path in sorted(directory.glob("*.jsonl")):
            try:
                day = datetime.strptime(path.stem, "%Y-%m-%d").date()
            except ValueError:
                continue
            if (start and day < start) or (end and day > end):
                continue
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    raw = json.loads(line)
                    if kind is not None and raw.get("kind") != kind:
                        continue
                    events.append(CanonicalAuditEvent.from_dict(raw))
            except (OSError, json.JSONDecodeError):
                continue
        return events
