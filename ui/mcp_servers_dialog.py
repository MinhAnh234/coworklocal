"""Add/edit one external MCP (Model Context Protocol) server entry — Settings'
"🔌 MCP Servers" section (see settings_dialog.py for the list/CRUD)."""
from __future__ import annotations

import shlex
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QLineEdit, QVBoxLayout,
)

from ..i18n import tr


class McpServerEditDialog(QDialog):
    """Form thêm/sửa một máy chủ MCP: tên, lệnh chạy, tham số và công tắc bật.

    Đã được ``ui/connectors_panel.py`` thay thế; giữ lại làm bản đối chiếu.
    """
    def __init__(self, parent=None, server: Optional[dict] = None):
        """Dựng form. ``server`` để None thì đây là form thêm mới."""
        super().__init__(parent)
        server = server or {}
        self.setWindowTitle(tr("mcp.edit_title") if server else tr("mcp.add_title"))
        self.setMinimumWidth(480)
        self._enabled = bool(server.get("enabled", True))

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(tr("mcp.name_label")))
        self.name = QLineEdit(server.get("name", ""))
        self.name.setPlaceholderText(tr("mcp.name_placeholder"))
        lay.addWidget(self.name)

        lay.addWidget(QLabel(tr("mcp.command_label")))
        self.command = QLineEdit(server.get("command", ""))
        self.command.setPlaceholderText(tr("mcp.command_placeholder"))
        lay.addWidget(self.command)

        lay.addWidget(QLabel(tr("mcp.args_label")))
        self.args = QLineEdit(" ".join(server.get("args", []) or []))
        self.args.setPlaceholderText(tr("mcp.args_placeholder"))
        lay.addWidget(self.args)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _on_accept(self) -> None:
        """Chỉ đóng khi đã có tên và lệnh chạy — thiếu một trong hai thì máy chủ không
        khởi động được. Con trỏ nhảy về ô tên thay vì hiện hộp lỗi.
        """
        if not self.name.text().strip() or not self.command.text().strip():
            self.name.setFocus()
            return
        self.accept()

    def result_server(self) -> dict:
        """Nội dung form dưới dạng dict.

        Tham số được tách bằng ``shlex`` chứ không phải ``split()``: đường dẫn có
        khoảng trắng phải đặt trong dấu nháy và vẫn tính là MỘT tham số.
        """
        args_text = self.args.text().strip()
        return {
            "name": self.name.text().strip(),
            "command": self.command.text().strip(),
            "args": shlex.split(args_text) if args_text else [],
            "enabled": self._enabled,
        }
