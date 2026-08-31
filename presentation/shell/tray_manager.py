"""Biểu tượng khay hệ thống — R08-T10.

Bóc từ ``app.py::MainWindow``. Giữ biểu tượng khay, menu chuột phải của nó, và
việc bắn thông báo bong bóng.

Vì sao tách: khay là thứ **có thể không tồn tại**. Máy không có khay hệ thống
(một số môi trường Linux, phiên RDP) thì ``isSystemTrayAvailable()`` trả False
và mọi thứ ở đây phải im lặng chấp nhận. Trộn lẫn trong MainWindow thì mỗi chỗ
dùng đều phải tự nhớ kiểm ``if self.tray is not None`` — đã có 6 chỗ như thế.
Gói lại thì chỗ gọi cứ gọi, không có khay thì không có gì xảy ra.
"""
from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


class TrayManager:
    """Khay hệ thống của một cửa sổ. An toàn khi máy không có khay."""

    def __init__(self, window, *, icon, tooltip: str, tr):
        """Dựng biểu tượng khay nếu hệ điều hành có; không có thì mọi thao tác về sau
        thành no-op.
        """
        self.window = window
        self._tr = tr
        self.icon: QSystemTrayIcon | None = None
        self._open_act: QAction | None = None
        self._quit_act: QAction | None = None
        self._tooltip = tooltip
        self._app_icon = icon

    # ---- dựng ------------------------------------------------------------

    def setup(self) -> None:
        """Dựng biểu tượng khay. Không có khay thì lặng lẽ bỏ qua."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        w = self.window
        self.icon = QSystemTrayIcon(self._app_icon(), w)
        self.icon.setToolTip(self._tooltip)

        menu = QMenu()
        self._open_act = QAction(self._tr("app.tray.open"), w)
        self._open_act.triggered.connect(w._show_window)
        self._quit_act = QAction(self._tr("app.tray.quit"), w)
        self._quit_act.triggered.connect(w._quit_app)
        menu.addAction(self._open_act)
        menu.addAction(self._quit_act)
        self.icon.setContextMenu(menu)

        self.icon.activated.connect(
            lambda reason: w._show_window() if reason == QSystemTrayIcon.Trigger else None)
        self.icon.show()

    def retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn cho tooltip và menu khay."""
        if self.icon is not None:
            self.icon.setToolTip(self._tooltip)
        if self._open_act is not None:
            self._open_act.setText(self._tr("app.tray.open"))
            self._quit_act.setText(self._tr("app.tray.quit"))

    def hide(self) -> None:
        """Ẩn biểu tượng khay; máy không có khay thì không làm gì."""
        if self.icon is not None:
            self.icon.hide()

    # ---- thông báo -------------------------------------------------------

    def show_message(self, title: str, body: str, *, error: bool = False,
                     msec: int = 5000) -> None:
        """Bắn bong bóng khay. Không có khay, hoặc hệ điều hành từ chối, thì
        thôi — một thông báo không hiện được không đáng làm hỏng lượt chạy."""
        if self.icon is None:
            return
        kind = QSystemTrayIcon.Critical if error else QSystemTrayIcon.Information
        try:
            self.icon.showMessage(title, body, kind, msec)
        except Exception:  # noqa: BLE001
            pass
