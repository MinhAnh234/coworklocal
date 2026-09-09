"""Runtime UI translation: English / Japanese / Vietnamese.

``tr(key, **kwargs)`` returns the string for the current language (falling
back to English, then the key itself so a missing entry is still visible
instead of crashing). ``.format(**kwargs)`` is applied when placeholders are
passed, so callers can do e.g. ``tr("composer.attachments", n=3)``.

Persistent, long-lived widgets (the main window chrome, the tabs, the
sidebar, the composer, ...) must reflect a language change immediately, so
they register a zero-arg callback via :func:`on_language_changed` that
re-applies ``tr()`` to their own text; the callback runs once right away and
again every time the language changes. Transient dialogs (Settings, Skills,
Flow, Permission...) are rebuilt from scratch each time they are opened, so
they simply call ``tr()`` while constructing their widgets and need no
registration.
"""
from __future__ import annotations

from typing import Callable, Dict, List

LANGUAGES: Dict[str, str] = {"en": "English", "ja": "日本語", "vi": "Tiếng Việt"}
# Short codes shown in the compact top-bar switcher (Settings keeps the full names above).
LANGUAGE_SHORT: Dict[str, str] = {"en": "EN", "ja": "JP", "vi": "VN"}
DEFAULT_LANGUAGE = "vi"

_current = DEFAULT_LANGUAGE
_listeners: List[Callable[[], None]] = []

# key -> {"en": ..., "ja": ..., "vi": ...}
from . import login_dialog as _login_dialog
from . import sidebar as _sidebar
from . import composer as _composer
from . import hint as _hint
from . import cowork_tab as _cowork_tab
from . import settings_dialog as _settings_dialog
from . import skills_dialog as _skills_dialog
from . import libreoffice_view as _libreoffice_view
from . import agents_admin_tab as _agents_admin_tab
from . import monitoring_overview as _monitoring_overview
from . import cloud_workspace as _cloud_workspace

# Gộp theo đúng thứ tự cũ: khoá trùng thì cụm sau thắng, y như khi tất cả
# còn nằm chung một dict literal.
STRINGS: Dict[str, Dict[str, str]] = {
    **_login_dialog.STRINGS,
    **_sidebar.STRINGS,
    **_composer.STRINGS,
    **_hint.STRINGS,
    **_cowork_tab.STRINGS,
    **_settings_dialog.STRINGS,
    **_skills_dialog.STRINGS,
    **_libreoffice_view.STRINGS,
    **_agents_admin_tab.STRINGS,
    **_monitoring_overview.STRINGS,
    **_cloud_workspace.STRINGS,
}


def set_language(lang: str) -> None:
    """Switch the active language and notify every registered persistent widget."""
    global _current
    if lang not in LANGUAGES:
        lang = DEFAULT_LANGUAGE
    if lang == _current:
        return
    _current = lang
    for fn in list(_listeners):
        try:
            fn()
        except RuntimeError:
            # The widget behind this callback was already destroyed — drop it.
            try:
                _listeners.remove(fn)
            except ValueError:
                pass


def get_language() -> str:
    """Mã ngôn ngữ đang dùng."""
    return _current


def tr(key: str, **kwargs) -> str:
    """Chuỗi đã dịch cho một khoá.

    Thiếu khoá thì trả về CHÍNH khoá đó — hiện ra một chuỗi lạ trên giao diện
    vẫn tốt hơn là làm vỡ màn hình. Thiếu bản dịch của ngôn ngữ hiện tại thì rơi
    về tiếng Anh.
    """
    entry = STRINGS.get(key)
    if not entry:
        return key
    text = entry.get(_current) or entry.get("en") or next(iter(entry.values()), key)
    return text.format(**kwargs) if kwargs else text


def on_language_changed(fn: Callable[[], None]) -> None:
    """Register a callback that re-applies translations to a persistent widget.

    Called once immediately (to apply the current language) and again on every
    future call to :func:`set_language`."""
    _listeners.append(fn)
    fn()
