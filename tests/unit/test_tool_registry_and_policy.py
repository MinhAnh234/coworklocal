"""Unit tests for EPIC R05: the tool descriptor/registry (R05-T01), the split
built-in handlers (R05-T02), and the policy gateway (R05-T03).

The gateway tests assert the SAME capability set each engine used to hard-code
as a name tuple still gets gated after the switch to capability lookup — that
equivalence is the whole point of R05-T03, not an incidental detail.
"""
from __future__ import annotations

from typing import Any, Dict

import pytest

from cowork_local.application.conversations import ToolPolicyGateway
from cowork_local.core.tools import TOOL_SPECS, ToolContext, execute_tool
from cowork_local.domain.tools import ToolCapability, ToolDescriptor, default_registry


# --------------------------------------------------------------------------- #
# R05-T01 - ToolDescriptor / ToolRegistry
# --------------------------------------------------------------------------- #
def test_capability_flags_compose():
    install = ToolDescriptor("install_package", "", {}, ToolCapability.WRITE | ToolCapability.EXECUTE)
    assert install.has(ToolCapability.WRITE)
    assert install.has(ToolCapability.EXECUTE)
    assert not install.has(ToolCapability.NETWORK)


def test_default_registry_matches_todays_hardcoded_gating_sets():
    """The two literal sets this EPIC replaces:
    ``core/tools.py::WRITE_TOOLS`` and ``core/chat_agent.py``'s
    ``("run_command", "install_package")`` tuple. The registry must agree
    with both, or the capability switch silently changes who gets gated."""
    registry = default_registry(TOOL_SPECS)

    execute_gated = {d.name for d in registry.all() if d.has(ToolCapability.EXECUTE)}
    assert execute_gated == {"run_command", "install_package"}

    write_gated = {d.name for d in registry.all() if d.has(ToolCapability.WRITE)}
    assert write_gated == {"write_file", "edit_file", "install_package"}


def test_unregistered_tool_has_no_capabilities():
    registry = default_registry(TOOL_SPECS)
    assert registry.capabilities_for("no_such_tool") is ToolCapability.NONE


# --------------------------------------------------------------------------- #
# R05-T02 - core/tools.py dispatch, now built from the split infra modules
# --------------------------------------------------------------------------- #
def test_execute_tool_still_dispatches_every_built_in(tmp_path):
    ctx = ToolContext(tmp_path)
    written = execute_tool(ctx, "write_file", {"path": "a.txt", "content": "hi"})
    assert written["ok"] is True
    read = execute_tool(ctx, "read_file", {"path": "a.txt"})
    assert read == {"ok": True, "output": "hi"}
    edited = execute_tool(ctx, "edit_file", {"path": "a.txt", "old_string": "hi", "new_string": "bye"})
    assert edited["ok"] is True
    assert execute_tool(ctx, "read_file", {"path": "a.txt"})["output"] == "bye"
    listing = execute_tool(ctx, "list_dir", {})
    assert listing["ok"] is True and "a.txt" in listing["output"]


def test_execute_tool_reports_unknown_name(tmp_path):
    ctx = ToolContext(tmp_path)
    result = execute_tool(ctx, "not_a_real_tool", {})
    assert result == {"ok": False, "output": "Tool not found: not_a_real_tool"}


# --------------------------------------------------------------------------- #
# R05-T03 - ToolPolicyGateway
# --------------------------------------------------------------------------- #
class _RecordingGate:
    def __init__(self, approve: bool):
        self.approve = approve
        self.calls: list = []

    def request(self, payload: Dict[str, Any]) -> bool:
        self.calls.append(payload)
        return self.approve


@pytest.fixture
def cowork_policy() -> ToolPolicyGateway:
    """Same construction as ``core/chat_agent.py``'s module-level
    ``_COWORK_TOOL_POLICY`` - EXECUTE is exactly what Cowork used to gate via
    the literal ``("run_command", "install_package")`` tuple."""
    return ToolPolicyGateway(default_registry(TOOL_SPECS), ToolCapability.EXECUTE)


def test_no_gate_means_auto_run(cowork_policy):
    assert cowork_policy.allow("run_command", None, {}) is True


def test_read_only_tool_never_asks_the_gate(cowork_policy):
    gate = _RecordingGate(approve=False)  # would reject if asked
    assert cowork_policy.allow("write_file", gate, {}) is True
    assert gate.calls == []  # never consulted - write_file isn't EXECUTE


def test_gated_capability_consults_the_gate_and_honors_its_answer(cowork_policy):
    approving = _RecordingGate(approve=True)
    assert cowork_policy.allow("run_command", approving, {"name": "run_command"}) is True
    assert approving.calls == [{"name": "run_command"}]

    rejecting = _RecordingGate(approve=False)
    assert cowork_policy.allow("install_package", rejecting, {}) is False
