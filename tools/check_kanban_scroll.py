"""Schedule Task must not scroll sideways on a screen the app supports.

Two separate causes, both reported as "some screens scroll, some don't":
  · each lane is a QListWidget whose column hint runs a few px past its own
    viewport, so individual lanes grew a scrollbar at most window widths;
  · the seven lanes together wanted 1242px where a 1280 window leaves 1091.
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

# Smallest screen the app is expected to run on, and the rail at both extremes.
SIZES = [(1280, 720), (1366, 768), (1600, 900), (1920, 1080), (1936, 1048)]


def main() -> int:
    sandbox = _isolate_home()
    from PySide6.QtWidgets import QAbstractScrollArea, QApplication, QScrollArea

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
    app.processEvents()

    fails = []
    for w, h in SIZES:
        # 150 is the default and 240 a realistic widening. 360 (the maximum)
        # on a 1280 screen leaves 920px for seven lanes that need 1067 — that
        # scroll is the user's own trade, so it is reported, not failed.
        for rail in (150, 240, 360):
            win.resize(w, h)
            app.processEvents()
            win.split.setSizes([rail, max(1, w - rail)])
            win._goto(win._ROW_SCHEDULE, None)
            app.processEvents()

            page = [p for p in win._page_widgets
                    if p is not None and hasattr(p, "counts_lbl")][0]
            outer = page.findChild(QScrollArea)
            lanes = [s for s in win.findChildren(QAbstractScrollArea)
                     if s.isVisible() and s.__class__.__name__ == "_KanbanColumn"]
            spill = outer.horizontalScrollBar().maximum()
            lane_spill = [s.horizontalScrollBar().maximum() for s in lanes]
            worst = max(lane_spill) if lane_spill else 0
            print(f"{w}x{h} rail={rail:<4}: {len(lanes)} lan rong "
                  f"{lanes[0].width() if lanes else 0:>4} | vung ngoai thua {spill:>4}px "
                  f"| lan thua toi da {worst}px")
            if spill and rail < 360:
                fails.append(f"{w}x{h} rail={rail}: 7 lan tran {spill}px")
            elif spill:
                print(f"      (rail keo het co: nguoi dung tu chon, thua {spill}px)")
            if worst:
                fails.append(f"{w}x{h} rail={rail}: mot lan tu tran {worst}px")

    print()
    for f in fails:
        print("FAIL  " + f)
    print("PASS  khong cuon ngang o moi co man hinh da thu" if not fails
          else f"{len(fails)} problem(s)")
    sys.stdout.flush()
    os._exit(1 if fails else 0)


if __name__ == "__main__":
    raise SystemExit(main())
