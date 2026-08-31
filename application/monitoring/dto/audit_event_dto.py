"""Application-layer view of an audit event — decoupled from the
infrastructure ``CanonicalAuditEvent`` so ``application/`` doesn't need to
share a concrete class with ``infrastructure/`` (only the shape). Field names
match the canonical audit schema (see
``infrastructure/telemetry/audit_logger.py``) 1:1.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class AuditEventDTO:
    """Một sự kiện kiểm toán ở dạng tầng application dùng — không phụ thuộc khuôn
    lưu trên đĩa, nên đổi định dạng nhật ký không kéo theo sửa giao diện.
    """
    ts: str
    kind: str
    name: str
    ok: bool
    detail: str
    agent_role: str = ""
    account: str = ""
    role: str = ""
    machine: str = ""

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> "AuditEventDTO":
        """Tolerant of missing keys — accepts both a
        ``CanonicalAuditEvent.to_dict()`` result and any historical raw
        ``.jsonl`` row."""
        return cls(
            ts=str(raw.get("ts", "")),
            kind=str(raw.get("kind", "")),
            name=str(raw.get("name", "")),
            ok=bool(raw.get("ok", False)),
            detail=str(raw.get("detail", "")),
            agent_role=str(raw.get("agent_role", "")),
            account=str(raw.get("account", "")),
            role=str(raw.get("role", "")),
            machine=str(raw.get("machine", "")),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Bản ghi dưới dạng dict cho lớp giao diện."""
        return {
            "ts": self.ts, "kind": self.kind, "agent_role": self.agent_role,
            "name": self.name, "ok": self.ok, "detail": self.detail,
            "account": self.account, "role": self.role, "machine": self.machine,
        }
