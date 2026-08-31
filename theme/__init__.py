"""The app's visual system: semantic design tokens + one style sheet template.

This replaces the previous mechanism, which was two hand-written Qt style
sheets (``_DARK`` / ``_LIGHT``) that duplicated each other and hard-coded ~105
hex literals, with a single source of truth:

    Palette (tokens)  ->  _TEMPLATE (one QSS)  ->  stylesheet(theme)

Rules of the system
-------------------
* **Nothing outside this module names a colour.** Widgets that paint with
  ``QPainter`` (charts, canvases, syntax highlighters) call :func:`palette` and
  read a token. Widgets that style themselves declaratively should instead be
  given an ``objectName`` and styled in ``_TEMPLATE`` below.
* **Tokens are semantic, not literal.** ``danger``/``text_muted``/``code_string``
  — never ``blue``/``grey2``. Adding a theme means adding a :class:`Palette`,
  not editing a style sheet.
* **No gradients, no glows.** The palette is Visual Studio Code's — "Dark
  Modern" and "Light Modern", taken from the shipped theme JSON. Flat surfaces,
  square-ish corners, one accent spent only on what the user acts on. Depth
  comes from the surface ramp and hairline borders, not from colour. Note the
  VS Code silhouette: the nav rail is *darker* than the content area, not
  lighter.

Contrast is held to WCAG AA (4.5:1) for body text and for text on filled
buttons. That is why ``accent`` and ``accent_solid`` are separate tokens: on a
dark background a blue readable *as text* is too light to carry white *as a
fill*, so each role gets the tint that passes.

Four VS Code values fall below AA and are nudged just far enough to clear it —
dark line numbers (3.59:1), light faint text on the sidebar (4.28:1), light
green (4.33:1) and light amber (3.12:1). Each carries a comment naming the
original value, so the deviation is auditable rather than silent.
"""
from __future__ import annotations

from .palettes import (  # noqa: F401 — giữ đường vào cũ
    DARK, LIGHT, Palette, _chevron_asset, _FONT, _MONO, _PALETTES,
)
from .qss import _TEMPLATE

from dataclasses import dataclass, asdict
from string import Template














# ---------------------------------------------------------------------------
# The one style sheet. `$token` placeholders are filled from the Palette above;
# use `${token}px` where a unit follows the name.
#
# Read it as a cascade: reset -> shell -> surfaces -> controls -> chrome.
# ---------------------------------------------------------------------------


def resolve_theme(theme: str) -> str:
    """Resolve ``'system'`` to ``'dark'``/``'light'`` from the OS colour scheme."""
    if theme in _PALETTES:
        return theme
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            scheme = app.styleHints().colorScheme()
            return "light" if scheme == Qt.ColorScheme.Light else "dark"
    except Exception:
        pass
    return "dark"


def palette(theme: str) -> Palette:
    """The token set for ``theme``. Painting code reads its colours from here."""
    return _PALETTES[resolve_theme(theme)]


# The theme the running app is currently showing. Painting code (paintEvent,
# QSyntaxHighlighter, canvas items) reads it via current_palette() instead of
# re-reading config.json — that used to cost a file open per repaint.
_active_theme = "dark"


def set_active_theme(theme: str) -> str:
    """Record the theme the app just applied. Call this next to every
    ``QApplication.setStyleSheet(stylesheet(...))``. Returns the resolved name."""
    global _active_theme
    _active_theme = resolve_theme(theme)
    return _active_theme


def current_theme() -> str:
    """The resolved theme ('dark'/'light') the app is showing right now."""
    return _active_theme


def current_palette() -> Palette:
    """Tokens for the theme the app is showing right now."""
    return _PALETTES[_active_theme]


def stylesheet(theme: str) -> str:
    """The application-wide Qt style sheet for ``theme``."""
    p = palette(theme)
    values = asdict(p)
    values["chevron_down"] = _chevron_asset("down", p.text_muted)
    values["chevron_up"] = _chevron_asset("up", p.text_muted)
    return _TEMPLATE.substitute(values)


def role_colors(theme: str) -> dict[str, str]:
    """Conversation/graph node colours keyed by role."""
    p = palette(theme)
    return {
        "user": p.role_user,
        "assistant": p.role_assistant,
        "tool": p.role_tool,
        "result": p.role_result,
        "error": p.role_error,
    }
