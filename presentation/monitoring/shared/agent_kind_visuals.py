"""Màu, huy hiệu và avatar của agent quản trị theo LOẠI VIỆC nó làm.

Bảng Agents Admin xếp agent theo ``task_kind`` (search / monitor / cowork /
graphrag / schedule / security / help). Ở đây gom toàn bộ phần "loại việc ấy
trông thế nào": màu định danh cho avatar, tông huy hiệu cho ô Vai trò, tông
huy hiệu cho ô Trạng thái.

Khác với ``formatters.py::agent_avatar_colour`` — chỗ đó đoán màu bằng cách
dò từ khoá trong TÊN agent, dùng cho các bảng chỉ có tên. Bảng quản trị biết
chính xác loại việc nên tra thẳng, không phải đoán.

Bảy loại, bảy tông riêng: không hai loại nào trùng màu huy hiệu, để phân biệt
được bằng màu chứ không phải chỉ bằng chữ. Màu cố định, không đổi theo giao
diện sáng/tối — cùng quy ước với avatar từng agent ở ``monitoring_tab.py``.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap

from .formatters import agent_initials

#: Màu vòng tròn avatar theo loại việc.
KIND_COLOUR = {
    "search": "#8A8886", "monitor": "#FFB900", "cowork": "#0078D4",
    "graphrag": "#8764B8", "schedule": "#107C10", "security": "#D13438",
    "help": "#E3008C",
}

#: Tên đối tượng huy hiệu (định nghĩa trong ``theme.py``) cho ô Vai trò.
KIND_BADGE = {
    "search": "badgeNeutral", "monitor": "badgeWarn", "cowork": "badge",
    "graphrag": "badgePurple", "schedule": "badgeSuccess", "security": "badgeDanger",
    "help": "badgePink",
}

#: Tông huy hiệu cho ô Trạng thái, theo kết quả lần kiểm tra gần nhất.
STATUS_BADGE = {
    "unchecked": "badgeNeutral", "checking": "badgeWarn",
    "ok": "badgeSuccess", "bad": "badgeDanger",
}


def kind_avatar_icon(kind: str, name: str, size: int = 20) -> QIcon:
    """Avatar tròn cho một agent: nền là màu của loại việc, chữ là tên viết tắt.

    Loại lạ (file cấu hình sửa tay, loại mới thêm mà quên khai màu) rơi về màu
    xanh mặc định thay vì không vẽ gì — thiếu màu đúng vẫn hơn thiếu avatar.
    """
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(KIND_COLOUR.get(kind, "#0078D4")))
    p.drawEllipse(0, 0, size, size)
    font = QFont()
    font.setPixelSize(max(7, size // 2))
    font.setBold(True)
    p.setFont(font)
    p.setPen(QColor("#FFFFFF"))
    p.drawText(pm.rect(), Qt.AlignCenter, agent_initials(name))
    p.end()
    return QIcon(pm)


__all__ = ["KIND_COLOUR", "KIND_BADGE", "STATUS_BADGE", "kind_avatar_icon"]
