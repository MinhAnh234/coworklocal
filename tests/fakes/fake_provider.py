"""Fake LLM Provider for offline unit, contract, and characterization testing.

Provides deterministic responses, stream simulation, tool-call dispatching,
and fault injection without requiring any external network access or API keys.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

try:
    from providers.base import (
        CancelFn,
        Provider,
        ProviderError,
        TextCallback,
        ToolSpec,
    )
except ImportError:
    from cowork_local.providers.base import (
        CancelFn,
        Provider,
        ProviderError,
        TextCallback,
        ToolSpec,
    )

ToolCallScript = Tuple[str, Dict[str, Any]]


@dataclass(frozen=True)
class ScriptedTurn:
    """What :class:`FakeProvider` should do for ONE ``chat()`` call."""

    text: str = ""
    reasoning: str = ""
    tool_calls: Sequence[Any] = ()
    error: Optional[str] = None
    chunk_size: int = 0


@dataclass
class RecordedCall:
    """A snapshot of one ``chat()`` invocation, for assertions after the fact."""

    messages: List[Dict[str, Any]]
    tool_names: List[str]
    cancelled: bool = False


class FakeProvider(Provider):
    """Deterministic test double mimicking real LLM Providers."""

    name = "fake"
    supports_vision = True

    def __init__(
        self,
        turns: Optional[Sequence[ScriptedTurn]] = None,
        *,
        model: str = "fake-model",
        models: Optional[Sequence[str]] = None,
        strict: bool = False,
        conf: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(dict(conf or {}, model=model))
        self._turns: List[ScriptedTurn] = list(turns or [])
        self._models = list(models or [model])
        self._strict = strict
        self._ids = itertools.count(1)
        self.calls: List[RecordedCall] = []
        self.call_history: List[List[Dict[str, Any]]] = []
        self.response_queue: List[Dict[str, Any]] = []
        self.error_queue: List[Exception] = []
        self.default_text: str = "Fake model response."
        self.last_tools: Optional[List[ToolSpec]] = None

    @property
    def call_count(self) -> int:
        return len(self.calls)

    @property
    def remaining_turns(self) -> int:
        return len(self._turns) + len(self.response_queue)

    def last_messages(self) -> List[Dict[str, Any]]:
        return self.calls[-1].messages if self.calls else []

    def queue_response(
        self,
        content: str = "",
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        reasoning: Optional[str] = None,
        chunks: Optional[List[str]] = None,
    ) -> "FakeProvider":
        self.response_queue.append({
            "content": content,
            "tool_calls": tool_calls or [],
            "reasoning": reasoning,
            "chunks": chunks or ([content] if content else []),
        })
        return self

    def queue_error(self, exc: Exception) -> "FakeProvider":
        self.error_queue.append(exc)
        return self

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[ToolSpec]] = None,
        on_text: Optional[TextCallback] = None,
        cancel: Optional[CancelFn] = None,
        on_reasoning: Optional[TextCallback] = None,
    ) -> Dict[str, Any]:
        self.last_tools = tools
        self.call_history.append([dict(m) for m in messages])
        record = RecordedCall(
            messages=[dict(m) for m in messages],
            tool_names=[t.name for t in (tools or [])],
        )
        self.calls.append(record)

        if cancel is not None and cancel():
            record.cancelled = True
            raise ProviderError("Execution aborted by user cancel")

        if self.error_queue:
            err = self.error_queue.pop(0)
            raise err

        if self.response_queue:
            resp = self.response_queue.pop(0)
            if resp.get("reasoning") and on_reasoning:
                on_reasoning(resp["reasoning"])
            for chunk in resp.get("chunks", []):
                if cancel is not None and cancel():
                    record.cancelled = True
                    raise ProviderError("Execution aborted by user cancel")
                if on_text:
                    on_text(chunk)
            out = {
                "role": "assistant",
                "content": resp.get("content", ""),
            }
            if resp.get("tool_calls"):
                out["tool_calls"] = resp["tool_calls"]
            return out

        if self._turns:
            turn = self._turns.pop(0)
            if self._is_cancelled(cancel):
                record.cancelled = True
                return {"role": "assistant", "content": ""}
            if turn.error:
                raise ProviderError(turn.error)
            if turn.reasoning and on_reasoning:
                on_reasoning(turn.reasoning)
            for piece in self._stream_pieces(turn):
                if self._is_cancelled(cancel):
                    record.cancelled = True
                    break
                if on_text:
                    on_text(piece)

            formatted_tool_calls = []
            for tc in turn.tool_calls:
                if isinstance(tc, dict):
                    formatted_tool_calls.append(tc)
                elif isinstance(tc, (tuple, list)) and len(tc) == 2:
                    formatted_tool_calls.append({
                        "id": f"call_{next(self._ids)}",
                        "name": tc[0],
                        "arguments": dict(tc[1]),
                    })
            out = {
                "role": "assistant",
                "content": turn.text,
            }
            if formatted_tool_calls:
                out["tool_calls"] = formatted_tool_calls
            return out

        if self._strict:
            raise AssertionError(
                f"FakeProvider script exhausted: chat() was called {len(self.calls)} "
                "time(s) but fewer turns were scripted."
            )

        if on_text:
            on_text(self.default_text)
        return {
            "role": "assistant",
            "content": self.default_text,
        }

    def list_models(self) -> List[str]:
        self.last_error = ""
        return list(self._models)

    @staticmethod
    def _stream_pieces(turn: ScriptedTurn) -> List[str]:
        if not turn.text:
            return []
        if turn.chunk_size <= 0:
            return [turn.text]
        size = turn.chunk_size
        return [turn.text[i:i + size] for i in range(0, len(turn.text), size)]


__all__ = ["FakeProvider", "ScriptedTurn", "RecordedCall"]
