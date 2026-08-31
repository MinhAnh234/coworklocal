"""Kanban board for Schedule Task (R08-T11, extracted from
``ui/schedule_task_tab.py``'s ``ScheduleTaskTab`` — Kanban rendering +
drag-drop + row actions, lines 41-79/222-300/302-484/496-548 of the original
795-line file).

Owns the 7-lane board itself. What used to be plain module-function calls
into ``core/tasks.py`` (``duplicate_task``, ``taskrepo.save_task``,
``taskrepo.delete_task``, ...) and ``self.scheduler.run_now(...)`` inline are
now calls into
``application/scheduling/task_application_service.py::TaskApplicationService``
(R07-T04) — the drag-drop business rules (dropping on Running/Done/Scheduled)
in particular used to be ~30 lines of if/elif inside a Qt slot; now it's
``TaskApplicationService.move_to_status`` plus a few branches on its result.

Task EDITING (opening ``TaskEditorDialog``) is deliberately NOT owned here —
``CalendarView`` needs the exact same "open the editor for this task id"
behaviour for its own click handler, so it stays a shell-level concern
(``schedule_task_tab.py``) both widgets request via a signal, instead of
being duplicated in two places.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMenu, QMessageBox, QScrollArea, QVBoxLayout, QWidget,
)

from cowork_local.application.scheduling.task_application_service import (
    TaskApplicationService,
)
from cowork_local.core.tasks import STATUSES, chain_error, new_task
from cowork_local.i18n import tr
from cowork_local.infrastructure.persistence.json.task_repository_impl import (
    TaskRepository,
)
from cowork_local.presentation.scheduling.run_history_dialog import RunHistoryDialog
from cowork_local.theme import current_palette
from cowork_local.ui.osutil import open_path

# Priority shown as a plain text tag (no colored-emoji squares). Only the
# elevated priorities get a visible marker; low/medium stay unmarked as before.
_PRIORITY_ICONS = {"low": "", "medium": "", "high": "· high", "critical": "· critical"}


class _KanbanColumn(QListWidget):
    """One status lane. Accepts drops from sibling columns; a drop means
    'move this task to my status'."""

    task_dropped = Signal(str, str)   # task_id, new_status

    def __init__(self, status: str):
        """Một cột Kanban ứng với một trạng thái task.

        Cho chọn nhiều thẻ trong CÙNG một cột (Shift/Ctrl) để chuột phải xoá hàng
        loạt, thay vì xoá từng cái.
        """
        super().__init__()
        self.status = status
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        # Shift/Ctrl-click several cards in the SAME column, then right-click
        # → "Delete N selected" to bulk-remove tasks instead of one at a time.
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setWordWrap(True)
        # Cards wrap, so there is never anything to reach by scrolling
        # sideways — but QListWidget's own column hint runs 1-6px past the
        # viewport; the board divides whatever width it has by seven instead
        # (see KanbanBoardWidget._fit_lanes()).
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setResizeMode(QListWidget.Adjust)   # re-wrap on every resize

    def dropEvent(self, event):  # noqa: N802
        """Thả một thẻ từ lane khác sang: báo lên bảng để đổi trạng thái task."""
        source = event.source()
        if isinstance(source, _KanbanColumn) and source is not self:
            item = source.currentItem()
            tid = item.data(Qt.UserRole) if item else None
            if tid:
                event.acceptProposedAction()
                self.task_dropped.emit(tid, self.status)
                return
        event.ignore()


class KanbanBoardWidget(QWidget):
    """The 7-lane board: Backlog / Scheduled / Running / Waiting Input /
    Done / Failed / Paused. Cards drag between columns (dropping = changing
    status via ``TaskApplicationService.move_to_status``), double-click and
    the right-click menu request an edit via :attr:`edit_requested`.

    Args:
        ctx: ``AppContext`` — passed through to ``TaskEditorDialog`` callers
            need it for, kept here only so callers don't have to fetch it
            separately.
        tasks_dir: ``None`` -> the app's default task-storage directory;
            tests pass a ``tmp_path``.
        scheduler: ``TaskScheduler`` (may be ``None`` — matches the original
            widget's "no scheduler in tests" tolerance) used as the
            ``run_now`` dispatch source for the service.
        service: inject a ready-made ``TaskApplicationService`` (tests); when
            ``None``, one is built from ``tasks_dir``/``scheduler``.
    """

    status_message = Signal(str)
    counts_changed = Signal(dict)     # status -> count, for the shell's summary label
    edit_requested = Signal(str)      # task_id — shell opens TaskEditorDialog

    _LANE_FLOOR_CH = 8   # roughly eight characters of a task title, plus padding

    def __init__(self, ctx, tasks_dir=None, scheduler=None,
                 service: Optional[TaskApplicationService] = None, parent=None):
        """Bảng Kanban các task.

        ``service`` để None thì tự dựng một cái từ kho task; ``scheduler`` để None
        thì bảng chỉ đọc/ghi task chứ không chạy được cái nào.
        """
        super().__init__(parent)
        self.ctx = ctx
        self._tasks_dir = tasks_dir
        self._repo = TaskRepository(tasks_dir)
        self._service = service or TaskApplicationService(
            self._repo, run_now=scheduler.run_now if scheduler is not None else None)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        board = QWidget()
        scroll.setWidget(board)
        cols = QHBoxLayout(board)
        cols.setSpacing(2)
        self.columns: Dict[str, _KanbanColumn] = {}
        self.column_headers: Dict[str, QLabel] = {}
        for status in STATUSES:
            box = QVBoxLayout()
            box.setContentsMargins(0, 0, 0, 0)
            box.setSpacing(2)
            head = QLabel()
            head.setStyleSheet("font-weight:600;")
            col = _KanbanColumn(status)
            col.setObjectName("kanbanLane")
            col.task_dropped.connect(self._on_task_dropped)
            col.itemDoubleClicked.connect(self._on_double_click)
            col.setContextMenuPolicy(Qt.CustomContextMenu)
            col.customContextMenuRequested.connect(
                lambda pos, c=col: self._context_menu(c, pos))
            box.addWidget(head)
            box.addWidget(col, 1)
            holder = QWidget()
            holder.setLayout(box)
            cols.addWidget(holder)
            self.columns[status] = col
            self.column_headers[status] = head
        root.addWidget(scroll, 1)
        self._board_scroll = scroll
        scroll.viewport().installEventFilter(self)

    def retranslate(self) -> None:
        """Áp lại tooltip của từng lane theo ngôn ngữ đang chọn."""
        for status, col in self.columns.items():
            col.setToolTip(tr(f"schedtask.col_tip.{status}"))

    # ---- lane widths ------------------------------------------------------
    def eventFilter(self, obj, event):  # noqa: N802
        """Vùng cuộn đổi kích thước thì chia lại bề rộng cho 7 lane."""
        if obj is self._board_scroll.viewport() and event.type() == QEvent.Resize:
            self._fit_lanes()
        return super().eventFilter(obj, event)

    def _fit_lanes(self) -> None:
        """Chia bề rộng cho 7 lane sao cho tất cả vừa một màn.

        Có sàn tối thiểu tính theo bề rộng ký tự, để tiêu đề lane không bị cắt cụt
        khi cửa sổ hẹp.
        """
        floor = self.fontMetrics().averageCharWidth() * self._LANE_FLOOR_CH + 24
        for col in self.columns.values():
            if col.minimumWidth() != floor:
                col.setMinimumWidth(floor)

    # ---- rendering ----------------------------------------------------------
    def _card_text(self, t: dict) -> str:
        """Chuỗi hiển thị trên một thẻ task: tiêu đề kèm mốc thời gian/độ ưu tiên."""
        prio = _PRIORITY_ICONS.get(t.get("priority", "medium"), "")
        ai = "[AI] " if t.get("is_ai_generated") else ""
        sched = t.get("schedule", {})
        when = sched.get("run_at") if sched.get("enabled") else None
        when_line = when or tr("schedtask.no_schedule")
        chain = ""
        if t.get("dependency", {}).get("next_task_id") or t.get("dependency", {}).get("previous_task_id"):
            chain = " (linked)"
        last = t.get("logs", {}).get("last_status")
        last_line = {"success": tr("schedtask.last_success"),
                     "failed": tr("schedtask.last_failed")}.get(last, tr("schedtask.last_never"))
        return (f"{ai}{t.get('title', '')}{chain}\n"
                f"{when_line}   {prio}\n{last_line}")

    def refresh(self) -> List[dict]:
        """Re-render every lane from disk. Returns the full task list so the
        shell can hand the same read to ``CalendarView.set_tasks`` without a
        second ``list_tasks`` call."""
        all_tasks = self._repo.list()
        counts = {s: 0 for s in STATUSES}
        for col in self.columns.values():
            col.clear()
        for t in all_tasks:
            status = t.get("status", "backlog")
            if status not in self.columns:
                continue
            counts[status] += 1
            item = QListWidgetItem(self._card_text(t))
            item.setData(Qt.UserRole, t["task_id"])
            self.columns[status].addItem(item)
        pal = current_palette()
        for status, col in self.columns.items():
            self.column_headers[status].setText(
                f"{tr(f'schedtask.status.{status}')} ({counts[status]})")
            # Dropping a card into Running STARTS the task for real, so that
            # lane is outlined while it holds anything.
            if status == "running" and counts[status]:
                col.setStyleSheet(
                    f"border: 1px solid {pal.warning}; border-radius: {pal.radius}px;")
                self.column_headers[status].setStyleSheet(
                    f"font-weight:600; color: {pal.warning};")
            else:
                col.setStyleSheet("")
                self.column_headers[status].setStyleSheet("font-weight:600;")
            if col.count() == 0:
                empty = QListWidgetItem(tr("schedtask.no_tasks"))
                empty.setFlags(Qt.NoItemFlags)
                col.addItem(empty)
        self.counts_changed.emit(counts)
        return all_tasks

    # ---- actions --------------------------------------------------------
    def _on_double_click(self, item: QListWidgetItem) -> None:
        """Bấm đúp một thẻ: mở trình sửa task đó."""
        tid = item.data(Qt.UserRole)
        if tid:
            self.edit_requested.emit(tid)

    def _on_task_dropped(self, task_id: str, new_status: str) -> None:
        """Dropping a card ACTS on the task via ``TaskApplicationService.
        move_to_status`` — see that method's docstring for the exact rules."""
        result = self._service.move_to_status(task_id, new_status)
        if result is None:
            self.refresh()
            return
        if result.blocked:
            self.refresh()   # can't drag a running task
            return
        if result.ran_now:
            self._emit_run_now_message(result.run_now_result,
                                       (result.task or {}).get("title", ""))
            self.refresh()
            return
        self.refresh()
        if result.needs_schedule:
            # No time set yet — a silently-disabled "Scheduled" card would
            # never run and look broken. Open the editor right away.
            self.status_message.emit(tr("schedtask.msg_set_schedule"))
            self.edit_requested.emit(task_id)

    @staticmethod
    def _is_multi_selection(item, selected) -> bool:
        """True when the right-clicked card is part of an existing multi-item
        selection — pure boolean, kept separate from _context_menu so it's
        testable without ever invoking Qt's (modal, event-loop-blocking) menu."""
        return len(selected) > 1 and item in selected

    def _context_menu(self, col: _KanbanColumn, pos) -> None:
        """Menu chuột phải trên một thẻ: chạy ngay, xem log, tạo task tiếp theo, xoá.

        Đang chọn nhiều thẻ thì chuyển sang menu xoá hàng loạt.
        """
        item = col.itemAt(pos)
        if item is None or not item.data(Qt.UserRole):
            return
        selected = [it for it in col.selectedItems() if it.data(Qt.UserRole)]
        if self._is_multi_selection(item, selected):
            self._bulk_delete_menu(col, pos, selected)
            return
        tid = item.data(Qt.UserRole)
        task = self._repo.get(tid)
        if not task:
            return
        menu = QMenu(col)
        run_act = menu.addAction(tr("schedtask.menu_run"))
        edit_act = menu.addAction(tr("schedtask.menu_edit"))
        dup_act = menu.addAction(tr("schedtask.menu_duplicate"))
        paused = task.get("status") == "paused"
        pause_act = menu.addAction(tr("schedtask.menu_resume" if paused else "schedtask.menu_pause"))
        logs_act = menu.addAction(tr("schedtask.menu_logs"))
        hist_act = menu.addAction(tr("schedtask.menu_history"))
        next_act = menu.addAction(tr("schedtask.menu_create_next"))
        menu.addSeparator()
        del_act = menu.addAction(tr("schedtask.menu_delete"))
        chosen = menu.exec(col.viewport().mapToGlobal(pos))
        if chosen == run_act:
            self._emit_run_now_message(self._service.run_now(tid), task.get("title", ""))
            self.refresh()
        elif chosen == edit_act:
            self.edit_requested.emit(tid)
        elif chosen == dup_act:
            self._service.duplicate(tid)
            self.refresh()
        elif chosen == pause_act:
            self._service.toggle_pause(tid)
            self.refresh()
        elif chosen == logs_act:
            self._view_logs(task)
        elif chosen == hist_act:
            RunHistoryDialog(task, self).exec()
        elif chosen == next_act:
            self._create_next_from_output(task)
        elif chosen == del_act:
            if QMessageBox.question(self, tr("schedtask.menu_delete"),
                                    tr("schedtask.delete_confirm", title=task.get("title", ""))
                                    ) == QMessageBox.Yes:
                self._service.delete(tid)
                self.refresh()

    def _bulk_delete_menu(self, col: _KanbanColumn, pos, selected) -> None:
        """Menu xoá hàng loạt khi đang chọn nhiều thẻ."""
        menu = QMenu(col)
        del_act = menu.addAction(tr("schedtask.menu_delete_selected", n=len(selected)))
        chosen = menu.exec(col.viewport().mapToGlobal(pos))
        if chosen == del_act:
            self._confirm_and_delete_selected(selected)

    def _confirm_and_delete_selected(self, selected) -> bool:
        """Confirm, then delete every task in ``selected``. Split out of
        _bulk_delete_menu so tests can drive it directly without having to
        fake a real (modal, event-loop-blocking) QMenu popup."""
        if QMessageBox.question(
                self, tr("schedtask.menu_delete"),
                tr("schedtask.delete_multi_confirm", n=len(selected))) != QMessageBox.Yes:
            return False
        ids = [it.data(Qt.UserRole) for it in selected if it.data(Qt.UserRole)]
        self._service.bulk_delete(ids)
        self.refresh()
        return True

    def _emit_run_now_message(self, result, title: str = "") -> None:
        """Báo kết quả của lệnh "chạy ngay" ra thanh trạng thái."""
        if result is None:
            return
        if result.ok:
            self.status_message.emit(tr("schedtask.msg_running", title=title))
        elif result.reason == "manual_task":
            self.status_message.emit(tr("schedtask.msg_manual_norun"))
        elif result.reason == "no_scheduler":
            self.status_message.emit(tr("schedtask.msg_no_scheduler"))

    def _view_logs(self, task: dict) -> None:
        """Mở thư mục hiện vật chứa log của các lượt chạy task này."""
        from cowork_local.core.tasks import ARTIFACTS_DIR

        run_id = task.get("logs", {}).get("last_run_id")
        if not run_id:
            QMessageBox.information(self, tr("schedtask.menu_logs"), tr("schedtask.no_runs_yet"))
            return
        folder = ARTIFACTS_DIR / task["task_id"] / run_id
        if folder.exists():
            open_path(str(folder))
        else:
            QMessageBox.information(self, tr("schedtask.menu_logs"), tr("schedtask.no_runs_yet"))

    def _create_next_from_output(self, task: dict) -> None:
        """Scaffold a follow-up task pre-wired to consume this task's output.
        Chain-cycle validation (``chain_error``) is core/tasks.py domain
        logic already, not duplicated here — only the save + edit-request
        wiring is this widget's job."""
        nxt = new_task(tr("schedtask.next_of", title=task.get("title", "")))
        nxt["task_type"] = "cowork"
        nxt["input"]["mode"] = "previous_task_output"
        nxt["input"]["previous_task_id"] = task["task_id"]
        nxt["dependency"]["previous_task_id"] = task["task_id"]
        err = chain_error(self._repo.list() + [nxt], task["task_id"], nxt["task_id"])
        if err:
            QMessageBox.warning(self, tr("schedtask.g_dependency"), err)
            return
        self._repo.save(nxt)
        task["dependency"]["next_task_id"] = nxt["task_id"]
        task["dependency"]["pass_output_to_next"] = True
        if task["dependency"].get("run_next_mode", "none") == "none":
            task["dependency"]["run_next_mode"] = "run_after_success"
        self._repo.save(task)
        self.refresh()
        self.edit_requested.emit(nxt["task_id"])


__all__ = ["KanbanBoardWidget"]
