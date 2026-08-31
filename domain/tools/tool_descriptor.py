"""ToolCapability / ToolDescriptor - the risk-tagged catalogue entry for one
tool the agent loop can call (R05-T01).

Today a tool is just a name inside ``core/tools.py::TOOL_SPECS`` (a
``providers.base.ToolSpec`` — name/description/JSON-schema parameters, with
no notion of risk) plus a hand-written membership test wherever gating is
needed: ``core/tools.py::WRITE_TOOLS``, ``core/code_agent.py``'s
``WRITE_TOOLS | MS365_WRITE_TOOLS``, and ``core/chat_agent.py``'s literal
``name in ("run_command", "install_package")``. Three call sites, three
independently-maintained lists, and a new tool (or an MCP/connector tool,
which has no list membership at all - see ``core/mcp_client.py``) is gated
only if someone remembers to add it everywhere.

``ToolDescriptor`` makes the risk an attribute of the tool itself, declared
once, so ``application/conversations/tool_policy_gateway.py`` (R05-T03) can
decide ALLOW/CONFIRM/DENY from data instead of a growing set of literal
tuples.

Pure domain code: stdlib only, no Qt, no I/O. ``to_spec``/``from_spec`` are
the only place this module touches something outside domain/, and that
something (``providers.base.ToolSpec``) is itself a plain dataclass with no
further dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Flag, auto
from typing import Any, Dict

from cowork_local.providers.base import ToolSpec


class ToolCapability(Flag):
    """What calling a tool can do to the machine or the network.

    A ``Flag`` (not a plain ``Enum``) because a single tool can combine risks
    - ``install_package`` writes to the environment, runs pip as a
    subprocess, AND needs network access. Composing three separate booleans
    per call site is exactly the duplication this type replaces.
    """

    NONE = 0
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()
    NETWORK = auto()


@dataclass(frozen=True)
class ToolDescriptor:
    """An immutable description of one callable tool.

    Attributes:
        name: the identifier the model calls (``ToolSpec.name``).
        description: shown to the model, unchanged from ``ToolSpec``.
        parameters: JSON-Schema object for the call's arguments.
        capabilities: the risk this tool carries - see :class:`ToolCapability`.
    """

    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    capabilities: ToolCapability = ToolCapability.NONE

    def has(self, capability: ToolCapability) -> bool:
        """True when this tool carries (any bit of) ``capability``."""
        return bool(self.capabilities & capability)

    def to_spec(self) -> ToolSpec:
        """Project back to the ``ToolSpec`` shape the model-facing catalogue
        and the provider call actually use - risk tagging is metadata the
        wire format has no room for."""
        return ToolSpec(name=self.name, description=self.description,
                        parameters=self.parameters)

    @classmethod
    def from_spec(cls, spec: ToolSpec,
                  capabilities: ToolCapability = ToolCapability.NONE) -> "ToolDescriptor":
        """Wrap an existing ``ToolSpec`` (built-in, MCP, or connector) with a
        capability tag. The one place callers attach risk to a spec they did
        not author themselves."""
        return cls(name=spec.name, description=spec.description,
                   parameters=spec.parameters, capabilities=capabilities)


__all__ = ["ToolCapability", "ToolDescriptor"]
