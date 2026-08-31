"""R04-T01 — unit tests for the immutable turn snapshot.

The snapshot exists so a turn already running cannot be altered by the UI the
user keeps clicking on. These tests pin exactly that: the object refuses
mutation, it copies the mutable collections handed to it at submit time, and it
owns the prompt-composition rules that were inline in
``ui/chat_panel.py::_start_turn``'s worker closure (prefix separator, session
notes, model-switch review note).
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from cowork_local.domain.agents.conversation_execution_request import (
    ConversationExecutionRequest,
)


def _request(**overrides) -> ConversationExecutionRequest:
    """A minimal valid request; each test overrides only what it exercises."""
    base = {"turn_id": "t1", "session_id": "s1"}
    base.update(overrides)
    return ConversationExecutionRequest(**base)


# -- immutability ---------------------------------------------------------- #
def test_request_rejects_mutation_after_construction() -> None:
    request = _request(model="gpt-4o-mini")

    with pytest.raises(FrozenInstanceError):
        request.model = "claude-sonnet-4-6"


def test_turn_id_is_required() -> None:
    with pytest.raises(ValueError):
        ConversationExecutionRequest(turn_id="", session_id="s1")


def test_session_id_is_required() -> None:
    with pytest.raises(ValueError):
        ConversationExecutionRequest(turn_id="t1", session_id="")


# -- snapshotting mutable UI state ---------------------------------------- #
def test_attachments_are_snapshotted_away_from_the_caller_list() -> None:
    picked = ["a.docx"]

    request = _request(attachments=picked)
    picked.append("b.pdf")   # the composer clears/refills its own list next turn

    assert request.attachments == ("a.docx",)


def test_messages_are_snapshotted_away_from_the_live_history_list() -> None:
    history = [{"role": "user", "content": "earlier"}]

    request = _request(messages=history)
    history.append({"role": "assistant", "content": "later"})

    assert len(request.messages) == 1
    assert isinstance(request.messages, tuple)


def test_allowed_tools_none_means_every_tool_stays_available() -> None:
    # None and () must stay distinguishable: None = no restriction, () = deny
    # every built-in tool. Coercing None to () would silently disarm the agent.
    assert _request().allowed_tools is None
    assert _request(allowed_tools=[]).allowed_tools == ()


def test_output_paths_accept_strings_and_normalise_to_path() -> None:
    request = _request(output_dir="out/t1", home_output_root="out")

    assert request.output_dir == Path("out/t1")
    assert request.home_output_root == Path("out")


# -- derived turn policy --------------------------------------------------- #
def test_effective_max_steps_uses_the_interactive_cap_by_default() -> None:
    assert _request(max_steps=30, completion_max_steps=200).effective_max_steps == 30


def test_effective_max_steps_lifts_the_cap_when_running_to_completion() -> None:
    request = _request(max_steps=30, completion_max_steps=200, run_to_completion=True)

    assert request.effective_max_steps == 200


def test_permission_gate_is_required_only_in_confirm_mode() -> None:
    assert _request(gate_mode="confirm").requires_permission_gate is True
    assert _request(gate_mode="auto").requires_permission_gate is False


def test_has_prompt_ignores_whitespace_only_input() -> None:
    assert _request(prompt="   \n ").has_prompt is False
    assert _request(prompt="do it").has_prompt is True


# -- prompt composition (moved out of the widget's worker closure) --------- #
def test_user_content_returns_the_body_unchanged_without_prefix_or_notes() -> None:
    assert _request().user_content("the body") == "the body"


def test_user_content_separates_the_instruction_prefix_from_the_body() -> None:
    request = _request(instruction_prefix="SKILL RULES")

    assert request.user_content("the body") == "SKILL RULES\n\n---\n\nthe body"


def test_user_content_appends_session_notes_after_the_body() -> None:
    request = _request(session_notes="Files produced earlier: a.md")

    assert request.user_content("the body") == "the body\n\nFiles produced earlier: a.md"


def test_user_content_falls_back_to_session_notes_when_the_body_is_empty() -> None:
    # An attachment-only turn has no typed text, so the notes must not be
    # prefixed with a stray blank line.
    request = _request(session_notes="Files produced earlier: a.md")

    assert request.user_content("") == "Files produced earlier: a.md"


def test_user_content_puts_the_review_note_ahead_of_everything_else() -> None:
    request = _request(instruction_prefix="SKILL RULES", review_note="[Note: switched]")

    content = request.user_content("the body")

    assert content == "[Note: switched]\n\nSKILL RULES\n\n---\n\nthe body"
