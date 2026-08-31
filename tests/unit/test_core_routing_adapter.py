"""Unit tests for the adapters that bridge the routing engine to the app service.

The integration suite covers the happy path over the real engine; this file pins
the translation edge cases that are hard to provoke there — malformed task
types, a missing ranking, and the service-caching contract.
"""

from __future__ import annotations

import pytest
from cowork_local.application.model_routing import (
    AppContextModeResolver,
    CoreRoutingEngine,
    RoutingApplicationService,
    RoutingMode,
    RoutingRequest,
)
from cowork_local.application.model_routing.core_routing_adapter import (
    build_routing_application_service,
)
from cowork_local.core.routing.models import SwitchDecision, SwitchMode, TaskType


class FakeRanking:
    """Just enough of ``selector.Ranking`` for the adapter's usability check."""

    def __init__(self, scores) -> None:
        self._scores = dict(scores)

    def score_of(self, key: str) -> float:
        return self._scores.get(key, 0.0)


class FakeRouteResult:
    """Stands in for ``core.routing.service.RouteResult``."""

    def __init__(self, decision, task_type=TaskType.CODING, ranking=None, target=None) -> None:
        self.decision = decision
        self.task_type = task_type
        self.ranking = ranking
        self._target = target

    @property
    def should_switch(self) -> bool:
        return self.decision.should_switch

    def target(self):
        return self._target


class FakeRoutingService:
    """Records the arguments the adapter forwards to the engine."""

    def __init__(self, result: FakeRouteResult) -> None:
        self.result = result
        self.calls: list = []

    def route(self, surface, prompt, current_provider, current_model, **kwargs):
        self.calls.append({"surface": surface, "prompt": prompt,
                           "current_provider": current_provider,
                           "current_model": current_model, **kwargs})
        return self.result


def make_decision(**overrides) -> SwitchDecision:
    fields = dict(
        should_switch=True,
        from_model="anthropic/weak-model",
        to_model="anthropic/strong-model",
        score_gain=0.3,
        reason="coding fit 0.9 > current 0.6",
        mode=SwitchMode.AUTO,
        task_type="coding",
    )
    fields.update(overrides)
    return SwitchDecision(**fields)


def make_request(**overrides) -> RoutingRequest:
    fields = dict(surface="cowork", prompt="Fix this bug",
                  current_provider="anthropic", current_model="weak-model")
    fields.update(overrides)
    return RoutingRequest(**fields)


# --------------------------------------------------------------------------- #
# CoreRoutingEngine translation
# --------------------------------------------------------------------------- #
def test_engine_flattens_the_route_result() -> None:
    """No ``core.routing`` type may leak past the adapter — the application
    service and the widgets only ever see plain fields."""
    service = FakeRoutingService(FakeRouteResult(
        make_decision(),
        ranking=FakeRanking({"anthropic/weak-model": 0.6}),
        target=("anthropic", "strong-model"),
    ))

    evaluation = CoreRoutingEngine(service).evaluate(make_request(), RoutingMode.AUTO)

    assert evaluation.task_type == "coding"          # str, not TaskType
    assert evaluation.should_switch is True
    assert evaluation.target_provider == "anthropic"
    assert evaluation.target_model == "strong-model"
    assert evaluation.score_gain == pytest.approx(0.3)
    assert evaluation.current_is_usable is True


def test_engine_forwards_the_mode_as_a_plain_string() -> None:
    """``RoutingService.route`` takes the mode as a string; handing it an enum
    would silently fall through to its "unknown mode -> off" branch."""
    service = FakeRoutingService(FakeRouteResult(make_decision(should_switch=False)))

    CoreRoutingEngine(service).evaluate(make_request(), RoutingMode.AUTO)

    assert service.calls[0]["mode_override"] == "auto"


