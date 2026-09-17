"""HTML preview page that loads nothing from the web while "Block network" is on.

``QWebEngineView.setHtml`` happily fetches every ``<img src="https://...">``,
``<script src>`` and stylesheet the previewed file references — an outbound
connection the user never asked for, made by the app itself. The preview gets
its own off-the-record profile (so the interceptor below touches no other web
view, e.g. the GraphRAG renderer) and every remote request is refused while
the switch is on. Local files, ``data:`` and ``qrc:`` URLs still load.

Lifetime rule: a ``QWebEngineProfile`` must outlive every page that uses it.
A profile owned by the view is destroyed *before* the page (children die in
creation order) — Qt then warns "Release of profile requested but
WebEnginePage still not deleted" and the app can abort later (0xc0000409 in
Qt6Core.dll, seen when switching tabs). So there is ONE profile for the whole
app, owned by the QApplication, and each page is owned by its view.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtWebEngineCore import (
    QWebEnginePage, QWebEngineProfile, QWebEngineSettings, QWebEngineUrlRequestInterceptor,
)
from PySide6.QtWidgets import QApplication

from cowork_local.application.network import network_guard

_REMOTE_SCHEMES = frozenset({"http", "https", "ws", "wss", "ftp"})
_profile: Optional[QWebEngineProfile] = None
_blocker: Optional["RemoteRequestBlocker"] = None   # Python must hold it, or it is collected


class RemoteRequestBlocker(QWebEngineUrlRequestInterceptor):
    """Refuses remote URLs whenever the network guard says the network is blocked."""

    def interceptRequest(self, info) -> None:  # noqa: N802 - Qt override
        """Called by WebEngine for every request the page makes."""
        if info.requestUrl().scheme().lower() in _REMOTE_SCHEMES and network_guard.is_blocked():
            info.block(True)


def preview_profile() -> QWebEngineProfile:
    """The app-wide off-the-record profile shared by every HTML preview."""
    global _profile, _blocker
    if _profile is None:
        _profile = QWebEngineProfile(QApplication.instance())   # no storage name = off the record
        _blocker = RemoteRequestBlocker(_profile)
        _profile.setUrlRequestInterceptor(_blocker)
        _profile.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
    return _profile


def install_offline_page(view) -> None:
    """Give ``view`` a page on the shared preview profile.

    The previewed file is loaded with a ``file://`` base URL, and Qt refuses
    every remote resource of such a page unless
    ``LocalContentCanAccessRemoteUrls`` is on — so web images never showed,
    even with the network open. The switch is turned on for the profile; the
    interceptor is what keeps remote content out while "Block network" is on.
    """
    view.setPage(QWebEnginePage(preview_profile(), view))


__all__ = ["RemoteRequestBlocker", "install_offline_page", "preview_profile"]
