"""Extract every interactive control from the UI source, mechanically.

Reading the files by hand and listing what I notice is exactly how functionality
gets dropped from a redesign. This walks the AST instead, so the inventory is
exhaustive by construction: if a widget is constructed in the file, it appears.

For each control it reports the variable it is bound to, its widget type, the
label expression (usually a ``tr("...")`` key), the signal handlers wired to it,
and the source line — enough to check "did the new design keep this?".

Run:  python tools/extract_controls.py [ui/file.py ...]
"""
from __future__ import annotations

import ast
import io
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
UI = REPO / "ui"

# Widget types that represent something the user can click, type in or toggle.
WIDGETS = {
    "QPushButton": "nút", "QToolButton": "nút icon", "QComboBox": "droplist",
    "QCheckBox": "ô tick", "QRadioButton": "radio", "QLineEdit": "ô nhập",
    "QPlainTextEdit": "ô nhập nhiều dòng", "QTextEdit": "ô nhập nhiều dòng",
    "QSpinBox": "ô số", "QDoubleSpinBox": "ô số", "QDateTimeEdit": "ô ngày giờ",
    "QDateEdit": "ô ngày", "QTimeEdit": "ô giờ", "QSlider": "thanh trượt",
    "QListWidget": "danh sách", "QTreeWidget": "cây", "QTableWidget": "bảng",
    "QTabWidget": "dải tab", "QTabBar": "dải tab", "QDialogButtonBox": "nút hộp thoại",
}
# Signals worth recording — these are the "it does something" wires.
SIGNALS = {
    "clicked", "toggled", "currentIndexChanged", "currentTextChanged",
    "textChanged", "returnPressed", "valueChanged", "itemClicked",
    "itemDoubleClicked", "currentItemChanged", "currentChanged",
    "customContextMenuRequested", "tabCloseRequested", "linkActivated",
    "stateChanged", "activated", "triggered", "editingFinished",
}


def _txt(node) -> str:
    """Best-effort source text for a label expression."""
    try:
        return ast.unparse(node)
    except Exception:                                          # noqa: BLE001
        return "?"


class Visitor(ast.NodeVisitor):
    def __init__(self, path: Path):
        self.path = path
        self.controls: dict[str, dict] = {}     # var name -> record
        self.menu_actions: list[dict] = []

    # ---- self.btn = QPushButton(...) / btn = QComboBox() -------------------
    def visit_Assign(self, node: ast.Assign) -> None:
        if isinstance(node.value, ast.Call):
            fn = node.value.func
            name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", "")
            if name in WIDGETS:
                for tgt in node.targets:
                    var = _txt(tgt)
                    args = [_txt(a) for a in node.value.args]
                    self.controls.setdefault(var, {
                        "var": var, "type": name, "kind": WIDGETS[name],
                        "label": args[0] if args else "",
                        "line": node.lineno, "signals": [], "object_name": "",
                    })
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        fn = node.func
        # ---- x.clicked.connect(handler) ----------------------------------
        if isinstance(fn, ast.Attribute) and fn.attr == "connect":
            sig = fn.value
            if isinstance(sig, ast.Attribute) and sig.attr in SIGNALS:
                var = _txt(sig.value)
                rec = self.controls.get(var)
                if rec is not None and node.args:
                    rec["signals"].append(f"{sig.attr} → {_txt(node.args[0])}")
        # ---- x.setText(tr("...")) / setObjectName / setToolTip -----------
        if isinstance(fn, ast.Attribute) and node.args:
            var = _txt(fn.value)
            rec = self.controls.get(var)
            if rec is not None:
                if fn.attr in ("setText", "setPlaceholderText") and not rec["label"]:
                    rec["label"] = _txt(node.args[0])
                elif fn.attr == "setObjectName":
                    rec["object_name"] = _txt(node.args[0]).strip("'\"")
                elif fn.attr == "setToolTip" and not rec["label"]:
                    rec["label"] = _txt(node.args[0])
        # ---- menu.addAction("Xoá") — context menus are real features -----
        if isinstance(fn, ast.Attribute) and fn.attr == "addAction" and node.args:
            self.menu_actions.append({
                "menu": _txt(fn.value), "label": _txt(node.args[0]),
                "line": node.lineno,
            })
        self.generic_visit(node)


def scan(path: Path) -> dict:
    tree = ast.parse(io.open(path, encoding="utf-8").read(), filename=str(path))
    v = Visitor(path)
    v.visit(tree)
    # Drop pure containers with no wiring and no label — they are layout, not
    # controls the user acts on directly.
    controls = [c for c in v.controls.values()
                if c["signals"] or c["label"] or c["object_name"]]
    controls.sort(key=lambda c: c["line"])
    return {"file": str(path.relative_to(REPO)),
            "controls": controls, "menu_actions": v.menu_actions}


def main(argv: list[str]) -> int:
    targets = [Path(a) for a in argv] or sorted(UI.glob("*.py"))
    out = []
    for t in targets:
        if t.name == "__init__.py":
            continue
        p = t if t.is_absolute() else (REPO / t if (REPO / t).exists() else t)
        try:
            out.append(scan(p))
        except SyntaxError as exc:                             # noqa: PERF203
            print(f"  SKIP {p.name}: {exc}", file=sys.stderr)
    dest = REPO / "docs" / "screens" / "controls.json"
    dest.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    n_ctl = sum(len(f["controls"]) for f in out)
    n_act = sum(len(f["menu_actions"]) for f in out)
    print(f"{len(out)} file · {n_ctl} control · {n_act} mục menu chuột phải → {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
