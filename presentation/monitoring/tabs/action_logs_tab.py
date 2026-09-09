"""Action Logs tab — the full audit log, newest first. Extracted from
``ui/monitoring_tab.py``'s action-table wiring inside
``MonitoringTab.__init__``.
"""
from __future__ import annotations

from typing import Callable, List

from PySide6.QtWidgets import QLineEdit, QPushButton, QWidget

from ....i18n import tr
from ..shared.ai_filter import start_ai_filter
from ..shared.event_table import EventTable
from ..shared.filter_scaffold import build_filter_scaffold


class ActionLogsTab(QWidget):
    """Tab "Nhật ký hành động": bảng mọi thao tác đọc/ghi tệp và chạy lệnh của agent."""
    def __init__(self, ctx, on_refresh_all: Callable[[], None]):
        """Tab Nhật ký hành động: bảng sự kiện kèm bộ lọc dùng chung."""
        super().__init__()
        self._ctx = ctx
        self._ai_state: dict = {}
        self.table = EventTable()
        parts = build_filter_scaffold(
            self, self.table, on_refresh=on_refresh_all,
            title_key="monitoring.action_logs_title",
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
