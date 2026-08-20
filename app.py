"""
pages (Dashboard / Schedule / Workspace / Cowork / Structure) and top bar."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QStyledItemDelegate,
    QApplication, QComboBox, QHBoxLayout, QLabel, QMainWindow, QMenu,
    QPushButton, QScrollArea, QSizePolicy, QSplitter, QStackedWidget,
    QSystemTrayIcon, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget,
)

from . import APP_NAME, DISPLAY_NAME, __version__
from .config import PROVIDER_LABELS, AppConfig
from .i18n import LANGUAGE_SHORT, LANGUAGES, get_language, on_language_changed, set_language, tr
from .state import AppContext
from .ui.widgets import tidy_popup
from .theme import current_palette, set_active_theme, stylesheet
from .core.task_scheduler import TaskScheduler
from .ui.cowork_tab import CoworkTab
from .ui.dashboard_tab import DashboardTab
from .ui.monitoring_tab import MonitoringTab
from .ui.schedule_task_tab import ScheduleTaskTab
from .ui.settings_dialog import SettingsDialog
from .ui.sidebar import HistorySidebar
from .ui.structure_graph_view import StructureGraphView
from .ui.workspace_tab import WorkspaceTab

ASSETS = Path(__file__).resolve().parent / "assets"

# Nav rail (sidebar navigation) widths — expanded shows icon+label, collapsed
# shows icon-only (still fully clickable, just narrower).
_NAV_EXPANDED_WIDTH = 150
_NAV_COLLAPSED_WIDTH = 54
# The splitter between rail and content draws a drag handle. It only means
# something if the rail can actually take a width from it, so the expanded rail
# is a range rather than one number; long project and thread names in RECENTS
# are the reason someone would widen it.
#
# The ceiling is a SHARE of the window, not a pixel count: 360px is a quarter
# of a 1440 screen and more than a quarter of a 1280 one, where it left the
# seven Kanban lanes 920px of the 1067 they need. A share behaves the same on
# every monitor.
# Where a rail row starts, and how much air sits between its icon and its
# label. The tree rows get these from the style; anything laid out by hand
# beside them has to use the same two numbers or it will not line up.
_NAV_ROW_INSET = 4
_NAV_ROW_GAP = 6
_NAV_MIN_WIDTH = 132
_NAV_MAX_SHARE = 0.22
_NAV_MAX_CEILING = 360


def app_icon() -> QIcon:
    """The buffalo app icon, used everywhere (window title bar, Windows taskbar and
    the tray). The multi-size ``.ico`` is loaded FIRST so Windows has the right
    pixmap for the taskbar; the high-res ``.png`` is added so the icon stays crisp
    at large sizes. This keeps the taskbar icon identical to the app's icon."""
    icon = QIcon()
    for name in ("icon.ico", "icon.png"):
        path = ASSETS / name
        if path.exists():
            icon.addFile(str(path))
    return icon


