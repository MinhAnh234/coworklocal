"""R04-T05 — unit tests for the unattended-run prompt assembly.

``_run_agent`` used to build this by rebinding ``prompt`` three times, each with
its own ``f"{block}\n\n{prompt}"``. The ORDER that produced is load-bearing (the
plan reminder has to lead, the task's own words have to trail) and it was
readable only by replaying the rebindings in your head.
"""

from __future__ import annotations

from cowork_local.core.task_executors import _unattended_prompt


def test_the_plan_reminder_leads_and_the_task_prompt_trails() -> None:
    built = _unattended_prompt("write the report")

    assert built.startswith("This runs unattended (Schedule Task)")
    assert built.endswith("write the report")


def test_a_skill_block_sits_between_the_reminder_and_the_agent_persona() -> None:
    built = _unattended_prompt("write the report", skill_text="SKILL",
                               agent_instructions="PERSONA")

    assert built.index("This runs unattended") < built.index("SKILL")
    assert built.index("SKILL") < built.index("PERSONA")
    assert built.index("PERSONA") < built.index("write the report")


def test_absent_blocks_leave_no_extra_blank_lines() -> None:
    built = _unattended_prompt("do it", skill_text="", agent_instructions=None)

    assert "\n\n\n" not in built
    assert built.count("do it") == 1
