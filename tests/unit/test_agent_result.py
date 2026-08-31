"""R04-T03 (a) — unit tests for the value a finished turn returns.

Two callers need different things out of one turn today:
``ui/chat_panel.py::_finalize_turn`` wants the message list, while
``core/task_executors.py::_run_agent`` returns a
``(answer_text, timed_out, incomplete_reason)`` tuple assembled by hand. This
type is what both read instead, so "what happened in that turn?" has one answer
with names on it.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from cowork_local.domain.agents.agent_event import PlanStep, TurnCompletedEvent
from cowork_local.domain.agents.agent_result import AgentResult


def test_result_rejects_mutation() -> None:
    result = AgentResult(steps_used=1)

    with pytest.raises(FrozenInstanceError):
        result.steps_used = 2


def test_messages_are_frozen_into_a_tuple() -> None:
    live = [{"role": "user", "content": "hi"}]

    result = AgentResult(messages=live)
    live.append({"role": "assistant", "content": "later"})

    assert result.messages == ({"role": "user", "content": "hi"},)


def test_final_text_is_the_last_non_empty_assistant_message() -> None:
    # A turn ends on a tool message often enough (cancelled mid-loop) that the
    # answer cannot simply be messages[-1].
    result = AgentResult(messages=[
        {"role": "assistant", "content": "first pass"},
        {"role": "assistant", "content": "the answer"},
        {"role": "tool", "tool_call_id": "c", "name": "read_file", "content": "..."},
    ])

    assert result.final_text == "the answer"


def test_final_text_skips_a_blank_assistant_message() -> None:
    result = AgentResult(messages=[
        {"role": "assistant", "content": "the answer"},
        {"role": "assistant", "content": "   "},
    ])

    assert result.final_text == "the answer"


def test_final_text_is_empty_when_the_model_never_answered() -> None:
    assert AgentResult(messages=[{"role": "user", "content": "hi"}]).final_text == ""


def test_a_plain_finished_turn_is_ok() -> None:
    assert AgentResult(messages=[{"role": "assistant", "content": "done"}]).ok is True


def test_a_cancelled_turn_is_not_ok() -> None:
    assert AgentResult(cancelled=True).ok is False


def test_a_failed_turn_is_not_ok_and_keeps_its_message() -> None:
    result = AgentResult(error="SecurityBlocked: nope")

    assert result.ok is False
    assert result.error == "SecurityBlocked: nope"


def test_hitting_the_step_ceiling_is_reported_separately_from_cancelling() -> None:
    # "Stopped because the safety limit was reached" and "the user pressed Stop"
    # need different wording in the transcript, so they stay separate flags.
    result = AgentResult(budget_exhausted=True, steps_used=30)

    assert result.budget_exhausted is True
    assert result.cancelled is False


def test_result_converts_to_the_turn_completed_event() -> None:
    result = AgentResult(
        messages=[{"role": "assistant", "content": "done"}],
        steps_used=3, cancelled=False, budget_exhausted=True,
    )

    assert result.to_turn_completed_event() == TurnCompletedEvent(
        final_text="done", steps_used=3, cancelled=False, budget_exhausted=True)


def test_plan_steps_are_frozen_into_a_tuple() -> None:
    steps = [PlanStep(title="Draft", status="done")]

    result = AgentResult(plan_steps=steps)
    steps.append(PlanStep(title="Review"))

    assert result.plan_steps == (PlanStep(title="Draft", status="done"),)
