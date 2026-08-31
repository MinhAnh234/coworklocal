"""EPIC R07-T03: QtSchedulerClock against a REAL QTimer/event loop.

``tests/unit/test_task_scheduler_dispatch.py`` covers ``TaskScheduler``'s
dispatch logic entirely through ``tests/fakes/fake_clock.py::FakeClock`` (no
Qt at all — that's the whole point of the extraction). This file is the
complement: it proves the adapter itself actually drives a real ``QTimer``
and pumps a real event loop, offscreen, the way ``test_history_dir_race.py``
proves ``ui/chat_panel.py``'s fix against real Qt rather than a double.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from cowork_local.infrastructure.qt.qt_scheduler_clock import QtSchedulerClock  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_start_fires_callback_on_the_real_qt_event_loop(qapp):
    clock = QtSchedulerClock()
    ticks = []
    clock.start(interval_ms=10, callback=lambda: ticks.append(1))
    try:
        QTest.qWait(200)   # let the real QTimer fire a few times
    finally:
        clock.stop()
    assert len(ticks) >= 1


def test_stop_prevents_further_callbacks(qapp):
    clock = QtSchedulerClock()
    ticks = []
    clock.start(interval_ms=10, callback=lambda: ticks.append(1))
    QTest.qWait(50)
    clock.stop()
    count_after_stop = len(ticks)
    QTest.qWait(100)
    assert len(ticks) == count_after_stop   # no more callbacks after stop()


def test_pump_processes_pending_events_without_raising(qapp):
    clock = QtSchedulerClock()
    clock.pump()   # must not raise even with nothing pending
