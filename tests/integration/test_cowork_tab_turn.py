"""R04-T04 — the migrated Cowork call site, exercised end to end without Qt.

``CoworkTab.build_job`` only ever *reads attributes* off its widget, so the real
production method can be invoked against a stand-in that supplies those
attributes. That is what happens here: the actual ``build_job`` body runs, builds
a request, wires the service through ``core_runtime_adapter``, and drives a real
turn (real tool execution, real output-folder cleanup) against ``FakeProvider``.

Why it matters: this is the only automated check that the widget's contract with
the service still holds — that the worker's list is appended to in place (the
transcript re-render and history merge both read it), that events still arrive as
legacy dicts, and that a produced file really lands in the turn's folder. None of
it needs a display server, so it runs in CI like every other test.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from cowork_local.config import DEFAULT_CONFIG, AppConfig
from cowork_local.tests.fakes.fake_provider import FakeProvider


class _FakeWorker:
    """The parts of ``core/worker.py::AgentWorker`` a job actually touches."""

    def __init__(self, approve_commands: bool = True) -> None:
        self.events: List[Dict[str, Any]] = []
        self.gate: Optional[Any] = None
        self._approve = approve_commands
        self.cancelled = False

    def emit_event(self, event: Dict[str, Any]) -> None:
        self.events.append(event)

    def is_cancelled(self) -> bool:
        return self.cancelled

    def new_gate(self, mode: str, agent_role: str = "") -> Any:
        # Mirrors AgentWorker.new_gate: the gate is stored on the worker so the
        # UI thread can resolve it, and answers request() from the worker thread.
        worker = self

        class _Gate:
            requests: List[Dict[str, Any]] = []

            def request(self, action: Dict[str, Any]) -> bool:
                self.requests.append(action)
                return worker._approve

        self.gate = _Gate()
        return self.gate


class _FakeCtx:
    """The ``AppContext`` surface ``build_job`` uses."""

    def __init__(self, config: AppConfig, confirm_commands: bool = False) -> None:
        self.config = config
        self._confirm = confirm_commands

    def project_confirm_commands(self) -> bool:
        return self._confirm

    def build_mcp_tools(self):
        return [], None


class _WidgetStub:
    """Stands in for the CoworkTab instance ``build_job`` reads its state from."""

    kind = "cowork"

    def __init__(self, out_root: Path, ctx: _FakeCtx, provider: FakeProvider) -> None:
        self._out_root = out_root
        self.ctx = ctx
        self._provider = provider
        self.title = "Report"
        self.session_id = "s1"
        self.project_id = ""          # the auto-seeded default workspace
        self._model = ""
        self._routed_provider = None
        self._routed_model = None

    def _session_output_dir(self) -> Path:
        return self._out_root

    def workspace_dir(self) -> Path:
        return self._out_root

    def admin_agent_prompt(self) -> str:
        return ""

    def build_provider(self) -> FakeProvider:
        return self._provider


def _config() -> AppConfig:
    """A real AppConfig that never touches ``~/.cowork_local``.

    The AI security guardrails are switched off: they would call the model to
    review the prompt, which is a separate feature with its own tests and would
    make this one depend on what the fake answers.
    """
    data = copy.deepcopy(DEFAULT_CONFIG)
    data["agent_security"]["enabled"] = False
    return AppConfig(data)


def _run_turn(tmp_path: Path, provider: FakeProvider, messages: List[Dict[str, Any]],
              *, confirm_commands: bool = False, approve: bool = True):
    """Invoke the real ``CoworkTab.build_job`` against the stub and run its job."""
    from cowork_local.ui.cowork_tab import CoworkTab

    out_dir = tmp_path / ".turns" / "t1"
    out_dir.mkdir(parents=True, exist_ok=True)
    widget = _WidgetStub(tmp_path, _FakeCtx(_config(), confirm_commands), provider)
    worker = _FakeWorker(approve_commands=approve)

    job = CoworkTab.build_job(widget, "make me a report", messages, out_dir)
    result = job(worker)
    return result, worker


def test_the_turn_runs_and_reports_its_folder(tmp_path: Path) -> None:
    provider = FakeProvider()
    provider.queue_response(content="Here you go.", chunks=["Here ", "you go."])
    messages = [{"role": "user", "content": "make me a report"}]

    result, worker = _run_turn(tmp_path, provider, messages)

    assert result["turn_dir"] == str(tmp_path / ".turns" / "t1")
    assert [e["type"] for e in worker.events] == [
        "text", "text", "assistant_done", "turn_completed"]


def test_the_worker_list_is_appended_to_in_place(tmp_path: Path) -> None:
    # _reattach_running_turn replays from this very list while the turn runs, and
    # _finalize_turn slices it by the pre-turn length afterwards.
    provider = FakeProvider()
    provider.queue_response(content="Done.")
    user = {"role": "user", "content": "make me a report"}
    messages = [user]

    result, _ = _run_turn(tmp_path, provider, messages)

    assert result["messages"] is messages
    # Identity, not just equality: _reattach_running_turn locates the turn's user
    # message with ``m is ctx["user_msg"]`` to replay the steps after it.
    assert any(m is user for m in messages)
    # Several system blocks are expected — the tool prompt plus the tagged
    # skills/security-rules blocks the runtime refreshes on every turn.
    assert [m["role"] for m in messages if m["role"] != "system"] == ["user", "assistant"]
    assert messages[-1]["content"] == "Done."


def test_a_saved_file_lands_in_the_turn_folder(tmp_path: Path) -> None:
    provider = FakeProvider()
    provider.queue_response(
        content="Writing it.",
        tool_calls=[{"id": "c1", "name": "save_file",
                     "arguments": {"filename": "report.md", "content": "# Report\n"}}],
    )
    provider.queue_response(content="Saved.")
    messages = [{"role": "user", "content": "make me a report"}]

    _, worker = _run_turn(tmp_path, provider, messages)

    produced = list((tmp_path / ".turns" / "t1").glob("*.md"))
    assert len(produced) == 1
    assert produced[0].read_text(encoding="utf-8") == "# Report\n"
    results = [e for e in worker.events if e["type"] == "tool_result"]
    assert results and results[0]["ok"] is True


def test_auto_run_mode_never_creates_a_permission_gate(tmp_path: Path) -> None:
    provider = FakeProvider()
    provider.queue_response(content="ok")

    _, worker = _run_turn(tmp_path, provider, [{"role": "user", "content": "hi"}],
                          confirm_commands=False)

    assert worker.gate is None


def test_confirm_mode_creates_the_gate_and_a_refusal_stops_the_command(tmp_path: Path) -> None:
    provider = FakeProvider()
    provider.queue_response(
        content="Running it.",
        tool_calls=[{"id": "c1", "name": "run_command",
                     "arguments": {"command": "echo hi"}}],
    )
    provider.queue_response(content="Understood.")

    _, worker = _run_turn(tmp_path, provider, [{"role": "user", "content": "run it"}],
                          confirm_commands=True, approve=False)

    assert worker.gate is not None
    refusals = [e for e in worker.events
                if e["type"] == "tool_result" and e["output"] == "Rejected by user."]
    assert len(refusals) == 1


def test_cancelling_before_the_turn_starts_calls_no_model(tmp_path: Path) -> None:
    from cowork_local.ui.cowork_tab import CoworkTab

    provider = FakeProvider()
    provider.queue_response(content="never")
    out_dir = tmp_path / ".turns" / "t1"
    out_dir.mkdir(parents=True)
    widget = _WidgetStub(tmp_path, _FakeCtx(_config()), provider)
    worker = _FakeWorker()
    worker.cancelled = True

    CoworkTab.build_job(widget, "x", [{"role": "user", "content": "x"}], out_dir)(worker)

    assert provider.call_count == 0
