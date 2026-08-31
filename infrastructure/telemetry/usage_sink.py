"""Token-usage telemetry as a publish/subscribe seam (R03-T06).

Before this module every provider adapter reached straight into
``core/usage_tracker.py`` and wrote a dashboard row itself, which meant the
provider layer owned a telemetry policy decision ("where do usage numbers go?")
and no test could observe a turn's token accounting without touching the real
``~/.cowork_local/usage/`` files.

Now a provider only *describes what happened* — it publishes an immutable
:class:`UsageEvent` — and subscribers decide what to do with it. The default
subscriber, :class:`UsageTrackerSink`, forwards to the existing usage tracker so
the Dashboard keeps working byte-for-byte; tests swap in
:class:`InMemoryUsageSink` and assert on the events directly.

Every publish path is failure-tolerant on purpose: telemetry must never be the
reason a chat turn dies, which is the same contract
``usage_tracker.record()`` already documents.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

logger = logging.getLogger("cowork_local.telemetry.usage")


@dataclass(frozen=True)
class UsageEvent:
    """One provider turn's token accounting.

    Frozen so a subscriber cannot mutate an event the next subscriber in the
    chain is about to receive. ``source``/``label`` stay optional: the usage
    tracker already derives them from thread-local context set by whoever ran
    the turn, and a provider adapter has no business knowing which UI surface
    invoked it.
    """

    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    # True when the counts are a ~4-chars-per-token approximation because the
    # gateway never sent a usage block. Surfaced in the Dashboard so users know
    # which rows are measured and which are guessed.
    estimated: bool = False
    source: Optional[str] = None   # None -> tracker's thread-local context
    label: Optional[str] = None    # None -> tracker's thread-local context
    extras: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        """Billable token count for this turn (cached tokens are already part
        of the input count reported by every gateway we support, so adding them
        again would double-count)."""
        return int(self.input_tokens) + int(self.output_tokens)

    def to_dict(self) -> Dict[str, Any]:
        """JSON-friendly view, using the same short keys as the usage tracker's
        on-disk rows so a caller can diff an event against a stored row."""
        return {
            "provider": self.provider,
            "model": self.model,
            "in": int(self.input_tokens),
            "out": int(self.output_tokens),
            "cache": int(self.cached_tokens),
            "estimated": bool(self.estimated),
            "source": self.source or "",
            "label": self.label or "",
        }


@runtime_checkable
class UsageEventSink(Protocol):
    """Anything that can receive :class:`UsageEvent`s.

    A ``Protocol`` rather than a base class so a plain object (or a test double,
    or a Qt-side adapter that re-emits a signal) qualifies without inheriting
    from infrastructure code.
    """

    def emit(self, event: UsageEvent) -> None:
        """Handle one usage event. Implementations MUST NOT raise."""


class UsageTrackerSink:
    """Default subscriber: writes each event through ``core/usage_tracker.py``.

    Keeps the existing Dashboard/telemetry pipeline (daily JSONL files, shared
    cross-machine mirror, per-thread accumulator) as the single writer, so
    routing this through an event seam changed the plumbing without changing
    a single stored byte.
    """

    def __init__(self, recorder=None) -> None:
        # The recorder is injectable so a test can verify the forwarding
        # contract without importing the real tracker (and its config paths).
        """``recorder`` tiêm được để test kiểm việc chuyển tiếp mà không phải nạp bộ
        theo dõi thật (và cả đống đường dẫn cấu hình của nó).
        """
        self._recorder = recorder

    def _resolve_recorder(self):
        """Late-bind ``usage_tracker.record``.

        Imported on first use rather than at module import so telemetry stays
        out of the import graph of anything that merely *declares* a sink.
        """
        if self._recorder is None:
            from ...core import usage_tracker as tracker

            self._recorder = tracker.record
        return self._recorder

    def emit(self, event: UsageEvent) -> None:
        """Forward one event; swallow every failure (telemetry is never fatal)."""
        try:
            record = self._resolve_recorder()
            if event.source is None:
                # Normal path: the worker thread already tagged its own
                # source/label via set_context(), so record() attributes the row.
                record(
                    event.provider, event.model,
                    int(event.input_tokens), int(event.output_tokens),
                    int(event.cached_tokens), estimated=bool(event.estimated),
                )
                return

            # Event carries its own attribution: apply it for this single write
            # and restore the thread's previous context afterwards, so a
            # re-attributed event cannot silently relabel every later turn that
            # runs on the same worker thread.
            from ...core import usage_tracker as tracker

            previous_source, previous_label = tracker.current_context()
            tracker.set_context(event.source, event.label or "")
            try:
                record(
                    event.provider, event.model,
                    int(event.input_tokens), int(event.output_tokens),
                    int(event.cached_tokens), estimated=bool(event.estimated),
                )
            finally:
                tracker.set_context(previous_source, previous_label)
        except Exception:  # noqa: BLE001 — usage tracking must never break a turn
            logger.debug("usage sink: forwarding to usage_tracker failed", exc_info=True)


class InMemoryUsageSink:
    """Collects events in a list — the test double for usage assertions."""

    def __init__(self) -> None:
        """Giữ sự kiện trong bộ nhớ cho test. Có khoá vì sự kiện đến từ nhiều luồng."""
        self.events: List[UsageEvent] = []
        self._lock = threading.Lock()

    def emit(self, event: UsageEvent) -> None:
        """Append under a lock: parallel Co4E flows publish from several worker
        threads at once and ``list.append`` alone would still be atomic, but the
        lock also makes :meth:`snapshot` a consistent read."""
        with self._lock:
            self.events.append(event)

    def snapshot(self) -> List[UsageEvent]:
        """A copy of everything received so far."""
        with self._lock:
            return list(self.events)

    def clear(self) -> None:
        """Xoá sạch sự kiện đã ghi (dùng trong test)."""
        with self._lock:
            self.events.clear()

    @property
    def total_tokens(self) -> int:
        """Tổng token của mọi sự kiện đã ghi."""
        return sum(e.total_tokens for e in self.snapshot())


class CompositeUsageSink:
    """Fans one event out to several subscribers.

    This is what makes the seam useful beyond the Dashboard: a future consumer
    (per-workspace budget guard, live cost meter) subscribes alongside the
    tracker instead of patching provider code again. One failing subscriber is
    logged and skipped so it cannot starve the others.
    """

    def __init__(self, sinks=None) -> None:
        """Gộp nhiều đích nhận sự kiện thành một. Dùng ``RLock`` vì một đích có thể gọi
        ngược lại vào composite trong lúc đang phát.
        """
        self._sinks: List[UsageEventSink] = list(sinks or ())
        self._lock = threading.RLock()

    def add(self, sink: UsageEventSink) -> None:
        """Thêm một đích ghi vào nhóm."""
        with self._lock:
            self._sinks.append(sink)

    def remove(self, sink: UsageEventSink) -> None:
        """Detach a subscriber; a sink that was never added is ignored so
        teardown code can call this unconditionally."""
        with self._lock:
            if sink in self._sinks:
                self._sinks.remove(sink)

    def sinks(self) -> List[UsageEventSink]:
        """Bản sao danh sách đích ghi hiện tại (an toàn khi duyệt)."""
        with self._lock:
            return list(self._sinks)

    def emit(self, event: UsageEvent) -> None:
        """Đẩy sự kiện tới mọi đích.

        Một đích lỗi không được làm hỏng các đích còn lại — ghi số liệu là việc phụ,
        không được phép làm vỡ lượt chat đang chạy.
        """
        for sink in self.sinks():
            try:
                sink.emit(event)
            except Exception:  # noqa: BLE001 — one bad subscriber must not stop the rest
                logger.debug("usage sink: subscriber %r failed", sink, exc_info=True)


# --------------------------------------------------------------------------- #
# Process-wide sink.
#
# Providers publish through the module-level helpers below rather than holding a
# sink reference, because a provider instance is created fresh for every turn
# (see AppContext.build_provider_for) and would otherwise have to be handed the
# telemetry wiring on every construction.
# --------------------------------------------------------------------------- #
_sink_lock = threading.RLock()
_sink: Optional[CompositeUsageSink] = None


def get_usage_sink() -> CompositeUsageSink:
    """The shared sink, seeded with :class:`UsageTrackerSink` on first use."""
    global _sink
    if _sink is None:
        with _sink_lock:
            if _sink is None:
                _sink = CompositeUsageSink([UsageTrackerSink()])
    return _sink


def set_usage_sink(sink: Optional[CompositeUsageSink]) -> None:
    """Replace the shared sink (``None`` restores the default on next use).

    Used by tests and by the app shell when it wants a different fan-out; kept
    explicit so nothing silently reconfigures telemetry mid-run.
    """
    global _sink
    with _sink_lock:
        _sink = sink


def subscribe(sink: UsageEventSink) -> UsageEventSink:
    """Attach an extra subscriber to the shared sink and return it (so callers
    can keep the handle for a later :func:`unsubscribe`)."""
    get_usage_sink().add(sink)
    return sink


def unsubscribe(sink: UsageEventSink) -> None:
    """Detach a subscriber previously passed to :func:`subscribe`."""
    get_usage_sink().remove(sink)


def publish(event: UsageEvent) -> None:
    """Publish one usage event to every subscriber.

    Never raises: called from inside a provider's streaming loop, where an
    exception would abort an otherwise successful turn.
    """
    try:
        get_usage_sink().emit(event)
    except Exception:  # noqa: BLE001
        logger.debug("usage sink: publish failed", exc_info=True)


def estimate_tokens(text: str) -> int:
    """~4 chars per token approximation, re-exported so provider adapters need
    exactly ONE telemetry import instead of also importing the tracker."""
    return max(0, len(text or "") // 4)


__all__ = [
    "UsageEvent",
    "UsageEventSink",
    "UsageTrackerSink",
    "InMemoryUsageSink",
    "CompositeUsageSink",
    "get_usage_sink",
    "set_usage_sink",
    "subscribe",
    "unsubscribe",
    "publish",
    "estimate_tokens",
]
