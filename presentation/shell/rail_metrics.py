"""Kích thước và cách vẽ một hàng trên thanh rail — R08-T10.

Chỉ số và cách vẽ, không có hành vi. Tách riêng vì ``theme.py`` cũng phải biết
mấy con số này (nó style ``#navrailBottom`` theo cùng lề), và vì thứ hay phải
tra lại nhất khi chỉnh giao diện là chúng — không nên nằm lẫn trong 400 dòng
dựng widget.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStyledItemDelegate

# ---- kích thước ---------------------------------------------------------
_NAV_EXPANDED_WIDTH = 150
_NAV_COLLAPSED_WIDTH = 54
_NAV_ROW_INSET = 8
_NAV_ROW_GAP = 6
_NAV_MIN_WIDTH = 132
_NAV_MAX_SHARE = 0.22
_NAV_MAX_CEILING = 360


class _NavItemDelegate(QStyledItemDelegate):
    """Keep a rail row's icon on the left edge, whatever the column is doing.

    QStyledItemDelegate hands the style decorationAlignment = AlignHCenter, so
    a row with no label — every row once the rail collapses to 54px — has its
    icon centred inside whatever box the column happens to give it. That box
    tracks the column width, which is not stable: stretched to the viewport the
    icons land in the middle of the rail, while a column left wider than the
    view leaves them at the left. Same code, two different pictures, which is
    why a test render disagreed with the running app.
    """

    def initStyleOption(self, option, index):
        """Ép icon của thanh menu canh trái và canh giữa theo chiều dọc.

        Mặc định Qt canh giữa icon theo chiều ngang, làm các dòng menu lệch nhau khi
        thanh được thu gọn.
        """
        super().initStyleOption(option, index)
        option.decorationAlignment = Qt.AlignLeft | Qt.AlignVCenter
