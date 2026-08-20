"""Rail icons must sit on one vertical line, and stay there when it collapses.

Two bugs this catches:
  · "Cài đặt" sat 42px right of "Dashboard"/"Giám sát" — its QSS margin pushed
    the button in while the tree rows above start at the rail edge.
  · Collapsing re-placed the icon of every label-less button, sliding ＋ to the
    middle of the 54px rail.

Runs with the app's real stylesheet loaded. Without it the window has no
padding, margins or borders and neither bug is visible — see _apply_theme.
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

TOL = 2   # px; anti-aliasing on an icon edge


def main() -> int:
    sandbox = _isolate_home()
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    _load_fonts()
    _freeze_schedulers()
    theme_name = _apply_theme(app)

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
    rail = win._nav_wrap

    def ink_x(w):
        """Leftmost painted pixel of a widget, in rail coordinates."""
        img = w.grab().toImage()
        bg = img.pixelColor(w.width() - 3, 2)
        for x in range(img.width()):
            for y in range(2, img.height() - 2):
                c = img.pixelColor(x, y)
                if (abs(c.red() - bg.red()) + abs(c.green() - bg.green())
                        + abs(c.blue() - bg.blue())) > 60:
                    return w.mapTo(rail, QPoint(x, 0)).x()
        return None

    def tree_text_x(tree):
        from PySide6.QtWidgets import QStyle, QStyleOptionViewItem
        index = tree.indexFromItem(tree.topLevelItem(0), 0)
        opt = QStyleOptionViewItem()
        tree.initViewItemOption(opt)
        opt.rect = tree.visualRect(index)
        tree.itemDelegate().initStyleOption(opt, index)
        txt = tree.style().subElementRect(QStyle.SE_ItemViewItemText, opt, tree)
        return tree.mapTo(rail, QPoint(txt.left(), 0)).x()

    def btn_text_x(w):
        """Left edge of the label: first ink past the icon's gap."""
        # Settings lays its own row out now, so read the label widget directly
        # rather than hunting for a gap in the painted pixels.
        lbl = getattr(win, "_nav_settings_text", None)
        if w is getattr(win, "_nav_settings_btn", None) and lbl is not None:
            return lbl.mapTo(rail, QPoint(0, 0)).x() if lbl.isVisible() else None
        if not w.text():
            return None
        img = w.grab().toImage()
        bg = img.pixelColor(w.width() - 3, 2)
        ink = []
        for x in range(img.width()):
            for y in range(2, img.height() - 2):
                c = img.pixelColor(x, y)
                if (abs(c.red() - bg.red()) + abs(c.green() - bg.green())
                        + abs(c.blue() - bg.blue())) > 60:
                    ink.append(x)
                    break
        if not ink:
            return None
        for a, b in zip(ink, ink[1:]):        # first gap = icon/label spacing
            if b - a > 2:
                return w.mapTo(rail, QPoint(b, 0)).x()
        return None

    def tree_icon_x(tree):
        from PySide6.QtWidgets import QStyle, QStyleOptionViewItem
        index = tree.indexFromItem(tree.topLevelItem(0), 0)
        opt = QStyleOptionViewItem()
        tree.initViewItemOption(opt)
        opt.rect = tree.visualRect(index)
        tree.itemDelegate().initStyleOption(opt, index)
        deco = tree.style().subElementRect(
            QStyle.SE_ItemViewItemDecoration, opt, tree)
        return tree.mapTo(rail, QPoint(deco.left(), 0)).x()

    def snapshot():
        app.processEvents()
        out = {"nav rows": tree_icon_x(win.nav),
               "bottom rows": tree_icon_x(win.nav_bottom),
               "bottom rows text": tree_text_x(win.nav_bottom)}
        for label, attr in (("MENU", "_nav_toggle_btn"),
                            ("new chat", "nav_new_chat"),
                            ("settings", "_nav_settings_btn")):
            w = getattr(win, attr, None)
            if w is not None and w.isVisible():
                out[label] = ink_x(w)
                if label == "settings":
                    out["settings text"] = btn_text_x(w)
        return out

    fails = []
    for theme_name in ("dark", "light"):
        _apply_theme(app, theme_name)
        app.processEvents()
        if win._nav_collapsed:
            win._toggle_nav()
        opened = snapshot()
        win._toggle_nav()
        app.processEvents()
        closed = snapshot()
        win._toggle_nav()
        app.processEvents()
        fails += compare(theme_name, rail, opened, closed)
        fails += column_widths_do_not_move_icons(win, app, theme_name)
        fails += rows_stay_under_the_header(win, app, theme_name)

    print()
    for f in fails:
        print(f"FAIL  {f}")
    print("PASS  every rail icon holds its line" if not fails
          else f"{len(fails)} problem(s)")
    sys.stdout.flush()
    os._exit(1 if fails else 0)


