"""WorkspaceFileTree — the folder-picker bar + directory tree pane of the
Folder Explorer (R08-T12, extracted from ``ui/folder_tab.py::FolderTab``,
lines 264-293/386-408 of the original 1587-line file).

Owns navigation only: which root is browsed and which file was clicked.
Rendering/editing the SELECTED file is
``document_preview_manager.py::DocumentPreviewManager``'s job — this widget
just emits :attr:`file_selected`.
"""
from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog, QFileSystemModel, QHBoxLayout, QLabel, QPushButton,
    QTreeView, QVBoxLayout, QWidget,
)

from cowork_local.i18n import tr
from cowork_local.ui.icons import icon


class WorkspaceFileTree(QWidget):
    """The left-hand tree pane: a path bar (label + "open folder" button)
    above a ``QFileSystemModel``-backed ``QTreeView``."""

    file_selected = Signal(str)   # absolute path of the clicked file
    root_changed = Signal(str)    # absolute path of the new root

    def __init__(self, initial_root: str, parent=None):
        """Cây tệp của thư mục làm việc, có ô đường dẫn ở trên làm tiêu đề màn hình."""
        super().__init__(parent)
        self._root = initial_root

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # The path IS the title of this screen, so it is written as one
        # rather than shown in a read-only text box that looks editable.
        # Full path on hover; the button still opens the folder picker.
        bar = QHBoxLayout()
        self.path_lbl = QLabel(self._root)
        self.path_lbl.setObjectName("folderTitle")
        self.path_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.path_lbl.setToolTip(self._root)
        self._open_btn = QPushButton()
        self._open_btn.setIcon(icon("folder"))
        self._open_btn.setObjectName("primary")
        self._open_btn.clicked.connect(self._pick_root)
        bar.addWidget(self.path_lbl, 1)
        bar.addWidget(self._open_btn)
        root_layout.addLayout(bar)

        self.model = QFileSystemModel()
        self.model.setRootPath(self._root)
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(self._root))
        for col in (1, 2, 3):          # hide Size / Type / Date-modified columns
            self.tree.hideColumn(col)
        self.tree.setHeaderHidden(True)
        self.tree.clicked.connect(self._on_tree_clicked)
        root_layout.addWidget(self.tree, 1)

        self.retranslate()

    def retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn."""
        self._open_btn.setToolTip(tr("folder.path_placeholder"))
        self._open_btn.setText(tr("folder.open_folder"))

    @property
    def root(self) -> str:
        """Thư mục gốc đang hiện."""
        return self._root

    def set_root(self, path: str) -> None:
        """Đổi thư mục gốc; đường dẫn rỗng hoặc không tồn tại thì BỎ QUA lặng lẽ.

        Chỗ gọi dựa vào việc ``root`` không đổi để biết cây đã từ chối đường dẫn.
        """
        p = str(path or "").strip()
        if not p or not os.path.isdir(p):
            return
        self._root = p
        self.path_lbl.setText(p)
        self.path_lbl.setToolTip(p)
        self.model.setRootPath(p)
        self.tree.setRootIndex(self.model.index(p))
        self.root_changed.emit(p)

    def _pick_root(self) -> None:
        """Mở hộp thoại chọn thư mục gốc."""
        chosen = QFileDialog.getExistingDirectory(self, tr("folder.open_folder"), self._root)
        if chosen:
            self.set_root(chosen)

    def _on_tree_clicked(self, index) -> None:
        """Bấm vào một mục: là tệp thì phát tín hiệu mở, là thư mục thì để cây tự bung."""
        path = self.model.filePath(index)
        if path and os.path.isfile(path):
            self.file_selected.emit(path)


__all__ = ["WorkspaceFileTree"]
