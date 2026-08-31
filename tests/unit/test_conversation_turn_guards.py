"""R04-T03 (b) — the turn loop: guards, permission gate, compaction, cleanup.

Split out of ``test_conversation_application_service.py`` to keep each file
inside the 400-LOC limit. Same fakes, same service; this half pins the ORDER of
the safety steps (guard before model, guard before execute, gate before execute)
and the promise that the output sandbox is tidied on the way out.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest
from cowork_local.application.conversations.conversation_application_service import (
    ConversationApplicationService,
)
from cowork_local.domain.agents.agent_event import (
    ErrorEvent,
    OutputsAddedEvent,
    ReasoningChunkEvent,
    TextChunkEvent,
    ToolCallFinishedEvent,
)
from cowork_local.tests.fakes.turn_runtime_fakes import (
    FakeModelCall,
    FakeReply,
    FakeToolRuntime,
    events_of_type,
    make_request,
    run_turn,
    tool_turn,
)


def _service(model, tools, **overrides) -> ConversationApplicationService:
    return ConversationApplicationService(model, tools, **overrides)


# --------------------------------------------------------------------------- #
# Guards and the permission gate.
# --------------------------------------------------------------------------- #
def test_the_prompt_guard_runs_before_the_model_is_ever_called() -> None:
    order: List[str] = []
    model = FakeModelCall([FakeReply(content="ok")])
    model_call = model.call

    def call(*a, **kw):
        order.append("model")
        return model_call(*a, **kw)

    model.call = call

    run_turn(_service(model, FakeToolRuntime(), prompt_guard=lambda messages: order.append("guard")))

    assert order == ["guard", "model"]


def test_a_blocked_prompt_propagates_before_the_output_folder_is_touched() -> None:
    model = FakeModelCall([FakeReply(content="never")])
    tools = FakeToolRuntime()
    events: List[Any] = []

    def guard(messages) -> None:
        raise RuntimeError("SecurityBlocked: nope")

    service = _service(model, tools, prompt_guard=guard)

    with pytest.raises(RuntimeError, match="SecurityBlocked"):
        service.execute(make_request(), events.append)

    assert model.calls == []
    assert events_of_type(events, ErrorEvent) == [ErrorEvent(message="SecurityBlocked: nope")]
    # Cleanup is NOT a read-only operation (it deletes a stale .scratch and every
    # empty sub-folder), so a turn rejected before it started must not run it.
    assert tools.finalize_calls == []


def test_output_cleanup_still_runs_when_the_turn_fails_mid_loop() -> None:
    # Once the turn has started producing files, the sandbox must be tidied on
    # the way out no matter how the turn ends.
    model = FakeModelCall([RuntimeError("gateway exploded")])
    tools = FakeToolRuntime()
    events: List[Any] = []

    with pytest.raises(RuntimeError, match="gateway exploded"):
        _service(model, tools).execute(make_request(), events.append)

    assert tools.finalize_calls == [{"before": "before", "cancelled": False}]
    assert events_of_type(events, ErrorEvent) == [ErrorEvent(message="gateway exploded")]


def test_the_command_guard_runs_before_the_tool_executes() -> None:
    order: List[str] = []
    model, tools = tool_turn("run_command", {"command": "ls"})
    original = tools.execute

    def execute(name, args, on_output=None, cancel=None):
        order.append("execute")
        return original(name, args, on_output=on_output, cancel=cancel)

    tools.execute = execute

    run_turn(_service(model, tools,
                  command_guard=lambda name, args: order.append(f"guard:{name}")))

    assert order == ["guard:run_command", "execute"]


def test_disabling_rule_enforcement_skips_both_guards() -> None:
    # Co4E flow steps run inside the workspace sandbox and opt out on purpose.
    calls: List[str] = []
    model, tools = tool_turn("run_command", {"command": "ls"})

    run_turn(_service(model, tools,
                  prompt_guard=lambda messages: calls.append("prompt"),
                  command_guard=lambda name, args: calls.append("command")),
         make_request(enforce_rules=False))

    assert calls == []


def test_the_permission_gate_is_asked_only_for_command_tools() -> None:
    asked: List[str] = []
    model, tools = tool_turn("save_file", {"filename": "a.md"})

    run_turn(_service(model, tools,
                  permission_request=lambda action: asked.append(action["name"]) or True),
         make_request(gate_mode="confirm"))

    assert asked == []          # save_file writes into the sandbox: never gated


def test_a_command_tool_in_confirm_mode_asks_before_running() -> None:
    asked: List[Dict[str, Any]] = []
    model, tools = tool_turn("run_command", {"command": "ls"})

    def approve(action: Dict[str, Any]) -> bool:
        asked.append(action)
        return True

    run_turn(_service(model, tools, permission_request=approve), make_request(gate_mode="confirm"))

    assert [a["name"] for a in asked] == ["run_command"]
    assert tools.executed == [("run_command", {"command": "ls"})]


def test_a_rejected_command_is_reported_as_a_failed_tool_and_never_runs() -> None:
    model, tools = tool_turn("run_command", {"command": "rm -rf /"})

    result, events = run_turn(_service(model, tools, permission_request=lambda action: False),
                          make_request(gate_mode="confirm"))

    assert tools.executed == []
    assert events_of_type(events, ToolCallFinishedEvent) == [ToolCallFinishedEvent(
        call_id="c1", name="run_command", ok=False, output="Rejected by user.")]
    assert result.messages[-2]["content"] == "Rejected by user."


def test_auto_mode_never_asks_even_for_a_command() -> None:
    model, tools = tool_turn("run_command", {"command": "ls"})

    def refuse(action):     # would block the turn if it were consulted
        raise AssertionError("the gate must not be consulted in auto mode")

    run_turn(_service(model, tools, permission_request=refuse), make_request(gate_mode="auto"))

    assert tools.executed == [("run_command", {"command": "ls"})]


# --------------------------------------------------------------------------- #
# Context compaction, reasoning, output cleanup.
# --------------------------------------------------------------------------- #
def test_the_conversation_is_offered_for_compaction_before_every_call() -> None:
    compactions: List[int] = []
    model, tools = tool_turn()

    run_turn(_service(model, tools,
                     compact=lambda messages, cancel: compactions.append(len(messages))))

    assert len(compactions) == 2      # once per provider call


def test_reasoning_is_streamed_as_its_own_event() -> None:
    model = FakeModelCall([FakeReply(content="42", reasoning="thinking...")])

    _, events = run_turn(_service(model, FakeToolRuntime()))

    assert events_of_type(events, ReasoningChunkEvent) == [ReasoningChunkEvent(delta="thinking...")]


def test_a_reasoning_only_reply_gets_a_visible_note_in_the_transcript() -> None:
    # Otherwise a Schedule Task run reads back an empty answer and writes
    # "(no output)" into its report.
    model = FakeModelCall([FakeReply(content="", reasoning="thought hard")])

    result, events = run_turn(_service(model, FakeToolRuntime()))

    assert "only its reasoning" in events_of_type(events, TextChunkEvent)[-1].delta
    assert "only its reasoning" in result.final_text


def test_promoted_and_discarded_output_files_are_reported_at_the_end() -> None:
    model = FakeModelCall([FakeReply(content="ok")])
    tools = FakeToolRuntime(added=("out/report.pptx",))

    _, events = run_turn(_service(model, tools))

    assert events_of_type(events, OutputsAddedEvent) == [
        OutputsAddedEvent(paths=("out/report.pptx",))]
    assert tools.finalize_calls == [{"before": "before", "cancelled": False}]
