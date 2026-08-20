"""Stable module entry point for ``python -m cowork_local.mcp_servers.project_context_server``."""

from .project_context.server import build_server, dispatch, main

__all__ = ["build_server", "dispatch", "main"]


if __name__ == "__main__":
    main()
