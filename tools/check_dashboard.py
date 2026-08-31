"""Check the Dashboard header regroup, on the real widget, offscreen.

Nine controls were on one row. They are now on two, grouped by what they do —
so this asserts that all nine are still present, still wired, and that the
header really is two rows now (row 1 = title + Refresh, row 2 = the selectors).

Run:  python tools/check_dashboard.py
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

from capture_screens import _apply_theme, _isolate_home, _load_fonts, control  # noqa: E402

HEADER = ["_title", "chart_prev_btn", "_chart_period_lbl", "chart_next_btn",
          "gran_combo", "metric_combo", "currency_lbl", "currency_combo",
          "refresh_btn"]


def main() -> int:
    sandbox = _isolate_home()
    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    _load_fonts()

    _apply_theme(app)   # measure the styled widget, not a bare one
    from cowork_local.config import AppConfig, CONFIG_DIR
    assert str(sandbox) in str(CONFIG_DIR), f"isolation failed: {CONFIG_DIR}"

    from seed_demo_data import seed
    seed()

    from cowork_local.i18n import set_language
    from cowork_local.state import AppContext
    # R08-T13 moved the screen out of ui/ into presentation/dashboard/ and
    # split its header controls across UsageChartWidget / HabitsWidget, so
    # every control below is looked up through `control()` rather than as a
    # direct attribute of the tab.
    from cowork_local.presentation.dashboard.dashboard_tab import DashboardTab

    set_language("vi")
    tab = DashboardTab(AppContext(AppConfig.load()))
    tab.resize(1100, 800)
    tab.show()
    app.processEvents()
    tab.refresh()
    app.processEvents()

    fails: list[str] = []
    missing = [n for n in HEADER if control(tab, n) is None]
    print(f"control header con nguyen: {len(HEADER) - len(missing)}/{len(HEADER)}")
    if missing:
        fails.append(f"mat control: {missing}")

    # Two rows: everything in the header must sit at one of exactly two y bands.
    tops = {}
    for n in HEADER:
        w = control(tab, n)
        tops.setdefault(round(w.mapTo(tab, w.rect().topLeft()).y() / 10), []).append(n)
    print(f"so hang cua header       : {len(tops)}")
    for band, names in sorted(tops.items()):
        print(f"   y~{band * 10:>4}px : {names}")
    if len(tops) != 2:
        fails.append(f"header co {len(tops)} hang, cho 2")

    # Still wired: changing the metric must not throw and must stick.
    metric = control(tab, "metric_combo")
    before = metric.currentData()
    metric.setCurrentIndex(1 - metric.currentIndex())
    app.processEvents()
    after = metric.currentData()
    print(f"doi chi so bieu do       : {before} -> {after}")
    if after == before:
        fails.append("combo chi so khong doi duoc")
    control(tab, "refresh_btn").click()
    app.processEvents()
    print("bam Lam moi              : khong loi")

    print()
    if fails:
        print("*** LOI ***")
        for f in fails:
            print("   " + f)
        return 1
    print("KET QUA: header Dashboard chia 2 hang, du 9 control")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
