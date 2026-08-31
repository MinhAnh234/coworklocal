"""Adapters that plug the existing routing engine into the application service.

:mod:`routing_application_service` is written against two narrow ports so it can
be unit-tested with plain fakes. This module supplies the real implementations —
the assessment/scoring engine in ``core/routing`` and the per-workspace mode
lookup on ``AppContext`` — and is therefore the ONLY file in
``application/model_routing/`` that knows those concrete types exist.

All engine imports are deferred into method bodies. Importing the routing stack
pulls in Pydantic models and the on-disk assessment store, and the UI must be
able to import this module during startup without paying that cost (the same
lazy-wiring reason ``state.py::AppContext.routing`` gives).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .routing_application_service import RoutingApplicationService
from .routing_models import RouteEvaluation, RoutingMode, RoutingRequest

logger = logging.getLogger("cowork_local.application.model_routing")


class CoreRoutingEngine:
    """:class:`RoutingDecisionPort` backed by ``core/routing/service.py``.

    Translates in both directions: application DTOs in, and the engine's
    ``RouteResult``/``SwitchDecision``/``TaskType`` flattened back out into a
    :class:`RouteEvaluation`, so no ``core.routing`` type ever escapes into the
    application service or the UI call sites.
    """

    def __init__(self, routing_service: Any) -> None:
        """Bọc ``core/routing/service.py`` vào cổng quyết định định tuyến."""
        self._routing_service = routing_service

    def evaluate(self, request: RoutingRequest, mode: RoutingMode) -> RouteEvaluation:
        """Rank candidates for this turn and report the engine's verdict."""
        from ...core.routing.models import TaskType, candidate_key

        result = self._routing_service.route(
            request.surface,
            request.prompt,
            request.current_provider,
            request.current_model,
            # The engine only knows off/auto/manual; FALLBACK was already mapped
            # to AUTO upstream so the value handed over here is always valid.
            mode_override=mode.value,
            required_capabilities=list(request.required_capabilities) or None,
            task_type=self._parse_task_type(request.task_type, TaskType),
        )

        decision = result.decision
        target = result.target()  # (provider, model_id) or None
        current_key = (
            candidate_key(request.current_provider, request.current_model)
            if request.current_model
            else ""
        )
        return RouteEvaluation(
            task_type=self._task_type_value(result.task_type),
            should_switch=bool(result.should_switch),
            target_provider=target[0] if target else None,
            target_model=target[1] if target else None,
            score_gain=float(getattr(decision, "score_gain", 0.0) or 0.0),
            reason=str(getattr(decision, "reason", "") or ""),
            current_is_usable=self._current_is_usable(result, current_key),
            decision=decision,
        )

    # -- translation helpers --------------------------------------------- #
    @staticmethod
    def _parse_task_type(raw: Optional[str], task_type_enum) -> Optional[Any]:
        """Coerce a task-type string to the engine's enum.

        ``None`` (the common case) means "let the engine classify the prompt".
        An unrecognised string is also downgraded to ``None`` rather than
        raising, so a stale value in a saved workspace cannot break a turn.
        """
        if raw is None:
            return None
        if isinstance(raw, task_type_enum):
            return raw
        try:
            return task_type_enum(str(raw).strip().lower())
        except ValueError:
            logger.warning("routing: unknown task type %r — classifying from the prompt", raw)
            return None

    @staticmethod
    def _task_type_value(task_type: Any) -> str:
        """The plain string form of the engine's task type enum."""
        return str(getattr(task_type, "value", task_type) or "")

    @staticmethod
    def _current_is_usable(result: Any, current_key: str) -> bool:
        """Whether the currently selected model can still serve this task.

        This is the signal FALLBACK mode acts on. A model is usable when the
        ranking scored it above zero; ``rank_models`` already drops candidates
        that are unavailable, lack a probe for this task type, or failed their
        last probe, so "absent from the ranking" is precisely "cannot serve it".

        With no ranking (routing off, or the engine's internal error path) or no
        current model, we answer True: absence of evidence must not trigger a
        surprise switch in a mode whose whole promise is not to surprise.
        """
        ranking = getattr(result, "ranking", None)
        if ranking is None or not current_key:
            return True
        try:
            return float(ranking.score_of(current_key)) > 0.0
        except Exception:  # noqa: BLE001 — defensive: never fail a turn on telemetry-ish data
            logger.debug("routing: could not score current model %r", current_key, exc_info=True)
            return True


class AppContextModeResolver:
    """:class:`ModeResolver` backed by the active workspace's settings.

    Reads through ``AppContext.project_routing_mode``, which already layers the
    workspace override on top of the global default — so per-workspace routing
    modes keep working unchanged now that the mode lookup moved out of the
    widgets.
    """

    def __init__(self, ctx: Any) -> None:
        """Đọc chế độ định tuyến từ ``AppContext``, để tầng application không phải biết
        hình dạng của context.
        """
        self._ctx = ctx

    def mode_for(self, surface: str) -> RoutingMode:
        """Effective mode for ``surface`` in the active workspace."""
        return RoutingMode.parse(self._ctx.project_routing_mode(surface))


def build_routing_application_service(ctx: Any) -> RoutingApplicationService:
    """The shared :class:`RoutingApplicationService` for this app context.

    Cached on the context (like ``AppContext.routing()`` caches the engine) so
    every surface talks to the same instance and a future stateful addition —
    per-surface cool-down, switch history — is shared rather than duplicated per
    widget. Falls back to a fresh instance if the context refuses attribute
    assignment, which keeps tests using lightweight stand-ins working.
    """
    cached = getattr(ctx, "_routing_app_service", None)
    if cached is not None:
        return cached

    service = RoutingApplicationService(
        CoreRoutingEngine(ctx.routing()),
        AppContextModeResolver(ctx),
        # Read at call time: the user can change the confirm timeout in Settings
        # between two turns and the next Manual dialog should honour it.
        confirm_timeout_sec=lambda: float(
            (ctx.config.routing or {}).get("confirm_timeout_sec", 60) or 60
        ),
    )
    try:
        ctx._routing_app_service = service
    except Exception:  # noqa: BLE001 — read-only/slotted stand-ins stay supported
        logger.debug("routing: could not cache the application service on the context", exc_info=True)
    return service


__all__ = [
    "AppContextModeResolver",
    "CoreRoutingEngine",
    "build_routing_application_service",
]
