"""Icons — a Monitoring sub-tab to browse the built-in icon set and add custom
icons for agents / flows.

Shows the built-in glyphs (the names usable in a Co4E step/agent ``icon`` field)
and the user's own imported SVG icons, with Add / Delete. Custom icons are saved
via ``core/custom_icons.py`` and become usable by name immediately.
"""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from ..core import custom_icons
from ..i18n import on_language_changed, tr
from ..state import AppContext
from . import icons as icons_mod
from .icons import icon


def _grid() -> QListWidget:
    """Dựng lưới hiển thị icon dạng ô vuông có nhãn."""
    g = QListWidget()
    g.setObjectName("iconGrid")   # accent border on hover/selection, see theme.py
    g.setViewMode(QListWidget.IconMode)
    g.setResizeMode(QListWidget.Adjust)
    g.setMovement(QListWidget.Static)
    g.setIconSize(QSize(28, 28))
    g.setGridSize(QSize(96, 74))
    g.setSpacing(4)
    return g


class IconsAdminTab(QWidget):
    """Tab "Icon" trong màn Giám sát: xem bộ icon hệ thống và thay icon bằng ảnh riêng."""
    def __init__(self, ctx: AppContext):
        """Tab quản trị biểu tượng: bộ dựng sẵn và bộ tự thêm.

        Ba nút thao tác nằm cạnh tiêu đề chứ không nằm dưới hai lưới — đặt dưới thì
        chúng trông như chỉ áp cho lưới tự thêm.
        """
        super().__init__()
        self.ctx = ctx
        root = QVBoxLayout(self)
        # Header row: the three actions sit beside the title, where the drawing
        # puts them, instead of in a strip below the two grids where they read
        # as belonging to the custom grid alone.
        head = QHBoxLayout()
        self._title = QLabel()
        self._title.setObjectName("monTitle")
        head.addWidget(self._title)
        head.addStretch(1)
        self.add_btn = QPushButton(); self.add_btn.setIcon(icon("plus"))
        self.add_btn.clicked.connect(self._add_icon)
        self.paste_btn = QPushButton()
        self.paste_btn.clicked.connect(self._add_from_svg_text)
        self.del_btn = QPushButton(); self.del_btn.setIcon(icon("trash"))
        self.del_btn.clicked.connect(self._delete_icon)
        for b in (self.add_btn, self.paste_btn, self.del_btn):
            head.addWidget(b)
        root.addLayout(head)

        self._hint = QLabel(); self._hint.setObjectName("hint"); self._hint.setWordWrap(True)
        root.addWidget(self._hint)

        # search over built-in names, with the magnifier the drawing asks for
        self.search = QLineEdit()
        self.search.addAction(icon("search"), QLineEdit.LeadingPosition)
        self.search.textChanged.connect(self._reload_builtin)
        root.addWidget(self.search)

        self._builtin_lbl = QLabel()
        self._builtin_lbl.setObjectName("navSectionHdr")   # quiet caps heading
        root.addWidget(self._builtin_lbl)
        self.builtin_grid = _grid()
        root.addWidget(self.builtin_grid, 2)

        self._custom_lbl = QLabel()
        self._custom_lbl.setObjectName("navSectionHdr")
        root.addWidget(self._custom_lbl)
        self.custom_grid = _grid()
        root.addWidget(self.custom_grid, 1)

        on_language_changed(self._retranslate)
        self._retranslate()

    # ---- rendering --------------------------------------------------------
    def _reload_builtin(self, *_a) -> None:
        """Nạp lại lưới icon dựng sẵn, lọc theo ô tìm kiếm."""
        q = self.search.text().strip().lower()
        self.builtin_grid.clear()
        for name in sorted(icons_mod._PATHS):
            if q and q not in name:
                continue
            it = QListWidgetItem(icon(name), name)
            it.setToolTip(name)
            it.setTextAlignment(Qt.AlignHCenter | Qt.AlignBottom)
            self.builtin_grid.addItem(it)

    def _reload_custom(self) -> None:
        """Nạp lại lưới icon do người dùng thêm."""
        self.custom_grid.clear()
        for name in custom_icons.list_custom():
            it = QListWidgetItem(icon(name), name)
            it.setToolTip(name)
            it.setData(Qt.UserRole, name)
            it.setTextAlignment(Qt.AlignHCenter | Qt.AlignBottom)
            self.custom_grid.addItem(it)

    # ---- actions ----------------------------------------------------------
    def _add_icon(self) -> None:
        """Thêm icon mới từ một tệp SVG."""
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, tr("icons_admin.add"), "", "SVG (*.svg)")
        if not path:
            return
        name, ok = QInputDialog.getText(self, tr("icons_admin.name_prompt"),
                                        tr("icons_admin.name_prompt"))
        if not ok:
            return
        try:
            custom_icons.add_from_file(path, name.strip())
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, tr("icons_admin.title"), str(exc))
            return
        self._reload_custom()

    def _add_from_svg_text(self) -> None:
        """Thêm icon bằng cách dán thẳng mã SVG."""
        name, ok = QInputDialog.getText(self, tr("icons_admin.name_prompt"),
                                        tr("icons_admin.name_prompt"))
        if not ok or not name.strip():
            return
        svg, ok = QInputDialog.getMultiLineText(self, tr("icons_admin.paste"),
                                                tr("icons_admin.paste_prompt"))
        if not ok:
            return
        try:
            custom_icons.add_svg(name.strip(), svg)
        except ValueError as exc:
            QMessageBox.warning(self, tr("icons_admin.title"), str(exc))
            return
        self._reload_custom()

    def _delete_icon(self) -> None:
        """Xoá icon tự thêm đang chọn; chưa chọn gì thì nhắc người dùng."""
        item = self.custom_grid.currentItem()
        if item is None:
            QMessageBox.information(self, tr("icons_admin.title"), tr("icons_admin.select_custom"))
            return
        custom_icons.delete_custom(item.data(Qt.UserRole))
        self._reload_custom()

    def _retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn."""
        self._title.setText(tr("monitoring.tab_icons"))
        self._hint.setText(tr("icons_admin.hint"))
        self.search.setPlaceholderText(tr("icons_admin.search"))
        # ICON TÍCH HỢP / ICON TÙY CHỈNH — caps, like every other section
        # heading the audit page draws.
        self._builtin_lbl.setText(tr("icons_admin.builtin").upper())
        self._custom_lbl.setText(tr("icons_admin.custom").upper())
        self.add_btn.setText(tr("icons_admin.add"))
        self.paste_btn.setText(tr("icons_admin.paste"))
        self.del_btn.setText(tr("icons_admin.delete"))
        self._reload_builtin()
        self._reload_custom()
