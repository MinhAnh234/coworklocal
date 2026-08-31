"""Round 3: is every control in the inventory still in the built app?

docs/screens/controls.json was extracted from the source by AST before the
redesign started. Rounds 1 and 2 ask whether the new shape is right; this one
asks the opposite question — whether rearranging dropped anything.

A control counts as alive if the attribute still exists on its screen's widget
AND is a real QWidget. Ones that were deliberately moved or replaced are listed
in MOVED with where they went, so an intentional change reads differently from
an accidental loss.

Run:  python tools/check_controls_alive.py
"""
from __future__ import annotations

import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from capture_screens import (  # noqa: E402
    _apply_theme, _freeze_schedulers, _isolate_home, _load_fonts, owner_of,
)

# controls.json lists every control in a FILE, and several files hold more than
# one class (schedule_task_tab.py alone has the tab plus three dialogs). Only
# the screen's own class lives on the widget we can inspect, so each control is
# attributed to its class first, using the file as it was when the inventory
# was taken — that is the baseline commit, not today's line numbers.
BASELINE = "291a611"


def class_ranges(path: str) -> list[tuple[str, int, int]]:
    """(class name, first line, last line) from the file at BASELINE."""
    import ast
    import subprocess
    try:
        src = subprocess.run(["git", "show", f"{BASELINE}:{path}"],
                             cwd=REPO, capture_output=True, text=True,
                             encoding="utf-8", check=True).stdout
    except Exception:                                        # noqa: BLE001
        return []
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    return [(n.name, n.lineno, max(getattr(x, "lineno", n.lineno)
                                   for x in ast.walk(n)))
            for n in tree.body if isinstance(n, ast.ClassDef)]


def owning_class(ranges, line: int) -> str:
    for name, start, end in ranges:
        if start <= line <= end:
            return name
    return ""


# Controls that are gone ON PURPOSE, with what replaced them. Anything missing
# and NOT listed here is a regression.
MOVED = {
    "ui\\help_agent_widget.py": {
        "self.collapse_btn": "→ mục 'Ẩn trợ lý' trong menu ⋯ của panel",
    },
    "ui\\monitoring_tab.py": {
        # e6adfd9 turned one Refresh in the Monitoring header into one per
        # table (page.title_refresh_btn on Bảo mật / MCP / Hành động / Agent).
        # Tổng quan gets none because it auto-refreshes every 3s (_REFRESH_MS);
        # Icon has nothing to refresh.
        "self.refresh_btn": "→ nút 'Làm mới' riêng trên từng bảng (title_refresh_btn)",
    },
    "ui\\schedule_task_tab.py": {
        "self.view_combo": "→ cặp tab Kanban | Lịch (view_tabs)",
    },
    "ui\\folder_tab.py": {
        "self.path_edit": "→ tiêu đề màn (path_lbl)",
    },
    "ui\\structure_graph_view.py": {
        "self._msgs_toggle_btn": "→ cặp tab Đồ thị | Tin nhắn (view_tabs)",
        # R08-T14 split the screen and renamed these two on the way out. Both
        # are still on screen, under a new owner and a new name, so they are
        # deliberate moves rather than losses.
        "self._ag_collapse": "→ GraphQaWidget._collapse_btn (nút thu gọn bảng Agent)",
        "self._msgs_view": "→ GraphMessagesView.widget (cây Tin nhắn theo ngày)",
    },
    "app.py": {
        "self.settings_btn": "→ nút Cài đặt ở đáy rail (_nav_settings_btn)",
    },
}

# The class whose controls each owner widget actually holds.
MAIN_CLASS = {
    "app.py": "MainWindow",
    "ui\\workspace_tab.py": "WorkspaceTab",
    "ui\\cowork_tab.py": "CoworkTab",
    "ui\\chat_panel.py": "ChatPanel",
    "ui\\composer.py": "Composer",
    "ui\\sidebar.py": "HistorySidebar",
    "ui\\co4e_tab.py": "Co4ETab",
    "ui\\folder_tab.py": "FolderTab",
    "ui\\structure_graph_view.py": "StructureGraphView",
    "ui\\schedule_task_tab.py": "ScheduleTaskTab",
    "ui\\dashboard_tab.py": "DashboardTab",
    "ui\\monitoring_tab.py": "MonitoringTab",
    "ui\\help_agent_widget.py": "HelpAgentWidget",
}

