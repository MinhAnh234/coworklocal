"""HAS_WEB_ENGINE — whether ``QWebEngineView`` is safe to construct here
(R08-T12/T14, extracted from ``ui/structure_graph_view.py``, lines 25-48 of
its original 1035-line version — the ONLY place this detection logic lived;
``ui/folder_tab.py`` used to import it FROM that module via a try/except).
"""
from __future__ import annotations

import sys
from pathlib import Path


def _frozen_onefile() -> bool:
    """True only for a PyInstaller ONEFILE build. Onefile extracts itself to a
    temp dir (sys._MEIPASS under %TEMP%), where the QtWebEngine helper process
    can't run — creating a QWebEngineView hard-crashes the app (reported as
    "click the graph tab → app closes"). A ONEDIR build keeps _MEIPASS as the
    ``_internal`` folder right next to the exe, where WebEngine works fine, so
    it keeps the full embedded D3/HTML view."""
    if not getattr(sys, "frozen", False):
        return False
    meipass = getattr(sys, "_MEIPASS", "")
    if not meipass:
        return False
    try:
        return Path(meipass).resolve().parent != Path(sys.executable).resolve().parent
    except OSError:  # can't tell → play safe: use the native/fallback view
        return True


# QtWebEngine is noisy and unreliable on the macOS runtime we support (GPU/
# helper-process failures leave the stacked view blank). The native Qt graph is
# already available and avoids that failure path entirely.
HAS_WEB_ENGINE = False

try:  # WebEngine + WebChannel are optional PySide6 add-ons
    if sys.platform == "darwin":
        raise ImportError("use native graph renderer on macOS")
    from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
    from PySide6.QtWebChannel import QWebChannel  # noqa: F401
    HAS_WEB_ENGINE = not _frozen_onefile()
except Exception:  # pragma: no cover
    HAS_WEB_ENGINE = False


__all__ = ["HAS_WEB_ENGINE"]
