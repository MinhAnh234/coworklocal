"""Khoá phạm vi quét của màn GraphRAG vào một project.

Tách khỏi ``graph_renderer.py``: file đó đã ở 399/400 dòng — đúng một dòng
trước trần của ``scripts/check_loc.py``, và cổng ấy nói rõ cách duy nhất đúng
khi chạm trần là tách file, không phải nới con số. Khối này là chỗ tự nhiên
để cắt: ba phương thức dưới đây chỉ nói về một việc — project nào đang khoá,
và thư mục nào đi theo nó — còn phần còn lại của renderer lo việc vẽ.

Là mixin chứ không phải đối tượng rời, cùng lý do như ``NavRailMixin``: ba
phương thức này đọc/ghi state của chính renderer (``project_combo``,
``path_edit``, ``_needs_scan``…). Biến thành đối tượng cộng tác thì phải viết
lại từng chỗ ``self.X`` thành ``self.renderer.X`` mà không đổi hành vi gì.
"""
from __future__ import annotations

from cowork_local.i18n import tr


class GraphProjectLockMixin:
    """Ba phương thức khoá-theo-project. Trộn vào ``GraphRenderer``."""

    def _refresh_project_combo(self) -> None:
        """Nạp lại danh sách project vào bộ chọn, giữ nguyên project đang chọn."""
        from cowork_local.core.projects import list_projects

        keep = self._active_project_id
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        self.project_combo.addItem(tr("structure.project_none"), "")
        row_to_select = 0
        for i, p in enumerate(list_projects(), start=1):
            self.project_combo.addItem(p.name, p.project_id)
            if p.project_id == keep:
                row_to_select = i
        self.project_combo.setCurrentIndex(row_to_select)
        self.project_combo.blockSignals(False)

    def set_project(self, project_id: str) -> None:
        """Khoá phạm vi quét vào một project (chuỗi rỗng là bỏ khoá)."""
        pid = project_id or ""
        self._refresh_project_combo()
        target = self.project_combo.findData(pid)
        if target < 0:
            target = 0
        if self.project_combo.currentIndex() == target:
            self._on_project_changed(target)
        else:
            self.project_combo.setCurrentIndex(target)

    def _on_project_changed(self, _idx: int) -> None:
        """Áp trạng thái khoá: đường dẫn chuyển sang chỉ đọc và trỏ vào thư mục"""
        from cowork_local.core.projects import load_project

        pid = self.project_combo.currentData() or ""
        project_changed = pid != self._active_project_id
        self._active_project_id = pid
        locked = bool(pid)
        self.path_edit.setReadOnly(locked)
        self._pick_btn.setEnabled(not locked)
        if locked:
            project = load_project(pid)
            if project is not None:
                self.path_edit.setText(str(project.workspace_dir()))
        # Changing the FOLDER changes what we scan just as much as changing the
        # project does. Keying this off the id alone left the path in the bar
        # updated while the graph in the middle still showed the old folder's
        # nodes: "Đổi" in the Project screen moves the folder, never the id.
        duong_dan = self.path_edit.text().strip()
        doi_muc_tieu = project_changed or duong_dan != self._active_path
        self._active_path = duong_dan
        if doi_muc_tieu:
            self.project_changed.emit()   # GraphQaWidget drops its temp extraction cache
            # Mark it and scan on the next visit rather than now — see
            # auto_scan_and_fit()'s docstring for why.
            self._needs_scan = True
            # ...except when this screen is the one on show. The picker lives HERE,
            # so a user changing project is already looking at the graph: there is
            # no "next visit" to defer to, and they had to press Scan by hand.
            # Deferring still applies when the change came from the Workspace
            # screen while this one is hidden, which is what it was for.
            if self.isVisible() and duong_dan:
                self._needs_scan = False
                self._scan()
