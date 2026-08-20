"""Check the Co4E sidebar rearrangement, on the real widget, offscreen.

Phase D only moved things and added a second door to "new flow". So the test
that matters is a subtraction test: every control that existed before must still
exist, the flow tab strip (which carries the pinned Runs tab and lets several
flows stay open) must be untouched, and the section headings must actually name
the list you are looking at — in all three languages.

Run:  python tools/check_co4e.py
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

# Every control the sidebar and the flow area had before these changes.
EXPECTED = [
    "wf_list", "wf_edit_btn", "wf_dup_btn", "wf_del_btn", "wf_runbg_btn",
    "agent_list", "ag_new_btn", "ag_edit_btn", "ag_del_btn",
    "skill_list", "sk_manage_btn",
    # Runs moved off the strip onto a toggle + a back button.
    "runs_btn", "runs_back_btn", "runs_table", "runs_side_list", "runs_more_btn",
    "name_edit", "add_step_btn", "save_btn", "save_tpl_btn", "mode_combo", "run_btn",
    "run_stop_btn", "run_rename_btn", "run_del_btn", "run_clear_btn", "ws_folder_btn",
]


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

    from cowork_local.i18n import set_language, tr
    from cowork_local.state import AppContext
    from cowork_local.ui.co4e_tab import Co4ETab

    set_language("vi")
    tab = Co4ETab(AppContext(AppConfig.load()))
    app.processEvents()

    fails: list[str] = []

    missing = [n for n in EXPECTED if getattr(tab, n, None) is None]
    print(f"control cu con nguyen : {len(EXPECTED) - len(missing)}/{len(EXPECTED)}")
    if missing:
        fails.append(f"mat control: {missing}")

    # The strip is gone from the screen, as the drawing asks.
    strip_shown = tab.flow_scroll.isVisible() or tab.flow_add_btn.isVisible()
    print(f"dai tab flow tren man : {strip_shown} (phai la False)")
    if strip_shown:
        fails.append("dai tab flow van con hien")

    # What the strip carried must still work. 1) Flow Status, both directions.
    tab.runs_btn.setChecked(True)
    app.processEvents()
    on_runs = tab.center_stack.currentIndex() == 0
    tab.runs_back_btn.click()
    app.processEvents()
    back = tab.center_stack.currentIndex() == 1
    print(f"Flow Status: mo = {on_runs} · quay ve flow = {back} "
          f"· nut gat dang bat = {tab.runs_btn.isChecked()}")
    if not (on_runs and back):
        fails.append("khong di/ve duoc trang Flow Status")
    if tab.runs_btn.isChecked():
        fails.append("nut gat Flow Status khong tra ve trang thai tat")

    # 2) Opening a flow from the list REPLACES the one on the canvas — one at a
    #    time now, which is the part of the old strip that genuinely goes away.
    from cowork_local.core import co4e as _co4e
    tab._open_flow(_co4e.new_workflow("Flow A"))
    app.processEvents()
    tab._open_flow(_co4e.new_workflow("Flow B"))
    app.processEvents()
    print(f"mo 2 flow lien tiep   : con {len(tab._flows)} flow tren canvas "
          f"({tab._wf.name!r})")
    if len(tab._flows) != 1:
        fails.append(f"cho 1 flow mo cung luc, thay {len(tab._flows)}")

    # One column, four named sections — no icon tabs left.
    from PySide6.QtWidgets import QTabWidget
    heads = [h.text() for h, _b, _s in tab._sections.values()]
    print(f"cot sidebar           : {heads}")
    if len(heads) != 4:
        fails.append(f"cho 4 muc trong cot sidebar, thay {len(heads)}")
    if tab.sidebar.findChildren(QTabWidget):
        fails.append("van con tab icon trong sidebar")

    # Every list visible at once — that is the point of dropping the tabs.
    tab.show()
    app.processEvents()
    shown = [n for n in ("wf_list", "agent_list", "skill_list", "runs_side_list")
             if not getattr(tab, n).isHidden()]
    print(f"danh sach hien cung luc: {shown}")
    if len(shown) != 4:
        fails.append(f"chi {len(shown)}/4 danh sach hien cung luc")

    # Headings fold their section, so a short window can still reach everything.
    head, body, _s = tab._sections["co4e.tab_agents"]
    head.setChecked(False)
    app.processEvents()
    folded = body.isHidden()
    head.setChecked(True)
    app.processEvents()
    print(f"gap/mo muc AGENTS      : gap = {folded} · mo lai = {not body.isHidden()}")
    if not folded:
        fails.append("bam tieu de khong gap duoc muc")

    # Both new-flow doors must land on the same slot.
    print(f"'Moi' canh WORKFLOWS  : {tab.wf_new_btn.text()!r}")
    before = tab._wf.name
    tab.wf_new_btn.click()
    app.processEvents()
    print(f"bam 'Moi' -> flow tren canvas {before!r} -> {tab._wf.name!r}")
    if tab._wf.name == before:
        fails.append("nut 'Moi' canh WORKFLOWS khong tao flow moi")

    # The action buttons that act on a selection stayed with the list.
    print(f"nut duoi danh sach     : agents = "
          f"{[b.toolTip() for b in (tab.ag_edit_btn, tab.ag_del_btn)]}")

    # --- small screens ------------------------------------------------------
    # The complaint that started this: on a laptop the four lists squeezed down
    # to one row each. Check real geometry at a few window heights.
    print()
    for w, h in ((1920, 1080), (1366, 768), (1280, 720)):
        tab.resize(w, h)
        app.processEvents()
        app.processEvents()
        heights = {n: getattr(tab, n).height()
                   for n in ("wf_list", "agent_list", "skill_list", "runs_side_list")}
        rows = {n: (getattr(tab, n).height() // max(1, getattr(tab, n).sizeHintForRow(0) or 18))
                for n in heights}
        print(f"{w}x{h}: cao = {heights} · so dong thay duoc = {rows}")
        thin = [n for n, v in heights.items() if v < 50]
        if thin:
            fails.append(f"o {w}x{h}, danh sach qua thap: {thin}")

    # Folding must hand its height to the others, not just hide the body.
    tab.resize(1280, 720)
    app.processEvents()
    before = tab.wf_list.height()
    for key in ("co4e.tab_skills", "co4e.runs_tab"):
        tab._sections[key][0].setChecked(False)
    app.processEvents(); app.processEvents()
    after = tab.wf_list.height()
    print(f"gap SKILLS + FLOW STATUS -> WORKFLOWS cao {before} -> {after}px")
    if after <= before:
        fails.append("gap muc khac ma WORKFLOWS khong duoc them cho")
    for key in ("co4e.tab_skills", "co4e.runs_tab"):
        tab._sections[key][0].setChecked(True)
    app.processEvents()

    print()
    for lang in ("vi", "en", "ja"):
        set_language(lang)
        tab._retranslate()
        app.processEvents()
        texts = [h.text() for h, _b, _s in tab._sections.values()]
        print(f"  {lang}: {texts}")
        print(f"        nut moi = {tab.wf_new_btn.text()!r}"
              f" · runs = {tab.runs_btn.text()!r} / {tab.runs_back_btn.text()!r}")
        if any(not t or "CO4E." in t for t in texts):
            fails.append(f"thieu ban dich tieu de muc cho {lang}")
    set_language("vi")

    print()
    if fails:
        print("*** LOI ***")
        for f in fails:
            print("   " + f)
        return 1
    print("KET QUA: Co4E sap xep lai, khong mat control nao")
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
