"""ScheduleCalculator - due-time / cron / interval math for Schedule Task,
extracted from ``core/tasks.py``'s "schedule math" section (R07-T02).

``core/tasks.py`` is already Qt-free (its own docstring says so), but it
still lives under ``core/`` where nothing enforces that "pure" claim - and it
is the ONE piece of scheduling logic ``docs/refactor/plan.md`` calls out as
needing its own unit tests (none existed before this task; see
``tests/unit/test_schedule_calculator.py``). Moving it to ``domain/tasks/``
makes the purity a build-time guarantee (``scripts/check_imports.py`` fails
the build if this file ever imports Qt, ``core``, or anything with I/O) and
gives the date math a home that is trivially unit-testable without going
through ``core/tasks.py``'s file-repository concerns at all.

Two pieces of this math are themselves implemented elsewhere in ``core/`` -
``core/cron.py::Cron`` (5-field cron parsing) and
``core/holiday_calendar.py::is_holiday`` (VN public holidays). Importing
``core`` from ``domain`` is exactly what ADR-001 rule I2 forbids (domain must
not know infrastructure/core exists), so this class takes them as
constructor-injected callables instead of importing them - the same
dependency-inversion shape ``application/conversations/conversation_
application_service.py`` (R04-T03) already uses for its provider factory.
``core/tasks.py`` wires the real ``Cron``/``is_holiday`` in; tests can inject
plain stub functions with zero I/O.
"""
from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Protocol

# Same on-disk format core/tasks.py::_TIME_FMT uses for schedule.run_at.
# Duplicated here (not imported - that would be a domain -> core edge) since
# it's a 1-line format string, not business logic.
_TIME_FMT = "%Y-%m-%d %H:%M"

_CRON_SEARCH_GUARD = 400   # matches the guard core/tasks.py used before extraction


class _CronLike(Protocol):
    """Structural shape this class needs from a cron object - satisfied by
    ``core/cron.py::Cron`` without this module importing it."""

    def next_after(self, after: datetime) -> Optional[datetime]:
        """Lần chạy kế tiếp sau một mốc thời gian; ``None`` nếu không bao giờ."""
        ...


def _parse_run_at(value: Optional[str]) -> Optional[datetime]:
    """Đọc chuỗi thời gian chạy thành ``datetime``; sai định dạng thì trả ``None``."""
    if not value:
        return None
    try:
        return datetime.strptime(value, _TIME_FMT)
    except ValueError:
        return None


class ScheduleCalculator:
    """Pure due-time computation for one task's ``schedule`` dict.

    ``is_holiday``: ``Callable[[date, country_code], bool]`` or ``None`` -
    when ``None``, a schedule with ``skip_holidays`` set simply never treats
    any day as a holiday (degrades gracefully instead of raising, mirroring
    how a caller who doesn't care about holidays can just not wire it up).

    ``make_cron``: ``Callable[[str], _CronLike]`` (raises on a malformed
    expression) or ``None`` - when ``None``, ``repeat_type == "cron"``
    schedules never produce a next run (same as an invalid expression today).
    """

    def __init__(self,
                is_holiday: Optional[Callable[[Any, str], bool]] = None,
                make_cron: Optional[Callable[[str], _CronLike]] = None) -> None:
        """``is_holiday``/``make_cron`` tiêm được nên lớp này không phụ thuộc vào lịch
        nghỉ hay bộ phân tích cron nào cụ thể — test truyền hàm giả vào.
        """
        self._is_holiday = is_holiday
        self._make_cron = make_cron

    def is_excluded_day(self, dt: datetime, sched: Dict[str, Any]) -> bool:
        """True when ``dt`` falls on a day this schedule must skip: a
        weekend (working_days_only) or a public holiday of the configured
        country."""
        if sched.get("working_days_only") and dt.weekday() >= 5:   # 5=Sat, 6=Sun
            return True
        if sched.get("skip_holidays") and self._is_holiday is not None:
            if self._is_holiday(dt.date(), sched.get("holiday_country", "")):
                return True
        return False

    def add_month(self, dt: datetime) -> datetime:
        """Calendar-aware +1 month, clamping the day to the target month's
        length (e.g. Jan 31 + 1 month -> Feb 28/29, not an overflow error)."""
        year = dt.year + (1 if dt.month == 12 else 0)
        month = 1 if dt.month == 12 else dt.month + 1
        day = min(dt.day, calendar.monthrange(year, month)[1])
        return dt.replace(year=year, month=month, day=day)

    def shift_off_excluded_days(self, dt: datetime, sched: Dict[str, Any]) -> datetime:
        """Push ``dt`` forward one day at a time until it lands on an
        allowed day (same time of day) - used for one-time schedules set on
        a weekend/holiday."""
        guard = 0
        while self.is_excluded_day(dt, sched) and guard < _CRON_SEARCH_GUARD:
            dt += timedelta(days=1)
            guard += 1
        return dt

    def compute_next_run(self, task: Dict[str, Any], after: datetime) -> Optional[datetime]:
        """The next run time strictly after ``after`` for a repeating task
        (daily / weekly / monthly / cron), or ``None`` for one-shot
        schedules. Occurrences on excluded days are skipped forward."""
        sched = task.get("schedule", {})
        repeat = sched.get("repeat_type", "none")

        if repeat == "cron":
            if self._make_cron is None:
                return None
            try:
                cron = self._make_cron(sched.get("cron_expression") or "")
            except Exception:
                # Any malformed-expression error the injected factory raises
                # (core/cron.py::CronError, or a fake's own error type in
                # tests) means "this schedule can't compute a next run" - not
                # a domain-layer crash.
                return None
            nxt = cron.next_after(after)
            guard = 0
            while nxt is not None and self.is_excluded_day(nxt, sched) and guard < _CRON_SEARCH_GUARD:
                nxt = cron.next_after(nxt)
                guard += 1
            return nxt

        base = _parse_run_at(sched.get("run_at"))
        if base is None:
            return None
        if repeat == "daily":
            advance = lambda d: d + timedelta(days=1)          # noqa: E731
        elif repeat == "weekly":
            advance = lambda d: d + timedelta(weeks=1)         # noqa: E731
        elif repeat == "monthly":
            advance = self.add_month
        else:
            return None
        nxt = base
        while nxt <= after:
            nxt = advance(nxt)
        guard = 0
        while self.is_excluded_day(nxt, sched) and guard < _CRON_SEARCH_GUARD:
            nxt = advance(nxt)
            guard += 1
        return nxt

    def due_tasks(self, tasks: List[Dict[str, Any]], now: datetime) -> List[Dict[str, Any]]:
        """Tasks that should start now: Scheduled + schedule enabled +
        run_at due."""
        due = []
        for t in tasks:
            if t.get("status") != "scheduled":
                continue
            sched = t.get("schedule", {})
            if not sched.get("enabled"):
                continue
            run_at = _parse_run_at(sched.get("run_at"))
            if run_at is not None and run_at <= now:
                due.append(t)
        return due


__all__ = ["ScheduleCalculator"]
