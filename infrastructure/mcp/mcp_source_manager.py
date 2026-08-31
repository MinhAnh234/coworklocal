"""McpToolSourceManager - the MCP server connection lifecycle, extracted out
of ``state.py::AppContext`` (R05-T05).

Today ``AppContext.build_mcp_tools`` inlines all of this: a ``_mcp_connections``
dict, a ``_conn_lock`` guarding check-then-create against concurrent turns (a
Cowork tab, a Co4E flow and a Scheduled Task can all call it at once), and a
"start it, cache it, skip it on failure" loop repeated for both the
admin-configured servers AND the built-in MS365 server
(``_ms365_builtin_connection``). None of that logic touches Qt; it was only
ever inline because ``AppContext`` is where the config lived.

This class owns the SAME cache/lock/start-or-skip behavior as a standalone,
directly testable object — ``AppContext`` becomes a thin caller (one instance
per app, same as it holds one ``RoutingApplicationService``).

Pure Python: no Qt. It DOES touch the network/filesystem via
``core.mcp_client.McpServerConnection`` (a subprocess + asyncio loop), which is
exactly what makes it infrastructure rather than domain.
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from cowork_local.core.mcp_client import McpServerConnection


class McpToolSourceManager:
    """Caches and supervises one :class:`McpServerConnection` per server name.

    ``connection_factory`` defaults to ``McpServerConnection`` itself; tests
    substitute a fake so no real subprocess is spawned (see
    ``tests/unit/test_mcp_source_manager.py``).
    """

    def __init__(self, connection_factory=McpServerConnection) -> None:
        """``connection_factory`` tiêm được để test không phải chạy tiến trình con thật.

        Có khoá riêng vì nhiều lượt chat song song cùng gọi tới đây: kiểm-rồi-tạo mà
        không khoá sẽ dựng hai kết nối cho cùng một máy chủ.
        """
        self._connections: Dict[str, McpServerConnection] = {}
        self._lock = threading.Lock()
        self._connection_factory = connection_factory

    def ensure(self, name: str, command: str, args: Optional[List[str]] = None,
               env: Optional[Dict[str, str]] = None) -> Optional[McpServerConnection]:
        """Return a live connection for ``name``, starting one if there is
        none cached or the cached one's subprocess has died.

        Serialized under one lock so two turns racing to build their tool
        list at the same moment share one subprocess per server instead of
        each spawning their own (the bug this replaces:
        ``AppContext._conn_lock``'s original docstring). Returns ``None`` -
        never raises - when the server fails to start, matching the existing
        "one broken server must not block the turn" behavior.
        """
        with self._lock:
            existing = self._connections.get(name)
            if existing is not None and existing.is_alive():
                return existing
            if existing is not None:
                self._connections.pop(name, None)
            connection = self._connection_factory(name, command, args or [], env)
            try:
                connection.start()
            except Exception:  # noqa: BLE001 - one broken server must not block the turn
                return None
            self._connections[name] = connection
            return connection

    def get(self, name: str) -> Optional[McpServerConnection]:
        """The cached connection for ``name``, without starting one."""
        return self._connections.get(name)

    def is_alive(self, name: str) -> bool:
        """Kết nối tới một MCP server còn sống không."""
        connection = self._connections.get(name)
        return connection is not None and connection.is_alive()

    def restart(self, name: str, command: str, args: Optional[List[str]] = None,
                env: Optional[Dict[str, str]] = None) -> Optional[McpServerConnection]:
        """Force a fresh connection for ``name`` even if the cached one still
        looks alive - for a server the caller knows is misbehaving."""
        with self._lock:
            self._connections.pop(name, None)
        return self.ensure(name, command, args, env)

    def stop(self, name: str) -> None:
        """Stop and forget one connection - used when a server becomes
        unavailable by configuration (e.g. MS365 signed out) rather than by
        crashing."""
        with self._lock:
            connection = self._connections.pop(name, None)
        if connection is not None:
            try:
                connection.stop()
            except Exception:  # noqa: BLE001 - shutdown must never raise into the caller
                pass

    def active(self) -> List[McpServerConnection]:
        """Every currently cached connection - what
        ``core/mcp_client.py::build_mcp_tools`` merges tool specs from."""
        return list(self._connections.values())

    def stop_all(self) -> None:
        """Terminate every connection's subprocess - called on app shutdown
        so none of them linger as orphan processes."""
        with self._lock:
            connections = list(self._connections.values())
            self._connections.clear()
        for connection in connections:
            try:
                connection.stop()
            except Exception:  # noqa: BLE001
                pass


__all__ = ["McpToolSourceManager"]
