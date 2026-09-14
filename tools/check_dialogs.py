"""Check the left-list + right-panel navigation in Settings and Task editor.

Both dialogs are navigated the same way, as the audit page asks: a list of the
real group boxes on the left, one panel shown at a time on the right. So the
test is that picking a row swaps the panel, that the rows match the groups, and
— since this is a rearrangement — that no input control went missing.

Run:  python tools/check_dialogs.py
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

# Every field each dialog must still offer after the move.
SETTINGS_FIELDS = [
    "language_combo", "theme_combo", "tray_chk", "notify_chk",
    "provider_combo", "prov_base", "prov_key", "prov_model",
    "sandbox_confirm",
    "sandbox_block_network", "sec_enabled", "ai_check",
]
TASK_FIELDS = [
    "title_edit", "desc_edit", "gen_desc_btn", "priority_combo", "status_combo",
    "workspace_combo", "provider_combo", "model_combo", "skill_combo",
    "sched_enabled", "run_at_edit", "files_list", "files_add_btn", "links_list",
    "links_add_btn", "next_combo", "run_next_combo", "pass_output_chk",
    "depends_list", "retry_spin", "timeout_spin", "approval_chk",
]


def check(name, dlg, app, expect_rows, fields):
    fails = []
    print(f"--- {name} ---")
    idx, stack = dlg.section_list, dlg.section_stack
    rows = [idx.item(i).text() for i in range(idx.count())]
    print(f"muc  : {rows}")
    if len(rows) != expect_rows:
        fails.append(f"{name}: cho {expect_rows} muc, thay {len(rows)}")
    if idx.count() != stack.count():
        fails.append(f"{name}: {idx.count()} muc nhung {stack.count()} panel")

    # Picking a row must swap the panel — and each panel must hold something.
    swapped, empty = 0, []
    for i in range(idx.count()):
        idx.setCurrentRow(i)
        for _ in range(3):
            app.processEvents()
        if stack.currentIndex() == i:
            swapped += 1
        page = stack.widget(i).widget()
        if not page.findChildren(type(page)):
            empty.append(rows[i])
    print(f"chon muc -> doi panel : {swapped}/{idx.count()}")
    if swapped != idx.count():
        fails.append(f"{name}: chon muc khong doi panel")
    if empty:
        fails.append(f"{name}: panel rong {empty}")

    missing = [f for f in fields if getattr(dlg, f, None) is None]
    print(f"field con nguyen      : {len(fields) - len(missing)}/{len(fields)}")
    if missing:
        fails.append(f"{name}: mat field {missing}")
    return fails


def main() -> int:
    sandbox = _isolate_home()
    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    _load_fonts()

    _apply_theme(app)   # measure the styled widget, not a bare one
    from cowork_local.config import AppConfig, CONFIG_DIR
    assert str(sandbox) in str(CONFIG_DIR), f"isolation failed: {CONFIG_DIR}"

    from cowork_local.i18n import set_language, tr
    from cowork_local.state import AppContext
    from cowork_local.ui.settings_dialog import SettingsDialog
    from cowork_local.ui.task_editor_dialog import TaskEditorDialog

    set_language("vi")
    ctx = AppContext(AppConfig.load())
    fails = []

    s = SettingsDialog(ctx)
    s.resize(900, 640)
    s.show()
    app.processEvents()
    fails += check("Cai dat", s, app, 5, SETTINGS_FIELDS)

    t = TaskEditorDialog(ctx=ctx)
    t.resize(900, 640)
    t.show()
    app.processEvents()
    fails += check("Task editor", t, app, 5, TASK_FIELDS)

    # Both dialogs must be navigated the SAME way — that is the stated point.
    same = (type(s.section_list) is type(t.section_list)
            and type(s.section_stack) is type(t.section_stack))
    print()
    print(f"hai hop thoai cung kieu dieu huong: {same}")
    if not same:
        fails.append("hai hop thoai dieu huong khac kieu")

    for lang in ("vi", "en", "ja"):
        set_language(lang)
        print(f"  {lang}: general={tr('settings.group.general')!r} "
              f"basic={tr('schedtask.g_basic')!r}")
    set_language("vi")

    print()
    if fails:
        print("*** LOI ***")
        for x in fails:
            print("   " + x)
        return 1
    print("KET QUA: hai hop thoai dung danh sach trai + panel phai, khong mat field")
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
