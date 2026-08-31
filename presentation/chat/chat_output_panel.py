"""Khung tệp vào/ra của một lượt chat — R08-T05.

Agent có thể tạo tệp trong lúc chạy. Thay vì bắt người dùng tự đi tìm,
khung này theo dõi thư mục output và hiện tệp mới ngay khi có.

``_is_intermediate_output`` là chỗ lọc: một lượt chạy đẻ ra nhiều tệp
trung gian mà người dùng không quan tâm; hiện hết thì khung thành bãi rác.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget
from ...i18n import tr
from ...ui.icons import icon as app_icon
from ...ui.osutil import open_path
from ...ui.widgets import CollapseStrip


class OutputPanelMixin:
    """Trộn vào ChatPanel."""

    def register_output(self, path: str) -> None:
        """Add a finished file to the Output list — skips intermediate/helper
        files (.scratch/ and, for Cowork, generator scripts) so only real
        deliverables show up. Auto-expands the Files panel if it was collapsed."""
        from ...ui.chat_panel import _is_scratch
        if _is_scratch(path) or self._is_intermediate_output(path):
            return
        # Auto-expand the Files panel if collapsed so the new file is visible.
        if not self._io_widget.isVisible():
            self._set_io_collapsed(False)
        self.output_section.add(path)
        wd = self.workspace_dir()
        if wd:
            # Let the Structure (RAG) graph auto-refresh from this workspace.
            self.output_changed.emit(str(wd))

    def _start_watching(self, directory: Path) -> None:
        """Start watching ``directory`` for new files. When new supported files
        appear, they are automatically loaded into the agent's context on the
        next turn (via ``_augment``)."""
        if self._watched_dir == directory:
            return
        self._stop_watching()
        try:
            directory = directory.resolve()
            if not directory.is_dir():
                return
            self._watched_dir = directory
            self._file_watcher.addPath(str(directory))
            # Snapshot the current set of files so we can detect NEW ones.
            self._known_files = set(
                str(p) for p in directory.iterdir()
                if p.is_file() and not p.name.startswith(".")
                and p.suffix.lower() in self._INPUT_EXTS
            )
        except OSError:
            self._watched_dir = None
            self._known_files = set()

    def _stop_watching(self) -> None:
        """Stop watching the current directory."""
        if self._watched_dir is not None:
            try:
                self._file_watcher.removePath(str(self._watched_dir))
            except OSError:
                pass
            self._watched_dir = None
            self._known_files = set()

    def _on_watched_dir_changed(self, path: str) -> None:
        """Called when the watched directory changes. Debounces rapid changes."""
        if path == str(self._watched_dir):
            self._watch_debounce.start()

    def _process_new_watched_files(self) -> None:
        """Compare current files against the known set and notify about new ones."""
        if self._watched_dir is None:
            return
        try:
            current = set(
                str(p) for p in self._watched_dir.iterdir()
                if p.is_file() and not p.name.startswith(".")
                and p.suffix.lower() in self._INPUT_EXTS
            )
        except OSError:
            return
        new_files = current - self._known_files
        if not new_files:
            self._known_files = current
            return
        self._known_files = current
        # Add new files to the Input section so the user can see them.
        for fp in sorted(new_files):
            self.input_section.add(fp)
        # Emit a status message so the user knows new files were detected.
        names = ", ".join(Path(p).name for p in sorted(new_files))
        self.status_message.emit(
            tr("chatpanel.new_files_detected", names=names, n=len(new_files))
        )

    def _is_intermediate_output(self, path: str) -> bool:
        """Override hook: hide helper/generator files from the Output list."""
        return False

    def on_file_written(self, path: str) -> None:
        """Hook: the agent created/edited a file (shown in the Output box)."""
        self.register_output(path)

    def on_inputs_added(self, paths: List[str]) -> None:
        """Ghi nhận các tệp người dùng vừa đính kèm vào mục "Tệp đầu vào"."""
        for p in paths:
            self.input_section.add(p)

    def _open_io_item(self, path: str) -> None:
        """Mở một tệp trong danh sách vào/ra bằng ứng dụng mặc định."""
        open_path(path)

    def _io_context_menu(self, section, pos) -> None:
        """Right-click menu on a file in the Input/Output lists: Open with the
        OS app, or view + AI-edit it inside the app (FileEditDialog)."""
        item = section.list.itemAt(pos)
        if item is None:
            return
        path = item.data(Qt.UserRole)
        if not path:
            return
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self)
        act_open = menu.addAction(app_icon("link"), tr("chatpanel.menu_open"))
        act_edit = menu.addAction(app_icon("edit"), tr("chatpanel.menu_ai_edit"))
        chosen = menu.exec(section.list.mapToGlobal(pos))
        if chosen is act_open:
            open_path(path)
        elif chosen is act_edit:
            from ...ui.file_edit_dialog import FileEditDialog

            FileEditDialog(self.ctx, path, self).exec()

    def _rebuild_io(self) -> None:
        """Dựng lại cả hai mục vào/ra từ trạng thái hiện tại của hội thoại."""
        self.input_section.clear()
        self.output_section.clear()
        for t in self.turns:
            for p in t.get("inputs", []):
                self.input_section.add(p)
            for p in t.get("outputs", []):
                self.output_section.add(p)

    def _set_io_collapsed(self, collapsed: bool) -> None:
        """Gập/mở khối vào/ra, đổi giữa panel đầy đủ và dải mỏng."""
        self._io_widget.setVisible(not collapsed)
        self._io_strip.setVisible(collapsed)
        strip_w = CollapseStrip.WIDTH + 2
        if collapsed:
            self._io_pane.setMaximumWidth(strip_w)
            self._collapse_split_pane(self._io_pane, strip_w)
        else:
            self._io_pane.setMaximumWidth(16777215)  # QWIDGETSIZE_MAX
            self._restore_split_sizes()

    def _collapse_split_pane(self, pane: QWidget, strip_w: int) -> None:
        """Shrink one splitter pane to ``strip_w`` and hand the freed width to
        the widest remaining pane. Works for any number of panes."""
        sizes = self.center_split.sizes()
        idx = self.center_split.indexOf(pane)
        if not (0 <= idx < len(sizes)):
            return
        diff = sizes[idx] - strip_w
        sizes[idx] = strip_w
        others = [i for i in range(len(sizes)) if i != idx and sizes[i] > 0]
        if others and diff != 0:
            big = max(others, key=lambda i: sizes[i])
            sizes[big] = max(strip_w, sizes[big] + diff)
        self.center_split.setSizes(sizes)

    def _restore_split_sizes(self) -> None:
        """Default expanded layout; panes still collapsed stay thin (max-width)."""
        self.center_split.setSizes([820, 220])

    def _turn_output_dir(self, turn_id: str) -> Optional[Path]:
        """Isolated output folder for one turn (None = share/no files). Overridden
        by tabs that write files, so concurrent turns never clobber each other."""
        return None

    def workspace_dir(self) -> Optional[Path]:
        """Folder shown via the 'open folder' link on messages (None = no link)."""
        return None
