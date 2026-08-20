"""With no project chosen, the gated screens must stay shut on every route.

The redesign shows Cowork and GraphRAG at all times instead of making them
appear and disappear. That is a presentation change only — the gate is the same
`isTabVisible` state as before — so this asserts the gate still actually holds,
and holds for programmatic jumps too, not just for the greyed rail rows.

Runs against an EMPTY home, not a copy of the real one: with any project on
disk the gate is open and the test proves nothing.
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sandbox = Path(tempfile.mkdtemp(prefix="cowork-gate-"))
(sandbox / ".cowork_local").mkdir(parents=True, exist_ok=True)
for _var in ("USERPROFILE", "HOME"):
    os.environ[_var] = str(sandbox)
os.environ.pop("HOMEDRIVE", None)
os.environ.pop("HOMEPATH", None)

from capture_screens import _apply_theme, _freeze_schedulers, _load_fonts  # noqa: E402


def main() -> int:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    _load_fonts()
    _freeze_schedulers()
    _apply_theme(app)

    from cowork_local.config import CONFIG_DIR
    assert str(sandbox) in str(CONFIG_DIR), f"isolation failed: {CONFIG_DIR}"

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
    n_projects = len(win.workspace.project_choices())
    print(f"project tren dia: {n_projects}")
    if n_projects:
        print("FAIL  home khong rong — phep thu vo nghia")
        sys.stdout.flush()
        os._exit(1)

    tree = win.nav
    rows = [(i, tree.topLevelItem(i)) for i in range(tree.topLevelItemCount())]
    locked = [(i, it) for i, it in rows if it.isDisabled()]
    print("dong bi khoa :", [it.text(0) for _i, it in locked])
    print("dong mo binh thuong:", [it.text(0) for _i, it in rows if not it.isDisabled()])
    if not locked:
        fails.append("khong project nao ma khong dong nao bi khoa")

    for _i, it in locked:
        if not it.toolTip(0):
            fails.append(f"dong khoa '{it.text(0)}' khong noi ly do")

    for i, it in locked:
        label = it.text(0)
        data = it.data(0, Qt.UserRole) or {}
        before = win.workspace.current_subtab()

        tree.setCurrentItem(it)
        app.processEvents()
        if win.workspace.current_subtab() != before:
            fails.append(f"bam duoc vao '{label}' du dang khoa")

        # the route a greyed row does not guard: a jump from code
        win._goto(data.get("page", 0), data.get("sub"))
        app.processEvents()
        landed = win.workspace.current_subtab()
        if landed == data.get("sub"):
            fails.append(f"_goto mo duoc '{label}' trong khi cong dang dong")
        print(f"  '{label}': bam -> {before}, _goto -> {landed} "
              f"(tab hien = {win.workspace.tabs.isTabVisible(data.get('sub'))})")

    # controls that would act on a project must be off too
    for name, widget in (("+ chat moi", win.nav_new_chat),
                         ("chon project", win.nav_project_btn)):
        if widget.isEnabled():
            fails.append(f"'{name}' van bam duoc khi chua co project")
    print(f"+ chat moi bat={win.nav_new_chat.isEnabled()} "
          f"tooltip={win.nav_new_chat.toolTip()!r}")

    print()
    for f in fails:
        print("FAIL  " + f)
    print("PASS  cong project van giu, ca khi bam lan khi goi tu code" if not fails
          else f"{len(fails)} problem(s)")
    sys.stdout.flush()
    os._exit(1 if fails else 0)


if __name__ == "__main__":
    raise SystemExit(main())
