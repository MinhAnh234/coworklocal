"""RunHistoryDialog — one task's run history as a table (R08-T11, split out
of ``kanban_board_widget.py`` to keep that file under the 400-line cap;
originally ``ui/schedule_task_tab.py::_RunHistoryDialog``, lines 496-548)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QDialogButtonBox, QLabel, QTableWidget,
    QTableWidgetItem, QVBoxLayout,
)

from cowork_local.i18n import tr
from cowork_local.ui.dialog_buttons import dialog_buttons
from cowork_local.ui.osutil import open_path


class RunHistoryDialog(QDialog):
    """Run history of one task as a table (newest first): time, status, error;
    double-click a row to open that run's artifact folder."""

    def __init__(self, task: dict, parent=None):
        """Hộp thoại xem lịch sử các lần chạy của một task."""
        super().__init__(parent)
        self._task = task
        self.setWindowTitle(f"{tr('schedtask.menu_history')} — {task.get('title', '')}")
        self.resize(620, 380)
        root = QVBoxLayout(self)
        hint = QLabel(tr("schedtask.hist_hint"))
        hint.setObjectName("hint")
        root.addWidget(hint)

        runs = list(reversed(task.get("runs", []) or []))
        self.table = QTableWidget(len(runs), 4)
        self.table.setHorizontalHeaderLabels([
            tr("schedtask.hist_col_time"), tr("schedtask.hist_col_status"),
            tr("schedtask.hist_col_run"), tr("schedtask.hist_col_error"),
        ])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        for row, run in enumerate(runs):
            cells = (
                run.get("finished_at", ""),
                str(run.get("status", "")),
                run.get("run_id", ""),
                (run.get("error") or "")[:200],
            )
            for col, text in enumerate(cells):
                item = QTableWidgetItem(str(text))
                if col == 0:
                    item.setData(Qt.UserRole, run.get("run_id", ""))
                self.table.setItem(row, col, item)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemDoubleClicked.connect(self._open_artifact)
        root.addWidget(self.table, 1)

        buttons = dialog_buttons(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)

    def _open_artifact(self, item: QTableWidgetItem) -> None:
        """Bấm một dòng: mở thư mục hiện vật của lượt chạy đó."""
        from cowork_local.core.tasks import ARTIFACTS_DIR

        first = self.table.item(item.row(), 0)
        run_id = first.data(Qt.UserRole) if first else ""
        if not run_id:
            return
        folder = ARTIFACTS_DIR / self._task["task_id"] / run_id
        if folder.exists():
            open_path(str(folder))


__all__ = ["RunHistoryDialog"]
