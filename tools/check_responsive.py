"""Measure what actually breaks on a small screen, screen by screen.

A pane is "clipped" when the width it is given is smaller than the width it says
it needs (minimumSizeHint): Qt then cuts content off instead of shrinking it,
which is what shows up as half-drawn buttons and cut-off labels.

Reports per destination, at a few window sizes, and lists the widest offenders
so a fix can be aimed at the right widget instead of guessed at.

Run:  python tools/check_responsive.py [width height ...]
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

from capture_screens import _freeze_schedulers, _isolate_home, _load_fonts  # noqa: E402

SIZES = [(1920, 1080), (1366, 768), (1280, 720)]


def panes(widget):
    """Direct children worth measuring: splitter panes and page-level boxes."""
    from PySide6.QtWidgets import QSplitter
    out = []
    for sp in widget.findChildren(QSplitter):
        for i in range(sp.count()):
            w = sp.widget(i)
            if w is not None and not w.isHidden():
                out.append((f"{sp.objectName() or 'splitter'}[{i}] {type(w).__name__}", w))
    return out


def main(argv) -> int:
    sizes = SIZES
    if len(argv) >= 2:
        sizes = [(int(argv[i]), int(argv[i + 1])) for i in range(0, len(argv) - 1, 2)]

    sandbox = _isolate_home()
    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    _load_fonts()
    _freeze_schedulers()

    from cowork_local.config import AppConfig, CONFIG_DIR
    assert str(sandbox) in str(CONFIG_DIR), f"isolation failed: {CONFIG_DIR}"

    from seed_demo_data import seed
    seed()

    from cowork_local.app import MainWindow
    from cowork_local.i18n import set_language
    from cowork_local.state import AppContext
    from cowork_local.theme import set_active_theme, stylesheet

    set_language("vi")
    cfg = AppConfig.load()
    set_active_theme(cfg.theme)
    app.setStyleSheet(stylesheet(cfg.theme))
    win = MainWindow(AppContext(cfg), user_name="local")
    win.show()
    for _ in range(6):
        app.processEvents()

    dests = [("Project", win._ROW_WORKSPACE, win.workspace._project_tab_idx),
             ("Cowork", win._ROW_WORKSPACE, win.workspace._cowork_tab_idx),
             ("Co4E", win._ROW_WORKSPACE, win.workspace._co4e_tab_idx),
             ("Folder", win._ROW_WORKSPACE, win.workspace._folder_tab_idx),
             ("GraphRAG", win._ROW_WORKSPACE, win.workspace._graphrag_tab_idx),
             ("Schedule", win._ROW_SCHEDULE, None),
             ("Dashboard", win._ROW_DASHBOARD, None),
             ("Monitoring", win._ROW_MONITORING, None)]

    print(f"cua so: minimumSizeHint = {win.minimumSizeHint().width()}"
          f"x{win.minimumSizeHint().height()}px")
    print()
    worst: dict[str, int] = {}
    for w, h in sizes:
        win.resize(w, h)
        for _ in range(4):
            app.processEvents()
        print(f"=== {w}x{h} ===")
        for name, page, sub in dests:
            win._goto(page, sub)
            for _ in range(4):
                app.processEvents()
            widget = win._page_widgets[page]
            need = widget.minimumSizeHint().width()
            have = widget.width()
            tight = [(n, p.minimumSizeHint().width(), p.width())
                     for n, p in panes(widget)
                     if p.minimumSizeHint().width() > p.width() + 1]
            flag = "" if need <= have else f"  <-- THIEU {need - have}px"
            print(f"   {name:11} can {need:5}px · duoc {have:5}px{flag}")
            for n, nd, hv in tight:
                print(f"        · {n:34} can {nd:4} duoc {hv:4}")
                worst[f"{name}/{n}"] = max(worst.get(f"{name}/{n}", 0), nd - hv)
        print()

    if worst:
        print("BO BO NHIEU NHAT:")
        for k, v in sorted(worst.items(), key=lambda kv: -kv[1])[:12]:
            print(f"   {v:5}px  {k}")
    else:
        print("KET QUA: khong pane nao bi bo o cac co da thu")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
