"""R03-T03/T04/T05 — the unified routing path over the REAL routing engine.

The unit tests drive ``RoutingApplicationService`` against fakes; this suite
proves the same service produces correct outcomes on top of the actual
``core/routing`` stack (classifier → assessment store → scorer → selector →
switch controller), which is what the three chat surfaces now call.

Offline by construction: a fake probe client answers benchmarks and judging, and
the assessment store is a temp file — no network, no Qt, no ``$HOME`` writes.
"""

from __future__ import annotations

import copy

import pytest
from cowork_local.application.model_routing import (
    AppContextModeResolver,
    CoreRoutingEngine,
    RoutingApplicationService,
    RoutingMode,
    RoutingRequest,
)
from cowork_local.config import DEFAULT_CONFIG, AppConfig
from cowork_local.core import projects as projects_mod
from cowork_local.core.routing.clients import CompletionResult
from cowork_local.core.routing.service import RoutingService
from cowork_local.core.routing.store import AssessmentStore
from cowork_local.state import AppContext

STRONG_ANSWER = "STRONG-DETAILED-CORRECT-ANSWER"
WEAK_ANSWER = "weak"


class FakeProbeClient:
    """Deterministic stand-in for the provider layer used during assessment.

    Mirrors ``tests/routing/test_service.py``'s client: benchmark prompts get a
    per-model canned answer, and judge prompts are graded by looking up that
    answer, so scores are stable and no model is ever really called.
    """

    def __init__(self, answers, quality) -> None:
        self.answers = answers
        self.quality = quality

    def complete(self, provider, model_id, messages) -> CompletionResult:
        text = messages[0]["content"]
        if "grading an AI assistant" in text:      # the judge rubric prompt
            score = 0.0
            for answer, value in self.quality.items():
                if answer and answer in text:
                    score = value
                    break
            return CompletionResult(text='{"score": %s}' % score)
        answer = self.answers.get((provider, model_id))
        if answer is None:
            return CompletionResult(error="unavailable")
        return CompletionResult(text=answer, tokens_out=len(answer) // 4)


@pytest.fixture()
def ctx(tmp_path, monkeypatch):
    """An AppContext with two assessable models and temp-only persistence."""
    # Keep workspace load/save off the developer's real ~/.cowork_local.
    monkeypatch.setattr(projects_mod, "PROJECTS_DIR", tmp_path / "projects")
    data = copy.deepcopy(DEFAULT_CONFIG)
    data["providers"] = {
        "anthropic": {"base_url": "x", "api_key": "x", "model": "strong-model"},
    }
    data["routing"]["candidates"] = [
        {"provider": "anthropic", "model_id": "strong-model", "tier": "powerful"},
        {"provider": "anthropic", "model_id": "weak-model", "tier": "fast"},
    ]
    data["routing"]["judge_provider"] = "anthropic"
    data["routing"]["judge_model"] = "judge-model"
    data["routing"]["policy"] = "quality"
    data["routing"]["min_score_gain"] = 0.05
    return AppContext(AppConfig(data=data, path=tmp_path / "config.json"))


@pytest.fixture()
def routing_service(ctx, tmp_path) -> RoutingService:
    """A real RoutingService with a populated assessment store."""
    client = FakeProbeClient(
        answers={
            ("anthropic", "strong-model"): STRONG_ANSWER,
            ("anthropic", "weak-model"): WEAK_ANSWER,
        },
        quality={STRONG_ANSWER: 0.95, WEAK_ANSWER: 0.35},
    )
    store = AssessmentStore(store_path=tmp_path / "assess.json",
                            history_dir=tmp_path / "history")
    service = RoutingService(ctx, store=store, client=client)
    service.reassess()          # populate real probe results + fit scores
    return service


@pytest.fixture()
def app_service(ctx, routing_service) -> RoutingApplicationService:
    """The application service wired exactly the way the UI wires it."""
    return RoutingApplicationService(
        CoreRoutingEngine(routing_service),
        AppContextModeResolver(ctx),
        confirm_timeout_sec=lambda: float(ctx.config.routing["confirm_timeout_sec"]),
    )


def coding_request(**overrides) -> RoutingRequest:
    """A coding turn currently pinned to the weaker model."""
    fields = dict(
        surface="cowork",
        prompt="Write a Python function to reverse a linked list",
        current_provider="anthropic",
        current_model="weak-model",
    )
    fields.update(overrides)
    return RoutingRequest(**fields)


# --------------------------------------------------------------------------- #
# Auto / Off / Manual over the real engine
# --------------------------------------------------------------------------- #
def test_auto_switches_to_the_better_assessed_model(app_service) -> None:
    """The real scorer must rank the strong model first and the service must
    hand that model back as this turn's override."""
    outcome = app_service.resolve(coding_request(mode=RoutingMode.AUTO))

    assert outcome.switched is True
    assert outcome.provider == "anthropic"
    assert outcome.model == "strong-model"
    assert outcome.task_type == "coding"     # classified from the prompt
    assert outcome.score_gain > 0


def test_off_keeps_the_pinned_model(app_service) -> None:
    """Off must not switch even when a clearly better model is assessed."""
    outcome = app_service.resolve(coding_request(mode=RoutingMode.OFF))

    assert outcome.switched is False
    assert outcome.provider is None


def test_manual_asks_before_switching(app_service) -> None:
    """The confirm callback receives the engine's own decision object, which is
    what ``ui/routing_toggle.py::confirm_switch`` renders."""
    seen: list = []

    outcome = app_service.resolve(
        coding_request(mode=RoutingMode.MANUAL),
        confirm=lambda decision, timeout: seen.append((decision, timeout)) or True,
    )

    assert outcome.switched is True
    decision, timeout = seen[0]
    assert decision.to_model == "anthropic/strong-model"
    assert decision.reason                       # human-readable explanation
    assert timeout == pytest.approx(60.0)        # from DEFAULT_CONFIG


def test_manual_decline_keeps_the_pinned_model(app_service) -> None:
    outcome = app_service.resolve(
        coding_request(mode=RoutingMode.MANUAL),
        confirm=lambda decision, timeout: False,
    )

    assert outcome.switched is False
    assert outcome.declined is True


def test_already_best_model_is_left_alone(app_service) -> None:
    """No pointless churn: being on the best model is not a switch."""
    outcome = app_service.resolve(
        coding_request(mode=RoutingMode.AUTO, current_model="strong-model"))

    assert outcome.switched is False


# --------------------------------------------------------------------------- #
# Fallback over the real engine
# --------------------------------------------------------------------------- #
def test_fallback_keeps_an_assessed_model_even_though_a_better_one_exists(app_service) -> None:
    """weak-model IS usable (it has a real probe score), so Fallback stays put
    where Auto would switch — the behavioural difference between the modes."""
    outcome = app_service.resolve(coding_request(mode=RoutingMode.FALLBACK))

    assert outcome.switched is False


def test_fallback_rescues_a_model_the_engine_cannot_serve(app_service) -> None:
    """A model absent from the ranking (never assessed / unavailable) is exactly
    the situation Fallback exists for."""
    outcome = app_service.resolve(
        coding_request(mode=RoutingMode.FALLBACK, current_model="ghost-model"))

    assert outcome.switched is True
    assert outcome.model == "strong-model"


# --------------------------------------------------------------------------- #
# Surface parity — the point of R03-T04/T05
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("surface", ["cowork", "co4e", "ai_edit"])
def test_every_surface_gets_the_same_decision(app_service, surface) -> None:
    """Chat, Co4E and AI-Edit used to hold three copies of this logic. Given the
    same inputs they must now be indistinguishable."""
    outcome = app_service.resolve(coding_request(surface=surface, mode=RoutingMode.AUTO))

    assert outcome.switched is True
    assert outcome.model == "strong-model"


def test_ai_edit_pinned_task_type_reaches_the_engine(app_service) -> None:
    """AI-Edit pins "coding" instead of classifying; the engine must honour it
    even when the instruction text reads like something else entirely."""
    outcome = app_service.resolve(coding_request(
        surface="ai_edit",
        prompt="Write a poem about the ocean",   # classifier would say "creative"
        task_type="coding",
        mode=RoutingMode.AUTO,
    ))

    assert outcome.task_type == "coding"


def test_mode_comes_from_the_workspace_when_not_pinned(ctx, app_service) -> None:
    """With no explicit mode, the service reads the per-workspace setting — the
    lookup the widgets used to do themselves."""
    ctx.config.data["routing"]["switch_mode"] = "auto"

    outcome = app_service.resolve(coding_request())

    assert outcome.mode is RoutingMode.AUTO
    assert outcome.switched is True


def test_fallback_mode_survives_a_round_trip_through_config(ctx) -> None:
    """The new mode must be persistable, or the toggle could never select it."""
    ctx.config.set_routing_mode_for("cowork", "fallback")

    assert ctx.config.routing_mode_for("cowork") == "fallback"
    assert ctx.project_routing_mode("cowork") == "fallback"


def test_unknown_persisted_mode_degrades_to_off(ctx) -> None:
    """A hand-edited config must not enable routing by accident."""
    ctx.config.routing["surface_modes"]["cowork"] = "turbo"

    assert ctx.config.routing_mode_for("cowork") == "off"
