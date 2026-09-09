"""Security Events tab — the audit log filtered to ``kind="security_block"``.
Extracted from ``ui/monitoring_tab.py``'s security-events wiring inside
``MonitoringTab.__init__``.
"""
from __future__ import annotations

from typing import Callable, List

from PySide6.QtWidgets import QLineEdit, QPushButton, QWidget

from ....i18n import tr
from ..shared.ai_filter import start_ai_filter
from ..shared.event_table import EventTable
from ..shared.filter_scaffold import build_filter_scaffold


class SecurityEventsTab(QWidget):
    """Tab "Sự kiện bảo mật": các lượt bị chặn hoặc phải xin phê duyệt."""
    def __init__(self, ctx, on_refresh_all: Callable[[], None]):
        """Tab Sự kiện bảo mật.

        Bỏ cột Kết quả (mọi dòng đều là bị chặn) và thay bằng cột Hành động có tô
        màu theo mức nghiêm trọng.
        """
        super().__init__()
        self._ctx = ctx
        self._ai_state: dict = {}
        # Security events are always ok=False, so this table trades the
        # tick/cross column for a tinted Action column (see EventTable).
        self.table = EventTable(show_result=False)
        parts = build_filter_scaffold(
            self, self.table, on_refresh=on_refresh_all,
            title_key="monitoring.security_events_title",
            with_search=True, with_detail=True, with_page_size=True,
            on_ai_filter=self._start_ai_filter)
        self.title_lbl = parts["title_lbl"]
        self.title_key = parts["title_key"]
        self.title_refresh_btn = parts["title_refresh_btn"]
        self.filter_edit = parts["filter_edit"]
        self.ai_filter_btn = parts["ai_filter_btn"]
        self.detail_panel = parts["detail_panel"]
        self.page_size_label = parts["page_size_label"]

    def set_events(self, events: List[dict]) -> None:
        """Đổ danh sách sự kiện vào bảng."""
        self.table.set_events(events)

    def retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn."""
        self.table.retranslate()
        self.filter_edit.setPlaceholderText(tr("monitoring.filter_placeholder"))
        self.detail_panel.retranslate()
        self.title_lbl.setText(tr(self.title_key))
        self.title_refresh_btn.setText(tr("monitoring.refresh"))
        self.page_size_label.setText(tr("monitoring.page_size_label"))

    def _start_ai_filter(self, search: QLineEdit, ai_btn: QPushButton) -> None:
        """Nhờ AI dịch câu tìm kiếm tự nhiên thành từ khoá lọc."""
        start_ai_filter(self._ctx, search, ai_btn, self._ai_state)
