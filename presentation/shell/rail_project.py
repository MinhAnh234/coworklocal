"""Bộ chọn project và danh sách RECENTS trên thanh rail — R08-T10.

Tách khỏi ``nav_rail.py``: thanh rail có hai phần đời sống khác hẳn nhau.

Phần điểm đến (Dashboard, Workspace, Giám sát…) là **tĩnh** — dựng một lần,
đổi khi đổi ngôn ngữ. Phần này thì **động**: đổi mỗi lần người dùng chọn
project khác, mỗi lần một cuộc trò chuyện được tạo hay kết thúc.

Trộn chung một file thì mỗi lần sửa danh sách gần đây lại phải cuộn qua toàn
bộ phần dựng rail. Cùng kiểu mixin, xem ghi chú ở đầu ``nav_rail.py``.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from ...i18n import tr
from ...ui.widgets import tidy_popup
from ...theme import current_palette



class RailProjectMixin:
    """Bộ chọn project + RECENTS. Trộn vào MainWindow."""

    def _sync_rail_project(self, *_a) -> None:
        """Mirror the workspace's project list/selection into the rail picker.

        One-way on purpose: the project list stays the source of truth, this is
        only a second place to see and change it.
        """
        if self._syncing_rail_project:
            return
        self._syncing_rail_project = True
        try:
            choices = self.workspace.project_choices()
            current = self.workspace.selected_project_id()
            self.nav_project.clear()
            for name, pid in choices:
                self.nav_project.addItem(f"📁 {name}", pid)
            if not choices:
                # No project yet: say so, and say what to do about it, instead of
                # leaving an empty box and a button that silently does nothing.
                self.nav_project.addItem(tr("app.nav.no_project"), "")
            idx = self.nav_project.findData(current)
            if idx >= 0:
                self.nav_project.setCurrentIndex(idx)
            has = bool(choices)
            tidy_popup(self.nav_project)
            self.nav_project.setEnabled(has)
            self.nav_project_btn.setEnabled(has)
            self.nav_project_btn.setToolTip(
                self.nav_project.currentText().replace("📁 ", "")
                if has else tr("app.nav.create_project_first"))
            self.nav_new_chat.setEnabled(has)
            self.nav_new_chat.setToolTip(
                "" if has else tr("app.nav.create_project_first"))
        finally:
            self._syncing_rail_project = False
    def _fill_rail_project_menu(self) -> None:
        """Mirror the picker's items. Choosing one moves the picker, which runs
        _on_rail_project_pick — the collapsed rail adds no second code path."""
        menu = self.nav_project_btn.menu()
        menu.clear()
        for i in range(self.nav_project.count()):
            act = menu.addAction(self.nav_project.itemText(i))
            act.setCheckable(True)
            act.setChecked(i == self.nav_project.currentIndex())
            act.triggered.connect(
                lambda _checked=False, row=i: self.nav_project.setCurrentIndex(row))
    def _on_rail_project_pick(self, _idx: int) -> None:
        """Chọn project ở thanh menu: chuyển workspace sang project đó.

        Cờ ``_syncing_rail_project`` chặn vòng lặp khi chính workspace vừa đặt lại
        bộ chọn này.
        """
        if self._syncing_rail_project:
            return
        pid = self.nav_project.currentData()
        if pid:
            self.workspace.choose_project(pid)
    def _refresh_rail_recents(self) -> None:
        """Re-fill the rail's recents from the active project's history."""
        from ...ui.icons import DOT_BLUE, dot_icon
        from ...ui.icons import icon as _icon

        tree = self.nav_recents
        blocked = tree.blockSignals(True)
        tree.clear()
        running = self._running_session_ids()
        threads = self.workspace.recent_threads(self._RAIL_RECENTS)
        for t in threads:
            it = QTreeWidgetItem([t["title"]])
            it.setToolTip(0, t["title"])
            if t["session_id"] in running:
                it.setIcon(0, dot_icon(DOT_BLUE))       # same marker as History
            elif t["pinned"]:
                it.setIcon(0, _icon("pin"))
            it.setData(0, Qt.UserRole, {"path": t["path"], "kind": t["kind"]})
            tree.addTopLevelItem(it)
        if not threads:
            it = QTreeWidgetItem([tr("sidebar.empty")])
            it.setDisabled(True)
            tree.addTopLevelItem(it)
        # The way back to everything the rail cannot show — styled as a link
        # (italic, accent-colored) so it reads as "go elsewhere", not another row.
        more = QTreeWidgetItem([tr("app.nav.all_projects")])
        more.setData(0, Qt.UserRole, {"all": True})
        more_font = more.font(0)
        more_font.setItalic(True)
        more.setFont(0, more_font)
        more.setForeground(0, QColor(current_palette().accent))
        tree.addTopLevelItem(more)
        tree.blockSignals(blocked)
        self.nav_recents_hdr.setVisible(not self._nav_collapsed)
        self.nav_recents.setVisible(not self._nav_collapsed)
    def goto_all_projects(self) -> None:
        """Mở khung "Tất cả project…": Workspace ▸ Cowork, bảng lịch sử bung ra.

        Phải đi qua ``_goto``, không được gọi thẳng ``show_history_pane()``:
        ``_goto`` là chỗ duy nhất dời vệt sáng trên thanh menu theo nội dung.
        Gọi tắt thì nội dung sang Cowork còn vệt sáng ở lại Project — và vì
        ``QTreeWidget`` không phát ``currentItemChanged`` khi bấm lại đúng dòng
        đang chọn, bấm "Project" sẽ KHÔNG có tác dụng gì cho tới khi người dùng
        bấm sang mục khác rồi bấm về.

        Gom vào một hàm vì có hai đường vào: link "Tất cả project…" ở mục GẦN
        ĐÂY, và màn hình mặc định lúc mở app.
        """
        sub = self.workspace._cowork_tab_idx
        # Chua chon project thi cong project dang giu sub-tab Cowork dong.
        # show_history_pane() mo no bang cua sau, bo qua cong — the la noi dung
        # o Cowork trong khi ca cong lan vet sang deu noi la Project. Man hinh
        # dung cho nguoi chua co project chinh la man quan ly project.
        if sub < 0 or not self.workspace.subtab_available(sub):
            self._goto(self._ROW_WORKSPACE, self.workspace._project_tab_idx)
            return
        self._goto(self._ROW_WORKSPACE, sub)
        self.workspace.show_history_pane()
        # Bang lich su duoc nhung trong sub-tab Cowork cua MOT project, nen
        # WorkspaceTab._bind_project da dat set_project_filter(pid) — no chi hien
        # thread cua project dang chon. Vao day bang link "Tat ca project…" ma van
        # con bo loc thi nguoi dung tao 5 project chi thay 1. Xoa bo loc SAU
        # show_history_pane(), vi ham do di qua duong doi sub-tab.
        self.sidebar.set_project_filter("")

    def _on_rail_recent(self, item, _col: int = 0) -> None:
        """Bấm một dòng trong mục GẦN ĐÂY: mở hội thoại đó, hoặc mở khung "Tất cả project…"."""
        data = item.data(0, Qt.UserRole) or {}
        if data.get("all"):
            self.goto_all_projects()
            return
        path = data.get("path")
        if path:
            self._goto(self._ROW_WORKSPACE, self.workspace._cowork_tab_idx)
            self.workspace.open_thread(path, data.get("kind", "cowork"))
    def _on_rail_new_chat(self) -> None:
        """Start a new chat, from any screen.

        Same call the Cowork toolbar button makes — that button stays exactly
        where it was; this is a second entry point, not a replacement.
        """
        self._goto(self._ROW_WORKSPACE, None)
        self.workspace.start_new_chat()
        self._select_nav_row(self._ROW_WORKSPACE, self.workspace.current_subtab())
    def _nav_new_chat_enabled(self) -> bool:
        """Nút "chat mới" chỉ bật khi đã có ít nhất một project."""
        return bool(self.workspace.project_choices())
