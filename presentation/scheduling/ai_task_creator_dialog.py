"""AiTaskCreatorDialog — "AI Create Task" (R08-T11, extracted from
``ui/schedule_task_tab.py``'s ``_AiCreateDialog``, lines 579-641/722-794 of
the original 795-line file).

Still one dialog with two tabs (AI-gen, then Import — the latter is
:class:`~presentation.scheduling.ai_task_import_dialog.ImportTaskPanel`,
embedded here rather than duplicated): the physical file split matches
``docs/refactor/Feature_Architecture_Proposal.md``'s R08-T11 breakdown, the
user-visible dialog is unchanged. ``_confirm`` still uses "whichever tab
produced a task list most recently" (mirroring the original class's shared
``self._planned`` attribute) — the AI-gen tab sets it on completion, the
Import tab reports it through :attr:`ImportTaskPanel.tasks_changed`.

AI generation goes through
``application/scheduling/ai_task_planner_service.py::AiTaskPlannerService``
(R07-T05) instead of ``core.ai_task_planner.plan_tasks`` directly.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from cowork_local.application.scheduling.ai_task_planner_service import (
    AiTaskPlannerService,
)
from cowork_local.core.projects import list_projects
from cowork_local.core.worker import AgentWorker
from cowork_local.i18n import tr
from cowork_local.presentation.scheduling.ai_task_import_dialog import ImportTaskPanel
from cowork_local.state import AppContext
from cowork_local.ui.dialog_buttons import dialog_buttons
from cowork_local.ui.icons import icon


class AiTaskCreatorDialog(QDialog):
    """Create tasks two ways, one tab each (both preview first — nothing is
    saved until the user confirms): ✨ AI gen from a natural-language
    description, or 📥 Import from a filled Excel/CSV/JSON file."""

    def __init__(self, ctx: AppContext, parent=None):
        """Hộp thoại tạo task bằng AI hoặc nhập từ tệp.

        Nhớ tab nào đang cấp danh sách task cho nút Đồng ý — hai tab cùng sinh ra
        danh sách, không phân biệt thì bấm Đồng ý có thể tạo nhầm danh sách của tab
        kia.
        """
        super().__init__(parent)
        self.ctx = ctx
        self._planner = AiTaskPlannerService(provider_factory=ctx.build_active_provider)
        self.created_tasks: List[dict] = []
        self._ai_planned: List[dict] = []
        # Which tab produced the task list currently backing the Ok button —
        # mirrors the original single-class dialog's shared `self._planned`
        # attribute, where whichever of _on_planned()/_load_import_file()
        # ran LAST (regardless of which tab is currently showing) won.
        self._active_source = "ai"
        self._worker: Optional[AgentWorker] = None
        self.setWindowTitle(tr("schedtask.ai_btn"))
        self.resize(600, 520)

        root = QVBoxLayout(self)
        ws_row = QHBoxLayout()
        ws_row.addWidget(QLabel(tr("schedtask.f_workspace")))
        self.workspace_combo = QComboBox()
        self.workspace_combo.addItem(tr("schedtask.no_workspace"), "")
        for p in list_projects():
            self.workspace_combo.addItem(p.name, p.project_id)
        self.workspace_combo.setToolTip(tr("schedtask.hint_workspace"))
        ws_row.addWidget(self.workspace_combo, 1)
        root.addLayout(ws_row)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self.tabs.addTab(self._build_ai_gen_page(), tr("schedtask.tab_ai"))
        self.import_panel = ImportTaskPanel(self._planner)
        self.import_panel.tasks_changed.connect(self._on_import_tasks_changed)
        self.tabs.addTab(self.import_panel, tr("schedtask.tab_import"))

        self.buttons = dialog_buttons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                                      ok="schedtask.ai_confirm")
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)
        self.buttons.accepted.connect(self._confirm)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

    # ---- AI-gen tab -------------------------------------------------------
    def _build_ai_gen_page(self) -> QWidget:
        """Dựng tab "Sinh bằng AI": ô mô tả, tệp/link đính kèm và nút sinh."""
        ai_page = QWidget()
        al = QVBoxLayout(ai_page)
        al.addWidget(QLabel(tr("schedtask.ai_desc_label")))
        self.desc_edit = QPlainTextEdit()
        self.desc_edit.setPlaceholderText(tr("schedtask.ai_desc_ph"))
        self.desc_edit.setMaximumHeight(110)
        al.addWidget(self.desc_edit)
        # Attachments (files + links) — merged into every task this generates,
        # AND into the planning prompt so the AI knows they exist.
        attach_row = QHBoxLayout()
        self.ai_files_edit = QLineEdit()
        self.ai_files_edit.setPlaceholderText(tr("schedtask.files_placeholder"))
        ai_pick_btn = QPushButton(tr("schedtask.pick_files"))
        ai_pick_btn.setIcon(icon("folder"))
        ai_pick_btn.clicked.connect(self._ai_pick_files)
        attach_row.addWidget(self.ai_files_edit, 1)
        attach_row.addWidget(ai_pick_btn)
        al.addWidget(QLabel(tr("schedtask.f_files")))
        al.addLayout(attach_row)
        self.ai_links_edit = QLineEdit()
        self.ai_links_edit.setPlaceholderText(tr("schedtask.links_placeholder"))
        al.addWidget(QLabel(tr("schedtask.f_links")))
        al.addWidget(self.ai_links_edit)
        self.gen_btn = QPushButton(tr("schedtask.ai_generate"))
        self.gen_btn.setIcon(icon("sparkle"))
        self.gen_btn.setObjectName("primary")
        self.gen_btn.clicked.connect(self._generate)
        al.addWidget(self.gen_btn)
        al.addWidget(QLabel(tr("schedtask.ai_preview_label")))
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        al.addWidget(self.preview, 1)
        return ai_page

    def _ai_pick_files(self) -> None:
        """Chọn tệp đính kèm làm ngữ cảnh cho AI lập kế hoạch."""
        from PySide6.QtWidgets import QFileDialog

        files, _ = QFileDialog.getOpenFileNames(self, tr("schedtask.pick_files"))
        if files:
            existing = [f for f in self.ai_files_edit.text().split(";") if f.strip()]
            self.ai_files_edit.setText("; ".join(existing + files))

    def _attached_files(self) -> List[str]:
        """Danh sách đường dẫn tệp đã nhập, tách theo dấu ``;``."""
        return [p.strip() for p in self.ai_files_edit.text().split(";") if p.strip()]

    def _attached_links(self) -> List[str]:
        """Danh sách link đã nhập, tách theo dấu ``;``."""
        return [u.strip() for u in self.ai_links_edit.text().split(";") if u.strip()]

    def _generate(self) -> None:
        """Nhờ AI tách mô tả thành nhiều task; đang chạy dở thì bỏ qua."""
        description = self.desc_edit.toPlainText().strip()
        if not description or self._worker is not None:
            return
        files, links = self._attached_files(), self._attached_links()
        self.gen_btn.setEnabled(False)
        self.gen_btn.setText(tr("schedtask.ai_generating"))

        def job(worker: AgentWorker):
            """Chạy nền: ghép mô tả với danh sách tệp/link rồi gọi bộ lập kế hoạch."""
            full_desc = description
            if files or links:
                attach_note = "; ".join(files + links)
                full_desc += f"\n\n(Attached references available: {attach_note})"
            planned = self._planner.plan(
                full_desc, file_paths=files, links=links, cancel=worker.is_cancelled)
            return {"tasks": planned}

        w = AgentWorker(job)
        w.finished_ok.connect(self._on_planned)
        w.failed.connect(self._on_failed)
        self._worker = w
        w.start()

    def _on_planned(self, result: dict) -> None:
        """Có kết quả: đổ danh sách task đề xuất ra bảng để người dùng xem lại."""
        self._worker = None
        self.gen_btn.setEnabled(True)
        self.gen_btn.setText(tr("schedtask.ai_generate"))
        self._ai_planned = result.get("tasks") or []
        self._active_source = "ai"
        lines = []
        for i, t in enumerate(self._ai_planned, 1):
            sched = t.get("schedule", {})
            when = sched.get("run_at") if sched.get("enabled") else tr("schedtask.no_schedule")
            dep = t.get("dependency", {})
            chain = f"  ← {dep.get('previous_task_id', '')[:8]}" if dep.get("previous_task_id") else ""
            lines.append(f"{i}. [{t.get('task_type')}] {t.get('title')}\n"
                         f"    {when}   repeat={sched.get('repeat_type', 'none')}{chain}\n"
                         f"    {t.get('description', '')[:150]}")
        self.preview.setPlainText("\n\n".join(lines))
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(bool(self._ai_planned))

    def _on_failed(self, err: str) -> None:
        """Lập kế hoạch lỗi: trả nút về trạng thái bấm được và hiện lý do."""
        self._worker = None
        self.gen_btn.setEnabled(True)
        self.gen_btn.setText(tr("schedtask.ai_generate"))
        self.preview.setPlainText(str(err))

    # ---- Import tab ---------------------------------------------------------
    def _on_import_tasks_changed(self, has_tasks: bool) -> None:
        """Tab Nhập có task thì chuyển nguồn dữ liệu sang đó và mở nút OK."""
        if has_tasks:
            self._active_source = "import"
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(has_tasks)

    # ---- confirm ------------------------------------------------------------
    def _confirm(self) -> None:
        """Chốt: lấy task từ nguồn đang hoạt động (AI hoặc Nhập) và gắn project cho chúng."""
        planned = self.import_panel.planned if self._active_source == "import" else self._ai_planned
        project_id = self.workspace_combo.currentData() or ""
        for t in planned:
            t["project_id"] = project_id
        self.created_tasks = planned
        self.accept()


__all__ = ["AiTaskCreatorDialog"]
