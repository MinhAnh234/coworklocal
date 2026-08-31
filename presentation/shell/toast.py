"""Thông báo nhỏ tự ẩn ở góc trên trái cửa sổ — R08-T10.

Hiện ngay trong app, khác với bong bóng khay hệ thống ở ``tray_manager.py``:
cái này hiện dù cửa sổ có đang được focus hay không, cái kia chỉ hiện khi
người dùng đang nhìn chỗ khác.
"""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel

from ...theme import current_palette


class Toast(QLabel):
    """A small auto-hiding notification shown at the window's top-left."""

    def __init__(self, parent):
        """Thông báo ngắn nổi lên rồi tự tắt; dựng ở trạng thái ẩn."""
        super().__init__(parent)
        self.setObjectName("toast")
        self.setWordWrap(True)
        self.setMaximumWidth(380)
        self.setVisible(False)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, text: str, ok: bool = True, ms: int = 4500) -> None:
        """Hiện một thông báo (xanh khi thành công, đỏ khi lỗi) rồi tự ẩn sau ``ms`` mili giây."""
        p = current_palette()
        bg = p.success_soft if ok else p.danger_soft
        fg = p.success if ok else p.danger
        self.setStyleSheet(
            f"#toast {{ background:{bg}; color:{fg}; border:1px solid {fg};"
            f" border-radius:{p.radius}px; padding:10px 16px; font-weight:600; }}")
        self.setText(text)
        self.adjustSize()
        self.move(14, 14)          # top-left of the window
        self.raise_()
        self.setVisible(True)
        self._timer.start(ms)
