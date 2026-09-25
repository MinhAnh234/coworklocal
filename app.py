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
from .presentation.shell.bootstrap import build_context
from .presentation.shell.branding import app_icon
from .presentation.shell.main_window import MainWindow

# Các checker trong tools/ và mã cũ vẫn import mấy tên này từ cowork_local.app.
# Giữ đường vào cũ để việc bóc tách không kéo theo sửa 24 file checker; nơi ở
# thật của chúng nay là presentation/shell/.
from .presentation.shell.rail_metrics import (  # noqa: E402,F401
    _NAV_COLLAPSED_WIDTH, _NAV_EXPANDED_WIDTH, _NAV_MAX_CEILING, _NAV_MAX_SHARE,
    _NAV_MIN_WIDTH, _NAV_ROW_GAP, _NAV_ROW_INSET, _NavItemDelegate,
)
from .presentation.shell.toast import Toast as _Toast  # noqa: E402,F401

from .presentation.shell.lifecycle_coordinator import LifecycleCoordinator
from .presentation.shell.tray_manager import TrayManager
from .state import AppContext
from .ui.widgets import tidy_popup
from .theme import current_palette, set_active_theme, stylesheet
from .core.task_scheduler import TaskScheduler
from .presentation.dashboard.dashboard_tab import DashboardTab
from .presentation.graph.structure_graph_view import StructureGraphView
from .presentation.scheduling.schedule_task_tab import ScheduleTaskTab
from .ui.cowork_tab import CoworkTab
from .ui.monitoring_tab import MonitoringTab
from .ui.settings_dialog import SettingsDialog
from .ui.sidebar import HistorySidebar
from .ui.workspace_tab import WorkspaceTab


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
    """Điểm vào ứng dụng: dựng Composition Root, gieo dữ liệu mặc định, áp theme
    rồi mở cửa sổ chính.

    Mọi bước gieo (skill dựng sẵn, flow dựng sẵn) đều bọc trong ``try`` — việc
    dọn nhà không bao giờ được phép chặn app khởi động.
    """
    argv = argv if argv is not None else sys.argv
    _set_windows_app_id()
    app = QApplication.instance() or QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(app_icon())
    try:
        from .config import CONFIG_DIR
        from .presentation.shell import crash_guard
        crash_guard.install(Path(CONFIG_DIR) / "logs")
    except Exception:  # noqa: BLE001 - crash logging must never block startup
        crash_guard = None
    # Composition Root: presentation/shell/bootstrap.py quyết định app chạy
    # bằng mảnh nào. Từ R02, đó là JsonConfigRepository + kho bí mật của hệ
    # điều hành, không còn config.py::AppConfig.
    ctx = build_context()
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
        """Theme đang để "Theo hệ thống" thì áp lại mỗi khi Windows đổi sáng/tối."""
        if ctx.config.theme == "system":
            set_active_theme("system")
            app.setStyleSheet(stylesheet("system"))
            win.cowork.apply_theme()
    try:
        app.styleHints().colorSchemeChanged.connect(_reapply_system_theme)
    except Exception:
        pass

    win.show()
    if crash_guard is not None:
        try:
            watchdog = crash_guard.HangWatchdog(DISPLAY_NAME, win)
            app.aboutToQuit.connect(watchdog.stop)
        except Exception:  # noqa: BLE001
            pass
    return app.exec()
