"""ScheduleTaskTab shell (R08-T11) — assembles
``kanban_board_widget.py::KanbanBoardWidget`` and
``calendar_view_widget.py::CalendarView`` behind the header/view-switch that
used to be inline in ``ui/schedule_task_tab.py`` (lines 81-245 of the
original 795-line file: header, view-tab wiring, lane-fit event filter moved
into the Kanban widget itself, the belt-and-braces 10s refresh timer).

Task EDITING (opening ``TaskEditorDialog``) lives HERE, not in either child
widget, because both need the exact same "open the editor for this task id"
behaviour — Kanban's double-click/edit-menu and Calendar's task click both
request it via a signal instead of each importing ``TaskEditorDialog``
themselves.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QSizePolicy, QStackedWidget,
    QTabBar, QVBoxLayout, QWidget,
)

from cowork_local.core.tasks import STATUSES, list_tasks, load_task, new_task, save_task
from cowork_local.i18n import on_language_changed, tr
from cowork_local.presentation.scheduling.calendar_view_widget import CalendarView
from cowork_local.presentation.scheduling.kanban_board_widget import KanbanBoardWidget
from cowork_local.state import AppContext
from cowork_local.ui.icons import icon

_VIEWS = ("kanban", "calendar")


class ScheduleTaskTab(QWidget):
    """Màn Lịch trình: phần vỏ ghép bảng Kanban và lịch tháng.

    Vỏ giữ ba việc mà cả hai khung nhìn đều cần: thanh tiêu đề, nút chuyển
    khung nhìn, và mở hộp thoại sửa task. Việc sửa task nằm ở đây (không ở
    từng widget con) vì Kanban lẫn Lịch đều cần đúng một hành vi "mở trình
    sửa cho task id này" — cả hai phát tín hiệu, vỏ mở hộp thoại.
    """
    status_message = Signal(str)

    def __init__(self, ctx: AppContext, scheduler=None, tasks_dir: Optional[Path] = None):
        """Vỏ màn Lịch task, ghép bảng Kanban và lịch.

        ``tasks_dir`` để None thì dùng thư mục mặc định. Cho phép truyền vào là điểm
        mới của R08-T11 — bản gộp cũ viết cứng, nên không test được nếu không đụng
        thư mục cấu hình thật của người dùng.
        """
        super().__init__()
        self.ctx = ctx
        self.scheduler = scheduler          # TaskScheduler (may be None in tests)
        # None -> the app's default TASKS_DIR (core/tasks.py). Overridable
        # (new in R08-T11; the original monolithic tab hardcoded None with no
        # way to point it at a tmp_path) so this shell is actually testable
        # without touching the user's real config folder — same shape
        # TaskScheduler.__init__ already accepts.
        self._tasks_dir: Optional[Path] = tasks_dir

        root = QVBoxLayout(self)

        # ---- header ----------------------------------------------------
        header = QHBoxLayout()
        self._title = QLabel()
        self._title.setStyleSheet("font-weight:700; font-size:15px;")
        self.counts_lbl = QLabel("")
        self.counts_lbl.setObjectName("hint")
        self.counts_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.counts_lbl.setMinimumWidth(0)
        self.add_btn = QPushButton()
        self.add_btn.setIcon(icon("plus"))
        self.add_btn.setObjectName("primary")
        self.add_btn.clicked.connect(self._add_task)
        self.ai_btn = QPushButton()
        self.ai_btn.setIcon(icon("sparkle"))
        self.ai_btn.clicked.connect(self._ai_create)
        # Two views of the same tasks, so they read as a pair of tabs rather
        # than a drop-list you have to open to discover the Calendar exists.
        self.view_tabs = QTabBar()
        self.view_tabs.setObjectName("viewTabs")
        self.view_tabs.setDrawBase(False)
        self.view_tabs.setExpanding(False)
        for _v in _VIEWS:
            self.view_tabs.addTab("")
        self.view_tabs.currentChanged.connect(self._on_view_changed)
        header.addWidget(self._title)
        header.addWidget(self.counts_lbl, 1)
        header.addWidget(self.view_tabs)
        header.addWidget(self.add_btn)
        header.addWidget(self.ai_btn)
        root.addLayout(header)

        # ---- board / calendar (two views of the SAME tasks) -----------------
        self._view_stack = QStackedWidget()
        self.kanban = KanbanBoardWidget(ctx, tasks_dir=self._tasks_dir, scheduler=scheduler)
        self.kanban.status_message.connect(self.status_message.emit)
        self.kanban.counts_changed.connect(self._on_counts_changed)
        self.kanban.edit_requested.connect(self._edit_task)
        self._view_stack.addWidget(self.kanban)
        self.calendar = CalendarView()
        self.calendar.edit_task.connect(self._edit_task)
        self.calendar.add_task_on_date.connect(self._add_task_on_date)
        self._view_stack.addWidget(self.calendar)
        root.addWidget(self._view_stack, 1)

        if self.scheduler is not None:
            self.scheduler.tasks_changed.connect(self.refresh)
            self.scheduler.task_started.connect(lambda _tid: self.refresh())
            self.scheduler.task_finished.connect(lambda _tid, _ok: self.refresh())

        # Belt-and-braces: also re-read the board every 10s so a card's lane
        # ALWAYS reflects reality (Scheduled → Running → Done) even if some
        # change slipped past the signals (e.g. task files edited externally).
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(10_000)
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start()

        self.refresh()
        on_language_changed(self._retranslate)

    # ---- i18n ------------------------------------------------------------
    def _retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn cho tiêu đề, nút và tên hai khung nhìn."""
        self._title.setText(tr("schedtask.title"))
        self.add_btn.setText(tr("schedtask.add_btn"))
        self.add_btn.setToolTip(tr("schedtask.add_tooltip"))
        self.ai_btn.setText(tr("schedtask.ai_btn"))
        self.ai_btn.setToolTip(tr("schedtask.ai_tooltip"))
        for i, v in enumerate(_VIEWS):
            self.view_tabs.setTabText(i, tr(f"schedtask.view.{v}"))
        self.kanban.retranslate()
        self.refresh()

    # ---- Kanban / Calendar view switch --------------------------------
    def _on_view_changed(self) -> None:
        """Đổi khung nhìn Kanban ⇄ Lịch theo tab đang chọn."""
        self._view_stack.setCurrentIndex(self.view_tabs.currentIndex())

    def _on_counts_changed(self, counts: dict) -> None:
        """Cập nhật dòng tóm tắt số task theo trạng thái.

        Chỉ liệt kê trạng thái có task; đặt luôn tooltip để khi thanh bị co hẹp
        người dùng vẫn đọc được đầy đủ.
        """
        summary = "   ".join(
            f"{tr(f'schedtask.status.{s}')}: {counts[s]}" for s in STATUSES if counts[s])
        self.counts_lbl.setText(summary)
        self.counts_lbl.setToolTip(summary)   # full text stays reachable if clipped

    def refresh(self) -> None:
        """Đọc lại toàn bộ task và vẽ lại cả Kanban lẫn Lịch."""
        all_tasks = self.kanban.refresh()
        self.calendar.set_tasks(all_tasks)

    # ---- task creation / editing (shared by Kanban + Calendar) -----------
    def _save_and_refresh(self, task: dict) -> None:
        """Ghi task xuống đĩa rồi vẽ lại màn hình."""
        save_task(task, self._tasks_dir)
        self.refresh()

    def _add_task(self) -> None:
        """Mở trình sửa để tạo task mới; chỉ lưu khi người dùng bấm xác nhận."""
        from cowork_local.ui.task_editor_dialog import TaskEditorDialog

        dlg = TaskEditorDialog(None, list_tasks(self._tasks_dir), self, ctx=self.ctx)
        if dlg.exec() and dlg.edited_task:
            self._save_and_refresh(dlg.edited_task)
            self.status_message.emit(tr("schedtask.msg_created"))

    def _edit_task(self, task_id: str) -> None:
        """Mở trình sửa cho một task đã có. Không tìm thấy id thì bỏ qua lặng lẽ
        (task có thể vừa bị xoá ở khung nhìn khác).
        """
        from cowork_local.ui.task_editor_dialog import TaskEditorDialog

        task = load_task(task_id, self._tasks_dir)
        if not task:
            return
        dlg = TaskEditorDialog(task, list_tasks(self._tasks_dir), self, ctx=self.ctx)
        if dlg.exec() and dlg.edited_task:
            self._save_and_refresh(dlg.edited_task)

    def _add_task_on_date(self, date_str: str) -> None:
        """Create a task pre-filled with the clicked calendar date (default
        09:00) — same editor Add Task opens, nothing is saved until confirmed."""
        from cowork_local.ui.task_editor_dialog import TaskEditorDialog

        t = new_task("", schedule={"enabled": True, "run_at": f"{date_str} 09:00"})
        dlg = TaskEditorDialog(t, list_tasks(self._tasks_dir), self, ctx=self.ctx)
        if dlg.exec() and dlg.edited_task:
            self._save_and_refresh(dlg.edited_task)
            self.status_message.emit(tr("schedtask.msg_created"))

    # ---- AI create ----------------------------------------------------------
    def _ai_create(self) -> None:
        """Mở hộp thoại nhờ AI lập kế hoạch, rồi lưu toàn bộ task nó sinh ra."""
        from cowork_local.presentation.scheduling.ai_task_creator_dialog import (
            AiTaskCreatorDialog,
        )

        dlg = AiTaskCreatorDialog(self.ctx, self)
        if dlg.exec() and dlg.created_tasks:
            for t in dlg.created_tasks:
                save_task(t, self._tasks_dir)
            self.refresh()
            self.status_message.emit(tr("schedtask.msg_ai_created", n=len(dlg.created_tasks)))


__all__ = ["ScheduleTaskTab"]
