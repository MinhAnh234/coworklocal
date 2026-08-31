"""R03-T06 — unit tests for the token-usage telemetry seam.

The seam exists so provider adapters stop owning telemetry policy. These tests
pin the two properties that makes that safe: events reach every subscriber, and
no telemetry failure can ever propagate back into the turn that produced it.
"""

from __future__ import annotations

import pytest
from cowork_local.infrastructure.telemetry import usage_sink
from cowork_local.infrastructure.telemetry.usage_sink import (
    CompositeUsageSink,
    InMemoryUsageSink,
    UsageEvent,
    UsageTrackerSink,
)


@pytest.fixture(autouse=True)
def isolated_sink(monkeypatch):
    """Give every test its own process-wide sink.

    Autouse because a leaked sink would let one test's subscriber observe the
    next test's events — and, worse, let a test write to the developer's real
    usage files through the default tracker sink.
    """
    monkeypatch.setattr(usage_sink, "_sink", None)
    yield
    monkeypatch.setattr(usage_sink, "_sink", None)


def make_event(**overrides) -> UsageEvent:
    fields = dict(provider="anthropic", model="claude-sonnet-4-6",
                  input_tokens=100, output_tokens=40, cached_tokens=10)
    fields.update(overrides)
    return UsageEvent(**fields)


# --------------------------------------------------------------------------- #
# UsageEvent
# --------------------------------------------------------------------------- #
def test_event_is_immutable() -> None:
    """A subscriber must not be able to edit the event the next one receives."""
    event = make_event()

    with pytest.raises(Exception):
        event.input_tokens = 0  # type: ignore[misc]


def test_total_tokens_does_not_double_count_cache_reads() -> None:
    """Every gateway we support already reports cached tokens inside the input
    count, so adding them again would inflate the dashboard."""
    assert make_event().total_tokens == 140


def test_to_dict_uses_the_stored_row_keys() -> None:
    """Matching the tracker's short keys lets a caller diff an event against a
    persisted row without a translation table."""
    row = make_event(source="cowork", label="Refactor chat").to_dict()

    assert row["in"] == 100 and row["out"] == 40 and row["cache"] == 10
    assert row["source"] == "cowork" and row["label"] == "Refactor chat"
    assert row["estimated"] is False


# --------------------------------------------------------------------------- #
# Fan-out
# --------------------------------------------------------------------------- #
def test_publish_reaches_every_subscriber() -> None:
    """The whole point of the seam: extra consumers attach without patching
    provider code."""
    first, second = InMemoryUsageSink(), InMemoryUsageSink()
    usage_sink.set_usage_sink(CompositeUsageSink([first, second]))

    usage_sink.publish(make_event())

    assert len(first.snapshot()) == 1
    assert len(second.snapshot()) == 1


def test_one_failing_subscriber_does_not_starve_the_others() -> None:
    """A buggy consumer must not silently disable the Dashboard."""
    class Exploding:
        def emit(self, event):
            raise RuntimeError("subscriber is broken")

    healthy = InMemoryUsageSink()
    usage_sink.set_usage_sink(CompositeUsageSink([Exploding(), healthy]))

    usage_sink.publish(make_event())

    assert len(healthy.snapshot()) == 1


def test_subscribe_and_unsubscribe_round_trip() -> None:
    """Teardown code calls unsubscribe unconditionally, so removing a sink that
    was never added must be harmless."""
    extra = InMemoryUsageSink()

    usage_sink.subscribe(extra)
    usage_sink.publish(make_event())
    usage_sink.unsubscribe(extra)
    usage_sink.unsubscribe(extra)          # second removal is a no-op
    usage_sink.publish(make_event(model="claude-opus-4-8"))

    assert [e.model for e in extra.snapshot()] == ["claude-sonnet-4-6"]


def test_default_sink_is_the_usage_tracker() -> None:
    """Out of the box the seam must preserve the existing Dashboard pipeline."""
    sinks = usage_sink.get_usage_sink().sinks()

    assert any(isinstance(s, UsageTrackerSink) for s in sinks)


def test_in_memory_sink_totals_and_clears() -> None:
    """Test-double conveniences the contract suite relies on."""
    sink = InMemoryUsageSink()
    sink.emit(make_event())
    sink.emit(make_event(input_tokens=1, output_tokens=1, cached_tokens=0))

    assert sink.total_tokens == 142
    sink.clear()
    assert sink.snapshot() == []


# --------------------------------------------------------------------------- #
# UsageTrackerSink forwarding
# --------------------------------------------------------------------------- #
def test_tracker_sink_forwards_the_counts() -> None:
    """The adapter must hand the tracker exactly what the provider measured."""
    recorded: list = []

    def fake_record(provider, model, tokens_in, tokens_out, cached, estimated=False):
        recorded.append((provider, model, tokens_in, tokens_out, cached, estimated))

    UsageTrackerSink(recorder=fake_record).emit(make_event(estimated=True))

    assert recorded == [("anthropic", "claude-sonnet-4-6", 100, 40, 10, True)]


def test_tracker_sink_restores_the_thread_context_it_borrowed() -> None:
    """An event carrying its own attribution must relabel ONE row, not every
    later turn that happens to run on the same worker thread."""
    from cowork_local.core import usage_tracker as tracker

    tracker.set_context("cowork", "original chat")
    seen: list = []
    UsageTrackerSink(recorder=lambda *a, **k: seen.append(tracker.current_context())).emit(
        make_event(source="co4e", label="flow run"))

    assert seen == [("co4e", "flow run")], "event attribution was not applied"
    assert tracker.current_context() == ("cowork", "original chat")


def test_tracker_sink_swallows_recorder_failures() -> None:
    """Telemetry is never allowed to abort an otherwise successful turn."""
    def boom(*_args, **_kwargs):
        raise OSError("usage directory is read-only")

    UsageTrackerSink(recorder=boom).emit(make_event())   # must not raise


def test_publish_never_raises_even_with_a_broken_sink() -> None:
    """Last line of defence: providers call publish() inside their stream loop."""
    class Hostile:
        def emit(self, event):
            raise RuntimeError("nope")

        def sinks(self):
            raise RuntimeError("nope")

    usage_sink.set_usage_sink(Hostile())

    usage_sink.publish(make_event())   # must not raise


def test_estimate_tokens_matches_the_tracker_heuristic() -> None:
    """Re-exported so adapters need one telemetry import; it must not drift."""
    from cowork_local.core import usage_tracker as tracker

    for text in ("", "a", "hello world", "x" * 4001):
        assert usage_sink.estimate_tokens(text) == tracker.estimate_tokens(text)
