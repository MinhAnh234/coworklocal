"""R04-T04 — unit tests for the shared turn-runtime helpers.

``combine_instructions`` is the small rule the UI applied inline: a turn's
standing instructions are several independent blocks (project context, an Admin
agent's persona, a skill's rules, an unattended-run reminder) that must be joined
with one blank line, skipping whatever is absent. Two call sites need it (T04's
widget and T05's task runner), which is exactly when a rule stops being an inline
expression.
"""

from __future__ import annotations

from cowork_local.application.conversations.turn_runtime import combine_instructions


def test_two_blocks_are_joined_by_a_blank_line() -> None:
    assert combine_instructions("PROJECT", "AGENT") == "PROJECT\n\nAGENT"


def test_an_absent_block_leaves_no_blank_line_behind() -> None:
    assert combine_instructions("", "AGENT") == "AGENT"
    assert combine_instructions("PROJECT", "") == "PROJECT"
    assert combine_instructions("PROJECT", None) == "PROJECT"


def test_whitespace_only_blocks_do_not_count_as_instructions() -> None:
    assert combine_instructions("   \n ", "AGENT") == "AGENT"


def test_nothing_to_say_produces_an_empty_string() -> None:
    assert combine_instructions() == ""
    assert combine_instructions("", None, "  ") == ""


def test_more_than_two_blocks_keep_their_order() -> None:
    assert combine_instructions("A", "B", "C") == "A\n\nB\n\nC"
