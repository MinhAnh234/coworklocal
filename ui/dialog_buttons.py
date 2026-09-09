"""Nút hộp thoại mang chữ của ứng dụng, không phải chữ mặc định của Qt.

``QDialogButtonBox(Save | Cancel)``, ``QMessageBox.question`` và
``QInputDialog.get*`` lấy nhãn nút từ bảng dịch của CHÍNH Qt. Ứng dụng không cài
``QTranslator`` nào — và bản PySide6 đang dùng cũng không đóng gói sẵn file
``qtbase_*.qm`` nào để cài — nên bảng đó luôn rơi về tiếng Anh: chọn tiếng Nhật
thì hộp thoại vẫn hiện "Save" / "Cancel" / "&Yes" / "&No". Đây là lỗi người dùng
báo, và nó không nằm ở dây nối i18n của dự án — ``tr()`` chưa từng được hỏi tới.

Các hàm dưới đây gán nhãn của dự án đè lên nhãn Qt. Dùng chúng thay cho việc
dựng ``QDialogButtonBox`` / gọi ``QMessageBox.question`` / ``QInputDialog.get*``
trực tiếp.
"""
from __future__ import annotations

from typing import Callable, Iterable, Tuple

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QInputDialog, QMessageBox, QWidget,
)

from ..i18n import bind_text, tr

#: tên gọi trong ``**override`` -> (cờ nút chuẩn, khoá dịch mặc định)
_STANDARD = {
    "save": (QDialogButtonBox.Save, "dialog.save"),
    "cancel": (QDialogButtonBox.Cancel, "dialog.cancel"),
    "ok": (QDialogButtonBox.Ok, "dialog.ok"),
    "close": (QDialogButtonBox.Close, "dialog.close"),
}


def dialog_buttons(standard, **override: str) -> QDialogButtonBox:
    """``QDialogButtonBox`` có nhãn đổi theo ngôn ngữ đang chọn.

    ``override`` đổi khoá dịch của một nút cụ thể — ``ok="schedtask.ai_confirm"``
    cho hộp thoại muốn nút OK mang chữ riêng. Phải đi qua đây chứ không
    ``setText(tr(...))`` sau khi dựng: lần đổi ngôn ngữ kế tiếp, ràng buộc bên
    dưới sẽ áp lại khoá mặc định và xoá mất chữ riêng đó.
    """
    box = QDialogButtonBox(standard)
    for name, (flag, key) in _STANDARD.items():
        button = box.button(flag)
        if button is not None:
            bind_text(button, override.get(name, key))
    return box


def confirm(parent: QWidget | None, title: str, body: str) -> bool:
    """Hỏi Có/Không, trả về True nếu người dùng đồng ý.

    Thay cho ``QMessageBox.question(...) == QMessageBox.Yes``, vốn hiện "&Yes" /
    "&No" tiếng Anh ở mọi ngôn ngữ. Hộp thoại dựng lại mỗi lần mở nên gọi
    ``tr()`` một lần khi dựng là đủ, không cần ràng buộc.
    """
    box = QMessageBox(QMessageBox.Question, title, body,
                      QMessageBox.Yes | QMessageBox.No, parent)
    box.button(QMessageBox.Yes).setText(tr("dialog.yes"))
    box.button(QMessageBox.No).setText(tr("dialog.no"))
    return box.exec() == QMessageBox.Yes


def _hoi(parent: QWidget | None, title: str, label: str,
         dung: Callable[[QInputDialog], None]) -> Tuple[str, bool]:
    """Khung chung của ba hàm hỏi bên dưới; ``dung`` chỉnh riêng từng kiểu.

    Các hàm tĩnh ``QInputDialog.get*`` tự dựng hộp thoại bên trong nên không
    chạm được vào nút của nó — phải tự dựng thì mới đặt được nhãn.
    """
    dlg = QInputDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setLabelText(label)
    dlg.setOkButtonText(tr("dialog.ok"))
    dlg.setCancelButtonText(tr("dialog.cancel"))
    dung(dlg)
    # exec() TRƯỚC, đọc giá trị SAU: gói cả hai vào một tuple thì Python tính
    # textValue() trước và trả về chữ có sẵn lúc chưa ai gõ gì.
    dong_y = dlg.exec() == QDialog.Accepted
    return dlg.textValue(), dong_y


def ask_text(parent: QWidget | None, title: str, label: str,
             text: str = "") -> Tuple[str, bool]:
    """Như ``QInputDialog.getText``, nhưng nút bấm theo ngôn ngữ đang chọn."""
    return _hoi(parent, title, label, lambda d: d.setTextValue(text))


def ask_multiline(parent: QWidget | None, title: str, label: str,
                  text: str = "") -> Tuple[str, bool]:
    """Như ``QInputDialog.getMultiLineText``, nút bấm theo ngôn ngữ đang chọn."""
    def dung(d: QInputDialog) -> None:
        d.setOption(QInputDialog.UsePlainTextEditForTextInput)
        d.setTextValue(text)

    return _hoi(parent, title, label, dung)


def ask_item(parent: QWidget | None, title: str, label: str,
             items: Iterable[str], current: int = 0,
             editable: bool = False) -> Tuple[str, bool]:
    """Như ``QInputDialog.getItem``, nút bấm theo ngôn ngữ đang chọn."""
    muc = list(items)

    def dung(d: QInputDialog) -> None:
        d.setComboBoxItems(muc)
        d.setComboBoxEditable(editable)
        if muc:
            d.setTextValue(muc[current])

    return _hoi(parent, title, label, dung)
