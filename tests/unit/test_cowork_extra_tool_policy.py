"""EPIC R05-T04: before this change, ``core/chat_agent.py::run_cowork`` called
``extra_executor(name, args)`` directly for any MCP/connector tool — no
permission check at all, regardless of the "confirm before running commands"
setting. This pins the fix: an extra tool now goes through the same
``ToolPolicyGateway`` as ``run_command``, using the conservative default
capability (``UNKNOWN_SOURCE_CAPABILITIES``) since MCP tools carry no
standard risk metadata.

Runs the real engine via :class:`FakeProvider`, matching
``tests/characterization/test_run_cowork.py``'s approach.
"""
from __future__ import annotations

from typing import Any, Dict, List

from cowork_local.core.chat_agent import run_cowork
from cowork_local.providers.base import ToolSpec
from tests.fakes import FakeProvider, ScriptedTurn


class _RecordingGate:
    def __init__(self, approve: bool):
        self.approve = approve
        self.calls: List[Dict[str, Any]] = []

    def request(self, payload: Dict[str, Any]) -> bool:
        self.calls.append(payload)
        return self.approve


_EXTRA_SPEC = ToolSpec(name="github__delete_repo", description="", parameters={"type": "object"})


def _run(tmp_path, provider, gate, executed: List[str]):
    events: List[Dict[str, Any]] = []
    messages: List[Dict[str, Any]] = [{"role": "user", "content": "hi"}]

    def extra_executor(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        executed.append(name)
        return {"ok": True, "output": "done"}

    run_cowork(provider, messages, tmp_path, events.append, gate=gate,
              extra_tools=[_EXTRA_SPEC], extra_executor=extra_executor)
    return events


def test_mcp_style_tool_is_rejected_without_ever_calling_the_executor(tmp_path):
    provider = FakeProvider([
        ScriptedTurn(tool_calls=[("github__delete_repo", {})]),
        ScriptedTurn(text="done"),
    ])
    gate = _RecordingGate(approve=False)
    executed: List[str] = []
    events = _run(tmp_path, provider, gate, executed)

    assert len(gate.calls) == 1 and gate.calls[0]["name"] == "github__delete_repo"
    assert executed == []  # rejected BEFORE the extra_executor ever ran
    results = [e for e in events if e.get("type") == "tool_result"]
    assert results[0]["ok"] is False


def test_mcp_style_tool_runs_once_approved(tmp_path):
    provider = FakeProvider([
        ScriptedTurn(tool_calls=[("github__delete_repo", {})]),
        ScriptedTurn(text="done"),
    ])
    gate = _RecordingGate(approve=True)
    executed: List[str] = []
    events = _run(tmp_path, provider, gate, executed)

    assert executed == ["github__delete_repo"]
    results = [e for e in events if e.get("type") == "tool_result"]
    assert results[0]["ok"] is True


def test_no_gate_preserves_auto_run_for_extra_tools(tmp_path):
    """``gate=None`` is Cowork's existing "no confirmation configured" state —
    must still auto-run, exactly like before this EPIC."""
    provider = FakeProvider([
        ScriptedTurn(tool_calls=[("github__delete_repo", {})]),
        ScriptedTurn(text="done"),
    ])
    executed: List[str] = []
    events = _run(tmp_path, provider, None, executed)

    assert executed == ["github__delete_repo"]
