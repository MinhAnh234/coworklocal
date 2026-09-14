"""DF-006 — the "Số dòng/trang" (rows per page) control plus real prev/next
pagination: EventTable's page-size/page-index state
(presentation/monitoring/shared/event_table.py) and its QComboBox + pager
button wiring in build_filter_scaffold (.../shared/filter_scaffold.py).

Options are 5/10/20/50/100 with a next/prev pager, per the QA follow-up on
DF-006 — the earlier fix only trimmed to a page size (dropping every row past
it with no way back); this exercises the real paging end to end."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication
QWidget = pytest.importorskip("PySide6.QtWidgets").QWidget

from cowork_local.presentation.monitoring.shared.event_table import (
    PAGE_SIZE_OPTIONS, EventTable,
)
from cowork_local.presentation.monitoring.shared.filter_scaffold import build_filter_scaffold


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _events(n: int):
    return [{"ts": f"2026-09-0{i % 9 + 1}T00:00:0{i % 9}", "kind": "tool_call",
              "name": f"e{i}", "ok": True, "detail": ""} for i in range(n)]


def test_page_size_options_are_5_10_20_50_100() -> None:
    assert PAGE_SIZE_OPTIONS == (5, 10, 20, 50, 100)


def test_default_page_size(qapp) -> None:
    table = EventTable()
    assert table.page_size() == 20
    table.set_events(_events(45))
    assert table.rowCount() == 20
    assert table.page_count() == 3
    assert table.current_page() == 0


def test_set_page_size_resets_to_first_page(qapp) -> None:
    table = EventTable()
    table.set_events(_events(45))
    table.next_page()
    assert table.current_page() == 1
    table.set_page_size(50)
    assert table.page_size() == 50
    assert table.current_page() == 0
    assert table.rowCount() == 45   # only 45 events total, fits in one page of 50


def test_next_prev_page_navigate_without_dropping_rows(qapp) -> None:
    table = EventTable()
    table.set_events(_events(45))
    table.set_page_size(20)
    assert table.rowCount() == 20

    table.next_page()
    assert table.current_page() == 1
    assert table.rowCount() == 20

    table.next_page()
    assert table.current_page() == 2
    assert table.rowCount() == 5   # last page: remainder

    table.next_page()   # already on last page — stays put
    assert table.current_page() == 2

    table.prev_page()
    assert table.current_page() == 1
    table.prev_page()
    table.prev_page()   # already on first page — stays put
    assert table.current_page() == 0


def test_page_changed_signal_reports_current_and_total(qapp) -> None:
    table = EventTable()
    seen = []
    table.page_changed.connect(lambda cur, total: seen.append((cur, total)))
    table.set_events(_events(45))
    table.set_page_size(20)
    table.next_page()
    assert seen[-1] == (1, 3)


def test_page_size_combo_is_only_added_when_requested(qapp) -> None:
    page = QWidget()
    table = EventTable()
    parts = build_filter_scaffold(page, table, on_refresh=lambda: None, with_page_size=False)
    assert "page_size_combo" not in parts
    assert "page_prev_btn" not in parts


def test_page_size_combo_changes_the_table(qapp) -> None:
    page = QWidget()
    table = EventTable()
    table.set_events(_events(45))
    parts = build_filter_scaffold(page, table, on_refresh=lambda: None, with_page_size=True)
    combo = parts["page_size_combo"]
    assert combo.count() == len(PAGE_SIZE_OPTIONS)
    assert combo.currentData() == 20   # matches EventTable's current page_size

    idx = PAGE_SIZE_OPTIONS.index(10)
    combo.setCurrentIndex(idx)

    assert table.page_size() == 10
    assert table.rowCount() == 10


def test_pager_buttons_disable_at_bounds_and_indicator_updates(qapp) -> None:
    page = QWidget()
    table = EventTable()
    table.set_events(_events(45))
    parts = build_filter_scaffold(page, table, on_refresh=lambda: None, with_page_size=True)
    table.set_page_size(20)
    prev_btn, next_btn = parts["page_prev_btn"], parts["page_next_btn"]
    indicator = parts["page_indicator_label"]

    assert not prev_btn.isEnabled()
    assert next_btn.isEnabled()
    assert indicator.text() == "Trang 1/3"

    next_btn.click()
    assert prev_btn.isEnabled()
    assert next_btn.isEnabled()
    assert indicator.text() == "Trang 2/3"

    next_btn.click()
    assert prev_btn.isEnabled()
    assert not next_btn.isEnabled()
    assert indicator.text() == "Trang 3/3"
