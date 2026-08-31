"""What one finished turn produced (R04-T03).

The outcome of a turn is currently spread over three shapes: ``run_cowork``
returns the mutated message list, ``task_executors._run_agent`` returns a
``(answer_text, timed_out, incomplete_reason)`` tuple, and the UI reconstructs
the rest (did it get cancelled? did it hit the ceiling?) from side effects. Each
caller therefore knows a slightly different amount about the same turn.

:class:`AgentResult` is the single answer. Frozen, like the request that started
the turn, so a result cannot be edited into disagreeing with what actually
happened.

Layer rules (``docs/architecture/ADR-001-layered-architecture.md``): domain
layer — standard library plus sibling domain types only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from .agent_event import PlanStep, TurnCompletedEvent


@dataclass(frozen=True)
class AgentResult:
    """The outcome of one conversation turn."""

    # The conversation AFTER the turn (system prompt, history, the new user
    # message, every assistant reply and tool result).
    messages: Tuple[Dict[str, Any], ...] = ()
    steps_used: int = 0                    # provider calls this turn consumed
    cancelled: bool = False                # the user pressed Stop
    budget_exhausted: bool = False         # stopped at effective_max_steps
    # The agent's final checklist, so a caller can ask "did it really finish?"
    # (``core/plan.py::plan_incomplete_reason``) without replaying the events.
    plan_steps: Tuple[PlanStep, ...] = ()
    # Non-empty when the turn ended on a failure. A string rather than the
    # exception: the domain layer must not depend on where the error came from,
    # and the message is what every consumer (bubble, error.txt, audit) shows.
    error: str = ""

    def __post_init__(self) -> None:
        """Freeze the collections the runtime hands over.

        Both arrive as live lists that the caller keeps appending to after the
        turn (the UI merges messages back into its own history), so copying here
        is what keeps a result a record rather than a moving target.
        """
        object.__setattr__(self, "messages", tuple(self.messages or ()))
        object.__setattr__(self, "plan_steps", tuple(self.plan_steps or ()))

    @property
    def final_text(self) -> str:
        """The answer to show the user.

        Scans backwards for the last assistant message with real content, which
        is not the same as ``messages[-1]``: a turn that was cancelled or that
        ran out of steps mid-loop ends on a tool message, and a reasoning-only
        reply leaves a blank assistant message behind. Same rule as
        ``core/task_executors.py::_last_assistant_text``, which this replaces.
        """
        for message in reversed(self.messages):
            if message.get("role") == "assistant" and (message.get("content") or "").strip():
                return str(message["content"])
        return ""

    @property
    def ok(self) -> bool:
        """Whether the turn ran to a normal end.

        Hitting the step ceiling still counts as ok: the agent did work and
        produced an answer, it just was not allowed to keep going — which the
        transcript says in its own note rather than by failing the turn.
        """
        return not self.error and not self.cancelled

    def to_turn_completed_event(self) -> TurnCompletedEvent:
        """The end-of-turn event carrying this outcome to subscribers."""
        return TurnCompletedEvent(
            final_text=self.final_text, steps_used=self.steps_used,
            cancelled=self.cancelled, budget_exhausted=self.budget_exhausted,
        )


__all__ = ["AgentResult"]
