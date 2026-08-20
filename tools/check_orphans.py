"""Catch controls orphaned by a neighbouring container being removed.

The audit page defaults every control to "giữ nguyên tại chỗ" and lists only the
ones that move. That default is unsafe when the thing a control sits *with* is
removed — then "unchanged" is impossible and the control has quietly lost its
home. This is how the Co4E "＋ new workflow" button vanished from the proposal:
it lives in the same layout row as the flow tab strip, and the strip was proposed
for removal.

Note the relationship is SIBLING, not parent/child: `flow_row` holds both the
scroller (wrapping `flow_bar`) and `flow_add_btn`. An earlier version of this
check looked only for `container.addWidget(child)` and therefore found nothing —
it passed while the bug was live. Verify any change here with --selftest.

Run:  python tools/check_orphans.py [--selftest]
"""
from __future__ import annotations

import ast
import io
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

# A MOVES note containing one of these means the thing is going away, so anything
# that only existed alongside it needs a new home.
REMOVAL_WORDS = ("bỏ;", "bỏ ", "gộp", "thay thế")


def layout_map(path: Path) -> tuple[dict[str, list[str]], dict[str, str]]:
    """(layout var -> widget vars added to it, wrapper var -> widget it wraps)."""
    members: dict[str, list[str]] = {}
    alias: dict[str, str] = {}
    tree = ast.parse(io.open(path, encoding="utf-8").read(), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        try:
            owner = ast.unparse(node.func.value)
            args = [ast.unparse(a) for a in node.args]
        except Exception:                                       # noqa: BLE001
            continue
        if not args:
            continue
        if node.func.attr in ("addWidget", "addLayout"):
            members.setdefault(owner, []).append(args[0])
        elif node.func.attr == "setWidget":
            # QScrollArea(inner): the scroller stands in for what it holds.
            alias[owner] = args[0]
    return members, alias


def main(argv: list[str]) -> int:
    import build_audit_page as B

    selftest = "--selftest" in argv
    moves = dict(B.MOVES)
    if selftest:
        # Re-create the original bug and prove the check reports it.
        moves.pop("self.flow_add_btn", None)

    removed = {k for k, v in moves.items()
               if any(w in v.lower() for w in REMOVAL_WORDS)}
    ctl = json.loads((REPO / "docs" / "screens" / "controls.json")
                     .read_text(encoding="utf-8"))

    problems: list[tuple[str, str, str, str]] = []
    n_sib = 0
    for rec in ctl:
        path = REPO / rec["file"]
        if not path.exists():
            continue
        members, alias = layout_map(path)
        labels = {c["var"]: (c.get("label_vi") or c.get("label") or "?")
                  for c in rec["controls"]}
        for layout, kids in members.items():
            # Resolve wrappers so a scroller counts as the widget it holds.
            resolved = {k: alias.get(k, k) for k in kids}
            gone = [k for k, r in resolved.items() if r in removed]
            if not gone:
                continue
            for kid in kids:
                if resolved[kid] in removed or kid not in labels:
                    continue
                n_sib += 1
                if kid not in moves:
                    problems.append((rec["file"], kid, labels[kid],
                                     f"cung hang voi {resolved[gone[0]]}"))

    print(f"control nam canh mot thanh phan bi bo : {n_sib}")
    print(f"thanh phan bi bo trong MOVES          : {len(removed)}"
          f"  {sorted(removed) if removed else ''}")
    print()
    if problems:
        print("*** CONTROL MO COI ***")
        for f, var, label, why in problems:
            print(f"   {f}: {var}  ({label})  — {why}")
        print()
        print(f"KET QUA: {len(problems)} control mat cho, can khai bao trong MOVES")
        return 0 if selftest else 1
    if selftest:
        print("KET QUA SELFTEST: *** THAT BAI — phep kiem KHONG bat duoc loi da biet ***")
        return 1
    print("KET QUA: khong co control nao bi mo coi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