def test_engine_reports_an_unranked_model_as_unusable() -> None:
    """This is the signal Fallback acts on: absent from the ranking means the
    selector already rejected it (unavailable / no probe / failed probe)."""
    service = FakeRoutingService(FakeRouteResult(
        make_decision(),
        ranking=FakeRanking({"anthropic/strong-model": 0.9}),   # current is absent
        target=("anthropic", "strong-model"),
    ))

    evaluation = CoreRoutingEngine(service).evaluate(make_request(), RoutingMode.AUTO)

    assert evaluation.current_is_usable is False


def test_engine_assumes_usable_without_a_ranking() -> None:
    """No ranking (routing off, or the engine's own error path) is absence of
    evidence — it must not trigger a surprise Fallback switch."""
    service = FakeRoutingService(FakeRouteResult(make_decision(), ranking=None))

    evaluation = CoreRoutingEngine(service).evaluate(make_request(), RoutingMode.AUTO)

    assert evaluation.current_is_usable is True


def test_engine_assumes_usable_when_the_ranking_misbehaves() -> None:
    """A broken ranking object must not fail the turn."""
    class BrokenRanking:
        def score_of(self, key):
            raise RuntimeError("corrupt ranking")

    service = FakeRoutingService(FakeRouteResult(make_decision(), ranking=BrokenRanking()))

    evaluation = CoreRoutingEngine(service).evaluate(make_request(), RoutingMode.AUTO)

    assert evaluation.current_is_usable is True


@pytest.mark.parametrize(
    "raw, expected",
    [("coding", TaskType.CODING), ("QA", TaskType.QA), (None, None), ("nonsense", None)],
)
def test_task_type_strings_are_coerced_or_dropped(raw, expected) -> None:
    """A pinned task type is honoured; an unknown one falls back to letting the
    engine classify the prompt rather than raising mid-turn."""
    service = FakeRoutingService(FakeRouteResult(make_decision(should_switch=False)))

    CoreRoutingEngine(service).evaluate(make_request(task_type=raw), RoutingMode.AUTO)

    assert service.calls[0]["task_type"] == expected


def test_required_capabilities_are_passed_as_a_list_or_none() -> None:
    """``rank_models`` filters on a list; an empty tuple must become None so it
    is treated as "no filter" rather than "require nothing, but filter"."""
    service = FakeRoutingService(FakeRouteResult(make_decision(should_switch=False)))
    engine = CoreRoutingEngine(service)

    engine.evaluate(make_request(required_capabilities=("vision",)), RoutingMode.AUTO)
    engine.evaluate(make_request(), RoutingMode.AUTO)

    assert service.calls[0]["required_capabilities"] == ["vision"]
    assert service.calls[1]["required_capabilities"] is None


# --------------------------------------------------------------------------- #
# Mode resolver + wiring
# --------------------------------------------------------------------------- #
def test_mode_resolver_reads_the_per_workspace_mode() -> None:
    """Per-workspace routing keeps working now that the lookup left the widgets."""
    class StubCtx:
        def project_routing_mode(self, surface):
            return "fallback" if surface == "co4e" else "off"

    resolver = AppContextModeResolver(StubCtx())

    assert resolver.mode_for("co4e") is RoutingMode.FALLBACK
    assert resolver.mode_for("cowork") is RoutingMode.OFF


def test_service_is_built_once_and_cached_on_the_context() -> None:
    """Every surface must share one instance, so future per-surface state (a
    cool-down, a switch history) is shared rather than duplicated per widget."""
    class StubCtx:
        def __init__(self):
            self.routing_calls = 0
            self.config = type("Cfg", (), {"routing": {"confirm_timeout_sec": 45}})()

        def routing(self):
            self.routing_calls += 1
            return FakeRoutingService(FakeRouteResult(make_decision(should_switch=False)))

        def project_routing_mode(self, surface):
            return "off"

    ctx = StubCtx()
    first = build_routing_application_service(ctx)
    second = build_routing_application_service(ctx)

    assert first is second
    assert ctx.routing_calls == 1
    assert isinstance(first, RoutingApplicationService)
    # The confirm timeout is read from config at call time, not frozen at build.
    assert first.confirm_timeout() == pytest.approx(45.0)
