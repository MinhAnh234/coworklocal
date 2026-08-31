"""The one place that decides how a turn is routed (R03-T03).

Before this service, ``ui/chat_panel.py#L638``, ``ui/co4e_tab.py`` and
``ui/folder_tab.py`` each carried their own copy of the same eight-step dance:
clear last turn's override → read the surface's mode → bail on "off" → call the
routing engine → check ``should_switch`` → resolve the target → show the Manual
confirm dialog → publish the override and a status line. Three copies meant
three chances to drift, and none of them could be tested without a Qt widget.

The dance now lives here, once, in pure Python:

* the routing engine is reached through :class:`RoutingDecisionPort`;
* the surface's Off/Auto/Manual/Fallback mode through :class:`ModeResolver`;
* the Manual-mode confirmation through a ``confirm`` callback supplied per call,
  so the Qt dialog stays in the presentation layer where it belongs.

Every failure path degrades to "keep the current model": a routing problem must
never be the reason a user cannot send a message.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, Protocol, runtime_checkable

from .routing_models import (
    RouteEvaluation,
    RoutingMode,
    RoutingOutcome,
    RoutingRequest,
)

logger = logging.getLogger("cowork_local.application.model_routing")

# Asks the user to approve a Manual-mode switch. Receives the underlying
# decision object (for rendering) plus the timeout in seconds; returns True to
# approve. Supplied by the caller so this module never imports a UI toolkit.
ConfirmationCallback = Callable[[Any, float], bool]


@runtime_checkable
class RoutingDecisionPort(Protocol):
    """The routing engine, as this service needs it.

    Narrowed to a single method on purpose: the concrete engine
    (``core/routing/service.py::RoutingService``) exposes assessment,
    persistence and scheduling too, none of which a turn-time decision needs.
    """

    def evaluate(self, request: RoutingRequest, mode: RoutingMode) -> RouteEvaluation:
        """Rank candidates for ``request`` and report whether to switch."""


@runtime_checkable
class ModeResolver(Protocol):
    """Resolves the effective routing mode for a surface.

    In the app this reads the active workspace's per-surface override with the
    global default behind it (``AppContext.project_routing_mode``); in tests it
    is a two-line stub.
    """

    def mode_for(self, surface: str) -> RoutingMode:
        """Effective mode for ``surface``."""


class RoutingApplicationService:
    """Turn-time routing decisions for every chat surface."""

    # Matches DEFAULT_CONFIG["routing"]["confirm_timeout_sec"]; used only when
    # no timeout provider is wired, so a bare service is still usable in tests.
    DEFAULT_CONFIRM_TIMEOUT_SEC = 60.0

    def __init__(
        self,
        decision_port: RoutingDecisionPort,
        mode_resolver: Optional[ModeResolver] = None,
        *,
        confirm_timeout_sec: Optional[Callable[[], float]] = None,
    ) -> None:
        """``mode_resolver`` để None thì mọi bề mặt đều coi như đang ở chế độ mặc định.
        ``confirm_timeout_sec`` là hàm chứ không phải số: người dùng đổi thiết lập
        giữa chừng thì lần hỏi sau phải theo giá trị mới.
        """
        self._decision_port = decision_port
        self._mode_resolver = mode_resolver
        # A callable rather than a number: the timeout lives in mutable config
        # the user can change in Settings between two turns.
        self._confirm_timeout_sec = confirm_timeout_sec

    # -- public API ------------------------------------------------------ #
    def resolve(
        self,
        request: RoutingRequest,
        confirm: Optional[ConfirmationCallback] = None,
    ) -> RoutingOutcome:
        """Decide this turn's provider/model.

        Returns a :class:`RoutingOutcome`; ``provider``/``model`` are ``None``
        whenever the surface should keep its own selection. Never raises — an
        unexpected failure is logged and reported as "keep current", because a
        broken assessment store must not block chatting.
        """
        mode = request.mode or self._resolve_mode(request.surface)
        try:
            return self._resolve_unguarded(request, mode, confirm)
        except Exception:  # noqa: BLE001 — routing must never break a turn
            logger.exception("routing.resolve failed — keeping the current model")
            return RoutingOutcome.keep_current(mode, reason="routing error — keeping current model")

    def confirm_timeout(self) -> float:
        """Seconds to wait for a Manual-mode confirmation.

        Falls back to the built-in default when the provider is missing or
        returns something unusable, so a corrupted config value cannot produce a
        zero-second dialog that instantly declines every switch.
        """
        if self._confirm_timeout_sec is None:
            return self.DEFAULT_CONFIRM_TIMEOUT_SEC
        try:
            value = float(self._confirm_timeout_sec())
        except (TypeError, ValueError):
            return self.DEFAULT_CONFIRM_TIMEOUT_SEC
        return value if value > 0 else self.DEFAULT_CONFIRM_TIMEOUT_SEC

    # -- internals ------------------------------------------------------- #
    def _resolve_mode(self, surface: str) -> RoutingMode:
        """The surface's configured mode, defaulting to OFF when unresolvable —
        routing stays opt-in, so "we don't know" must mean "don't switch"."""
        if self._mode_resolver is None:
            return RoutingMode.OFF
        try:
            return RoutingMode.parse(self._mode_resolver.mode_for(surface))
        except Exception:  # noqa: BLE001 — a config read must not break a turn
            logger.exception("routing: could not resolve mode for surface %r", surface)
            return RoutingMode.OFF

    def _resolve_unguarded(
        self,
        request: RoutingRequest,
        mode: RoutingMode,
        confirm: Optional[ConfirmationCallback],
    ) -> RoutingOutcome:
        """The decision flow proper; :meth:`resolve` owns the safety net."""
        # 1. Routing disabled, or nothing to classify -> keep the selection.
        if mode is RoutingMode.OFF:
            return RoutingOutcome.keep_current(mode, reason="routing off")
        if not request.has_prompt:
            return RoutingOutcome.keep_current(mode, reason="empty prompt — nothing to route")

        # 2. Ask the engine. FALLBACK is evaluated with AUTO's ranking because
        #    it needs the same candidate list; only the accept/reject rule below
        #    differs, so the engine stays unaware of the extra mode.
        engine_mode = RoutingMode.AUTO if mode is RoutingMode.FALLBACK else mode
        evaluation = self._decision_port.evaluate(request, engine_mode)

        # 3. Apply the mode's own accept rule to the engine's verdict.
        if mode is RoutingMode.FALLBACK:
            accepted, reason = self._fallback_verdict(evaluation)
        else:
            accepted, reason = evaluation.should_switch, evaluation.reason

        if not accepted or not evaluation.has_target:
            return RoutingOutcome.keep_current(
                mode,
                reason=reason or evaluation.reason,
                task_type=evaluation.task_type,
                decision=evaluation.decision,
            )

        # 4. Manual mode asks first; a decline or a timeout keeps the current
        #    model (and is reported as such, so the surface can tell the two
        #    cases apart from "nothing better was found").
        if mode is RoutingMode.MANUAL and not self._approved(evaluation, confirm):
            return RoutingOutcome.keep_current(
                mode,
                reason="switch declined by user or confirmation timed out",
                task_type=evaluation.task_type,
                declined=True,
                decision=evaluation.decision,
            )

        # 5. Publish the override for THIS turn only. The provider falls back to
        #    the request's current provider when the engine named a model but no
        #    provider (same-provider switch).
        return RoutingOutcome(
            mode=mode,
            switched=True,
            provider=evaluation.target_provider or request.current_provider,
            model=evaluation.target_model or "",
            task_type=evaluation.task_type,
            score_gain=evaluation.score_gain,
            reason=reason or evaluation.reason,
            decision=evaluation.decision,
        )

    @staticmethod
    def _fallback_verdict(evaluation: RouteEvaluation) -> tuple:
        """FALLBACK's accept rule: switch ONLY to rescue an unusable selection.

        The user's pinned model wins as long as it can serve the turn, even when
        a higher-scoring candidate exists — that is the whole point of the mode.
        A switch happens only when the current model is not a usable candidate
        (never assessed, marked unavailable, or its last probe failed) and the
        engine has something to move to.
        """
        if evaluation.current_is_usable:
            return False, "fallback mode — current model is healthy, keeping it"
        if not evaluation.has_target:
            return False, "fallback mode — current model unusable and no replacement available"
        return True, "fallback mode — current model unavailable, switching to the best alternative"

    def _approved(
        self,
        evaluation: RouteEvaluation,
        confirm: Optional[ConfirmationCallback],
    ) -> bool:
        """Run the Manual-mode confirmation callback.

        No callback means no way to ask, and silently switching in Manual mode
        would violate the mode's contract — so a missing callback is treated as
        "not approved". A callback that raises is treated the same way, since a
        broken dialog must not auto-approve a model change.
        """
        if confirm is None:
            logger.warning("routing: manual mode without a confirmation callback — keeping current model")
            return False
        try:
            return bool(confirm(evaluation.decision, self.confirm_timeout()))
        except Exception:  # noqa: BLE001
            logger.exception("routing: confirmation callback failed — keeping current model")
            return False


__all__ = [
    "ConfirmationCallback",
    "ModeResolver",
    "RoutingApplicationService",
    "RoutingDecisionPort",
]
