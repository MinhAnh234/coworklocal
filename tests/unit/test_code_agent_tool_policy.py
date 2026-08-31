"""EPIC R05-T03/T04: ``core/code_agent.py::run_code`` used to gate tool calls
with ``if name in (WRITE_TOOLS | MS365_WRITE_TOOLS): gate.request(...)``. This
pins that the switch to ``ToolPolicyGateway`` still gates exactly the same
calls: ``write_file`` (a WRITE tool) consults the gate; ``list_dir``
(read-only) never does.

Runs the REAL engine (``run_code``) via :class:`FakeProvider`, same approach
``tests/characterization/test_run_cowork.py`` uses for the Cowork engine.
"""
from __future__ import annotations

from typing import Any, Dict, List

from cowork_local.core.code_agent import run_code
from cowork_local.core.tools import ToolContext
from tests.fakes import FakeProvider, ScriptedTurn


class _RecordingGate:
    def __init__(self, approve: bool):
        self.approve = approve
        self.calls: List[Dict[str, Any]] = []

    def request(self, payload: Dict[str, Any]) -> bool:
        self.calls.append(payload)
        return self.approve


def _run(tmp_path, provider, gate):
    ctx = ToolContext(tmp_path)
    events: List[Dict[str, Any]] = []
    messages: List[Dict[str, Any]] = [{"role": "user", "content": "do it"}]
    run_code(provider, messages, ctx, gate, events.append)
    return events


def test_write_file_consults_the_gate_and_honors_rejection(tmp_path):
    provider = FakeProvider([
        ScriptedTurn(tool_calls=[("write_file", {"path": "a.txt", "content": "hi"})]),
        ScriptedTurn(text="done"),
    ])
    gate = _RecordingGate(approve=False)
    events = _run(tmp_path, provider, gate)

    assert len(gate.calls) == 1 and gate.calls[0]["name"] == "write_file"
    results = [e for e in events if e.get("type") == "tool_result"]
    assert results[0]["ok"] is False
    assert not (tmp_path / "a.txt").exists()  # rejected, never actually written


def test_read_only_tool_never_consults_the_gate(tmp_path):
    (tmp_path / "existing.txt").write_text("x", encoding="utf-8")
    provider = FakeProvider([
        ScriptedTurn(tool_calls=[("list_dir", {})]),
        ScriptedTurn(text="done"),
    ])
    gate = _RecordingGate(approve=False)  # would reject if ever asked
    events = _run(tmp_path, provider, gate)

    assert gate.calls == []
    results = [e for e in events if e.get("type") == "tool_result"]
    assert results[0]["ok"] is True
