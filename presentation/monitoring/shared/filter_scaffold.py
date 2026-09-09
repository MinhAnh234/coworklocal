"""Page scaffolding shared by the Security Events / MCP Call History / Action
Logs / Agent Status tabs: title + refresh button, optional search box +
AI-filter button, optional table+detail-panel split. Extracted from
``ui/monitoring_tab.py``'s ``MonitoringTab._wrap_with_filter``/
``_sync_event_detail`` — those used to be rebuilt 3 times almost identically
for the 3 event-table pages; this is the one shared implementation.

Builds directly into a caller-supplied ``page`` widget (which must not have a
layout yet) and returns a dict of the sub-widgets the caller needs to keep
(e.g. to implement its own ``retranslate()``).
"""
from __future__ import annotations

from typing import Callable, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSplitter, QTableWidget, QVBoxLayout, QWidget,
)

from ....i18n import bind_tip, tr
from ....ui.icons import icon
from .event_table import PAGE_SIZE_OPTIONS, ClickOutsideCloser, EventTable
from .event_detail_panel import EventDetailPanel


def _sync_event_detail(table: EventTable, panel: EventDetailPanel) -> None:
    # currentRow() alone is not enough: clearSelection() (used by the panel's
    # close button) drops the selection but leaves the current cell in
    # place, so a stale currentRow() would keep the panel open.
    """Đồng bộ panel chi tiết với dòng đang chọn trong bảng.

    Chỉ nhìn ``currentRow()`` là chưa đủ: ``clearSelection()`` (nút đóng của panel
    dùng) bỏ vùng chọn nhưng GIỮ nguyên ô hiện tại, nên chỉ dựa vào
    ``currentRow()`` thì panel sẽ không bao giờ đóng.
    """
    row = table.currentRow()
    has_selection = bool(table.selectedItems())
    ev = table.event_at_row(row) if (has_selection and row >= 0) else None
    if ev:
        panel.show_event(ev, row)
    panel.setVisible(bool(ev))


def build_filter_scaffold(
    page: QWidget, table: QTableWidget, *, on_refresh: Callable[[], None],
    title_key: Optional[str] = None, with_search: bool = True,
    with_detail: bool = False, with_page_size: bool = False,
    on_ai_filter: Optional[Callable[[QLineEdit, QPushButton], None]] = None,
) -> Dict[str, object]:
    """Dựng khung chung cho một tab sự kiện: tiêu đề, nút làm mới, ô tìm kiếm,
    nút lọc bằng AI, control "Số dòng/trang" (nếu ``with_page_size``) và panel
    chi tiết.

    Bốn tab sự kiện của màn Giám sát chỉ khác nhau ở nguồn dữ liệu, nên phần vỏ
    này được dựng một lần và dùng chung.
    """
    lay = QVBoxLayout(page)
    lay.setContentsMargins(0, 0, 0, 0)
    parts: Dict[str, object] = {}

    if title_key:
        hdr = QHBoxLayout()
        title_lbl = QLabel(tr(title_key))
        title_lbl.setStyleSheet("font-weight:700; font-size:14px;")
        hdr.addWidget(title_lbl)
        hdr.addStretch(1)
        refresh_btn = QPushButton(tr("monitoring.refresh"))
        refresh_btn.setIcon(icon("refresh"))
        refresh_btn.setObjectName("primary")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(on_refresh)
        hdr.addWidget(refresh_btn)
        lay.addLayout(hdr)
        parts.update(title_lbl=title_lbl, title_key=title_key, title_refresh_btn=refresh_btn)

    if with_search:
        row = QHBoxLayout()
        search = QLineEdit()
        search.setPlaceholderText(tr("monitoring.filter_placeholder"))
        search.textChanged.connect(table.apply_filter)
        ai_btn = QPushButton(tr("monitoring.ai_filter_btn"))
        ai_btn.setIcon(icon("sparkle"))
        # Bound rather than set once: this scaffold builds the button for all
        # three event tabs, and none of their retranslate() methods can reach a
        # tooltip that was applied here.
        bind_tip(ai_btn, "monitoring.ai_filter_tooltip")
        ai_btn.setCursor(Qt.PointingHandCursor)
        if on_ai_filter is not None:
            ai_btn.clicked.connect(lambda: on_ai_filter(search, ai_btn))
        row.addWidget(search, 1)
        row.addWidget(ai_btn)
        if with_page_size and isinstance(table, EventTable):
            # DF-006: the item-per-page count was never surfaced anywhere in
            # the UI (design called for it) — EventTable already trims to a
            # page size internally (default 300), this just makes that
            # number visible AND user-choosable instead of a fixed constant.
            page_size_lbl = QLabel(tr("monitoring.page_size_label"))
            page_size_combo = QComboBox()
            for n in PAGE_SIZE_OPTIONS:
                page_size_combo.addItem(str(n), n)
            current = table.page_size()
            page_size_combo.setCurrentIndex(
                PAGE_SIZE_OPTIONS.index(current) if current in PAGE_SIZE_OPTIONS else 2)
            page_size_combo.currentIndexChanged.connect(
                lambda i: table.set_page_size(page_size_combo.itemData(i)))
            row.addWidget(page_size_lbl)
            row.addWidget(page_size_combo)
            parts.update(page_size_label=page_size_lbl, page_size_combo=page_size_combo)
        lay.addLayout(row)
        parts.update(filter_edit=search, ai_filter_btn=ai_btn)

    if with_detail:
        # Click a row -> its full record opens in a detail panel on the
        # right (the table itself clips the detail text to 300 chars). A
        # pointing-hand cursor over the rows signals that they're clickable.
        table.setCursor(Qt.PointingHandCursor)
        detail = EventDetailPanel()
        detail.setVisible(False)
        detail.closed.connect(table.clearSelection)
        table.itemSelectionChanged.connect(lambda: _sync_event_detail(table, detail))
        split = QSplitter(Qt.Horizontal)
        split.addWidget(table)
        split.addWidget(detail)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 0)
        split.setChildrenCollapsible(False)
        split.setSizes([700, 320])
        lay.addWidget(split, 1)
        parts["detail_panel"] = detail

        # Esc, anywhere focus is inside this page, closes the panel the same
        # way the close button does.
        esc = QShortcut(QKeySequence(Qt.Key_Escape), page)
        esc.setContext(Qt.WidgetWithChildrenShortcut)
        esc.activated.connect(table.clearSelection)
        parts["detail_esc_shortcut"] = esc

        # A click outside both the table and the panel also closes it.
        click_filter = ClickOutsideCloser(table, detail, split)
        QApplication.instance().installEventFilter(click_filter)
        parts["detail_click_filter"] = click_filter
    else:
        lay.addWidget(table, 1)

    return parts
