"""The help panel must follow a language switch — transcript included.

retranslate() re-labelled the chrome but not the rendered HTML transcript, so
the greeting and the "AI Assistant" speaker label stayed in the language the
panel happened to be built in.
"""
from __future__ import annotations

import os
import re
import sys
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

    sys.stdout.reconfigure(encoding="utf-8")   # ja/vi text on a cp932 console
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
    win.resize(1400, 900)
    win.show()
    app.processEvents()

    panel = win.help_agent
    fails = []
    for lang in ("en", "ja", "vi"):
        win._set_language(lang) if hasattr(win, "_set_language") else set_language(lang)
        if not hasattr(win, "_set_language"):
            panel.retranslate()
        app.processEvents()

        # The panel greets by the signed-in name, not the placeholder.
        want = panel._greeting()
        shown = re.sub("<[^>]+>", " ", panel.log.toHtml())
        shown = " ".join(shown.split())
        # compare on the stable half of the sentence, the name is substituted
        probe = " ".join(want.split())[:28]
        state = "ok" if probe and probe in shown else "MISSING"
        print(f"{lang}: title={panel.title.text()!r} greeting={state}")
        if state != "ok":
            print(f"    muon: {probe!r}")
            print(f"    thay: {shown[:160]!r}")
        if state != "ok":
            fails.append(f"{lang}: transcript still shows another language")

    print()
    print("PASS  panel follows the language" if not fails
          else "\n".join(f"FAIL  {f}" for f in fails))
    sys.stdout.flush()
    os._exit(1 if fails else 0)


if __name__ == "__main__":
    raise SystemExit(main())
