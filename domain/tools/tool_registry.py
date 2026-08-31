"""ToolRegistry - the centralised catalogue every tool source registers into
(R05-T01).

Built-in file/command/fetch tools (``core/tools.py``), MCP server tools
(``core/mcp_client.py``) and unified connectors (``core/ext_connectors.py``)
each produce their own ``List[ToolSpec]`` today, concatenated ad-hoc by
``core/tools.py::combine_tool_sources``. None of that concatenation carries
risk information, which is exactly why an MCP tool call reaches
``core/chat_agent.py`` with no ``ToolDescriptor`` to consult and skips the
permission gate entirely (the gap R05-T04 closes).

``ToolRegistry`` is the one place a :class:`~domain.tools.tool_descriptor.ToolDescriptor`
is looked up by name, so a policy gateway - or anything else that needs to ask
"what can this tool do" - has a single source of truth instead of re-deriving
it from a spec list.

Pure domain code: stdlib only, no Qt, no I/O.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from cowork_local.providers.base import ToolSpec

from .tool_descriptor import ToolCapability, ToolDescriptor


class ToolRegistry:
    """An in-memory, name-keyed catalogue of :class:`ToolDescriptor`.

    Deliberately mutable and unordered-by-name-only: a turn builds one
    registry from whichever tool sources it has (built-ins + whatever MCP
    servers/connectors are enabled), so re-registering the same name simply
    replaces the previous descriptor rather than raising - the same
    "last one wins" behaviour ``combine_tool_sources`` already has for
    duplicate tool names across sources.
    """

    def __init__(self, descriptors: Optional[Iterable[ToolDescriptor]] = None) -> None:
        """Đăng ký sẵn một loạt tool. Đi qua ``register`` chứ không gán thẳng dict để
        mọi kiểm tra trùng tên đều chạy.
        """
        self._by_name: Dict[str, ToolDescriptor] = {}
        for descriptor in descriptors or ():
            self.register(descriptor)

    def register(self, descriptor: ToolDescriptor) -> None:
        """Đăng ký (hoặc thay thế) một tool theo tên."""
        self._by_name[descriptor.name] = descriptor

    def get(self, name: str) -> Optional[ToolDescriptor]:
        """Mô tả của một tool; ``None`` nếu chưa đăng ký."""
        return self._by_name.get(name)

    def all(self) -> List[ToolDescriptor]:
        """Danh sách mọi tool đã đăng ký."""
        return list(self._by_name.values())

    def specs(self) -> List[ToolSpec]:
        """Every registered descriptor, projected back to ``ToolSpec`` - the
        shape the provider call and the model-facing catalogue need."""
        return [d.to_spec() for d in self._by_name.values()]

    def capabilities_for(self, name: str) -> ToolCapability:
        """The capability set for ``name``, or ``NONE`` for an unknown tool.

        Returning ``NONE`` rather than raising lets a policy gateway treat an
        unregistered tool the same way as one with no declared risk - the
        gateway's DENY-on-unknown-name rule is a deliberate, separate check,
        not something this lookup should pre-empt.
        """
        descriptor = self._by_name.get(name)
        return descriptor.capabilities if descriptor is not None else ToolCapability.NONE

    def __contains__(self, name: str) -> bool:
        """``"tên" in registry`` — tra theo tên tool."""
        return name in self._by_name

    def __len__(self) -> int:
        """Số tool đã đăng ký."""
        return len(self._by_name)


# --------------------------------------------------------------------------- #
# Default capability map for this app's built-in tools (core/tools.py).
# Kept here, next to the registry, rather than inside core/tools.py itself -
# core/ is the legacy engine layer being strangled, not where new domain facts
# should accumulate.
# --------------------------------------------------------------------------- #
_CAP = ToolCapability
BUILT_IN_CAPABILITIES: Dict[str, ToolCapability] = {
    "read_file": _CAP.READ,
    "list_dir": _CAP.READ,
    "write_file": _CAP.WRITE,
    "edit_file": _CAP.WRITE,
    "run_command": _CAP.EXECUTE,
    "install_package": _CAP.WRITE | _CAP.EXECUTE | _CAP.NETWORK,
    "fetch_url": _CAP.NETWORK,
    "jira_search": _CAP.NETWORK,
    "jira_get_issue": _CAP.NETWORK,
    # Advertised by every engine but has no filesystem/process/network effect
    # of its own - it only drives the Plan panel (see core/chat_agent.py).
    "update_plan": _CAP.NONE,
    "save_file": _CAP.WRITE,
}

# Tools with no standard, self-declared risk metadata (every MCP server tool,
# every unified connector) are tagged with this conservative default - see
# R05-T04. Better to over-gate an unknown remote tool than to silently let it
# through as READ-only.
UNKNOWN_SOURCE_CAPABILITIES: ToolCapability = _CAP.WRITE | _CAP.EXECUTE | _CAP.NETWORK


def default_registry(specs: Iterable[ToolSpec]) -> ToolRegistry:
    """Build a registry from ``core/tools.py``'s own ``TOOL_SPECS`` (plus
    ``save_file``/``update_plan``, which the engines add separately), using
    :data:`BUILT_IN_CAPABILITIES`. A spec with no entry in that map falls back
    to :data:`UNKNOWN_SOURCE_CAPABILITIES` - the same conservative default
    applied to MCP/connector tools, so a built-in nobody has classified yet
    fails safe instead of silently ungated."""
    registry = ToolRegistry()
    for spec in specs:
        capability = BUILT_IN_CAPABILITIES.get(spec.name, UNKNOWN_SOURCE_CAPABILITIES)
        registry.register(ToolDescriptor.from_spec(spec, capability))
    return registry


__all__ = [
    "ToolRegistry",
    "BUILT_IN_CAPABILITIES",
    "UNKNOWN_SOURCE_CAPABILITIES",
    "default_registry",
]
