"""R04-T03 (c) — the service must behave exactly like ``run_cowork``.

The unit tests prove the loop follows the rules I wrote down. They cannot prove
those rules are the ones the shipped runtime actually follows. This file does:
each test scripts one provider, runs the SAME turn twice — once through
``core/chat_agent.py::run_cowork``, once through
``ConversationApplicationService`` wired by ``core_runtime_adapter`` — and
compares the emitted event stream, the resulting conversation and the tool list
the model was shown.

Anything the port got wrong (a missing event, a reordered guard, a different
tool set, a changed message) fails here rather than in front of a user. The only
allowed difference is the extra ``turn_completed`` event R04 introduces, which
has no legacy consumer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cowork_local.application.conversations.core_runtime_adapter import (
    build_cowork_conversation_service,
    legacy_event_sink,
)
from cowork_local.core import chat_agent
from cowork_local.domain.agents.conversation_execution_request import (
    ConversationExecutionRequest,
)
from cowork_local.tests.fakes.fake_provider import FakeProvider

_USER_TURN = [{"role": "user", "content": "make me a report"}]


class _FakeGate:
    """Stands in for ``core/permissions.py::PermissionGate``."""

    def __init__(self, approve: bool) -> None:
        self.approve = approve
        self.requests: List[Dict[str, Any]] = []

    def request(self, action: Dict[str, Any]) -> bool:
        self.requests.append(action)
        return self.approve


def _normalise(events: List[Dict[str, Any]], out_dir: Path) -> List[Dict[str, Any]]:
    """Replace the run's own output path with a placeholder.

    The two runs write into different temp folders, so absolute paths in
    ``tool_result``/``outputs_*`` events differ by construction. Everything else
    must match verbatim.
    """
    marker, raw = "<OUT>", str(out_dir)

    def scrub(value: Any) -> Any:
        if isinstance(value, str):
            return value.replace(raw, marker).replace(raw.replace("\\", "/"), marker)
        if isinstance(value, list):
            return [scrub(v) for v in value]
        if isinstance(value, dict):
            return {k: scrub(v) for k, v in value.items()}
        return value

    return [scrub(e) for e in events]


def _run_legacy(tmp_path: Path, provider: FakeProvider, *, allowed_tools=None,
                gate: Optional[_FakeGate] = None, max_steps: int = 30
                ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    """Run the turn through the existing ``run_cowork``."""
    out_dir = tmp_path / "legacy"
    out_dir.mkdir(parents=True, exist_ok=True)
    events: List[Dict[str, Any]] = []
    messages = [dict(m) for m in _USER_TURN]

    chat_agent.run_cowork(
        provider, messages, out_dir, events.append, title="Report",
        security_config=None, allowed_tools=allowed_tools, gate=gate, max_steps=max_steps,
    )
    tool_names = [t.name for t in (provider.last_tools or [])]
    return _normalise(events, out_dir), messages, tool_names


def _run_service(tmp_path: Path, provider: FakeProvider, *, allowed_tools=None,
                 gate: Optional[_FakeGate] = None, max_steps: int = 30
                 ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    """Run the same turn through the application service."""
    out_dir = tmp_path / "service"
    out_dir.mkdir(parents=True, exist_ok=True)
    events: List[Dict[str, Any]] = []

    service = build_cowork_conversation_service(
        provider, out_dir, events.append, title="Report", security_config=None, gate=gate)
    request = ConversationExecutionRequest(
        turn_id="t1", session_id="s1",
        # run_cowork receives the user message already appended; the request
        # carries the history and this turn's prompt separately.
        messages=_USER_TURN[:-1], prompt=_USER_TURN[-1]["content"],
        output_dir=out_dir, allowed_tools=allowed_tools, max_steps=max_steps,
        gate_mode="confirm" if gate is not None else "auto",
    )
    result = service.execute(request, legacy_event_sink(events.append))

    # The end-of-turn event is new in R04 and has no legacy counterpart.
    kept = [e for e in events if e.get("type") != "turn_completed"]
    tool_names = [t.name for t in (provider.last_tools or [])]
    return _normalise(kept, out_dir), list(result.messages), tool_names


def _assert_parity(tmp_path: Path, script, *, approve: Optional[bool] = None, **kwargs) -> None:
    """Script two identical providers, run both paths, compare everything."""
    legacy_provider, service_provider = FakeProvider(), FakeProvider()
    script(legacy_provider)
    script(service_provider)

    legacy_gate = _FakeGate(approve) if approve is not None else None
    service_gate = _FakeGate(approve) if approve is not None else None

    legacy_events, legacy_messages, legacy_tools = _run_legacy(
        tmp_path, legacy_provider, gate=legacy_gate, **kwargs)
    service_events, service_messages, service_tools = _run_service(
        tmp_path, service_provider, gate=service_gate, **kwargs)

    assert service_events == legacy_events
    assert service_messages == legacy_messages
    assert service_tools == legacy_tools
    if legacy_gate is not None and service_gate is not None:
        assert [r["name"] for r in service_gate.requests] == \
               [r["name"] for r in legacy_gate.requests]


# --------------------------------------------------------------------------- #
# Scenarios.
# --------------------------------------------------------------------------- #
def test_a_plain_answer_turn_behaves_identically(tmp_path: Path) -> None:
    def script(provider: FakeProvider) -> None:
        provider.queue_response(content="Here you go.", chunks=["Here ", "you go."])

    _assert_parity(tmp_path, script)


def test_a_save_file_turn_behaves_identically(tmp_path: Path) -> None:
    def script(provider: FakeProvider) -> None:
        provider.queue_response(
            content="Writing it.",
            tool_calls=[{"id": "c1", "name": "save_file",
                         "arguments": {"filename": "report.md", "content": "# Report\n"}}],
        )
        provider.queue_response(content="Saved.")

    _assert_parity(tmp_path, script)


def test_an_update_plan_turn_behaves_identically(tmp_path: Path) -> None:
    def script(provider: FakeProvider) -> None:
        provider.queue_response(
            content="Planning.",
            tool_calls=[{"id": "c1", "name": "update_plan",
                         "arguments": {"steps": [{"title": "Draft", "status": "running"},
                                                 {"title": "Ship", "status": "pending"}]}}],
        )
        provider.queue_response(content="Done.")

    _assert_parity(tmp_path, script)


def test_a_reasoning_only_reply_behaves_identically(tmp_path: Path) -> None:
    def script(provider: FakeProvider) -> None:
        provider.queue_response(content="", reasoning="thinking hard")

    _assert_parity(tmp_path, script)


def test_restricting_the_tool_scope_advertises_the_same_tools(tmp_path: Path) -> None:
    def script(provider: FakeProvider) -> None:
        provider.queue_response(content="ok")

    _assert_parity(tmp_path, script, allowed_tools=["save_file"])


def test_a_rejected_command_behaves_identically(tmp_path: Path) -> None:
    # The security-critical path: the gate says no, so the command must never
    # run and the model must read back the same refusal in both designs.
    def script(provider: FakeProvider) -> None:
        provider.queue_response(
            content="Running it.",
            tool_calls=[{"id": "c1", "name": "run_command",
                         "arguments": {"command": "echo hi"}}],
        )
        provider.queue_response(content="Understood.")

    _assert_parity(tmp_path, script, approve=False)


def test_hitting_the_step_ceiling_behaves_identically(tmp_path: Path) -> None:
    # The model never stops calling tools, so both paths must stop at the same
    # place and say so the same way.
    def script(provider: FakeProvider) -> None:
        for i in range(4):
            provider.queue_response(
                content=f"step {i}",
                tool_calls=[{"id": f"c{i}", "name": "save_file",
                             "arguments": {"filename": f"f{i}.md", "content": "x"}}],
            )

    _assert_parity(tmp_path, script, max_steps=2)
