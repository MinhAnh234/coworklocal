"""Offline test doubles for the R04 turn runtime seams.

Sits beside ``fake_provider.py``/``fake_tool_executor.py`` (R01-T02) and plays
the same role one level up: those fake a *provider*, these fake the ports
``ConversationApplicationService`` is driven through
(``application/conversations/turn_runtime.py``).

Deliberately dumb — they record what they were asked and return canned answers.
A failing test then points at the service under test rather than at a mock
framework's configuration.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from cowork_local.domain.agents.agent_event import ToolPreview
from cowork_local.domain.agents.conversation_execution_request import (
    ConversationExecutionRequest,
)


class FakeSpec:
    """An advertised tool. The service only ever reads ``.name`` off a spec."""

    def __init__(self, name: str) -> None:
        self.name = name


class FakeReply:
    """One programmed provider answer."""

    def __init__(self, content: str = "", tool_calls=None, chunks=None, reasoning: str = ""):
        self.content = content
        self.tool_calls = tool_calls or []
        # Default to streaming the whole content as a single chunk, which is what
        # a non-streaming gateway effectively does.
        self.chunks = chunks if chunks is not None else ([content] if content else [])
        self.reasoning = reasoning


class FakeModelCall:
    """:class:`ModelCallPort` returning programmed replies in order.

    A programmed entry may be an exception instead of a reply, which is how a
    test simulates the gateway dying mid-turn.
    """

    def __init__(self, replies: List[Any]) -> None:
        self.replies = list(replies)
        self.calls: List[Dict[str, Any]] = []

    def call(self, messages, tools, on_text=None, on_reasoning=None, cancel=None):
        # Snapshot the messages: the service keeps mutating its own list, so
        # storing it by reference would make every recorded call look identical.
        self.calls.append({"messages": [dict(m) for m in messages],
                           "tool_names": [getattr(t, "name", "") for t in tools]})
        reply = self.replies.pop(0) if self.replies else FakeReply(content="(default)")
        if isinstance(reply, BaseException):
            raise reply
        if reply.reasoning and on_reasoning:
            on_reasoning(reply.reasoning)
        for chunk in reply.chunks:
            if on_text and chunk:
                on_text(chunk)
        assistant: Dict[str, Any] = {"role": "assistant", "content": reply.content}
        if reply.tool_calls:
            assistant["tool_calls"] = reply.tool_calls
        return assistant


class FakeToolRuntime:
    """:class:`ToolRuntimePort` over an imaginary output folder."""

    def __init__(self, specs=("save_file", "run_command", "update_plan"),
                 results: Optional[Dict[str, Dict[str, Any]]] = None,
                 removed: Tuple[str, ...] = (), added: Tuple[str, ...] = ()) -> None:
        self._specs = [FakeSpec(n) for n in specs]
        self._results = results or {}
        self._removed, self._added = removed, added
        self.executed: List[Tuple[str, Dict[str, Any]]] = []
        self.finalize_calls: List[Dict[str, Any]] = []
        # When set, every executed tool streams this string through ``on_output``.
        self.emit_output: Optional[str] = None

    def specs(self, allowed_tools=None):
        if allowed_tools is None:
            return list(self._specs)
        return [s for s in self._specs if s.name in allowed_tools]

    def preview(self, name, args):
        return ToolPreview(kind="info", title=name, text=str(args))

    def execute(self, name, args, on_output=None, cancel=None):
        self.executed.append((name, dict(args)))
        if self.emit_output and on_output:
            on_output(self.emit_output)
        return dict(self._results.get(name, {"ok": True, "output": f"{name} ok"}))

    def snapshot(self):
        return "before"

    def finalize(self, before, cancelled=False):
        self.finalize_calls.append({"before": before, "cancelled": cancelled})
        return list(self._removed), list(self._added)


# --------------------------------------------------------------------------- #
# Small helpers shared by the turn tests.
# --------------------------------------------------------------------------- #
def make_request(**overrides) -> ConversationExecutionRequest:
    """A minimal valid request; each test overrides only what it exercises."""
    base: Dict[str, Any] = {"turn_id": "t1", "session_id": "s1", "prompt": "do it"}
    base.update(overrides)
    return ConversationExecutionRequest(**base)


def run_turn(service, request=None, cancel=None):
    """Execute a turn and return ``(result, events)``."""
    events: List[Any] = []
    result = service.execute(request or make_request(), events.append, cancel=cancel)
    return result, events


def events_of_type(events, cls):
    """Every emitted event of one type, in order."""
    return [e for e in events if isinstance(e, cls)]


def tool_turn(tool_name: str = "save_file", args=None, **tool_kwargs):
    """A turn that calls one tool and then answers — ``(model, tools)``."""
    calls = [{"id": "c1", "name": tool_name, "arguments": args or {"filename": "a.md"}}]
    model = FakeModelCall([FakeReply(content="working", tool_calls=calls),
                           FakeReply(content="done")])
    return model, FakeToolRuntime(**tool_kwargs)


__all__ = [
    "FakeSpec", "FakeReply", "FakeModelCall", "FakeToolRuntime",
    "make_request", "run_turn", "events_of_type", "tool_turn",
]
