"""Workspace ▸ Cowork against its wireframe (section 5).

The drawing heads the screen with the THREAD's title — "Gom số liệu doanh thu",
not the word "Cowork" — with the model beside it, Skills and Cuộc trò chuyện mới
on the right, and a caps TỆP ĐẦU RA (n) panel down the side.
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
    from PySide6.QtWidgets import QApplication

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
    from cowork_local.core.history import list_conversations, load_conversation
    from cowork_local.i18n import set_language, tr
    from cowork_local.state import AppContext

    set_language("vi")
    win = MainWindow(AppContext(AppConfig.load()), user_name="local")
    win.resize(1920, 1000)
    win.show()
    app.processEvents()
    win._goto(win._ROW_WORKSPACE, win.workspace._cowork_tab_idx)
    app.processEvents()
    c = win.cowork
    fails = []

    # a new thread has no title yet, so the screen name stands in
    print(f"chua mo thread: tieu de={c._title_lbl.text()!r}")
    if not c._title_lbl.text().strip():
        fails.append("tieu de trong khi chua mo thread")

    convs = list_conversations()
    if not convs:
        fails.append("khong co hoi thoai de kiem")
    else:
        conv = load_conversation(Path(convs[0]["path"]))
        c.load_conversation(conv)
        app.processEvents()
        want = conv.get("title", "")
        print(f"sau khi mo thread: tieu de={c._title_lbl.text()!r} (thread={want!r})")
        if want and c._title_lbl.text() != want:
            fails.append(f"tieu de khong theo thread: {c._title_lbl.text()!r} != {want!r}")
        if c._title_lbl.text() == tr("cowork.title") and want:
            fails.append("tieu de van la ten man hinh")

    # the files panel is a caps section carrying its own count
    head = c.output_section.header.text()
    print(f"pane tep dau ra: {head!r}")
    body = head.lstrip("▾▸ ").split(" (")[0]
    if body != body.upper():
        fails.append(f"tieu de pane chua viet hoa: {head!r}")
    if "(" not in head:
        fails.append("tieu de pane khong kem so luong")

    # toolbar keeps both actions the drawing shows
    for name, btn in (("Skills", c.skills_btn), ("chat moi", c._new_btn)):
        if not btn.isVisible():
            fails.append(f"thieu nut {name} tren thanh cong cu")
    print(f"nut tren thanh cong cu: {c.skills_btn.text()!r}, {c._new_btn.text()!r}")

    # the status strip, read left to right, is
    #   Agent: … · Định tuyến: … · ↓in ↑out · $cost · 📁 folder
    from PySide6.QtCore import QPoint as _P

    bar = c._usage_total_lbl.parentWidget()
    def _x(widget):
        return widget.mapTo(bar, _P(0, 0)).x()

    usage_text = c._usage_total_lbl.text()
    print(f"usage tren dai: {usage_text!r}")
    if not usage_text.strip():
        fails.append("dai duoi khong hien token/chi phi cua thread da mo")
    order = [("Agent", _x(c._agent_lbl)), ("Dinh tuyen", _x(c.routing_toggle)),
             ("usage", _x(c._usage_total_lbl))]
    folder = getattr(c, "folder_lbl", None)
    if folder is not None:
        order.append(("thu muc", _x(folder)))
    print("thu tu: " + " < ".join(f"{n}({x})" for n, x in order))
    for (n1, x1), (n2, x2) in zip(order, order[1:]):
        if x1 >= x2:
            fails.append(f"dai duoi sai thu tu: {n1} khong dung truoc {n2}")

    # the drawing gives Cowork two columns; History lives in the rail's RECENTS
    # and its pane arrives folded to the strip the drawing keeps
    w = win.workspace
    sb = w._sidebar
    print(f"vao Cowork: History hien={sb.isVisible()}")
    if sb.isVisible():
        fails.append("pane Lich su van o tren man Cowork — ban ve chi co 2 cot")
    w.show_history_pane()
    app.processEvents()
    print(f"sau 'Tat ca project…': History hien={sb.isVisible()} rong={sb.width()}px")
    if not sb.isVisible():
        fails.append("'Tat ca project…' khong mo duoc pane Lich su")
    w._on_history_fold(True)
    app.processEvents()

    # one heading on the files panel, with the chevron at its right — the
    # drawing has "TỆP ĐẦU RA (3) ›" and nothing above it
    from PySide6.QtCore import QPoint as _QP

    hdr_w = c.output_section.header
    chev = c._io_collapse_btn
    same_row = abs(hdr_w.mapTo(c, _QP(0, 0)).y() - chev.mapTo(c, _QP(0, 0)).y()) <= 8
    chev_right = chev.mapTo(c, _QP(0, 0)).x() > hdr_w.mapTo(c, _QP(0, 0)).x()
    # Count what the panel actually shows as headings. Asking whether the old
    # label is visible proved nothing: unparented, it reports invisible whether
    # or not the code hides it.
    from PySide6.QtWidgets import QLabel

    heads = [l.text() for l in c._io_widget.findChildren(QLabel)
             if l.isVisible() and l.text().strip()]
    print(f"tieu de hien trong pane: {heads} | "
          f"chevron cung hang={same_row} ben phai={chev_right}")
    if heads:
        fails.append(f"pane co tieu de thua ngoai '{hdr_w.text()}': {heads}")
    if not (same_row and chev_right):
        fails.append("chevron thu gon khong nam cuoi hang tieu de pane")

    # the composer spans the screen, under BOTH columns — inside the chat
    # column it stopped at the files panel's edge and shrank when files arrived
    from PySide6.QtCore import QPoint

    c._set_io_collapsed(False)
    app.processEvents()
    split = c.center_split
    files_pane = split.widget(1)
    comp_right = c.composer.mapTo(c, QPoint(c.composer.width(), 0)).x()
    files_left = files_pane.mapTo(c, QPoint(0, 0)).x()
    below = c.composer.mapTo(c, QPoint(0, 0)).y() > split.mapTo(c, QPoint(0, 0)).y()
    spans = comp_right > files_left
    print(f"o nhap: rong {c.composer.width()} / man {c.width()} | "
          f"duoi splitter={below} | trai qua duoi pane tep={spans}")
    if not below:
        fails.append("o nhap khong nam duoi hang than")
    if not spans:
        fails.append("o nhap dung lai o mep pane tep, khong trai het man")

    print()
    for f in fails:
        print("FAIL  " + f)
    print("PASS  man Cowork khop ban ve" if not fails else f"{len(fails)} problem(s)")
    sys.stdout.flush()
    os._exit(1 if fails else 0)


if __name__ == "__main__":
    raise SystemExit(main())
