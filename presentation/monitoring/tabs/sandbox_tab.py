"""Sandbox Details card — the current sandbox id/status/uptime/resource
limits/network state, with a collapsible fold that ALSO nests the
Permissions card inside it (see ``security_settings_tab.PermissionsCard``),
exactly matching the pre-refactor ``ui/monitoring_tab.py`` layout: Sandbox
and Permissions answer the same question ("what is the agent allowed to
touch?"), so they share one fold rather than being two independent
top-level sections. This card is embedded inside ``overview_tab.OverviewTab``
at the same position the original ``QGroupBox`` occupied — no new top-level
tab is added, so the visible UI is unchanged.
"""
from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ....i18n import tr
from ..shared.badges import apply_badge
from ..shared.layout_helpers import kv_row
from ..shared.open_settings import open_settings_and_notify
from .security_settings_tab import PermissionsCard


class SandboxDetailsCard(QGroupBox):
    """Thẻ "Trạng thái sandbox": backend cách ly đang dùng, giới hạn tài nguyên và
    trạng thái chặn mạng.
    """
    def __init__(self, ctx, on_settings_changed: Callable[[], None]):
        """Thẻ thông tin sandbox: cơ chế cách ly đang dùng và các giới hạn của nó."""
        super().__init__()
        self._ctx = ctx
        self._on_settings_changed = on_settings_changed
        self.setObjectName("monSection")
        sbx_lay = QVBoxLayout(self)

        self.summary_lbl = QLabel()
        self.summary_lbl.setWordWrap(True)
        sbx_lay.addWidget(self.summary_lbl)

        self.more_btn = QPushButton()
        self.more_btn.setObjectName("co4eSectionAction")
        self.more_btn.setFlat(True)
        self.more_btn.setCheckable(True)
        self.more_btn.setCursor(Qt.PointingHandCursor)
        sbx_lay.addWidget(self.more_btn, 0, Qt.AlignLeft)

        self._detail = QWidget()
        self._detail.setVisible(False)
        self.more_btn.toggled.connect(self._detail.setVisible)
        self.more_btn.toggled.connect(self._sync_more_label)
        sbx_lay.addWidget(self._detail)
        detail_lay = QVBoxLayout(self._detail)
        detail_lay.setContentsMargins(0, 4, 0, 0)

        self.id_lbl, self.id_val = kv_row(detail_lay)
        self.status_lbl, self.status_val = kv_row(detail_lay)
        self.status_val.setObjectName("badgeSuccess")
        self.created_lbl, self.created_val = kv_row(detail_lay)
        self.uptime_lbl, self.uptime_val = kv_row(detail_lay)

        limits_row = QHBoxLayout()
        self.limits_lbl = QLabel()
        self.limits_lbl.setObjectName("hint")
        self.limits_lbl.setWordWrap(True)
        self.edit_btn = QPushButton()
        self.edit_btn.setFlat(True)
        self.edit_btn.clicked.connect(self._open_settings)
        limits_row.addWidget(self.limits_lbl, 1)
        limits_row.addWidget(self.edit_btn)
        detail_lay.addLayout(limits_row)

        self.net_lbl, self.net_val = kv_row(detail_lay)

        # The Permissions card is nested inside THIS fold, not a sibling
        # section — matches the original layout exactly.
        self.permissions_card = PermissionsCard(ctx, on_settings_changed)
        detail_lay.addWidget(self.permissions_card)

    def _open_settings(self) -> None:
        """Mở hộp thoại Cài đặt tới nhóm an toàn, đóng xong thì làm mới thẻ."""
        open_settings_and_notify(self._ctx, self, self._on_settings_changed)

    def _sync_more_label(self, *_a) -> None:
        """Label the fold with what it will do next."""
        open_ = self.more_btn.isChecked()
        self.more_btn.setText(("▾ " if open_ else "▸ ") + tr("monitoring.overview_sbx_detail"))

    def retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn."""
        self.setTitle(tr("monitoring.overview_sandbox_details_title").upper().replace("&", "&&"))
        self.id_lbl.setText(tr("monitoring.overview_sandbox_id"))
        self.status_lbl.setText(tr("monitoring.overview_status"))
        self.created_lbl.setText(tr("monitoring.overview_created"))
        self.uptime_lbl.setText(tr("monitoring.overview_uptime"))
        self.edit_btn.setText(tr("monitoring.overview_edit"))
        self.net_lbl.setText(tr("monitoring.overview_network_label"))
        self.permissions_card.retranslate()
        self._sync_more_label()

    def refresh(self) -> None:
        """Đọc lại cấu hình an toàn và cập nhật các dòng trạng thái."""
        sec = self._ctx.config.agent_security
        net_blocked = bool(sec.get("block_network"))

        self.id_val.setText(f"sbx_{os.getpid():x}")
        self.status_val.setText(tr("monitoring.overview_status_running"))
        self.created_val.setText(datetime.fromtimestamp(self._ctx.started_at).strftime("%H:%M:%S"))
        uptime_s = max(0, int(time.time() - self._ctx.started_at))
        h, rem = divmod(uptime_s, 3600)
        m, s = divmod(rem, 60)
        self.uptime_val.setText(f"{h}h {m}m {s}s" if h else f"{m}m {s}s")

        limit_parts = []
        if sec.get("resource_limit_cpu_percent"):
            limit_parts.append(f"CPU {sec['resource_limit_cpu_percent']}%")
        if sec.get("resource_limit_memory_mb"):
            limit_parts.append(f"MEM {sec['resource_limit_memory_mb']}MB")
        if sec.get("resource_limit_disk_mb"):
            limit_parts.append(f"DISK {sec['resource_limit_disk_mb']}MB")
        limits_text = ", ".join(limit_parts) if limit_parts else tr("monitoring.na")
        self.limits_lbl.setText(tr("monitoring.overview_resource_limits") + ": " + limits_text)

        self.net_val.setText(
            tr("monitoring.overview_network_disabled") if net_blocked
            else tr("monitoring.overview_network_enabled"))
        apply_badge(self.net_val, "badgeWarn" if net_blocked else "badgeSuccess")

        # The one line the wireframe shows; the detail above stays a fold away.
        self.summary_lbl.setText(" · ".join([
            f'{tr("monitoring.overview_perm_fs")}: {tr("monitoring.overview_perm_fs_value")}',
            f'{tr("monitoring.overview_perm_network")}: '
            f'{tr("monitoring.overview_network_disabled") if net_blocked else tr("monitoring.overview_network_enabled")}',
            f'{tr("monitoring.overview_perm_process")}: {tr("monitoring.overview_perm_process_value")}',
            f'{tr("monitoring.overview_resource_limits")}: {limits_text}',
        ]))
        self._sync_more_label()

        self.permissions_card.refresh()
