"""R04-T03 (b) — the turn loop: composition, tool dispatch, budget, cancel.

Behaviour that used to be reachable only by running the real widget. Every
dependency is a fake from ``tests/fakes/turn_runtime_fakes.py``, so the file
runs in milliseconds and each test states one rule of the loop.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from cowork_local.application.conversations.conversation_application_service import (
    ConversationApplicationService,
)
from cowork_local.domain.agents.agent_event import (
    AssistantMessageCompletedEvent,
    PlanStep,
    PlanUpdatedEvent,
    TextChunkEvent,
    ToolCallFinishedEvent,
    ToolCallStartedEvent,
    ToolOutputChunkEvent,
    ToolPreview,
    TurnCompletedEvent,
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
# The happy path.
# --------------------------------------------------------------------------- #
def test_a_plain_answer_streams_text_then_reports_the_message_and_the_turn() -> None:
    model = FakeModelCall([FakeReply(content="Hello there", chunks=["Hello ", "there"])])

    result, events = run_turn(_service(model, FakeToolRuntime()))

    assert [e.delta for e in events_of_type(events, TextChunkEvent)] == ["Hello ", "there"]
    assert events_of_type(events, AssistantMessageCompletedEvent) == [
        AssistantMessageCompletedEvent(content="Hello there")]
    assert events_of_type(events, TurnCompletedEvent) == [
        TurnCompletedEvent(final_text="Hello there", steps_used=1)]
    assert result.final_text == "Hello there"
    assert result.ok is True


def test_the_composed_user_message_is_appended_before_the_first_call() -> None:
    model = FakeModelCall([FakeReply(content="ok")])
    request = make_request(prompt="ship it", instruction_prefix="RULES",
                       session_notes="earlier: a.md",
                       messages=[{"role": "user", "content": "previous"}])

    run_turn(_service(model, FakeToolRuntime()), request)

    sent = model.calls[0]["messages"]
    assert sent[-1] == {"role": "user",
                        "content": "RULES\n\n---\n\nship it\n\nearlier: a.md"}
    assert sent[-2] == {"role": "user", "content": "previous"}


def test_attachments_are_read_when_the_turn_runs_not_when_it_was_built() -> None:
    # Extraction can pip-install a parser or shell out to LibreOffice, so it must
    # happen here (worker thread), not while the UI was assembling the request.
    seen: List[Tuple[str, Tuple[str, ...]]] = []

    def reader(prompt: str, attachments: Tuple[str, ...]) -> str:
        seen.append((prompt, attachments))
        return f"{prompt}\n\n<contents of {len(attachments)} file(s)>"

    model = FakeModelCall([FakeReply(content="ok")])
    request = make_request(prompt="summarise", attachments=["a.docx", "b.pdf"])

    run_turn(_service(model, FakeToolRuntime(), attachment_reader=reader), request)

    assert seen == [("summarise", ("a.docx", "b.pdf"))]
    assert "contents of 2 file(s)" in model.calls[0]["messages"][-1]["content"]


def test_the_prompt_preparer_is_told_which_tools_the_turn_advertises() -> None:
    # The system prompt gains an MS365 paragraph only when ms365__* tools are
    # present, so the preparer has to see the real list.
    seen: List[Tuple[str, ...]] = []
    model = FakeModelCall([FakeReply(content="ok")])
    tools = FakeToolRuntime(specs=("save_file", "ms365__send_mail"))

    run_turn(_service(model, tools,
                  prepare_prompt=lambda messages, names: seen.append(names)))

    assert seen == [("save_file", "ms365__send_mail")]


def test_only_the_allowed_tools_are_advertised() -> None:
    model = FakeModelCall([FakeReply(content="ok")])
    tools = FakeToolRuntime(specs=("save_file", "run_command", "update_plan"))

    run_turn(_service(model, tools), make_request(allowed_tools=("save_file", "update_plan")))

    assert model.calls[0]["tool_names"] == ["save_file", "update_plan"]


# --------------------------------------------------------------------------- #
# Tool dispatch.
# --------------------------------------------------------------------------- #
def tool_turn(tool_name: str = "save_file", args=None, **tool_kwargs):
    """A turn that calls one tool, then answers."""
    calls = [{"id": "c1", "name": tool_name, "arguments": args or {"filename": "a.md"}}]
    model = FakeModelCall([FakeReply(content="working", tool_calls=calls),
                        FakeReply(content="done")])
    return model, FakeToolRuntime(**tool_kwargs)


def test_a_tool_call_is_announced_executed_and_answered_in_the_message_list() -> None:
    model, tools = tool_turn(results={"save_file": {"ok": True, "output": "saved",
                                                     "path": "out/a.md"}})

    result, events = run_turn(_service(model, tools))

    assert events_of_type(events, ToolCallStartedEvent) == [ToolCallStartedEvent(
        call_id="c1", name="save_file", arguments={"filename": "a.md"},
        preview=ToolPreview(kind="info", title="save_file", text="{'filename': 'a.md'}"))]
    assert events_of_type(events, ToolCallFinishedEvent) == [ToolCallFinishedEvent(
        call_id="c1", name="save_file", ok=True, output="saved", path="out/a.md")]
    assert tools.executed == [("save_file", {"filename": "a.md"})]
    assert result.messages[-2] == {"role": "tool", "tool_call_id": "c1",
                                   "name": "save_file", "content": "saved"}


def test_live_tool_output_is_streamed_while_the_tool_runs() -> None:
    model, tools = tool_turn("run_command", {"command": "ls"})
    tools.emit_output = "file-a\n"

    _, events = run_turn(_service(model, tools))

    assert events_of_type(events, ToolOutputChunkEvent) == [ToolOutputChunkEvent(
        call_id="c1", name="run_command", delta="file-a\n")]


def test_the_loop_ends_as_soon_as_the_model_stops_calling_tools() -> None:
    model, tools = tool_turn()

    result, _ = run_turn(_service(model, tools))

    assert result.steps_used == 2
    assert result.budget_exhausted is False


def test_the_plan_tool_reports_a_plan_update_and_no_tool_bubble() -> None:
    calls = [{"id": "c1", "name": "update_plan",
              "arguments": {"steps": [{"title": "Draft", "status": "running"}]}}]
    model = FakeModelCall([FakeReply(content="planning", tool_calls=calls), FakeReply(content="done")])
    tools = FakeToolRuntime(results={"update_plan": {
        "ok": True, "output": "Plan updated.",
        "plan_steps": [PlanStep(title="Draft", status="running")]}})

    result, events = run_turn(_service(model, tools))

    assert events_of_type(events, PlanUpdatedEvent) == [
        PlanUpdatedEvent(steps=(PlanStep(title="Draft", status="running"),))]
    assert events_of_type(events, ToolCallStartedEvent) == []
    assert events_of_type(events, ToolCallFinishedEvent) == []
    assert result.plan_steps == (PlanStep(title="Draft", status="running"),)


# --------------------------------------------------------------------------- #
# Budget, cancellation.
# --------------------------------------------------------------------------- #
def test_running_out_of_steps_is_flagged_and_announced() -> None:
    # The model keeps calling tools forever; the ceiling must stop it visibly.
    forever = [FakeReply(content=f"step {i}",
                      tool_calls=[{"id": f"c{i}", "name": "save_file", "arguments": {}}])
               for i in range(5)]
    model = FakeModelCall(forever)

    result, events = run_turn(_service(model, FakeToolRuntime()), make_request(max_steps=2))

    assert result.steps_used == 2
    assert result.budget_exhausted is True
    assert "2-step safety limit" in events_of_type(events, TextChunkEvent)[-1].delta
    # The note reaches the transcript but NOT the stored answer: a turn that hits
    # the ceiling always ends on a tool message, and the existing runtime only
    # merges the note when the last message is the assistant's. Pinned here so a
    # future change to that rule is a deliberate decision, not a silent drift.
    assert result.final_text == "step 1"


def test_run_to_completion_uses_the_higher_ceiling() -> None:
    forever = [FakeReply(content="x", tool_calls=[{"id": "c", "name": "save_file", "arguments": {}}])
               for _ in range(6)]
    model = FakeModelCall(forever)

    result, _ = run_turn(_service(model, FakeToolRuntime()),
                     make_request(max_steps=2, completion_max_steps=5, run_to_completion=True))

    assert result.steps_used == 5


def test_a_turn_cancelled_before_it_starts_never_calls_the_model() -> None:
    model = FakeModelCall([FakeReply(content="never")])

    result, events = run_turn(_service(model, FakeToolRuntime()), cancel=lambda: True)

    assert model.calls == []
    assert result.cancelled is True
    assert result.budget_exhausted is False
    assert events_of_type(events, TurnCompletedEvent) == [TurnCompletedEvent(cancelled=True)]


def test_cancelling_during_a_turn_stops_dispatching_the_remaining_tool_calls() -> None:
    calls = [{"id": "c1", "name": "save_file", "arguments": {}},
             {"id": "c2", "name": "save_file", "arguments": {}}]
    model = FakeModelCall([FakeReply(content="two tools", tool_calls=calls)])
    tools = FakeToolRuntime()
    stop = {"now": False}

    def cancel() -> bool:
        return stop["now"]

    original_execute = tools.execute

    def execute(name, args, on_output=None, cancel=None):
        stop["now"] = True            # cancel raised while the first tool runs
        return original_execute(name, args, on_output=on_output, cancel=cancel)

    tools.execute = execute

    result, _ = run_turn(_service(model, tools), cancel=cancel)

    assert len(tools.executed) == 1
    assert result.cancelled is True


# --------------------------------------------------------------------------- #
# Bring-your-own working list.
#
# ``ui/chat_panel.py`` holds the turn's message list in its own turn context and
# reads it WHILE the worker appends (``_reattach_running_turn`` replays the steps
# done so far when the user reopens a running conversation; ``_finalize_turn``
# slices it by ``snapshot_len``). A service that built its own private list would
# silently break both, so a caller can hand its list over instead.
# --------------------------------------------------------------------------- #
def test_a_caller_supplied_list_is_appended_to_in_place() -> None:
    model, tools = tool_turn()
    live: List[Dict[str, Any]] = [{"role": "user", "content": "already composed"}]

    result = ConversationApplicationService(model, tools).execute(
        make_request(), lambda event: None, messages=live)

    roles = [m["role"] for m in live]
    assert roles == ["user", "assistant", "tool", "assistant"]
    assert result.messages == tuple(live)


def test_a_caller_supplied_list_is_used_as_is_without_recomposing_the_prompt() -> None:
    # The widget already applied the skill prefix and the session notes when it
    # built its message; composing again would duplicate them.
    model = FakeModelCall([FakeReply(content="ok")])
    user = {"role": "user", "content": "already composed"}
    live = [user]

    ConversationApplicationService(model, FakeToolRuntime()).execute(
        make_request(prompt="typed text", instruction_prefix="RULES",
                     session_notes="notes"),
        lambda event: None, messages=live)

    assert live[0] is user
    assert live[0]["content"] == "already composed"
    assert [m["role"] for m in live].count("user") == 1


def test_a_caller_supplied_list_skips_the_attachment_reader() -> None:
    # Reading the attachments is what produced the caller's message in the first
    # place; doing it again would re-parse every file.
    model = FakeModelCall([FakeReply(content="ok")])
    calls: List[Any] = []

    ConversationApplicationService(
        model, FakeToolRuntime(),
        attachment_reader=lambda prompt, attachments: calls.append(prompt) or prompt,
    ).execute(make_request(attachments=["a.docx"]), lambda event: None,
              messages=[{"role": "user", "content": "composed"}])

    assert calls == []
