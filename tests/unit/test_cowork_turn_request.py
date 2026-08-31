"""R04-T04 — unit tests for the UI-state -> request mapping.

Three small rules used to sit inline in ``ui/cowork_tab.py::build_job``, where no
test could reach them: the turn's prompt is the last message in the working list,
the history is everything before it, and the confirm-commands flag becomes a gate
mode. Getting any of them wrong is silent (a duplicated user message, a command
that stops asking for approval), so they are pinned here.
"""

from __future__ import annotations

from pathlib import Path

from cowork_local.application.conversations.cowork_turn_request import (
    build_cowork_turn_request,
)


def _build(**overrides):
    base = {
        "turn_id": "t3",
        "session_id": "s1",
        "messages": [{"role": "user", "content": "make me a report"}],
    }
    base.update(overrides)
    return build_cowork_turn_request(**base)


def test_the_last_message_becomes_the_prompt_and_the_rest_the_history() -> None:
    request = _build(messages=[
        {"role": "user", "content": "earlier"},
        {"role": "assistant", "content": "sure"},
        {"role": "user", "content": "now this"},
    ])

    assert request.prompt == "now this"
    assert request.messages == ({"role": "user", "content": "earlier"},
                                {"role": "assistant", "content": "sure"})


def test_an_empty_working_list_yields_an_empty_prompt() -> None:
    # Defensive: a turn with no message at all must not raise on messages[-1].
    request = _build(messages=[])

    assert request.prompt == ""
    assert request.messages == ()


def test_confirming_commands_puts_the_turn_in_confirm_gate_mode() -> None:
    assert _build(confirm_commands=True).gate_mode == "confirm"
    assert _build(confirm_commands=False).gate_mode == "auto"
    assert _build().gate_mode == "auto"          # auto-run is the default


def test_the_captured_widget_state_is_carried_into_the_request() -> None:
    request = _build(
        surface="cowork", project_id="p7", title="Weekly report",
        provider_id="anthropic", model="claude-sonnet-4-6",
        instructions="PROJECT RULES", output_dir="out/.turns/t3",
        home_output_root="out", agent_role="cowork",
    )

    assert (request.turn_id, request.session_id) == ("t3", "s1")
    assert (request.surface, request.project_id, request.title) == \
           ("cowork", "p7", "Weekly report")
    assert (request.provider_id, request.model) == ("anthropic", "claude-sonnet-4-6")
    assert request.project_context == "PROJECT RULES"
    assert request.output_dir == Path("out/.turns/t3")
    assert request.home_output_root == Path("out")
    assert request.agent_role == "cowork"


def test_the_prompt_survives_a_message_whose_content_is_missing() -> None:
    request = _build(messages=[{"role": "user"}])

    assert request.prompt == ""
