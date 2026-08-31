"""EPIC R08-T13: DashboardQueryService — no Qt.

``core/usage_tracker.py::USAGE_DIR`` is a module-level constant (not
injectable per-call except through an explicit ``directory=`` kwarg
``load_events`` alone accepts) — this is a pre-existing testability gap the
original ``ui/dashboard_tab.py`` also had (it had zero tests before this
task). Monkeypatching the module attribute is what lets these tests write
usage events without touching the real ``~/.cowork_local/usage/``.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from cowork_local.application.monitoring import DashboardQueryService
from cowork_local.config import AppConfig
from cowork_local.core import usage_tracker as ut
from cowork_local.state import AppContext


@pytest.fixture
def usage_dir(tmp_path, monkeypatch):
    import sys
    d = tmp_path / "usage"
    for mod in list(sys.modules.values()):
        if mod is not None and getattr(mod, "__name__", "").endswith("usage_tracker") and hasattr(mod, "USAGE_DIR"):
            monkeypatch.setattr(mod, "USAGE_DIR", d)
    monkeypatch.setattr(ut, "USAGE_DIR", d)
    return d


@pytest.fixture
def ctx(tmp_path):
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


def test_period_range_is_inclusive_end(usage_dir, ctx):
    query = DashboardQueryService(ctx, directory=usage_dir)
    start, end = query.period_range("week", 0)
    assert start <= end


def test_summary_aggregates_events_in_range(usage_dir, ctx):
    test_day = date(2025, 6, 15)
    _write_event(usage_dir, test_day, **{"in": 100, "out": 50})
    _write_event(usage_dir, test_day - timedelta(days=400), **{"in": 999, "out": 999})   # out of range
    query = DashboardQueryService(ctx, directory=usage_dir)

    summary = query.summary(test_day, test_day)

    assert len(summary["events"]) == 1
    assert summary["stats"]["in"] == 100
    assert summary["stats"]["out"] == 50
    assert summary["total_cost"] >= 0


def test_summary_empty_range_has_no_events(usage_dir, ctx):
    query = DashboardQueryService(ctx, directory=usage_dir)
    summary = query.summary(date(2020, 1, 1), date(2020, 1, 1))
    assert summary["events"] == []
    assert summary["stats"]["total"] == 0


def test_pricing_returns_a_dict_with_currency(usage_dir, ctx):
    query = DashboardQueryService(ctx, directory=usage_dir)
    pricing = query.pricing()
    assert "currency" in pricing


def test_chart_series_returns_points_for_the_granularity(usage_dir, ctx):
    today = date.today()
    _write_event(usage_dir, today)
    query = DashboardQueryService(ctx, directory=usage_dir)

    pts = query.chart_series("week", 0, "tokens")

    assert len(pts) == 7   # week view = 7 days
    assert all(isinstance(p, tuple) and len(p) == 2 for p in pts)


def test_budget_status_none_when_no_budget_set(usage_dir, ctx):
    query = DashboardQueryService(ctx, directory=usage_dir)
    assert query.budget_status() is None


def test_set_budget_then_status_reflects_it(usage_dir, ctx):
    query = DashboardQueryService(ctx, directory=usage_dir)
    query.set_budget(100.0, "USD")
    status = query.budget_status()
    assert status is not None
    assert status["amount_usd"] == pytest.approx(100.0)
