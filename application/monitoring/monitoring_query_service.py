"""Read-only query service over audit events — filter + sort + pagination.

Pure Python: no PySide6 import, no UI code. Depends only on an injected
``AuditEventRepository`` (see ``repository/audit_event_repository.py``), so it
is fully unit-testable with ``InMemoryAuditEventRepository`` and independent
of file I/O or Qt.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .dto.audit_event_dto import AuditEventDTO
from .repository.audit_event_repository import AuditEventRepository


@dataclass(frozen=True)
class Page:
    """Một trang kết quả truy vấn nhật ký: các mục, tổng số, số trang và cỡ trang."""
    items: List[AuditEventDTO]
    total: int
    page: int
    page_size: int

    @property
    def has_more(self) -> bool:
        """Còn trang sau nữa không."""
        return self.page * self.page_size < self.total


class MonitoringQueryService:
    """Read-only. Callers ask for a filtered/sorted/paginated slice of the
    audit log; this service never writes anything."""

    def __init__(self, repository: AuditEventRepository) -> None:
        """Nhận kho sự kiện kiểm toán qua tham số — bản thật đọc đĩa, bản test nằm
        trong bộ nhớ.
        """
        self._repository = repository

    def query(self, kind: Optional[str] = None, ok: Optional[bool] = None,
              text: Optional[str] = None, sort_by: str = "ts",
              descending: bool = True, page: int = 1, page_size: int = 50) -> Page:
        """Lọc theo loại/kết quả/từ khoá, sắp xếp rồi cắt thành một trang."""
        events = self._repository.load(kind=kind)

        if ok is not None:
            events = [e for e in events if e.ok == ok]
        if text:
            needle = text.lower()
            events = [e for e in events
                     if needle in e.name.lower() or needle in e.detail.lower()]

        events = sorted(events, key=lambda e: getattr(e, sort_by, ""), reverse=descending)

        total = len(events)
        page = max(1, page)
        start = (page - 1) * page_size
        items = events[start:start + page_size] if page_size > 0 else events
        return Page(items=items, total=total, page=page, page_size=page_size)
