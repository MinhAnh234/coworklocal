"""EPIC R07-T02: ScheduleCalculator — pure due-time/cron math.

This is the one piece of scheduling logic core/tasks.py's own docstring
claimed was "Qt-free so it can be unit-tested headlessly" but had NO unit
test at all before this task (confirmed by grepping tests/ for
"schedule_calculator"/"compute_next_run"/"cron" — nothing matched). These
tests exercise domain/tasks/schedule_calculator.py directly, with no Qt, no
filesystem, and fake holiday/cron callables so the module stays provably
zero-I/O.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from cowork_local.domain.tasks.schedule_calculator import ScheduleCalculator


def _sched(**overrides):
    base = {
        "enabled": True,
        "run_at": "2026-08-24 09:00",   # a Monday
        "repeat_type": "none",
        "cron_expression": None,
        "working_days_only": False,
        "skip_holidays": False,
        "holiday_country": "VN",
    }
    base.update(overrides)
    return base


def _task(**sched_overrides):
    return {"status": "scheduled", "schedule": _sched(**sched_overrides)}


class _FakeCron:
    """A cron stub that fires every day at a fixed hour:minute — enough to
    exercise the cron branch without depending on core/cron.py::Cron."""

    def __init__(self, expression: str):
        if expression == "bad":
            raise ValueError("bad cron expression")
        self.hour, self.minute = 10, 0

    def next_after(self, after: datetime) -> datetime:
        candidate = after.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)
        if candidate <= after:
            from datetime import timedelta
            candidate += timedelta(days=1)
        return candidate


def _is_weekend_holiday(date_, country):
    # A deterministic fake: only 2026-08-29 (a Saturday) counts as a holiday.
    return date_.isoformat() == "2026-08-29"


def test_daily_advances_by_one_day():
    calc = ScheduleCalculator()
    task = _task(repeat_type="daily")
    nxt = calc.compute_next_run(task, datetime(2026, 8, 24, 9, 0))
    assert nxt == datetime(2026, 8, 25, 9, 0)


def test_weekly_advances_by_seven_days():
    calc = ScheduleCalculator()
    task = _task(repeat_type="weekly")
    nxt = calc.compute_next_run(task, datetime(2026, 8, 24, 9, 0))
    assert nxt == datetime(2026, 8, 31, 9, 0)


def test_monthly_clamps_day_to_shorter_month():
    calc = ScheduleCalculator()
    task = _task(run_at="2026-01-31 09:00", repeat_type="monthly")
    nxt = calc.compute_next_run(task, datetime(2026, 1, 31, 9, 0))
    assert nxt == datetime(2026, 2, 28, 9, 0)   # Feb 2026 has 28 days


def test_one_shot_repeat_type_none_has_no_next_run():
    calc = ScheduleCalculator()
    task = _task(repeat_type="none")
    assert calc.compute_next_run(task, datetime(2026, 8, 24, 9, 0)) is None


def test_cron_without_injected_factory_returns_none():
    """No make_cron wired in -> a cron schedule simply never produces a next
    run, instead of crashing the caller."""
    calc = ScheduleCalculator()
    task = _task(repeat_type="cron", cron_expression="0 10 * * *")
    assert calc.compute_next_run(task, datetime(2026, 8, 24, 9, 0)) is None


def test_cron_uses_injected_factory():
    calc = ScheduleCalculator(make_cron=_FakeCron)
    task = _task(repeat_type="cron", cron_expression="0 10 * * *")
    nxt = calc.compute_next_run(task, datetime(2026, 8, 24, 9, 0))
    assert nxt == datetime(2026, 8, 24, 10, 0)


def test_malformed_cron_expression_returns_none_not_raise():
    calc = ScheduleCalculator(make_cron=_FakeCron)
    task = _task(repeat_type="cron", cron_expression="bad")
    assert calc.compute_next_run(task, datetime(2026, 8, 24, 9, 0)) is None


def test_working_days_only_skips_weekend():
    calc = ScheduleCalculator()
    # 2026-08-28 is a Friday; +1 day (daily) would land on Saturday 08-29.
    task = _task(run_at="2026-08-28 09:00", repeat_type="daily", working_days_only=True)
    nxt = calc.compute_next_run(task, datetime(2026, 8, 28, 9, 0))
    assert nxt.weekday() < 5   # Monday 08-31, not the weekend


def test_skip_holidays_uses_injected_is_holiday():
    calc = ScheduleCalculator(is_holiday=_is_weekend_holiday)
    # 2026-08-28 (Fri) + 1 day = 2026-08-29, which the fake marks a holiday.
    task = _task(run_at="2026-08-28 09:00", repeat_type="daily", skip_holidays=True)
    nxt = calc.compute_next_run(task, datetime(2026, 8, 28, 9, 0))
    assert nxt == datetime(2026, 8, 30, 9, 0)   # skipped past the holiday


def test_skip_holidays_without_injected_is_holiday_degrades_gracefully():
    calc = ScheduleCalculator()   # no is_holiday wired in
    task = _task(run_at="2026-08-28 09:00", repeat_type="daily", skip_holidays=True)
    nxt = calc.compute_next_run(task, datetime(2026, 8, 28, 9, 0))
    assert nxt == datetime(2026, 8, 29, 9, 0)   # no holiday check applied at all


def test_shift_off_excluded_days_moves_weekend_forward():
    calc = ScheduleCalculator()
    sched = _sched(working_days_only=True)
    saturday = datetime(2026, 8, 29, 9, 0)
    shifted = calc.shift_off_excluded_days(saturday, sched)
    assert shifted.weekday() < 5
    assert shifted >= saturday


def test_add_month_end_of_year_rolls_to_january():
    calc = ScheduleCalculator()
    assert calc.add_month(datetime(2026, 12, 15, 9, 0)) == datetime(2027, 1, 15, 9, 0)


def test_due_tasks_filters_by_status_enabled_and_run_at():
    calc = ScheduleCalculator()
    now = datetime(2026, 8, 27, 12, 0)
    due_now = _task(run_at="2026-08-27 09:00")
    due_now["title"] = "due"
    future = _task(run_at="2026-08-28 09:00")
    future["title"] = "future"
    disabled = _task(run_at="2026-08-27 09:00", enabled=False)
    disabled["title"] = "disabled"
    not_scheduled = _task(run_at="2026-08-27 09:00")
    not_scheduled["title"] = "backlog"
    not_scheduled["status"] = "backlog"

    result = calc.due_tasks([due_now, future, disabled, not_scheduled], now)
    assert [t["title"] for t in result] == ["due"]


def test_due_tasks_empty_when_no_tasks():
    calc = ScheduleCalculator()
    assert calc.due_tasks([], datetime(2026, 8, 27, 12, 0)) == []
