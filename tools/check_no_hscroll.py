"""Prove the long dialogs never scroll sideways — including at large fonts.

The report that started this came from a display at 125–150% scaling, where
every label is wider than on a 100% screen. Rather than trusting one font size,
this runs each dialog at several point sizes and several widths and fails if any
horizontal scrollbar turns up, in the scroll area or in the section index.

Run:  python tools/check_no_hscroll.py
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

from capture_screens import _apply_theme, _isolate_home, _load_fonts  # noqa: E402

WIDTHS = (1100, 964, 820, 700)
POINTS = (9, 11, 14)          # ~100%, ~125%, ~150% display scaling


def hscroll(dlg, app):
    """(scroll-area overflow, index overflow) — each True means content is
    wider than the space it is given.

    A dialog built from step tabs has one scroll area per page, and a page that
    is not current has stale geometry — so each tab is brought to the front
    before its page is measured.
    """
    from PySide6.QtWidgets import QListWidget, QScrollArea
    over_area = False
    stack = getattr(dlg, "section_stack", None)
    if stack is not None:
        # One scroll area per section; a page that is not current has stale
        # geometry, so bring each to the front before measuring it.
        idx = dlg.section_list
        keep = idx.currentRow()
        for i in range(stack.count()):
            idx.setCurrentRow(i)
            for _ in range(3):
                app.processEvents()
            sa = stack.widget(i)
            if sa.widget().sizeHint().width() > sa.viewport().width():
                over_area = True
        idx.setCurrentRow(keep)
    else:
        sa = dlg.findChildren(QScrollArea)[0]
        over_area = sa.widget().sizeHint().width() > sa.viewport().width()
    idx = dlg.findChild(QListWidget, "sectionIndex")
    over_idx = False
    if idx is not None:
        over_idx = _index_elides(idx)
    return over_area, over_idx


def _index_elides(idx) -> bool:
    """True when a section name does not fit the visible width of the list.

    Two earlier attempts got this wrong:
      · `sizeHintForColumn(0) > viewport().width()` returns 182px at 9pt, 11pt
        and 14pt alike — it does not track the font, so it called the 9pt
        dialog broken while nothing on screen was clipped.
      · Asking the delegate whether it elides. It does not: the view lays each
        row out at its natural width and the viewport simply clips what runs
        past it, so a list squeezed to 90px still reported "no elision".

    So compare the painted text against the width that is actually on screen.
    """
    from PySide6.QtGui import QFontMetrics
    from PySide6.QtWidgets import QStyle, QStyleOptionViewItem

    for i in range(idx.count()):
        row = idx.indexFromItem(idx.item(i))
        opt = QStyleOptionViewItem()
        idx.initViewItemOption(opt)
        opt.rect = idx.visualRect(row)
        idx.itemDelegate().initStyleOption(opt, row)
        box = idx.style().subElementRect(QStyle.SE_ItemViewItemText, opt, idx)
        label = idx.item(i).text()
        visible = idx.viewport().width() - box.left()
        if QFontMetrics(opt.font).horizontalAdvance(label) > visible:
            return True
    return False


def main() -> int:
    sandbox = _isolate_home()
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    _load_fonts()

    _apply_theme(app)   # measure the styled widget, not a bare one
    from cowork_local.config import AppConfig, CONFIG_DIR
    assert str(sandbox) in str(CONFIG_DIR), f"isolation failed: {CONFIG_DIR}"

    from cowork_local.i18n import set_language
    from cowork_local.state import AppContext
    from cowork_local.ui.settings_dialog import SettingsDialog
    from cowork_local.ui.task_editor_dialog import TaskEditorDialog

    set_language("vi")
    ctx = AppContext(AppConfig.load())
    fails: list[str] = []

    for pt in POINTS:
        f = QFont(app.font())
        f.setPointSize(pt)
        app.setFont(f)
        for name, make in (("Cai dat", lambda: SettingsDialog(ctx)),
                           ("Task editor", lambda: TaskEditorDialog(ctx=ctx))):
            dlg = make()
            dlg.show()
            row = []
            for w in WIDTHS:
                dlg.resize(w, 900)
                for _ in range(4):
                    app.processEvents()
                over_area, over_idx = hscroll(dlg, app)
                row.append(f"{w}:{'A' if over_area else '.'}{'I' if over_idx else '.'}")
                if over_area:
                    fails.append(f"{name} @ {pt}pt {w}px — vung cuon tran ngang")
                if over_idx:
                    fails.append(f"{name} @ {pt}pt {w}px — muc luc tran ngang")
            print(f"  {pt:>2}pt  {name:12} {' '.join(row)}")
            dlg.close()
        print()

    print("A = vung cuon tran · I = muc luc tran · . = khong tran")
    print()
    if fails:
        print("*** LOI ***")
        for x in fails:
            print("   " + x)
        return 1
    print("KET QUA: khong hop thoai nao cuon ngang, o moi co chu va be rong da thu")
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
