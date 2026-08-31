"""Calendar view for Schedule Task — an alternative to the Kanban board
(R08-T11, relocated from ``ui/calendar_view.py`` with no logic changes):
Week / Month / Year granularity, each task placed on its scheduled date
(``schedule.run_at``). Click a task to edit it (same editor the Kanban
board's double-click opens); click a day's "+" to create a task pre-filled
with that date. All grid/date math lives in ``core/calendar_grid.py`` (no Qt,
directly unit-testable) — this module is just the Qt rendering of it.
"""
from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from cowork_local.core.calendar_grid import (
    GRANULARITIES, group_tasks_by_date, month_grid, month_task_counts, shift_period, week_days,
)
from cowork_local.i18n import on_language_changed, tr
from cowork_local.theme import current_palette
from cowork_local.ui.icons import icon

_WEEKDAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


class _DayCell(QFrame):
    """Một ô ngày trên lưới lịch: số ngày, nút thêm task, và danh sách task của ngày đó."""
    add_requested = Signal(str)   # "YYYY-MM-DD"
    task_clicked = Signal(str)    # task_id

    def __init__(self):
        """Một ô ngày trên lịch, chứa các task đến hạn hôm đó."""
        super().__init__()
        self.setObjectName("dayCell")
        self.setFrameShape(QFrame.StyledPanel)
        self._date_str = ""
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(2)
        head = QHBoxLayout()
        self.date_lbl = QLabel()
        self.add_btn = QPushButton("+")
        self.add_btn.setFixedSize(20, 20)
        self.add_btn.clicked.connect(lambda: self.add_requested.emit(self._date_str))
        head.addWidget(self.date_lbl, 1)
        head.addWidget(self.add_btn)
        lay.addLayout(head)
        self.list = QListWidget()
        self.list.setFrameShape(QFrame.NoFrame)
        # Transparent so the cell's today/weekend tint shows through the task area.
        self.list.setStyleSheet("background: transparent;")
        self.list.itemClicked.connect(self._on_item_clicked)
        lay.addWidget(self.list, 1)

    def set_day(self, d: date, tasks: List[dict], dim: bool,
                today: bool = False, weekend: bool = False) -> None:
        """Vẽ lại ô cho một ngày cụ thể.

        Chỉ "hôm nay" được nền tô đậm kèm viền nhấn; cuối tuần chỉ đổi nền chìm.
        Nhờ vậy mắt bắt vào hôm nay trước, còn khối cuối tuần chỉ hiện ra khi
        người dùng quét cả tháng. ``dim`` làm mờ ngày thuộc tháng khác.
        """
        self._date_str = d.isoformat()
        self.date_lbl.setText(str(d.day))
        p = current_palette()
        num_color = p.accent if today else (p.text_faint if dim else p.text)
        self.date_lbl.setStyleSheet(f"font-weight:600; color:{num_color};")
        # Today is the only cell that gets a filled surface + accent border;
        # weekends are set apart by a recessed surface alone, so the eye lands
        # on "today" first and on the weekend block only when scanning.
        r = p.radius
        if today:
            css = (f"#dayCell {{ background: {p.accent_soft}; "
                   f"border: 1px solid {p.accent}; border-radius: {r}px; }}")
        elif weekend:
            css = (f"#dayCell {{ background: {p.surface}; "
                   f"border: 1px solid {p.border}; border-radius: {r}px; }}")
        else:
            css = f"#dayCell {{ border: 1px solid {p.border}; border-radius: {r}px; }}"
        self.setStyleSheet(css)
        self.list.clear()
        for t in tasks:
            item = QListWidgetItem(t.get("title") or tr("schedtask.no_title"))
            item.setData(Qt.UserRole, t.get("task_id"))
            self.list.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """Bấm vào một task trong ô: phát id lên để lớp trên mở trình sửa."""
        tid = item.data(Qt.UserRole)
        if tid:
            self.task_clicked.emit(tid)