def rows_stay_under_the_header(win, app, theme_name):
    """The destinations start just below the ＋ button in both states.

    Collapsing hides RECENTS, the one item in the scroll body with a stretch
    factor. With nothing left to expand, a box layout centres what remains, and
    the whole group slid ~300px down the rail.
    """
    from PySide6.QtCore import QPoint

    rail = win._nav_wrap
    gaps = {}
    for state in ("open", "collapsed"):
        if (state == "collapsed") != win._nav_collapsed:
            win._toggle_nav()
        app.processEvents()
        btn = win.nav_new_chat
        below = btn.mapTo(rail, QPoint(0, btn.height())).y()
        top = win.nav.mapTo(rail, QPoint(0, 0)).y() +             win.nav.visualItemRect(win.nav.topLevelItem(0)).top()
        gaps[state] = top - below
    if win._nav_collapsed:
        win._toggle_nav()
        app.processEvents()
    print(f"  gap under ＋: open={gaps['open']}px collapsed={gaps['collapsed']}px")
    if abs(gaps["collapsed"] - gaps["open"]) > 4:
        return [f"{theme_name}: the destinations sit {gaps['collapsed']}px below "
                f"the ＋ button when collapsed but {gaps['open']}px when open"]
    return []


def column_widths_do_not_move_icons(win, app, theme_name):
    """The icon must not care how wide the column is.

    On the machine that reported this the column matched the rail and the icons
    sat in the middle; in a test render the column stayed wider than the view
    and the same code drew them at the left. So sweep the width and require the
    icon to hold still.
    """
    from PySide6.QtWidgets import QStyle, QStyleOptionViewItem

    if not win._nav_collapsed:
        win._toggle_nav()
        app.processEvents()
    fails, seen = [], {}
    # The invariant that matters. A centred decoration is the only way Qt can
    # put a label-less row's icon anywhere but the left edge, and how far it
    # travels depends on the box the column hands it — which is why this
    # reproduces on one machine and not another. Require the instruction
    # itself, not just the pixel it happens to produce here.
    from PySide6.QtCore import Qt as _Qt
    for tree_name in ("nav", "nav_bottom"):
        tree = getattr(win, tree_name)
        index = tree.indexFromItem(tree.topLevelItem(0), 0)
        opt = QStyleOptionViewItem()
        tree.initViewItemOption(opt)
        tree.itemDelegate().initStyleOption(opt, index)
        align = int(opt.decorationAlignment)
        if align & int(_Qt.AlignHCenter) or not align & int(_Qt.AlignLeft):
            fails.append(f"{theme_name} {tree_name}: decorationAlignment={align}"
                         f" — icon is free to drift off the left edge")
    for tree_name in ("nav", "nav_bottom"):
        tree = getattr(win, tree_name)
        keep = tree.columnWidth(0)
        for width in (tree.viewport().width(), 70, 100, 140):
            tree.setColumnWidth(0, width)
            app.processEvents()
            index = tree.indexFromItem(tree.topLevelItem(0), 0)
            opt = QStyleOptionViewItem()
            tree.initViewItemOption(opt)
            opt.rect = tree.visualRect(index)
            tree.itemDelegate().initStyleOption(opt, index)
            x = tree.style().subElementRect(
                QStyle.SE_ItemViewItemDecoration, opt, tree).left()
            seen.setdefault(tree_name, []).append((width, x))
        tree.setColumnWidth(0, keep)
        app.processEvents()
        xs = {x for _w, x in seen[tree_name]}
        if len(xs) > 1:
            fails.append(f"{theme_name} {tree_name}: icon x changes with the "
                         f"column width — {seen[tree_name]}")
    print(f"  column sweep: " + "  ".join(
        f"{n}={[x for _w, x in v]}" for n, v in seen.items()))
    win._toggle_nav()
    app.processEvents()
    return fails


def compare(theme_name, rail, opened, closed):
    print()
    print(f"theme={theme_name}")
    print(f"{'element':<12}{'open':>7}{'collapsed':>11}{'drift':>8}")
    fails = []
    for key in opened:
        a, b = opened[key], closed.get(key)
        drift = "-" if a is None or b is None else f"{b - a:+d}"
        print(f"{key:<12}{str(a):>7}{str(b):>11}{drift:>8}")
        if a is not None and b is not None and abs(b - a) > TOL:
            fails.append(f"{key}: icon moves {b - a:+d}px when the rail collapses")

    # Settings is a button but reads as one more row in the bottom list, so
    # both its icon and its label have to start where theirs do.
    for state, snap in (("open", opened), ("collapsed", closed)):
        for what in ("", " text"):
            ref, got = snap.get("bottom rows" + what), snap.get("settings" + what)
            if ref is not None and got is not None and abs(got - ref) > TOL:
                fails.append(f"{theme_name} {state}: settings{what} x={got} but "
                             f"the rows above it start at x={ref}")
    return fails


if __name__ == "__main__":
    raise SystemExit(main())
