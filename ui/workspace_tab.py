"""Workspace screen — the app's home. Manages Projects (Claude-Projects style)
AND hosts, per selected project, the **Cowork** chat and **GraphRAG** views as
sub-tabs, all confined to that project's sandbox.

Left: the list of projects (create / delete, collapsible). Right: a tab strip
for the selected project —

* **Cowork** — the chat (with its per-project History sidebar).
* **GraphRAG** — the knowledge graph, locked to the project's sandbox.
* **Project** — name, description, shared **instructions** (injected into every
  chat of the project), its sandbox **workspace folder**, and the project's
  conversation **threads**.

The Cowork/GraphRAG widgets are created by the main window and handed in so the
whole app shares one instance of each; when they are not provided (e.g. unit
tests that exercise only project management) the screen still works as a plain
project manager.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPlainTextEdit, QPushButton, QSplitter, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ..i18n import on_language_changed, tr
from ..presentation.workspace.project_editing import ProjectEditingMixin, ProjectRow
from ..state import AppContext
from .icons import collapse_left_icon, icon
from .osutil import open_folder
from .widgets import CollapseStrip


class WorkspaceTab(ProjectEditingMixin, QWidget):
    """Trang chủ Workspace: cột project, cột lịch sử, và 5 sub-tab
    (Dự án · Cowork · Co4E · Thư mục · GraphRAG).

    Đây là chỗ CHỐT project đang hoạt động: :meth:`_bind_project` đặt
    ``ctx.active_project_id``, và mọi chế độ theo-workspace (định tuyến, tự
    chạy) đều phân giải theo giá trị đó.
    """
    status_message = Signal(str)
    open_chat = Signal(str, dict)      # kind, conversation — open a thread in Cowork
    new_chat = Signal(str)             # project_id — start a new thread in this project
    projects_changed = Signal()        # created/edited/deleted → History regroups
    subtabs_changed = Signal()         # visible sub-tabs changed → left-nav children refresh
    project_selected = Signal(str)     # project_id — the rail's picker follows this

    # ---- nav integration: the sub-tabs are driven from the left nav rail -----
    def nav_subtabs(self):
        """(label, index, icon_name) for each VISIBLE sub-tab — the left nav lists
        these as children under 'Workspaces'. Icons are keyed by tab index (not
        label) so they're correct in every language."""
        icons = {self._project_tab_idx: "folder", self._cowork_tab_idx: "chat",
                 self._co4e_tab_idx: "flow", self._folder_tab_idx: "folder",
                 self._graphrag_tab_idx: "graph"}
        return [(self.tabs.tabText(i), i, icons.get(i, "chevron-right"))
                for i in range(self.tabs.count()) if self.tabs.isTabVisible(i)]

    def nav_entries(self):
        """(label, index, icon_name, enabled) for EVERY sub-tab, hidden ones
        included.

        The rail lists all five all the time and greys out the ones the project
        gate is currently closing (Cowork, GraphRAG) instead of removing them —
        same gate, shown rather than hidden, so the menu stops changing shape
        under the user's hand. See nav_subtabs() for the visible-only view.
        """
        icons = {self._project_tab_idx: "folder", self._cowork_tab_idx: "chat",
                 self._co4e_tab_idx: "flow", self._folder_tab_idx: "folder",
                 self._graphrag_tab_idx: "graph"}
        return [(self.tabs.tabText(i), i, icons.get(i, "chevron-right"),
                 self.tabs.isTabVisible(i))
                for i in range(self.tabs.count())]

    def subtab_available(self, index: int) -> bool:
        """False while the project gate is holding this sub-tab shut.

        The rail greys those rows out, but that only guards the rail. This lets
        every other route ask the same question of the same state.
        """
        return bool(0 <= index < self.tabs.count() and self.tabs.isTabVisible(index))

    def select_subtab(self, index: int) -> None:
        """Chuyển sang sub-tab thứ ``index`` (thanh menu bên trái gọi vào đây)."""
        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)

    def current_subtab(self) -> int:
        """Chỉ số sub-tab đang mở."""
        return self.tabs.currentIndex()

    def hide_tab_bar(self) -> None:
        """Hide the in-content tab strip (the nav rail drives the sub-tabs now),
        so the content area is as large as possible."""
        self.tabs.tabBar().hide()

    def __init__(self, ctx: AppContext, cowork=None, structure=None, sidebar=None):
        """Màn Workspace: danh sách dự án bên trái, các tab con của dự án bên phải.

        Cột lịch sử mở ở trạng thái gập cho tới khi người dùng chủ động mở ra, đúng
        như bản vẽ bố cục màn này.
        """
        super().__init__()
        self.ctx = ctx
        self._current_id = ""
        # True once the user asks for the full History panel; until then Cowork
        # opens with it folded, as the drawing lays the screen out.
        self._history_opened = False
        # Shared widgets embedded as per-project sub-tabs (None in unit tests
        # that only drive project management).
        self._cowork = cowork
        self._structure = structure
        self._sidebar = sidebar

        root = QVBoxLayout(self)
        # Title row — the drawing puts "+ Project mới" up here beside the title,
        # not at the foot of the project list where it read as belonging to the
        # list's own controls.
        self._header = QLabel()
        self._header.setStyleSheet("font-weight:700; font-size:15px;")
        self._new_btn = QPushButton()
        self._new_btn.setIcon(icon("plus"))
        self._new_btn.setObjectName("primary")
        self._new_btn.clicked.connect(self._create)
        title_row = QHBoxLayout()
        title_row.addWidget(self._header)
        title_row.addStretch(1)
        title_row.addWidget(self._new_btn)
        root.addLayout(title_row)
        self._hint = QLabel()
        self._hint.setObjectName("hint")
        self._hint.setWordWrap(True)
        root.addWidget(self._hint)

        self._split = QSplitter(Qt.Horizontal)
        root.addWidget(self._split, 1)

        # ---- left: project list (collapsible — same chevron/strip pattern
        # as History and the GraphRAG Agent panel) ---------------------------
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        left_hdr = QHBoxLayout()
        self._projects_hdr = QLabel()
        self._projects_hdr.setObjectName("navSectionHdr")
        left_hdr.addWidget(self._projects_hdr)
        self._proj_collapse_btn = QPushButton()
        self._proj_collapse_btn.setIcon(collapse_left_icon())
        self._proj_collapse_btn.setFixedWidth(28)
        self._proj_collapse_btn.clicked.connect(lambda: self._set_projects_collapsed(True))
        left_hdr.addWidget(self._proj_collapse_btn)
        left_hdr.addStretch(1)
        ll.addLayout(left_hdr)
        self.project_list = QListWidget()
        self.project_list.currentItemChanged.connect(self._on_select)
        ll.addWidget(self.project_list, 1)
        btns = QHBoxLayout()
        # Delete stays under the list it acts on. The drawing does not show it,
        # but it does not show it moved either, and dropping a control is not
        # something a layout pass gets to do.
        self._del_btn = QPushButton()
        self._del_btn.setIcon(icon("trash"))
        self._del_btn.clicked.connect(self._delete)
        btns.addWidget(self._del_btn, 1)
        ll.addLayout(btns)
        self._projects_panel = left

        # Thin strip shown in place of the project list when collapsed —
        # clicking it re-expands (identical affordance to History's).
        self._projects_strip = CollapseStrip(tr("workspace.expand_projects_tooltip"), expand_dir="right")
        self._projects_strip.clicked.connect(lambda: self._set_projects_collapsed(False))
        self._projects_strip.setVisible(False)
        self._projects_pane = QWidget()
        ppl = QHBoxLayout(self._projects_pane)
        ppl.setContentsMargins(0, 0, 0, 0)
        ppl.setSpacing(0)
        ppl.addWidget(self._projects_strip)
        ppl.addWidget(left, 1)
        self._split.addWidget(self._projects_pane)

        # ---- right: per-project tabs (Project / Cowork / GraphRAG) -----------
        # Project comes FIRST; Cowork + GraphRAG only appear once a project is
        # actually selected (see _update_tab_visibility).
        self.tabs = QTabWidget()
        # A QTabWidget's minimum width is the MAXIMUM over every page, hidden
        # ones included — so Co4E (the widest, ~1180px) was setting the floor for
        # Project and Cowork as well, and through them for the whole window,
        # which then refused to be smaller than 1453px on any screen. An explicit
        # minimum overrides that: each page still gets whatever width is going,
        # and the pages that are not on screen no longer vote.
        self.tabs.setMinimumWidth(560)
        self._project_tab_idx = self.tabs.addTab(self._build_project_tab(), tr("workspace.tab_project"))
        self._cowork_tab_idx = -1
        self._graphrag_tab_idx = -1

        if self._cowork is not None:
            cowork_page = QWidget()
            cpl = QVBoxLayout(cowork_page)
            cpl.setContentsMargins(0, 0, 0, 0)
            cpl.addWidget(self._cowork)
            self._cowork_tab_idx = self.tabs.addTab(cowork_page, tr("workspace.tab_cowork"))

        # Co4E — node-graph workflow studio (built-in flows, agents, skills, a
        # runner + chat). Always available (not project-gated): its workflows
        # live globally under ~/.cowork_local/co4e, not inside one project.
        # Placed BEFORE GraphRAG in the tab order (user request).
        from .co4e_tab import Co4ETab

        self._co4e = Co4ETab(self.ctx)
        self._co4e_tab_idx = self.tabs.addTab(self._co4e, tr("workspace.tab_co4e"))
        self.tabs.setTabToolTip(self._co4e_tab_idx, tr("workspace.tab_co4e_tooltip"))

        # Folder — a two-pane file explorer (tree + view/edit) placed right below
        # Co4E. Always available (not project-gated); its root follows the
        # selected project's workspace folder when one is chosen.
        from ..presentation.folder.folder_tab import FolderTab

        self._folder = FolderTab(self.ctx, cowork=self._cowork)
        self._folder.status_message.connect(self.status_message)
        self._folder_tab_idx = self.tabs.addTab(self._folder, tr("workspace.tab_folder"))

        if self._structure is not None:
            self._graphrag_tab_idx = self.tabs.addTab(self._structure, tr("workspace.tab_graphrag"))

        self.tabs.currentChanged.connect(self._on_tab_changed)

        # History lives in its own pane of the OUTER splitter (not nested
        # inside the Cowork tab page) so it stays visible across Cowork AND
        # GraphRAG, instead of disappearing whenever GraphRAG is the active
        # sub-tab (QTabWidget only shows the current page's widget).
        if self._sidebar is not None:
            self._split.addWidget(self._sidebar)
            self._wire_sidebar()
        self._split.addWidget(self.tabs)
        self._split.setStretchFactor(0, 0)
        if self._sidebar is not None:
            self._split.setStretchFactor(1, 0)
            self._split.setStretchFactor(2, 1)
            self._split.setSizes([260, 240, 800])
        else:
            self._split.setStretchFactor(1, 1)
            self._split.setSizes([260, 900])
        self._apply_pane_visibility()

        self.refresh()
        self.install_project_editing()
        on_language_changed(self._retranslate)
        self._retranslate()

    # ---- project settings tab -------------------------------------------
    def _build_project_tab(self) -> QWidget:
        """Dựng sub-tab "Dự án": tên, mô tả, chỉ dẫn chung và thư mục sandbox."""
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 4, 4, 4)

        self.name_edit = QLineEdit()
        self.desc_edit = QLineEdit()
        self._name_lbl = QLabel()
        self._desc_lbl = QLabel()
        rl.addWidget(self._name_lbl)
        rl.addWidget(self.name_edit)
        rl.addWidget(self._desc_lbl)
        rl.addWidget(self.desc_edit)

        self._instr_lbl = QLabel()
        self.instr_edit = QPlainTextEdit()
        self.instr_edit.setMaximumHeight(120)
        rl.addWidget(self._instr_lbl)
        rl.addWidget(self.instr_edit)

        self._folder_hdr = QLabel()
        rl.addWidget(self._folder_hdr)
        folder_row = QHBoxLayout()
        # The drawing shows the path in a field, not as grey caption text. A
        # read-only line edit looks like one and, unlike a label, lets the path
        # be selected and copied.
        self.folder_lbl = QLineEdit()
        self.folder_lbl.setReadOnly(True)
        self._browse_btn = QPushButton()
        self._browse_btn.setIcon(icon("folder"))
        self._browse_btn.clicked.connect(self._pick_folder)
        self._open_btn = QPushButton()
        self._open_btn.setIcon(icon("upload"))
        self._open_btn.clicked.connect(self._open_workspace)
        folder_row.addWidget(self.folder_lbl, 1)
        folder_row.addWidget(self._browse_btn)
        folder_row.addWidget(self._open_btn)
        rl.addLayout(folder_row)

        # DF-007 — an ALTERNATIVE way to set output_dir: browse OneDrive/
        # SharePoint via Graph API and download a local mirror instead of
        # picking an already-local folder. output_dir still always ends up a
        # real local path (see Project.cloud_source) — nothing downstream
        # (run_command/read_file/...) needs to know the difference.
        cloud_row = QHBoxLayout()
        self._cloud_pick_btn = QPushButton()
        self._cloud_pick_btn.setIcon(icon("cloud"))
        self._cloud_pick_btn.clicked.connect(self._pick_cloud_folder)
        self._cloud_sync_btn = QPushButton()
        self._cloud_sync_btn.setIcon(icon("refresh"))
        self._cloud_sync_btn.clicked.connect(self._sync_cloud_folder)
        self._cloud_sync_btn.hide()
        cloud_row.addWidget(self._cloud_pick_btn)
        cloud_row.addWidget(self._cloud_sync_btn)
        cloud_row.addStretch(1)
        rl.addLayout(cloud_row)
        self._cloud_badge_lbl = QLabel()
        self._cloud_badge_lbl.setWordWrap(True)
        self._cloud_badge_lbl.hide()
        rl.addWidget(self._cloud_badge_lbl)

        rl.addStretch(1)      # the drawing floats Lưu project at the bottom
        save_row = QHBoxLayout()
        self._save_btn = QPushButton()
        self._save_btn.setIcon(icon("save"))
        self._save_btn.setObjectName("primary")
        self._save_btn.clicked.connect(self._save)
        save_row.addStretch(1)
        save_row.addWidget(self._save_btn)
        rl.addLayout(save_row)

        # The per-project conversation-threads list ("group chat") was removed
        # from here — chats live in the History sidebar + the Cowork tab. Keep
        # the settings compact at the top with a stretch below.
        rl.addStretch(1)
        return right

    # ---- embedded sidebar (History inside the Cowork tab) ---------------
    def _wire_sidebar(self) -> None:
        """Nối các tín hiệu của cột lịch sử vào màn Workspace."""
        sb = self._sidebar
        sb.open_chat.connect(self._on_sidebar_open)
        sb.new_chat.connect(self._on_sidebar_new)
        sb.collapse_requested.connect(lambda: self._on_history_fold(True))
        sb.expand_requested.connect(lambda: self._on_history_fold(False))
        sb.refresh_requested.connect(self._on_sidebar_refresh)
        sb.history_changed.connect(self._reload_threads)

    def _on_history_fold(self, collapsed: bool) -> None:
        """Its chevron closes the panel away, back to the drawn layout."""
        self._history_opened = not collapsed
        if collapsed:
            self._sidebar.setVisible(False)
            self._apply_pane_visibility()
        else:
            self._set_sidebar_collapsed(False)

    def _set_sidebar_collapsed(self, collapsed: bool) -> None:
        """Collapse/expand History sidebar and redistribute splitter space so
        the Cowork chat area fills the freed width (same pattern as
        _set_projects_collapsed)."""
        sb = self._sidebar
        sb.set_collapsed(collapsed)
        strip_w = CollapseStrip.WIDTH + 2
        if sb is None:
            return
        # Find sidebar index in splitter
        idx = self._split.indexOf(sb)
        if not (0 <= idx < self._split.count()):
            return
        sizes = self._split.sizes()
        if collapsed:
            freed = sizes[idx] - strip_w
            sizes[idx] = strip_w
        else:
            freed = 240 - sizes[idx]
            sizes[idx] = 240
        # Give freed width to the LAST pane (tabs/Cowork area)
        if freed != 0 and len(sizes) > 1:
            sizes[-1] = max(1, sizes[-1] + freed)
        self._split.setSizes(sizes)

    def _on_sidebar_open(self, kind: str, conv: dict) -> None:
        """Mở một hội thoại từ cột lịch sử, kèm chuyển sang đúng project của nó.

        Id "default" (hội thoại cũ chưa gắn project) CỐ Ý không được coi là một
        project thật — Cowork xử lý riêng nó như phạm vi toàn cục, không có tri thức
        project nào.
        """
        pid = conv.get("project_id", "") or "default"
        # The legacy "default"/no-project id is intentionally not a real
        # Project row (Cowork itself special-cases it as global/no-knowledge —
        # see chat_agent.py), so it's fine to open with nothing selected. But a
        # genuinely deleted project id must NOT force the Cowork tab open,
        # since _update_tab_visibility never ran for it — that would show the
        # Cowork page while the tab strip still says "no project selected".
        if pid not in ("", "default") and not self._select_project_row(pid):
            self.status_message.emit(tr("workspace.conversation_project_missing"))
            return
        if self._cowork is not None:
            self._cowork.load_conversation(conv)
        self._show_cowork_tab()
        self.open_chat.emit(kind or "cowork", conv)

    def _on_sidebar_new(self, kind: str) -> None:
        """Bấm "chat mới" ở cột lịch sử: mở hội thoại mới rồi nhảy sang tab Cowork."""
        if self._cowork is not None:
            self._cowork.new_session()
        self._show_cowork_tab()

    def _on_sidebar_refresh(self) -> None:
        """Cột lịch sử yêu cầu làm mới: cập nhật lại trạng thái Cowork và danh sách."""
        if self._cowork is not None:
            self._cowork.refresh_status()
        if self._sidebar is not None:
            self._sidebar.refresh()

    def _show_cowork_tab(self) -> None:
        """Chuyển sang sub-tab Cowork nếu nó đang hiện."""
        if self._cowork_tab_idx >= 0:
            self.tabs.setCurrentIndex(self._cowork_tab_idx)

    def _on_tab_changed(self, idx: int) -> None:
        # Entering GraphRAG builds its (lazy) WebEngine view and scans the
        # project's sandbox; entering it is what keeps startup RAM low.
        """Đổi sub-tab: vào GraphRAG mới dựng khung WebEngine và quét sandbox.

        Dựng lười như vậy chính là thứ giữ cho RAM lúc khởi động ở mức thấp.
        """
        if idx == self._graphrag_tab_idx and self._structure is not None:
            self._structure.auto_scan_and_fit()
        self._apply_pane_visibility()

    def _apply_pane_visibility(self) -> None:
        """Which side panes accompany each sub-tab:

            Project  → project list ✓   History ✗
            Cowork   → project list ✗   History ✓
            GraphRAG → project list ✗   History ✗

        Every page other than Project/Cowork (GraphRAG) gets the full width;
        switching projects is done from the Project tab (the list there is
        the app's only project picker)."""
        idx = self.tabs.currentIndex()
        on_project = idx == self._project_tab_idx
        on_cowork = self._cowork_tab_idx >= 0 and idx == self._cowork_tab_idx
        self._projects_pane.setVisible(on_project)
        # "Workspace — Projects" and its three-line explanation describe the
        # PROJECT screen, but were drawn above every sub-tab — ~90px of vertical
        # space taken from Co4E's canvas and Folder's tree on every laptop
        # screen. Shown where they apply; the text itself is unchanged.
        self._header.setVisible(on_project)
        # The title row sits above the sub-tabs, so everything on it has to
        # follow the same rule the title does — moving + Project mới up here put
        # it in the corner of Cowork, Co4E, Folder and GraphRAG as well.
        self._new_btn.setVisible(on_project)
        # ...and the explanation only while there is nothing to explain against:
        # the drawing heads a populated screen with the title alone.
        self._hint.setVisible(on_project and self.project_list.count() == 0)
        narrow = getattr(self, "_is_narrow", False)
        if self._sidebar is not None:
            # Cowork is two columns in the drawing — transcript and files — with
            # no history pane and no strip where one used to be. The relocation
            # table is explicit: History moves to Sidebar ▸ RECENTS, "giữ, dễ
            # tới hơn". So the panel is not on this screen at all until asked
            # for: "Tất cả project…" in RECENTS brings it in, since search,
            # filters, pin, rename and multi-select delete live only there.
            self._sidebar.setVisible(on_cowork and self._history_opened)
            if on_cowork and self._history_opened:
                self._sidebar.set_collapsed(False)
        # QSplitter ignores hidden panes, but the freed width isn't handed to
        # the remaining panes deterministically — set explicit sizes after any
        # pane toggle (same lesson as _set_projects_collapsed).
        total = sum(self._split.sizes()) or 1300
        # A collapsed pane must be given the STRIP width here, not its open
        # width: this ran after every tab change and handed History a flat
        # 240px even while it was folded to an 18px strip, leaving ~220px of
        # dead space beside the chat on a small screen.
        strip_w = CollapseStrip.WIDTH + 2
        proj_w = 0
        if on_project:
            proj_w = strip_w if self._projects_strip.isVisible() else 260
        hist_w = 0
        if on_cowork and self._sidebar is not None:
            hist_w = strip_w if self._sidebar.is_collapsed() else 240
        if self._split.count() >= 3:
            self._split.setSizes([proj_w, hist_w, max(1, total - proj_w - hist_w)])
        else:
            self._split.setSizes([proj_w, max(1, total - proj_w)])

    # ---- i18n ------------------------------------------------------------
    def _retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn cho tiêu đề, gợi ý và tên các sub-tab."""
        self._header.setText(tr("workspace.header"))
        self._hint.setText(tr("workspace.hint"))
        self._projects_hdr.setText(tr("workspace.projects_heading").upper())
        self._folder_hdr.setText(tr("workspace.folder_label"))
        self._new_btn.setText(tr("workspace.new_project"))
        self._del_btn.setText(tr("workspace.delete"))
        self._name_lbl.setText(tr("workspace.name"))
        self._desc_lbl.setText(tr("workspace.description"))
        self._instr_lbl.setText(tr("workspace.instructions"))
        self.instr_edit.setPlaceholderText(tr("workspace.instructions_placeholder"))
        self._browse_btn.setText(tr("workspace.browse"))
        self._browse_btn.setToolTip(tr("workspace.browse_tooltip"))
        self._open_btn.setText(tr("workspace.open_folder"))
        self._cloud_pick_btn.setText(tr("workspace.cloud_pick"))
        self._cloud_sync_btn.setText(tr("workspace.cloud_sync"))
        self._refresh_cloud_badge()
        self._save_btn.setText(tr("workspace.save"))
        self.retranslate_project_rows()
        self._proj_collapse_btn.setToolTip(tr("workspace.collapse_projects_tooltip"))
        self._projects_strip.setToolTip(tr("workspace.expand_projects_tooltip"))
        self.tabs.setTabText(self._project_tab_idx, tr("workspace.tab_project"))
        if self._cowork_tab_idx >= 0:
            self.tabs.setTabText(self._cowork_tab_idx, tr("workspace.tab_cowork"))
        if self._co4e_tab_idx >= 0:
            self.tabs.setTabText(self._co4e_tab_idx, tr("workspace.tab_co4e"))
            self.tabs.setTabToolTip(self._co4e_tab_idx, tr("workspace.tab_co4e_tooltip"))
        if getattr(self, "_folder_tab_idx", -1) >= 0:
            self.tabs.setTabText(self._folder_tab_idx, tr("workspace.tab_folder"))
        if self._graphrag_tab_idx >= 0:
            self.tabs.setTabText(self._graphrag_tab_idx, tr("workspace.tab_graphrag"))

    # ---- project list collapse (same pattern as History / GraphRAG Agent panel) --
    # Below this window width the three panes (projects 260 + history 240 +
    # the sub-page, which alone wants ~1245px on Cowork) no longer fit and Qt
    # clips them instead of shrinking. Measured with tools/check_responsive.py.
    _NARROW = 1500

    def showEvent(self, e):  # noqa: N802 - Qt override
        """Lần hiện đầu tiên mới gắn bộ canh bố cục hẹp — trước đó chưa biết bề rộng thật."""
        super().showEvent(e)
        if getattr(self, "_narrow", None) is None:
            from .widgets import narrow_guard
            self._narrow = narrow_guard(self, self._NARROW, self._apply_narrow)
        self._narrow.attach()

    def _apply_narrow(self, narrow: bool) -> None:
        """Fold the two side panes on a small screen so the sub-page keeps its
        width; unfold them when the window grows back.

        Nothing becomes unreachable: both panes leave their usual collapse strip
        behind, and the project picker + RECENTS in the rail cover the same
        ground while they are folded.
        """
        self._is_narrow = narrow
        self._set_projects_collapsed(narrow)
        if self._sidebar is not None:
            self._set_sidebar_collapsed(narrow)
        # The chat's Files pane (~300px) is the other thing that pushes Cowork
        # past the window; it has the same collapse strip to come back from.
        if self._cowork is not None and hasattr(self._cowork, "_set_io_collapsed"):
            self._cowork._set_io_collapsed(narrow)
        if not narrow:
            # Re-apply the per-tab rules the two calls above just overrode.
            self._apply_pane_visibility()

    def _set_projects_collapsed(self, collapsed: bool) -> None:
        """Gập/mở cột project, đổi giữa panel đầy đủ và dải mỏng."""
        strip_w = CollapseStrip.WIDTH + 2
        self._projects_panel.setVisible(not collapsed)
        self._projects_strip.setVisible(collapsed)
        if collapsed:
            self._projects_pane.setMaximumWidth(strip_w)
            # A maximumWidth constraint alone doesn't make QSplitter hand the
            # freed space to the OTHER pane(s) — it must be told explicitly
            # (same fix as StructureGraphView._set_agent_collapsed), otherwise
            # the tabs pane on the right stays stuck at its old (narrower)
            # size. The freed width goes to the LAST pane (tabs) regardless of
            # whether History occupies a middle pane or not.
            sizes = self._split.sizes()
            if len(sizes) >= 2:
                freed = sizes[0] - strip_w
                sizes[0] = strip_w
                sizes[-1] = max(1, sizes[-1] + freed)
                self._split.setSizes(sizes)
        else:
            self._projects_pane.setMaximumWidth(16777215)  # QWIDGETSIZE_MAX
            if self._sidebar is not None:
                self._split.setSizes([260, 240, 800])
            else:
                self._split.setSizes([260, 900])

    # ---- data ------------------------------------------------------------
    def refresh_ai_models(self) -> None:
        """Reload the Folder tab's AI-edit model picker for the active provider —
        called when the active provider changes so the picker never keeps a
        stale model list from the old provider.

        R08-T12 moved the picker off ``FolderTab`` and onto the AI-Edit panel
        (``ai_panel.resolver``). The old guard here tested for
        ``folder.ai_model_combo``, an attribute that no longer exists on the
        tab, so this hook silently did nothing and a provider switch left the
        picker listing the previous provider's models. Reach the resolver
        directly instead.

        Refreshes unconditionally, exactly as the pre-refactor tab did. Gating
        on "the picker already holds a list" looks tidier but breaks the case
        that matters most: the first fetch failing (endpoint down, no network)
        leaves the list empty, and the user switching provider afterwards is
        precisely when the retry has to happen."""
        folder = getattr(self, "_folder", None)
        panel = getattr(folder, "ai_panel", None)
        resolver = getattr(panel, "resolver", None)
        if resolver is not None:
            resolver.refresh()

    def refresh(self) -> None:
        """Re-list projects, keeping the current selection when possible. No
        auto-seed: an empty workspace stays empty (the user must create a
        project before Cowork/GraphRAG appear — see _update_tab_visibility)."""
        from ..core.projects import list_projects

        keep = self._current_id
        counts = self._project_counts()
        self.project_list.blockSignals(True)
        self.project_list.clear()
        row_to_select = 0
        for i, p in enumerate(list_projects()):
            chats, tasks = counts.get(p.project_id, (0, 0))
            # No text on the item: the row widget paints the name, and setting
            # both drew it twice, one string ghosting the other.
            item = QListWidgetItem()
            item.setData(Qt.UserRole, p.project_id)
            if p.description:
                item.setToolTip(p.description)
            self.project_list.addItem(item)
            row = ProjectRow(p.name, chats, tasks)
            item.setSizeHint(row.sizeHint())
            self.project_list.setItemWidget(item, row)
            if p.project_id == keep:
                row_to_select = i
        self.project_list.blockSignals(False)
        self.project_list.setCurrentRow(row_to_select)
        # The drawing heads a populated screen with the title alone; the
        # explanation is what an EMPTY one says instead of showing nothing.
        self._hint.setVisible(self.project_list.count() == 0)
        self._load_current()

    @staticmethod
    def _project_counts():
        """{project_id: (chats, tasks)} — read once per refresh, not per row."""
        from ..core.history import history_dirs, list_conversations_by_project
        from ..core.tasks import list_tasks

        out: dict = {}
        for conv in list_conversations_by_project(history_dirs()):
            pid = conv.get("project_id") or "default"
            chats, tasks = out.get(pid, (0, 0))
            out[pid] = (chats + 1, tasks)
        for task in list_tasks():
            pid = task.get("project_id") or "default"
            chats, tasks = out.get(pid, (0, 0))
            out[pid] = (chats, tasks + 1)
        return out

    def _selected_id(self) -> str:
        """Id project đang chọn trong danh sách; '' nếu chưa chọn gì."""
        item = self.project_list.currentItem()
        return item.data(Qt.UserRole) if item else ""

    def _select_project_row(self, project_id: str) -> bool:
        """Chọn dòng ứng với một project id; trả về ``False`` nếu không tìm thấy."""
        for i in range(self.project_list.count()):
            if self.project_list.item(i).data(Qt.UserRole) == project_id:
                self.project_list.setCurrentRow(i)
                return True
        return False

    def _on_select(self, *_a) -> None:
        """Đổi dòng chọn trong danh sách project: nạp project đó lên form."""
        self._load_current()

    def _load_current(self) -> None:
        """Nạp project đang chọn lên form và nối mọi sub-tab vào nó."""
        from ..core.projects import load_project, project_history_dir

        pid = self._selected_id()
        self._current_id = pid
        # Deactivate the Cowork/GraphRAG panes while (re)loading — creating a
        # project or switching to another one re-binds their sandbox/history
        # underneath them, so they must not look interactive mid-transition.
        self._set_tabs_busy(True)
        try:
            project = load_project(pid) if pid else None
            # Route conversation history INTO the project's workspace folder so
            # sharing that folder shares the history (another machine can view +
            # continue). No project → global history dir (attribute cleared).
            if project is not None:
                self.ctx.config._project_history_dir = project_history_dir(project)
            else:
                self.ctx.config._project_history_dir = None
            if project is not None:
                self.name_edit.setText(project.name)
                self.desc_edit.setText(project.description)
                self.instr_edit.setPlainText(project.instructions)
                self.folder_lbl.setText(str(project.workspace_dir()))
                self._del_btn.setEnabled(True)
                self._reload_threads()
                if getattr(self, "_folder", None) is not None:
                    self._folder.set_project_root(str(project.workspace_dir()))
            else:
                self.name_edit.clear()
                self.desc_edit.clear()
                self.instr_edit.clear()
                self.folder_lbl.setText("")
                self._del_btn.setEnabled(False)
            self._refresh_cloud_badge(project)
            # Show Cowork/GraphRAG ONLY when a project is actually selected.
            self._update_tab_visibility(project is not None)
            # Bind the embedded Cowork/GraphRAG/History to this project's sandbox.
            self._bind_project(pid)
        finally:
            self._set_tabs_busy(False)
        # The rail's project picker mirrors this selection — it is a second view
        # of the same state, never a second source of truth.
        self.project_selected.emit(pid)

    # ---- rail integration -------------------------------------------------
    def project_choices(self):
        """(name, project_id) for the rail picker, in the list's own order.

        Read from the store, which is what the list is built from — reading
        item.text() coupled the picker to how a row happens to be drawn, and
        when rows became widgets the picker went blank: every project showed
        as a bare folder glyph with no name.
        """
        from ..core.projects import list_projects

        return [(p.name, p.project_id) for p in list_projects()]

    def selected_project_id(self) -> str:
        """Id project đang chọn — lối vào công khai cho lớp ngoài."""
        return self._selected_id()

    def choose_project(self, project_id: str) -> bool:
        """Select a project by id — the same path the list row takes."""
        return self._select_project_row(project_id)

    def recent_threads(self, limit: int = 5):
        """The active project's most recent conversations, newest first.

        Scoped to the project on purpose: history is stored inside the project's
        own folder (config.history_dir() follows the selection) and the History
        pane groups by project. A flat, cross-project recents list would quietly
        drop that scoping.
        """
        from ..core.history import list_conversations

        pid = self._current_id
        if not pid:
            return []
        try:
            convos = list_conversations(self.ctx.config.history_dir())
        except Exception:                                        # noqa: BLE001
            return []
        out = []
        for meta in convos:
            if (meta.get("project_id", "") or "default") != pid:
                continue
            out.append({
                "title": meta.get("title") or tr("sidebar.empty"),
                "path": str(meta["path"]),
                "kind": meta.get("kind", "") or "cowork",
                "pinned": bool(meta.get("pinned", False)),
                "session_id": meta.get("session_id", ""),
            })
            if len(out) >= limit:
                break
        return out

    def open_thread(self, path: str, kind: str = "cowork") -> bool:
        """Open a conversation by file path — the same route the History pane's
        own click takes (load_conversation → _on_sidebar_open)."""
        from ..core.history import load_conversation

        try:
            conv = load_conversation(path)
        except Exception:                                        # noqa: BLE001
            return False
        self._on_sidebar_open(kind, conv)
        return True

    def show_history_pane(self) -> None:
        """Bring the full History panel into view (un-collapsing it if needed).

        The rail's recents list is a shortcut, not a replacement: search,
        filters, pin, rename, multi-select delete and the context menu all still
        live in this panel.
        """
        self._history_opened = True
        self._show_cowork_tab()
        self._sidebar.setVisible(True)
        self._set_sidebar_collapsed(False)

    def start_new_chat(self) -> None:
        """Start a new thread in the current project and show it.

        Exactly what the History pane's own new-chat button does
        (_on_sidebar_new); the rail button is a second door to the same room,
        not a second implementation.
        """
        self._on_sidebar_new("cowork")

    def _set_tabs_busy(self, busy: bool) -> None:
        """Khoá/mở các sub-tab phụ thuộc project trong lúc đang chuyển project."""
        for idx in (self._cowork_tab_idx, self._graphrag_tab_idx):
            if idx >= 0:
                widget = self.tabs.widget(idx)
                if widget is not None:
                    widget.setEnabled(not busy)

    def _update_tab_visibility(self, has_project: bool) -> None:
        """Cowork + GraphRAG tabs are visible only while a project is
        selected; otherwise the screen shows just the Project (management)
        tab."""
        for idx in (self._cowork_tab_idx, self._graphrag_tab_idx):
            if idx >= 0:
                self.tabs.setTabVisible(idx, has_project)
        if not has_project:
            self.tabs.setCurrentIndex(self._project_tab_idx)
        # setCurrentIndex doesn't fire currentChanged when the Project tab is
        # already current — re-apply the pane rules explicitly.
        self._apply_pane_visibility()
        self.subtabs_changed.emit()   # left-nav children follow visible sub-tabs

    def _bind_project(self, pid: str) -> None:
        # This is THE central project-switch hook — make the selected project the
        # ACTIVE workspace so per-workspace modes (routing + auto-run) resolve
        # against it, then refresh every surface's toggles to show its modes.
        """Đặt project đang hoạt động và làm mới mọi thứ phụ thuộc nó.

        Đây là hook chuyển project TRUNG TÂM: đặt ``ctx.active_project_id`` để chế
        độ theo-workspace (định tuyến, tự chạy) phân giải đúng, rồi làm mới công
        tắc trên từng bề mặt cho khớp.
        """
        self.ctx.active_project_id = pid or "default"
        self._refresh_mode_toggles()
        if self._structure is not None:
            self._structure.set_workspace_project(pid)
        if self._sidebar is not None:
            self._sidebar.set_project_filter(pid)   # "" → show all (no project selected)
        # Route Co4E flow output into THIS project's workspace folder (so flow
        # files land in the selected workspace, like Cowork — not the config dir).
        if self._co4e is not None:
            self._co4e.set_project(pid)
        if self._cowork is not None and pid:
            # Switch to a fresh thread in the newly selected project (past
            # threads are reopened from History), unless the current thread is
            # already in it.
            if getattr(self._cowork, "project_id", "") != pid:
                self._cowork.new_session()
                self._cowork.set_project(pid)

    def _refresh_mode_toggles(self) -> None:
        """Re-point every surface's Off/Auto/Manual + Auto-run toggles at the
        ACTIVE workspace's modes (called whenever the selected project changes)."""
        targets = [
            (self._cowork, "routing_toggle"),
            (self._cowork, "autorun_toggle"),
            (self._co4e, "co4e_routing_toggle"),
            (self._folder, "ai_routing_toggle"),
        ]
        for widget, attr in targets:
            toggle = getattr(widget, attr, None) if widget is not None else None
            if toggle is not None:
                toggle.refresh()

    def _reload_threads(self) -> None:
        # The threads list was removed from the Project tab; nothing to reload.
        """Nạp lại danh sách luồng chat của project.

        Danh sách này đã bị gỡ khỏi tab Dự án nên thường là no-op; giữ lại để mã
        cũ còn gọi tới không vỡ.
        """
        if not hasattr(self, "threads"):
            return
        from ..core.history import list_conversations

        self.threads.clear()
        pid = self._current_id or "default"
        for conv in list_conversations(self.ctx.config.history_dir()):
            if conv.get("project_id", "default") != pid:
                continue
            label = conv["title"]
            if conv.get("created"):
                label += f"   ·   {conv['created'][:16].replace('T', ' ')}"
            item = QTreeWidgetItem([label])
            item.setData(0, Qt.UserRole, str(conv["path"]))
            self.threads.addTopLevelItem(item)

    # ---- actions -----------------------------------------------------------
    def _pick_folder(self) -> None:
        """Chọn thư mục sandbox cho project đang mở."""
        from ..core.projects import load_project, save_project

        pid = self._current_id
        project = load_project(pid) if pid else None
        if project is None:
            return
        chosen = QFileDialog.getExistingDirectory(
            self, tr("workspace.browse_tooltip"), str(project.workspace_dir()))
        if not chosen:
            return
        project.output_dir = chosen
        save_project(project)
        self.folder_lbl.setText(chosen)
        self.status_message.emit(tr("workspace.saved", name=project.name))

    def _open_workspace(self) -> None:
        """Mở thư mục sandbox của project trong trình quản lý tệp của hệ điều hành."""
        from ..core.projects import load_project, project_history_dir

        project = load_project(self._current_id) if self._current_id else None
        if project is None:
            return
        wd = project.workspace_dir()
        wd.mkdir(parents=True, exist_ok=True)
        open_folder(str(wd))

    def _cloud_token(self):
        """Lấy access token MS365 hiện tại theo cấu hình — raise
        ``Ms365AuthError`` nếu chưa đăng nhập/hết hạn (gọi picker trước nên
        thường đã có sẵn phiên đăng nhập)."""
        from ..core.ms365_auth import get_access_token

        ms365 = (self.ctx.config.ms365 or {})
        return get_access_token(ms365.get("tenant_id", ""), ms365.get("client_id", ""))

    def _pick_cloud_folder(self) -> None:
        """DF-007 — duyệt OneDrive/SharePoint qua Graph API, tải một bản
        mirror cục bộ xuống rồi dùng bản mirror đó làm output_dir của
        project. Xem core/cloud_workspace_sync.py cho giới hạn (một chiều,
        thủ công, không đồng bộ liên tục, không xử lý xung đột)."""
        from ..core.cloud_workspace_sync import download_folder
        from ..core.ms365_auth import Ms365AuthError
        from ..core.projects import WORKSPACES_DIR, load_project, save_project
        from .cloud_folder_picker_dialog import pick_cloud_folder

        pid = self._current_id
        project = load_project(pid) if pid else None
        if project is None:
            return
        cloud_source = pick_cloud_folder(self, self.ctx.config)
        if not cloud_source:
            return
        local_dir = WORKSPACES_DIR / project.project_id / "_cloud_mirror"
        self._cloud_pick_btn.setEnabled(False)
        try:
            token = self._cloud_token()
            report = download_folder(token, cloud_source, local_dir)
        except Ms365AuthError as exc:
            QMessageBox.warning(self, tr("workspace.cloud_pick"), str(exc))
            return
        finally:
            self._cloud_pick_btn.setEnabled(True)
        project.output_dir = str(local_dir)
        project.cloud_source = cloud_source
        save_project(project)
        self.folder_lbl.setText(str(local_dir))
        self._refresh_cloud_badge(project)
        self.projects_changed.emit()
        if report.errors:
            QMessageBox.warning(self, tr("workspace.cloud_pick"),
                                 tr("workspace.cloud_sync_errors", n=len(report.errors)))
        self.status_message.emit(tr("workspace.saved", name=project.name))

    def _sync_cloud_folder(self) -> None:
        """DF-007 — đẩy thay đổi cục bộ lên cloud rồi tải lại (một chiều mỗi
        bước, thủ công, chạy khi bấm nút). Không xoá file 2 phía, không phát
        hiện xung đột — xem core/cloud_workspace_sync.py."""
        from ..core.cloud_workspace_sync import download_folder, upload_folder
        from ..core.ms365_auth import Ms365AuthError
        from ..core.projects import load_project

        pid = self._current_id
        project = load_project(pid) if pid else None
        if project is None or not project.cloud_source:
            return
        self._cloud_sync_btn.setEnabled(False)
        try:
            token = self._cloud_token()
            up_report = upload_folder(token, project.cloud_source, project.workspace_dir())
            down_report = download_folder(token, project.cloud_source, project.workspace_dir())
        except Ms365AuthError as exc:
            QMessageBox.warning(self, tr("workspace.cloud_sync"), str(exc))
            return
        finally:
            self._cloud_sync_btn.setEnabled(True)
        lines = [tr("workspace.cloud_sync_result",
                     up=up_report.transferred, down=down_report.transferred)]
        n_errors = len(up_report.errors) + len(down_report.errors)
        if n_errors:
            lines.append(tr("workspace.cloud_sync_errors", n=n_errors))
        n_skipped = len(up_report.skipped_too_large)
        if n_skipped:
            lines.append(tr("workspace.cloud_sync_skipped", n=n_skipped))
        QMessageBox.information(self, tr("workspace.cloud_sync"), "\n".join(lines))

    def _refresh_cloud_badge(self, project=None) -> None:
        """Hiện/ẩn badge ☁ + nút Đồng bộ theo project đang mở có phải một
        mirror cloud hay không (``project.cloud_source``)."""
        if project is None:
            from ..core.projects import load_project

            project = load_project(self._current_id) if self._current_id else None
        cloud_source = project.cloud_source if project is not None else None
        if not cloud_source:
            self._cloud_badge_lbl.hide()
            self._cloud_sync_btn.hide()
            return
        if cloud_source.get("provider") == "sharepoint":
            text = tr("workspace.cloud_badge_sharepoint",
                      site=cloud_source.get("site_name", ""),
                      path=cloud_source.get("remote_path", "") or "/")
        else:
            text = tr("workspace.cloud_badge_onedrive",
                      path=cloud_source.get("remote_path", "") or "/")
        self._cloud_badge_lbl.setText(text)
        self._cloud_badge_lbl.show()
        self._cloud_sync_btn.show()
