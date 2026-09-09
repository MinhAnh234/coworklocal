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

``setText(tr("k"))`` on its own is only correct for the instant it runs, and a
screen with dozens of such one-shot calls is where "I picked English and half
the screen is still Vietnamese" comes from. The :func:`bind_text` family
attaches the key to the widget instead, so every future language change
re-applies it — one line per widget, and nothing to remember in a separate
``retranslate`` method. Bindings hold the widget WEAKLY, so they are safe for
widgets that get rebuilt constantly (Kanban rows, calendar cells).
"""
from __future__ import annotations

import weakref
from typing import Any, Callable, Dict, Iterable, List, Tuple

LANGUAGES: Dict[str, str] = {"en": "English", "ja": "日本語", "vi": "Tiếng Việt"}
# Short codes shown in the compact top-bar switcher (Settings keeps the full names above).
LANGUAGE_SHORT: Dict[str, str] = {"en": "EN", "ja": "JP", "vi": "VN"}
DEFAULT_LANGUAGE = "vi"

_current = DEFAULT_LANGUAGE
_listeners: List[Callable[[], None]] = []
#: (weak ref to the widget, how to re-apply its text) — see :func:`bind_text`.
_bindings: List[Tuple["weakref.ref", Callable[[Any], None]]] = []

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
from . import dialog_buttons as _dialog_buttons
from . import connectors as _connectors

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
    **_dialog_buttons.STRINGS,
    **_connectors.STRINGS,
}


def set_language(lang: str) -> None:
    """Switch the active language and notify every registered persistent widget."""
    global _current
    if lang not in LANGUAGES:
        lang = DEFAULT_LANGUAGE
    if lang == _current:
        return
    _current = lang
    _apply_bindings()
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
    future call to :func:`set_language`. For a single widget whose text is one
    key, prefer :func:`bind_text` and friends — they need no callback of their
    own and cannot keep a destroyed widget alive."""
    _listeners.append(fn)
    fn()


# ---- per-widget bindings -------------------------------------------------

def _bind(widget: Any, apply: Callable[[Any], None]) -> Any:
    """Attach a text re-application to one widget, run it now, return the widget.

    ``apply`` takes the widget as its argument rather than closing over it: a
    closure would keep the widget alive for the life of the process, which is
    exactly what the weak reference here exists to avoid.

    The widget comes back out so a call site can bind IN PLACE of the one-shot
    call it replaces — ``bind_text(QLabel(), k)`` where ``QLabel(tr(k))`` was —
    without spending a line, which several screens here cannot afford (Gate S).
    """
    _bindings.append((weakref.ref(widget), apply))
    apply(widget)
    return widget


def _apply_bindings() -> None:
    """Re-apply every live binding; drop the ones whose widget is gone.

    Both halves of "gone" are handled: the Python wrapper collected (the weak
    ref answers None) and the C++ object deleted underneath a live wrapper
    (``RuntimeError``). Neither may stop the remaining widgets from updating.
    """
    alive: List[Tuple["weakref.ref", Callable[[Any], None]]] = []
    for ref, apply in _bindings:
        widget = ref()
        if widget is None:
            continue
        try:
            apply(widget)
        except RuntimeError:
            continue
        alive.append((ref, apply))
    _bindings[:] = alive


def bind_text(widget: Any, key: str, **kwargs) -> Any:
    """Keep ``widget``'s label on ``key`` through every language change."""
    return _bind(widget, lambda w: w.setText(tr(key, **kwargs)))


def bind_tip(widget: Any, key: str, **kwargs) -> Any:
    """Keep ``widget``'s tooltip on ``key`` through every language change."""
    return _bind(widget, lambda w: w.setToolTip(tr(key, **kwargs)))


def bind_placeholder(widget: Any, key: str, **kwargs) -> Any:
    """Keep an input's placeholder on ``key`` through every language change."""
    return _bind(widget, lambda w: w.setPlaceholderText(tr(key, **kwargs)))


def bind_items(widget: Any, keys: Iterable[str]) -> Any:
    """Keep a combo's item LABELS on ``keys``, by position.

    ``setItemText`` on purpose: clearing and re-adding the items would drop the
    per-item data every caller persists (routing mode, task type) and reset the
    current selection as a side effect of a translation.
    """
    keys = list(keys)

    def _apply(w: Any) -> None:
        """Re-label each item that still exists, leaving its data alone."""
        for i, key in enumerate(keys[:w.count()]):
            w.setItemText(i, tr(key))

    return _bind(widget, _apply)


def bind_dynamic(widget: Any, apply: Callable[[], None]) -> Any:
    """Bind text that is not one plain key — a count, a name, a joined list.

    ``apply`` takes no argument and re-reads whatever it needs itself; the
    widget is still what decides how long the binding lives.
    """
    return _bind(widget, lambda _w: apply())