class _Toast(QLabel):
    """A small auto-hiding notification shown at the window's top-left."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setWordWrap(True)
        self.setMaximumWidth(380)
        self.setVisible(False)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, text: str, ok: bool = True, ms: int = 4500) -> None:
        p = current_palette()
        bg = p.success_soft if ok else p.danger_soft
        fg = p.success if ok else p.danger
        self.setStyleSheet(
            f"#toast {{ background:{bg}; color:{fg}; border:1px solid {fg};"
            f" border-radius:{p.radius}px; padding:10px 16px; font-weight:600; }}")
        self.setText(text)
        self.adjustSize()
        self.move(14, 14)          # top-left of the window
        self.raise_()
        self.setVisible(True)
        self._timer.start(ms)


class _NavItemDelegate(QStyledItemDelegate):
    """Keep a rail row's icon on the left edge, whatever the column is doing.

    QStyledItemDelegate hands the style decorationAlignment = AlignHCenter, so
    a row with no label — every row once the rail collapses to 54px — has its
    icon centred inside whatever box the column happens to give it. That box
    tracks the column width, which is not stable: stretched to the viewport the
    icons land in the middle of the rail, while a column left wider than the
    view leaves them at the left. Same code, two different pictures, which is
    why a test render disagreed with the running app.
    """

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.decorationAlignment = Qt.AlignLeft | Qt.AlignVCenter


class MainWindow(QMainWindow):
    # Nav rows (Dashboard/Schedule/Monitoring are lazy; Workspace is the eager home page).
    _ROW_DASHBOARD, _ROW_SCHEDULE, _ROW_WORKSPACE, _ROW_MONITORING = 0, 1, 2, 3

    def __init__(self, ctx: AppContext, user_name: str = ""):
        super().__init__()
        self.ctx = ctx
        self._user_name = user_name
        self._really_quit = False
        self.tray = None
        self._nav_collapsed = False    # icon-only nav rail toggle (Task: collapsible nav)
        self._history_collapsed = False   # remembers History's own collapse-to-strip state
        self.setWindowTitle(f"{DISPLAY_NAME} v{__version__}")
        self.setWindowIcon(app_icon())
        # Fit to the available screen so the window never opens larger than the
        # monitor (auto-fit). Keep a modest minimum that still fits small laptops.
        self._fit_to_screen(1180, 760)

        self.sidebar = HistorySidebar(ctx)
        # Task scheduler ENGINE runs in the background whether or not its Kanban
        # UI (built lazily) is on screen — scheduled tasks must fire regardless.
        self.task_scheduler = TaskScheduler(ctx, parent=self)
        # Desktop notification when a scheduled task finishes; also refresh
        # History — a cowork/code task run saves itself as a new session there.
        self.task_scheduler.task_finished.connect(self._on_scheduled_task_done)
        # NOTE: task_started fires BEFORE the worker thread even begins, so its
        # session doesn't exist on disk yet — refreshing History here would
        # find nothing. history_ready fires once the session is actually
        # saved (right as the run starts, then again after each turn), which
        # is what really makes a Running task's session show up live.
        self.task_scheduler.history_ready.connect(lambda _tid: self._refresh_history())

        # Cowork chat + GraphRAG view are embedded as sub-tabs INSIDE the
        # Workspace screen (per selected project). GraphRAG's heavy
        # QtWebEngine is still built lazily on first display
        # (StructureGraphView._ensure_web).
        self.cowork = CoworkTab(ctx)
        self.structure = StructureGraphView(ctx)
        self.structure.status_message.connect(self.statusBar().showMessage)
        self.cowork.output_changed.connect(self.structure.schedule_rescan)
        self.cowork.status_message.connect(self.statusBar().showMessage)
        # Refresh History (list + running markers + current highlight) whenever a
        # conversation is created/updated or a turn finishes.
        self.cowork.turn_finished.connect(lambda *_: self._refresh_history())
        self.cowork.history_changed.connect(self._refresh_history)
        self.cowork.turn_finished.connect(
            lambda result: self._notify_task(self.cowork, "cowork", result))

        # Workspace screen — the app HOME: project management + the per-project
        # Cowork / GraphRAG sub-tabs and History.
        self.workspace = WorkspaceTab(ctx, cowork=self.cowork, structure=self.structure,
                                      sidebar=self.sidebar)
        self.workspace.status_message.connect(self.statusBar().showMessage)
        self.workspace.projects_changed.connect(self._on_projects_changed)
        self.workspace.open_chat.connect(lambda *_: self._refresh_history())
        self.workspace.new_chat.connect(lambda *_: self._refresh_history())

        # Dashboard + Schedule pages are built lazily on first visit (lazy page
        # creation — keeps startup light); None until then.
        self.dashboard = None
        self.schedule = None
        self.monitoring = None

        # --- right side: top bar + pages (nav rail drives the stack) ---
        right = QWidget()
        right.setObjectName("contentArea")
        rlay = QVBoxLayout(right)
        rlay.setContentsMargins(10, 10, 10, 10)
        rlay.setSpacing(10)
        rlay.addWidget(self._build_topbar())

        self.pages = QStackedWidget()
        # (i18n key, icon, builder-or-None, eager-widget-or-None) — page index == list index
        self._nav_defs = [
            ("app.tab.dashboard", "dashboard", self._build_dashboard, None),
            ("app.tab.schedule", "schedule", self._build_schedule, None),
            ("app.tab.workspace", "workspaces", None, self.workspace),
            ("app.tab.monitoring", "monitoring", self._build_monitoring, None),
        ]
        self._page_widgets = []   # page index → widget (placeholder until lazily built)
        self._built = []
        for _key, _icon_name, _builder, widget in self._nav_defs:
            page = widget if widget is not None else QWidget()
            self.pages.addWidget(page)
            self._page_widgets.append(page)
            self._built.append(widget is not None)

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
        from .ui.icons import collapse_left_icon, collapse_right_icon
        from .ui.icons import icon as _icon
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
        # Bottom-pinned group: the places you visit occasionally, kept out of the
        # way of the ones you live in. A hairline (styled via #navrailBottom in
        # theme.py) separates the two lists.
        nvl.addWidget(self.nav_bottom, 0)
        # Settings reads as one more row under Dashboard / Giám sát, so its icon
        # and label must start exactly where theirs do. Letting QPushButton place
        # them does not achieve that: the gap it leaves between icon and text is
        # the platform style's, and on macOS it is visibly tighter than the tree
        # rows above — a Windows-tuned nudge only moved the mismatch. So the row
        # is laid out here, in the same two numbers the tree uses: 4px in, 6px
        # between.
        self._nav_settings_btn = QPushButton()
        self._nav_settings_btn.setObjectName("navSettingsBtn")
        self._nav_settings_btn.setFlat(True)
        self._nav_settings_btn.setCursor(Qt.PointingHandCursor)
        self._nav_settings_btn.clicked.connect(self._open_settings)
        srow = QHBoxLayout(self._nav_settings_btn)
        srow.setContentsMargins(_NAV_ROW_INSET, 6, 8, 6)
        srow.setSpacing(_NAV_ROW_GAP)
        self._nav_settings_icon = QLabel()
        self._nav_settings_icon.setPixmap(_icon("settings").pixmap(16, 16))
        self._nav_settings_icon.setFixedSize(16, 16)
        self._nav_settings_text = QLabel(tr("app.settings"))
        srow.addWidget(self._nav_settings_icon)
        srow.addWidget(self._nav_settings_text)
        srow.addStretch(1)
        nvl.addWidget(self._nav_settings_btn)
        self._account_row = self._build_account_row()
        nvl.addWidget(self._account_row)

        self.split = QSplitter(Qt.Horizontal)
        self.split.addWidget(self._nav_wrap)
        self.split.addWidget(right)
        self.split.setStretchFactor(0, 0)
        self.split.setStretchFactor(1, 1)
        self.split.setSizes([_NAV_EXPANDED_WIDTH, 1000])
        self.split.splitterMoved.connect(self._on_split_moved)
        self.setCentralWidget(self.split)
        # Landing stays Workspace ▸ Project, exactly as before. Go through _goto
        # so the page is actually shown — selecting the row alone only moves the
        # highlight (its signals are blocked to avoid rebuild loops).
        self._goto(self._ROW_WORKSPACE, self.workspace.current_subtab())
        self.toast = _Toast(self)   # top-left "task done" popup
        # Floating in-app Help assistant — a robot icon pinned bottom-right on
        # every screen; expands into a small help-only chat (see
        # ui/help_agent_widget.py). Managed in Monitoring → Agents Admin.
        from .ui.help_agent_widget import HelpAgentWidget
        self.help_agent = HelpAgentWidget(ctx, self, user_name=self._user_name)
        self.help_agent.status_message.connect(self.statusBar().showMessage)

        self.statusBar().showMessage(tr("app.status.ready"))
        # Author credit, pinned to the bottom-right corner. A permanent status-bar
        # widget sits at the right end and is never cleared by showMessage (which
        # writes on the left).
        self._credit = QLabel(tr("app.credit"))
        self._credit.setObjectName("faint")
        self._credit.setStyleSheet("padding: 0 10px;")
        self.statusBar().addPermanentWidget(self._credit)
        self._restore_sessions()
        self._setup_tray()
        # Start the task scheduler last, once the whole window exists — it
        # catches up any overdue tasks right away (first tick runs inline).
        self.task_scheduler.start()
        # Auto Model Routing: periodic reassess + pending-switch expiry. Runs
        # background probes only when genuinely due (never a burst at launch).
        try:
            from .core.routing.scheduler import RoutingScheduler
            self.routing_scheduler = RoutingScheduler(self.ctx, self.ctx.routing(), parent=self)
            self.routing_scheduler.start()
        except Exception:  # noqa: BLE001 — routing must never block app startup
            self.routing_scheduler = None
        on_language_changed(self._retranslate)

    def resizeEvent(self, event):  # noqa: N802 - Qt override
        super().resizeEvent(event)
        # The rail's ceiling is a share of the window, so it moves with the
        # window. Computed once at construction it was read off a not-yet-sized
        # window and stuck at 162px on every monitor.
        if getattr(self, "_nav_wrap", None) is not None and not self._nav_collapsed:
            self._set_nav_width_range(_NAV_MIN_WIDTH, self._nav_max_width())
        # Keep the floating Help assistant pinned to the bottom-right corner.
        if getattr(self, "help_agent", None) is not None:
            self.help_agent.reposition()

    def showEvent(self, event):  # noqa: N802 - Qt override
        super().showEvent(event)
        if getattr(self, "help_agent", None) is not None:
            self._update_dock_guard()
            self.help_agent.reposition()
            self.help_agent.raise_()
        # Build GraphRAG's browser view and first graph once the window is up
        # and idle, so clicking GraphRAG does not sit on an empty view while
        # both happen. 3s is after the first paint and any startup refresh.
        if not getattr(self, "_graph_prewarmed", False):
            self._graph_prewarmed = True
            QTimer.singleShot(3000, self._prewarm_graph)

    def _prewarm_graph(self) -> None:
        view = getattr(self, "structure", None)
        if view is None or not hasattr(view, "prewarm"):
            return
        try:
            view.prewarm()
        except Exception:  # noqa: BLE001 — a warm-up must never break the app
            pass

    # ---- i18n ----------------------------------------------------------
    def _retranslate(self) -> None:
        """Re-apply the current language to this window's own static chrome
        (tabs are the only long-lived text here; the tabs/dialogs retranslate
        themselves)."""
        self._apply_nav_labels()
        self._nav_toggle_btn.setText("" if self._nav_collapsed else tr("app.nav.menu_label"))
        self._nav_toggle_btn.setToolTip(
            tr("app.nav.expand_tooltip") if self._nav_collapsed else tr("app.nav.collapse_tooltip"))
        self._credit.setText(tr("app.credit"))
        if hasattr(self, "provider_lbl"):
            self.provider_lbl.setText(tr("app.provider"))
        if hasattr(self, "settings_btn"):
            self.settings_btn.setText(tr("app.settings"))
        if hasattr(self, "theme_btn"):
            self.theme_btn.setToolTip(tr("settings.theme"))
            for value, act in self._theme_actions.items():
                act.setText(tr(f"settings.theme_{value}"))
        if hasattr(self, "logo_lbl"):
            self.logo_lbl.setText(tr("app.logo"))
        if getattr(self, "help_agent", None) is not None:
            self.help_agent.retranslate()
        if self.tray is not None:
            self.tray.setToolTip(DISPLAY_NAME)
        if hasattr(self, "_tray_open_act"):
            self._tray_open_act.setText(tr("app.tray.open"))
            self._tray_quit_act.setText(tr("app.tray.quit"))

    # ---- system tray (run in background when the window is closed) ---
    def _setup_tray(self) -> None:
        from PySide6.QtGui import QAction

        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(app_icon(), self)
        self.tray.setToolTip(DISPLAY_NAME)
        menu = QMenu()
        self._tray_open_act = QAction(tr("app.tray.open"), self)
        self._tray_open_act.triggered.connect(self._show_window)
        self._tray_quit_act = QAction(tr("app.tray.quit"), self)
        self._tray_quit_act.triggered.connect(self._quit_app)
        menu.addAction(self._tray_open_act)
        menu.addAction(self._tray_quit_act)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self._show_window() if reason == QSystemTrayIcon.Trigger else None)
        self.tray.show()

    def _page_index(self, widget) -> int:
        return self.pages.indexOf(widget)

    # ---- lazy page building -------------------------------------------
    def _build_dashboard(self):
        d = DashboardTab(self.ctx)
        d.status_message.connect(self.statusBar().showMessage)
        self.dashboard = d
        return d

    def _build_schedule(self):
        s = ScheduleTaskTab(self.ctx, self.task_scheduler)
        s.status_message.connect(self.statusBar().showMessage)
        self.schedule = s
        return s

    def _build_monitoring(self):
        m = MonitoringTab(self.ctx, cowork=self.cowork, structure=self.structure,
                          task_scheduler=self.task_scheduler)
        m.status_message.connect(self.statusBar().showMessage)
        self.monitoring = m
        return m

    def _ensure_page(self, row: int) -> None:
        """Build a lazy nav page on first visit and swap it in for its placeholder."""
        if not (0 <= row < len(self._built)) or self._built[row]:
            return
        builder = self._nav_defs[row][2]
        if builder is None:
            return
        real = builder()
        placeholder = self._page_widgets[row]
        self.pages.insertWidget(row, real)     # placeholder shifts to row+1
        self.pages.removeWidget(placeholder)
        placeholder.deleteLater()
        self._page_widgets[row] = real
        self._built[row] = True
        # Monitoring KEEPS its own tab strip: its eight sub-views live in the
        # page, not in the rail. Workspace is the one that hides its strip,
        # because the rail lists its sub-views directly.

    def _page_index(self, widget) -> int:
        if widget is self.workspace:
            return self._ROW_WORKSPACE
        if self.dashboard is not None and widget is self.dashboard:
            return self._ROW_DASHBOARD
        if self.schedule is not None and widget is self.schedule:
            return self._ROW_SCHEDULE
        if self.monitoring is not None and widget is self.monitoring:
            return self._ROW_MONITORING
        return self.pages.indexOf(widget)

    # ---- flat nav rail -------------------------------------------------
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
            from .ui.icons import icon as _icon
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
        if self._syncing_rail_project:
            return
        pid = self.nav_project.currentData()
        if pid:
            self.workspace.choose_project(pid)

    # ---- rail RECENTS --------------------------------------------------
    _RAIL_RECENTS = 5

    def _refresh_rail_recents(self) -> None:
        """Re-fill the rail's recents from the active project's history."""
        from .ui.icons import DOT_BLUE, dot_icon
        from .ui.icons import icon as _icon

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

    def _on_rail_recent(self, item, _col: int = 0) -> None:
        data = item.data(0, Qt.UserRole) or {}
        if data.get("all"):
            self._goto(self._ROW_WORKSPACE, self.workspace._cowork_tab_idx)
            self.workspace.show_history_pane()
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

    def _nav_new_chat_enabled(self) -> bool:
        return bool(self.workspace.project_choices())

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
        if not self._nav_collapsed:
            self._nav_width = max(_NAV_MIN_WIDTH,
                                  min(self._nav_max_width(), self._nav_wrap.width()))

    def _toggle_nav(self) -> None:
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

    def _running_session_ids(self):
        """All conversation ids currently running — interactive Cowork/Code
        chat tab AgentWorkers, plus Schedule Task runs (their own session,
        tracked by the scheduler), so a task's live run gets the same
        "running" marker in History an interactive chat gets."""
        return set(self.cowork.running_session_ids()) | self.task_scheduler.running_session_ids()

    def _refresh_history(self) -> None:
        """Rebuild the History list with the current conversation highlighted and
        the running ones marked. Deferred to the next event-loop tick: this is often
        triggered (via load_conversation) from inside the sidebar's own item-click
        handler, and clearing the tree there would delete the item mid-click."""
        from PySide6.QtCore import QTimer

        def _do() -> None:
            current = self.cowork.session_id
            self.sidebar.set_view_state(current, self._running_session_ids())
            self.sidebar.refresh()
            self._refresh_rail_recents()   # the rail shortcut follows the panel

        QTimer.singleShot(0, _do)

    def _on_scheduled_task_done(self, task_id: str, ok: bool) -> None:
        """Desktop notification for a finished scheduled task (toast always,
        tray balloon when the window isn't focused), then refresh History —
        cowork/co4e task runs just saved themselves as new sessions there."""
        from .core.tasks import load_task

        task = load_task(task_id) or {}
        title = task.get("title", "")
        msg = (tr("app.toast.task_done", title=title) if ok
               else tr("app.toast.task_failed", title=title))
        self.toast.show_message(msg, ok=ok)
        if (self.tray is not None
                and self.ctx.config.data.get("tray", {}).get("notify_on_done", True)
                and not self.isActiveWindow()):
            try:
                self.tray.showMessage(
                    DISPLAY_NAME, msg,
                    QSystemTrayIcon.Information if ok else QSystemTrayIcon.Warning, 5000)
            except Exception:  # noqa: BLE001
                pass
        self._refresh_history()

    def _notify_task(self, tab, kind: str, result: dict) -> None:
        """Notify when a task finishes/fails (skip if more stages queued)."""
        if tab.composer.has_queue():
            return  # a flow / queue is still running — notify only at the end
        name = tr(f"app.tab.{kind}")
        err = (result or {}).get("error")
        # In-app popup at the top-left (shown whether or not the window is focused).
        self.toast.show_message(
            tr("app.toast.error", name=name) if err else tr("app.toast.done", name=name), ok=not err)
        # System-tray balloon only when the window isn't the active one.
        if self.tray is None:
            return
        if not self.ctx.config.data.get("tray", {}).get("notify_on_done", True):
            return
        if self.isActiveWindow():
            return  # user is looking at the window already
        err = (result or {}).get("error")
        title = tr("app.toast.error", name=name) if err else tr("app.toast.done", name=name)
        body = (err if err else (tab._last_assistant_text() or "Task completed."))[:140]
        icon = QSystemTrayIcon.Critical if err else QSystemTrayIcon.Information
        try:
            self.tray.showMessage(title, body, icon, 5000)
        except Exception:
            pass

    def _show_window(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_app(self) -> None:
        self._really_quit = True
        self.close()

    def _restore_sessions(self) -> None:
        """Reopen the last conversation per tab (recover after a crash/abrupt exit)."""
        from pathlib import Path

        from .core.history import load_conversation

        last = self.ctx.config.data.get("last_session", {})
        path = last.get("cowork", "")
        if path and Path(path).exists():
            try:
                self.cowork.load_conversation(load_conversation(path))
                # Reflect the restored thread's project in the Workspace home
                # (selecting the matching row won't wipe it — the project id
                # already matches, so _bind_project starts no new session).
                # Skip forcing the Cowork tab open for a project that no
                # longer exists (deleted since this session was saved) — that
                # would show the Cowork page while the tab strip still says
                # "no project selected" (see WorkspaceTab._on_sidebar_open).
                pid = self.cowork.project_id
                if pid in ("", "default") or self.workspace._select_project_row(pid):
                    self.workspace._show_cowork_tab()
            except Exception:
                pass

    # ---- top bar -----------------------------------------------------
    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("topbar")
        # Styled centrally (see theme._TEMPLATE): flat, with a single hairline
        # separating it from the content below — no card box behind it.
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 10, 12, 10)
        h.setSpacing(10)
        # FPT logo slot in front of the brand text: shown only when a logo
        # image has been dropped into assets/ (see _brand_logo_pixmap) — the
        # brand works text-only until the real artwork is supplied.
        self.logo_img = QLabel()
        logo_pm = self._brand_logo_pixmap()
        if logo_pm is not None:
            self.logo_img.setPixmap(logo_pm)
        else:
            self.logo_img.setVisible(False)
        h.addWidget(self.logo_img)
        self.logo_lbl = QLabel(tr("app.logo"))
        self.logo_lbl.setObjectName("brand")   # styled centrally — see theme._TEMPLATE
        h.addWidget(self.logo_lbl)
        h.addStretch(1)
        # Provider / language / theme / Settings used to live here, five controls
        # wide across the top of every screen. They are per-account settings, not
        # per-screen ones, so they moved to the account row at the foot of the
        # rail (_build_account_row) — same widgets, same handlers, new home.
        return bar

    def _build_account_row(self) -> QWidget:
        """The rail's foot: who you are, and the settings that follow you.

        Nothing new is introduced here — these are the exact widgets the top bar
        used to hold, moved as-is so every existing signal still lands.
        """
        box = QWidget()
        box.setObjectName("navAccount")
        v = QVBoxLayout(box)
        v.setContentsMargins(6, 4, 6, 4)
        v.setSpacing(4)

        who = QHBoxLayout()
        who.setSpacing(4)
        self.account_lbl = QLabel(f"👤 {self._user_name}" if self._user_name else "👤")
        self.account_lbl.setObjectName("hint")
        who.addWidget(self.account_lbl, 1)
        self.language_combo = QComboBox()
        for key in LANGUAGES:
            self.language_combo.addItem(LANGUAGE_SHORT.get(key, key.upper()), key)
            self.language_combo.setItemData(
                self.language_combo.count() - 1, LANGUAGES[key], Qt.ToolTipRole)
        idx = self.language_combo.findData(get_language())
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        tidy_popup(self.language_combo)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        who.addWidget(self.language_combo)
        self.theme_btn = self._build_theme_button()
        who.addWidget(self.theme_btn)
        v.addLayout(who)

        self.provider_lbl = QLabel(tr("app.provider"))
        self.provider_lbl.setObjectName("hint")
        self.provider_lbl.setVisible(False)   # the combo names itself in the rail
        self.provider_combo = QComboBox()
        self.provider_combo.setToolTip(tr("app.provider"))
        for key, label in PROVIDER_LABELS.items():
            self.provider_combo.addItem(label, key)
        tidy_popup(self.provider_combo)
        idx = self.provider_combo.findData(self.ctx.config.active_provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        v.addWidget(self.provider_lbl)
        v.addWidget(self.provider_combo)
        return box

    _BRAND_LOGO_NAMES = ("fpt_logo.png", "fpt-logo.png", "logo_fpt.png", "fpt_logo.jpg")
    _BRAND_LOGO_HEIGHT = 22

    def _brand_logo_pixmap(self):
        """The FPT logo scaled to top-bar height, or None while no logo file
        exists yet — drop the artwork into src/cowork_local/assets/ under one
        of the _BRAND_LOGO_NAMES and it appears on next launch."""
        from PySide6.QtGui import QPixmap

        for name in self._BRAND_LOGO_NAMES:
            path = ASSETS / name
            if not path.exists():
                continue
            pm = QPixmap(str(path))
            if pm.isNull():
                continue
            return pm.scaledToHeight(self._BRAND_LOGO_HEIGHT, Qt.SmoothTransformation)
        return None

    _THEME_ICONS = {"system": "monitor", "dark": "moon", "light": "sun"}

    def _build_theme_button(self) -> QToolButton:
        """A single icon button (System/Dark/Light) replacing the old
        Settings-only theme dropdown — one click applies the choice
        immediately via the existing _apply_theme(), no dialog round-trip."""
        from .ui.icons import icon as _icon

        btn = QToolButton()
        btn.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(btn)
        self._theme_actions = {}
        for value, icon_name in self._THEME_ICONS.items():
            act = menu.addAction(_icon(icon_name), tr(f"settings.theme_{value}"))
            act.triggered.connect(lambda _checked=False, v=value: self._set_theme(v))
            self._theme_actions[value] = act
        btn.setMenu(menu)
        btn.setIcon(_icon(self._THEME_ICONS.get(self.ctx.config.theme, "monitor")))
        return btn

    def _set_theme(self, value: str) -> None:
        from .ui.icons import icon as _icon

        self.ctx.config.theme = value
        self.ctx.save()
        self._apply_theme()
        self.theme_btn.setIcon(_icon(self._THEME_ICONS.get(value, "monitor")))

    # ---- handlers ----------------------------------------------------
    def _on_provider_changed(self, _idx: int) -> None:
        self.ctx.config.active_provider = self.provider_combo.currentData()
        self.ctx.save()
        self.cowork.refresh_header()
        # Reload the Cowork tab's Agent (Model) list for the newly selected provider.
        self.cowork.refresh_agents()
        self.workspace.refresh_ai_models()   # + the Folder AI-edit model picker
        self.statusBar().showMessage(
            tr("app.status.using_provider",
               label=PROVIDER_LABELS.get(self.ctx.config.active_provider))
        )

    def _on_language_changed(self, _idx: int) -> None:
        lang = self.language_combo.currentData()
        if not lang or lang == get_language():
            return
        self.ctx.config.language = lang
        self.ctx.save()
        set_language(lang)   # notifies every registered persistent widget

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.ctx, self)
        if dlg.exec():
            self._apply_theme()
            # Settings can change the theme too — keep the rail's toggle icon
            # showing the value that is actually in effect.
            from .ui.icons import icon as _theme_icon
            self.theme_btn.setIcon(
                _theme_icon(self._THEME_ICONS.get(self.ctx.config.theme, "monitor")))
            set_language(self.ctx.config.language)   # apply if changed in Settings
            # reflect provider/theme/language changes
            i = self.provider_combo.findData(self.ctx.config.active_provider)
            if i >= 0:
                self.provider_combo.setCurrentIndex(i)
            li = self.language_combo.findData(get_language())
            if li >= 0:
                self.language_combo.blockSignals(True)
                self.language_combo.setCurrentIndex(li)
                self.language_combo.blockSignals(False)
            self.cowork.refresh_header()
            self.cowork.refresh_agents()
            self.workspace.refresh_ai_models()   # + the Folder AI-edit model picker
            max_files = int(self.ctx.config.data.get("attachments", {}).get("max_files", 10) or 0)
            self.cowork.composer.set_max_attachments(max_files)
            self.sidebar.refresh()
            self.statusBar().showMessage(tr("app.status.settings_saved"))

    def _goto(self, page: int, sub) -> None:
        self._ensure_page(page)                # build lazy page on first visit
        self.pages.setCurrentIndex(page)
        if page == self._ROW_WORKSPACE:
            self.workspace.refresh()           # re-list projects + threads on entry
        widget = self._page_widgets[page]
        if sub is not None and hasattr(widget, "select_subtab"):
            # Enforce the project gate here rather than at each entry point. A
            # greyed rail row cannot be clicked, but _goto is also reached from
            # RECENTS and from startup restore, and it used to open a sub-tab
            # the gate was holding shut — page shown, tab strip still hiding it.
            if hasattr(widget, "subtab_available") and not widget.subtab_available(sub):
                self.statusBar().showMessage(tr("app.nav.needs_project"), 4000)
            else:
                widget.select_subtab(sub)
        # Move the highlight with the content, however navigation was triggered —
        # a programmatic _goto used to leave it on whatever was clicked last.
        if not self._nav_building:
            self._select_nav_row(page, sub)
        self._update_dock_guard()
        # Switching pages updates which conversation is "current".
        self._refresh_history()

    def _update_dock_guard(self) -> None:
        """Keep the floating assistant clear of a screen's own bottom bar.

        Only Cowork has one (the composer). Everywhere else the dock sits in
        the corner as before.
        """
        dock = getattr(self, "help_agent", None)
        if dock is None:
            return
        guard = 0
        on_cowork = (self.pages.currentIndex() == self._ROW_WORKSPACE
                     and self.workspace.current_subtab() == self.workspace._cowork_tab_idx)
        if on_cowork:
            comp = getattr(self.cowork, "composer", None)
            if comp is not None and not comp.isHidden():
                # Measured from the composer's TOP edge in window coordinates:
                # its own height misses the extra row of controls laid out under
                # it, which left the dot still overlapping by ~25px.
                origin = comp.mapTo(self, comp.rect().topLeft())
                # ...but only lift the dot if the composer is actually beneath
                # it. The composer stops at the chat column's right edge, well
                # short of the dot, so lifting it there raised the dot 156px for
                # nothing — on Cowork alone it sat off the corner every other
                # screen keeps it in.
                dock_left = dock.x() - self.mapToGlobal(self.rect().topLeft()).x()
                dock_right = dock_left + dock.width()
                if dock_right > origin.x() and dock_left < origin.x() + comp.width():
                    guard = max(0, self.height() - origin.y() + 8)
        dock.set_bottom_guard(guard)

    def _on_projects_changed(self) -> None:
        self.sidebar.refresh()                 # History regroups by project
        self.cowork._apply_output_folder_label()  # project may have been renamed
        self.structure._refresh_project_combo()   # GraphRAG's project lock list follows too

    def _apply_theme(self) -> None:
        app = QApplication.instance()
        if app:
            set_active_theme(self.ctx.config.theme)
            app.setStyleSheet(stylesheet(self.ctx.config.theme))
        # Re-apply theme styles to chat bubbles so they adapt to the new theme.
        self.cowork.apply_theme()
        if getattr(self, "help_agent", None) is not None:
            self.help_agent.apply_theme()   # chat body follows theme (header stays fixed)

    # ---- sizing ------------------------------------------------------
    # Share of the available screen the window takes when it has room to. Fixed
    # pixels do not travel: 1180×760 fills a laptop and looks lost on a 4K
    # panel. `want_*` stays the floor so a small screen behaves as before.
    _SCREEN_SHARE_W, _SCREEN_SHARE_H = 0.80, 0.85

    def _fit_to_screen(self, want_w: int, want_h: int) -> None:
        screen = self.screen() or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else None
        if avail is None:
            self.resize(want_w, want_h)
            return
        margin = 60
        # Take a share of the screen, never less than the asked-for size and
        # never more than the screen can show.
        w = min(max(want_w, int(avail.width() * self._SCREEN_SHARE_W)),
                avail.width() - margin)
        h = min(max(want_h, int(avail.height() * self._SCREEN_SHARE_H)),
                avail.height() - margin)
        # minimum must never exceed what the screen can show
        self.setMinimumSize(min(820, avail.width() - margin), min(520, avail.height() - margin))
        self.resize(max(w, 1), max(h, 1))
        frame = self.frameGeometry()
        frame.moveCenter(avail.center())
        self.move(frame.topLeft())

    def moveEvent(self, event):  # noqa: N802 - Qt override
        super().moveEvent(event)
        # Dragged to another monitor: its work area (and scaling) may differ, so
        # the floating assistant re-pins and the panes re-decide if they fit.
        self._on_screen_maybe_changed()

    def _on_screen_maybe_changed(self) -> None:
        screen = self.screen()
        if screen is getattr(self, "_last_screen", None):
            return
        self._last_screen = screen
        avail = screen.availableGeometry() if screen else None
        if avail is not None:
            self.setMinimumSize(min(820, avail.width() - 60),
                                min(520, avail.height() - 60))
        if getattr(self, "help_agent", None) is not None:
            self._update_dock_guard()
            self.help_agent.reposition()

    # ---- lifecycle ---------------------------------------------------
    def closeEvent(self, event) -> None:  # noqa: N802
        keep = (self.tray is not None
                and self.ctx.config.data.get("tray", {}).get("minimize_on_close", True))
        if keep and not self._really_quit:
            # Keep running in the background; tasks continue and autosave.
            event.ignore()
            self.hide()
            try:
                self.tray.showMessage(
                    DISPLAY_NAME, tr("app.tray.running_body"),
                    QSystemTrayIcon.Information, 4000)
            except Exception:
                pass
            return
        # Real quit: stop every running turn (a tab may have several), then close.
        self.task_scheduler.stop()   # also stops any scheduled tasks
        if getattr(self, "routing_scheduler", None) is not None:
            self.routing_scheduler.stop()
        for tab in (self.cowork,):
            for w in tab.active_workers():
                if w.isRunning():
                    w.request_stop()
                    w.wait(1500)
        # Safely stop codebase-memory UI if the method exists
        if hasattr(self.structure, 'stop_cmem_ui'):
            self.structure.stop_cmem_ui()
        self.ctx.stop_mcp_connections()  # never leave a connected MCP server subprocess behind
        if self.tray is not None:
            self.tray.hide()
        super().closeEvent(event)


def _set_windows_app_id() -> None:
    """Make Windows use our window icon on the taskbar (not python.exe's)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FPT.CoworkLocal.2.0")
    except Exception:
        pass


def run(argv: List[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv
    _set_windows_app_id()
    app = QApplication.instance() or QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(app_icon())
    ctx = AppContext(AppConfig.load())
    set_language(ctx.config.language)
    # Built-in default skills (if any are bundled) are always-on and loaded
    # straight from the package; tidy away any copy seeded by older versions so they
    # stay hidden from the Skills manager.
    try:
        from .core.skills import prune_seeded_builtins
        prune_seeded_builtins()
    except Exception:  # noqa: BLE001 - housekeeping must never block startup
        pass
    # Seed the bundled built-in skill library + the built-in Co4E flow into the
    # user's editable stores on first run, so they show up in the Skill Manager
    # and the Flow sidebar out-of-the-box (a user-deleted one is not re-seeded).
    try:
        from .core.skills import seed_library_skills
        from .core.co4e_builtins import seed_builtin_flows
        changed = False
        # Content-versioned: returns the full tag list to persist (delivers updates
        # to shipped skills, preserves user edits to unchanged ones, respects deletion).
        skill_tags = seed_library_skills(ctx.config.seeded_library_skills)
        if set(skill_tags) != set(ctx.config.seeded_library_skills):
            ctx.config.seeded_library_skills = skill_tags
            changed = True
        new_flows = seed_builtin_flows(ctx.config.seeded_builtin_flows)
        if new_flows:
            ctx.config.seeded_builtin_flows = ctx.config.seeded_builtin_flows + new_flows
            changed = True
        if changed:
            ctx.config.save()
    except Exception:  # noqa: BLE001 - seeding must never block startup
        pass
    set_active_theme(ctx.config.theme)
    app.setStyleSheet(stylesheet(ctx.config.theme))

    # Follow the OS light/dark scheme live when theme is "Auto (System)".
    import socket

    from .core import audit_log, usage_tracker

    machine = socket.gethostname()
    usage_tracker.set_identity("local", machine, "")
    audit_log.set_identity("local", machine, "admin", "")

    win = MainWindow(ctx, user_name="local")

    def _reapply_system_theme(*_a):
        if ctx.config.theme == "system":
            set_active_theme("system")
            app.setStyleSheet(stylesheet("system"))
            win.cowork.apply_theme()
    try:
        app.styleHints().colorSchemeChanged.connect(_reapply_system_theme)
    except Exception:
        pass

    win.show()
    return app.exec()
