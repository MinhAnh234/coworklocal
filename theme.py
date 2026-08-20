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


# ---------------------------------------------------------------------------
# The one style sheet. `$token` placeholders are filled from the Palette above;
# use `${token}px` where a unit follows the name.
#
# Read it as a cascade: reset -> shell -> surfaces -> controls -> chrome.
# ---------------------------------------------------------------------------
_TEMPLATE = Template("""
/* ---- reset ------------------------------------------------------------ */
* { font-family: $font_family; font-size: ${font_size}px; }
QWidget { background: $bg; color: $text; }
QMainWindow::separator { background: $border; width: 1px; height: 1px; }
QSplitter::handle { background: $border; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }
QSplitter::handle:hover { background: $border_strong; }
QStatusBar { background: $bg; color: $text_faint; border-top: 1px solid $border; }
QToolTip {
    background: $overlay; color: $text; border: 1px solid $border_strong;
    border-radius: ${radius}px; padding: 5px 9px;
}

/* Icons are drawn at text scale, not as decoration. */
QPushButton, QToolButton, QComboBox, QTabBar { qproperty-iconSize: 15px 15px; }
QTreeWidget#navrail { qproperty-iconSize: 22px 16px; }

/* ---- shell ------------------------------------------------------------ */
QWidget#topbar { background: $bg; border: none; border-bottom: 1px solid $border; }
QLabel#brand { color: $text; font-size: 15px; font-weight: 700; background: transparent; }
QWidget#navWrap { background: $nav_bg; border-right: 1px solid $nav_border; }
QWidget#navWrap QTreeWidget, QWidget#navWrap QListWidget { background: transparent; border: none; }
QWidget#contentArea { background: $bg; }

/* Rail rows sit on nav_bg, so they need their own hover/selected steps — the
   generic ones are tuned against `bg` and wash out here. The active item also
   carries a 2px accent marker, so which section you are in survives even at a
   glance or for anyone who cannot separate the two greys. */
QWidget#navWrap QTreeWidget::item, QWidget#navWrap QListWidget::item {
    padding: 6px 4px; border-radius: ${radius}px;
}
QWidget#navWrap QTreeWidget::item:hover, QWidget#navWrap QListWidget::item:hover {
    background: $nav_hover;
}
QWidget#navWrap QTreeWidget::item:selected, QWidget#navWrap QListWidget::item:selected {
    background: $nav_selected; color: $text;
    border-left: 2px solid $accent; font-weight: 600;
}
/* Rows the project gate is holding shut: still listed, visibly not open. */
QWidget#navWrap QTreeWidget::item:disabled { color: $text_faint; }
/* The pinned bottom group (Dashboard, Monitoring) — one hairline separates it
   from the list above so "occasional" reads apart from "everyday". */
QTreeWidget#navrailBottom { border-top: 1px solid $nav_border; }
QScrollArea#navScroll { background: transparent; border: none; }
QScrollArea#navScroll > QWidget > QWidget { background: transparent; }
/* Monitoring ▸ Overview reads as titled sections down one column, the way the
   audit page draws it — a quiet caps heading with the content flat underneath,
   not six bordered boxes competing with the cards inside them. */
QGroupBox#monSection {
    background: transparent; border: none; margin-top: 16px;
    padding: 6px 0 0 0; font-weight: 700;
}
QGroupBox#monSection::title {
    subcontrol-origin: margin; subcontrol-position: top left; left: 2px; top: 0;
    padding: 0; color: $text_faint; font-size: 11px; letter-spacing: 0.5px;
}
/* Segmented control: two-to-four choices shown side by side (language, theme)
   instead of a drop-list you must open to see what the options even are. */
QPushButton#segItem {
    background: $surface_raised; color: $text_muted; border: 1px solid $border;
    padding: 4px 12px; margin: 0; border-radius: 0;
}
QPushButton#segItem:hover { background: $hover; color: $text; }
QPushButton#segItem:checked {
    background: $accent_solid; color: #FFFFFF; border-color: $accent_solid; font-weight: 600;
}
/* Table of contents down the left of the long dialogs (Settings, Task editor). */
QListWidget#sectionIndex { background: $surface; border-right: 1px solid $border; }
QListWidget#sectionIndex::item { padding: 7px 10px; border-radius: ${radius}px; }
QListWidget#sectionIndex::item:hover { background: $hover; }
QListWidget#sectionIndex::item:selected {
    background: $nav_selected; color: $text; font-weight: 600;
}
/* The strip under the typing box: agent · routing · usage · folder. Reads as
   status, not as a second toolbar, so the eye lands on the input first. */
QWidget#composerStatus { border-top: 1px solid $border; background: transparent; }
QWidget#composerStatus QLabel { color: $text_faint; font-size: 11px; }
QWidget#composerStatus QPushButton, QWidget#composerStatus QComboBox {
    background: transparent; border: none; color: $text_muted; font-size: 11px;
    padding: 2px 6px; border-radius: ${radius_sm}px;
}
QWidget#composerStatus QPushButton:hover, QWidget#composerStatus QComboBox:hover {
    background: $hover; color: $text;
}
/* Folder: the current path, written as the screen's title. */
QLabel#folderTitle { color: $text; font-size: 14px; font-weight: 600; background: transparent; }
/* A pair of view tabs inside a page header (Schedule, GraphRAG) — flatter and
   quieter than the app's main tab bars, since they switch a view, not a page. */
QTabBar#viewTabs::tab {
    background: transparent; color: $text_muted; border: none;
    padding: 4px 12px; margin: 0 2px; border-radius: ${radius}px;
}
QTabBar#viewTabs::tab:hover { background: $hover; color: $text; }
QTabBar#viewTabs::tab:selected { background: $active; color: $text; font-weight: 600; }
/* Co4E sidebar section headings — same quiet caps as the rail's RECENTS, so
   "which list am I looking at" is answered on screen, not in a tooltip. */
/* The action beside a Co4E section heading ("+ Mới", "Quản lý skill…"). The
   wireframe writes these as small accent text; as full buttons they were the
   loudest thing in the sidebar and each cost a row of height. */
QPushButton#co4eSectionAction {
    background: transparent; border: none; color: $accent;
    font-size: 11px; font-weight: 600; padding: 1px 4px;
    border-radius: ${radius_sm}px; qproperty-iconSize: 11px 11px;
}
QPushButton#co4eSectionAction:hover { background: $hover; color: $accent; }
QPushButton#co4eSectionAction:pressed { background: $active; }
QPushButton#co4eSectionHdr {
    color: $text_faint; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;
    background: transparent; border: none; text-align: left; padding: 2px 0;
}
QPushButton#co4eSectionHdr:hover { color: $text; }
/* Account row at the foot of the rail: who you are + the settings that follow
   you (provider, language, theme). Separated by a hairline like the group above. */
QWidget#navAccount { border-top: 1px solid $nav_border; }
QWidget#navAccount QComboBox {
    background: $surface_raised; border: 1px solid $nav_border; color: $text;
    padding: 3px 6px; border-radius: ${radius}px;
}
/* RECENTS section label — quiet, so the thread titles under it read first. */
QLabel#navSectionHdr {
    color: $text_faint; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;
    padding: 8px 8px 2px 8px; background: transparent;
}
QTreeWidget#navRecents { border-top: 1px solid $nav_border; }

/* Icon library cells. The audit page's note on this screen is that the cells
   had no visible edge on hover or selection, so you could not tell what you
   were about to pick — "cùng ngôn ngữ thẻ với Agent/Công cụ". */
QListWidget#iconGrid { background: transparent; border: none; }
QListWidget#iconGrid::item {
    border: 1px solid transparent; border-radius: ${radius}px;
    color: $text_muted; padding: 4px;
}
QListWidget#iconGrid::item:hover {
    border: 1px solid $accent; background: $hover; color: $text;
}
QListWidget#iconGrid::item:selected {
    border: 1px solid $accent; background: $accent_wash; color: $text;
}
/* Screen title beside its actions, same weight the other admin screens use. */
QLabel#monTitle { font-size: 15px; font-weight: 700; color: $text; }
/* Rail header — the primary action, so it is the one filled button up there. */
QPushButton#navNewChatBtn {
    background: $accent_solid; color: #FFFFFF; border: none; font-weight: 600;
    padding: 7px 10px; border-radius: ${radius}px; text-align: left;
}
QPushButton#navNewChatBtn:hover { background: $accent_solid_hover; }
QPushButton#navNewChatBtn:disabled { background: $border_strong; color: $text_faint; }
QComboBox#navProjectPick {
    background: $surface_raised; border: 1px solid $nav_border; color: $text;
    padding: 4px 8px; border-radius: ${radius}px;
}
/* Stand-in for the picker while the rail is 54px wide: icon only, no arrow —
   the arrow would eat a third of the width for no information. */
QToolButton#navProjectPickMini {
    background: $surface_raised; border: 1px solid $nav_border; border-radius: ${radius}px;
    padding: 4px; qproperty-iconSize: 16px 16px;
}
QToolButton#navProjectPickMini:hover { background: $nav_hover; }
QToolButton#navProjectPickMini:disabled { background: transparent; border-color: $border; }
QToolButton#navProjectPickMini::menu-indicator { image: none; width: 0; }

QPushButton#navSettingsBtn {
    background: transparent; border: none; color: $text_muted;
    /* Padding stays at 0: the row lays its own icon and label out, so that
       the spacing does not change with the platform's button style. */
    padding: 0; text-align: left; border-radius: ${radius}px;
    /* No side margin: Settings reads as one more row under Dashboard/Giám sát,
       so its icon has to start on their x. A 6px margin put it at 14 — near
       enough the middle of the collapsed 54px rail to look centred. */
    margin: 2px 0px 6px 0px;
}
QPushButton#navSettingsBtn:hover { background: $nav_hover; color: $text; }
QPushButton#navSettingsBtn:pressed { background: $active; }


/* ---- surfaces --------------------------------------------------------- */
QGroupBox {
    background: $surface; border: 1px solid $border; border-radius: ${radius_lg}px;
    margin-top: 14px; padding: 16px 12px 12px 12px; font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin; subcontrol-position: top left; left: 12px; top: 1px;
    padding: 0 6px; color: $text_muted; font-size: 12px; font-weight: 600;
}
QFrame[frameShape="4"], QFrame[frameShape="5"] { background: $border; border: none; }
QScrollArea { background: transparent; border: none; }
QAbstractScrollArea::corner { background: transparent; }

/* ---- tabs: an underline, not a pill. -------------------------------------
   The old pill tabs read as buttons and fought the real buttons for
   attention. A 2px rule under the active label is quieter and unambiguous. */
QTabWidget::pane { background: $bg; border: none; border-top: 1px solid $border; top: -1px; }
QTabBar { background: transparent; qproperty-drawBase: 0; }
QTabBar::tab {
    background: transparent; color: $text_muted; padding: 9px 14px; margin: 0 2px 0 0;
    border: none; border-bottom: 2px solid transparent; font-weight: 500;
}
QTabBar::tab:selected { color: $text; border-bottom: 2px solid $accent; font-weight: 600; }
QTabBar::tab:hover:!selected { color: $text; background: $hover; }

/* Co4E flow strip — browser-style tabs, so these stay enclosed. */
QTabBar#flowTabs::tab {
    background: $surface; color: $text_muted; border: 1px solid $border;
    border-radius: ${radius}px; padding: 6px 10px; margin: 0 3px 0 0; min-height: 22px;
}
QTabBar#flowTabs::tab:selected { background: $surface_raised; color: $text; border-color: $border_strong; }
QTabBar#flowTabs::tab:hover:!selected { background: $hover; color: $text; }
QPushButton#flowAddBtn {
    background: transparent; color: $text_muted; border: 1px solid $border;
    border-radius: ${radius}px; padding: 6px 0; font-size: 15px; min-height: 22px;
}
QPushButton#flowAddBtn:hover { background: $hover; color: $text; }

/* Co4E icon sidebar — no chrome until it is the active one. */
QTabBar#co4eSideTabs { qproperty-iconSize: 18px 18px; }
QTabBar#co4eSideTabs::tab {
    background: transparent; color: $text_muted; border: none;
    border-radius: ${radius}px; padding: 6px; margin: 0 4px 0 0;
}
QTabBar#co4eSideTabs::tab:selected { background: $accent_soft; color: $text; }
QTabBar#co4eSideTabs::tab:hover:!selected { background: $hover; color: $text; }
QGraphicsView#co4eCanvas {
    background: $surface; border: 1px solid $border; border-radius: ${radius_lg}px;
}

/* ---- text entry & item views ------------------------------------------ */
QPlainTextEdit, QTextEdit, QTextBrowser, QLineEdit, QSpinBox, QDoubleSpinBox,
QTreeView, QListView, QTableView, QTreeWidget, QListWidget, QTableWidget {
    background: $surface_raised; color: $text; border: 1px solid $border;
    border-radius: ${radius}px; selection-background-color: $selection_bg;
    selection-color: $selection_fg; outline: 0;
}
QPlainTextEdit, QTextEdit, QLineEdit, QSpinBox, QDoubleSpinBox { padding: 6px 8px; }
QPlainTextEdit:hover, QTextEdit:hover, QLineEdit:hover { border-color: $border_strong; }
QPlainTextEdit:focus, QTextEdit:focus, QLineEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid $focus_ring; }
QLineEdit:disabled, QPlainTextEdit:disabled, QTextEdit:disabled {
    background: $surface; color: $text_disabled;
}
/* Explicit up/down button geometry: once ANY spin-box subcontrol is styled,
   Qt uses exactly this rect for both painting AND hit-testing, so the
   clickable area can no longer drift from what's drawn (the previous
   unstyled default arrows misaligned their own click region at 125%/150%
   Windows display scaling — this pins both to the same rect instead). */
QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border; subcontrol-position: top right;
    width: 18px; height: 15px; border: none; background: transparent;
}
QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border; subcontrol-position: bottom right;
    width: 18px; height: 15px; border: none; background: transparent;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover { background: $hover; }
QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed,
QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed { background: $active; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url($chevron_up); width: 9px; height: 9px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url($chevron_down); width: 9px; height: 9px; }
QSpinBox::up-arrow:disabled, QSpinBox::down-arrow:disabled,
QDoubleSpinBox::up-arrow:disabled, QDoubleSpinBox::down-arrow:disabled { image: none; }

QTreeView::item, QListView::item, QTableView::item { padding: 4px 3px; border-radius: ${radius_sm}px; }
QTreeView::item:hover, QListView::item:hover { background: $hover; }
QTreeView::item:selected, QListView::item:selected, QTableView::item:selected {
    background: $accent_soft; color: $text;
}
/* The platform style draws its own dotted/solid focus rect on the current
   cell on top of the selection tint above — visible as a stray light border
   on a click. The selection tint already marks "current row"; drop the rect. */
QTreeView::item:focus, QListView::item:focus, QTableView::item:focus { outline: none; border: none; }
/* Kanban lanes (Schedule Task): seven lanes share the board width, so a card's
   own inset competes with the other six for space the same way the inter-lane
   gap did — trimmed to match. */
QListWidget#kanbanLane::item { padding: 3px 2px; }
QHeaderView::section {
    background: $bg; color: $text_muted; border: none;
    border-bottom: 1px solid $border; padding: 7px 6px; font-weight: 600;
}

/* ---- buttons -----------------------------------------------------------
   Default is a quiet outline. Weight is reserved for #primary / #danger, so
   at most one button per view should carry a fill. */
QPushButton {
    background: $surface_raised; color: $text; border: 1px solid $border_strong;
    border-radius: ${radius}px; padding: 7px 14px; font-weight: 500;
}
QPushButton:hover { background: $hover; border-color: $border_strong; }
QPushButton:pressed { background: $active; }
QPushButton:disabled { color: $text_disabled; background: $surface; border-color: $border; }
QPushButton:focus { border: 1px solid $focus_ring; }

QPushButton#primary {
    background: $accent_solid; color: $on_accent; border: 1px solid transparent; font-weight: 600;
}
QPushButton#primary:hover { background: $accent_solid_hover; }
QPushButton#primary:pressed { background: $accent_solid_active; }
QPushButton#primary:disabled { background: $surface; color: $text_disabled; border-color: $border; }

QPushButton#danger {
    background: $danger_solid; color: $on_accent; border: 1px solid transparent; font-weight: 600;
}
QPushButton#danger:hover { background: $danger_solid_hover; }
QPushButton#danger:disabled { background: $surface; color: $text_disabled; border-color: $border; }

/* Ghost buttons: nav section headers and icon-only chrome. */
QPushButton#navMenuBtn {
    background: transparent; border: none; border-radius: ${radius}px; padding: 5px 6px;
    font-weight: 600; font-size: 11px; letter-spacing: 0.6px; color: $text_faint; text-align: left;
}
QPushButton#navMenuBtn:hover { background: $hover; color: $text; }
QPushButton#navMenuBtn:pressed { background: $active; }

QToolButton {
    background: transparent; color: $text_muted; border: none;
    border-radius: ${radius}px; padding: 5px;
}
QToolButton:hover { background: $hover; color: $text; }
QToolButton:pressed { background: $active; }
QToolButton::menu-indicator { image: none; }

/* ---- pickers ----------------------------------------------------------- */
QComboBox {
    background: $surface_raised; color: $text; border: 1px solid $border_strong;
    border-radius: ${radius}px; padding: 6px 10px;
}
QComboBox:hover { background: $hover; }
QComboBox:focus { border-color: $focus_ring; }
QComboBox:disabled { color: $text_disabled; background: $surface; border-color: $border; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox::down-arrow { image: url($chevron_down); width: 10px; height: 10px; }
QComboBox::down-arrow:disabled { image: none; }
QComboBox QAbstractItemView {
    background: $overlay; color: $text; border: 1px solid $border_strong;
    border-radius: ${radius}px; padding: 4px; outline: none;
    selection-background-color: $accent_soft; selection-color: $text;
}

QMenu { background: $overlay; color: $text; border: 1px solid $border_strong;
        border-radius: ${radius}px; padding: 4px; }
QMenu::item { padding: 6px 14px; border-radius: ${radius_sm}px; }
QMenu::item:selected { background: $accent_soft; color: $text; }
QMenu::item:disabled { color: $text_disabled; }
QMenu::separator { height: 1px; background: $border; margin: 4px 6px; }

QMenuBar { background: $bg; color: $text; border-bottom: 1px solid $border; }
QMenuBar::item { padding: 5px 10px; border-radius: ${radius_sm}px; background: transparent; }
QMenuBar::item:selected { background: $hover; }

/* ---- toggles ----------------------------------------------------------- */
QCheckBox, QRadioButton { spacing: 8px; background: transparent; }
QCheckBox::indicator, QRadioButton::indicator {
    width: 16px; height: 16px; background: $surface_raised;
    border: 1px solid $border_strong; border-radius: ${radius_sm}px;
}
QRadioButton::indicator { border-radius: 9px; }
QCheckBox::indicator:hover, QRadioButton::indicator:hover { border-color: $accent; }
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background: $accent_solid; border-color: $accent_solid;
}
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {
    background: $surface; border-color: $border;
}
QCheckBox::indicator:checked:disabled, QRadioButton::indicator:checked:disabled {
    background: $border_strong; border-color: $border_strong;
}

QSlider::groove:horizontal { height: 4px; background: $border; border-radius: 2px; }
QSlider::sub-page:horizontal { background: $accent_solid; border-radius: 2px; }
QSlider::handle:horizontal {
    width: 14px; height: 14px; margin: -6px 0; border-radius: 7px;
    background: $surface_raised; border: 1px solid $border_strong;
}
QSlider::handle:horizontal:hover { border-color: $accent; }

QProgressBar {
    background: $surface; border: none; border-radius: 3px;
    height: 6px; text-align: center; color: $text_muted;
}
QProgressBar::chunk { background: $accent_solid; border-radius: 3px; }

/* ---- scrollbars: overlay-thin, no arrows. ------------------------------ */
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: $scroll_handle; border-radius: 4px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: $scroll_handle_hover; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: $scroll_handle; border-radius: 4px; min-width: 28px; }
QScrollBar::handle:horizontal:hover { background: $scroll_handle_hover; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; border: none; background: none; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }

/* ---- badges & inline text tones ---------------------------------------
   One shape, seven tones. Pick by meaning: badgeSuccess for a finished run,
   badgeDanger for a failed one — not by which colour looks nice. badgeNeutral
   is the odd one out: it deliberately uses OPAQUE tokens ($active/$text_muted,
   not an rgba() *_soft one) since it renders inside table cells that can sit
   over a selection tint — an rgba() background there would composite
   differently selected vs not (see Monitoring ▸ Sự kiện bảo mật's Hành động
   pill, which hit exactly this). */
QLabel#badge, QLabel#badgeSuccess, QLabel#badgeWarn, QLabel#badgeDanger,
QLabel#badgePurple, QLabel#badgePink, QLabel#badgeNeutral {
    border-radius: ${radius_sm}px; padding: 2px 8px; font-size: 12px; font-weight: 600;
}
QLabel#badge        { background: $info_soft;    color: $info; }
QLabel#badgeSuccess { background: $success_soft; color: $success; }
QLabel#badgeWarn    { background: $warning_soft; color: $warning; }
QLabel#badgeDanger  { background: $danger_soft;  color: $danger; }
QLabel#badgePurple  { background: $purple_soft;  color: $purple; }
QLabel#badgePink    { background: $pink_soft;    color: $pink; }
QLabel#badgeNeutral { background: $active;       color: $text_muted; }

/* ---- event-detail panel (Monitoring ▸ Sự kiện bảo mật) -----------------
   A neutral, low-emphasis tag — the "Loại" chip: a category label with no
   colour coding of its own (colour is reserved for the Trạng thái badge
   beside it). */
QLabel#neutralTag {
    background: $surface_raised; border: 1px solid $border; border-radius: ${radius_sm}px;
    padding: 2px 8px; font-size: 12px;
}
/* A short identifier shown as a bordered monospace chip (machine name,
   event id). */
QLabel#monoChip {
    font-family: "Cascadia Code", Consolas, monospace; background: $surface_raised;
    border: 1px solid $border; border-radius: ${radius_sm}px; padding: 1px 6px; font-size: 12px;
}
/* Section caption inside the panel — the same quiet caps heading as
   Monitoring ▸ Overview's group titles (monSection::title above), with a
   hairline under it since the panel has no group-box border of its own. */
QLabel#detailSectionHdr {
    color: $text_faint; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;
    padding-bottom: 4px; margin-top: 6px; border-bottom: 1px solid $border;
}
/* The blocked-detail text renders as a fixed dark "terminal" block — the
   same look in both themes, like a code snippet, so it reads consistently
   against whichever tint the row around it happens to carry. */
QWidget#detailCodeBlock { background: #1B1A19; border-radius: ${radius}px; }
QLabel#detailCodeText {
    color: #CCFF00; font-family: "Cascadia Code", Consolas, monospace; font-size: 12px;
}
QPushButton#detailCopyBtn {
    background: rgba(255,255,255,0.15); color: #FFFFFF; border: none;
    border-radius: ${radius_sm}px; padding: 3px 10px; font-size: 11px;
}
QPushButton#detailCopyBtn:hover { background: rgba(255,255,255,0.25); }

QLabel { background: transparent; }
QLabel#hint { color: $text_muted; }
QLabel#faint { color: $text_faint; }
QLabel#warning { color: $warning; font-weight: 600; }
QLabel#error { color: $danger; font-weight: 600; }
QLabel#success { color: $success; font-weight: 600; }
QLabel#sectionTitle { color: $text; font-size: 15px; font-weight: 600; }

/* ---- code, terminals & logs -------------------------------------------
   These read as "sunken" surfaces: the eye goes in, not across. */
QPlainTextEdit#codeEditor, QPlainTextEdit#termOutput, QPlainTextEdit#logView {
    background: $code_bg; color: $code_fg; border: none;
    font-family: $font_mono; selection-background-color: $code_selection;
}
QLineEdit#termInput {
    background: $code_bg; color: $code_fg; border: none; border-top: 1px solid $border;
    font-family: $font_mono; border-radius: 0; padding: 7px 10px;
}
QLineEdit#termInput:focus { border-top-color: $accent; }

/* The help-agent dock styles itself from these same tokens — it is a floating
   overlay that re-applies on every theme switch. See ui/help_agent_widget.py. */
""")


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