# Which built widget owns each source file's controls.
def owners(win):
    ws = win.workspace
    import cowork_local.ui.co4e_tab as co4e_mod
    return {
        "app.py": win,
        "ui\\workspace_tab.py": ws,
        "ui\\cowork_tab.py": ws._cowork,
        "ui\\chat_panel.py": ws._cowork,
        "ui\\composer.py": ws._cowork.composer,
        "ui\\sidebar.py": win.sidebar,
        "ui\\co4e_tab.py": win.findChildren(co4e_mod.Co4ETab)[0],
        "ui\\folder_tab.py": ws.tabs.widget(ws._folder_tab_idx),
        "ui\\structure_graph_view.py": ws.tabs.widget(ws._graphrag_tab_idx),
        "ui\\schedule_task_tab.py": win._page_widgets[win._ROW_SCHEDULE],
        "ui\\dashboard_tab.py": win._page_widgets[win._ROW_DASHBOARD],
        "ui\\monitoring_tab.py": win._page_widgets[win._ROW_MONITORING],
        "ui\\help_agent_widget.py": win.help_agent,
    }


def main() -> int:
    sandbox = _isolate_home()
    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    _load_fonts()
    _freeze_schedulers()

    _apply_theme(app)   # measure the styled window, not a bare one
    from cowork_local.config import AppConfig, CONFIG_DIR
    assert str(sandbox) in str(CONFIG_DIR), f"isolation failed: {CONFIG_DIR}"

    from seed_demo_data import seed
    seed()

    from cowork_local.app import MainWindow
    from cowork_local.i18n import set_language
    from cowork_local.state import AppContext

    set_language("vi")
    win = MainWindow(AppContext(AppConfig.load()), user_name="local")
    win.resize(1600, 950)
    win.show()
    # Build every lazy page before looking for its controls.
    for row in (win._ROW_DASHBOARD, win._ROW_SCHEDULE, win._ROW_MONITORING):
        win._goto(row, None)
        for _ in range(6):
            app.processEvents()
    for sub in range(win.workspace.tabs.count()):
        win._goto(win._ROW_WORKSPACE, sub)
        for _ in range(6):
            app.processEvents()

    index = json.loads((REPO / "docs" / "screens" / "controls.json")
                       .read_text(encoding="utf-8"))
    own = owners(win)

    alive = dead = moved = skipped = other_class = relocated = 0
    losses: list[tuple[str, str, str]] = []
    moves: list[tuple[str, str, str]] = []
    for rec in index:
        holder = own.get(rec["file"])
        if holder is None:
            skipped += len(rec["controls"])
            continue
        ranges = class_ranges(rec["file"].replace("\\", "/"))
        want = MAIN_CLASS.get(rec["file"], "")
        for c in rec["controls"]:
            var = c["var"]
            if not var.startswith("self."):
                skipped += 1
                continue
            # Belongs to a dialog defined in the same file → not on this widget.
            if ranges and want and owning_class(ranges, c["line"]) != want:
                other_class += 1
                continue
            name = var.split(".", 1)[1]
            if getattr(holder, name, None) is not None:
                alive += 1
            elif var in MOVED.get(rec["file"], {}):
                moved += 1
            else:
                # EPIC R08 extracted sub-widgets out of every screen, so a
                # control can still be on screen while no longer being a direct
                # attribute of the screen's own widget (FolderTab.mode_btn ->
                # FolderTab.preview.mode_btn). Searching the subtree keeps the
                # subtraction test honest: it still fails on a control that is
                # genuinely gone, but a relocation now reads as a relocation.
                sub = owner_of(holder, name)
                if sub is not None:
                    relocated += 1
                    moves.append((rec["file"], var, type(sub).__name__))
                else:
                    dead += 1
                    losses.append((rec["file"], var,
                                   c.get("label_vi") or c.get("label") or "?"))

    print(f"control con song    : {alive}")
    print(f"co y doi cho        : {moved}")
    for f, v, w in [(f, v, MOVED[f][v]) for f in MOVED for v in MOVED[f]]:
        print(f"   {v:26} {w}")
    print(f"doi cho khi tach     : {relocated}  (con tren man, nam trong widget con)")
    for f, var, own in sorted(moves):
        print(f"   {var:26} -> {own}.{var.split('.', 1)[1]}")
    print(f"thuoc class khac    : {other_class}  (hop thoai dinh nghia cung file)")
    print(f"khong kiem duoc     : {skipped}  (dialog dung rieng, bien cuc bo)")
    print(f"MAT                 : {dead}")
    for f, var, label in losses:
        print(f"   ! {f}: {var}  ({label})")
    print()
    if dead:
        print("*** VONG 3 THAT BAI: co control bien mat ***")
        return 1
    print("KET QUA VONG 3: khong control nao bien mat ngoai y muon")
    return 0


if __name__ == "__main__":
    _rc = main()
    # Qt (WebEngine especially) crashes during interpreter teardown with
    # 0xC0000409 AFTER the work is done, which would mask the real result —
    # and check_probes_bite reads these exit codes to decide whether a probe
    # caught its mutation. Leave immediately with the verdict instead.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_rc)
