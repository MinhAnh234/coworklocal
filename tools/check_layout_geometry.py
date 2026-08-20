"""Round 2: does the built layout have the SHAPE the wireframes draw?

Round 1 asks "does the feature exist". A screen can pass that and still be laid
out wrongly — right widgets, wrong order, wrong side, wrong proportions. This
round measures real geometry against what the audit page's wireframes depict:
reading order of the rail, section order down Monitoring, which side each pane
is on, and the size relationships the design calls out (hero card, the dot).

Run:  python tools/check_layout_geometry.py
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

from capture_screens import _apply_theme, _freeze_schedulers, _isolate_home, _load_fonts  # noqa: E402

# The rail, top to bottom, as the audit page's rail() helper draws it.
RAIL_ORDER = ["Project", "Cowork", "Co4E", "Thư mục", "GraphRAG", "Schedule Task"]
RAIL_BOTTOM = ["Dashboard", "Giám sát"]
# Monitoring ▸ Tổng quan, in the order the wireframe stacks it: what it cost →
# what the machine is doing → what the agent may touch → per-model prices →
# what actually happened.
MON_ORDER = ["ov_usage_group", "ov_resource_group", "ov_sandbox_details_group",
             "ov_pricing_group", "ov_activity_group", "ov_audit_group"]


def main() -> int:
    sandbox = _isolate_home()
    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    _load_fonts()
    _freeze_schedulers()

    _apply_theme(app)   # measure the styled window, not a bare one
    from cowork_local.config import AppConfig, CONFIG_DIR
    assert str(sandbox) in str(CONFIG_DIR), f"isolation failed: {CONFIG_DIR}"

    from seed_demo_data import seed
    seed()

    from cowork_local.app import MainWindow
    from cowork_local.i18n import set_language
    from cowork_local.state import AppContext

    set_language("vi")
    win = MainWindow(AppContext(AppConfig.load()), user_name="local")
    win.resize(1600, 950)
    win.show()
    for _ in range(8):
        app.processEvents()
    ws = win.workspace
    fails: list[str] = []

    def top_of(w, ref):
        return w.mapTo(ref, w.rect().topLeft()).y()

    def left_of(w, ref):
        return w.mapTo(ref, w.rect().topLeft()).x()

    # --- 1. rail: reading order, and the rail is on the LEFT ---------------
    rows = [win.nav.topLevelItem(i).text(0) for i in range(win.nav.topLevelItemCount())]
    bottom = [win.nav_bottom.topLevelItem(i).text(0)
              for i in range(win.nav_bottom.topLevelItemCount())]
    print(f"thanh menu  : {rows}")
    print(f"nhom day    : {bottom}")
    if rows != RAIL_ORDER:
        fails.append(f"thu tu thanh menu lech: {rows} != {RAIL_ORDER}")
    if bottom != RAIL_BOTTOM:
        fails.append(f"thu tu nhom day lech: {bottom} != {RAIL_BOTTOM}")
    rail_x = left_of(win._nav_wrap, win)
    content_x = left_of(win.pages, win)
    print(f"rail x={rail_x} · noi dung x={content_x}")
    if rail_x >= content_x:
        fails.append("rail khong nam ben trai noi dung")

    # --- 2. rail header order: picker ABOVE the new-chat button ------------
    py, by = top_of(win.nav_project, win), top_of(win.nav_new_chat, win)
    ry = top_of(win.nav_recents, win)
    ay = top_of(win._account_row, win)
    print(f"bo chon y={py} · nut chat moi y={by} · GAN DAY y={ry} · tai khoan y={ay}")
    if not (py < by < ry < ay):
        fails.append("thu tu doc cua rail sai (bo chon → chat moi → GAN DAY → tai khoan)")

    # --- 3. Monitoring: one column, sections in the drawn order ------------
    win._goto(win._ROW_MONITORING, None)
    for _ in range(8):
        app.processEvents()
    mon = win._page_widgets[win._ROW_MONITORING]
    tops = [(n, top_of(getattr(mon, n), mon)) for n in MON_ORDER if getattr(mon, n, None)]
    lefts = {n: left_of(getattr(mon, n), mon) for n, _y in tops}
    print("Monitoring, tu tren xuong:")
    for n, y in tops:
        print(f"   {n:28} y={y:5} x={lefts[n]}")
    if [n for n, _ in sorted(tops, key=lambda t: t[1])] != [n for n, _ in tops]:
        fails.append("thu tu muc trong Monitoring khong khop ban ve")
    # Sandbox and Permissions share a row; everything else is full width.
    perm_y = top_of(mon.ov_permissions_group, mon)
    sbx_y = top_of(mon.ov_sandbox_details_group, mon)
    same_row = abs(perm_y - sbx_y) < 20
    print(f"Sandbox | Quyen cung hang: {same_row}")
    if not same_row:
        fails.append("Sandbox va Quyen khong cung mot hang")
    price_w = mon.ov_pricing_group.width()
    res_w = mon.ov_resource_group.width()
    print(f"bang gia rong {price_w}px · tai nguyen {res_w}px (deu tron be ngang)")
    if price_w < res_w * 0.95:
        fails.append("bang gia model khong chiem tron be ngang")

    # --- 3b. Schedule: all seven lanes on screen, no horizontal scroll -----
    win._goto(win._ROW_SCHEDULE, None)
    for _ in range(8):
        app.processEvents()
    sched = win._page_widgets[win._ROW_SCHEDULE]
    from PySide6.QtWidgets import QScrollArea
    lanes = list(sched.columns.values())
    # The page holds more than one scroll area — take the one the lanes live in.
    board = next(sa for sa in sched.findChildren(QScrollArea)
                 if sa.isAncestorOf(lanes[0]))
    rightmost = max(left_of(c, board.widget()) + c.width() for c in lanes)
    fits = rightmost <= board.viewport().width() + 2
    print(f"Schedule: {len(lanes)} lane · mep phai x={rightmost} · "
          f"khung rong {board.viewport().width()} · vua mot man = {fits}")
    if len(lanes) != 7:
        fails.append(f"chi co {len(lanes)} lane, thiet ke la 7")
    if not fits:
        fails.append(f"lane thu 7 nam ngoai man ({rightmost} > "
                     f"{board.viewport().width()}) — phai cuon ngang")

    # --- 4. Dashboard: hero left, taller; supporting tiles in a 2x2 --------
    win._goto(win._ROW_DASHBOARD, None)
    for _ in range(8):
        app.processEvents()
    dash = win._page_widgets[win._ROW_DASHBOARD]
    hero, small = dash.card_cost, dash.card_total
    print(f"the Chi phi : x={left_of(hero, dash)} cao={hero.height()} · "
          f"the phu x={left_of(small, dash)} cao={small.height()}")
    if left_of(hero, dash) >= left_of(small, dash):
        fails.append("the Chi phi khong nam ben trai cac the phu")
    if hero.height() < small.height() * 1.5:
        fails.append("the Chi phi khong cao gap ruoi the phu")
    row1 = top_of(dash.card_total, dash)
    row2 = top_of(dash.card_out, dash)
    print(f"the phu hang 1 y={row1} · hang 2 y={row2} (phai la 2 hang)")
    if row2 <= row1:
        fails.append("4 the phu khong xep 2x2")

    # --- 5. Cowork: the dot clears the composer, and is the declared size --
    win._goto(win._ROW_WORKSPACE, ws._cowork_tab_idx)
    for _ in range(8):
        app.processEvents()
    dock = win.help_agent
    comp = ws._cowork.composer
    dock_bottom = top_of(dock, win) + dock.height()
    comp_top = top_of(comp, win)
    print(f"cham {dock.width()}x{dock.height()} · day y={dock_bottom} · o nhap dinh y={comp_top}")
    # Reading _DOT and comparing against it makes this unfailable — change the
    # constant and the expectation moves with it (check_probes_bite caught
    # exactly that). Bound what the design actually claims instead: a square
    # chip, big enough to hit, far smaller than the 84x64 button it replaced.
    # 26px was drawn, 52px is what the user asked for; 64 is the ceiling past
    # which "gọn" stops being true.
    if not 24 <= dock.width() <= 64 or dock.width() != dock.height():
        fails.append(f"cham tro ly {dock.width()}x{dock.height()}px, "
                     f"cho o khoang 24..64 va phai vuong")
    if dock_bottom > comp_top:
        fails.append("cham tro ly de len o nhap")
    if left_of(dock, win) + dock.width() > win.width():
        fails.append("cham tro ly tran ra ngoai cua so")

    # --- 6. Co4E: sidebar left, canvas middle, config right ---------------
    win._goto(win._ROW_WORKSPACE, ws._co4e_tab_idx)
    for _ in range(8):
        app.processEvents()
    import cowork_local.ui.co4e_tab as co4e_mod
    c4 = win.findChildren(co4e_mod.Co4ETab)[0]
    xs = [c4._split.widget(i).x() for i in range(c4._split.count())]
    print(f"Co4E 3 pane x = {xs}")
    if xs != sorted(xs):
        fails.append("thu tu 3 pane cua Co4E sai (trai → giua → phai)")
    heads = [h.text() for h, _b, _s in c4._sections.values()]
    print(f"cot sidebar: {heads}")
    if len(heads) != 4:
        fails.append(f"cot sidebar co {len(heads)} muc, ban ve ve 4")

    print()
    if fails:
        print("*** LECH BO CUC ***")
        for f in fails:
            print("   " + f)
        return 1
    print("KET QUA VONG 2: hinh hoc khop ban ve")
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
