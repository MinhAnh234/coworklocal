"""A drop-list must have room for its text and for the tick beside it.

macOS marks the current row with a checkmark; Windows does not. The language
combo is only as wide as "VN", and the popup inherits that width, so on macOS
the tick landed on top of the two letters. Reported from a Mac, so this checks
the property that made it possible rather than the platform.
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
    from PySide6.QtWidgets import QApplication, QStyle

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
    win.resize(1400, 900)
    win.show()
    app.processEvents()

    fails = []
    from PySide6.QtWidgets import QStyledItemDelegate
    for name in ("language_combo", "nav_project", "provider_combo"):
        combo = getattr(win, name, None)
        if combo is None or not combo.count():
            continue
        view = combo.view()
        fm = view.fontMetrics()
        longest = max(fm.horizontalAdvance(combo.itemText(i))
                      for i in range(combo.count()))
        tick = combo.style().pixelMetric(QStyle.PM_IndicatorWidth, None, combo)
        need = longest + tick
        have = max(view.minimumWidth(), combo.width())
        print(f"{name:15}: chu dai nhat {longest:>4}px + dau tick {tick:>3}px "
              f"= can {need:>4}px | popup rong {have:>4}px")
        if have < need:
            fails.append(f"{name}: popup {have}px, khong du {need}px cho chu + dau tick")

        # No tick: the row is already tinted, and the menu-style delegate that
        # draws one on macOS covered the two letters it was marking.
        deleg = combo.itemDelegate()
        plain = type(deleg) is QStyledItemDelegate
        print(f"{'':15}  delegate={type(deleg).__name__} (khong ve dau tick={plain})")
        if not plain:
            fails.append(f"{name}: dung delegate kieu menu — macOS se ve dau tick")

        # ...and the current row must still be obvious without one.
        view = combo.view()
        sheet = app.styleSheet()
        if "selection-background-color" not in sheet:
            fails.append("popup khong to mau muc dang chon")

    print()
    for f in fails:
        print("FAIL  " + f)
    print("PASS  moi drop-list du cho chu va dau tick" if not fails
          else f"{len(fails)} problem(s)")
    sys.stdout.flush()
    os._exit(1 if fails else 0)


if __name__ == "__main__":
    raise SystemExit(main())
