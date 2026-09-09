"""Mục "Giới thiệu" trong Cài đặt.

Dòng ghi công tác giả trước đây nằm cố định ở góc dưới phải cửa sổ, dưới dạng
widget thường trực của thanh trạng thái. Chỗ đó chiếm một góc màn hình trên MỌI
màn hình, suốt cả phiên làm việc, cho một thông tin người dùng chỉ cần đọc một
lần. Chuyển vào Cài đặt: vẫn tra được bất cứ lúc nào, nhưng không còn đứng
thường trực trong tầm mắt.

Cùng nhóm widget với bốn mục kia của Cài đặt (``general``/``provider``/
``parameter``/``routing``) nên nó tự là một trang, không cần lắp ráp riêng.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ... import DISPLAY_NAME, __version__
from ...i18n import tr


class AboutSettingsWidget(QWidget):
    """Nhóm "Giới thiệu": tên ứng dụng và dòng ghi công tác giả."""

    def __init__(self, ctx=None, parent: QWidget | None = None) -> None:
        """Trang Giới thiệu. ``ctx`` không dùng tới, giữ cho khớp chữ ký của
        bốn widget Cài đặt còn lại."""
        super().__init__(parent)
        self.ctx = ctx

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        # Tên sản phẩm là danh từ riêng, không dịch — lấy thẳng từ gốc gói,
        # cùng nguồn với tiêu đề cửa sổ (main_window.py:90) nên hai chỗ không lệch.
        self.app_label = QLabel(f"{DISPLAY_NAME} v{__version__}")
        # Không đặt màu ở đây: cỡ chữ là khác biệt duy nhất cần thiết, còn màu
        # do theme quyết định (xem theme/__init__.py — ngoài theme/ không file
        # nào được đặt tên một màu).
        font = self.app_label.font()
        font.setPointSize(font.pointSize() + 4)
        font.setBold(True)
        self.app_label.setFont(font)
        layout.addWidget(self.app_label)

        self.version_label = QLabel(tr("app.version", v=__version__))
        self.version_label.setObjectName("faint")
        self.version_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.version_label)

        layout.addStretch(1)

    def apply_to(self, data: dict) -> None:
        """Không có thiết lập nào để ghi — mục này chỉ hiển thị.

        Vẫn khai để khớp giao diện chung của các trang Cài đặt: ``_save`` gọi
        ``apply_to`` trên từng trang, nên một trang thiếu hàm này sẽ là
        ``AttributeError`` ngay lần đầu ai đó thêm nó vào vòng lặp.
        """
        return
