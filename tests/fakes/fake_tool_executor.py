"""Fake Tool Executor for isolated, offline agent tool-call verification.

Allows tests to verify tool invocation arguments, mock tool return values,
and simulate failures/delays without performing unsafe host disk or OS operations.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


class FakeToolExecutor:
    """Mock execution engine for agent tool-call dispatching."""

    def __init__(self) -> None:
        # History of all executed tool invocations: List of {"name": str, "args": dict, "result": dict}
        self.call_log: List[Dict[str, Any]] = []
        # Custom handlers registered per tool name
        self.handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        # Pre-programmed fixed responses keyed by tool name
        self.mock_responses: Dict[str, Dict[str, Any]] = {}
        # Default response when no specific handler or response is found
        self.default_result: Dict[str, Any] = {"ok": True, "output": "Fake tool executed successfully."}

    def register_handler(
        self,
        tool_name: str,
        handler: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> FakeToolExecutor:
        """Register a dynamic handler function for a specific tool name."""
        self.handlers[tool_name] = handler
        return self

    def set_mock_response(
        self,
        tool_name: str,
        result: Dict[str, Any],
    ) -> FakeToolExecutor:
        """Set a static return payload for a specific tool name."""
        self.mock_responses[tool_name] = result
        return self

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call using registered mocks and record invocation details."""
        # 1. Resolve result from handler, preset response, or default fallback
        if tool_name in self.handlers:
            result = self.handlers[tool_name](arguments)
        elif tool_name in self.mock_responses:
            result = self.mock_responses[tool_name]
        else:
            result = dict(self.default_result)
            result["tool"] = tool_name
            result["received_args"] = arguments

        # 2. Record execution trace for post-test assertions
        self.call_log.append({
            "name": tool_name,
            "args": dict(arguments),
            "result": dict(result),
        })

        return result

    def get_calls_for(self, tool_name: str) -> List[Dict[str, Any]]:
        """Retrieve all recorded calls for a given tool name."""
        return [call for call in self.call_log if call["name"] == tool_name]

    def reset(self) -> None:
        """Clear recorded logs and registered mock responses."""
        self.call_log.clear()
        self.handlers.clear()
        self.mock_responses.clear()
