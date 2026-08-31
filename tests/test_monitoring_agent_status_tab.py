"""Task 1 (sub-step 6d) — AgentStatusTab widget smoke test."""
from __future__ import annotations

import copy
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from cowork_local.config import AppConfig, DEFAULT_CONFIG
from cowork_local.presentation.monitoring.tabs.agent_status_tab import AgentStatusTab


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class _FakeCowork:
    def active_workers(self):
        return [1, 2]


class _FakeTaskScheduler:
    def running_count(self):
        return 3


class _FakeCtx:
    def __init__(self, tmp_path):
        self.config = AppConfig(data=copy.deepcopy(DEFAULT_CONFIG), path=tmp_path / "c.json")
        self.config.data["agent_security"]["enabled"] = True


def test_agent_status_tab_has_no_search_or_detail(qapp, tmp_path) -> None:
    tab = AgentStatusTab(_FakeCtx(tmp_path), on_refresh_all=lambda: None)
    assert not hasattr(tab, "filter_edit")
    assert not hasattr(tab, "detail_panel")


def test_refresh_populates_six_rows_with_live_counts(qapp, tmp_path) -> None:
    tab = AgentStatusTab(_FakeCtx(tmp_path), on_refresh_all=lambda: None,
                         cowork=_FakeCowork(), task_scheduler=_FakeTaskScheduler())
    tab.refresh()
    assert tab.table.rowCount() == 6
    assert tab.table.item(0, 0).text()   # Cowork row has a label
    assert tab.table.cellWidget(0, 1) is not None   # badge pill widget


def test_retranslate_does_not_raise(qapp, tmp_path) -> None:
    tab = AgentStatusTab(_FakeCtx(tmp_path), on_refresh_all=lambda: None)
    tab.retranslate()
