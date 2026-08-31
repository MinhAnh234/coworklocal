"""R04-T02 — unit tests for the typed agent event stream.

The events replace the untyped ``{"type": ...}`` dicts the runtime emits today,
but ``ui/chat_panel.py::_on_event`` still dispatches on those dicts until R08.
So the contract under test is two-sided: each event must be a real typed value
AND must serialise back to the exact legacy shape the widget already reads —
same wire name, same keys, same optional-key behaviour.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from cowork_local.domain.agents.agent_event import (
    AssistantMessageCompletedEvent,
    ErrorEvent,
    HistoryReadyEvent,
    NoticeEvent,
    OutputsAddedEvent,
    OutputsRemovedEvent,
    PlanStep,
    PlanUpdatedEvent,
    ReasoningChunkEvent,
    TextChunkEvent,
    ToolCallFinishedEvent,
    ToolCallStartedEvent,
    ToolOutputChunkEvent,
    ToolPreview,
    TurnCompletedEvent,
)
from cowork_local.domain.agents.agent_event_codec import from_legacy_dict


# -- base contract --------------------------------------------------------- #
def test_events_reject_mutation() -> None:
    event = TextChunkEvent(delta="hello")

    with pytest.raises(FrozenInstanceError):
        event.delta = "goodbye"


# -- legacy wire compatibility --------------------------------------------- #
def test_text_chunk_serialises_as_the_legacy_text_event() -> None:
    assert TextChunkEvent(delta="hi").to_legacy_dict() == {"type": "text", "delta": "hi"}


def test_reasoning_chunk_serialises_as_the_legacy_reasoning_event() -> None:
    assert ReasoningChunkEvent(delta="hmm").to_legacy_dict() == {
        "type": "reasoning", "delta": "hmm"}


def test_assistant_message_completed_serialises_as_assistant_done() -> None:
    # Fires once per provider call, so several times in a tool-using turn — it
    # is NOT the end of the turn (that is TurnCompletedEvent).
    assert AssistantMessageCompletedEvent(content="done").to_legacy_dict() == {
        "type": "assistant_done", "content": "done"}


def test_tool_call_started_serialises_with_the_legacy_id_and_args_keys() -> None:
    event = ToolCallStartedEvent(
        call_id="call_1", name="write_file", arguments={"path": "a.md"},
        preview=ToolPreview(kind="diff", title="Create file: a.md", text="+ hi"),
    )

    assert event.to_legacy_dict() == {
        "type": "tool_proposed",
        "id": "call_1",
        "name": "write_file",
        "args": {"path": "a.md"},
        "preview": {"kind": "diff", "title": "Create file: a.md", "text": "+ hi"},
    }


def test_tool_call_started_omits_the_preview_when_there_is_none() -> None:
    event = ToolCallStartedEvent(call_id="call_1", name="read_file")

    assert "preview" not in event.to_legacy_dict()


def test_tool_output_chunk_serialises_as_the_legacy_tool_output_event() -> None:
    event = ToolOutputChunkEvent(call_id="call_1", name="run_command", delta="line\n")

    assert event.to_legacy_dict() == {
        "type": "tool_output", "id": "call_1", "name": "run_command", "delta": "line\n"}


def test_tool_call_finished_serialises_as_the_legacy_tool_result_event() -> None:
    event = ToolCallFinishedEvent(
        call_id="call_1", name="save_file", ok=True, output="saved",
        path="C:/out/a.md", produced=["C:/out/b.pptx"],
    )

    assert event.to_legacy_dict() == {
        "type": "tool_result",
        "id": "call_1",
        "name": "save_file",
        "ok": True,
        "output": "saved",
        "path": "C:/out/a.md",
        "produced": ["C:/out/b.pptx"],
    }


def test_tool_call_finished_omits_path_and_produced_when_empty() -> None:
    # chat_agent only sets these keys when they exist; emitting them as None
    # would make ``ev.get("path")`` truthy checks read differently downstream.
    legacy = ToolCallFinishedEvent(call_id="c", name="read_file", ok=True).to_legacy_dict()

    assert "path" not in legacy
    assert "produced" not in legacy


def test_plan_updated_serialises_steps_back_to_title_status_dicts() -> None:
    event = PlanUpdatedEvent(steps=(PlanStep(title="Read config", status="done"),
                                    PlanStep(title="Patch it", status="running")))

    assert event.to_legacy_dict() == {
        "type": "plan_set",
        "steps": [{"title": "Read config", "status": "done"},
                  {"title": "Patch it", "status": "running"}],
    }


def test_notice_serialises_with_its_level() -> None:
    assert NoticeEvent(text="reading page 2/9", level="progress").to_legacy_dict() == {
        "type": "notice", "level": "progress", "text": "reading page 2/9"}


def test_notice_defaults_to_the_info_level() -> None:
    assert NoticeEvent(text="compacted").to_legacy_dict()["level"] == "info"


def test_outputs_added_and_removed_serialise_their_path_lists() -> None:
    assert OutputsAddedEvent(paths=("a.md",)).to_legacy_dict() == {
        "type": "outputs_added", "paths": ["a.md"]}
    assert OutputsRemovedEvent(paths=("tmp.py",)).to_legacy_dict() == {
        "type": "outputs_removed", "paths": ["tmp.py"]}


def test_history_ready_serialises_its_session_id() -> None:
    assert HistoryReadyEvent(session_id="s7").to_legacy_dict() == {
        "type": "history_ready", "session_id": "s7"}


# -- events introduced by R04 (no legacy consumer) ------------------------- #
def test_turn_completed_carries_the_final_answer_and_step_count() -> None:
    event = TurnCompletedEvent(final_text="all done", steps_used=3)

    assert event.to_legacy_dict() == {
        "type": "turn_completed", "final_text": "all done", "steps_used": 3,
        "cancelled": False, "budget_exhausted": False}


def test_error_event_is_fatal_unless_marked_recoverable() -> None:
    assert ErrorEvent(message="boom").recoverable is False
    assert ErrorEvent(message="rate limited", recoverable=True).recoverable is True


# -- parsing legacy dicts back into events --------------------------------- #
_ROUND_TRIP_CASES = [
    TextChunkEvent(delta="hi"),
    ReasoningChunkEvent(delta="hmm"),
    AssistantMessageCompletedEvent(content="done"),
    ToolCallStartedEvent(call_id="c", name="run_command", arguments={"command": "ls"},
                         preview=ToolPreview(kind="command", title="Run", text="ls")),
    ToolCallStartedEvent(call_id="c", name="read_file"),
    ToolOutputChunkEvent(call_id="c", name="run_command", delta="out"),
    ToolCallFinishedEvent(call_id="c", name="save_file", ok=True, output="ok",
                          path="a.md", produced=["b.md"]),
    ToolCallFinishedEvent(call_id="c", name="read_file", ok=False, output="missing"),
    PlanUpdatedEvent(steps=(PlanStep(title="Step", status="pending"),)),
    NoticeEvent(text="warned", level="warning"),
    OutputsAddedEvent(paths=("a.md",)),
    OutputsRemovedEvent(paths=("tmp.py",)),
    HistoryReadyEvent(session_id="s7"),
    TurnCompletedEvent(final_text="done", steps_used=2, cancelled=True),
    ErrorEvent(message="boom", recoverable=True),
]


@pytest.mark.parametrize("event", _ROUND_TRIP_CASES, ids=lambda e: type(e).__name__)
def test_every_event_survives_a_round_trip_through_the_legacy_dict(event) -> None:
    assert from_legacy_dict(event.to_legacy_dict()) == event


def test_unknown_event_types_parse_to_none_instead_of_raising() -> None:
    # Co4E emits its own vocabulary (node_status, stage_text, run_done) which R04
    # deliberately leaves alone; a bridge must be able to pass those through
    # untouched rather than crash on them.
    assert from_legacy_dict({"type": "node_status", "node_id": "n1"}) is None
    assert from_legacy_dict({"type": ""}) is None
    assert from_legacy_dict("not a dict") is None


def test_missing_payload_keys_parse_to_empty_values() -> None:
    # Defensive: a truncated event from an older emitter must not kill the turn.
    assert from_legacy_dict({"type": "text"}) == TextChunkEvent(delta="")
    assert from_legacy_dict({"type": "tool_result", "id": "c", "name": "x"}) == (
        ToolCallFinishedEvent(call_id="c", name="x", ok=False, output=""))


def test_plan_steps_from_legacy_drop_entries_without_a_title() -> None:
    # normalize_plan_steps already clamps upstream; this only guards the parse
    # path so a hand-written dict cannot produce a titleless step.
    event = from_legacy_dict({"type": "plan_set",
                              "steps": [{"title": "Real", "status": "done"}, {"status": "done"}]})

    assert event == PlanUpdatedEvent(steps=(PlanStep(title="Real", status="done"),))
