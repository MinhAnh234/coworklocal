"""FakeClock - offline stand-in for ``platform/qt/qt_scheduler_clock.py::
QtSchedulerClock`` (R07-T03).

``TaskScheduler`` (``core/task_scheduler.py``) needs a clock that can
``start(interval_ms, callback)`` / ``stop()`` / ``pump()``. In production
that's a real ``QTimer``, which means testing dispatch logic (what runs, in
what order, what gets re-armed) would otherwise require a live Qt event loop
ticking every 30 seconds. This double satisfies the same duck-typed
interface with manual control: ``fire()`` calls the scripted callback once,
synchronously, on whichever thread the test is running on - no timers, no
event loop, no waiting.
"""
from __future__ import annotations

from typing import Callable, Optional


class FakeClock:
    """Scriptable stand-in for :class:`QtSchedulerClock`.

    Args:
        running: whether ``start()`` has been called and ``stop()`` hasn't
            since - a test can assert on this to check lifecycle wiring.
        pump_count: how many times ``pump()`` was called - lets a test on
            ``TaskScheduler.stop()``'s drain loop assert the event loop was
            actually pumped while waiting for workers.
    """

    def __init__(self) -> None:
        self._callback: Optional[Callable[[], None]] = None
        self.interval_ms: Optional[int] = None
        self.running: bool = False
        self.pump_count: int = 0

    def start(self, interval_ms: int, callback: Callable[[], None]) -> None:
        self.interval_ms = interval_ms
        self._callback = callback
        self.running = True

    def stop(self) -> None:
        self.running = False

    def pump(self) -> None:
        self.pump_count += 1

    def fire(self) -> None:
        """Test helper: manually trigger one tick, as if the interval had
        elapsed. A no-op when the clock isn't running (matches a real
        ``QTimer`` never firing after ``stop()``)."""
        if self.running and self._callback is not None:
            self._callback()


__all__ = ["FakeClock"]
