"""Application model routing package: model route decisions and multi-provider balancing.

Public surface (R03-T03 — the single routing entry point every chat surface uses):

* :class:`RoutingApplicationService` — decides one turn's provider/model.
* :class:`RoutingRequest` / :class:`RoutingOutcome` — the immutable DTOs in and out.
* :class:`RoutingMode` — Off / Auto / Manual / Fallback.
* :func:`build_routing_application_service` — wires the service to a live
  ``AppContext`` (engine + per-workspace mode + confirm timeout).

Typical call site (see ``ui/chat_panel.py::_apply_routing``)::

    service = build_routing_application_service(self.ctx)
    outcome = service.resolve(
        RoutingRequest(surface="cowork", prompt=text,
                       current_provider=provider, current_model=model),
        confirm=lambda decision, timeout: confirm_switch(self, decision, timeout),
    )

Only ``core_routing_adapter`` touches ``core/routing``; the service and the DTOs
stay pure Python so the whole rule set is testable without Qt or the engine.
"""

from .core_routing_adapter import (
    AppContextModeResolver,
    CoreRoutingEngine,
    build_routing_application_service,
)
from .routing_application_service import (
    ConfirmationCallback,
    ModeResolver,
    RoutingApplicationService,
    RoutingDecisionPort,
)
from .routing_models import (
    RouteEvaluation,
    RoutingMode,
    RoutingOutcome,
    RoutingRequest,
)

__all__ = [
    "AppContextModeResolver",
    "ConfirmationCallback",
    "CoreRoutingEngine",
    "ModeResolver",
    "RouteEvaluation",
    "RoutingApplicationService",
    "RoutingDecisionPort",
    "RoutingMode",
    "RoutingOutcome",
    "RoutingRequest",
    "build_routing_application_service",
]
