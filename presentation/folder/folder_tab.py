"""FolderTab shell (R08-T12) — assembles
``workspace_file_tree.py::WorkspaceFileTree``,
``document_preview_manager.py::DocumentPreviewManager`` and
``ai_file_editor_dialog.py::AiFileEditorDialog`` behind the splitter/terminal
layout that used to be inline in ``ui/folder_tab.py::FolderTab.__init__``
(lines 238-384 of the original 1587-line file).

The AI-panel toggle button (``ai_btn``) lives here because it controls
things two different children own: the panel's own visibility AND the
content splitter's sizing — a genuine shell-level concern, not either
child's.
"""
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSplitter, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, Signal

from cowork_local.i18n import on_language_changed, tr
from cowork_local.presentation.folder.ai_file_editor_dialog import AiFileEditorDialog
from cowork_local.presentation.folder.document_preview_manager import DocumentPreviewManager
from cowork_local.presentation.folder.workspace_file_tree import WorkspaceFileTree
from cowork_local.state import AppContext
from cowork_local.ui.icons import icon


class FolderTab(QWidget):
    """Two-pane file explorer: directory tree + view/edit pane (+ collapsible
    AI-edit panel, + collapsible terminal)."""

    status_message = Signal(str)

    def __init__(self, ctx: AppContext, cowork=None):
        """Ghép ba phần của tab Thư mục: cây tệp, khung xem và terminal."""
        super().__init__()
        self.ctx = ctx
        self._root = str(ctx.config.cowork_output_dir())

        root_layout = QVBoxLayout(self)
        split = QSplitter(Qt.Horizontal)

        self.tree = WorkspaceFileTree(self._root)
        split.addWidget(self.tree)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)

        self.preview = DocumentPreviewManager(self._root)
        self.ai_panel = AiFileEditorDialog(ctx, self.preview, cowork=cowork)

        self.ai_btn = QPushButton()        # expand/collapse the AI-edit panel
        self.ai_btn.setIcon(icon("sparkle"))
        self.ai_btn.setCheckable(True)
        self.ai_btn.clicked.connect(self._toggle_ai_panel)
        # Same visual position as the original single-class header: between
        # the Preview⇄Edit toggle and Save (file_label=0, mode_btn=1).
        self.preview.header_layout.insertWidget(2, self.ai_btn)
        self.ai_panel.badge_changed.connect(self._on_ai_badge_changed)

        content_split = QSplitter(Qt.Horizontal)
        content_split.addWidget(self.preview)
        content_split.addWidget(self.ai_panel)
        content_split.setStretchFactor(0, 1)
        content_split.setStretchFactor(1, 0)
        content_split.setSizes([700, 320])
        self._content_split = content_split
        self.ai_panel.setVisible(False)   # default collapsed
        rl.addWidget(content_split, 1)

        split.addWidget(right)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([300, 800])
        root_layout.addWidget(split, 1)

        # Terminal CLI below the file view — collapsible, default collapsed;
        # opening it points the shell at the current workspace folder.
        from cowork_local.ui.terminal_panel import TerminalPanel

        self.terminal = TerminalPanel()
        self.terminal.set_cwd(self._root)
        self.terminal.expanded.connect(lambda: self.terminal.set_cwd(self._root))
        root_layout.addWidget(self.terminal)

        self.tree.file_selected.connect(self.preview.open_file)
        self.preview.status_message.connect(self.status_message.emit)
        self.ai_panel.status_message.connect(self.status_message.emit)

        on_language_changed(self._retranslate)
        self._retranslate()

    # ---- public API ---------------------------------------------------------
    def set_root(self, path: str) -> None:
        """Đổi thư mục gốc của cả ba widget con.

        ``WorkspaceFileTree`` lặng lẽ từ chối đường dẫn không hợp lệ, nên chỉ lan
        sang khung xem và terminal khi cây thật sự đã nhận.
        """
        self.tree.set_root(path)
        # WorkspaceFileTree silently no-ops on an invalid path (same guard
        # the original single-class _root setter had) — mirror that here by
        # only propagating when the tree actually accepted it.
        if self.tree.root == path:
            self._root = path
            self.preview.set_root(path)
            self.terminal.set_cwd(path)

    def _toggle_ai_panel(self) -> None:
        """Gập/mở panel AI-Edit; mở ra thì báo cho panel biết để nó nạp model lần đầu."""
        show = self.ai_btn.isChecked()
        self.ai_panel.setVisible(show)
        if show:
            self._content_split.setSizes([700, 320])
            self.ai_panel.on_opened()

    def _on_ai_badge_changed(self, suffix: str) -> None:
        """Cập nhật huy hiệu trên nút AI-Edit (số việc đang chờ)."""
        self.ai_btn.setText(tr("folder.ai_edit") + suffix)

    def _retranslate(self) -> None:
        """Chuyển lệnh dịch lại xuống cho cả ba widget con."""
        self.tree.retranslate()
        self.preview.retranslate()
        self.ai_panel.retranslate()
        self.ai_btn.setText(tr("folder.ai_edit"))
        self.ai_btn.setToolTip(tr("folder.ai_edit_tooltip"))


__all__ = ["FolderTab"]
