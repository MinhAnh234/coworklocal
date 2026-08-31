"""Thanh điều hướng bên trái — R08-T10.

Bóc từ ``MainWindow``: 18 phương thức dựng và điều khiển thanh rail, cộng danh
sách RECENTS, bộ chọn project, và việc thu gọn về dải icon 54px.

Đây là **mixin**, không phải widget rời — nói thẳng để khỏi hiểu nhầm. Cả 18
phương thức đọc/ghi state của cửa sổ (``self._page_widgets``, ``self.workspace``,
``self.splitter``…). Biến thành đối tượng cộng tác thì phải viết lại từng chỗ
``self.X`` thành ``self.window.X``, tức sửa gần 300 dòng chỉ để đổi cách gọi —
rủi ro cao mà không đổi hành vi. Mixin cho được thứ đang cần: mỗi mảng nằm ở
một file, ai sửa rail thì mở file rail.

Chuyển thành widget thật khi thanh rail cần dùng lại ở cửa sổ khác — hiện chưa.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QMenu, QPushButton, QScrollArea, QSizePolicy, QSplitter, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget
from ...i18n import tr
from .rail_metrics import _NAV_COLLAPSED_WIDTH, _NAV_EXPANDED_WIDTH, _NAV_MAX_CEILING, _NAV_MAX_SHARE, _NAV_MIN_WIDTH, _NavItemDelegate
from ...ui.widgets import tidy_popup




class NavRailMixin:
    """18 phương thức thanh rail. Trộn vào MainWindow."""

    def _build_nav_rail(self, right, rlay) -> None:
        """Dựng toàn bộ thanh rail và ghép với vùng nội dung.

        Bóc khỏi ``MainWindow.__init__`` — 162 dòng dựng rail nằm lẫn giữa
        phần dựng trang và phần khởi động scheduler, nên đọc ``__init__`` là
        phải lội qua cả rail mới tới được thứ mình cần.
        """
        # Left nav rail — ONE FLAT LIST, no accordion. Every screen the user
        # works in is one click away: the Workspace sub-views are listed
        # directly instead of hiding behind an expandable parent. The two
        # occasional admin destinations sit in a second, bottom-pinned list.
        #
        # Monitoring is the exception that keeps its sub-views OUT of the rail:
        # it has eight, which would double the rail's length for screens opened
        # once a week. Its own tab strip is left visible instead (it was hidden
        # while the rail carried its children), so all eight stay reachable.
        self.nav = self._new_nav_tree("navrail")
        self.nav_bottom = self._new_nav_tree("navrailBottom")
        self._nav_building = False       # guards the rebuild → select → rebuild loop
        self.workspace.hide_tab_bar()
        self._rebuild_nav()
        self.workspace.subtabs_changed.connect(self._rebuild_nav)
        for tree in (self.nav, self.nav_bottom):
            tree.currentItemChanged.connect(
                lambda cur, _prev, t=tree: self._on_nav_current(t, cur))
        rlay.addWidget(self.pages, 1)

        # Nav rail wrapper: a small toggle button ABOVE the page list so the
        # whole rail can collapse to icon-only (still fully clickable). Same
        # collapse/expand chevron iconography as every other collapsible panel.
        from ...ui.icons import collapse_left_icon, collapse_right_icon
        from ...ui.icons import icon as _icon
        self._collapse_left_icon = collapse_left_icon
        self._collapse_right_icon = collapse_right_icon
        self._nav_wrap = QWidget()
        self._nav_wrap.setObjectName("navWrap")
        self._nav_width = _NAV_EXPANDED_WIDTH   # remembered across collapses
        self._set_nav_width_range(_NAV_MIN_WIDTH, self._nav_max_width())
        nvl = QVBoxLayout(self._nav_wrap)
        nvl.setContentsMargins(0, 0, 0, 0)
        nvl.setSpacing(0)
        # Small, left-aligned "MENU" button (icon + label) instead of a
        # full-width centered icon — sits flush with the rail's left edge,
        # matching how the nav items themselves align their icon+label.
        self._nav_toggle_btn = QPushButton(tr("app.nav.menu_label"))
        self._nav_toggle_btn.setIcon(collapse_left_icon())
        self._nav_toggle_btn.setObjectName("navMenuBtn")
        self._nav_toggle_btn.setFlat(True)
        self._nav_toggle_btn.setCursor(Qt.PointingHandCursor)
        self._nav_toggle_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._nav_toggle_btn.clicked.connect(self._toggle_nav)
        # Zero left margin: the button's own QSS padding (6px) then lines its
        # 16px icon up with the nav items' icons below (1px list frame + item
        # padding) — same indent level, same icon size as e.g. Dashboard.
        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(0, 8, 10, 8)
        toggle_row.addWidget(self._nav_toggle_btn, 0, Qt.AlignLeft)
        toggle_row.addStretch(1)
        nvl.addLayout(toggle_row)
        # Primary action at the top of the rail, with the project it will land
        # in named right above it. Before, starting a chat in another project
        # meant leaving Cowork → Project tab → click a row → come back.
        self.nav_project = QComboBox()
        self.nav_project.setObjectName("navProjectPick")
        self.nav_project.setToolTip(tr("app.nav.project_pick"))
        self.nav_project.currentIndexChanged.connect(self._on_rail_project_pick)
        tidy_popup(self.nav_project)
        self.nav_new_chat = QPushButton(tr("cowork.new_chat"))
        self.nav_new_chat.setObjectName("navNewChatBtn")
        self.nav_new_chat.setIcon(_icon("plus"))
        self.nav_new_chat.setCursor(Qt.PointingHandCursor)
        self.nav_new_chat.clicked.connect(self._on_rail_new_chat)
        # At 54px the picker cannot show a name, but dropping it altogether left
        # the collapsed rail with no way to change project at all. This stands in
        # for it: same list, same handler, just the folder icon and a tooltip.
        self.nav_project_btn = QToolButton()
        self.nav_project_btn.setObjectName("navProjectPickMini")
        self.nav_project_btn.setIcon(_icon("folder"))
        self.nav_project_btn.setCursor(Qt.PointingHandCursor)
        self.nav_project_btn.setPopupMode(QToolButton.InstantPopup)
        self.nav_project_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.nav_project_btn.setMenu(QMenu(self.nav_project_btn))
        self.nav_project_btn.menu().aboutToShow.connect(self._fill_rail_project_menu)
        self.nav_project_btn.setVisible(False)
        head = QVBoxLayout()
        head.setContentsMargins(6, 0, 6, 6)
        head.setSpacing(6)
        head.addWidget(self.nav_project)
        head.addWidget(self.nav_project_btn)
        head.addWidget(self.nav_new_chat)
        nvl.addLayout(head)
        self.workspace.project_selected.connect(self._sync_rail_project)
        self.workspace.projects_changed.connect(self._sync_rail_project)
        self._syncing_rail_project = False
        self._sync_rail_project()
        # The destinations and RECENTS scroll together; the bottom group, the
        # Settings button and the account row stay pinned below them.
        #
        # Without this the rail simply ran out of room on a short window (a
        # 1280×720 laptop leaves ~570px here): nav and the bottom group have
        # fixed heights, so the squeeze fell entirely on RECENTS, and once that
        # hit zero the layout drew the "GẦN ĐÂY" heading straight over the last
        # nav row.
        self._nav_scroll = QScrollArea()
        self._nav_scroll.setObjectName("navScroll")
        self._nav_scroll.setWidgetResizable(True)
        self._nav_scroll.setFrameShape(QScrollArea.NoFrame)
        self._nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_body = QWidget()
        sv = QVBoxLayout(scroll_body)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(0)
        sv.addWidget(self.nav, 0)
        # RECENTS — the threads of the project named in the picker above, right
        # where Claude puts them. A shortcut only: the full History panel (search,
        # filters, pin, bulk delete, context menu) stays exactly where it is, and
        # "all projects…" at the end of this list opens it.
        self.nav_recents_hdr = QLabel(tr("app.nav.recents"))
        self.nav_recents_hdr.setObjectName("navSectionHdr")
        sv.addWidget(self.nav_recents_hdr)
        self.nav_recents = self._new_nav_tree("navRecents")
        self.nav_recents.itemClicked.connect(self._on_rail_recent)
        sv.addWidget(self.nav_recents, 1)
        # Collapsing hides RECENTS, and with it the only item carrying a stretch
        # factor. A box layout with nothing left to expand centres what remains,
        # so the destinations dropped ~300px down the rail — "thu gọn menu lại
        # ra giữa". This spacer takes the slack instead, and takes none of it
        # while RECENTS is visible (stretch 0 against its 1).
        sv.addStretch(0)
        self._nav_scroll.setWidget(scroll_body)
        nvl.addWidget(self._nav_scroll, 1)
        self._build_rail_bottom(nvl)
        nvl.addWidget(self._account_row)

        self.split = QSplitter(Qt.Horizontal)
        self.split.addWidget(self._nav_wrap)
        self.split.addWidget(right)
        self.split.setStretchFactor(0, 0)
        self.split.setStretchFactor(1, 1)
        self.split.setSizes([_NAV_EXPANDED_WIDTH, 1000])
        self.split.splitterMoved.connect(self._on_split_moved)
        self.setCentralWidget(self.split)

    def _new_nav_tree(self, name: str) -> QTreeWidget:
        """One flat, single-column list. No indentation and no expand arrows —
        every row is a destination, nothing is a container."""
        tree = QTreeWidget()
        tree.setObjectName(name)
        tree.setHeaderHidden(True)
        tree.setIndentation(0)
        tree.setRootIsDecorated(False)
        tree.setUniformRowHeights(True)
        # The column follows the viewport instead of the widest label. Left
        # to size itself it stayed ~100px wide inside the 54px collapsed
        # rail, so a horizontal scrollbar appeared and slid the icons out of
        # the position they hold while the rail is open.
        from PySide6.QtWidgets import QHeaderView
        tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tree.setItemDelegate(_NavItemDelegate(tree))
        return tree

    def _nav_rows(self):
        """(tree, page, sub, label, icon, enabled) for every row, rail order.

        Workspace contributes all five of its sub-views — including the two the
        project gate currently disables — so the rail never changes shape while
        the user is looking at it.
        """
        rows = [(self.nav, self._ROW_WORKSPACE, sub, label, ic, on)
                for label, sub, ic, on in self.workspace.nav_entries()]
        rows.append((self.nav, self._ROW_SCHEDULE, None,
                     tr("app.tab.schedule"), "schedule", True))
        rows.append((self.nav_bottom, self._ROW_DASHBOARD, None,
                     tr("app.tab.dashboard"), "dashboard", True))
        rows.append((self.nav_bottom, self._ROW_MONITORING, None,
                     tr("app.tab.monitoring"), "monitoring", True))
        return rows

    def _rebuild_nav(self, force: bool = False) -> None:
        """Re-fill both lists from _nav_rows(), keeping the current selection.

        Rebuilding changes the current item, which would fire navigation and can
        loop back here via subtabs_changed — hence the guard and the blocked
        signals.
        """
        if self._nav_building:
            return
        spec = self._nav_rows()
        # Rebuilding deletes the QTreeWidgetItems, including the one a signal is
        # currently being delivered for. subtabs_changed fires on every visit to
        # Workspace, so skip the rebuild unless the rows really differ.
        sig = [(label, page, sub, enabled)
               for _t, page, sub, label, _ic, enabled in spec]
        if not force and sig == getattr(self, "_nav_sig", None):
            return
        self._nav_sig = sig
        self._nav_building = True
        try:
            from ...ui.icons import icon as _icon
            keep = self._current_nav_key()
            for tree in (self.nav, self.nav_bottom):
                blocked = tree.blockSignals(True)
                tree.clear()
                tree.blockSignals(blocked)
            for tree, page, sub, label, icon_name, enabled in spec:
                it = QTreeWidgetItem([""] if self._nav_collapsed else [label])
                it.setIcon(0, _icon(icon_name))
                it.setData(0, Qt.UserRole, {"page": page, "sub": sub})
                if not enabled:
                    # Same gate as before, shown instead of hidden: the row stays
                    # in place, greyed, and says why it cannot be opened.
                    it.setDisabled(True)
                    it.setToolTip(0, tr("app.nav.needs_project"))
                elif self._nav_collapsed:
                    it.setToolTip(0, label)
                blocked = tree.blockSignals(True)
                tree.addTopLevelItem(it)
                tree.blockSignals(blocked)
            # Both destination lists are exactly as tall as their rows; the
            # stretch in between belongs to RECENTS.
            for tree in (self.nav, self.nav_bottom):
                n = tree.topLevelItemCount()
                row_h = tree.sizeHintForRow(0) if n else 0
                tree.setFixedHeight(n * row_h + 8)
            if keep:
                self._select_nav_row(*keep)
        finally:
            self._nav_building = False

    def _current_nav_key(self):
        """(page, sub) of the highlighted row, or None."""
        for tree in (self.nav, self.nav_bottom):
            it = tree.currentItem()
            if it is not None and it.isSelected():
                data = it.data(0, Qt.UserRole) or {}
                if "page" in data:
                    return data["page"], data.get("sub")
        return None

    def _select_nav_row(self, page: int, sub) -> None:
        """Highlight the row for (page, sub) without triggering navigation.

        Called both when the user clicks (to keep the two lists mutually
        exclusive) and from _goto, so programmatic navigation moves the
        highlight too — it used to stay behind on whatever was clicked last.
        """
        for tree in (self.nav, self.nav_bottom):
            blocked = tree.blockSignals(True)
            match = None
            for i in range(tree.topLevelItemCount()):
                it = tree.topLevelItem(i)
                data = it.data(0, Qt.UserRole) or {}
                if data.get("page") == page and (
                        data.get("sub") == sub or data.get("sub") is None):
                    match = it
                    break
            if match is not None:
                tree.setCurrentItem(match)
            else:
                tree.setCurrentItem(None)
                tree.clearSelection()
            tree.blockSignals(blocked)

    def _on_nav_current(self, tree: QTreeWidget, item) -> None:
        """A row was picked: clear the other list so only one row looks active."""
        if item is None or self._nav_building:
            return
        data = item.data(0, Qt.UserRole) or {}
        other = self.nav_bottom if tree is self.nav else self.nav
        blocked = other.blockSignals(True)
        other.setCurrentItem(None)
        other.clearSelection()
        other.blockSignals(blocked)
        self._goto(data.get("page", 0), data.get("sub"))

    # ---- rail header: project picker + new chat ------------------------



    # ---- rail RECENTS --------------------------------------------------
    _RAIL_RECENTS = 5




    def _apply_nav_labels(self) -> None:
        """Re-label every row for the current language and collapse state
        (collapsed = icon only, label moves to the tooltip)."""
        # force: collapsing leaves the row spec identical, only the text changes.
        self._rebuild_nav(force=True)
        self._nav_settings_text.setText(tr("app.settings"))
        self._nav_settings_text.setVisible(not self._nav_collapsed)
        self._nav_settings_btn.setToolTip(tr("app.settings"))
        # Collapsed to 54px there is no room for either control's label; the
        # picker would be a stub of a name, so it steps aside entirely and the
        # button keeps just its ＋ icon.
        self.nav_project.setVisible(not self._nav_collapsed)
        self.nav_project_btn.setVisible(self._nav_collapsed)
        self._refresh_rail_recents()
        # Collapsed to 54px only the theme toggle still fits; the rest of the
        # account row would be clipped, so it steps aside (Settings, which opens
        # the same values in a dialog, stays reachable as an icon).
        self.account_lbl.setVisible(not self._nav_collapsed)
        self.language_combo.setVisible(not self._nav_collapsed)
        self.provider_combo.setVisible(not self._nav_collapsed)
        self.nav_new_chat.setText("" if self._nav_collapsed else tr("cowork.new_chat"))
        if self._nav_new_chat_enabled():
            self.nav_new_chat.setToolTip(
                tr("cowork.new_chat") if self._nav_collapsed else "")
        self._sync_rail_project()


    def _nav_max_width(self) -> int:
        """The rail's ceiling for THIS window, as a share of it."""
        return max(_NAV_MIN_WIDTH,
                   min(_NAV_MAX_CEILING, int(self.width() * _NAV_MAX_SHARE)))

    def _set_nav_width_range(self, lo: int, hi: int) -> None:
        """setFixedWidth would leave the splitter handle inert — visible, and
        doing nothing when dragged."""
        self._nav_wrap.setMinimumWidth(lo)
        self._nav_wrap.setMaximumWidth(hi)

    def _on_split_moved(self, _pos: int, _index: int) -> None:
        """Người dùng kéo thanh chia: nhớ lại bề rộng thanh menu để lần mở sau giữ nguyên."""
        if not self._nav_collapsed:
            self._nav_width = max(_NAV_MIN_WIDTH,
                                  min(self._nav_max_width(), self._nav_wrap.width()))

    def _toggle_nav(self) -> None:
        """Thu gọn / mở rộng thanh menu, nhớ bề rộng trước khi thu để khôi phục đúng."""
        if not self._nav_collapsed:
            self._nav_width = max(_NAV_MIN_WIDTH,
                                  min(self._nav_max_width(), self._nav_wrap.width()))
        self._nav_collapsed = not self._nav_collapsed
        if self._nav_collapsed:
            width = _NAV_COLLAPSED_WIDTH
            self._set_nav_width_range(width, width)
        else:
            width = self._nav_width
            self._set_nav_width_range(_NAV_MIN_WIDTH, self._nav_max_width())
        self._apply_nav_labels()
        # Same chevron convention as every other collapsible panel: right-
        # pointing (fill-right) means "click to expand", left means "collapse".
        self._nav_toggle_btn.setIcon(
            self._collapse_right_icon() if self._nav_collapsed else self._collapse_left_icon())
        # Collapsed rail is icon-only (54px) — the "MENU" label wouldn't fit
        # next to the icon, same rule the nav items themselves follow.
        self._nav_toggle_btn.setText("" if self._nav_collapsed else tr("app.nav.menu_label"))
        self._nav_toggle_btn.setToolTip(
            tr("app.nav.expand_tooltip") if self._nav_collapsed else tr("app.nav.collapse_tooltip"))
        # Give/reclaim the width difference to the main content pane.
        sizes = self.split.sizes()
        if len(sizes) == 2:
            diff = sizes[0] - width
            sizes[0] = width
            sizes[1] = max(1, sizes[1] + diff)
            self.split.setSizes(sizes)
