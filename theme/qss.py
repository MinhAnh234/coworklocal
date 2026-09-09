"""Khuôn QSS của toàn ứng dụng — 470 dòng bảng kiểu.

Tách khỏi ``theme.py`` vì nó là **dữ liệu**, không phải logic: một chuỗi
``string.Template`` mà ``stylesheet()`` thay biến vào. Để chung thì mỗi lần
muốn sửa một hàm nhỏ trong theme.py lại phải cuộn qua 470 dòng CSS.

Sửa màu thì sang ``theme/palettes.py``; ở đây chỉ sửa hình dạng và khoảng cách.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from string import Template


from .qss_controls import QSS_CONTROLS

_QSS_SHELL = """
/* ---- reset ------------------------------------------------------------ */
* { font-family: $font_family; font-size: ${font_size}px; }
QWidget { background: $bg; color: $text; }
QMainWindow::separator { background: $border; width: 1px; height: 1px; }
QSplitter::handle { background: $border; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }
QSplitter::handle:hover { background: $border_strong; }
QStatusBar { background: $bg; color: $text_faint; border-top: 1px solid $border; }
/* Dòng phiên bản ở góc phải: đẩy chữ ra khỏi mép cửa sổ. Đặt padding ở nhãn
   chứ không ở QStatusBar — margin/padding của thanh không dịch được widget mà
   layout nội bộ của nó ghim vào sát mép phải. */
QStatusBar QLabel { padding-right: 10px; }
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
    padding: 6px 10px; border-radius: ${radius}px;
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
    /* No margin at all. A vertical one here was doing the opposite of what it
       read as: QVBoxLayout gave this button its geometry with the margin
       ignored (nav_bottom's bottom edge and this button's top edge measured
       the same y), while the PAINTER honoured it — so the only thing 10px/14px
       actually did was inset the hover fill, leaving Settings with a visibly
       shorter hover pill than the rows above. Spacing above/below the row is
       nav_rail's, which pins this button to the rows' own height. */
    margin: 0;
}
QPushButton#navSettingsBtn:hover { background: $nav_hover; color: $text; }
QPushButton#navSettingsBtn:pressed { background: $active; }


"""

#: Hai nửa nối lại. Cắt đôi vì một chuỗi 470 dòng vượt ngưỡng 400 dòng/file.
_TEMPLATE = Template(_QSS_SHELL + QSS_CONTROLS)
