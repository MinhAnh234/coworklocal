"""Task 1 (sub-step 6f) — OverviewTab widget smoke test."""
from __future__ import annotations

import copy
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from cowork_local.config import AppConfig, DEFAULT_CONFIG
from cowork_local.presentation.monitoring.tabs.overview_tab import OverviewTab


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class _FakeCtx:
    def __init__(self, tmp_path):
        self.config = AppConfig(data=copy.deepcopy(DEFAULT_CONFIG), path=tmp_path / "c.json")
        self.started_at = time.time() - 30

    def save(self):
        pass

    def cowork_output_dir(self):
        return "."


def _make_tab(tmp_path):
    return OverviewTab(
        _FakeCtx(tmp_path), on_status_message=lambda _m: None,
        on_settings_changed=lambda: None, on_view_all_action_logs=lambda: None,
        action_logs_tab_visible=True)


def test_construction_and_retranslate(qapp, tmp_path) -> None:
    tab = _make_tab(tmp_path)
    tab.retranslate()  # must not raise


def test_refresh_with_no_events_shows_no_activity_text(qapp, tmp_path) -> None:
    tab = _make_tab(tmp_path)
    tab.retranslate()
    tab.refresh(events=[])
    assert tab.activity_lbl.text() != ""


def test_refresh_with_events_renders_activity_lines(qapp, tmp_path) -> None:
    tab = _make_tab(tmp_path)
    tab.retranslate()
    tab.refresh(events=[
        {"ts": "2026-01-01T00:00:00", "kind": "tool_call", "name": "run_command", "ok": True},
        {"ts": "2026-01-01T00:00:05", "kind": "security_block", "name": "blocked", "ok": False},
    ])
    assert "run_command" in tab.activity_lbl.text() or "blocked" in tab.activity_lbl.text()


def test_view_all_button_invokes_callback(qapp, tmp_path) -> None:
    calls = []
    tab = OverviewTab(
        _FakeCtx(tmp_path), on_status_message=lambda _m: None,
        on_settings_changed=lambda: None, on_view_all_action_logs=lambda: calls.append(1),
        action_logs_tab_visible=True)
    tab.view_all_btn.click()
    assert calls == [1]


def test_audit_group_visibility_follows_constructor_flag(qapp, tmp_path) -> None:
    hidden_tab = OverviewTab(
        _FakeCtx(tmp_path), on_status_message=lambda _m: None,
        on_settings_changed=lambda: None, on_view_all_action_logs=lambda: None,
        action_logs_tab_visible=False)
    assert hidden_tab.audit_group.isHidden() is True