class CalendarView(QWidget):
    """Khung nhìn Lịch của màn Lịch trình: xem theo tuần, tháng hoặc năm.

    Widget này chỉ VẼ và phát tín hiệu; việc tạo/sửa task do vỏ
    ``ScheduleTaskTab`` làm, vì Kanban cũng cần đúng hành vi đó.
    """
    add_task_on_date = Signal(str)   # "YYYY-MM-DD"
    edit_task = Signal(str)          # task_id

    def __init__(self):
        """Lịch xem task theo tháng/tuần/ngày, neo vào hôm nay."""
        super().__init__()
        self.granularity = "month"
        self.anchor = date.today()
        self._tasks: List[dict] = []

        root = QVBoxLayout(self)
        head = QHBoxLayout()
        self.prev_btn = QPushButton()
        self.prev_btn.setIcon(icon("chevron-left"))
        self.prev_btn.clicked.connect(lambda: self._shift(-1))
        self.today_btn = QPushButton()
        self.today_btn.clicked.connect(self._go_today)
        self.next_btn = QPushButton()
        self.next_btn.setIcon(icon("chevron-right"))
        self.next_btn.clicked.connect(lambda: self._shift(1))
        self.period_lbl = QLabel()
        self.period_lbl.setStyleSheet("font-weight:700;")
        self.granularity_combo = QComboBox()
        for g in GRANULARITIES:
            self.granularity_combo.addItem("", g)
        self.granularity_combo.currentIndexChanged.connect(self._on_granularity_changed)
        head.addWidget(self.prev_btn)
        head.addWidget(self.today_btn)
        head.addWidget(self.next_btn)
        head.addWidget(self.period_lbl, 1)
        head.addWidget(self.granularity_combo)
        root.addLayout(head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setSpacing(4)
        scroll.setWidget(self._grid_host)
        root.addWidget(scroll, 1)

        on_language_changed(self._retranslate)
        self._retranslate()

    def _retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn rồi vẽ lại lưới."""
        self.today_btn.setText(tr("schedtask.cal_today"))
        self.prev_btn.setToolTip(tr("schedtask.cal_prev"))
        self.next_btn.setToolTip(tr("schedtask.cal_next"))
        for i, g in enumerate(GRANULARITIES):
            self.granularity_combo.setItemText(i, tr(f"schedtask.cal_gran.{g}"))
        self._render()

    # ---- public ------------------------------------------------------
    def set_tasks(self, tasks: List[dict]) -> None:
        """Nhận danh sách task mới và vẽ lại toàn bộ khung nhìn."""
        self._tasks = tasks
        self._render()

    def show_month(self, year: int, month: int) -> None:
        """Switch to Month view centered on (year, month) — used when the
        user drills down from a Year-view row."""
        self.anchor = date(year, month, 1)
        self.granularity = "month"
        idx = self.granularity_combo.findData("month")
        if idx >= 0:
            self.granularity_combo.blockSignals(True)
            self.granularity_combo.setCurrentIndex(idx)
            self.granularity_combo.blockSignals(False)
        self._render()

    # ---- navigation ---------------------------------------------------
    def _shift(self, direction: int) -> None:
        """Lùi/tiến một kỳ theo đúng độ mịn đang chọn (tuần, tháng hay năm)."""
        self.anchor = shift_period(self.anchor, self.granularity, direction)
        self._render()

    def _go_today(self) -> None:
        """Nhảy về kỳ chứa ngày hôm nay."""
        self.anchor = date.today()
        self._render()

    def _on_granularity_changed(self) -> None:
        """Đổi độ mịn tuần/tháng/năm và vẽ lại."""
        data = self.granularity_combo.currentData()
        if data:
            self.granularity = data
        self._render()

    # ---- rendering ------------------------------------------------------
    def _clear_grid(self) -> None:
        """Xoá sạch lưới trước khi vẽ lại.

        Dùng ``deleteLater`` chứ không bỏ tham chiếu: widget Qt còn đang trong
        hàng đợi sự kiện, xoá ngay có thể làm vỡ lúc đang xử lý sự kiện chuột.
        """
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _render(self) -> None:
        """Vẽ lại lưới theo độ mịn đang chọn: tuần, tháng (kèm ngày tràn) hoặc năm."""
        self._update_period_label()
        self._clear_grid()
        by_date = group_tasks_by_date(self._tasks)
        if self.granularity == "week":
            self._render_days(week_days(self.anchor), by_date)
        elif self.granularity == "year":
            self._render_year(by_date)
        else:
            self._render_days(sum(month_grid(self.anchor), []), by_date, mark_month=self.anchor.month)

    def _render_days(self, days: List[date], by_date: Dict[str, List[dict]],
                     mark_month: Optional[int] = None) -> None:
        """Vẽ lưới 7 cột: hàng đầu là tên thứ, các hàng sau là ô ngày.

        ``mark_month`` là tháng "chính": ngày thuộc tháng khác bị làm mờ. Cột 5 và
        6 là thứ Bảy và Chủ nhật vì ``_WEEKDAY_KEYS`` bắt đầu từ thứ Hai.
        """
        for col, key in enumerate(_WEEKDAY_KEYS):
            lbl = QLabel(tr(f"schedtask.cal_weekday.{key}"))
            lbl.setStyleSheet("font-weight:600;")
            lbl.setAlignment(Qt.AlignCenter)
            self._grid.addWidget(lbl, 0, col)
        today = date.today()
        rows = [days[i:i + 7] for i in range(0, len(days), 7)]
        for r, week in enumerate(rows, start=1):
            for c, d in enumerate(week):
                cell = _DayCell()
                dim = mark_month is not None and d.month != mark_month
                # _WEEKDAY_KEYS is Mon..Sun → columns 5 (Sat) and 6 (Sun) are the weekend.
                cell.set_day(d, by_date.get(d.isoformat(), []), dim,
                             today=(d == today), weekend=(c in (5, 6)))
                cell.add_requested.connect(self.add_task_on_date.emit)
                cell.task_clicked.connect(self.edit_task.emit)
                self._grid.addWidget(cell, r, c)

    def _render_year(self, by_date: Dict[str, List[dict]]) -> None:
        """Xem theo năm: danh sách 12 tháng kèm số task, bấm vào là mở tháng đó."""
        counts = month_task_counts(by_date, self.anchor.year)
        lst = QListWidget()
        for m in range(1, 13):
            label = date(self.anchor.year, m, 1).strftime("%B")
            n = counts[m]
            text = tr("schedtask.cal_month_count", month=label, n=n) if n else label
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, m)
            lst.addItem(item)
        lst.itemClicked.connect(lambda item: self.show_month(self.anchor.year, item.data(Qt.UserRole)))
        self._grid.addWidget(lst, 0, 0)

    def _update_period_label(self) -> None:
        """Cập nhật nhãn kỳ đang xem: khoảng ngày (tuần), năm, hoặc YYYY-MM (tháng)."""
        if self.granularity == "week":
            days = week_days(self.anchor)
            self.period_lbl.setText(f"{days[0].isoformat()} - {days[-1].isoformat()}")
        elif self.granularity == "year":
            self.period_lbl.setText(str(self.anchor.year))
        else:
            self.period_lbl.setText(self.anchor.strftime("%Y-%m"))


__all__ = ["CalendarView"]
