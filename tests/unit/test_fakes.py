"""Unit tests for FakeProvider and FakeToolExecutor test doubles."""
from __future__ import annotations

import pytest

from providers.base import ProviderError
from tests.fakes.fake_provider import FakeProvider
from tests.fakes.fake_tool_executor import FakeToolExecutor


def test_fake_provider_text_streaming() -> None:
    """Verify that FakeProvider streams text chunks to on_text callback."""
    provider = FakeProvider()
    provider.queue_response(content="Hello world", chunks=["Hello ", "world"])

    streamed: list[str] = []
    response = provider.chat(
        messages=[{"role": "user", "content": "Hi"}],
        on_text=lambda piece: streamed.append(piece),
    )

    assert response["role"] == "assistant"
    assert response["content"] == "Hello world"
    assert "".join(streamed) == "Hello world"
    assert provider.call_count == 1


def test_fake_provider_tool_calls_and_reasoning() -> None:
    """Verify reasoning streaming and tool_calls payload emission."""
    provider = FakeProvider()
    tool_call = {
        "id": "call_123",
        "name": "save_file",
        "arguments": {"filename": "out.txt", "content": "data"},
    }
    provider.queue_response(
        content="Creating file",
        tool_calls=[tool_call],
        reasoning="User wants output in a file",
    )

    reasoning_chunks: list[str] = []
    response = provider.chat(
        messages=[{"role": "user", "content": "Save to out.txt"}],
        on_reasoning=lambda piece: reasoning_chunks.append(piece),
    )

    assert response["content"] == "Creating file"
    assert response["tool_calls"] == [tool_call]
    assert reasoning_chunks == ["User wants output in a file"]


def test_fake_provider_error_injection() -> None:
    """Verify that queued exceptions are raised on demand."""
    provider = FakeProvider()
    provider.queue_error(ProviderError("Rate limit exceeded (429)"))

    with pytest.raises(ProviderError, match="Rate limit exceeded"):
        provider.chat(messages=[{"role": "user", "content": "Hi"}])


def test_fake_provider_cancellation() -> None:
    """Verify that cancellation stops execution immediately."""
    provider = FakeProvider()
    provider.queue_response(content="Long reply", chunks=["Part 1", "Part 2"])

    is_cancelled = False

    def cancel_fn() -> bool:
        return is_cancelled

    is_cancelled = True
    with pytest.raises(ProviderError, match="aborted by user cancel"):
        provider.chat(
            messages=[{"role": "user", "content": "Hi"}],
            cancel=cancel_fn,
        )


def test_fake_tool_executor() -> None:
    """Verify that FakeToolExecutor records calls and returns expected mock outputs."""
    executor = FakeToolExecutor()
    executor.set_mock_response("read_file", {"ok": True, "content": "file contents"})
    executor.register_handler("calc", lambda args: {"ok": True, "result": args.get("a", 0) + args.get("b", 0)})

    res1 = executor.execute("read_file", {"path": "test.txt"})
    assert res1["ok"] is True
    assert res1["content"] == "file contents"

    res2 = executor.execute("calc", {"a": 5, "b": 10})
    assert res2["result"] == 15

    assert len(executor.call_log) == 2
    assert executor.get_calls_for("calc")[0]["args"] == {"a": 5, "b": 10}
