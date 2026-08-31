"""Hai bảng màu Tối và Sáng, cùng lớp ``Palette`` — dữ liệu, không logic.

Tách khỏi ``theme.py``: đây là chỗ duy nhất cần mở khi đổi màu. Mọi thứ khác
trong theme chỉ đọc từ đây.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from string import Template

def _chevron_asset(direction: str, color: str) -> str:
    """Render (and cache on disk) a small chevron PNG for QComboBox/QSpinBox
    arrow subcontrols. QSS's ``image:`` property only accepts a resource or
    file path, never a live QPixmap — and once ``::drop-down``/``::up-button``/
    ``::down-button`` are styled at all, Qt stops drawing its own built-in
    arrow, so without this the controls show no affordance whatsoever."""
    import hashlib
    import tempfile
    from pathlib import Path

    key = hashlib.md5(f"{direction}-{color}".encode()).hexdigest()[:10]
    path = Path(tempfile.gettempdir()) / "cowork_local_theme" / f"chevron_{key}.png"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtGui import QColor, QPainter, QPixmap

        size = 12
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        pen = p.pen()
        pen.setColor(QColor(color))
        pen.setWidthF(1.6)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        pts = ([QPointF(2.5, 4.5), QPointF(6, 8), QPointF(9.5, 4.5)] if direction == "down"
               else [QPointF(2.5, 7.5), QPointF(6, 4), QPointF(9.5, 7.5)])
        p.drawPolyline(pts)
        p.end()
        pm.save(str(path))
    return path.as_posix()

@dataclass(frozen=True)
class Palette:
    """Every colour and shape value the interface is allowed to use."""

    name: str

    # --- surfaces: a 4-step ramp from the window back to the frontmost layer.
    bg: str               # window / canvas backdrop
    surface: str          # panels, cards, group boxes (NOT the nav rail)
    surface_raised: str   # inputs, lists, trees — things you type or pick in
    overlay: str          # menus, tooltips, popups (floats above everything)
    sunken: str           # logs, code, terminals — things you read into
    hover: str            # hover wash on rows, tabs, ghost buttons
    active: str           # pressed / held state

    # The nav rail gets its own step rather than borrowing `surface`. It is a
    # permanent region of the window, not a card floating on the page.
    #
    # Following VS Code, the rail is *darker* than the content area (dark) or a
    # shade off white (light). The step is small on purpose — VS Code separates
    # the rail with a border, not a big tonal jump — so `nav_border` is doing
    # real work here and must stay visible.
    nav_bg: str
    nav_border: str
    nav_hover: str
    nav_selected: str

    # --- lines
    border: str           # default hairline
    border_strong: str    # hairline that must survive next to a filled surface
    focus_ring: str       # keyboard/typing focus

    # --- text
    text: str
    text_muted: str       # secondary copy, captions, group-box titles
    text_faint: str       # metadata, timestamps, placeholder
    text_disabled: str
    on_accent: str        # text drawn on top of a filled accent/status surface

    # --- accent: `accent` tints text & icons, `accent_solid` fills buttons.
    accent: str
    accent_solid: str
    accent_solid_hover: str
    accent_solid_active: str
    accent_soft: str      # translucent wash for selected rows (QSS only)
    accent_soft_hover: str
    accent_wash: str      # the same tint pre-blended to a solid, for Qt rich
                          # text (bgcolor=, <table>) where alpha is ignored

    # --- status
    success: str
    success_soft: str
    warning: str
    warning_soft: str
    danger: str
    danger_solid: str
    danger_solid_hover: str
    danger_soft: str
    info: str
    info_soft: str
    purple: str
    purple_soft: str
    pink: str
    pink_soft: str

    # --- selection (text selection inside editors and inputs)
    selection_bg: str
    selection_fg: str

    # --- scrollbars
    scroll_handle: str
    scroll_handle_hover: str

    # --- code & terminal
    code_bg: str
    code_fg: str
    code_gutter_bg: str
    code_gutter_fg: str
    code_selection: str
    code_comment: str
    code_keyword: str
    code_type: str
    code_func: str
    code_attr: str
    code_string: str
    code_number: str
    code_error: str

    # --- diff / inline change badges
    diff_add_bg: str
    diff_add_fg: str
    diff_del_bg: str
    diff_del_fg: str

    # --- charts
    chart_grid: str
    chart_label: str

    # --- conversation & graph node roles
    role_user: str
    role_assistant: str
    role_tool: str
    role_result: str
    role_error: str

    # --- shape & type
    radius_sm: int
    radius: int
    radius_lg: int
    font_family: str
    font_size: int
    font_mono: str

_FONT = '"Segoe UI Variable Text", "Segoe UI", "Inter", "Helvetica Neue", "Yu Gothic UI", "Meiryo", sans-serif'

_MONO = '"Cascadia Code", "JetBrains Mono", "Consolas", "SF Mono", monospace'

DARK = Palette(
    name="dark",
    # ---- VS Code "Dark Modern" ----------------------------------------------
    # Values taken from the shipped theme JSON. Where VS Code's own choice falls
    # below WCAG AA it is nudged just far enough to pass; each such value carries
    # a note with VS Code's original and the measured ratio.
    bg="#1F1F1F",                 # editor.background
    surface="#252526",            # panel / card
    surface_raised="#313131",     # input.background
    overlay="#252526",            # menus, tooltips
    sunken="#181818",             # logs, terminals — below the ramp
    hover="#2A2D2E",              # list.hoverBackground
    active="#37373D",             # list.inactiveSelectionBackground
    # The sidebar is DARKER than the editor — that is the VS Code silhouette.
    nav_bg="#181818",             # sideBar.background
    nav_border="#2B2B2B",         # sideBar.border
    nav_hover="#2A2D2E",
    nav_selected="#04395E",       # list.activeSelectionBackground
    border="#2B2B2B",             # panel.border
    border_strong="#3C3C3C",      # input.border
    focus_ring="#0078D4",         # focusBorder
    text="#CCCCCC",               # editor.foreground
    text_muted="#9D9D9D",         # descriptionForeground
    text_faint="#9A9A9A",       # lifted: #8B8B8B was 3.82:1 on input surfaces
    text_disabled="#5A5A5A",
    on_accent="#FFFFFF",
    accent="#4DAAFC",             # textLink.foreground — accent as TEXT
    accent_solid="#0078D4",       # button.background — accent as FILL
    accent_solid_hover="#026EC1",
    accent_solid_active="#005FB8",
    accent_soft="rgba(0,120,212,0.22)",
    accent_soft_hover="rgba(0,120,212,0.32)",
    accent_wash="#12283C",        # pre-blended: Qt rich text ignores alpha
    success="#89D185",            # gitDecoration added
    success_soft="rgba(137,209,133,0.16)",
    warning="#CCA700",            # editorWarning
    warning_soft="rgba(204,167,0,0.16)",
    danger="#F76464",             # editorError #F14C4C lifted (4.29:1 on panels)
    danger_solid="#C4302B",
    danger_solid_hover="#D9433C",
    danger_soft="rgba(241,76,76,0.16)",
    info="#4DAAFC",
    info_soft="rgba(77,170,252,0.16)",
    purple="#C586C0",             # Dark+ syntax purple
    purple_soft="rgba(197,134,192,0.16)",
    pink="#D16D9E",
    pink_soft="rgba(209,109,158,0.16)",
    selection_bg="#264F78",       # editor.selectionBackground
    selection_fg="#FFFFFF",
    scroll_handle="#4E4E4E",      # scrollbarSlider
    scroll_handle_hover="#5A5A5A",
    code_bg="#1F1F1F",
    code_fg="#CCCCCC",
    code_gutter_bg="#1F1F1F",
    # VS Code uses #6E7681 for line numbers — only 3.59:1. Lifted to clear AA.
    code_gutter_fg="#858D97",
    code_selection="#264F78",
    code_comment="#6A9955",       # ---- Dark+ syntax, unchanged --------------
    code_keyword="#569CD6",
    code_type="#4EC9B0",
    code_func="#DCDCAA",
    code_attr="#9CDCFE",
    code_string="#CE9178",
    code_number="#B5CEA8",
    code_error="#F44747",
    diff_add_bg="#1B3A1B",        # diffEditor inserted, pre-blended
    diff_add_fg="#89D185",
    diff_del_bg="#4B1818",        # diffEditor removed, pre-blended
    diff_del_fg="#F76464",
    chart_grid="#2B2B2B",
    chart_label="#9D9D9D",
    role_user="#4DAAFC",
    role_assistant="#4EC9B0",
    role_tool="#C586C0",
    role_result="#89D185",
    role_error="#F14C4C",
    radius_sm=3,                  # VS Code is squarer than the previous look
    radius=4,
    radius_lg=6,
    font_family=_FONT,
    font_size=13,
    font_mono=_MONO,
)

LIGHT = Palette(
    name="light",
    # ---- VS Code "Light Modern" ---------------------------------------------
    bg="#FFFFFF",                 # editor.background
    surface="#F8F8F8",            # sideBar / panel
    surface_raised="#FFFFFF",     # input.background
    overlay="#FFFFFF",
    sunken="#F3F3F3",
    hover="#F2F2F2",              # list.hoverBackground
    active="#E8E8E8",             # list.activeSelectionBackground
    nav_bg="#F8F8F8",             # sideBar.background
    nav_border="#E5E5E5",         # sideBar.border
    nav_hover="#F2F2F2",
    nav_selected="#E4E6F1",       # active row, tinted toward the accent
    border="#E5E5E5",
    border_strong="#CECECE",      # input.border
    focus_ring="#005FB8",         # focusBorder
    text="#3B3B3B",               # editor.foreground
    text_muted="#616161",
    # VS Code uses #767676 — 4.28:1 on the sidebar. Darkened to clear AA there.
    text_faint="#6E6E6E",
    text_disabled="#A0A0A0",
    on_accent="#FFFFFF",
    accent="#005FB8",             # textLink / button
    accent_solid="#005FB8",
    accent_solid_hover="#0258A8",
    accent_solid_active="#004C97",
    accent_soft="rgba(0,95,184,0.10)",
    accent_soft_hover="rgba(0,95,184,0.16)",
    accent_wash="#E6EEF8",
    # VS Code green #388A34 is 4.33:1 and amber #BF8803 only 3.12:1 — both lifted.
    success="#317A2D",
    success_soft="#DFF3DE",
    warning="#8F6500",            # VS Code #BF8803 = 3.12:1
    warning_soft="#FBF0D0",
    danger="#CD3131",             # editorError
    danger_solid="#CD3131",
    danger_solid_hover="#B82A2A",
    danger_soft="#FDEFEF",        # lightened so #CD3131 clears AA on it
    info="#005FB8",
    info_soft="#DDEBF9",
    purple="#6F42C1",
    purple_soft="#EDE7FA",
    pink="#B3247E",
    pink_soft="#FAE3F0",
    selection_bg="#ADD6FF",       # editor.selectionBackground
    selection_fg="#000000",
    scroll_handle="#C1C1C1",
    scroll_handle_hover="#A6A6A6",
    code_bg="#FFFFFF",
    code_fg="#3B3B3B",
    code_gutter_bg="#F8F8F8",
    code_gutter_fg="#656C76",     # VS Code #6E7681 = 4.33:1 on the gutter
    code_selection="#ADD6FF",
    code_comment="#008000",       # ---- Light+ syntax ------------------------
    code_keyword="#0000FF",
    code_type="#267F99",
    code_func="#795E26",
    code_attr="#E50000",
    code_string="#A31515",
    code_number="#098658",
    code_error="#CD3131",
    diff_add_bg="#DBF4DB",
    diff_add_fg="#1E6F1A",
    diff_del_bg="#FBE3E3",
    diff_del_fg="#B82A2A",
    chart_grid="#E5E5E5",
    chart_label="#616161",
    role_user="#005FB8",
    role_assistant="#267F99",
    role_tool="#6F42C1",
    role_result="#317A2D",
    role_error="#CD3131",
    radius_sm=3,
    radius=4,
    radius_lg=6,
    font_family=_FONT,
    font_size=13,
    font_mono=_MONO,
)

_PALETTES = {"dark": DARK, "light": LIGHT}
