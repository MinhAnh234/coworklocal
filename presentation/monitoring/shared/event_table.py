"""Read-only audit-event table shared by the Security Events / MCP Call
History / Action Logs tabs, plus the click-outside-closes-detail-panel event
filter. Extracted verbatim from ``ui/monitoring_tab.py``.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QEvent, QObject, QRect, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QWidget

from ....core import agent_roles
from ....i18n import tr
from ....theme import current_palette
from ....ui.icons import DOT_GREEN, DOT_RED, icon
from .badges import action_label
from .formatters import agent_avatar_icon, fmt_event_time

_DEFAULT_PAGE_SIZE = 20
PAGE_SIZE_OPTIONS = (5, 10, 20, 50, 100)


class _TimeItem(QTableWidgetItem):
    """The Time column shows "dd/MM hh:mm", which does not sort correctly as
    text (day-of-month leads, not year/month) — so sorting compares the raw
    ISO ``ts`` each item is built from instead of its displayed text."""

    def __init__(self, raw_ts: str, display: str):
        """Ô thời gian giữ luôn chuỗi gốc: hiện ra là chữ đã rút gọn, nhưng sắp xếp
        phải theo mốc thật chứ không theo thứ tự chữ cái.
        """
        super().__init__(display)
        self._raw_ts = raw_ts

    def __lt__(self, other):
        """So sánh theo mốc thời gian gốc, không theo chuỗi hiển thị.

        Sắp theo chuỗi đã định dạng sẽ ra thứ tự sai ngay khi định dạng có chữ
        ("5 phút trước" đứng trước "hôm qua").
        """
        if isinstance(other, _TimeItem):
            return self._raw_ts < other._raw_ts
        return super().__lt__(other)


class EventTable(QTableWidget):
    """A read-only table of audit-log events — newest-first by default, and
    every column header is click-to-sort (ascending/descending toggle; the
    Time column sorts by the underlying ISO timestamp, not its "dd/MM hh:mm"
    display text — see :class:`_TimeItem`)."""

    # What each blocked action is, as a colour. Security events all record
    # ok=False, so the tick/cross column said the same thing on every row; the
    # useful distinction is WHICH rule fired.
    _ACTION_TINTS = {
        "prompt": "accent",
        "dangerous_command": "danger",
        "run_command": "danger",
        "install_package": "warning",
        "path_outside_sandbox": "success",
        "network_blocked": "accent",
        "secret_in_output": "warning",
    }

    # Emitted whenever the rendered page changes (new data, page-size change,
    # or prev/next navigation) — args are (current_page, page_count), both
    # 1-based-friendly in that current_page is 0-indexed but page_count is a
    # plain count. filter_scaffold.py's pager label/buttons listen to this.
    page_changed = Signal(int, int)

    def __init__(self, show_result: bool = True):
        # Security Events drops the result column entirely (see _ACTION_TINTS).
        """Bảng sự kiện dùng chung của các tab Giám sát.

        ``show_result`` tắt cột Kết quả cho màn Sự kiện bảo mật — ở đó mọi dòng đều
        là thất bại nên cột ấy chỉ tốn chỗ.
        """
        self._show_result = show_result
        self._page_size = _DEFAULT_PAGE_SIZE
        self._current_page = 0
        self._last_events: List[dict] = []
        self._sorted_events: List[dict] = []
        super().__init__(0, 7 if show_result else 6)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setIconSize(QSize(20, 20))
        self.verticalHeader().setVisible(False)
        # Fixed row height — letting Qt auto-size rows from content fought with
        # the action column's cell widget geometry settling stale/oversized on
        # an intermediate sizing pass, clipping the pill's text.
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.verticalHeader().setDefaultSectionSize(32)
        self.setSortingEnabled(True)
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        for col in range(self.columnCount() - 1):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)

    def retranslate(self) -> None:
        """Áp lại tên cột theo ngôn ngữ đang chọn."""
        cols = [tr("monitoring.col_time"),
                tr("monitoring.col_agent") if not self._show_result else tr("monitoring.col_role"),
                tr("monitoring.col_account"), tr("monitoring.col_machine")]
        if self._show_result:
            cols += [tr("monitoring.col_name"), tr("monitoring.col_result")]
        else:
            cols += [tr("monitoring.col_action")]
        cols += [tr("monitoring.col_detail_block") if not self._show_result else tr("monitoring.col_detail")]
        self.setHorizontalHeaderLabels(cols)

    def page_size(self) -> int:
        """Số dòng đang hiển thị mỗi trang."""
        return self._page_size

    def page_count(self) -> int:
        """Tổng số trang với dữ liệu và số dòng/trang hiện tại (tối thiểu 1)."""
        if not self._sorted_events:
            return 1
        return -(-len(self._sorted_events) // self._page_size)  # ceil div

    def current_page(self) -> int:
        """Trang đang hiển thị, đánh số từ 0."""
        return self._current_page

    def go_to_page(self, page: int) -> None:
        """Nhảy tới một trang cụ thể (đánh số từ 0), tự kẹp trong khoảng hợp lệ."""
        self._current_page = page
        self._render_current_page()

    def next_page(self) -> None:
        """Sang trang kế — không làm gì nếu đã ở trang cuối."""
        self.go_to_page(self._current_page + 1)

    def prev_page(self) -> None:
        """Về trang trước — không làm gì nếu đã ở trang đầu."""
        self.go_to_page(self._current_page - 1)

    def set_page_size(self, n: int) -> None:
        """Đổi số dòng hiển thị mỗi trang, quay về trang đầu, rồi vẽ lại với dữ
        liệu đã có sẵn (không cần refresh lại từ nguồn)."""
        self._page_size = n
        self._current_page = 0
        self._render_current_page()

    def set_events(self, events: List[dict]) -> None:
        """Đổ danh sách sự kiện vào bảng: mới nhất lên đầu, chia trang theo
        ``self._page_size`` — xem qua trang khác bằng ``next_page``/``prev_page``
        (nút tiến/lùi ở filter_scaffold.py), không còn bị cắt bỏ vĩnh viễn như
        trước (DF-006)."""
        self._last_events = events
        self._sorted_events = sorted(events, key=lambda e: e.get("ts", ""), reverse=True)
        self._current_page = 0
        self._render_current_page()

    def _render_current_page(self) -> None:
        """Vẽ đúng một trang (theo ``self._current_page``/``self._page_size``)
        từ ``self._sorted_events`` đã sắp sẵn.

        Tắt sắp xếp trong lúc đổ dữ liệu — để bật, Qt sắp lại sau mỗi dòng và việc
        nạp chậm đi theo bậc hai.
        """
        self._current_page = max(0, min(self._current_page, self.page_count() - 1))
        start = self._current_page * self._page_size
        events = self._sorted_events[start:start + self._page_size]
        self.setSortingEnabled(False)
        self.setRowCount(len(events))
        for row, ev in enumerate(events):
            is_admin_violation = ev.get("role") == "admin" and not ev.get("ok", True)
            cells = [
                ev.get("ts", ""), agent_roles.label_for(ev.get("agent_role", "")),
                ev.get("account", "") or "—", ev.get("machine", "") or "—",
                ev.get("name", ""),
            ]
            if self._show_result:
                cells.append("")
            cells.append((ev.get("detail") or "")[:300])
            pal = current_palette()
            for col, text in enumerate(cells):
                item = (_TimeItem(str(text), fmt_event_time(str(text))) if col == 0
                        else QTableWidgetItem(str(text)))
                if col == 0:
                    # Stash the full event (untruncated detail included) on the
                    # Time cell, so a click-to-open detail panel survives the
                    # user re-sorting the table by any column.
                    item.setData(Qt.UserRole, ev)
                if col == 1:
                    item.setIcon(agent_avatar_icon(str(text)))
                if self._show_result and col == 5:
                    item.setIcon(icon("check", color=DOT_GREEN) if ev.get("ok")
                                 else icon("close", color=DOT_RED))
                if not self._show_result and col == 4:
                    # Human-readable label, tinted by which rule fired, via the
                    # ITEM's own colours — NOT a setCellWidget() pill, which is
                    # pinned to a screen position rather than travelling with
                    # the item across a re-sort.
                    tint = getattr(pal, self._ACTION_TINTS.get(
                        ev.get("name", ""), "text_muted"), pal.text_muted)
                    item.setText(action_label(str(text)))
                    colour = QColor(tint)
                    item.setForeground(QBrush(colour))
                    soft = QColor(colour)
                    soft.setAlpha(38)
                    item.setBackground(QBrush(soft))
                if is_admin_violation:
                    item.setBackground(QBrush(QColor(229, 72, 77, 60)))
                self.setItem(row, col, item)
        self.setSortingEnabled(True)
        self.apply_filter(getattr(self, "_filter_needle", ""))
        self.page_changed.emit(self._current_page, self.page_count())

    def apply_filter(self, needle: str) -> None:
        """Ẩn/hiện dòng theo từ khoá tìm kiếm (không phân biệt hoa thường)."""
        self._filter_needle = (needle or "").strip().lower()
        for row in range(self.rowCount()):
            if not self._filter_needle:
                self.setRowHidden(row, False)
                continue
            match = any(
                self._filter_needle in (self.item(row, col).text().lower()
                                        if self.item(row, col) else "")
                for col in range(self.columnCount()))
            self.setRowHidden(row, not match)

    def event_at_row(self, row: int) -> Optional[dict]:
        """Bản ghi sự kiện gắn với một dòng; ``None`` nếu dòng trống."""
        item = self.item(row, 0)
        return item.data(Qt.UserRole) if item else None


class ClickOutsideCloser(QObject):
    """Closes the event-detail panel on a click anywhere outside the
    table/panel splitter — judged by screen-space geometry (is the click's
    global position inside the splitter's on-screen rectangle), not by which
    exact widget object received the event (unreliable mid-drag on the
    splitter's handle)."""

    def __init__(self, table: "EventTable", panel: QWidget, container: QWidget):
        """Bấm ra ngoài panel chi tiết thì đóng nó lại."""
        super().__init__(container)
        self._table = table
        self._panel = panel
        self._container = container

    def eventFilter(self, obj, event) -> bool:
        """Bắt cú bấm chuột trong toàn khung: rơi ngoài cả bảng lẫn panel thì đóng panel."""
        if event.type() == QEvent.MouseButtonPress and self._panel.isVisible():
            global_pos = event.globalPosition().toPoint()
            top_left = self._container.mapToGlobal(self._container.rect().topLeft())
            rect = QRect(top_left, self._container.size())
            if not rect.contains(global_pos):
                self._table.clearSelection()
        return False
