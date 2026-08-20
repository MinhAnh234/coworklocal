"""The splitter handle beside the rail has to actually move the rail.

setFixedWidth left it drawn but inert: it looked draggable and did nothing.
Also checks that a width the user drags to survives a collapse/expand, and
that collapsing still pins the rail at 54px.
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

    from cowork_local.app import (
        _NAV_COLLAPSED_WIDTH, _NAV_MIN_WIDTH, MainWindow)
    from cowork_local.config import AppConfig
    from cowork_local.i18n import set_language
    from cowork_local.state import AppContext

    set_language("vi")
    win = MainWindow(AppContext(AppConfig.load()), user_name="local")
    win.resize(1400, 900)
    win.show()
    app.processEvents()

    fails = []
    rail, split = win._nav_wrap, win.split

    def drag_to(px):
        """What the splitter does when the handle is dragged."""
        total = sum(split.sizes())
        split.setSizes([px, max(1, total - px)])
        app.processEvents()
        win._on_split_moved(px, 1)
        app.processEvents()
        return rail.width()

    start = rail.width()
    wide = drag_to(300)
    print(f"keo rong : {start} -> {wide}px")
    if wide <= start:
        fails.append(f"keo tay nam ra 300px ma rail van {wide}px")

    narrow = drag_to(_NAV_MIN_WIDTH)
    print(f"keo hep  : {wide} -> {narrow}px")
    if narrow >= wide:
        fails.append(f"keo hep lai khong an: {narrow}px")

    # The ceiling is a share of the window now, so ask the window for it.
    ceiling = win._nav_max_width()
    over = drag_to(ceiling + 200)
    print(f"keo qua max: {over}px (tran {ceiling} = {ceiling * 100 // win.width()}% cua so)")
    if over > ceiling:
        fails.append(f"rail vuot tran: {over} > {ceiling}")

    under = drag_to(20)
    print(f"keo duoi min: {under}px (san {_NAV_MIN_WIDTH})")
    if under < _NAV_MIN_WIDTH:
        fails.append(f"rail thap hon san: {under} < {_NAV_MIN_WIDTH}")

    # a dragged width has to come back after a fold
    chosen = drag_to(min(280, win._nav_max_width()))
    win._toggle_nav()
    app.processEvents()
    folded = rail.width()
    print(f"thu gon  : {folded}px")
    if folded != _NAV_COLLAPSED_WIDTH:
        fails.append(f"thu gon phai la {_NAV_COLLAPSED_WIDTH}px, dang {folded}px")
    win._toggle_nav()
    app.processEvents()
    back = rail.width()
    print(f"mo lai   : {back}px (da chon {chosen}px)")
    if abs(back - chosen) > 4:
        fails.append(f"mo lai quen be rong da keo: {back} thay vi {chosen}")

    # The ceiling is a share, so it has to move with the window — it was read
    # once at construction and stuck at 162px on every monitor.
    seen = {}
    for w in (1280, 1600, 1936):
        win.resize(w, 900)
        app.processEvents()
        split.setSizes([2000, 1])       # drag the handle as far right as it goes
        app.processEvents()
        seen[w] = (rail.width(), win._nav_max_width())
        print(f"cua so {w}: keo het co -> {seen[w][0]}px (tran {seen[w][1]}px)")
    for w, (got, ceiling) in seen.items():
        if abs(got - ceiling) > 4:
            fails.append(f"cua so {w}: keo het chi duoc {got}px, tran la {ceiling}px")
    if len({c for _g, c in seen.values()}) == 1:
        fails.append("tran khong doi theo be rong cua so — dang la px co dinh")

    print()
    for f in fails:
        print("FAIL  " + f)
    print("PASS  tay nam keo duoc, nho be rong qua lan gap" if not fails
          else f"{len(fails)} problem(s)")
    sys.stdout.flush()
    os._exit(1 if fails else 0)


if __name__ == "__main__":
    raise SystemExit(main())
