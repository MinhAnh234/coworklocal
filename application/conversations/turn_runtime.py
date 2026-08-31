"""The seams :mod:`conversation_application_service` runs a turn through (R04-T03).

Two Protocols and six callables — chosen deliberately, not by reflex. The
refactor plan forbids giving every class an interface, so a contract exists here
only where there is both a real ``core/*`` implementation AND a test double:

* :class:`ModelCallPort` — one provider round-trip *including* the app's
  existing context-overflow recovery, which is why the raw ``Provider.chat``
  signature is not enough.
* :class:`ToolRuntimePort` — the tool + output-folder runtime, kept as one
  cohesive object because every method operates on the same sandbox.

Everything else is a single function, so it is expressed as a callable type
rather than a class with one method (the same choice R03 made for
``ConfirmationCallback``). All of them are optional: a service built with none
of them still runs a plain chat turn, which is what keeps the unit tests short.

Layer rules (``docs/architecture/ADR-001-layered-architecture.md``): application
layer — pure Python. Nothing here imports PySide6, ``core.*``, ``providers.*``
or ``ui.*``; the concrete wiring lives in :mod:`core_runtime_adapter`.
"""

from __future__ import annotations

from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    runtime_checkable,
)

from ...domain.agents.agent_event import AgentEvent, ToolPreview

# The plan tool is special-cased by the loop: it drives the Plan panel and
# produces no chat bubble and no file. Named here so the check is not a bare
# string literal in the middle of the dispatch.
PLAN_TOOL = "update_plan"

# Tools that need approval before they run when the workspace is in confirm
# mode. R05 replaces this tuple with a real ``ToolPolicyGateway`` keyed on
# ToolCapability; until then it mirrors exactly what the runtime gates today.
GATED_TOOLS = ("run_command", "install_package")

# Shown when the user (or the workspace policy) rejects a proposed command. The
# exact string also becomes the tool message the model reads back, so it must
# stay stable.
REJECTED_OUTPUT = "Rejected by user."

# A reasoning model can answer with thinking only. The note is written into the
# assistant message itself, not merely emitted, so an unattended run does not
# read back an empty answer and report "(no output)".
REASONING_ONLY_NOTE = "*(model returned only its reasoning — try rephrasing)*"

# Emitted when the turn is stopped by its own safety ceiling rather than by the
# model finishing. Never silent: being cut off looks exactly like being done.
BUDGET_NOTE_TEMPLATE = (
    "\n\n⚠️ Reached the {steps}-step safety limit before the task signalled "
    "completion — stopping here. Re-run to continue if more work remains."
)


def combine_instructions(*blocks: Optional[str]) -> str:
    """Join the standing-instruction blocks of a turn, skipping the absent ones.

    A turn's instructions arrive as several independent blocks — the project's
    shared context, an Admin agent's persona, a skill's rules, the
    "this runs unattended" reminder — and each caller was joining them inline
    with its own ``f"{a}\\n\\n{b}" if a else b`` expression. Two call sites now
    need the same rule (the Cowork widget in R04-T04 and the task runner in
    R04-T05), which is the point at which it stops being an expression.

    Whitespace-only blocks count as absent: they would otherwise open the system
    prompt with a stray blank line.
    """
    return "\n\n".join(b.strip() for b in blocks if b and b.strip())


# --------------------------------------------------------------------------- #
# Callables.
# --------------------------------------------------------------------------- #
# Receives every typed event the turn produces. The caller decides what that
# means — render it, forward it as a legacy dict, autosave on it.
EventSink = Callable[[AgentEvent], None]

# True once the user has asked to stop. Polled between steps and between tool
# calls, the same cadence the current runtime uses.
CancelFn = Callable[[], bool]

# ``(prompt, attachment_paths) -> body``. Runs on the worker thread because
# extracting a .docx may pip-install a parser or call LibreOffice.
AttachmentReader = Callable[[str, Tuple[str, ...]], str]

# ``(messages, advertised_tool_names) -> None`` — inserts the system prompt and
# folds in skills, security rules and project instructions, in place. It needs
# the tool names because the system prompt gains an MS365 paragraph only when
# ms365 tools are actually present.
PromptPreparer = Callable[[List[Dict[str, Any]], Tuple[str, ...]], None]

# Reviews the assembled request; raises to refuse the turn outright.
PromptGuard = Callable[[List[Dict[str, Any]]], None]

# Reviews one proposed tool call; raises to refuse it.
CommandGuard = Callable[[str, Dict[str, Any]], None]

# ``(messages, cancel) -> None``. Summarises old turns in place when the
# conversation nears the model's context budget; a no-op when compaction is off
# or the conversation is short. It takes the cancel signal because compacting
# calls the model itself, so Stop has to reach it too.
ContextCompactor = Callable[[List[Dict[str, Any]], "CancelFn"], None]

# ``(action) -> approved``. Blocks the worker thread while a human decides.
PermissionRequest = Callable[[Dict[str, Any]], bool]


# --------------------------------------------------------------------------- #
# Ports.
# --------------------------------------------------------------------------- #
@runtime_checkable
class ModelCallPort(Protocol):
    """One call to the model, with the app's retry/recovery behaviour applied."""

    def call(self, messages: List[Dict[str, Any]], tools: Sequence[Any],
             on_text: Optional[Callable[[str], None]] = None,
             on_reasoning: Optional[Callable[[str], None]] = None,
             cancel: Optional[CancelFn] = None) -> Dict[str, Any]:
        """Return the canonical assistant message (content plus tool calls)."""


@runtime_checkable
class ToolRuntimePort(Protocol):
    """The tools a turn may call, and the folder its files land in."""

    def specs(self, allowed_tools: Optional[Sequence[str]] = None) -> Sequence[Any]:
        """Tool specs to advertise to the model, already filtered.

        Returns opaque objects (the provider layer's ``ToolSpec``); the service
        only ever reads ``.name`` off them, which is what keeps this layer free
        of a provider import.
        """

    def preview(self, name: str, args: Dict[str, Any]) -> Optional[ToolPreview]:
        """Human-readable description of a call that is about to run."""

    def execute(self, name: str, args: Dict[str, Any],
                on_output: Optional[Callable[[str], None]] = None,
                cancel: Optional[CancelFn] = None) -> Dict[str, Any]:
        """Run one tool call.

        Returns the runtime's own result mapping: ``ok``, ``output``, optionally
        ``path``/``produced`` for files it created, and ``plan_steps`` for the
        plan tool.
        """

    def snapshot(self) -> Any:
        """Opaque record of the output folder before the turn started."""

    def finalize(self, before: Any, cancelled: bool = False
                 ) -> Tuple[Sequence[str], Sequence[str]]:
        """Tidy the output folder; return ``(removed_paths, added_paths)``.

        Not read-only — it deletes the scratch sandbox and flattens sub-folders —
        so the service only calls it for a turn that actually started.
        """


__all__ = [
    "PLAN_TOOL", "GATED_TOOLS", "REJECTED_OUTPUT", "REASONING_ONLY_NOTE",
    "BUDGET_NOTE_TEMPLATE", "combine_instructions",
    "EventSink", "CancelFn", "AttachmentReader", "PromptPreparer", "PromptGuard",
    "CommandGuard", "ContextCompactor", "PermissionRequest",
    "ModelCallPort", "ToolRuntimePort",
]
