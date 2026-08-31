"""The turn lifecycle, once, in pure Python (R04-T03).

Extracted from ``core/chat_agent.py::run_cowork``, whose 260-line body mixed the
lifecycle (compose the prompt, call the model, dispatch tools, respect the step
ceiling, tidy the sandbox) with the concrete machinery that does each of those
things. The lifecycle is the part with rules worth testing — and the part that
was untestable, because reaching it meant standing up a Qt widget and a worker
thread.

Here it is a plain object driven through the seams in :mod:`turn_runtime`, so a
test states a rule ("the guard runs before the model", "a rejected command never
executes") in three lines. ``core/chat_agent.py`` keeps its signature and
delegates, and the presentation layer keeps receiving the same events via the
legacy codec, so nothing downstream had to change with it.

Behavioural contract: this is a faithful port, not an improvement pass. Where
the original had a quirk (the step-ceiling note only merges into the answer when
the last message is the assistant's), the quirk is preserved and commented —
changing what a user sees belongs in its own change, not smuggled into a move.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from ...domain.agents.agent_event import (
    AssistantMessageCompletedEvent,
    ErrorEvent,
    OutputsAddedEvent,
    OutputsRemovedEvent,
    PlanStep,
    PlanUpdatedEvent,
    ReasoningChunkEvent,
    TextChunkEvent,
    ToolCallFinishedEvent,
    ToolCallStartedEvent,
    ToolOutputChunkEvent,
)
from ...domain.agents.agent_result import AgentResult
from ...domain.agents.conversation_execution_request import ConversationExecutionRequest
from .turn_runtime import (
    BUDGET_NOTE_TEMPLATE,
    GATED_TOOLS,
    PLAN_TOOL,
    REASONING_ONLY_NOTE,
    REJECTED_OUTPUT,
    AttachmentReader,
    CancelFn,
    CommandGuard,
    ContextCompactor,
    EventSink,
    ModelCallPort,
    PermissionRequest,
    PromptGuard,
    PromptPreparer,
    ToolRuntimePort,
)

logger = logging.getLogger("cowork_local.application.conversations")


class ConversationApplicationService:
    """Runs one :class:`ConversationExecutionRequest` to completion."""

    def __init__(
        self,
        model: ModelCallPort,
        tools: ToolRuntimePort,
        *,
        prepare_prompt: Optional[PromptPreparer] = None,
        prompt_guard: Optional[PromptGuard] = None,
        command_guard: Optional[CommandGuard] = None,
        compact: Optional[ContextCompactor] = None,
        permission_request: Optional[PermissionRequest] = None,
        attachment_reader: Optional[AttachmentReader] = None,
    ) -> None:
        """Nhận vào các cổng (port) thay vì tự dựng phụ thuộc.

        ``model`` và ``tools`` bắt buộc; mọi thứ còn lại là tuỳ chọn và để None thì
        bỏ qua bước đó. Nhờ vậy test dựng được service với đúng phần nó cần kiểm,
        không phải dựng cả provider thật lẫn sandbox.
        """
        self._model = model
        self._tools = tools
        # Every hook is optional so the service degrades to a plain chat turn.
        # That is not only a test convenience: a headless caller legitimately has
        # no guards (``security_config=None`` today) and no permission dialog.
        self._prepare_prompt = prepare_prompt
        self._prompt_guard = prompt_guard
        self._command_guard = command_guard
        self._compact = compact
        self._permission_request = permission_request
        self._attachment_reader = attachment_reader

    # -- public API ------------------------------------------------------ #
    def execute(self, request: ConversationExecutionRequest, sink: EventSink,
                cancel: Optional[CancelFn] = None,
                messages: Optional[List[Dict[str, Any]]] = None) -> AgentResult:
        """Run the turn, streaming events to ``sink``, and report the outcome.

        ``messages``, when given, is a working list the caller already built —
        it MUST already end with this turn's user message, and the service
        appends into that very object instead of composing its own. The Cowork
        widget needs this: it hands out the same list to
        ``_reattach_running_turn``, which replays the steps done so far while the
        worker is still appending, and to ``_finalize_turn``, which slices it by
        the pre-turn snapshot length. A private list would break both silently.
        Passing ``None`` (every headless caller) lets the service compose the
        list from the request, which is the mode the rest of this class assumes.

        Raises whatever the runtime raises (a blocked prompt, a dead gateway):
        the caller already has a failure path for that — ``AgentWorker.failed``
        in the UI, the artifact writer in Schedule Task — and swallowing the
        exception here would silently turn a failed turn into an empty answer.
        An :class:`ErrorEvent` is emitted first so subscribers see the failure
        on the same stream as everything else.
        """
        cancel = cancel or (lambda: False)

        # -- pre-flight. Runs BEFORE the output snapshot, so a turn refused here
        #    leaves the output folder completely untouched (tidying is not a
        #    read-only operation — see ToolRuntimePort.finalize).
        try:
            # The caller's list is used by reference on purpose (see above); only
            # the self-composed path may build a fresh one.
            working = messages if messages is not None else self._compose_messages(request)
            tools = list(self._tools.specs(request.allowed_tools))
            if self._prepare_prompt is not None:
                self._prepare_prompt(working, tuple(getattr(t, "name", "") for t in tools))
            if request.enforce_rules and self._prompt_guard is not None:
                self._prompt_guard(working)
        except Exception as exc:  # noqa: BLE001 — reported, then re-raised as-is
            sink(ErrorEvent(message=str(exc)))
            raise

        before = self._tools.snapshot()
        steps_used = 0
        plan_steps: Tuple[PlanStep, ...] = ()
        completed_naturally = False
        try:
            for _ in range(request.effective_max_steps):
                if cancel():
                    break
                # Auto-compress when nearing the model's context budget; a no-op
                # when off or when the conversation is still short.
                if self._compact is not None:
                    self._compact(working, cancel)

                assistant = self._model.call(
                    working, tools,
                    on_text=lambda piece: sink(TextChunkEvent(delta=piece)),
                    on_reasoning=lambda piece: sink(ReasoningChunkEvent(delta=piece)),
                    cancel=cancel,
                )
                working.append(assistant)
                steps_used += 1
                tool_calls = assistant.get("tool_calls") or []

                if not tool_calls and not (assistant.get("content") or "").strip():
                    # Written into the message, not just emitted, so the stored
                    # conversation never ends on a blank assistant turn.
                    assistant["content"] = REASONING_ONLY_NOTE
                    sink(TextChunkEvent(delta=REASONING_ONLY_NOTE))
                sink(AssistantMessageCompletedEvent(content=assistant.get("content", "")))

                if not tool_calls:
                    completed_naturally = True
                    break

                for call in tool_calls:
                    if cancel():
                        break
                    tool_message, steps = self._dispatch(request, call, sink, cancel)
                    working.append(tool_message)
                    if steps is not None:
                        plan_steps = steps

            if not completed_naturally and not cancel():
                self._announce_budget_exhausted(request, working, sink)
        except Exception as exc:  # noqa: BLE001 — reported, then re-raised as-is
            sink(ErrorEvent(message=str(exc)))
            raise
        finally:
            # Always tidy: the sandbox and generator scripts must not survive a
            # turn that stopped abruptly. Runs on success, cancel and failure.
            self._finalize_outputs(before, sink, cancelled=cancel())

        result = AgentResult(
            messages=working, steps_used=steps_used, cancelled=cancel(),
            budget_exhausted=not completed_naturally and not cancel(),
            plan_steps=plan_steps,
        )
        sink(result.to_turn_completed_event())
        return result

    # -- internals ------------------------------------------------------- #
    def _compose_messages(self, request: ConversationExecutionRequest) -> List[Dict[str, Any]]:
        """History snapshot plus this turn's user message.

        The attachment text is read HERE rather than when the request was built,
        because extraction is slow enough to freeze the UI thread; the request
        deliberately carries paths only.
        """
        body = request.prompt
        if self._attachment_reader is not None:
            body = self._attachment_reader(request.prompt, request.attachments)
        messages = [dict(m) for m in request.messages]
        messages.append({"role": "user", "content": request.user_content(body)})
        return messages

    def _dispatch(self, request: ConversationExecutionRequest, call: Dict[str, Any],
                  sink: EventSink, cancel: CancelFn
                  ) -> Tuple[Dict[str, Any], Optional[Tuple[PlanStep, ...]]]:
        """Run one tool call.

        Returns ``(tool_message, plan_steps)`` — the message to append to the
        conversation, and the new checklist when this call was the plan tool
        (``None`` otherwise, so the caller can tell "no change" from "empty
        plan").
        """
        call_id = str(call.get("id", ""))
        name = str(call.get("name", ""))
        args = call.get("arguments") or {}

        # The plan tool is invisible in the transcript: it updates the Plan panel
        # and nothing else, so it skips preview, guard and gate entirely.
        if name == PLAN_TOOL:
            outcome = self._tools.execute(name, args, on_output=None, cancel=cancel)
            steps = tuple(outcome.get("plan_steps") or ())
            sink(PlanUpdatedEvent(steps=steps))
            return self._tool_message(call_id, name, outcome.get("output", "")), steps

        # Announce first: the user sees the code/command about to run before the
        # guard or the approval dialog interrupts them, which is the whole point
        # of showing the step CLI-style.
        preview = self._tools.preview(name, args)
        sink(ToolCallStartedEvent(call_id=call_id, name=name, arguments=dict(args),
                                  preview=preview))

        if request.enforce_rules and self._command_guard is not None:
            self._command_guard(name, args)

        if not self._approved(request, name, args, preview, sink, call_id):
            return self._tool_message(call_id, name, REJECTED_OUTPUT), None

        outcome = self._tools.execute(
            name, args,
            on_output=lambda piece: sink(ToolOutputChunkEvent(
                call_id=call_id, name=name, delta=piece)),
            cancel=cancel,
        )
        sink(ToolCallFinishedEvent(
            call_id=call_id, name=name, ok=bool(outcome.get("ok", False)),
            output=str(outcome.get("output", "")), path=str(outcome.get("path", "") or ""),
            produced=outcome.get("produced") or (),
        ))
        return self._tool_message(call_id, name, outcome.get("output", "")), None

    def _approved(self, request: ConversationExecutionRequest, name: str,
                  args: Dict[str, Any], preview: Any, sink: EventSink,
                  call_id: str) -> bool:
        """Whether this call may run.

        Only command-shaped tools are gated, and only when the workspace asked
        to confirm them: file writes stay inside the turn's own sandbox, so
        prompting for those would be noise. A rejection is reported as a failed
        tool result — the model needs to read back that it was refused, or it
        will simply try the same call again.
        """
        if not request.requires_permission_gate or name not in GATED_TOOLS:
            return True
        if self._permission_request is None:
            # Confirm mode with nobody to ask: refusing is the safe direction,
            # since auto-running is exactly what confirm mode exists to prevent.
            logger.warning("turn: confirm mode without a permission callback — refusing %r", name)
            approved = False
        else:
            approved = bool(self._permission_request({
                "name": name, "args": args,
                "preview": preview.to_dict() if preview is not None else {},
            }))
        if not approved:
            sink(ToolCallFinishedEvent(call_id=call_id, name=name, ok=False,
                                       output=REJECTED_OUTPUT))
        return approved

    @staticmethod
    def _tool_message(call_id: str, name: str, output: Any) -> Dict[str, Any]:
        """The canonical ``role: tool`` message the model reads back."""
        return {"role": "tool", "tool_call_id": call_id, "name": name,
                "content": str(output or "")}

    @staticmethod
    def _announce_budget_exhausted(request: ConversationExecutionRequest,
                                   messages: List[Dict[str, Any]], sink: EventSink) -> None:
        """Report being cut off by the step ceiling.

        The note always reaches the transcript. It is merged into the stored
        answer only when the last message is the assistant's — which, when the
        ceiling is hit, it never is (the turn ends on a tool result). The branch
        is kept because it is what the current runtime does, and because it is
        the correct behaviour the day a caller ends the loop differently.
        """
        note = BUDGET_NOTE_TEMPLATE.format(steps=request.effective_max_steps)
        sink(TextChunkEvent(delta=note))
        if messages and messages[-1].get("role") == "assistant":
            messages[-1]["content"] = (messages[-1].get("content") or "") + note

    def _finalize_outputs(self, before: Any, sink: EventSink, cancelled: bool) -> None:
        """Tidy the output folder and report what moved.

        Failures are logged, never raised: this runs in a ``finally``, so an
        exception here would replace the turn's real error (or its success) with
        a housekeeping one.
        """
        try:
            removed, added = self._tools.finalize(before, cancelled=cancelled)
        except Exception:  # noqa: BLE001
            logger.exception("turn: tidying the output folder failed")
            return
        if removed:
            sink(OutputsRemovedEvent(paths=tuple(removed)))
        if added:
            sink(OutputsAddedEvent(paths=tuple(added)))


__all__ = ["ConversationApplicationService"]
