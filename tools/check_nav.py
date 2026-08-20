"""Smoke-test the flat nav rail against a real MainWindow.

Builds the window offscreen on a COPY of ~/.cowork_local (schedulers no-oped, so
nothing scheduled can fire) and answers the questions the redesign has to get
right:

  * is every destination that used to be reachable still reachable?
  * does the rail highlight follow the content, from clicks AND from _goto?
  * do the project-gated rows stay listed (greyed) instead of disappearing?
  * does Monitoring still expose all eight sub-views, now via its own tab strip?

Run:  python tools/check_nav.py
"""
from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO.parent))                        # `import cowork_local`
sys.path.insert(0, str(Path(__file__).resolve().parent))    # sibling tools
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from capture_screens import _apply_theme, _freeze_schedulers, _isolate_home, _load_fonts  # noqa: E402


def rows(tree):
    from PySide6.QtCore import Qt
    out = []
    for i in range(tree.topLevelItemCount()):
        it = tree.topLevelItem(i)
        data = it.data(0, Qt.UserRole) or {}
        out.append((it.text(0), data.get("page"), data.get("sub"),
                    not it.isDisabled()))
    return out


def main() -> int:
    sandbox = _isolate_home()
    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    _load_fonts()
    _freeze_schedulers()

    _apply_theme(app)   # measure the styled window, not a bare one
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
    app.processEvents()

    fails: list[str] = []
    print("THANH MENU CHINH")
    for label, page, sub, on in rows(win.nav):
        print(f"   {label:22} page={page} sub={sub}  {'' if on else '(mo — chua chon project)'}")
    print("NHOM GHIM DAY")
    for label, page, sub, on in rows(win.nav_bottom):
        print(f"   {label:22} page={page} sub={sub}")
    print(f"NUT: {win._nav_settings_btn.text()}")
    print()

    main_rows, bottom_rows = rows(win.nav), rows(win.nav_bottom)
    n_total = len(main_rows) + len(bottom_rows)
    # Five Workspace sub-views + Schedule, then Dashboard + Monitoring.
    if len(main_rows) != 6:
        fails.append(f"thanh chinh co {len(main_rows)} dong, cho 6")
    if len(bottom_rows) != 2:
        fails.append(f"nhom day co {len(bottom_rows)} dong, cho 2")
    if any(sub is not None for _l, _p, sub, _o in bottom_rows):
        fails.append("nhom day khong duoc mang sub-tab")

    # The two gated rows must be PRESENT (that is the point) — greyed is fine.
    labels = [r[0] for r in main_rows]
    ws_labels = [lab for lab, _i, _ic, _on in win.workspace.nav_entries()]
    for lab in ws_labels:
        if lab not in labels:
            fails.append(f"mat dong Workspace: {lab}")
    print(f"du 5 man Workspace tren thanh menu: {all(l in labels for l in ws_labels)}"
          f"  ({', '.join(ws_labels)})")

    # Highlight must follow the content for every row, both ways round.
    # Re-fetch items by index every time: navigating can rebuild the rail, which
    # deletes the C++ objects a held reference points at.
    ok_click = ok_goto = 0
    for which, name in ((win.nav, "chinh"), (win.nav_bottom, "day")):
        for i in range(which.topLevelItemCount()):
            label, page, sub, on = rows(which)[i]
            if not on:
                continue
            which.setCurrentItem(which.topLevelItem(i))    # as if clicked
            app.processEvents()
            if win.pages.currentIndex() == page:
                ok_click += 1
            else:
                fails.append(f"bam '{label}' ({name}) khong mo dung trang")
            win._goto(page, sub)                           # programmatic
            app.processEvents()
            cur = next((t.currentItem() for t in (win.nav, win.nav_bottom)
                        if t.currentItem() is not None and t.currentItem().isSelected()), None)
            if cur is not None and cur.text(0) == label:
                ok_goto += 1
            else:
                fails.append(f"_goto toi '{label}' nhung vet sang o "
                             f"'{cur.text(0) if cur else 'khong dau'}'")
    n_live = sum(1 for r in main_rows + bottom_rows if r[3])
    print(f"bam mo dung trang        : {ok_click}/{n_live}")
    print(f"vet sang theo _goto      : {ok_goto}/{n_live}")

    # Only one row may look active across the two lists.
    lit = sum(1 for t in (win.nav, win.nav_bottom) for i in range(t.topLevelItemCount())
              if t.topLevelItem(i).isSelected())
    print(f"so dong dang sang        : {lit} (phai la 1)")
    if lit != 1:
        fails.append(f"{lit} dong cung sang")

    # Monitoring's eight sub-views moved to its own tab strip — check it is shown.
    win._ensure_page(win._ROW_MONITORING)
    mon = win._page_widgets[win._ROW_MONITORING]
    # isVisible() is False for everything while the window has never been shown;
    # isHidden() asks the question that actually matters here.
    strip_visible = not mon.tabs.tabBar().isHidden() if hasattr(mon, "tabs") else False
    n_sub = len(mon.nav_subtabs())
    print(f"Monitoring: {n_sub} man, dai tab hien = {strip_visible}")
    if n_sub != 8:
        fails.append(f"Monitoring chi con {n_sub} man")
    if not strip_visible:
        fails.append("dai tab Monitoring van bi an — 8 man khong toi duoc")

    # Workspace's own strip stays hidden: the rail lists those five instead.
    ws_strip = not win.workspace.tabs.tabBar().isHidden()
    print(f"Workspace: dai tab hien = {ws_strip} (phai la False — thanh menu lo roi)")
    if ws_strip:
        fails.append("dai tab Workspace hien lai — trung voi thanh menu")

    # The whole point of the change: with no project selected the two gated rows
    # must stay in place, greyed — not vanish and resize the menu.
    win.workspace._update_tab_visibility(False)
    app.processEvents()
    gated = rows(win.nav)
    off = [lab for lab, _p, _s, on in gated if not on]
    print()
    print(f"chua chon project   : van du {len(gated)} dong, mo: {off or 'khong'}")
    if len(gated) != len(main_rows):
        fails.append(f"chua chon project thi thanh menu con {len(gated)} dong "
                     f"(truoc {len(main_rows)}) — item van bien mat")
    if len(off) != 2:
        fails.append(f"cho 2 dong bi mo (Cowork, GraphRAG), thay {len(off)}")

    # --- rail header: project picker + new chat (Phase A) ------------------
    print()
    n_proj = win.nav_project.count()
    print(f"bo chon project : {n_proj} muc · dang chon "
          f"{win.nav_project.currentText()!r}")
    print(f"nut chat moi    : {win.nav_new_chat.text()!r} "
          f"(bat = {win.nav_new_chat.isEnabled()})")
    if win.nav_project.currentData() != win.workspace.selected_project_id():
        fails.append("bo chon project khong khop voi project dang chon")

    # Picking in the rail must move the real selection, not just the combo.
    if n_proj > 1:
        other = next(i for i in range(n_proj)
                     if win.nav_project.itemData(i) != win.workspace.selected_project_id())
        want = win.nav_project.itemData(other)
        win.nav_project.setCurrentIndex(other)
        app.processEvents()
        got = win.workspace.selected_project_id()
        print(f"doi project tu rail: chon {want} -> workspace dang o {got}")
        if got != want:
            fails.append("doi project tren rail khong doi project that")
        if win.nav_project.currentData() != got:
            fails.append("bo chon khong dong bo nguoc lai")

    # New chat from any screen: lands on Cowork with an empty thread, and the
    # old toolbar button must still be there.
    win._goto(win._ROW_DASHBOARD, None)
    app.processEvents()
    before = win.cowork.current_session_id() if hasattr(win.cowork, "current_session_id") else None
    win._on_rail_new_chat()
    app.processEvents()
    on_cowork = (win.pages.currentIndex() == win._ROW_WORKSPACE
                 and win.workspace.current_subtab() == win.workspace._cowork_tab_idx)
    print(f"bam '＋ chat moi' tu Dashboard -> dung o Cowork: {on_cowork}")
    if not on_cowork:
        fails.append("nut chat moi khong dua toi Cowork")
    old_btn = getattr(win.cowork, "_new_btn", None)
    print(f"nut cu tren thanh Cowork con nguyen: {old_btn is not None} "
          f"({old_btn.text()!r})" if old_btn is not None else "MAT NUT CU")
    if old_btn is None:
        fails.append("nut 'Cuoc tro chuyen moi' cu tren Cowork bi mat")

    # --- rail RECENTS (Phase B) --------------------------------------------
    from PySide6.QtCore import Qt as _Qt
    win._refresh_rail_recents()
    app.processEvents()
    rec = win.nav_recents
    items = [(rec.topLevelItem(i).text(0), rec.topLevelItem(i).data(0, _Qt.UserRole) or {})
             for i in range(rec.topLevelItemCount())]
    threads = [t for t, d in items if d.get("path")]
    print()
    print(f"GAN DAY ({win.nav_recents_hdr.text()}): {len(threads)} thread"
          f" + dong '{items[-1][0]}'")
    for t in threads:
        print(f"   {t}")
    if not items[-1][1].get("all"):
        fails.append("thieu dong 'Tat ca project…'")
    if len(threads) > win._RAIL_RECENTS:
        fails.append(f"GAN DAY liet ke {len(threads)} thread, toi da {win._RAIL_RECENTS}")

    # Scoped to the active project — a flat cross-project list would lose that.
    pid = win.workspace.selected_project_id()
    all_titles = {t["title"] for t in win.workspace.recent_threads(99)}
    other_pid = next((p for _n, p in win.workspace.project_choices() if p != pid), "")
    if other_pid:
        win.workspace.choose_project(other_pid)
        app.processEvents()
        win._refresh_rail_recents()
        other_titles = {t["title"] for t in win.workspace.recent_threads(99)}
        print(f"doi sang project khac: danh sach doi = {other_titles != all_titles}")
        if other_titles & all_titles and other_titles == all_titles:
            fails.append("GAN DAY khong gom theo project — hai project cung mot danh sach")
        win.workspace.choose_project(pid)
        app.processEvents()
        win._refresh_rail_recents()

    # Clicking a thread must open it through the normal route.
    if threads:
        win._goto(win._ROW_DASHBOARD, None)
        app.processEvents()
        # Re-fetch: the project switch above rebuilt this list, deleting the
        # items a held reference would point at.
        win._on_rail_recent(win.nav_recents.topLevelItem(0))
        app.processEvents()
        on_cowork = (win.pages.currentIndex() == win._ROW_WORKSPACE
                     and win.workspace.current_subtab() == win.workspace._cowork_tab_idx)
        print(f"bam thread gan day -> mo o Cowork: {on_cowork}")
        if not on_cowork:
            fails.append("bam thread trong GAN DAY khong mo duoc")

    # The full History panel must still exist, with all its controls.
    sb = win.sidebar
    kept = [n for n in ("search_box", "search_btn", "tree", "_collapse_btn")
            if getattr(sb, n, None) is not None]
    print(f"khung History day du van con: {len(kept)}/4 control goc {kept}")
    if len(kept) != 4:
        fails.append("khung History bi mat control")

    # --- account row moved off the top bar (Phase C) -----------------------
    print()
    from PySide6.QtWidgets import QWidget as _QWidget
    top_kids = {w.objectName() or type(w).__name__
                for w in win.findChildren(_QWidget)
                if w.parent() is not None and w.parent().objectName() == "topbar"}
    print(f"top bar con lai : {sorted(top_kids)}")
    for name in ("provider_combo", "language_combo", "theme_btn"):
        w = getattr(win, name, None)
        if w is None:
            fails.append(f"mat control {name}")
            continue
        in_rail = win._nav_wrap.isAncestorOf(w)
        print(f"   {name:16} nam trong rail = {in_rail}")
        if not in_rail:
            fails.append(f"{name} chua chuyen xuong rail")
    # They must still work, not just exist: flipping the language must retranslate.
    from cowork_local.i18n import get_language
    before_lang = get_language()
    other = next(i for i in range(win.language_combo.count())
                 if win.language_combo.itemData(i) != before_lang)
    win.language_combo.setCurrentIndex(other)
    app.processEvents()
    after_lang = get_language()
    print(f"doi ngon ngu tu rail: {before_lang} -> {after_lang}")
    if after_lang == before_lang:
        fails.append("combo ngon ngu o rail khong doi duoc ngon ngu")
    win.language_combo.setCurrentIndex(win.language_combo.findData(before_lang))
    app.processEvents()
    print(f"provider dang chon : {win.provider_combo.currentText()!r}")
    print(f"tai khoan          : {win.account_lbl.text()!r}")

    # Collapsing the rail must not take the project picker away with it: at
    # 54px the combo cannot show a name, so a folder button stands in for it.
    if not win._nav_collapsed:
        win._toggle_nav()
        app.processEvents()
    mini = getattr(win, "nav_project_btn", None)
    if mini is None or mini.isHidden():
        fails.append("thu gon rail xong khong con cach nao doi project")
    else:
        mini.menu().aboutToShow.emit()
        app.processEvents()
        menu_items = [a.text() for a in mini.menu().actions()]
        combo_items = [win.nav_project.itemText(i)
                       for i in range(win.nav_project.count())]
        if menu_items != combo_items:
            fails.append(f"menu project khi thu gon lech voi combo: "
                         f"{menu_items} vs {combo_items}")
        elif len(menu_items) > 1:
            before = win.workspace.selected_project_id()
            # Any row but the one already selected, or nothing would change.
            row = (win.nav_project.currentIndex() + 1) % len(menu_items)
            mini.menu().actions()[row].trigger()
            app.processEvents()
            after = win.workspace.selected_project_id()
            if after == before:
                fails.append("chon project tu menu thu gon khong doi project")
            else:
                print(f"doi project khi thu gon: {before} -> {after}")
    win._toggle_nav()
    app.processEvents()

    print()
    print(f"tong dong dieu huong: {n_total} + nut Cai dat")
    if fails:
        print("*** LOI ***")
        for f in fails:
            print("   " + f)
        return 1
    print("KET QUA: thanh menu phang chay dung")
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
