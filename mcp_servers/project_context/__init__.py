"""Provider-neutral Project Context MCP server template."""

from .server import build_server, dispatch

__all__ = ["build_server", "dispatch"]
