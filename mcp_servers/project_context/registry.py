"""Immutable registry composed before member work starts to prevent merge conflicts."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

from .foundation import ToolTemplate
from .tools.change_context import TOOL as CHANGE_CONTEXT_TOOL
from .tools.issue_context import TOOL as ISSUE_CONTEXT_TOOL
from .tools.knowledge_search import TOOL as KNOWLEDGE_SEARCH_TOOL

TOOLS: tuple[ToolTemplate, ...] = (
    ISSUE_CONTEXT_TOOL,
    KNOWLEDGE_SEARCH_TOOL,
    CHANGE_CONTEXT_TOOL,
)
TOOLS_BY_NAME = MappingProxyType({tool.name: tool for tool in TOOLS})
TOOL_NAMES = tuple(tool.name for tool in TOOLS)


def tool_declarations() -> list[dict[str, Any]]:
    """Danh sách khai báo của mọi tool đã đăng ký, để trả về cho ``list_tools``."""
    return [tool.declaration() for tool in TOOLS]
