"""R04-T05 — the Schedule Task runner's cowork branch, pinned before and after.

Written against the CURRENT ``_run_agent`` first, as the safety net for moving it
onto ``ConversationApplicationService``: an unattended run has five behaviours the
interactive path does not have (the plan reminder prefixed to the prompt, the
session registered in History before the model starts, a re-save after every
assistant message, the timeout notice, and the "did the agent's own checklist
finish?" report), and none of them was covered by a test.

Everything is isolated from the user's real config: history goes to ``tmp_path``
via ``history.custom_dir`` and the AI guardrails are off, so no run touches
``~/.cowork_local`` or calls a model to review a prompt.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from cowork_local.config import DEFAULT_CONFIG, AppConfig
from cowork_local.core import task_executors
from cowork_local.tests.fakes.fake_provider import FakeProvider


class _FakeCtx:
    """The ``AppContext`` surface ``_run_agent`` touches."""

    def __init__(self, config: AppConfig, provider: FakeProvider) -> None:
        self.config = config
        self._provider = provider

    def build_active_provider(self) -> FakeProvider:
        return self._provider

    def build_provider_for(self, name=None, model=None) -> FakeProvider:
        return self._provider


def _config(tmp_path: Path) -> AppConfig:
    data = copy.deepcopy(DEFAULT_CONFIG)
    # Keep the run entirely offline and off the real config dir.
    data["agent_security"]["enabled"] = False
    data["history"]["custom_dir"] = str(tmp_path / "history")
    return AppConfig(data)


def _run(tmp_path: Path, provider: FakeProvider, *, prompt: str = "write the report",
         timeout_sec: Optional[int] = None, admin_agent: Any = None):
    """Run one cowork task and return ``(result_tuple, events, config)``."""
    out_dir = tmp_path / "run"
    out_dir.mkdir(parents=True, exist_ok=True)
    config = _config(tmp_path)
    events: List[Dict[str, Any]] = []

    result = task_executors._run_agent(
        _FakeCtx(config, provider), "cowork", prompt, out_dir,
        events.append, lambda: False, title="Weekly report",
        timeout_sec=timeout_sec, admin_agent=admin_agent,
    )
    return result, events, config


def _saved_conversation(config: AppConfig) -> Dict[str, Any]:
    """The single conversation the run wrote into the isolated history folder."""
    files = list(Path(config.history_dir()).rglob("*.json"))
    assert len(files) == 1, f"expected one saved conversation, found {files}"
    return json.loads(files[0].read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
def test_a_cowork_task_returns_the_final_answer(tmp_path: Path) -> None:
    provider = FakeProvider()
    provider.queue_response(content="Report is ready.")

    (answer, timed_out, incomplete), _events, _config = _run(tmp_path, provider)

    assert answer == "Report is ready."
    assert timed_out is False
    assert incomplete == ""


def test_the_plan_reminder_is_prefixed_to_the_prompt(tmp_path: Path) -> None:
    # An unattended run has nobody watching, so the agent is pushed to keep its
    # own checklist honest. The reminder must lead the message.
    provider = FakeProvider()
    provider.queue_response(content="ok")

    _run(tmp_path, provider, prompt="write the report")

    sent = provider.call_history[0][-1]["content"]
    assert sent.startswith("This runs unattended (Schedule Task)")
    assert sent.endswith("write the report")


def test_an_admin_agent_persona_sits_between_the_reminder_and_the_prompt(
        tmp_path: Path) -> None:
    class _Agent:
        # An admin agent may pin its own provider/model; blank means "use the
        # machine's Settings default", which is what build_agent_provider reads.
        provider = ""
        model = ""

        def effective_prompt(self) -> str:
            return "You are the reporting agent."

    provider = FakeProvider()
    provider.queue_response(content="ok")

    _run(tmp_path, provider, prompt="write the report", admin_agent=_Agent())

    sent = provider.call_history[0][-1]["content"]
    assert sent.index("This runs unattended") < sent.index("You are the reporting agent.")
    assert sent.index("You are the reporting agent.") < sent.index("write the report")


def test_the_session_is_announced_once_it_exists_on_disk(tmp_path: Path) -> None:
    # The scheduler refreshes History on this event, so it must not fire before
    # the conversation is really there.
    provider = FakeProvider()
    provider.queue_response(content="ok")

    _result, events, config = _run(tmp_path, provider)

    ready = [e for e in events if e["type"] == "history_ready"]
    assert len(ready) == 1
    assert ready[0]["session_id"]
    assert _saved_conversation(config)["session_id"] == ready[0]["session_id"]


def test_the_saved_conversation_carries_the_answer_and_the_task_title(
        tmp_path: Path) -> None:
    provider = FakeProvider()
    provider.queue_response(content="Report is ready.")

    _result, _events, config = _run(tmp_path, provider)

    saved = _saved_conversation(config)
    assert saved["title"] == "[Task] Weekly report"
    assert saved["messages"][-1] == {"role": "assistant", "content": "Report is ready."}


def test_an_unfinished_checklist_is_reported_back_to_the_scheduler(
        tmp_path: Path) -> None:
    # The agent ticked no step to done, so the task must not be called finished
    # just because no exception was raised.
    provider = FakeProvider()
    provider.queue_response(
        content="Working on it.",
        tool_calls=[{"id": "c1", "name": "update_plan",
                     "arguments": {"steps": [{"title": "Draft", "status": "running"}]}}],
    )
    provider.queue_response(content="Stopping here.")

    (_answer, _timed_out, incomplete), _events, _config = _run(tmp_path, provider)

    assert incomplete
    assert "Draft" in incomplete


def test_a_finished_checklist_reports_nothing_outstanding(tmp_path: Path) -> None:
    provider = FakeProvider()
    provider.queue_response(
        content="Done.",
        tool_calls=[{"id": "c1", "name": "update_plan",
                     "arguments": {"steps": [{"title": "Draft", "status": "done"}]}}],
    )
    provider.queue_response(content="All done.")

    (_answer, _timed_out, incomplete), _events, _config = _run(tmp_path, provider)

    assert incomplete == ""


def test_running_out_of_time_appends_the_timeout_notice_to_the_conversation(
        tmp_path: Path) -> None:
    # A negative timeout puts the deadline in the past, which is the only
    # deterministic way to exercise a wall-clock branch in a unit test.
    provider = FakeProvider()
    provider.queue_response(content="never gets there")

    (answer, timed_out, incomplete), events, config = _run(
        tmp_path, provider, timeout_sec=-1)

    assert timed_out is True
    assert incomplete == ""          # a timeout is not an unfinished checklist
    assert "quá thời gian chờ" in answer
    assert any(e["type"] == "assistant_done" and "quá thời gian chờ" in e["content"]
               for e in events)
    assert "quá thời gian chờ" in _saved_conversation(config)["messages"][-1]["content"]
