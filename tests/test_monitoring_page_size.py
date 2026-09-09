"""DF-006 — the "Số dòng/trang" (rows per page) control: EventTable's
page-size state (presentation/monitoring/shared/event_table.py) and its
QComboBox wiring in build_filter_scaffold (.../shared/filter_scaffold.py).
No dedicated test existed for this before — the design called for a
user-visible/choosable item-per-page control, and this exercises it end to
end (combo selection -> EventTable actually re-trimming its rows)."""
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


def test_default_page_size_matches_old_max_rows(qapp) -> None:
    table = EventTable()
    assert table.page_size() == 300
    table.set_events(_events(500))
    assert table.rowCount() == 300


def test_set_page_size_retrims_without_reloading(qapp) -> None:
    table = EventTable()
    table.set_events(_events(500))
    table.set_page_size(50)
    assert table.page_size() == 50
    assert table.rowCount() == 50


def test_page_size_combo_is_only_added_when_requested(qapp) -> None:
    page = QWidget()
    table = EventTable()
    parts = build_filter_scaffold(page, table, on_refresh=lambda: None, with_page_size=False)
    assert "page_size_combo" not in parts


def test_page_size_combo_changes_the_table(qapp) -> None:
    page = QWidget()
    table = EventTable()
    table.set_events(_events(500))
    parts = build_filter_scaffold(page, table, on_refresh=lambda: None, with_page_size=True)
    combo = parts["page_size_combo"]
    assert combo.count() == len(PAGE_SIZE_OPTIONS)
    assert combo.currentData() == 300   # matches EventTable's current page_size

    idx = PAGE_SIZE_OPTIONS.index(50)
    combo.setCurrentIndex(idx)

    assert table.page_size() == 50
    assert table.rowCount() == 50
