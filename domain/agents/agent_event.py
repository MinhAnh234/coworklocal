"""Typed events a turn emits while it runs (R04-T02).

The runtime currently speaks in bare dicts: ``emit({"type": "tool_result", "id":
..., "ok": ...})``. Nothing declares which keys a given type carries, so the
only specification is the 130-line ``if/elif`` chain in
``ui/chat_panel.py::_on_event`` — and a typo in an emitter surfaces as a widget
that silently renders nothing.

This module makes the vocabulary explicit. Each event is a frozen dataclass with
real fields, and each one knows how to serialise itself back to the exact legacy
dict the widget already reads (:meth:`AgentEvent.to_legacy_dict`), with
:func:`from_legacy_dict` parsing the other way. That two-way bridge is what lets
R04 introduce typed events WITHOUT touching the presentation layer — decomposing
``_on_event`` into a renderer is R08-T01's job, and forcing both changes into one
PR is exactly the "rewrite everything at once" the refactor plan forbids.

Scope note: this covers the interactive/scheduled **Cowork turn** vocabulary
(the ``run_cowork`` path R04 unifies). Co4E's own node events (``node_status``,
``stage_text``, ``run_done``) belong to ``Co4EWorkflowService`` in R07-T06 and
are deliberately left as dicts here — :func:`from_legacy_dict` returns ``None``
for them so a bridge can pass them straight through.

Layer rules (``docs/architecture/ADR-001-layered-architecture.md``): domain
layer, standard library only. No PySide6, no ``core/*`` imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, Iterable, Optional, Tuple

# Notice levels. "progress" is special-cased by the UI (it retargets the live
# thinking indicator instead of adding a bubble), so the vocabulary is pinned
# here rather than left to each emitter's string literal.
NOTICE_INFO = "info"
NOTICE_WARNING = "warning"
NOTICE_PROGRESS = "progress"


# --------------------------------------------------------------------------- #
# Value objects shared by several events.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ToolPreview:
    """The human-readable preview of a proposed tool call.

    Mirrors ``core/tools.py::describe_action``'s return shape exactly (three
    string keys, nothing else), so wrapping it in a type is lossless. ``kind``
    drives which bubble the UI renders: "diff" -> coloured before/after,
    "command" -> terminal block, "info" -> plain text.
    """

    kind: str = "info"
    title: str = ""
    text: str = ""

    def to_dict(self) -> Dict[str, str]:
        """Ba khoá đúng như ``core/tools.py::describe_action`` trả về — không thêm không bớt."""
        return {"kind": self.kind, "title": self.title, "text": self.text}

    @classmethod
    def from_dict(cls, raw: Any) -> Optional["ToolPreview"]:
        """Parse a legacy preview dict; ``None`` when there was none.

        A non-dict value degrades to ``None`` rather than raising: a malformed
        preview must cost the user a nicer bubble, never the whole turn.
        """
        if not isinstance(raw, dict) or not raw:
            return None
        return cls(kind=str(raw.get("kind", "info")), title=str(raw.get("title", "")),
                   text=str(raw.get("text", "")))


@dataclass(frozen=True)
class PlanStep:
    """One entry of the agent's ``update_plan`` checklist.

    ``status`` is kept a plain string on purpose: ``core/plan.py`` already owns
    validation (clamping anything unknown to "pending" against
    pending/running/done/error), and duplicating that vocabulary here would give
    the app two sources of truth to drift apart.
    """

    title: str
    status: str = "pending"

    def to_dict(self) -> Dict[str, str]:
        """Một bước kế hoạch dưới dạng dict, để đưa vào payload sự kiện."""
        return {"title": self.title, "status": self.status}


def _as_str_tuple(values: Iterable[Any]) -> Tuple[str, ...]:
    """Freeze an iterable of paths into a tuple of strings.

    Emitters hand us live lists (``record["outputs"]``, ``_cleanup``'s result);
    copying decouples the event from later mutation of that list.
    """
    return tuple(str(v) for v in (values or ()))


# --------------------------------------------------------------------------- #
# Base class.
# --------------------------------------------------------------------------- #
class AgentEvent:
    """Base for every turn event.

    Not a dataclass itself (it holds no data) — subclasses are the frozen
    dataclasses. ``EVENT_TYPE`` is the legacy wire name, which stays the single
    identifier shared between the typed world and the dict world.
    """

    EVENT_TYPE: ClassVar[str] = ""

    def _payload(self) -> Dict[str, Any]:
        """Type-specific keys of the legacy dict (without ``type``)."""
        return {}

    def to_legacy_dict(self) -> Dict[str, Any]:
        """The exact dict shape ``ui/chat_panel.py::_on_event`` dispatches on."""
        return {"type": self.EVENT_TYPE, **self._payload()}


# --------------------------------------------------------------------------- #
# Streaming events.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class TextChunkEvent(AgentEvent):
    """A fragment of the assistant's visible answer."""

    EVENT_TYPE: ClassVar[str] = "text"
    delta: str = ""

    def _payload(self) -> Dict[str, Any]:
        """``{delta}`` — một mẩu câu trả lời đang phát dần."""
        return {"delta": self.delta}


@dataclass(frozen=True)
class ReasoningChunkEvent(AgentEvent):
    """A fragment of a reasoning model's thinking, shown in a collapsed box."""

    EVENT_TYPE: ClassVar[str] = "reasoning"
    delta: str = ""

    def _payload(self) -> Dict[str, Any]:
        """``{delta}`` — một mẩu suy luận nội bộ của model."""
        return {"delta": self.delta}


@dataclass(frozen=True)
class AssistantMessageCompletedEvent(AgentEvent):
    """One assistant message finished streaming.

    Emitted once per provider call, so a tool-using turn produces SEVERAL of
    these — it marks an autosave point, not the end of the turn. The end of the
    turn is :class:`TurnCompletedEvent`.
    """

    EVENT_TYPE: ClassVar[str] = "assistant_done"
    content: str = ""

    def _payload(self) -> Dict[str, Any]:
        """``{content}`` — nội dung trọn vẹn của một lượt gọi provider."""
        return {"content": self.content}


# --------------------------------------------------------------------------- #
# Tool-call lifecycle.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ToolCallStartedEvent(AgentEvent):
    """A tool call is about to run (after any security/permission gate).

    Field names are the typed ones (``call_id``, ``arguments``); the legacy keys
    ``id``/``args`` are produced only at the serialisation boundary, so new code
    never has to shadow the ``id`` builtin.
    """

    EVENT_TYPE: ClassVar[str] = "tool_proposed"
    call_id: str = ""
    name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    preview: Optional[ToolPreview] = None

    def _payload(self) -> Dict[str, Any]:
        """``{id, name, args}``, kèm ``preview`` chỉ khi thật sự có.

        Không có xem trước thì BỎ HẲN khoá thay vì gửi ``None``: widget đang viết
        ``ev.get("preview") or {}``, tức nó đã quen với việc khoá vắng mặt.
        """
        payload: Dict[str, Any] = {"id": self.call_id, "name": self.name,
                                   "args": dict(self.arguments)}
        # Omitted rather than sent as None: the widget does
        # ``preview = ev.get("preview") or {}`` and an absent key is the shape it
        # already handles for tools without a preview.
        if self.preview is not None:
            payload["preview"] = self.preview.to_dict()
        return payload


@dataclass(frozen=True)
class ToolOutputChunkEvent(AgentEvent):
    """Live stdout/stderr from a running command, appended to its step bubble."""

    EVENT_TYPE: ClassVar[str] = "tool_output"
    call_id: str = ""
    name: str = ""
    delta: str = ""

    def _payload(self) -> Dict[str, Any]:
        """``{id, name, delta}`` — một mẩu đầu ra tool đang chạy."""
        return {"id": self.call_id, "name": self.name, "delta": self.delta}


@dataclass(frozen=True)
class ToolCallFinishedEvent(AgentEvent):
    """A tool call returned. ``path``/``produced`` name files it created."""

    EVENT_TYPE: ClassVar[str] = "tool_result"
    call_id: str = ""
    name: str = ""
    ok: bool = False
    output: str = ""
    path: str = ""                      # the single file this call wrote, if any
    produced: Tuple[str, ...] = ()      # extra deliverables a command produced

    def __post_init__(self) -> None:
        # Callers pass a live list; freeze it so the event cannot change later.
        """Đóng băng danh sách tệp đầu ra thành tuple.

        Bên gọi truyền vào một list đang sống; không sao chép thì sự kiện đã phát đi
        vẫn đổi nội dung được về sau — sự kiện phải là ảnh chụp bất biến.
        """
        object.__setattr__(self, "produced", _as_str_tuple(self.produced))

    def _payload(self) -> Dict[str, Any]:
        """``{id, name, ok, output}``, kèm ``error``/``produced`` chỉ khi có.

        Hai khoá sau vắng mặt khi rỗng, đúng như ``chat_agent`` vẫn phát: phía
        nhận kiểm bằng ``ev.get(...)`` nên thêm giá trị rỗng là đổi hành vi.
        """
        payload: Dict[str, Any] = {"id": self.call_id, "name": self.name,
                                   "ok": self.ok, "output": self.output}
        # Both keys stay ABSENT when empty, matching what chat_agent emits today:
        # downstream code tests them with ``ev.get(...)`` truthiness and iterates
        # ``ev.get("produced", [])``, so adding empty values would be a change.
        if self.path:
            payload["path"] = self.path
        if self.produced:
            payload["produced"] = list(self.produced)
        return payload


# --------------------------------------------------------------------------- #
# Side-channel events (plan, notices, output folder).
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PlanUpdatedEvent(AgentEvent):
    """The agent published a new version of its step checklist (full list)."""

    EVENT_TYPE: ClassVar[str] = "plan_set"
    steps: Tuple[PlanStep, ...] = ()

    def __post_init__(self) -> None:
        """Đóng băng danh sách bước kế hoạch thành tuple."""
        object.__setattr__(self, "steps", tuple(self.steps or ()))

    def _payload(self) -> Dict[str, Any]:
        """``{steps}`` — cả danh sách bước, vì agent gửi lại trọn kế hoạch mỗi lần cập nhật."""
        return {"steps": [s.to_dict() for s in self.steps]}


@dataclass(frozen=True)
class NoticeEvent(AgentEvent):
    """An aside outside the model's own answer.

    Three sources today: context auto-compaction (info), a blocked
    security check (warning), and attachment reading progress (progress).
    """

    EVENT_TYPE: ClassVar[str] = "notice"
    text: str = ""
    level: str = NOTICE_INFO

    def _payload(self) -> Dict[str, Any]:
        """``{level, text}`` — một dòng thông báo (info / cảnh báo / tiến độ)."""
        return {"level": self.level, "text": self.text}


@dataclass(frozen=True)
class OutputsAddedEvent(AgentEvent):
    """Deliverables appeared in the turn's output folder."""

    EVENT_TYPE: ClassVar[str] = "outputs_added"
    paths: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Đóng băng danh sách đường dẫn thành tuple."""
        object.__setattr__(self, "paths", _as_str_tuple(self.paths))

    def _payload(self) -> Dict[str, Any]:
        """``{paths}`` — các tệp vừa sinh ra, đổi về list cho JSON hoá được."""
        return {"paths": list(self.paths)}


@dataclass(frozen=True)
class OutputsRemovedEvent(AgentEvent):
    """Intermediate/generator files were cleaned up — drop them from Output."""

    EVENT_TYPE: ClassVar[str] = "outputs_removed"
    paths: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Đóng băng danh sách đường dẫn thành tuple."""
        object.__setattr__(self, "paths", _as_str_tuple(self.paths))

    def _payload(self) -> Dict[str, Any]:
        """``{paths}`` — các tệp trung gian vừa được dọn."""
        return {"paths": list(self.paths)}


@dataclass(frozen=True)
class HistoryReadyEvent(AgentEvent):
    """The turn's conversation now exists on disk and can be opened.

    Emitted by the unattended (Schedule Task) path so the scheduler refreshes
    History only once the session is really there.
    """

    EVENT_TYPE: ClassVar[str] = "history_ready"
    session_id: str = ""

    def _payload(self) -> Dict[str, Any]:
        """``{session_id}`` — lịch sử đã ghi xong, kèm id phiên để mở lại."""
        return {"session_id": self.session_id}


# --------------------------------------------------------------------------- #
# Turn-level events introduced by R04 (no legacy consumer yet).
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class TurnCompletedEvent(AgentEvent):
    """The whole turn ended — exactly once per turn.

    Nothing consumes ``"turn_completed"`` yet: the widget's ``if/elif`` chain
    simply has no branch for it, so emitting it is inert until R08 wires a
    renderer. It exists now because the state it carries (was the turn
    cancelled? did it hit the step ceiling?) is currently reconstructed by the
    UI from side effects rather than being told to it.
    """

    EVENT_TYPE: ClassVar[str] = "turn_completed"
    final_text: str = ""
    steps_used: int = 0
    cancelled: bool = False
    budget_exhausted: bool = False      # stopped at effective_max_steps

    def _payload(self) -> Dict[str, Any]:
        """``{final_text, steps_used, cancelled, budget_exhausted}`` — tổng kết cả lượt."""
        return {"final_text": self.final_text, "steps_used": self.steps_used,
                "cancelled": self.cancelled, "budget_exhausted": self.budget_exhausted}


@dataclass(frozen=True)
class ErrorEvent(AgentEvent):
    """The turn hit an error.

    ``recoverable`` separates "this turn is over" from "something failed but the
    loop carried on" — a distinction the current code loses, because both end up
    as a bare ``except Exception`` plus a text bubble.
    """

    EVENT_TYPE: ClassVar[str] = "error"
    message: str = ""
    recoverable: bool = False

    def _payload(self) -> Dict[str, Any]:
        """``{message, recoverable}`` — lỗi kèm cờ có thể thử lại hay không."""
        return {"message": self.message, "recoverable": self.recoverable}


__all__ = [
    "NOTICE_INFO", "NOTICE_WARNING", "NOTICE_PROGRESS",
    "AgentEvent", "ToolPreview", "PlanStep",
    "TextChunkEvent", "ReasoningChunkEvent", "AssistantMessageCompletedEvent",
    "ToolCallStartedEvent", "ToolOutputChunkEvent", "ToolCallFinishedEvent",
    "PlanUpdatedEvent", "NoticeEvent", "OutputsAddedEvent", "OutputsRemovedEvent",
    "HistoryReadyEvent", "TurnCompletedEvent", "ErrorEvent",
]
