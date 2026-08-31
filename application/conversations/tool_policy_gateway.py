"""ToolPolicyGateway - one confirm/deny decision path for every tool call
(R05-T03).

Today "does this tool call need the user's OK first" is answered by a
different hand-written check per engine:

* ``core/chat_agent.py::run_cowork`` — ``name in ("run_command",
  "install_package")``, a literal tuple.
* ``core/code_agent.py::run_code`` — ``name in (WRITE_TOOLS | MS365_WRITE_TOOLS)``,
  a set built from two other hand-maintained sets.
* MCP/connector tools (``core/mcp_client.py``, ``core/ext_connectors.py``) —
  no check at all; ``chat_agent.py`` calls ``extra_executor(name, args)``
  directly.

Three answers to the same question, and the third one is a real gap: an MCP
tool that deletes files or calls an external API today runs with zero
confirmation even when the user turned "confirm before running commands" on.

This gateway answers the question from data (:class:`~domain.tools.tool_descriptor.ToolCapability`
via a :class:`~domain.tools.tool_registry.ToolRegistry`) instead of a literal
name list, so registering a tool with the right capability is what gates it -
nothing to remember at each new call site. R05-T04 is what actually registers
MCP/connector tools with a capability; this module only needs the mechanism
to exist.

Pure Python: no Qt, no direct dialog. The actual approval prompt stays exactly
what it is today - a ``gate`` object with a ``.request(payload) -> bool``
method, supplied by the presentation layer (Settings' "confirm before running
commands" wires it up, or None for auto-run) - this module only decides
WHEN to ask it, never how to render the question.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Protocol

from cowork_local.domain.tools import ToolCapability, ToolRegistry


class ConfirmGate(Protocol):
    """Shape of the existing ``PermissionGate`` both engines already use."""

    """Hỏi người dùng; trả về ``True`` nếu được đồng ý."""
    def request(self, payload: Dict[str, Any]) -> bool:
        """Hỏi người dùng về một lời gọi tool; trả về ``True`` nếu được đồng ý."""
        ...


class ToolPolicyGateway:
    """Decides whether a tool call needs approval, for ONE calling surface.

    ``gated_capabilities`` is what makes this per-surface: Cowork only ever
    asked about ``run_command``/``install_package`` (capability ``EXECUTE``),
    while the Code tab additionally confirms plain file writes (capability
    ``WRITE``). Passing the wrong set here would silently change which tools
    prompt for approval - see the callers in ``core/chat_agent.py`` and
    ``core/code_agent.py`` for the exact sets that preserve today's behavior.
    """

    def __init__(self, registry: ToolRegistry, gated_capabilities: ToolCapability) -> None:
        """Nhận sổ đăng ký tool và tập năng lực cần xin phép.

        Truyền vào chứ không viết cứng: mỗi bề mặt chat có ngưỡng riêng, và test đặt
        được ngưỡng của mình mà không đụng cấu hình thật.
        """
        self._registry = registry
        self._gated_capabilities = gated_capabilities

    def requires_confirmation(self, name: str) -> bool:
        """True when ``name``'s declared capabilities overlap this surface's
        gated set. An unregistered tool never requires confirmation through
        this path - callers that must fail safe on unknown tools check
        ``name in registry`` themselves (see R05-T04's MCP wrapping, which
        registers every tool it exposes before any call can reach here)."""
        return bool(self._registry.capabilities_for(name) & self._gated_capabilities)

    def allow(self, name: str, gate: Optional[ConfirmGate], payload: Dict[str, Any]) -> bool:
        """True when the call may proceed.

        ``gate is None`` preserves each engine's existing "no gate wired -
        auto-run" behavior; a tool outside ``gated_capabilities`` is never
        asked about, matching read-only tools "never confirm" today.
        ``payload`` is whatever ``gate.request(...)`` already expects at that
        call site (the two engines use slightly different dict shapes) - this
        gateway only decides WHETHER to call it, never reshapes the payload.
        """
        if gate is None or not self.requires_confirmation(name):
            return True
        return bool(gate.request(payload))


__all__ = ["ToolPolicyGateway", "ConfirmGate"]
