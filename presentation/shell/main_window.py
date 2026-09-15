"""Cửa sổ chính — R08-T10.

Bóc nguyên khối ra khỏi ``app.py``. ``app.py`` giờ chỉ còn điểm vào của chương
trình: dựng QApplication, gọi Composition Root, mở cửa sổ.

Vì sao tách: ``app.py`` là nơi mọi thứ đổ về — nó vừa là điểm vào, vừa giữ cửa
sổ, vừa giữ thanh điều hướng, vừa giữ thanh trên cùng. Ai sửa bất cứ mảng nào
cũng phải mở đúng một file 1.293 dòng, và ba người sửa ba mảng khác nhau thì
đụng nhau ở cùng một chỗ.
"""
from __future__ import annotations

"""
pages (Dashboard / Schedule / Workspace / Cowork / Structure) and top bar."""

import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from ... import DISPLAY_NAME, __version__
from ...i18n import on_language_changed, tr
from .branding import app_icon
from .lifecycle_coordinator import LifecycleCoordinator
from .page_registry import PageRegistryMixin
from .rail_project import RailProjectMixin
from .session_events import SessionEventsMixin
from .toast import Toast
from .top_bar import TopBarMixin
from .nav_rail import NavRailMixin
from .rail_metrics import _NAV_MIN_WIDTH
from .tray_manager import TrayManager
from ...state import AppContext
from ...core.task_scheduler import TaskScheduler
from ...ui.sidebar import HistorySidebar
from ...ui.workspace_tab import WorkspaceTab




# Nav rail (sidebar navigation) widths — expanded shows icon+label, collapsed
# shows icon-only (still fully clickable, just narrower).
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







