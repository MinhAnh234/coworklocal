"""Xuất khung đồ thị đang xem ra file PNG — tách khỏi ``graph_renderer.py``.

GraphRAG có hai khung xem: cảnh Qt 2D và trang D3 chạy trong WebEngine. Hai
khung ấy chụp ảnh theo hai cách hoàn toàn khác nhau (``QWidget.grab()`` so
với một lượt gọi JavaScript trả về data URL), nên chỗ này gom cả hai lại sau
một hàm duy nhất và tự chọn đường đi.
"""
from __future__ import annotations

import base64
from typing import Callable, Optional

from PySide6.QtWidgets import QFileDialog, QWidget

from cowork_local.i18n import tr

#: Bên gọi truyền vào để hiện kết quả trên thanh trạng thái.
StatusFn = Callable[[str], None]


def ask_export_path(parent: QWidget) -> str:
    """Hỏi người dùng nơi lưu ảnh; trả về '' nếu họ bấm Huỷ."""
    path, _ = QFileDialog.getSaveFileName(
        parent, tr("structure.export_title"), "structure-graph.png", "PNG (*.png)")
    return path or ""


def export_widget_grab(widget: QWidget, path: str, status: StatusFn) -> None:
    """Chụp thẳng widget đang hiện ra PNG.

    Đây cũng là đường lui khi xuất từ D3 thất bại: chụp widget luôn cho ra
    một tấm ảnh, dù không sắc nét bằng bản vẽ vector của D3.
    """
    if widget.grab().save(path, "PNG"):
        status(tr("structure.export_done", path=path))
    else:
        status(tr("structure.export_failed", err="grab() returned no image"))


def export_d3_png(web, path: str, fallback: QWidget, status: StatusFn) -> None:
    """Xuất PNG từ trang D3 bằng cách nhờ chính trang đó vẽ ra data URL.

    ``runJavaScript`` chạy bất đồng bộ nên kết quả về trong hàm gọi lại. Mọi
    đường hỏng — trang chưa nạp xong, ``window.exportPng`` không tồn tại,
    chuỗi trả về không phải data URL — đều quay sang chụp widget, để người
    dùng bấm Xuất vẫn luôn nhận được một file thay vì im lặng không có gì.
    """
    def on_result(data_url) -> None:
        """Nhận data URL từ trang D3 và ghi ra file; hỏng ở bất cứ đâu thì quay sang
        chụp widget.
        """
        if not isinstance(data_url, str) or "," not in data_url:
            export_widget_grab(fallback, path, status)
            return
        try:
            with open(path, "wb") as f:
                f.write(base64.b64decode(data_url.split(",", 1)[1]))
            status(tr("structure.export_done", path=path))
        except (OSError, ValueError) as exc:
            status(tr("structure.export_failed", err=str(exc)))

    web.page().runJavaScript("window.exportPng ? window.exportPng() : ''", on_result)


def export_png(parent: QWidget, showing: QWidget, web: Optional[object],
               is_web_visible: bool, status: StatusFn) -> None:
    """Hỏi đường dẫn rồi xuất khung ĐANG hiện — D3 hay cảnh Qt tuỳ tab đang mở.

    Chỉ dùng đường D3 khi trang D3 thật sự đang hiển thị; đang xem cảnh Qt mà
    lại chụp D3 thì ảnh ra không khớp với thứ người dùng nhìn thấy.
    """
    path = ask_export_path(parent)
    if not path:
        return
    if web is not None and is_web_visible:
        export_d3_png(web, path, showing, status)
    else:
        export_widget_grab(showing, path, status)


__all__ = ["export_png", "export_d3_png", "export_widget_grab", "ask_export_path"]
