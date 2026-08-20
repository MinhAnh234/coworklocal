"""List every show/hide/enable/disable rule, baseline vs now.

The redesign was allowed to change the flow. It was NOT allowed to change what
is hidden or greyed out — those rules encode real preconditions, and dropping
one turns a guarded action into a broken one.

Reports rules that disappeared, appeared, or changed target between the
pre-redesign commit and HEAD.
"""
from __future__ import annotations

import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "291a611"
CALL = re.compile(
    r"(?P<target>[\w\.\[\]\(\)_]*?)\.?(?P<verb>setVisible|setHidden|setEnabled|"
    r"setDisabled|setTabVisible|setTabEnabled|hide|show)\s*\(")


def files():
    out = subprocess.run(["git", "diff", "--name-only", f"{BASE}..HEAD", "--", "*.py"],
                         capture_output=True, text=True, encoding="utf-8").stdout
    return [f for f in out.split() if f.endswith(".py") and not f.startswith("tools/")]


def _arg(s, start):
    """Text inside the call's parentheses — the CONDITION, which matters as
    much as the call being there at all."""
    depth, out = 0, []
    for ch in s[start:]:
        if ch == "(":
            depth += 1
            if depth == 1:
                continue
        elif ch == ")":
            depth -= 1
            if depth == 0:
                break
        if depth >= 1:
            out.append(ch)
    return "".join(out).strip()


def rules(rev, path):
    """{(target, verb): set(conditions)} for one revision of one file."""
    src = subprocess.run(["git", "show", f"{rev}:{path}"],
                         capture_output=True, text=True, encoding="utf-8",
                         errors="replace").stdout or ""
    found = {}
    for n, line in enumerate(src.splitlines(), 1):
        s = line.strip()
        if s.startswith("#") or s.startswith('"'):
            continue
        for m in CALL.finditer(s):
            target, verb = m.group("target"), m.group("verb")
            if not target or (verb in ("hide", "show") and not target):
                continue
            cond = _arg(s, m.end() - 1) or "-"
            found.setdefault((target, verb), {}).setdefault(cond, n)
    return found


def main() -> int:
    gone, added, changed = [], [], []
    for path in files():
        old, new = rules(BASE, path), rules("HEAD", path)
        for key in sorted(set(old) - set(new)):
            gone.append((path, key, old[key]))
        for key in sorted(set(new) - set(old)):
            added.append((path, key, new[key]))
        for key in sorted(set(new) & set(old)):
            if set(old[key]) != set(new[key]):
                changed.append((path, key, old[key], new[key]))

    print(f"=== A. LUAT BI BO ({len(gone)}) ===")
    for path, (target, verb), conds in gone:
        for cond, line in conds.items():
            print(f"  {path}:{line:<5} {target}.{verb}({cond})")

    print()
    print(f"=== B. DIEU KIEN DOI ({len(changed)}) ===")
    for path, (target, verb), oldc, newc in changed:
        print(f"  {path}  {target}.{verb}()")
        for c in sorted(set(oldc) - set(newc)):
            print(f"      cu  : ({c})")
        for c in sorted(set(newc) - set(oldc)):
            print(f"      moi : ({c})   dong {newc[c]}")

    print()
    print(f"=== C. LUAT MOI THEM ({len(added)}) ===")
    for path, (target, verb), conds in added:
        for cond, line in conds.items():
            print(f"  {path}:{line:<5} {target}.{verb}({cond})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
