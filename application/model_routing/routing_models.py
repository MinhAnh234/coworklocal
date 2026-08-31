"""Pure-Python DTOs exchanged with :mod:`routing_application_service`.

These types are the vocabulary the chat surfaces (Cowork chat, Co4E, AI-Edit)
now speak instead of each re-deriving routing state from raw config lookups and
``core/routing`` internals.

Layer rules (``docs/architecture/ADR-001-layered-architecture.md``): application
code is 100% pure Python. Nothing here imports PySide6, and nothing here imports
``core.routing`` either — the concrete routing engine is reached only through
the adapter in :mod:`core_routing_adapter`, which keeps this module trivially
testable with plain fakes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Tuple


class RoutingMode(str, Enum):
    """The four routing behaviours a surface can be in (R03-T03).

    ``OFF``/``AUTO``/``MANUAL`` map 1:1 onto the existing per-surface toggle and
    onto ``core/routing/models.py::SwitchMode``. ``FALLBACK`` is new and
    deliberately NOT an optimisation mode: it keeps whatever model the user
    chose and only re-routes when that model cannot serve the turn, which is the
    behaviour a resilience-minded workspace wants (never surprise me, but never
    leave me stuck either).
    """

    OFF = "off"
    AUTO = "auto"
    MANUAL = "manual"
    FALLBACK = "fallback"

    @classmethod
    def parse(cls, raw: Any, default: "RoutingMode" = None) -> "RoutingMode":
        """Best-effort coercion from config/UI strings.

        Routing must never break a turn, so an unrecognised value degrades to
        ``default`` (``OFF`` unless told otherwise) instead of raising — the same
        defensive posture ``config.routing_mode_for`` already takes.
        """
        fallback = default if default is not None else cls.OFF
        if isinstance(raw, cls):
            return raw
        try:
            return cls(str(raw or "").strip().lower())
        except ValueError:
            return fallback


@dataclass(frozen=True)
class RoutingRequest:
    """Everything needed to decide how ONE turn should be routed.

    Frozen: the request is captured from live UI state (the selected model, the
    typed prompt) and then handed to code that may run on a worker thread. An
    immutable snapshot means the user changing the model picker mid-turn cannot
    retroactively alter the decision that was already made — the same rationale
    behind R04's ``ConversationExecutionRequest``.
    """

    surface: str                       # "cowork" | "co4e" | "ai_edit" | ...
    prompt: str                        # the user's text; drives task classification
    current_provider: str              # provider the surface would use as-is
    current_model: str = ""            # model the surface would use ("" = provider default)
    mode: Optional[RoutingMode] = None  # explicit override; None -> resolve per surface
    # Pre-classified task type ("coding", "qa", ...). AI-Edit always knows its
    # turns are coding work, so it pins this and skips prompt classification.
    task_type: Optional[str] = None
    required_capabilities: Tuple[str, ...] = ()   # e.g. ("vision",)

    @property
    def has_prompt(self) -> bool:
        """Whether there is anything to classify. An empty prompt cannot be
        routed meaningfully, so every surface short-circuits on it."""
        return bool((self.prompt or "").strip())


@dataclass(frozen=True)
class RouteEvaluation:
    """A routing engine's verdict, normalised away from ``core/routing`` types.

    The adapter flattens ``RouteResult``/``SwitchDecision`` into these plain
    fields so the application service never touches Pydantic models or enums
    owned by another layer. ``decision`` still carries the original object
    because the Manual-mode confirm dialog renders its ``reason``.
    """

    task_type: str
    should_switch: bool
    target_provider: Optional[str] = None
    target_model: Optional[str] = None
    score_gain: float = 0.0
    reason: str = ""
    # False when the currently selected model is not a usable candidate for this
    # task (unranked, unavailable, or failed its last probe) — the single signal
    # FALLBACK mode acts on.
    current_is_usable: bool = True
    decision: Any = None               # original SwitchDecision, for the UI dialog

    @property
    def has_target(self) -> bool:
        """A switch is only actionable when the engine named a model to move to."""
        return bool(self.target_model or self.target_provider)


@dataclass(frozen=True)
class RoutingOutcome:
    """What the calling surface should actually do for this turn.

    A surface needs exactly three things from routing — "which provider/model do
    I build?", "do I tell the user?" and "was I told to stand down?" — so those
    are the fields here, and nothing else. ``provider``/``model`` are ``None``
    when the surface should keep its own selection untouched.
    """

    mode: RoutingMode
    switched: bool = False
    provider: Optional[str] = None
    model: Optional[str] = None
    task_type: str = ""
    score_gain: float = 0.0
    reason: str = ""
    # True when Manual mode proposed a switch and the user declined or the
    # confirmation timed out. Distinct from "no switch proposed" so a surface
    # can tell "routing had nothing to offer" from "the user said no".
    declined: bool = False
    decision: Any = field(default=None, repr=False)

    @property
    def should_notify(self) -> bool:
        """Whether the surface should post the "switched model" status bubble.
        Only an executed switch is worth interrupting the transcript for."""
        return self.switched

    @classmethod
    def keep_current(
        cls,
        mode: RoutingMode,
        *,
        reason: str = "",
        task_type: str = "",
        declined: bool = False,
        decision: Any = None,
    ) -> "RoutingOutcome":
        """The no-change outcome — the single constructor for every path that
        leaves the surface's own model selection in place (routing off, empty
        prompt, no better candidate, user declined, internal error)."""
        return cls(
            mode=mode, switched=False, provider=None, model=None,
            task_type=task_type, reason=reason, declined=declined, decision=decision,
        )


__all__ = ["RoutingMode", "RoutingRequest", "RouteEvaluation", "RoutingOutcome"]
