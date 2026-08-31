"""Domain entities for tool risk classification and lookup (EPIC R05)."""

from .tool_descriptor import ToolCapability, ToolDescriptor
from .tool_registry import (
    BUILT_IN_CAPABILITIES,
    UNKNOWN_SOURCE_CAPABILITIES,
    ToolRegistry,
    default_registry,
)

__all__ = [
    "ToolCapability",
    "ToolDescriptor",
    "ToolRegistry",
    "BUILT_IN_CAPABILITIES",
    "UNKNOWN_SOURCE_CAPABILITIES",
    "default_registry",
]
