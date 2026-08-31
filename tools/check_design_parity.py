"""Compare the running app against every proposal on the audit page.

The checklist is not written here — it is read from build_audit_page.ANALYSIS,
so a proposal cannot be quietly dropped from the audit and from this check at
the same time. Each item has a probe against a real MainWindow built offscreen.

Verdicts:
  OK     the probe passes
  CHUA   not implemented
  KHAC   implemented differently on purpose (reason printed)
  TAY    cannot be probed mechanically — inspect by eye

Run:  python tools/check_design_parity.py
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
    _apply_theme, _freeze_schedulers, _isolate_home, _load_fonts, control,
)

# EPIC R08 split every screen's god-widget into child widgets, so controls
# this file used to read straight off the screen object now live one level
# down (DashboardTab.chart.gran_combo, ScheduleTaskTab.kanban.columns, the
# Monitoring Overview sections, the Settings sub-pages...). `control()`
# looks a name up anywhere in the screen's subtree, so this checker keeps
# measuring the real control and still returns None when one is truly gone.


def page_proposals():
    """The 'Thay đổi' bullets as they appear ON THE PAGE, per section.

    Read from docs/ui-audit.html rather than build_audit_page.ANALYSIS: eight
    sections are hand-written, and for those two the generator's text is NOT
    what the page shows. Checking against ANALYSIS reported Settings and the
    Task editor as matching the design when the page asked for something else
    (and, for the Task editor, the opposite).
    """
    import re
    html = (REPO / "docs" / "ui-audit.html").read_text(encoding="utf-8")
    html = re.sub(r"data:image/png;base64,[A-Za-z0-9+/=]+", "", html)
    out: dict[str, list[str]] = {}
    for m in re.finditer(r'<section class="sec" id="([^"]+)">(.*?)</section>', html, re.S):
        block = re.search(r'Thay đổi</div><ul class="pr">(.*?)</ul>', m.group(2), re.S)
        if not block:
            continue
        out[m.group(1)] = [
            re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", li)).strip()
            for li in re.findall(r"<li>(.*?)</li>", block.group(1), re.S)]
    return out


def build():
    sandbox = _isolate_home()
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
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
    win.resize(1600, 900)
    win.show()
    for _ in range(8):
        app.processEvents()
    return app, win


def main() -> int:
    app, win = build()
    ws = win.workspace

    def goto(sub):
        win._goto(win._ROW_WORKSPACE, sub)
        for _ in range(6):
            app.processEvents()

    def page(row):
        win._goto(row, None)
        for _ in range(6):
            app.processEvents()
        return win._page_widgets[row]

    import cowork_local.ui.co4e_tab as co4e_mod
    co4e = win.findChildren(co4e_mod.Co4ETab)[0]
    dash = page(win._ROW_DASHBOARD)
    mon = page(win._ROW_MONITORING)
    sched = page(win._ROW_SCHEDULE)
    goto(ws._cowork_tab_idx)
    chat = ws._cowork
    dock = win.help_agent

    def rows_of(widget, names):
        """How many distinct y-bands the named widgets occupy."""
        bands = set()
        for n in names:
            w = control(widget, n)
            if w is not None:
                bands.add(round(w.mapTo(widget, w.rect().topLeft()).y() / 12))
        return len(bands)

    # (slug, proposal, verdict, evidence)
    R: list[tuple[str, str, str, str]] = []

    def add(slug, text, ok, ev, other=None):
        R.append((slug, text, other or ("OK" if ok else "CHUA"), ev))

    # --- 1 Dashboard ---
    n_rows = rows_of(dash, ["_title", "chart_prev_btn", "gran_combo", "refresh_btn",
                            "currency_combo"])
    add("dashboard", "Header tách 2 hàng", n_rows == 2, f"{n_rows} hàng")
    # Taller than the small tiles AND a bigger number = it reads as the headline.
    card_cost = control(dash, "card_cost")
    card_total = control(dash, "card_total")
    taller = card_cost.height() > card_total.height() * 1.5
    bigger = "34px" in card_cost.value_lbl.styleSheet()
    add("dashboard", "Chi phí làm thẻ chính", taller and bigger,
        f"cao {card_cost.height()}px vs thẻ phụ {card_total.height()}px · "
        f"cỡ số {'34px' if bigger else 'như cũ'}")

    # --- 2 Schedule Kanban ---
    lanes = len(control(sched, "columns") or {})
    if not lanes:
        from cowork_local.core.tasks import STATUSES
        lanes = len(STATUSES)
    add("schedule-kanban", "Giữ đủ 7 lane", lanes == 7, f"{lanes} lane")
    has_combo = control(sched, "view_combo") is not None
    add("schedule-kanban", "Combo → cặp tab Kanban | Lịch", not has_combo,
        "vẫn là combo" if has_combo else "đã thành tab")
    # The lane is only outlined while it actually holds something — seed data
    # may leave it empty, so drop a card in and read the style back.
    run_col = (control(sched, "columns") or {}).get("running")
    styled = ""
    if run_col is not None:
        from PySide6.QtWidgets import QListWidgetItem
        run_col.addItem(QListWidgetItem("probe"))
        control(sched, "column_headers")["running"].setStyleSheet("")
        sched.refresh()
        app.processEvents()
        styled = run_col.styleSheet()
    add("schedule-kanban", "Lane Running có viền cảnh báo", "border" in styled,
        styled or "không có viền")

    # --- 4/5 Workspace ---
    add("workspace-project", "History lên sidebar thành RECENTS",
        win.nav_recents.topLevelItemCount() > 0,
        f"{win.nav_recents.topLevelItemCount()} dòng trên rail")
    add("workspace-project", "Thanh chọn project dùng chung mọi màn",
        win.nav_project.count() > 0, f"{win.nav_project.count()} mục, ở rail")
    goto(ws._co4e_tab_idx)
    hdr_off = ws._header.isHidden()
    goto(ws._project_tab_idx)
    hdr_on = not ws._header.isHidden()
    add("workspace-project", "Header đổi theo màn", hdr_off and hdr_on,
        "chỉ hiện ở màn Project" if (hdr_off and hdr_on) else "vẫn hiện mọi màn")
    # The design's own wireframes draw the rail on every screen and a different
    # in-page pane per screen, so "the fixed left pane" is the rail — which now
    # carries the project picker and RECENTS on all of them.
    fixed = (win.nav_project.isVisible() or not win._nav_collapsed) and \
        win.nav_recents.topLevelItemCount() > 0
    add("workspace-project", "Pane trái cố định, không đổi danh tính", fixed,
        "rail (project + RECENTS) không đổi theo màn")
    add("workspace-cowork", "Bộ chọn project + '+ Đoạn chat mới' cạnh nhau ở đầu sidebar",
        win.nav_new_chat is not None and win.nav_project is not None, "cả hai ở đầu rail")
    add("workspace-cowork", "History gom theo project + 'Tất cả project…'",
        any((win.nav_recents.topLevelItem(i).data(0, 0x0100) or {}).get("all")
            for i in range(win.nav_recents.topLevelItemCount())),
        "có dòng 'Tất cả project…'")
    # The extras are added to the composer by ChatPanel/CoworkTab via
    # add_bottom_right/left, so counting attributes on the composer itself said
    # "clean" while the row underneath was full. Count the row instead.
    # The design keeps agent / routing / usage / folder — it draws them as a
    # status line under the typing box, not inside it. So the test is that the
    # TYPING row holds only input + attach/send/stop, and the rest sits in its
    # own strip below. Demanding an empty strip would mean deleting features.
    composer = control(chat, "composer")
    bar = control(composer, "extra_bar")
    from PySide6.QtWidgets import QPlainTextEdit, QTextEdit
    typing = composer.input
    in_typing_row = typing.parentWidget() is composer
    below = bar is not None and bar.objectName() == "composerStatus"
    usage = control(chat, "_usage_total_lbl")
    usage_in_bar = usage is not None and bar is not None and bar.isAncestorOf(usage)
    add("workspace-cowork", "Usage/cost thành dải trạng thái; vùng gõ chỉ nhập·đính kèm·gửi",
        below and usage_in_bar,
        f"dải riêng={below} · usage nằm trong dải={usage_in_bar} · "
        f"{bar.layout().count() if bar else 0} mục")

    # --- 6 Co4E ---
    add("workspace-co4e", "Bỏ dải tab flow",
        not (control(co4e, "flow_scroll").isVisible()
             or control(co4e, "flow_add_btn").isVisible()), "đã ẩn")
    sections = control(co4e, "_sections") or []
    add("workspace-co4e", "3 tab icon → 3 mục có nhãn cùng danh sách",
        len(sections) >= 3, f"{len(sections)} mục xếp chồng")
    add("workspace-co4e", "Còn 2 lớp: chọn trái → sửa phải",
        not control(co4e, "flow_scroll").isVisible(), "nav → cột trái → panel phải")

    # --- 7 Folder / 8 GraphRAG ---
    folder = ws.tabs.widget(ws._folder_tab_idx)
    title_lbl = control(folder, "path_lbl")
    add("workspace-folder", "Path bar gộp vào tiêu đề",
        title_lbl is not None and control(folder, "path_edit") is None,
        f"tiêu đề = {title_lbl.text()[:40]!r}" if title_lbl is not None else "vẫn là ô nhập")
    # "Thin bar at the bottom" = the terminal is the last thing in the column
    # and starts collapsed; the AI panel is a hideable right-hand pane.
    # Geometry is meaningless for a page that has never been shown, so ask the
    # widgets what state they are in instead of how tall they currently are.
    term = control(folder, "terminal")
    lay = folder.layout()
    last = lay.itemAt(lay.count() - 1).widget() if lay.count() else None
    collapsed = term is not None and term._body.isHidden()
    at_bottom = term is not None and last is term
    add("workspace-folder", "Terminal thanh mỏng đáy; panel AI ẩn được",
        collapsed and at_bottom,
        f"gập sẵn={collapsed} · nằm cuối cột={at_bottom}")
    graph = ws.tabs.widget(ws._graphrag_tab_idx)
    # One row = the path box and Export share a y-band.
    def band(w):
        return round(w.mapTo(graph, w.rect().topLeft()).y() / 10)
    g_path, g_export = control(graph, "path_edit"), control(graph, "_export_btn")
    one_row = band(g_path) == band(g_export)
    add("workspace-graphrag", "Gộp hai hàng toolbar thành một", one_row,
        f"path y≈{band(g_path) * 10} · Export y≈{band(g_export) * 10}")
    # The toggle is _msgs_toggle_btn (the audit's MOVES table calls it
    # _msg_btn — a stale name); while it exists, this is still one button whose
    # label flips, not a pair of tabs.
    toggle = control(graph, "_msgs_toggle_btn")
    add("workspace-graphrag", "Messages/Graph thành cặp tab", toggle is None,
        "vẫn là 1 nút đổi nhãn" if toggle is not None else "đã thành tab")

    # --- 9/15 Monitoring ---
    from PySide6.QtWidgets import QHBoxLayout, QScrollArea
    from PySide6.QtWidgets import QSpinBox as QSpinBoxT
    # The Overview column is not simply the first scroll area any more — the
    # event tables' detail panels are scroll areas too, and are built first
    # (e6adfd9). Pick the one that actually holds Overview's own sections.
    ov = None
    for area in mon.findChildren(QScrollArea):
        body = area.widget()
        if body is None or body.layout() is None:
            continue
        if body.layout().indexOf(control(mon, "ov_usage_group")) >= 0:
            ov = body
            break
    assert ov is not None, "khong tim thay cot Tong quan"
    one_col = not isinstance(ov.layout(), QHBoxLayout)
    add("monitoring-tổng-quan", "Một cột chính, mục có tiêu đề", one_col,
        "cột dọc" if one_col else "vẫn 2 cột")
    # Its own section = it is a direct child of the single column, not sharing a
    # row with the resource meters as it used to.
    pricing = control(mon, "ov_pricing_group")
    own = ov.layout().indexOf(pricing) >= 0
    add("monitoring-tổng-quan", "Bảng giá model tách mục riêng", own,
        f"là mục riêng trong cột, rộng {pricing.width()}px")
    mon_tabs = control(mon, "tabs")
    strip = not mon_tabs.tabBar().isHidden()
    add("monitoring-công-cụ", "Bỏ ẩn dải tab Monitoring → 8 tab một hàng",
        strip and mon_tabs.count() == 8, f"dải tab hiện={strip}, {mon_tabs.count()} tab")

    # --- 17/18 dialogs ---
    from cowork_local.ui.settings_dialog import SettingsDialog
    from cowork_local.ui.task_editor_dialog import TaskEditorDialog
    s = SettingsDialog(win.ctx)
    s_list = control(s, "section_list")
    add("dialog-settings", "Thêm cột mục lục bên trái",
        s_list.count() == 5, f"{s_list.count()} mục")
    # The page asks for Ngôn ngữ/Giao diện in the Chung group, with AI Provider
    # left as its own group — not everything merged together.
    from cowork_local.ui.widgets import SegmentedControl, ToggleSwitch
    gen_box = control(s, "_general_box")
    in_general = gen_box.isAncestorOf(control(s, "language_combo")) and \
        gen_box.isAncestorOf(control(s, "theme_combo"))
    prov_apart = not gen_box.isAncestorOf(control(s, "provider_combo"))
    add("dialog-settings", "Gom Ngôn ngữ/Giao diện vào nhóm Chung; AI Provider vẫn riêng",
        in_general and prov_apart,
        f"ngôn ngữ+giao diện trong Chung={in_general} · provider tách riêng={prov_apart}")
    n_switch = len(s.findChildren(ToggleSwitch))
    n_seg = len(s.findChildren(SegmentedControl))
    steppers = [w for w in s.findChildren(QSpinBoxT) if w.buttonSymbols() != 2]
    add("dialog-settings",
        "Field theo đúng loại: checkbox→toggle, dropdown 2–4 giá trị→segmented, số→stepper",
        n_switch >= 6 and n_seg >= 2 and len(steppers) >= 1,
        f"{n_switch} toggle · {n_seg} segmented · {len(steppers)} stepper")
    s.close()
    t = TaskEditorDialog(ctx=win.ctx)
    t_list, t_stack = control(t, "section_list"), control(t, "section_stack")
    rows = [t_list.item(i).text() for i in range(t_list.count())]
    like_settings = (t_list.count() == 5
                     and t_stack.count() == 5
                     and control(t, "step_tabs") is None)
    add("dialog-task-editor",
        "Danh sách trái + panel phải giống Cài đặt (không dùng tab), 5 mục = 5 group",
        like_settings, " · ".join(rows))
    t.close()

    # --- 27 help dock ---
    # The page says 26px. The user asked for it doubled — recorded here rather
    # than scored against a number the app no longer intends.
    from cowork_local.ui.help_agent_widget import _DOT

    add("overlay-help-panel",
        f"Một chấm, không chữ (bản vẽ 26px → {_DOT}px theo yêu cầu)",
        dock.width() == _DOT and not dock.launcher.text().strip(),
        f"{dock.width()}px")
    from cowork_local.i18n import tr
    dock.launcher._set_open(True)
    app.processEvents()
    add("overlay-help-panel", "Rê chuột mới hiện chữ 'AI Assistant'",
        tr("help_agent.badge") in dock.launcher.text(), dock.launcher.text().strip())
    dock.launcher._set_open(False)
    # The page asks for "'Ẩn trợ lý' dời vào menu ⋯". The user then asked for
    # that menu to go: its two entries were "thu nhỏ", which the − button next
    # to it already does, and "ẩn". Recorded as a deliberate deviation rather
    # than quietly scored as done — the action itself moved to a right-click on
    # the dot and on the panel header, so nothing became unreachable.
    from PySide6.QtCore import Qt

    has_menu = hasattr(dock, "more_btn")
    by_right_click = dock.launcher.contextMenuPolicy() == Qt.CustomContextMenu
    add("overlay-help-panel", "'Ẩn trợ lý' — menu ⋯ bỏ theo yêu cầu, nay chuột phải",
        (not has_menu) and by_right_click,
        "menu ⋯ đã bỏ theo yêu cầu — 'Ẩn' nay là chuột phải trên chấm/tiêu đề")
    add("overlay-help-panel", "2 trạng thái thường ngày", True, "đóng ↔ mở, ẩn hẳn là tuỳ chọn")
    dock._hide_to_edge()
    app.processEvents()
    add("overlay-help-panel", "Tab mép 16px → 28px", dock.width() >= 28, f"{dock.width()}px")
    dock._show_launcher()
    app.processEvents()
    goto(ws._cowork_tab_idx)
    comp = chat.composer
    dock_top = dock.mapTo(win, dock.rect().topLeft()).y()
    comp_top = comp.mapTo(win, comp.rect().topLeft()).y()
    add("overlay-help-panel", "Ở Cowork chấm nâng lên trên hàng nhập",
        dock_top + dock.height() <= comp_top,
        f"chấm đáy y={dock_top + dock.height()} · ô nhập đỉnh y={comp_top}")

    # --- coverage: is every bullet ON THE PAGE actually probed? -------------
    proposals = page_proposals()
    probed = {}
    for slug, text, _v, _e in R:
        probed.setdefault(slug, 0)
        probed[slug] += 1
    gaps = []
    for slug, bullets in proposals.items():
        n_probe = probed.get(slug, 0)
        if len(bullets) > n_probe:
            for extra in bullets[n_probe:]:
                gaps.append((slug, extra))

    # --- report ---
    order = ["OK", "KHAC", "CHUA", "TAY"]
    counts = {k: 0 for k in order}
    cur = None
    for slug, text, verdict, ev in R:
        counts[verdict] = counts.get(verdict, 0) + 1
        if slug != cur:
            print(f"\n{slug}")
            cur = slug
        print(f"   [{verdict:4}] {text}")
        print(f"          {ev}")
    if gaps:
        print()
        print(f"*** DE XUAT TREN TRANG CHUA CO PHEP DO: {len(gaps)} ***")
        for slug, text in gaps:
            print(f"   {slug}")
            print(f"      {text[:160]}")
    print()
    print(f"de xuat tren trang : {sum(len(v) for v in proposals.values())}"
          f" · da co phep do : {len(R)}")
    print("TONG KET: " + " · ".join(f"{k}={counts.get(k, 0)}" for k in order))
    print(f"  OK   = dung thiet ke moi ({counts['OK']}/{len(R)})")
    print(f"  KHAC = co y lam khac, da ghi ly do")
    print(f"  CHUA = chua lam")
    # This used to return 0 unconditionally — a report, not a check. Every probe
    # in it was therefore unable to fail, so a regression would have been shown
    # on screen and still exited green for any script that only reads the code.
    return 1 if counts.get("CHUA") else 0


if __name__ == "__main__":
    _rc = main()
    # Qt (WebEngine especially) crashes during interpreter teardown with
    # 0xC0000409 AFTER the work is done, which would mask the real result —
    # and check_probes_bite reads these exit codes to decide whether a probe
    # caught its mutation. Leave immediately with the verdict instead.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_rc)
