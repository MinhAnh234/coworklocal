"""Hộp thoại thêm/sửa một agent trong danh mục quản trị — R08-T08.

Tách khỏi ``agents_admin_tab.py``: bảng danh sách và hộp thoại sửa là hai
việc khác nhau, và hộp thoại còn tự đi hỏi provider xem có những model nào
(``_load_live_models``) — thứ bảng không cần biết.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from ....config import PROVIDER_LABELS
from ....core import admin_agents, preview_ai
from ....core.worker import AgentWorker
from ....i18n import on_language_changed, tr
from ....state import AppContext
from ....ui.icons import icon
from ....ui.widgets import ToggleSwitch, badge_pill_widget


class AgentEditDialog(QDialog):
    """Add/Edit one admin agent. The provider/model pickers are drop-lists,
    not free text — ``provider_combo`` offers the app's built-in providers
    (plus "machine default"), ``model_combo`` offers that provider's REAL
    model list once fetched via "Load models" (same on-demand fetch the
    Preview tab and Settings' own "Load" button use) — editable so an admin
    can still pin an exact model string that isn't in the fetched list yet."""

    def __init__(self, parent=None, ctx: Optional[AppContext] = None,
                 agent: Optional[admin_agents.AdminAgent] = None,
                 default_model_hint: str = ""):
        """Form thêm/sửa một agent quản trị.

        Danh sách model của từng provider được nạp nền và nhớ lại, để đổi qua đổi
        lại giữa các provider không phải gọi mạng lần nữa.
        """
        super().__init__(parent)
        self.ctx = ctx
        self._existing = agent
        self._live_models: Dict[str, List[str]] = {}
        self._workers: List[AgentWorker] = []
        self.setWindowTitle(tr("agents_admin.edit_title") if agent
                            else tr("agents_admin.add_title"))
        self.resize(420, 400)
        form = QFormLayout(self)
        self.name_edit = QLineEdit(agent.name if agent else "")
        form.addRow(tr("agents_admin.f_name"), self.name_edit)
        self.kind_combo = QComboBox()
        for kind in admin_agents.TASK_KINDS:
            self.kind_combo.addItem(tr(f"agents_admin.kind.{kind}"), kind)
        if agent:
            idx = self.kind_combo.findData(agent.task_kind)
            if idx >= 0:
                self.kind_combo.setCurrentIndex(idx)
        form.addRow(tr("agents_admin.f_kind"), self.kind_combo)
        self.prompt_edit = QPlainTextEdit(agent.prompt if agent else "")
        self.prompt_edit.setPlaceholderText(tr("agents_admin.f_prompt_placeholder"))
        self.prompt_edit.setMaximumHeight(110)
        form.addRow(tr("agents_admin.f_prompt"), self.prompt_edit)

        self.provider_combo = QComboBox()
        self.provider_combo.addItem(tr("agents_admin.provider_default"), _PROVIDER_DEFAULT)
        for key, label in PROVIDER_LABELS.items():
            self.provider_combo.addItem(label, key)
        if agent and agent.provider:
            idx = self.provider_combo.findData(agent.provider)
            if idx >= 0:
                self.provider_combo.setCurrentIndex(idx)
        self.provider_combo.currentIndexChanged.connect(self._refresh_model_combo)
        form.addRow(tr("agents_admin.f_provider"), self.provider_combo)

        model_row = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        if agent and agent.model:
            self.model_combo.addItem(agent.model)
        self.model_combo.setEditText(agent.model if agent else "")
        self.model_combo.lineEdit().setPlaceholderText(
            tr("agents_admin.f_model_placeholder", model=default_model_hint or "—"))
        self.load_models_btn = QPushButton()
        self.load_models_btn.setIcon(icon("download"))
        self.load_models_btn.setToolTip(tr("agents_admin.load_models_tooltip"))
        self.load_models_btn.clicked.connect(self._load_live_models)
        self.load_models_btn.setEnabled(self.ctx is not None)
        model_row.addWidget(self.model_combo, 1)
        model_row.addWidget(self.load_models_btn)
        form.addRow(tr("agents_admin.f_model"), model_row)

        self.enabled_chk = QCheckBox(tr("agents_admin.f_enabled"))
        self.enabled_chk.setChecked(agent.enabled if agent else True)
        form.addRow("", self.enabled_chk)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _load_live_models(self) -> None:
        """Nạp danh sách model đang sống của mọi provider, ở luồng nền."""
        if self.ctx is None:
            return
        self.load_models_btn.setEnabled(False)
        ctx = self.ctx

        def job(_worker: AgentWorker):
            """Chạy nền: hỏi từng provider danh sách model."""
            return preview_ai.fetch_live_models(ctx)

        def done(result: dict) -> None:
            """Ghi nhớ danh sách model rồi nạp vào ô chọn theo provider đang chọn."""
            self.load_models_btn.setEnabled(True)
            self._live_models = result or {}
            self._refresh_model_combo()
            if not self._live_models:
                QMessageBox.information(self, tr("agents_admin.add_title"),
                                        tr("agents_admin.load_models_empty"))

        def failed(err: str) -> None:
            """Nạp model lỗi: hiện cảnh báo và mở khoá lại nút."""
            self.load_models_btn.setEnabled(True)
            QMessageBox.warning(self, tr("agents_admin.add_title"), err)

        w = AgentWorker(job)
        w.finished_ok.connect(done)
        w.failed.connect(failed)
        self._workers.append(w)
        w.start()

    def _refresh_model_combo(self) -> None:
        """Nạp lại ô chọn model theo provider đang chọn, giữ nguyên thứ đang gõ."""
        provider_key = self.provider_combo.currentData()
        current_text = self.model_combo.currentText().strip()
        models = self._live_models.get(provider_key, []) if provider_key else []
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(models)
        self.model_combo.setEditText(current_text)
        self.model_combo.blockSignals(False)

    def result_fields(self) -> Dict[str, str]:
        """Các trường agent lấy từ form, để chỗ gọi dựng bản ghi."""
        return {
            "name": self.name_edit.text().strip(),
            "task_kind": self.kind_combo.currentData(),
            "prompt": self.prompt_edit.toPlainText().strip(),
            "provider": self.provider_combo.currentData() or "",
            "model": self.model_combo.currentText().strip(),
            "enabled": self.enabled_chk.isChecked(),
        }
