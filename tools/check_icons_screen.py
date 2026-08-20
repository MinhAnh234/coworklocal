"""The Icon library screen against its wireframe.

The drawing (section 16) puts the three actions on the title row, a magnifier
in the search box, caps section headings, and — its stated complaint — a
visible edge on an icon cell when you hover or select it, so you can tell what
you are about to pick.
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
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QApplication, QLineEdit

    app = QApplication([])
    _load_fonts()
    _freeze_schedulers()
    _apply_theme(app)

    from cowork_local.config import CONFIG_DIR
    assert str(sandbox) in str(CONFIG_DIR), f"isolation failed: {CONFIG_DIR}"

    from cowork_local.config import AppConfig
    from cowork_local.i18n import set_language
    from cowork_local.state import AppContext
    from cowork_local.ui.icons_admin_tab import IconsAdminTab

    set_language("vi")
    tab = IconsAdminTab(AppContext(AppConfig.load()))
    tab.resize(1100, 700)
    tab.show()
    app.processEvents()

    fails = []

    # 1. actions on the title row, to its right — not in a strip below the
    #    grids. Comparing y alone was not enough: a button left out of the
    #    layout sits at (0,0), which is "the same row" by accident.
    title = tab._title
    t_pos = title.mapTo(tab, QPoint(0, 0))
    t_mid = t_pos.y() + title.height() // 2
    t_right = t_pos.x() + title.width()
    for name, btn in (("Thêm", tab.add_btn), ("Dán", tab.paste_btn),
                      ("Xóa", tab.del_btn)):
        pos = btn.mapTo(tab, QPoint(0, 0))
        mid = pos.y() + btn.height() // 2
        aligned = abs(mid - t_mid) <= 6
        after = pos.x() >= t_right
        print(f"nut {name:5}: tam y={mid} (tieu de {t_mid}) thang hang={aligned} "
              f"| x={pos.x()} (sau tieu de {t_right})={after}")
        if not (aligned and after):
            fails.append(f"nut {name} khong nam cung hang, ben phai tieu de")

    # 2. magnifier in the search box
    lead = tab.search.actions()
    print(f"o tim co icon kinh lup: {bool(lead)}")
    if not lead:
        fails.append("o tim thieu icon kinh lup")

    # 3. caps headings
    for name, lbl in (("tich hop", tab._builtin_lbl), ("tuy chinh", tab._custom_lbl)):
        text = lbl.text()
        print(f"tieu de {name}: {text!r}")
        if text != text.upper():
            fails.append(f"tieu de {name} chua viet hoa: {text!r}")

    # 4. the cell has an edge to see — compare the painted cell hovered vs not
    grid = tab.builtin_grid
    if grid.count():
        rect = grid.visualItemRect(grid.item(0))
        plain = grid.grab(rect).toImage()
        grid.setCurrentRow(0)
        app.processEvents()
        picked = grid.grab(rect).toImage()
        diff = sum(1 for x in range(plain.width()) for y in range(plain.height())
                   if plain.pixelColor(x, y) != picked.pixelColor(x, y))
        print(f"o icon doi {diff} diem anh khi duoc chon")
        if diff == 0:
            fails.append("o icon khong doi gi khi duoc chon — khong thay minh dang chon cai nao")
    else:
        fails.append("luoi icon rong")

    print()
    for f in fails:
        print("FAIL  " + f)
    print("PASS  man Icon khop ban ve" if not fails else f"{len(fails)} problem(s)")
    sys.stdout.flush()
    os._exit(1 if fails else 0)


if __name__ == "__main__":
    raise SystemExit(main())
