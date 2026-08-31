"""Legacy dict -> typed :mod:`agent_event` translation (R04-T02).

Kept in its own module for two reasons. It is a **temporary compatibility
shim**: once R08-T01 turns ``ui/chat_panel.py::_on_event`` into an event
renderer that consumes typed events directly, nothing needs to parse dicts any
more and this whole file gets deleted — a deletion that stays trivial only while
it is isolated. And it keeps ``agent_event.py`` inside the 400-LOC limit the
architecture rules impose, without diluting either file's single job: one
declares the vocabulary, the other bridges it to the old wire format.

Serialisation the other way lives on the events themselves
(``AgentEvent.to_legacy_dict``), because an event has to be emittable without
anyone importing a codec.

SEAM · dựng 2026-08-23 · chưa nối dây (F-05)
------------------------------------------------------------
Được nối khi: ``presentation/chat`` dùng thẳng sự kiện có kiểu, không còn đọc dict cũ nữa.
Để dormant thì sao: Shim này để xoá, không để giữ. Còn nó thì khuôn dict cũ
vẫn là một hợp đồng phải duy trì.

Cổng ``scripts/check_orphan_modules.py`` đếm tuổi seam từ ngày trên
và nhắc khi quá ``SEAM_MAX_AGE_DAYS``. Đổi nội dung dòng đó thì cổng
đọc theo — đừng sửa ngày để làm im lời nhắc.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .agent_event import (
    AgentEvent,
    AssistantMessageCompletedEvent,
    ErrorEvent,
    HistoryReadyEvent,
    NOTICE_INFO,
    NoticeEvent,
    OutputsAddedEvent,
    OutputsRemovedEvent,
    PlanStep,
    PlanUpdatedEvent,
    ReasoningChunkEvent,
    TextChunkEvent,
    ToolCallFinishedEvent,
    ToolCallStartedEvent,
    ToolOutputChunkEvent,
    ToolPreview,
    TurnCompletedEvent,
)


def _plan_steps_from_legacy(raw: Any) -> Tuple[PlanStep, ...]:
    """Parse the legacy ``steps`` list, dropping anything unusable.

    A step with no title cannot be rendered or ticked off, so it is discarded
    instead of becoming a blank row in the Plan panel.
    """
    if not isinstance(raw, list):
        return ()
    steps: List[PlanStep] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        steps.append(PlanStep(title=title, status=str(item.get("status", "pending"))))
    return tuple(steps)


def _parse_tool_started(raw: Dict[str, Any]) -> ToolCallStartedEvent:
    """Rebuild a ``tool_proposed`` event, mapping ``id``/``args`` to typed names."""
    args = raw.get("args")
    return ToolCallStartedEvent(
        call_id=str(raw.get("id", "")), name=str(raw.get("name", "")),
        arguments=dict(args) if isinstance(args, dict) else {},
        preview=ToolPreview.from_dict(raw.get("preview")),
    )


def _parse_tool_finished(raw: Dict[str, Any]) -> ToolCallFinishedEvent:
    """Rebuild a ``tool_result`` event; the optional file keys may be absent."""
    return ToolCallFinishedEvent(
        call_id=str(raw.get("id", "")), name=str(raw.get("name", "")),
        ok=bool(raw.get("ok", False)), output=str(raw.get("output", "")),
        path=str(raw.get("path", "") or ""), produced=raw.get("produced") or (),
    )


# One parser per wire name. A table (rather than an if/elif chain) keeps adding
# an event a single-line change and makes the supported set introspectable.
_PARSERS = {
    TextChunkEvent.EVENT_TYPE: lambda raw: TextChunkEvent(delta=str(raw.get("delta", ""))),
    ReasoningChunkEvent.EVENT_TYPE: lambda raw: ReasoningChunkEvent(
        delta=str(raw.get("delta", ""))),
    AssistantMessageCompletedEvent.EVENT_TYPE: lambda raw: AssistantMessageCompletedEvent(
        content=str(raw.get("content", ""))),
    ToolCallStartedEvent.EVENT_TYPE: _parse_tool_started,
    ToolOutputChunkEvent.EVENT_TYPE: lambda raw: ToolOutputChunkEvent(
        call_id=str(raw.get("id", "")), name=str(raw.get("name", "")),
        delta=str(raw.get("delta", ""))),
    ToolCallFinishedEvent.EVENT_TYPE: _parse_tool_finished,
    PlanUpdatedEvent.EVENT_TYPE: lambda raw: PlanUpdatedEvent(
        steps=_plan_steps_from_legacy(raw.get("steps"))),
    NoticeEvent.EVENT_TYPE: lambda raw: NoticeEvent(
        text=str(raw.get("text", "")), level=str(raw.get("level", NOTICE_INFO))),
    OutputsAddedEvent.EVENT_TYPE: lambda raw: OutputsAddedEvent(paths=raw.get("paths") or ()),
    OutputsRemovedEvent.EVENT_TYPE: lambda raw: OutputsRemovedEvent(paths=raw.get("paths") or ()),
    HistoryReadyEvent.EVENT_TYPE: lambda raw: HistoryReadyEvent(
        session_id=str(raw.get("session_id", ""))),
    TurnCompletedEvent.EVENT_TYPE: lambda raw: TurnCompletedEvent(
        final_text=str(raw.get("final_text", "")), steps_used=int(raw.get("steps_used", 0) or 0),
        cancelled=bool(raw.get("cancelled", False)),
        budget_exhausted=bool(raw.get("budget_exhausted", False))),
    ErrorEvent.EVENT_TYPE: lambda raw: ErrorEvent(
        message=str(raw.get("message", "")), recoverable=bool(raw.get("recoverable", False))),
}


def from_legacy_dict(payload: Any) -> Optional[AgentEvent]:
    """Parse an emitted dict into a typed event, or ``None`` if it isn't ours.

    ``None`` (rather than an exception) is the contract that makes incremental
    adoption possible: a bridge sitting between the runtime and the widget can
    type the events it recognises and forward everything else — Co4E's node
    events, or anything a future emitter adds — completely untouched.
    """
    if not isinstance(payload, dict):
        return None
    parser = _PARSERS.get(str(payload.get("type", "")))
    return parser(payload) if parser is not None else None


__all__ = ["from_legacy_dict"]