class MainWindow(NavRailMixin, RailProjectMixin, TopBarMixin,
                 PageRegistryMixin, SessionEventsMixin, QMainWindow):
    #: Biểu tượng khay, hoặc None nếu máy không có khay. Vẫn giữ tên cũ vì
    #: còn vài chỗ đọc thẳng self.tray; bản thân việc dựng/ẩn/thông báo đã
    #: chuyển sang self._tray (TrayManager).
    """Cửa sổ chính: thanh menu trái, thanh trên, bốn trang nội dung và khay hệ thống.

    Ghép từ nhiều mixin (thanh menu, bộ chọn project, thanh trên, sổ đăng ký
    trang, sự kiện phiên) để mỗi phần nằm trong một file dưới trần 400 dòng.
    """
    tray = property(lambda self: self._tray.icon)

    # Nav rows (Dashboard/Schedule/Monitoring are lazy; Workspace is the eager home page).
    _ROW_DASHBOARD, _ROW_SCHEDULE, _ROW_WORKSPACE, _ROW_MONITORING = 0, 1, 2, 3

    def __init__(self, ctx: AppContext, user_name: str = ""):
        """Dựng cửa sổ chính: thanh điều hướng, các trang và biểu tượng khay."""
        super().__init__()
        self.ctx = ctx
        self._user_name = user_name
        self._really_quit = False
        self._life = LifecycleCoordinator(self)
        # Khay hệ thống: presentation/shell/tray_manager.py (R08-T10).
        self._tray = TrayManager(self, icon=app_icon, tooltip=DISPLAY_NAME, tr=tr)
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
        from ...ui.cowork_tab import CoworkTab
        self.cowork = CoworkTab(ctx)
        self.structure = None
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

        self._build_nav_rail(right, rlay)
        # Land on the Workspace screen. Go through _goto so the page is actually
        # shown — selecting the row alone only moves the highlight (its signals
        # are blocked to avoid rebuild loops). Which Workspace sub-view the user
        # ends up looking at is settled after _restore_sessions(), below.
        self._goto(self._ROW_WORKSPACE, self.workspace.current_subtab())
        self.toast = Toast(self)   # top-left "task done" popup
        # Floating in-app Help assistant — a robot icon pinned bottom-right on
        # every screen; expands into a small help-only chat (see
        # ui/help_agent_widget.py). Managed in Monitoring → Agents Admin.
        from ...ui.help_agent_widget import HelpAgentWidget
        self.help_agent = HelpAgentWidget(ctx, self, user_name=self._user_name)
        self.help_agent.status_message.connect(self.statusBar().showMessage)

        self.statusBar().showMessage(tr("app.status.ready"))
        # Góc dưới phải: đúng một dòng phiên bản (cùng nguồn với tiêu đề cửa sổ).
        # Tắt size grip — nó vẽ một vệt ngay bên phải chữ; cửa sổ vẫn kéo được cạnh.
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().addPermanentWidget(QLabel(tr("app.version", v=__version__)))
        self._restore_sessions()
        # Open on "All projects…" — literally the same call the nav rail's link
        # of that name makes, so the rail highlight and the content can never
        # disagree. This runs AFTER the restore on purpose: _restore_sessions
        # still reloads the last thread, because recovering it after a crash is
        # the whole point of it, but the user should first see the list of
        # everything rather than whichever conversation happened to be open when
        # the app was last closed.
        self.goto_all_projects()
        self._tray.setup()
        # Start the task scheduler last, once the whole window exists — it
        # catches up any overdue tasks right away (first tick runs inline).
        self.task_scheduler.start()
        # Auto Model Routing: periodic reassess + pending-switch expiry. Runs
        # background probes only when genuinely due (never a burst at launch).
        try:
            from ...core.routing.scheduler import RoutingScheduler
            self.routing_scheduler = RoutingScheduler(self.ctx, self.ctx.routing(), parent=self)
            self.routing_scheduler.start()
        except Exception:  # noqa: BLE001 — routing must never block app startup
            self.routing_scheduler = None
        on_language_changed(self._retranslate)

    def resizeEvent(self, event):  # noqa: N802 - Qt override
        """Đổi kích thước cửa sổ thì tính lại trần bề rộng thanh menu.

        Trần là một tỉ lệ của cửa sổ nên phải tính lại ở đây; tính một lần lúc dựng
        sẽ đọc phải kích thước của cửa sổ chưa được cấp phát.
        """
        super().resizeEvent(event)
        # The rail's ceiling is a share of the window, so it moves with the
        # window. Computed once at construction it was read off a not-yet-sized
        # window and stuck at 162px on every monitor.
        if getattr(self, "_nav_wrap", None) is not None and not self._nav_collapsed:
            self._set_nav_width_range(_NAV_MIN_WIDTH, self._nav_max_width())
        # Keep the floating Help assistant pinned to the bottom-right corner.
        if getattr(self, "help_agent", None) is not None:
            # The Cowork composer can wrap an extra control row as the window
            # narrows/widens, which changes how much bottom guard the dock
            # needs — recompute it on every resize, not just reposition with
            # whatever guard height was last measured at tab-entry time.
            self._update_dock_guard()
            self.help_agent.reposition()

    def showEvent(self, event):  # noqa: N802 - Qt override
        """Lần hiện đầu tiên: ghim lại trợ lý nổi cho đúng vị trí thật."""
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
        """Dựng sẵn khung đồ thị GraphRAG lúc máy rảnh, để lần bấm đầu không giật."""
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
        if hasattr(self, "provider_lbl"):
            self.provider_lbl.setText(tr("app.provider"))
            # The label is hidden — the combo names itself through its tooltip
            # (see top_bar._build_account_row), so that is the one users read.
            self.provider_combo.setToolTip(tr("app.provider"))
        if hasattr(self, "nav_project"):
            self.nav_project.setToolTip(tr("app.nav.project_pick"))
            self.nav_recents_hdr.setText(tr("app.nav.recents"))
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
        self._tray.retranslate()
        # Thanh trạng thái (góc dưới bên trái) nhận thông báo từ hàng chục nơi
        # qua signal ``status_message``, và signal đó mang CHUỖI ĐÃ DỊCH chứ
        # không mang khoá — nên không thể dịch lại câu đang hiện. Đưa nó về câu
        # nền của ngôn ngữ mới: câu cũ không đọng lại bằng thứ tiếng vừa rời đi,
        # mà chỗ đó cũng không trống trơn. Thông báo là ghi chú về một việc vừa
        # xong, nên bỏ nó đi khi đổi ngôn ngữ không làm mất thông tin nào.
        self.statusBar().showMessage(tr("app.status.ready"))

    # ---- system tray (run in background when the window is closed) ---


    # ---- lazy page building -------------------------------------------



        # Monitoring KEEPS its own tab strip: its eight sub-views live in the
        # page, not in the rail. Workspace is the one that hides its strip,
        # because the rail lists its sub-views directly.


    # ---- flat nav rail -------------------------------------------------





    def _show_window(self) -> None:
        """Đưa cửa sổ trở lại từ khay hệ thống và kéo lên trước."""
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_app(self) -> None:
        """Thoát hẳn ứng dụng (khác với đóng cửa sổ về khay)."""
        self._really_quit = True
        self.close()


    # ---- top bar -----------------------------------------------------


    _BRAND_LOGO_NAMES = ("fpt_logo.png", "fpt-logo.png", "logo_fpt.png", "fpt_logo.jpg")
    _BRAND_LOGO_HEIGHT = 22


    _THEME_ICONS = {"system": "monitor", "dark": "moon", "light": "sun"}



    # ---- handlers ----------------------------------------------------




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



    # ---- sizing ------------------------------------------------------
    # Share of the available screen the window takes when it has room to. Fixed
    # pixels do not travel: 1180×760 fills a laptop and looks lost on a 4K
    # panel. `want_*` stays the floor so a small screen behaves as before.
    # Canh cửa sổ và tắt sạch: presentation/shell/lifecycle_coordinator.py
    def _fit_to_screen(self, want_w: int, want_h: int) -> None:
        """Canh cửa sổ vừa màn hình hiện tại."""
        self._life.fit_to_screen(want_w, want_h)

    def _on_screen_maybe_changed(self) -> None:
        """Cửa sổ có thể đã sang màn hình khác: ghim lại trợ lý và tính lại bố cục."""
        if not self._life.screen_maybe_changed():
            return
        if getattr(self, "help_agent", None) is not None:
            self._update_dock_guard()
            self.help_agent.reposition()


    def moveEvent(self, event):  # noqa: N802 - Qt override
        """Kéo cửa sổ sang màn hình khác thì vùng làm việc và tỉ lệ hiển thị có thể
        khác — trợ lý nổi ghim lại, các pane quyết định lại xem còn vừa không.
        """
        super().moveEvent(event)
        # Dragged to another monitor: its work area (and scaling) may differ, so
        # the floating assistant re-pins and the panes re-decide if they fit.
        self._on_screen_maybe_changed()


    # ---- lifecycle ---------------------------------------------------
    def closeEvent(self, event) -> None:  # noqa: N802
        """Đóng cửa sổ: thu về khay nếu cấu hình cho chạy nền, còn không thì thoát hẳn.

        Chạy nền tiếp thì task theo lịch vẫn chạy và vẫn tự lưu.
        """
        if self._life.should_keep_running():
            # Chạy nền tiếp: task vẫn chạy và vẫn tự lưu.
            event.ignore()
            self.hide()
            self._tray.show_message(DISPLAY_NAME, tr("app.tray.running_body"), msec=4000)
            return
        # Real quit: stop every running turn (a tab may have several), then close.
        self._life.shutdown()
        self._tray.hide()
        super().closeEvent(event)
