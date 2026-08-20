"""Does the layout adapt across screen sizes AND display scalings?

Two things change between machines, and only one of them is width:

  * the screen is bigger or smaller — more or fewer pixels to lay out in;
  * the display scale is 100/125/150% — the SAME number of logical pixels
    holds less, because every label and margin is taller.

A breakpoint written as a raw pixel number only holds on the machine it was
tuned on. This walks a grid of (window size × font scale) and, for each cell,
checks that no screen is clipped and that the panes folded when they had to.

Run:  python tools/check_multi_screen.py
"""
from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from capture_screens import _apply_theme, _freeze_schedulers, _isolate_home, _load_fonts  # noqa: E402

# Real-world panels, from a small laptop up to 4K-at-150%-effective.
SIZES = [(1280, 720), (1366, 768), (1600, 900), (1920, 1080), (2560, 1440)]
# 9pt ≈ 100%, 11pt ≈ 125%, 14pt ≈ 150% of the design baseline.
POINTS = [9, 11, 14]


def main() -> int:
    sandbox = _isolate_home()
    from PySide6.QtGui import QFont
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
    from cowork_local.ui.widgets import ui_scale

    set_language("vi")
    fails: list[str] = []
    print(f"{'co chu':>7} {'cua so':>11} {'thang do':>9}  {'man bi bo':>10}  panel da gap")
    print("-" * 86)

    for pt in POINTS:
        f = QFont(app.font())
        f.setPointSize(pt)
        app.setFont(f)
        win = MainWindow(AppContext(AppConfig.load()), user_name="local")
        win.show()
        for _ in range(6):
            app.processEvents()
        ws = win.workspace
        dests = [("Project", win._ROW_WORKSPACE, ws._project_tab_idx),
                 ("Cowork", win._ROW_WORKSPACE, ws._cowork_tab_idx),
                 ("Co4E", win._ROW_WORKSPACE, ws._co4e_tab_idx),
                 ("Folder", win._ROW_WORKSPACE, ws._folder_tab_idx),
                 ("GraphRAG", win._ROW_WORKSPACE, ws._graphrag_tab_idx),
                 ("Schedule", win._ROW_SCHEDULE, None),
                 ("Dashboard", win._ROW_DASHBOARD, None),
                 ("Monitoring", win._ROW_MONITORING, None)]

        for w, h in SIZES:
            win.resize(w, h)
            for _ in range(6):
                app.processEvents()
            clipped = []
            for name, page, sub in dests:
                win._goto(page, sub)
                for _ in range(4):
                    app.processEvents()
                widget = win._page_widgets[page]
                if widget.minimumSizeHint().width() > widget.width() + 1:
                    clipped.append(name)
            folded = []
            if getattr(ws, "_is_narrow", False):
                folded.append("pane Project/History")
            import cowork_local.ui.co4e_tab as co4e_mod
            c4 = win.findChildren(co4e_mod.Co4ETab)[0]
            if c4._config_collapsed:
                folded.append("panel cau hinh Co4E")
            scale = ui_scale(win)
            print(f"{pt:>5}pt {w:>5}x{h:<5} {scale:>8.2f}  "
                  f"{(', '.join(clipped) or 'khong'):>10}  {', '.join(folded) or '-'}")
            if clipped:
                fails.append(f"{pt}pt {w}x{h}: bi bo — {clipped}")
        # The window must never demand more than the smallest panel we support.
        need = win.minimumSizeHint().width()
        if need > SIZES[0][0]:
            fails.append(f"{pt}pt: cua so doi toi thieu {need}px, "
                         f"rong hon man nho nhat ({SIZES[0][0]}px)")
        print(f"{'':>7} {'':>11} {'':>9}  cua so doi toi thieu: {need}px")
        win.close()
        del win
        for _ in range(3):
            app.processEvents()

    print()
    if fails:
        print("*** KHONG THICH UNG DUOC ***")
        for x in fails:
            print("   " + x)
        return 1
    print("KET QUA: bo cuc thich ung o moi co man hinh va muc phong chu da thu")
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
