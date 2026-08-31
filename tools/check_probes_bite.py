"""Round 5: do the checks actually bite?

Rounds 1–4 all report green. That is only worth something if the checks would
have turned red had the work not been done. So this round breaks the app on
purpose, one feature at a time, and fails if the corresponding check still
passes — a check that cannot fail is not evidence.

Each mutation is applied by monkey-patching the module BEFORE the checker
builds its own window, then undone.

Run:  python tools/check_probes_bite.py
"""
from __future__ import annotations

import io
import os
import runpy
import subprocess
import sys


sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# (name, file, find, replace, checker that must FAIL because of it)
MUTATIONS = [
    ("phong to cham tro ly gap doi khai bao",
     "ui/help_agent_widget.py", "_DOT = 52", "_DOT = 104",
     "check_layout_geometry.py"),
    ("tra lane Running ve khong vien",
     # R08-T11 doi cho: ScheduleTaskTab tach ra, phan ve Kanban (ke ca vien
     # canh bao cua lane Running) nam o presentation/scheduling/.
     "presentation/scheduling/kanban_board_widget.py",
     'if status == "running" and counts[status]:',
     'if False:',
     "check_design_parity.py"),
    ("bo cot muc luc cua Cai dat",
     "ui/settings_dialog.py",
     "self.section_list, self.section_stack = section_panels(pages)",
     "self.section_list, self.section_stack = section_panels(pages[:1])",
     "check_dialogs.py"),
    ("noi lai dai tab flow Co4E",
     # R08-T09 doi cho: Co4ETab tach thanh 7 mixin duoi presentation/co4e/.
     "presentation/co4e/co4e_layout.py",
     "self.flow_scroll.setVisible(False)",
     "self.flow_scroll.setVisible(True)",
     "check_co4e.py"),
    ("bo dong 'Tat ca project...' khoi GAN DAY",
     # R08-T10 doi cho: MainWindow bi boc khoi app.py sang presentation/shell/,
     # RECENTS nam o rail_project.py, cay dieu huong o nav_rail.py.
     "presentation/shell/rail_project.py",
     'more.setData(0, Qt.UserRole, {"all": True})',
     'more.setData(0, Qt.UserRole, {})',
     "check_design_parity.py"),
    ("tra thanh menu ve accordion (bo nhom day)",
     "presentation/shell/nav_rail.py",
     'rows.append((self.nav_bottom, self._ROW_DASHBOARD, None,',
     'rows.append((self.nav, self._ROW_DASHBOARD, None,',
     "check_layout_geometry.py"),
]


def run_checker(script: str) -> int:
    """Run a checker in a fresh process; return its exit code."""
    proc = subprocess.run(
        [sys.executable, str(REPO / "tools" / script)],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8",
        errors="replace", env={**os.environ, "QT_QPA_PLATFORM": "offscreen",
                               "PYTHONIOENCODING": "utf-8"})
    return proc.returncode


def tree_state() -> str:
    return subprocess.run(["git", "status", "--short"], cwd=REPO,
                          capture_output=True, text=True).stdout.strip()


def main() -> int:
    fails: list[str] = []
    # Compare the tree BEFORE and AFTER, not against a clean tree: work in
    # progress is legitimately uncommitted, and demanding a clean tree made this
    # round fail for a reason that has nothing to do with the mutations.
    before = tree_state()
    print(f"{'hong gi':44} {'phep do':26} ket qua")
    print("-" * 88)
    for name, rel, find, repl, checker in MUTATIONS:
        path = REPO / rel
        # newline="" both ways: the default translates on read AND write, so a
        # LF file came back as CRLF and every mutated file was left "modified"
        # even after being restored.
        with io.open(path, "r", encoding="utf-8", newline="") as fh:
            original = fh.read()
        if find not in original:
            fails.append(f"{name}: khong tim thay doan can sua trong {rel}")
            print(f"{name:44} {checker:26} *** KHONG AP DUNG DUOC ***")
            continue

        def write(text: str) -> None:
            with io.open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(text)

        write(original.replace(find, repl, 1))
        try:
            code = run_checker(checker)
        finally:
            write(original)                                # always restore
        bit = code != 0
        print(f"{name:44} {checker:26} {'BAT DUOC' if bit else '*** KHONG BAT ***'}")
        if not bit:
            fails.append(f"{name}: {checker} van bao xanh du da lam hong")

    # Everything must be back exactly as it was before this run.
    after = tree_state()
    same = after == before
    print()
    print("cay lam viec sau khi thu giong het truoc:", "co" if same else "*** KHAC ***")
    if not same:
        print("   truoc:", before.replace("\n", " | ") or "(sach)")
        print("   sau  :", after.replace("\n", " | ") or "(sach)")
        fails.append("file chua duoc khoi phuc sau khi thu")

    print()
    if fails:
        print("*** VONG 5 THAT BAI ***")
        for f in fails:
            print("   " + f)
        return 1
    print(f"KET QUA VONG 5: ca {len(MUTATIONS)} phep do deu bat duoc loi khi co tinh lam hong")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
