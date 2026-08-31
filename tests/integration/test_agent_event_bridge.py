"""R04-T02 — the typed event vocabulary vs. what the real runtime emits.

The unit tests pin each event against the shape I *read* out of
``core/chat_agent.py``. This one removes the reading: it runs the actual
``run_cowork`` loop offline (FakeProvider, real tool execution, real cleanup)
and asserts every dict it emits is recognised by :func:`from_legacy_dict` and
survives a round trip byte-for-byte.

That makes it a guard against the two failure modes a hand-written vocabulary
has: an event type nobody modelled, and a key that silently changes meaning.
Either one would surface here as a failure instead of as a blank chat bubble
after R04-T03 starts routing events through the typed layer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pytest
from cowork_local.core import chat_agent
from cowork_local.domain.agents.agent_event_codec import from_legacy_dict
from cowork_local.tests.fakes.fake_provider import FakeProvider


def _run_turn_and_collect(tmp_path: Path, provider: FakeProvider) -> List[Dict[str, Any]]:
    """Run one real ``run_cowork`` turn offline and return every emitted dict."""
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    emitted: List[Dict[str, Any]] = []

    chat_agent.run_cowork(
        provider=provider,
        messages=[{"role": "user", "content": "make me a report"}],
        output_dir=output_dir,
        emit=emitted.append,
        # security_config=None disables the AI guardrail layers, which is the
        # documented behaviour for headless callers and keeps this test offline.
        security_config=None,
        title="Report",
    )
    return emitted


def _reporting_turn(tmp_path: Path) -> List[Dict[str, Any]]:
    """A turn that streams text, calls save_file, then answers — the common path."""
    provider = FakeProvider()
    provider.queue_response(
        content="Writing it now.",
        chunks=["Writing ", "it now."],
        tool_calls=[{"id": "call_1", "name": "save_file",
                     "arguments": {"filename": "report.md", "content": "# Report\n"}}],
    )
    provider.queue_response(content="Saved to report.md.", chunks=["Saved to report.md."])
    return _run_turn_and_collect(tmp_path, provider)


def test_the_runtime_emits_only_event_types_the_domain_layer_models(tmp_path: Path) -> None:
    emitted = _reporting_turn(tmp_path)

    unmodelled = sorted({e["type"] for e in emitted if from_legacy_dict(e) is None})

    assert unmodelled == [], f"run_cowork emits event types R04-T02 does not model: {unmodelled}"


def test_every_emitted_event_round_trips_without_losing_a_key(tmp_path: Path) -> None:
    emitted = _reporting_turn(tmp_path)
    assert emitted, "the turn produced no events at all — the fixture is wrong"

    for raw in emitted:
        event = from_legacy_dict(raw)
        assert event is not None, raw
        assert event.to_legacy_dict() == raw, f"round trip changed the {raw['type']} event"


def test_a_tool_using_turn_really_exercises_the_tool_events(tmp_path: Path) -> None:
    # Guards the test above from passing trivially: if the fixture ever stopped
    # calling a tool, the round-trip check would only cover text events.
    types = {e["type"] for e in _reporting_turn(tmp_path)}

    assert {"text", "assistant_done", "tool_proposed", "tool_result"} <= types


def test_reasoning_events_from_a_thinking_model_round_trip(tmp_path: Path) -> None:
    # A separate fixture because only reasoning models emit these, and the
    # common-path turn above would otherwise never cover the event.
    provider = FakeProvider()
    provider.queue_response(content="42", chunks=["42"], reasoning="Let me think...")

    emitted = _run_turn_and_collect(tmp_path, provider)

    reasoning_events = [e for e in emitted if e["type"] == "reasoning"]
    assert reasoning_events, "a reasoning model produced no reasoning event"
    for raw in reasoning_events:
        assert from_legacy_dict(raw).to_legacy_dict() == raw


def test_plan_events_from_the_real_update_plan_tool_round_trip(tmp_path: Path) -> None:
    provider = FakeProvider()
    provider.queue_response(
        content="Planning.",
        tool_calls=[{"id": "call_1", "name": "update_plan",
                     "arguments": {"steps": [{"title": "Draft", "status": "running"},
                                             {"title": "Review", "status": "pending"}]}}],
    )
    provider.queue_response(content="Done.")

    emitted = _run_turn_and_collect(tmp_path, provider)

    plan_events = [e for e in emitted if e["type"] == "plan_set"]
    assert plan_events, "update_plan did not produce a plan_set event"
    for raw in plan_events:
        assert from_legacy_dict(raw).to_legacy_dict() == raw
