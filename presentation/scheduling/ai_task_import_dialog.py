"""Import-from-file tab content for AI Create Task (R08-T11, extracted from
``ui/schedule_task_tab.py``'s ``_AiCreateDialog`` — the Import tab + its
``_DropZone``, lines 551-576/643-665/674-720 of the original file).

:class:`ImportTaskPanel` is a plain ``QWidget`` (not its own dialog) so
``ai_task_creator_dialog.py`` can embed it as one tab of the single AI-create
dialog the user sees — the two files are a code split, not a UX split; there
is still one dialog with two tabs, exactly as before.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QPushButton,
    QVBoxLayout, QWidget,
)

from cowork_local.application.scheduling.ai_task_planner_service import (
    AiTaskPlannerService,
)
from cowork_local.i18n import tr
from cowork_local.theme import current_palette
from cowork_local.ui.icons import icon
from cowork_local.ui.osutil import open_path


class _DropZone(QLabel):
    """Drag-an-.xlsx-here area for the Import tab."""

    file_dropped = Signal(str)

    def __init__(self):
        """Vùng kéo–thả tệp danh sách task."""
        super().__init__()
        from PySide6.QtCore import Qt

        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(70)
        _p = current_palette()
        self.setStyleSheet(
            f"QLabel {{ border: 1px dashed {_p.border_strong};"
            f" border-radius: {_p.radius_lg}px;"
            f" color: {_p.text_muted}; padding: 10px; }}")
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):  # noqa: N802
        """Chỉ nhận tệp có đuôi hợp lệ."""
        urls = event.mimeData().urls()
        if urls and urls[0].toLocalFile().lower().endswith(
                (".xlsx", ".xlsm", ".xls", ".csv", ".json")):
            event.acceptProposedAction()

    def dropEvent(self, event):  # noqa: N802
        """Thả tệp: phát đường dẫn lên để panel đọc và dựng danh sách task."""
        urls = event.mimeData().urls()
        if urls:
            self.file_dropped.emit(urls[0].toLocalFile())


class ImportTaskPanel(QWidget):
    """Pick/drag an Excel/CSV/JSON file, preview the tasks it maps to, and
    hold that NOT-yet-saved list — the dialog reads :attr:`planned` when the
    user confirms.

    Args:
        planner: an ``AiTaskPlannerService`` — ``import_file`` is called
            through it (R07-T05) rather than ``core.task_import`` directly.
    """

    tasks_changed = Signal(bool)   # True when the current preview has >=1 valid task

    def __init__(self, planner: AiTaskPlannerService, parent=None):
        """Panel nhập task từ tệp: xuất mẫu, chọn tệp, xem trước rồi mới tạo."""
        super().__init__(parent)
        self._planner = planner
        self.planned: List[dict] = []

        il = QVBoxLayout(self)
        tpl_btn = QPushButton(tr("schedtask.export_template_btn"))
        tpl_btn.setIcon(icon("upload"))
        tpl_btn.clicked.connect(self._export_template)
        il.addWidget(tpl_btn)
        pick_row = QHBoxLayout()
        pick_btn = QPushButton(tr("schedtask.import_pick_btn"))
        pick_btn.setIcon(icon("folder"))
        pick_btn.clicked.connect(self._pick_import_file)
        pick_row.addWidget(pick_btn)
        pick_row.addStretch(1)
        il.addLayout(pick_row)
        self.drop_zone = _DropZone()
        self.drop_zone.setText(tr("schedtask.drop_hint"))
        self.drop_zone.file_dropped.connect(self._load_import_file)
        il.addWidget(self.drop_zone)
        il.addWidget(QLabel(tr("schedtask.ai_preview_label")))
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        il.addWidget(self.preview, 1)

    def _export_template(self) -> None:
        """Xuất file mẫu Excel để người dùng điền danh sách task rồi nhập lại."""
        from PySide6.QtWidgets import QFileDialog

        from cowork_local.core.task_excel import export_template

        path, _ = QFileDialog.getSaveFileName(
            self, tr("schedtask.export_template_btn"),
            "cowork_tasks_template.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        try:
            export_template(path)
            open_path(str(Path(path).parent))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, tr("schedtask.tab_import"), str(exc))

    def _pick_import_file(self) -> None:
        """Chọn file danh sách task để nhập."""
        from PySide6.QtWidgets import QFileDialog

        from cowork_local.core.task_import import IMPORT_FILTER

        path, _ = QFileDialog.getOpenFileName(
            self, tr("schedtask.import_pick_btn"), "", IMPORT_FILTER)
        if path:
            self._load_import_file(path)

    def _load_import_file(self, path: str) -> None:
        """Đọc file và dựng danh sách task xem trước; file sai khuôn thì hiện lý do cụ
        thể chứ không im lặng bỏ qua.
        """
        try:
            self.planned = self._planner.import_file(path)
        except ValueError as exc:
            # Same as the original single-class dialog: a bad file leaves
            # whatever was previously loaded in `planned` untouched (only the
            # preview text and the Ok button reflect the failure) rather than
            # discarding a prior successful load.
            self.preview.setPlainText(str(exc))
            self.tasks_changed.emit(False)
            return
        by_id = {t["task_id"]: t["title"] for t in self.planned}
        lines = []
        for i, t in enumerate(self.planned, 1):
            sched = t.get("schedule", {})
            when = sched.get("run_at") if sched.get("enabled") else tr("schedtask.no_schedule")
            deps = t.get("dependency", {}).get("depends_on") or []
            dep_note = ("  ← depends: " + ", ".join(by_id.get(d, "?") for d in deps)) if deps else ""
            lines.append(f"{i}. [{t.get('task_type')}] {t.get('title')}\n"
                         f"    {when}   repeat={sched.get('repeat_type', 'none')}{dep_note}")
        self.preview.setPlainText("\n\n".join(lines))
        self.tasks_changed.emit(bool(self.planned))


__all__ = ["ImportTaskPanel"]
