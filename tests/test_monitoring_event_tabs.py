"""Task 1 (sub-step 6c) — SecurityEventsTab / McpTab / ActionLogsTab.

Widget smoke tests against the offscreen QPA platform (see
test_monitoring_event_widgets.py for why no pytest-qt is needed). Verifies
each tab wires build_filter_scaffold correctly, exposes the attributes the
container's retranslate loop needs, and forwards set_events to its table.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from cowork_local.presentation.monitoring.tabs.action_logs_tab import ActionLogsTab
from cowork_local.presentation.monitoring.tabs.mcp_tab import McpTab
from cowork_local.presentation.monitoring.tabs.security_events_tab import SecurityEventsTab


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.mark.parametrize("cls,expected_title_key", [
    (SecurityEventsTab, "monitoring.security_events_title"),
    (McpTab, "monitoring.mcp_history_title"),
    (ActionLogsTab, "monitoring.action_logs_title"),
])
def test_tab_exposes_container_facing_attributes(qapp, cls, expected_title_key) -> None:
    refresh_calls = []
    tab = cls(ctx=None, on_refresh_all=lambda: refresh_calls.append(1))
    assert tab.title_key == expected_title_key
    assert tab.filter_edit is not None
    assert tab.detail_panel is not None

    tab.title_refresh_btn.click()
    assert refresh_calls == [1]


def test_set_events_forwards_to_table(qapp) -> None:
    tab = SecurityEventsTab(ctx=None, on_refresh_all=lambda: None)
    tab.set_events([{"ts": "2026-01-01T00:00:00", "kind": "security_block", "name": "x",
                     "ok": False, "detail": "d", "account": "a", "machine": "m"}])
    assert tab.table.rowCount() == 1


def test_retranslate_does_not_raise(qapp) -> None:
    tab = McpTab(ctx=None, on_refresh_all=lambda: None)
    tab.retranslate()  # must not raise


def test_ai_filter_noop_when_search_box_empty(qapp) -> None:
    tab = ActionLogsTab(ctx=None, on_refresh_all=lambda: None)
    tab.ai_filter_btn.click()  # empty search text -> start_ai_filter no-ops, must not raise
