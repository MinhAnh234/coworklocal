"""The immutable snapshot of ONE chat turn (R04-T01).

Today a turn's inputs live in a closure plus a 15-key ``ctx`` dict built inside
``ui/chat_panel.py::_start_turn``, and the worker thread reads the widget back
(``self._model``, ``self.title``, ``self.project_id``) while it runs. That is
the mechanism behind the whole class of "I changed the model mid-answer and the
running turn behaved oddly" reports: the turn has no snapshot of its own, so
every later click on the UI is visible to work already in flight.

:class:`ConversationExecutionRequest` is that missing snapshot. Everything the
runtime needs for one turn is captured once, on the UI thread, at submit time,
and then handed to code that runs on a worker thread. Frozen, so no caller —
widget or service — can retroactively change a decision the turn already acted
on.

Layer rules (see ``docs/architecture/ADR-001-layered-architecture.md``): this is
the domain layer, so standard library only. No PySide6, no ``requests``, no
filesystem access, and deliberately no import of ``core/*`` — a request only
*describes* a turn; running it is the application layer's job
(``application/conversations/``).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Separator between an instruction prefix (a ``/skill`` block, an ``/agent``
# persona) and the user's own request. Kept as a constant because the prefix is
# assembled in the presentation layer while the body is only known later on the
# worker thread — both halves must agree on the exact separator or the model
# sees a different prompt shape than it did before this refactor.
PREFIX_SEPARATOR = "\n\n---\n\n"


@dataclass(frozen=True)
class ConversationExecutionRequest:
    """Everything needed to execute one conversation turn.

    Frozen for the reason above; use :meth:`with_model` / :meth:`with_output_dir`
    to derive an adjusted copy rather than mutating one another thread may be
    reading.

    Note on depth: ``messages`` is a *shallow* snapshot (a tuple holding the
    same message dicts the caller passed). That matches the existing
    ``snapshot = list(self.messages)`` semantics in ``_start_turn`` exactly —
    the turn is protected from the history list being appended to or replaced,
    which is what actually happens between turns. Making it deep would silently
    change how ``_finalize_turn`` merges the turn's messages back, so the
    stronger guarantee is left to R04-T03 where that merge moves.
    """

    # -- identity ------------------------------------------------------- #
    turn_id: str                       # unique within a session ("t1", "t2", ...)
    session_id: str                    # the conversation this turn belongs to
    surface: str = "cowork"            # routing/mode key: "cowork" | "co4e" | "ai_edit"
    project_id: str = ""               # workspace the turn is confined to
    title: str = ""                    # conversation title; also names saved files

    # -- what the user asked -------------------------------------------- #
    # The typed request, already stripped of any ``/skill`` or ``/agent``
    # directive (those become ``instruction_prefix``).
    prompt: str = ""
    instruction_prefix: str = ""       # skill rules + agent persona for this turn
    # Prepended when the model/agent was switched mid-conversation, asking the
    # model to re-check the previous step before continuing. Invisible in the
    # chat bubble — it only travels in the payload sent to the provider.
    review_note: str = ""
    # Attachment PATHS, not their text: extracting a .docx can pip-install a
    # parser or shell out to LibreOffice, which must not run on the UI thread.
    # The runtime reads them later and passes the result to :meth:`user_content`.
    attachments: Tuple[str, ...] = ()
    # Conversation history as of submit time; the new user message is NOT part
    # of it (the runtime appends it once the body is composed).
    messages: Tuple[Dict[str, Any], ...] = ()

    # -- which model answers -------------------------------------------- #
    # Already resolved upstream: an Admin-agent pin, the tab's own picker, or a
    # routing override published by ``RoutingApplicationService`` (R03). The
    # runtime does not re-decide, so a switch cannot land mid-turn.
    provider_id: str = ""
    model: str = ""                    # "" = the provider's configured default

    # -- standing instructions ------------------------------------------ #
    project_context: str = ""          # Claude-Projects-style shared instructions
    session_notes: str = ""            # e.g. files this conversation already produced

    # -- tool scope and turn limits -------------------------------------- #
    # None = every enabled built-in tool. An explicit (possibly empty) tuple
    # restricts the ADVERTISED tools, which is how a "read-only" step is made
    # literally unable to write.
    allowed_tools: Optional[Tuple[str, ...]] = None
    max_steps: int = 30                # interactive cap
    completion_max_steps: int = 200    # runaway ceiling for run-to-completion work
    run_to_completion: bool = False    # Co4E flow steps need the higher ceiling
    enforce_rules: bool = True         # False for sandboxed Co4E runs
    gate_mode: str = "auto"            # "confirm" -> ask before run_command/install
    agent_role: str = "cowork"         # audit-log attribution ("cowork" | "task" | ...)

    # -- where its files go ---------------------------------------------- #
    output_dir: Optional[Path] = None       # this turn's isolated sandbox
    home_output_root: Optional[Path] = None  # conversation Output root to promote into

    # -- unattended execution (Schedule Task) ----------------------------- #
    unattended: bool = False           # no human watching; plan tracking is enforced
    timeout_sec: Optional[int] = None  # None = no wall-clock limit

    # Escape hatch for surface-specific data a future task needs to thread
    # through without another schema change (same role as
    # ``ProviderDescriptor.extras``).
    extras: Dict[str, Any] = field(default_factory=dict)

    # -- validation / normalisation --------------------------------------- #
    def __post_init__(self) -> None:
        """Reject unusable requests and freeze the mutable inputs.

        Validation lives here (not at the call site) so a request that exists is
        always safe to key by: the audit log, the History autosave and the
        per-turn output folder are all named from ``session_id``/``turn_id``.

        Normalisation matters just as much: the caller hands us the composer's
        own attachment LIST and the live history LIST, and both get cleared or
        appended to for the next turn. Copying them into tuples here is what
        actually makes the snapshot a snapshot. ``object.__setattr__`` is the
        standard way to do this in a frozen dataclass.
        """
        if not (self.turn_id or "").strip():
            raise ValueError("ConversationExecutionRequest.turn_id must not be empty")
        if not (self.session_id or "").strip():
            raise ValueError("ConversationExecutionRequest.session_id must not be empty")

        object.__setattr__(self, "attachments", tuple(self.attachments or ()))
        object.__setattr__(self, "messages", tuple(self.messages or ()))
        # None must survive: it means "no restriction", while an empty tuple
        # means "deny every built-in tool" — two very different turns.
        if self.allowed_tools is not None:
            object.__setattr__(self, "allowed_tools", tuple(self.allowed_tools))
        # Accept str paths so a call site holding a config value does not have to
        # wrap it; everything downstream can then assume Path.
        for name in ("output_dir", "home_output_root"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, Path):
                object.__setattr__(self, name, Path(value))

    # -- derived turn policy ---------------------------------------------- #
    @property
    def has_prompt(self) -> bool:
        """Whether the user actually typed something (an attachment-only turn
        legitimately has none). Mirrors ``RoutingRequest.has_prompt`` so both
        DTOs answer the "is there anything to work with?" question the same way.
        """
        return bool((self.prompt or "").strip())

    @property
    def effective_max_steps(self) -> int:
        """The tool-use budget for this turn.

        Run-to-completion work (a Co4E flow step whose single instruction may
        need many tool calls) gets the higher ceiling; interactive chat keeps the
        tight cap. Either way the turn still ends the moment the model stops
        calling tools — this is only the runaway limit.
        """
        return self.completion_max_steps if self.run_to_completion else self.max_steps

    @property
    def requires_permission_gate(self) -> bool:
        """Whether ``run_command``/``install_package`` must be approved first.

        Resolved by the caller (per-workspace Auto-run override, else the global
        "confirm before running commands" setting) and frozen here, so toggling
        the setting mid-turn cannot change the rules the turn started under.
        """
        return self.gate_mode == "confirm"

    # -- prompt composition ------------------------------------------------ #
    def user_content(self, body: str = "") -> str:
        """The exact ``content`` to send as this turn's user message.

        ``body`` is the request text AFTER attachment extraction, which happens
        on the worker thread — hence a method taking it as an argument rather
        than a stored field. The assembly order reproduces the closure in
        ``_start_turn`` byte for byte, because changing what a model receives is
        a behaviour change, not a refactor:

        1. session notes are appended after the body;
        2. the instruction prefix goes in front, behind a fixed separator;
        3. the model-switch review note goes ahead of everything.
        """
        content = body or ""
        notes = self.session_notes or ""
        if notes:
            # Guard the empty-body case (attachment-only turn) so the payload
            # never opens with a stray blank line.
            content = f"{content}\n\n{notes}" if content else notes
        prefix = self.instruction_prefix or ""
        if prefix:
            content = f"{prefix}{PREFIX_SEPARATOR}{content}"
        review = self.review_note or ""
        if review:
            content = f"{review}\n\n{content}"
        return content

    # -- derivation --------------------------------------------------------- #
    def with_model(self, provider_id: str = "", model: str = "") -> "ConversationExecutionRequest":
        """A copy pinned to another provider/model.

        Needed when a decision lands between building the request and running it
        (a routing override, an Admin-agent pin). Deriving a new request keeps
        the "one turn, one immutable snapshot" rule intact instead of patching a
        request another thread may already hold.
        """
        return replace(self, provider_id=provider_id or self.provider_id,
                       model=model or self.model)

    def with_output_dir(self, output_dir) -> "ConversationExecutionRequest":
        """A copy writing into a different sandbox — used when the caller only
        learns the per-turn folder after the request is assembled."""
        return replace(self, output_dir=output_dir)


__all__ = ["PREFIX_SEPARATOR", "ConversationExecutionRequest"]
