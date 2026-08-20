"""The assistant dot sits in the bottom-right corner — unless the composer is
genuinely underneath it.

It used to lift on Cowork whenever a composer existed, measured only on the
vertical axis. On a wide window the composer stops at the chat column's right
edge, far short of the dot, so the dot rose 156px for nothing and Cowork was
the one screen where it was not in the corner.
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

from capture_screens import (  # noqa: E402
    _apply_theme, _freeze_schedulers, _isolate_home, _load_fonts)


def main() -> int:
    sandbox = _isolate_home()
    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    _load_fonts()
    _freeze_schedulers()
    _apply_theme(app)

    from cowork_local.config import CONFIG_DIR
    assert str(sandbox) in str(CONFIG_DIR), f"isolation failed: {CONFIG_DIR}"

    from seed_demo_data import seed
    seed()

    from cowork_local.app import MainWindow
    from cowork_local.config import AppConfig
    from cowork_local.i18n import set_language
    from cowork_local.state import AppContext

    set_language("vi")
    win = MainWindow(AppContext(AppConfig.load()), user_name="local")
    win.show()
    dock = win.help_agent
    fails = []

    def gap_and_overlap(width, height):
        win.resize(width, height)
        app.processEvents()
        win._goto(win._ROW_WORKSPACE, win.workspace._cowork_tab_idx)
        app.processEvents()
        comp = win.cowork.composer
        origin = comp.mapTo(win, comp.rect().topLeft())
        dleft = dock.x() - win.mapToGlobal(win.rect().topLeft()).x()
        overlaps = (dleft + dock.width() > origin.x()
                    and dleft < origin.x() + comp.width())
        gap = win.height() - (dock.y() + dock.height())
        return gap, overlaps, origin.x() + comp.width(), dleft

    # baseline: every other screen
    win.resize(1936, 1048)
    app.processEvents()
    win._goto(win._ROW_WORKSPACE, win.workspace._project_tab_idx)
    app.processEvents()
    corner = win.height() - (dock.y() + dock.height())
    print(f"man thuong      : cach day {corner}px")

    for w, h in ((1936, 1048), (1200, 800), (900, 700)):
        gap, over, comp_right, dleft = gap_and_overlap(w, h)
        print(f"Cowork {w}x{h:<5}: cach day {gap:>4}px | composer het o x={comp_right} "
              f"| cham o x={dleft} | chong nhau={over}")
        if over and gap <= corner:
            fails.append(f"{w}x{h}: composer nam duoi cham ma cham khong duoc nang")
        if not over and gap != corner:
            fails.append(f"{w}x{h}: khong chong nhau ma cham van lech "
                         f"({gap}px thay vi {corner}px)")

    print()
    for f in fails:
        print("FAIL  " + f)
    print("PASS  cham o goc, chi nang khi that su bi che" if not fails
          else f"{len(fails)} problem(s)")
    sys.stdout.flush()
    os._exit(1 if fails else 0)


if __name__ == "__main__":
    raise SystemExit(main())
