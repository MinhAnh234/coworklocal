"""EPIC R07-T03: TaskScheduler <-> clock wiring, entirely through
tests/fakes/fake_clock.py::FakeClock — no real QTimer, no Qt event loop.

Scope note: this only exercises the clock injection seam (start arms+starts
the clock with `tick`, stop stops it), not the full dispatch/execution
pipeline (`_start` -> `AgentWorker` -> `execute_task`), which needs a real
``ctx``/provider and is exactly the kind of Qt-adjacent, thread-heavy path
better left to an offscreen integration test if/when R08 touches this file
again — recorded here rather than silently left untested.
"""
from __future__ import annotations

from cowork_local.core.task_scheduler import TICK_MS, TaskScheduler
from tests.fakes import FakeClock


def test_start_arms_and_starts_the_injected_clock(tmp_path):
    clock = FakeClock()
    scheduler = TaskScheduler(ctx=None, tasks_dir=tmp_path, clock=clock)
    ticks = []
    # Instance-attribute override, set BEFORE start(): TaskScheduler.start()
    # reads `self.tick`, which Python resolves to this override rather than
    # the class method, so we can count calls without a real due task/ctx.
    scheduler.tick = lambda: ticks.append(1)

    scheduler.start()

    assert clock.running is True
    assert clock.interval_ms == TICK_MS
    assert ticks == [1]   # the catch-up tick() call at startup


def test_clock_fire_drives_another_tick(tmp_path):
    clock = FakeClock()
    scheduler = TaskScheduler(ctx=None, tasks_dir=tmp_path, clock=clock)
    ticks = []
    scheduler.tick = lambda: ticks.append(1)
    scheduler.start()

    clock.fire()

    assert ticks == [1, 1]


def test_stop_stops_the_clock(tmp_path):
    clock = FakeClock()
    scheduler = TaskScheduler(ctx=None, tasks_dir=tmp_path, clock=clock)
    scheduler.tick = lambda: None
    scheduler.start()

    scheduler.stop()

    assert clock.running is False


def test_fire_after_stop_does_not_call_tick(tmp_path):
    clock = FakeClock()
    scheduler = TaskScheduler(ctx=None, tasks_dir=tmp_path, clock=clock)
    ticks = []
    scheduler.tick = lambda: ticks.append(1)
    scheduler.start()
    scheduler.stop()

    clock.fire()

    assert ticks == [1]   # only the startup catch-up tick, nothing after stop
