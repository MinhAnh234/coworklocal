"""GraphRAG rebuilds when it is opened, not every time a project is picked.

Switching project used to rescan the folder, redo the force layout and setHtml
the whole D3 page immediately — for a tab usually not on screen. With the rail's
picker one click away from anywhere, that fired constantly, and the rebuild you
did see on opening GraphRAG read as the page reloading itself.
"""
from __future__ import annotations

import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from capture_screens import (  # noqa: E402
    _apply_theme, _freeze_schedulers, _isolate_home, _load_fonts, owner_of)


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
    from cowork_local.i18n import set_language
    from cowork_local.state import AppContext

    set_language("vi")
    win = MainWindow(AppContext(AppConfig.load()), user_name="local")
    win.resize(1600, 950)
    win.show()
    app.processEvents()
    st, w = win.structure, win.workspace
    # R08-T14 split StructureGraphView: the browser view, the cached graph
    # and the scan/render steps all moved onto GraphRenderer, while the shell
    # only forwards the public methods. Probe the widget that owns them.
    st = owner_of(st, "web") or st
    fails: list[str] = []

    # startup itself must not build any of it
    if st.web is not None or st._graph is not None:
        fails.append("dung san do thi ngay luc khoi dong — startup phai nhe")

    # the idle warm-up builds the browser view and the first graph off the
    # click path (MainWindow fires this on a 3s timer; call it directly here)
    win._prewarm_graph()
    deadline = time.monotonic() + 30
    while st._graph is None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.02)
    if st._graph is None:
        print("FAIL  lam nong khong dung duoc do thi")
        sys.stdout.flush()
        os._exit(1)
    print(f"sau khi lam nong: web={'co' if st.web else 'chua'} do thi={'co' if st._graph else 'chua'}")

    calls = {"scan": 0, "html": 0}
    real_scan, real_html = st._scan, st._render_d3
    st._scan = lambda: (calls.__setitem__("scan", calls["scan"] + 1), real_scan())[1]
    st._render_d3 = lambda: (calls.__setitem__("html", calls["html"] + 1), real_html())[1]

    # ...so the click itself does nothing but show it — this is the flash
    t0 = time.monotonic()
    win._goto(win._ROW_WORKSPACE, w._graphrag_tab_idx)
    app.processEvents()
    print(f"bam vao GraphRAG: {(time.monotonic() - t0) * 1000:.0f}ms "
          f"_scan={calls['scan']} setHtml={calls['html']}")
    if calls["scan"] or calls["html"]:
        fails.append("bam vao GraphRAG van phai quet/nap lai trang — con chop trang")

    # re-entering an unchanged graph must not rebuild anything
    for _ in range(3):
        win._goto(win._ROW_WORKSPACE, w._project_tab_idx)
        app.processEvents()
        win._goto(win._ROW_WORKSPACE, w._graphrag_tab_idx)
        app.processEvents()
    print(f"vao lai 3 lan (khong doi gi): _scan={calls['scan']} setHtml={calls['html']}")
    if calls["scan"] or calls["html"]:
        fails.append("vao lai GraphRAG van quet/reload du khong co gi doi")

    # switching project off-screen defers the work
    win._goto(win._ROW_WORKSPACE, w._cowork_tab_idx)
    app.processEvents()
    ids = [pid for _n, pid in w.project_choices()]
    for pid in ids[1:3]:
        w.choose_project(pid)
        app.processEvents()
    print(f"doi {len(ids[1:3])} project khi dang o Cowork: _scan={calls['scan']} "
          f"setHtml={calls['html']} | can quet lan toi={st._needs_scan}")
    if calls["scan"]:
        fails.append("doi project van quet ngay du GraphRAG khong tren man")
    if len(ids) > 1 and not st._needs_scan:
        fails.append("doi project ma khong danh dau can quet lai")

    # ...and opening it does the work once
    win._goto(win._ROW_WORKSPACE, w._graphrag_tab_idx)
    app.processEvents()
    print(f"mo GraphRAG: _scan={calls['scan']}")
    if len(ids) > 1 and calls["scan"] != 1:
        fails.append(f"mo GraphRAG phai quet dung 1 lan, dang {calls['scan']}")

    print()
    for f in fails:
        print("FAIL  " + f)
    print("PASS  GraphRAG chi dung lai do thi khi can" if not fails
          else f"{len(fails)} problem(s)")
    sys.stdout.flush()
    os._exit(1 if fails else 0)


if __name__ == "__main__":
    raise SystemExit(main())
