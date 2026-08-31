"""Opens the Settings dialog and runs a callback afterward — shared by the
Sandbox Details and Permissions cards' "Edit" buttons, both of which used to
call the identical ``MonitoringTab._open_settings_and_refresh``.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QWidget


def open_settings_and_notify(ctx, parent: QWidget, on_changed: Callable[[], None]) -> None:
    """Mở hộp thoại Cài đặt rồi gọi ``on_changed`` sau khi đóng.

    Các thẻ trong màn Giám sát dùng chung hàm này để làm mới sau khi người dùng
    sửa cấu hình an toàn.
    """
    from ....ui.settings_dialog import SettingsDialog

    dlg = SettingsDialog(ctx, parent)
    dlg.exec()
    on_changed()
