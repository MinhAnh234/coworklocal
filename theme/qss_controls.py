"""Nửa sau của khuôn QSS: bề mặt, tab, ô nhập, nút, badge, log.

Cắt đôi khuôn QSS đúng mạch của chính nó: ``theme/qss.py`` giữ phần vỏ
(reset + shell: thanh rail, khung chính), file này giữ phần điều khiển.
Hai nửa được nối lại trong ``theme/qss.py``.

Sửa màu thì sang ``theme/palettes.py``; ở đây chỉ sửa hình dạng và khoảng cách.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from string import Template


QSS_CONTROLS = """/* ---- surfaces --------------------------------------------------------- */
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
"""
