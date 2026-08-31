"""EPIC R05-T05: the MCP connection lifecycle extracted out of
``state.py::AppContext`` into :class:`McpToolSourceManager`.

Uses a fake connection (no real subprocess/asyncio loop) so these tests run in
milliseconds and don't depend on any actual MCP server being installed.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from cowork_local.infrastructure.mcp import McpToolSourceManager


class _FakeConnection:
    """Stands in for ``core.mcp_client.McpServerConnection`` — tracks
    start/stop calls instead of spawning anything."""

    instances: List["_FakeConnection"] = []

    def __init__(self, name: str, command: str, args: Optional[List[str]] = None,
                env: Optional[Dict[str, str]] = None):
        self.name = name
        self.command = command
        self.args = args
        self.env = env
        self.started = False
        self.stopped = False
        self._alive = True
        _FakeConnection.instances.append(self)

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True
        self._alive = False

    def is_alive(self) -> bool:
        return self._alive


def _manager() -> McpToolSourceManager:
    _FakeConnection.instances.clear()
    return McpToolSourceManager(connection_factory=_FakeConnection)


def test_ensure_starts_once_and_caches_the_live_connection():
    mgr = _manager()
    first = mgr.ensure("github", "npx", ["-y", "github-mcp"])
    second = mgr.ensure("github", "npx", ["-y", "github-mcp"])

    assert first is second  # same connection reused, not a second subprocess
    assert len(_FakeConnection.instances) == 1
    assert first.started is True


def test_two_concurrent_ensures_for_different_servers_dont_collide():
    mgr = _manager()
    a = mgr.ensure("server-a", "cmd-a")
    b = mgr.ensure("server-b", "cmd-b")
    assert a is not b
    assert {c.name for c in mgr.active()} == {"server-a", "server-b"}


def test_ensure_restarts_when_the_cached_connection_died():
    mgr = _manager()
    first = mgr.ensure("flaky", "cmd")
    first.stop()  # simulate the subprocess crashing
    assert mgr.is_alive("flaky") is False

    second = mgr.ensure("flaky", "cmd")
    assert second is not first
    assert len(_FakeConnection.instances) == 2


def test_a_server_that_fails_to_start_returns_none_and_isnt_cached():
    class _DyingConnection(_FakeConnection):
        def start(self) -> None:
            raise RuntimeError("boom")

    mgr = McpToolSourceManager(connection_factory=_DyingConnection)
    assert mgr.ensure("broken", "cmd") is None
    assert mgr.get("broken") is None


def test_stop_removes_one_connection_without_touching_others():
    mgr = _manager()
    mgr.ensure("keep", "cmd")
    doomed = mgr.ensure("drop", "cmd")

    mgr.stop("drop")

    assert doomed.stopped is True
    assert mgr.get("drop") is None
    assert mgr.get("keep") is not None


def test_stop_all_stops_every_connection_and_clears_the_cache():
    mgr = _manager()
    mgr.ensure("a", "cmd")
    mgr.ensure("b", "cmd")

    mgr.stop_all()

    assert all(c.stopped for c in _FakeConnection.instances)
    assert mgr.active() == []
