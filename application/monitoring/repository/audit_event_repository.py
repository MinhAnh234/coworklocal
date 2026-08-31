"""Audit-event repository — the boundary between ``MonitoringQueryService``
and where events actually live. ``CanonicalAuditEventRepository`` is the real
adapter (wraps an injected ``CanonicalAuditLogger``); ``InMemoryAuditEventRepository``
is a constructor-injected test double, following this repo's existing
``Fake*``/``Recording*`` convention (see ``tests/routing/*``,
``tests/test_project_context_mcp_template.py``) rather than ``unittest.mock``.
"""
from __future__ import annotations

from typing import List, Optional, Protocol

from ..dto.audit_event_dto import AuditEventDTO


class AuditEventRepository(Protocol):
    """Cổng đọc nhật ký kiểm toán mà tầng application dùng.

    Chỉ là hợp đồng: bản cài đặt thật đọc từ file cục bộ hoặc thư mục chia sẻ,
    còn test truyền vào bộ giả.
    """
    def load(self, kind: Optional[str] = None) -> List[AuditEventDTO]:
        """Đọc sự kiện kiểm toán, lọc theo loại nếu có."""
        ...


class CanonicalAuditEventRepository:
    """Adapter over ``infrastructure.telemetry.audit_logger.CanonicalAuditLogger``
    — the only place this application service reaches into infrastructure."""

    def __init__(self, audit_logger) -> None:
        """Bọc bộ ghi nhật ký kiểm toán chuẩn để đọc sự kiện ra."""
        self._audit_logger = audit_logger

    def load(self, kind: Optional[str] = None) -> List[AuditEventDTO]:
        """Đọc sự kiện từ nhật ký và đổi sang DTO của tầng application."""
        events = self._audit_logger.load_events(kind=kind)
        return [AuditEventDTO.from_raw(e.to_dict()) for e in events]


class InMemoryAuditEventRepository:
    """Test double — holds a fixed list of events, no file I/O."""

    def __init__(self, events: List[AuditEventDTO]) -> None:
        """Nhận sẵn danh sách sự kiện. Chép lại chứ không giữ tham chiếu: bên gọi sửa
        danh sách gốc thì kết quả test không được đổi theo.
        """
        self._events = list(events)

    def load(self, kind: Optional[str] = None) -> List[AuditEventDTO]:
        """Trả về danh sách đã nạp sẵn, lọc theo loại nếu có."""
        if kind is None:
            return list(self._events)
        return [e for e in self._events if e.kind == kind]
