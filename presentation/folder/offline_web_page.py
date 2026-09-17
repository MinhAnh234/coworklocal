"""HTML preview page that loads nothing from the web while "Block network" is on.

``QWebEngineView.setHtml`` happily fetches every ``<img src="https://...">``,
``<script src>`` and stylesheet the previewed file references — an outbound
connection the user never asked for, made by the app itself. The preview gets
its own off-the-record profile (so the interceptor below touches no other web
view, e.g. the GraphRAG renderer) and every remote request is refused while
the switch is on. Local files, ``data:`` and ``qrc:`` URLs still load.
"""
from __future__ import annotations

from PySide6.QtWebEngineCore import (
    QWebEnginePage, QWebEngineProfile, QWebEngineUrlRequestInterceptor,
)

from cowork_local.application.network import network_guard

_REMOTE_SCHEMES = frozenset({"http", "https", "ws", "wss", "ftp"})


class RemoteRequestBlocker(QWebEngineUrlRequestInterceptor):
    """Refuses remote URLs whenever the network guard says the network is blocked."""

    def interceptRequest(self, info) -> None:  # noqa: N802 - Qt override
        """Called by WebEngine for every request the page makes."""
        if info.requestUrl().scheme().lower() in _REMOTE_SCHEMES and network_guard.is_blocked():
            info.block(True)


def install_offline_page(view) -> None:
    """Give ``view`` a private profile whose remote requests obey the guard."""
    profile = QWebEngineProfile(view)          # no storage name = off the record
    blocker = RemoteRequestBlocker(profile)
    profile.setUrlRequestInterceptor(blocker)
    view.setPage(QWebEnginePage(profile, view))
    view._remote_blocker = blocker             # keep the interceptor alive with the view


__all__ = ["RemoteRequestBlocker", "install_offline_page"]
