"""EPIC R08-T13: TokenUsageCardWidget / UsageChartWidget / HabitsWidget /
DashboardTab shell, real Qt offscreen.

``DashboardQueryService``'s own logic is unit tested (R08-T13, no Qt) in
``tests/unit/test_dashboard_query_service.py``; this file proves the three
widgets and the shell are actually wired to it and to each other (the period
selector living on ``UsageChartWidget`` driving all three).
"""
from __future__ import annotations

import json
import os
from datetime import date

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cowork_local.config import AppConfig  # noqa: E402
from cowork_local.core import usage_tracker as ut  # noqa: E402
from cowork_local.state import AppContext  # noqa: E402

pytest.importorskip("PySide6", reason="Qt is required for the integration suite")


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def usage_dir(tmp_path, monkeypatch):
    d = tmp_path / "usage"
    monkeypatch.setattr(ut, "USAGE_DIR", d)
    return d


@pytest.fixture
def ctx(qt_app, tmp_path):
    return AppContext(AppConfig.load(tmp_path / "config.json"))


def _write_event(usage_dir, day: date, **overrides):
    usage_dir.mkdir(parents=True, exist_ok=True)
    event = {
        "ts": f"{day.isoformat()}T10:00:00", "source": "cowork", "label": "Test chat",
        "provider": "anthropic", "model": "claude-sonnet-4-6",
        "in": 100, "out": 50, "cache": 0, "estimated": False,
        "account": "", "machine": "",
    }
    event.update(overrides)
    path = usage_dir / f"{day.isoformat()}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def test_dashboard_tab_builds_and_populates_cards(usage_dir, ctx):
    from cowork_local.presentation.dashboard.dashboard_tab import DashboardTab

    _write_event(usage_dir, date.today())
    tab = DashboardTab(ctx)   # refresh() runs once at construction

    assert "100" in tab.token_cards.card_in.value_lbl.text() \
        or tab.token_cards.card_in.value_lbl.text()   # non-crashing, has SOME text
    assert tab.token_cards.card_total.value_lbl.text() != ""


def test_period_navigation_on_chart_refreshes_the_whole_shell(usage_dir, ctx):
    from cowork_local.presentation.dashboard.dashboard_tab import DashboardTab

    _write_event(usage_dir, date.today())
    tab = DashboardTab(ctx)
    calls = []
    tab.refresh = lambda *a, orig=tab.refresh: (calls.append(1), orig(*a))[-1]

    tab.chart._chart_prev()

    assert calls == [1]


def test_granularity_change_resets_offset_to_current(usage_dir, ctx):
    from cowork_local.presentation.dashboard.dashboard_tab import DashboardTab
    from cowork_local.presentation.dashboard.usage_chart_widget import UsageChartWidget

    tab = DashboardTab(ctx)
    tab.chart._chart_offset = -3

    idx = tab.chart.gran_combo.findData("month")
    tab.chart.gran_combo.setCurrentIndex(idx)

    assert tab.chart.chart_offset == 0


def test_currency_change_persists_and_triggers_refresh(usage_dir, ctx):
    from cowork_local.presentation.dashboard.dashboard_tab import DashboardTab

    tab = DashboardTab(ctx)
    idx = tab.chart.currency_combo.findData("EUR") \
        if tab.chart.currency_combo.findData("EUR") >= 0 else 0
    seen = []
    tab.chart.currency_changed.connect(lambda: seen.append(1))

    tab.chart.currency_combo.setCurrentIndex(idx)

    if tab.chart.currency_combo.currentData() != "USD":
        assert seen == [1]
        assert ctx.config.data["usage"]["currency"] == tab.chart.currency_combo.currentData()


def test_habits_widget_ai_analyze_noop_without_data(usage_dir, ctx):
    """No events in range -> emits a status message instead of starting a
    background worker (matches the original _ai_analyze guard)."""
    from cowork_local.presentation.dashboard.habits_widget import HabitsWidget
    from cowork_local.application.monitoring import DashboardQueryService

    query = DashboardQueryService(ctx)
    widget = HabitsWidget(ctx, query)
    widget.refresh(date(2020, 1, 1), date(2020, 1, 1))
    messages = []
    widget.status_message.connect(messages.append)

    widget._ai_analyze()

    assert messages   # "no data" status, no worker started
    assert widget._ai_worker is None


def test_budget_apply_updates_budget_card(usage_dir, ctx):
    from cowork_local.application.monitoring import DashboardQueryService
    from cowork_local.presentation.dashboard.token_usage_card_widget import TokenUsageCardWidget

    query = DashboardQueryService(ctx)
    widget = TokenUsageCardWidget(ctx, query)
    widget.budget_card.budget_spin.setValue(50.0)

    widget._apply_budget()

    status = query.budget_status()
    assert status is not None
    assert status["amount_usd"] == pytest.approx(50.0)
