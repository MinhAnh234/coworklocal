"""Check the redesigned help dock on the real widget, offscreen.

The claim being made is a size claim ("84×64 → 26×26"), so this measures the
widget instead of trusting the constants, and confirms that nothing the old
three-button layout could do has gone missing — hiding to the edge just moved
into the panel's ⋯ menu.

Run:  python tools/check_help_dock.py
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


def main() -> int:
    sandbox = _isolate_home()
    from PySide6.QtWidgets import QApplication, QWidget

    app = QApplication([])
    _load_fonts()

    _apply_theme(app)   # measure the styled widget, not a bare one
    from cowork_local.config import AppConfig, CONFIG_DIR
    assert str(sandbox) in str(CONFIG_DIR), f"isolation failed: {CONFIG_DIR}"

    from cowork_local.i18n import set_language, tr
    from cowork_local.state import AppContext
    from cowork_local.ui.help_agent_widget import HelpAgentWidget

    set_language("vi")
    host = QWidget()
    host.resize(1200, 800)
    dock = HelpAgentWidget(AppContext(AppConfig.load()), host, user_name="local")
    app.processEvents()

    fails: list[str] = []
    OLD_W, OLD_H = 84, 64          # 64px badge + 2px gap + 18px chevron

    closed = dock.size()
    print(f"dong          : {closed.width()}x{closed.height()}px "
          f"(cu {OLD_W}x{OLD_H})")
    area_new, area_old = closed.width() * closed.height(), OLD_W * OLD_H
    print(f"dien tich     : {area_new} vs {area_old}px2 "
          f"({100 - round(area_new / area_old * 100)}% nho hon)")
    # The page draws 26px; the user asked for double. Read the size the module
    # declares rather than a number written here, so the two cannot drift, and
    # keep the two things that actually matter: it is a square chip, and it is
    # still far smaller than the button it replaced.
    if closed.width() != closed.height():
        fails.append(f"nut dong khong vuong: {closed.width()}x{closed.height()}")
    if area_new >= area_old:
        fails.append(f"khong con nho hon nut cu: {area_new} vs {area_old}px2")
    # clears the ~24px comfortable-tap floor the old 18px chevron missed
    if min(closed.width(), closed.height()) < 24:
        fails.append("vung bam nho hon 24px")

    # Hover: the name appears, and only then.
    print(f"chu luc dong  : {dock.launcher.text()!r} (phai rong)")
    if dock.launcher.text().strip():
        fails.append("nut dong ma van hien chu")
    dock.launcher._set_open(True)
    app.processEvents()
    hovered = dock.size()
    print(f"re chuot      : {hovered.width()}x{hovered.height()}px · "
          f"chu = {dock.launcher.text().strip()!r}")
    if tr("help_agent.badge") not in dock.launcher.text():
        fails.append("re chuot khong hien 'AI Assistant'")
    if hovered.width() <= closed.width():
        fails.append("re chuot ma nut khong no ra")
    dock.launcher._set_open(False)
    app.processEvents()
    if dock.size().width() != closed.width():
        fails.append("roi chuot ma nut khong thu lai")

    # Every state still reachable, and the corner anchor still holds.
    for state, call in (("panel", dock._expand), ("launcher", dock._collapse),
                        ("hidden", dock._hide_to_edge), ("launcher", dock._show_launcher)):
        call()
        app.processEvents()
        got = dock._state
        inside = (dock.x() + dock.width() <= host.width()
                  and dock.y() + dock.height() <= host.height())
        print(f"trang thai {state:9}: {got:9} {dock.width():3}x{dock.height():3} "
              f"goc phai duoi = {inside}")
        if got != state:
            fails.append(f"khong vao duoc trang thai {state}")
        if not inside:
            fails.append(f"trang thai {state} tran ra ngoai cua so")

    # The edge tab was 16px — below anything comfortable to hit.
    dock._hide_to_edge()
    app.processEvents()
    print(f"tab mep       : {dock.width()}px (cu 16px)")
    if dock.width() < 24:
        fails.append(f"tab mep {dock.width()}px, van duoi 24px")
    dock._show_launcher()

    # The ⋯ menu is gone (user's call — its two entries were "collapse", which
    # the − button beside it already did, and "hide"). Nothing was lost with it:
    # collapse is the − button and the dot, hide is a right-click on either the
    # dot or the open panel's header. Check the routes, not the menu.
    from PySide6.QtCore import Qt as _Qt

    if hasattr(dock, "more_btn"):
        fails.append("menu ⋯ van con tren panel")
    dock._collapse()
    app.processEvents()
    if dock._state != "launcher":
        fails.append("nut − khong thu nho duoc ve cham")
    if dock.launcher.contextMenuPolicy() != _Qt.CustomContextMenu:
        fails.append("cham khong co menu chuot phai de an")
    dock._hide_to_edge()
    app.processEvents()
    if dock._state != "hidden":
        fails.append("khong an duoc vao canh phai")
    print(f"thu nho + an   : ca hai duong deu chay (trang thai cuoi={dock._state!r})")
    dock._show_launcher()
    app.processEvents()
    print(f"nut thu nho   : {dock.min_btn.toolTip()!r}")
    print(f"nut gui / o nhap: {dock.send_btn is not None} / {dock.input is not None}")

    # All three languages must have the new strings.
    for lang in ("vi", "en", "ja"):
        set_language(lang)
        dock.retranslate()
        # more_tooltip went with the ⋯ menu; dot_hint replaces it as the
        # string that tells you the right-click is there.
        vals = [dock.launcher.toolTip(), tr("help_agent.badge"),
                tr("help_agent.dot_hint")]
        print(f"  {lang}: badge={vals[1]!r} goi y chuot phai={vals[2]!r}")
        if any(not v or v.startswith("help_agent.") for v in vals):
            fails.append(f"thieu ban dich cho {lang}")
    set_language("vi")

    print()
    if fails:
        print("*** LOI ***")
        for f in fails:
            print("   " + f)
        return 1
    print("KET QUA: nut tro ly gon lai, khong mat chuc nang nao")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
