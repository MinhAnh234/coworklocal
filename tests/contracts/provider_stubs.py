"""Offline transport doubles + per-protocol stream scripts for the provider contract tests.

Kept in its own module so ``test_providers.py`` stays a readable list of
assertions instead of a wall of SSE fixtures, and so the LOC ceiling (400 lines
per production file, applied here too) is comfortably met by both halves.

Nothing in here touches the network: :class:`FakeStreamResponse` mimics just
enough of ``requests.Response`` for the streaming loops in
``providers/openai_compat.py`` and ``providers/anthropic.py`` — status code,
mutable ``encoding``, ``iter_lines`` and ``close``.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

# Canonical turn every protocol script below must produce, so the contract test
# can assert one expected result no matter which provider produced it.
EXPECTED_TEXT = "Hello world"
EXPECTED_TOOL_CALL = {"id": "call-1", "name": "read_file", "arguments": {"path": "a.txt"}}
EXPECTED_INPUT_TOKENS = 11
EXPECTED_OUTPUT_TOKENS = 7
EXPECTED_CACHED_TOKENS = 3


class FakeStreamResponse:
    """A minimal stand-in for a streaming ``requests.Response``.

    ``iter_lines`` replays pre-baked SSE lines; ``closed`` records that the
    provider released the connection, which the contract asserts because a
    provider that leaks the response leaks a socket per turn.
    """

    def __init__(
        self,
        lines: Optional[List[str]] = None,
        status_code: int = 200,
        body: str = "",
        headers: Optional[Dict[str, str]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.status_code = status_code
        self._lines = list(lines or ())
        self.text = body
        self.headers = dict(headers or {})
        self._payload = payload
        self.closed = False
        # Providers force UTF-8 on the response before reading it; the attribute
        # simply has to exist and be writable.
        self.encoding = None

    def iter_lines(self, decode_unicode: bool = False):
        for line in self._lines:
            yield line

    def json(self) -> Any:
        if self._payload is None:
            raise ValueError("no JSON payload configured on this fake response")
        return self._payload

    def close(self) -> None:
        self.closed = True


def _sse(payload: Dict[str, Any]) -> str:
    """One SSE ``data:`` line carrying a JSON event."""
    return "data: " + json.dumps(payload, ensure_ascii=False)


def openai_stream_lines() -> List[str]:
    """A complete OpenAI Chat Completions stream: text, one tool call, usage.

    Split across several deltas on purpose — chunk boundaries are where naive
    stream parsers break, so the contract exercises them.
    """
    return [
        _sse({"choices": [{"delta": {"content": "Hello "}}]}),
        _sse({"choices": [{"delta": {"content": "world"}}]}),
        _sse({"choices": [{"delta": {"tool_calls": [{
            "index": 0, "id": "call-1",
            "function": {"name": "read_file", "arguments": '{"path":'},
        }]}}]}),
        # Arguments arrive fragmented; the provider must concatenate before parsing.
        _sse({"choices": [{"delta": {"tool_calls": [{
            "index": 0, "function": {"arguments": '"a.txt"}'},
        }]}}]}),
        _sse({
            "choices": [{"delta": {}}],
            "usage": {
                "prompt_tokens": EXPECTED_INPUT_TOKENS,
                "completion_tokens": EXPECTED_OUTPUT_TOKENS,
                "prompt_tokens_details": {"cached_tokens": EXPECTED_CACHED_TOKENS},
            },
        }),
        "data: [DONE]",
    ]


def anthropic_stream_lines() -> List[str]:
    """The same canonical turn expressed as an Anthropic Messages stream."""
    return [
        _sse({"type": "message_start", "message": {"usage": {
            "input_tokens": EXPECTED_INPUT_TOKENS,
            "cache_read_input_tokens": EXPECTED_CACHED_TOKENS,
        }}}),
        _sse({"type": "content_block_start", "index": 0,
              "content_block": {"type": "text"}}),
        _sse({"type": "content_block_delta", "index": 0,
              "delta": {"type": "text_delta", "text": "Hello "}}),
        _sse({"type": "content_block_delta", "index": 0,
              "delta": {"type": "text_delta", "text": "world"}}),
        _sse({"type": "content_block_start", "index": 1, "content_block": {
            "type": "tool_use", "id": "call-1", "name": "read_file"}}),
        _sse({"type": "content_block_delta", "index": 1,
              "delta": {"type": "input_json_delta", "partial_json": '{"path":'}}),
        _sse({"type": "content_block_delta", "index": 1,
              "delta": {"type": "input_json_delta", "partial_json": '"a.txt"}'}}),
        _sse({"type": "message_delta",
              "usage": {"output_tokens": EXPECTED_OUTPUT_TOKENS}}),
        _sse({"type": "message_stop"}),
    ]


# Per wire protocol: how to script a successful turn, and the model-list payload
# ``list_models()`` expects. Keyed by the descriptor's wire protocol value so a
# new provider that reuses an existing protocol needs no new entry here.
PROTOCOL_FIXTURES = {
    "openai_compat": {
        "stream_lines": openai_stream_lines,
        "models_payload": {"data": [{"id": "gpt-4o-mini"}, {"id": "gpt-4o"}]},
        "expected_models": ["gpt-4o-mini", "gpt-4o"],
    },
    "anthropic": {
        "stream_lines": anthropic_stream_lines,
        "models_payload": {"data": [{"id": "claude-sonnet-4-6"}]},
        "expected_models": ["claude-sonnet-4-6"],
    },
}


class ScriptedTransport:
    """Replaces ``Provider._request`` and hands back scripted responses.

    Records every call so a test can assert *how* the provider talked to the
    endpoint (method, url, JSON payload) without a socket ever being opened.
    """

    def __init__(self, responses: List[FakeStreamResponse]) -> None:
        self._responses = list(responses)
        self.calls: List[Dict[str, Any]] = []

    def __call__(self, method: str, url: str, **kwargs) -> FakeStreamResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        if not self._responses:
            raise AssertionError(f"unexpected extra request: {method} {url}")
        # Pop in order: a provider that retries gets the NEXT scripted response,
        # which is how the retry/error paths are driven.
        return self._responses.pop(0)

    @property
    def last_payload(self) -> Dict[str, Any]:
        """The JSON body of the most recent request."""
        return self.calls[-1].get("json") or {}


__all__ = [
    "EXPECTED_CACHED_TOKENS",
    "EXPECTED_INPUT_TOKENS",
    "EXPECTED_OUTPUT_TOKENS",
    "EXPECTED_TEXT",
    "EXPECTED_TOOL_CALL",
    "FakeStreamResponse",
    "PROTOCOL_FIXTURES",
    "ScriptedTransport",
    "anthropic_stream_lines",
    "openai_stream_lines",
]
