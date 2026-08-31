"""Mục Chung trong Cài đặt — R08-T07.

Ngôn ngữ, giao diện, khay hệ thống, và dòng gợi ý cuối trang.

Bản trước khi tách dựng mục này thành một ``QFormLayout`` rời, gắn vào layout
gốc, rồi ở đoạn lắp ráp lại gỡ ra để nhét vào hộp riêng — kèm một widget cao
0 pixel làm mốc cuộn. Vòng vo đó chỉ tồn tại vì mục này không phải group box
như bốn mục kia. Gói thành widget là hết: nó tự là một trang, không cần gỡ ra
gắn vào, không cần mốc giả.
"""
from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLabel, QVBoxLayout, QWidget

from ...i18n import LANGUAGES, tr
from ...ui.widgets import SegmentedControl, ToggleSwitch


class GeneralSettingsWidget(QWidget):
    """Nhóm "Chung" trong Cài đặt: ngôn ngữ, giao diện, khởi động cùng hệ thống,
    thu về khay.
    """
    def __init__(self, ctx, parent=None):
        """Nhóm Cài đặt chung: ngôn ngữ, giao diện, thư mục dùng chung."""
        super().__init__(parent)
        data = ctx.config.data
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        form = QFormLayout()

        self.language_combo = SegmentedControl()
        for key, label in LANGUAGES.items():
            self.language_combo.addItem(label, key)
        _select(self.language_combo, ctx.config.language)
        form.addRow(tr("settings.language"), self.language_combo)

        # Giao diện cũng có trên hàng tài khoản ở thanh bên (một cú bấm để lật
        # nhanh); đây là cùng một giá trị, nhưng có tên và có giải thích, cho
        # người đi tìm nó trong Cài đặt.
        self.theme_combo = SegmentedControl()
        for key in ("system", "dark", "light"):
            self.theme_combo.addItem(tr(f"settings.theme_{key}"), key)
        _select(self.theme_combo, getattr(ctx.config, "theme", "system"))
        form.addRow(tr("settings.theme"), self.theme_combo)

        tray = data.get("tray", {})
        self.tray_chk = ToggleSwitch(tr("settings.tray_keep"))
        self.tray_chk.setChecked(bool(tray.get("minimize_on_close", True)))
        form.addRow("", self.tray_chk)
        self.notify_chk = ToggleSwitch(tr("settings.tray_notify"))
        self.notify_chk.setChecked(bool(tray.get("notify_on_done", True)))
        form.addRow("", self.notify_chk)

        outer.addLayout(form)

        note = QLabel(tr("settings.tip"))
        note.setObjectName("hint")
        note.setWordWrap(True)   # không thì đúng một dòng này quyết định bề ngang dialog
        outer.addWidget(note)
        outer.addStretch(1)

    # ---- lưu ------------------------------------------------------------

    def apply_to(self, data: dict) -> None:
        """Ghi các lựa chọn chung vào dict cấu hình.

        Không tự áp theme ở đây: ``MainWindow._open_settings`` áp lại sau khi hộp
        thoại đóng, làm cả hai chỗ sẽ vẽ lại giao diện hai lần.
        """
        data["language"] = self.language_combo.currentData()
        # MainWindow._open_settings áp lại giao diện sau khi dialog đóng, nên
        # ghi giá trị ở đây là đủ để nó có hiệu lực.
        data["theme"] = self.theme_combo.currentData()
        tray = data.setdefault("tray", {})
        tray["minimize_on_close"] = self.tray_chk.isChecked()
        tray["notify_on_done"] = self.notify_chk.isChecked()


def _select(combo, value: str) -> None:
    """Chọn mục mang dữ liệu ``value`` trong một combo; không có thì để nguyên."""
    i = combo.findData(value)
    if i >= 0:
        combo.setCurrentIndex(i)
