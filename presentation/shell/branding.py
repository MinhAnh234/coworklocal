"""Tên gọi và biểu tượng của ứng dụng — R08-T10.

Tách riêng vì cả cửa sổ chính lẫn thanh trên cùng đều cần, mà để ở một trong
hai thì file kia phải import ngược lại — vòng import.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon

#: branding.py nằm sâu 2 cấp nên phải trỏ ngược lên gốc gói.
ASSETS = Path(__file__).resolve().parents[2] / "assets"


def app_icon() -> QIcon:
    """The buffalo app icon, used everywhere (window title bar, Windows taskbar and
    the tray). The multi-size ``.ico`` is loaded FIRST so Windows has the right
    pixmap for the taskbar; the high-res ``.png`` is added so the icon stays crisp
    at large sizes. This keeps the taskbar icon identical to the app's icon."""
    icon = QIcon()
    for name in ("icon.ico", "icon.png"):
        path = ASSETS / name
        if path.exists():
            icon.addFile(str(path))
    return icon
