"""Task 1 (sub-step 6g) — the new presentation/monitoring/monitoring_tab.py
container. Builds a real MonitoringTab against a real AppConfig/AppContext
(same convention as tests/routing/test_service.py: real config/context, only
the true external collaborators — here, none — get a fake), and verifies the
public API app.py depends on is intact: constructor signature,
``status_message`` signal, ``select_subtab``, ``nav_subtabs``,
``hide_tab_bar``.
"""
from __future__ import annotations

import copy
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from cowork_local.config import AppConfig, DEFAULT_CONFIG
from cowork_local.presentation.monitoring.monitoring_tab import MonitoringTab
from cowork_local.state import AppContext


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def ctx(tmp_path):
    config = AppConfig(data=copy.deepcopy(DEFAULT_CONFIG), path=tmp_path / "config.json")
    return AppContext(config)


def test_constructor_accepts_apps_py_call_signature(qapp, ctx) -> None:
    # app.py:499-502 calls MonitoringTab(self.ctx, cowork=..., structure=...,
    # task_scheduler=...) — all optional besides ctx.
    tab = MonitoringTab(ctx)
    assert tab.tabs.count() >= 1


def test_status_message_signal_exists(qapp, ctx) -> None:
    tab = MonitoringTab(ctx)
    received = []
    tab.status_message.connect(received.append)
    tab.status_message.emit("hello")
    assert received == ["hello"]


def test_select_subtab_and_nav_subtabs(qapp, ctx) -> None:
    tab = MonitoringTab(ctx)
    subtabs = tab.nav_subtabs()
    assert len(subtabs) == tab.tabs.count()
    tab.select_subtab(1)
    assert tab.tabs.currentIndex() == 1


def test_hide_tab_bar_does_not_raise(qapp, ctx) -> None:
    tab = MonitoringTab(ctx)
    tab.hide_tab_bar()


def test_full_refresh_populates_event_tabs_via_query_service(qapp, ctx, monkeypatch) -> None:
    from cowork_local.core import audit_log

    audit_dir = ctx.config.path.parent / "audit"
    monkeypatch.setattr(audit_log, "AUDIT_DIR", audit_dir)
    monkeypatch.setattr(audit_log, "_logger", audit_log.CanonicalAuditLogger(audit_dir))
    audit_log.record("security_block", "run_command", False, detail="blocked")
    audit_log.record("mcp_call", "search", True)
    audit_log.record("tool_call", "read_file", True)

    tab = MonitoringTab(ctx, cowork=None, structure=None, task_scheduler=None)
    tab.refresh()

    assert tab.security_tab.table.rowCount() == 1
    assert tab.mcp_tab.table.rowCount() == 1
    assert tab.action_tab.table.rowCount() == 3


def test_retranslate_does_not_raise(qapp, ctx) -> None:
    tab = MonitoringTab(ctx)
    tab._retranslate()


def test_settings_changed_callback_is_the_container_full_refresh(qapp, ctx) -> None:
    # Editing Settings from either the Sandbox or the nested Permissions
    # card's "Edit" button used to call the same
    # MonitoringTab._open_settings_and_refresh -> self.refresh(); the
    # container now wires both cards' on_settings_changed to its own
    # bound refresh method, so this equality is the direct replacement
    # for that identity.
    tab = MonitoringTab(ctx)
    assert tab.overview_tab.sandbox_card._on_settings_changed == tab.refresh
    assert tab.overview_tab.sandbox_card.permissions_card._on_settings_changed == tab.refresh
