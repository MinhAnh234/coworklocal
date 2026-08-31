"""QtSchedulerClock - the ``QTimer``-backed periodic ticker `TaskScheduler`
needs, pulled out from ``core/task_scheduler.py`` into its own adapter
(R07-T03).

``core/task_scheduler.py::TaskScheduler`` is the only file in the scheduling
stack that imports Qt at all (confirmed by grep — ``core/tasks.py`` and
``core/task_executors.py`` are Qt-free). Everything it needs Qt FOR is small
and mechanical: an interval timer that calls back into ``tick()`` every
``TICK_MS``, plus, during ``stop()``, a way to pump the event loop so a
worker thread's queued ``finished_ok``/``failed`` signal still gets delivered
while draining running tasks (see the long comment on ``TaskScheduler.stop()``
for why that pump matters).

Wrapping exactly that surface — ``start(interval_ms, callback)``, ``stop()``,
``pump()`` — behind :class:`QtSchedulerClock` lets ``TaskScheduler`` take a
clock as a constructor parameter instead of constructing a ``QTimer``
itself. Production wiring is unchanged (``TaskScheduler`` defaults to a real
``QtSchedulerClock`` when no clock is passed); tests can inject
``tests/fakes/fake_clock.py::FakeClock`` to control ticks by hand with no Qt
event loop running at all.

See ``infrastructure/qt/__init__.py`` for why this lives under
``infrastructure/qt/`` and not the ``platform/qt/`` path the original plan
named.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QCoreApplication, QObject, QTimer


class QtSchedulerClock:
    """Owns one ``QTimer``. Not itself a ``QObject`` subclass — it OWNS a
    ``QObject``-parented timer instead of inheriting from one, so callers
    (like ``FakeClock`` in tests) can satisfy the same duck-typed interface
    without any Qt base class at all."""

    def __init__(self, parent: Optional[QObject] = None) -> None:
        # Parented so the timer is torn down with its owner instead of
        # outliving it — the same lifetime QTimer(self) gave it inside
        # TaskScheduler before this extraction.
        """Dựng ``QTimer`` gắn vào ``parent`` để nó bị dọn cùng chủ sở hữu, đúng vòng
        đời nó vốn có khi còn nằm trong ``TaskScheduler``.
        """
        self._timer = QTimer(parent)
        self._timer.timeout.connect(self._on_timeout)
        self._callback: Optional[Callable[[], None]] = None

    def _on_timeout(self) -> None:
        """Mỗi nhịp ``QTimer``: gọi callback đã đăng ký."""
        if self._callback is not None:
            self._callback()

    def start(self, interval_ms: int, callback: Callable[[], None]) -> None:
        """Arm and start the timer. Calling this again while already
        running re-arms it with the new interval/callback (matches
        ``QTimer.start()``'s own restart-on-repeat-call behaviour)."""
        self._callback = callback
        self._timer.setInterval(interval_ms)
        self._timer.start()

    def stop(self) -> None:
        """Dừng nhịp đếm."""
        self._timer.stop()

    def pump(self) -> None:
        """Process one batch of pending Qt events — used by
        ``TaskScheduler.stop()``'s bounded drain loop so a worker thread's
        queued completion signal can still be delivered while we wait for it
        to exit."""
        QCoreApplication.processEvents()


__all__ = ["QtSchedulerClock"]
