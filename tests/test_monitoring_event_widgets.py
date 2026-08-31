"""Task 1 (sub-step 6b) — EventTable / EventDetailPanel widget smoke tests.

These instantiate real PySide6 widgets against the offscreen QPA platform
(no display needed, no pytest-qt dependency — a plain QApplication instance
is enough to construct/query widgets, only an actual event loop would need
more). Verifies the extraction into presentation/monitoring/shared/ wires up
without error and preserves the pre-refactor row/column behaviour.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from cowork_local.presentation.monitoring.shared.event_detail_panel import EventDetailPanel
from cowork_local.presentation.monitoring.shared.event_table import EventTable


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _sample_event(**overrides):
    ev = {"ts": "2026-05-25T15:03:00", "kind": "security_block", "name": "run_command",
          "ok": False, "detail": "blocked it", "account": "alice", "machine": "m1",
          "agent_role": "cowork"}
    ev.update(overrides)
    return ev


def test_event_table_security_events_hides_result_column(qapp) -> None:
    table = EventTable(show_result=False)
    table.retranslate()
    assert table.columnCount() == 6


def test_event_table_generic_shows_result_column(qapp) -> None:
    table = EventTable(show_result=True)
    table.retranslate()
    assert table.columnCount() == 7


def test_set_events_populates_rows_newest_first(qapp) -> None:
    table = EventTable(show_result=True)
    table.set_events([
        _sample_event(ts="2026-05-25T10:00:00", name="first"),
        _sample_event(ts="2026-05-25T12:00:00", name="second"),
    ])
    assert table.rowCount() == 2
    assert table.item(0, 4).text() == "second"
    assert table.item(1, 4).text() == "first"


def test_event_at_row_round_trips_full_event(qapp) -> None:
    table = EventTable(show_result=False)
    ev = _sample_event()
    table.set_events([ev])
    assert table.event_at_row(0) == ev


def test_apply_filter_hides_non_matching_rows(qapp) -> None:
    table = EventTable(show_result=True)
    table.set_events([_sample_event(name="run_command"), _sample_event(name="fetch_url")])
    table.apply_filter("fetch")
    hidden = [table.isRowHidden(r) for r in range(table.rowCount())]
    assert hidden.count(True) == 1


def test_detail_panel_shows_event_without_error(qapp) -> None:
    panel = EventDetailPanel()
    panel.retranslate()
    panel.show_event(_sample_event(), 0)
    assert panel._detail_text == "blocked it"
