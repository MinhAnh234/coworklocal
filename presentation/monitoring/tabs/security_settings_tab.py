"""Permissions card — "what is the agent allowed to touch?", displayed
nested inside the Sandbox Details card's expandable fold (see
``sandbox_tab.SandboxDetailsCard``), exactly as in the pre-refactor
``ui/monitoring_tab.py`` (``self._sbx_detail.layout().addWidget(self.ov_permissions_group)``).
Editing still opens the same Settings dialog as the Sandbox card's own
"Edit" button — this card only DISPLAYS ``ctx.config.agent_security``, it
does not host its own settings-editing UI.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QPushButton, QVBoxLayout

from ....i18n import tr
from ..shared.badges import apply_badge
from ..shared.layout_helpers import kv_row
from ..shared.open_settings import open_settings_and_notify


class PermissionsCard(QGroupBox):
    """Thẻ "Quyền": agent đang được phép làm gì với tệp, mạng và lệnh shell."""
    def __init__(self, ctx, on_settings_changed: Callable[[], None]):
        """Thẻ thiết lập quyền: agent được đụng tới gì mà không phải hỏi."""
        super().__init__()
        self._ctx = ctx
        self._on_settings_changed = on_settings_changed
        self.setObjectName("monSection")
        perm_lay = QVBoxLayout(self)

        self.fs_lbl, self.fs_val = kv_row(perm_lay)
        self.network_lbl, self.network_val = kv_row(perm_lay)
        self.process_lbl, self.process_val = kv_row(perm_lay)
        self.env_lbl, self.env_val = kv_row(perm_lay)

        self.edit_btn = QPushButton()
        self.edit_btn.setFlat(True)
        self.edit_btn.clicked.connect(self._open_settings)
        perm_lay.addWidget(self.edit_btn, 0, Qt.AlignLeft)

    def _open_settings(self) -> None:
        """Mở hộp thoại Cài đặt tới nhóm an toàn, đóng xong thì làm mới thẻ."""
        open_settings_and_notify(self._ctx, self, self._on_settings_changed)

    def retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn."""
        self.setTitle(tr("monitoring.overview_permissions_title").upper())
        self.fs_lbl.setText(tr("monitoring.overview_perm_fs"))
        self.fs_val.setText(tr("monitoring.overview_perm_fs_value"))
        self.network_lbl.setText(tr("monitoring.overview_perm_network"))
        self.process_lbl.setText(tr("monitoring.overview_perm_process"))
        self.process_val.setText(tr("monitoring.overview_perm_process_value"))
        self.env_lbl.setText(tr("monitoring.overview_perm_env"))
        self.env_val.setText(tr("monitoring.overview_perm_env_value"))
        self.edit_btn.setText(tr("monitoring.overview_edit"))

    def refresh(self) -> None:
        """Đọc lại cấu hình an toàn và cập nhật các dòng quyền."""
        net_blocked = bool(self._ctx.config.agent_security.get("block_network"))
        self.network_val.setText(
            tr("monitoring.overview_perm_network_blocked") if net_blocked
            else tr("monitoring.overview_perm_network_allowed"))
        apply_badge(self.network_val, "badgeWarn" if net_blocked else "badgeSuccess")
