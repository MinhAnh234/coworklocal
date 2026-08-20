"""Workspace ▸ Project against its wireframe (section 4).

The drawing: a "Quản lý project" title with + Project mới on its right, a caps
PROJECT heading over the list, every row carrying "N đoạn chat · M task", and
the form reading Tên / Mô tả / Instructions / Thư mục làm việc.
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
    _apply_theme, _freeze_schedulers, _isolate_home, _load_fonts)


def main() -> int:
    sandbox = _isolate_home()
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QApplication, QLabel

    app = QApplication([])
    _load_fonts()
    _freeze_schedulers()
    _apply_theme(app)

    from cowork_local.config import CONFIG_DIR
    assert str(sandbox) in str(CONFIG_DIR), f"isolation failed: {CONFIG_DIR}"

    from seed_demo_data import seed
    seed()

    from cowork_local.app import MainWindow
    from cowork_local.config import AppConfig
    from cowork_local.i18n import set_language, tr
    from cowork_local.state import AppContext

    set_language("vi")
    win = MainWindow(AppContext(AppConfig.load()), user_name="local")
    win.resize(1400, 900)
    win.show()
    app.processEvents()
    win._goto(win._ROW_WORKSPACE, win.workspace._project_tab_idx)
    app.processEvents()

    w = win.workspace
    fails = []

    # 1. title, and the create button on its row, to its right
    print(f"tieu de: {w._header.text()!r}")
    if w._header.text() != tr("workspace.header"):
        fails.append("tieu de khong phai workspace.header")
    h_pos = w._header.mapTo(w, QPoint(0, 0))
    h_mid = h_pos.y() + w._header.height() // 2
    b_pos = w._new_btn.mapTo(w, QPoint(0, 0))
    b_mid = b_pos.y() + w._new_btn.height() // 2
    aligned = abs(b_mid - h_mid) <= 8
    after = b_pos.x() >= h_pos.x() + w._header.width()
    print(f"nut '+ Project mới': tam y={b_mid} (tieu de {h_mid}) thang hang={aligned} "
          f"| x={b_pos.x()} sau tieu de={after}")
    if not (aligned and after):
        fails.append("nut tao project khong nam cung hang, ben phai tieu de")

    # 2. caps heading over the list
    hdr = w._projects_hdr.text()
    print(f"tieu de pane trai: {hdr!r}")
    if not hdr or hdr != hdr.upper():
        fails.append(f"tieu de pane trai chua viet hoa: {hdr!r}")

    # 3. every row says how much is in the project
    lst = w.project_list
    if not lst.count():
        fails.append("khong co project nao de kiem")
    shown = 0
    for i in range(lst.count()):
        row = lst.itemWidget(lst.item(i))
        labels = [l.text() for l in row.findChildren(QLabel)] if row else []
        if len(labels) < 2:
            fails.append(f"hang {i} khong co dong dem chat/task")
            continue
        shown += 1
        if i < 2:
            print(f"  hang {i}: {labels[0]!r} / {labels[1]!r}")
        # the sub-line must be the counts string, not the name repeated
        if labels[1] == labels[0] or not any(ch.isdigit() for ch in labels[1]):
            fails.append(f"hang {i}: dong phu khong phai so dem: {labels[1]!r}")
    print(f"so hang co dong dem: {shown}/{lst.count()}")

    # 4. the form reads as the drawing labels it
    want = [tr("workspace.name"), tr("workspace.description"),
            tr("workspace.instructions"), tr("workspace.folder_label")]
    seen = [l.text() for l in w.findChildren(QLabel) if l.isVisible() and l.text()]
    for label in want:
        if label not in seen:
            fails.append(f"thieu nhan {label!r}")
    print(f"nhan form: {want}")

    # 5. the drawing heads a populated screen with the title alone; the
    #    explanation belongs to an empty one.
    print(f"hint hien voi {lst.count()} project: {w._hint.isVisible()}")
    if lst.count() and w._hint.isVisible():
        fails.append("doan giai thich van hien du da co project")

    # 6. the path is a field in the drawing, not caption text
    from PySide6.QtWidgets import QLineEdit
    is_field = isinstance(w.folder_lbl, QLineEdit) and w.folder_lbl.isReadOnly()
    print(f"o thu muc: {type(w.folder_lbl).__name__} (o nhap chi doc={is_field})")
    if not is_field:
        fails.append("duong dan thu muc khong phai o nhap chi doc")

    # 7. Lưu project floats at the foot of the panel, not right under the form
    save_y = w._save_btn.mapTo(w, QPoint(0, 0)).y()
    folder_y = w.folder_lbl.mapTo(w, QPoint(0, 0)).y()
    print(f"nut Luu y={save_y}, o thu muc y={folder_y}, cach {save_y - folder_y}px")
    if save_y - folder_y < 80:
        fails.append("nut Luu khong bi day xuong day panel")

    # 8. the rail's picker must name the projects. It reads project_choices(),
    #    which used to read item.text() — and when rows became widgets the item
    #    text went empty, so every entry showed as a bare folder glyph. Creating
    #    a project is when a user notices, so create one here.
    before = [n for n, _pid in w.project_choices()]
    w._create()
    app.processEvents()
    choices = w.project_choices()
    picker = [win.nav_project.itemText(i) for i in range(win.nav_project.count())]
    print(f"project_choices: {[n for n, _p in choices][:4]}")
    print(f"picker hien thi: {picker[:4]}")
    if any(not name.strip() for name, _pid in choices):
        fails.append("project_choices tra ve ten rong")
    if len(choices) <= len(before):
        fails.append("tao project moi khong vao danh sach")
    for name, _pid in choices:
        if not any(name in text for text in picker):
            fails.append(f"picker khong hien ten {name!r}")
            break

    # 9. the title row sits above the sub-tabs, so what is on it must follow
    #    the title — + Project mới turned up in the corner of every other one.
    for idx, name in ((w._cowork_tab_idx, "Cowork"), (w._co4e_tab_idx, "Co4E"),
                      (w._folder_tab_idx, "Thu muc"),
                      (w._graphrag_tab_idx, "GraphRAG")):
        if idx < 0:
            continue
        win._goto(win._ROW_WORKSPACE, idx)
        app.processEvents()
        if w._new_btn.isVisible():
            fails.append(f"nut '+ Project moi' hien ca o man {name}")
    win._goto(win._ROW_WORKSPACE, w._project_tab_idx)
    app.processEvents()
    print(f"nut tao chi hien o Project: {not any('Project moi' in f for f in fails)}")

    print()
    for f in fails:
        print("FAIL  " + f)
    print("PASS  man Project khop ban ve" if not fails else f"{len(fails)} problem(s)")
    sys.stdout.flush()
    os._exit(1 if fails else 0)


if __name__ == "__main__":
    raise SystemExit(main())
