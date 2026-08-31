"""Characterization tests for core/chat_agent.py (run_chat and run_cowork runtime seams).

These tests capture existing behavior as an executable baseline specification,
ensuring that future refactoring to ConversationApplicationService does not alter
core turn semantics, event emissions, or file handling.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from cowork_local.core import chat_agent
from cowork_local.tests.fakes.fake_provider import FakeProvider


def test_run_chat_characterization() -> None:
    """Capture baseline behavior of run_chat: system prompt insertion, streaming, and message persistence."""
    provider = FakeProvider()
    provider.queue_response(content="Hello there!", chunks=["Hello ", "there!"])

    messages: List[Dict[str, Any]] = [{"role": "user", "content": "Hi assistant"}]
    emitted_events: List[Dict[str, Any]] = []

    def emit(event: Dict[str, Any]) -> None:
        emitted_events.append(event)

    result = chat_agent.run_chat(
        provider=provider,
        messages=messages,
        emit=emit,
    )

    # 1. Verify system prompt was injected at position 0
    assert messages[0]["role"] == "system"
    assert "Cowork Local" in messages[0]["content"]

    # 2. Verify returned assistant message
    assert result["role"] == "assistant"
    assert result["content"] == "Hello there!"

    # 3. Verify assistant message was appended to messages list
    assert messages[-1] == result

    # 4. Verify emitted events sequence
    text_deltas = [e["delta"] for e in emitted_events if e["type"] == "text"]
    assert "".join(text_deltas) == "Hello there!"
    assert any(e["type"] == "assistant_done" for e in emitted_events)


def test_run_cowork_save_file_characterization(tmp_path: Path) -> None:
    """Capture baseline behavior of run_cowork: tool execution loop and file production."""
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    provider = FakeProvider()
    # Step 1: Model requests save_file tool
    provider.queue_response(
        content="Saving your requested report.",
        tool_calls=[{
            "id": "call_save_1",
            "name": "save_file",
            "arguments": {
                "filename": "report.md",
                "content": "# Executive Summary\nAll systems nominal.",
            },
        }],
    )
    # Step 2: Model finishes after tool result
    provider.queue_response(
        content="I have created report.md in your output directory.",
        chunks=["I have created report.md in your output directory."],
    )

    messages: List[Dict[str, Any]] = [{"role": "user", "content": "Export report to markdown file"}]
    emitted_events: List[Dict[str, Any]] = []

    def emit(event: Dict[str, Any]) -> None:
        emitted_events.append(event)

    final_messages = chat_agent.run_cowork(
        provider=provider,
        messages=messages,
        output_dir=output_dir,
        emit=emit,
        enforce_rules=False,
    )

    # 1. Verify file was created in output directory with expected content
    created_file = output_dir / "report.md"
    assert created_file.exists()
    assert created_file.read_text(encoding="utf-8") == "# Executive Summary\nAll systems nominal."

    # 2. Verify message history contains user -> assistant (tool_calls) -> tool -> assistant
    roles = [m["role"] for m in final_messages]
    assert "system" in roles
    assert "user" in roles
    assert "tool" in roles

    # 3. Verify tool result message content
    tool_msg = next(m for m in final_messages if m["role"] == "tool")
    assert tool_msg["name"] == "save_file"
    assert "Saved report.md" in tool_msg["content"]


def test_run_cowork_cancellation_characterization(tmp_path: Path) -> None:
    """Capture cancellation behavior in run_cowork."""
    output_dir = tmp_path / "output_cancel"
    output_dir.mkdir(parents=True, exist_ok=True)

    provider = FakeProvider()
    provider.queue_response(content="Working...")

    is_cancelled = True

    def check_cancel() -> bool:
        return is_cancelled

    emitted_events: List[Dict[str, Any]] = []
    messages: List[Dict[str, Any]] = [{"role": "user", "content": "Please start"}]

    chat_agent.run_cowork(
        provider=provider,
        messages=messages,
        output_dir=output_dir,
        emit=lambda e: emitted_events.append(e),
        cancel=check_cancel,
        enforce_rules=False,
    )

    # Provider should not have executed turns if cancelled right away
    assert provider.call_count == 0


def test_cleanup_turn_output_characterization(tmp_path: Path) -> None:
    """Capture behavior of temporary .scratch folder cleanup and artifact preservation."""
    output_dir = tmp_path / "output_cleanup"
    output_dir.mkdir(parents=True, exist_ok=True)
    scratch_dir = output_dir / ".scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)

    # Create a generator script and a deliverable inside scratch
    generator_script = scratch_dir / "gen.py"
    generator_script.write_text("print('generating')", encoding="utf-8")
    deliverable = scratch_dir / "data.csv"
    deliverable.write_text("a,b,c\n1,2,3", encoding="utf-8")

    before_snapshot = chat_agent._snapshot(output_dir)
    removed, moved = chat_agent._cleanup_cowork_intermediates(output_dir, before_snapshot, cancelled=False)

    # .scratch directory should be removed
    assert not scratch_dir.exists()
    # deliverable should be moved to output root
    root_csv = output_dir / "data.csv"
    assert root_csv.exists()
    # script should not be in output root
    assert not (output_dir / "gen.py").exists()

