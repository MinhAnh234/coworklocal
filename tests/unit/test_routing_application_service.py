"""R03-T03 — unit tests for the unified routing decision rules.

The point of moving these rules out of the three chat widgets is that they can
now be exercised without Qt, without the assessment store and without a network:
the service talks to two narrow ports, so every mode is driven here by ~10-line
fakes. Each test names the behaviour a chat surface depends on.
"""

from __future__ import annotations

import pytest
from cowork_local.application.model_routing import (
    RouteEvaluation,
    RoutingApplicationService,
    RoutingMode,
    RoutingOutcome,
    RoutingRequest,
)


class FakeDecisionPort:
    """A routing engine that returns a canned verdict and records its input."""

    def __init__(self, evaluation: RouteEvaluation) -> None:
        self.evaluation = evaluation
        self.calls: list = []

    def evaluate(self, request: RoutingRequest, mode: RoutingMode) -> RouteEvaluation:
        self.calls.append((request, mode))
        return self.evaluation


class ExplodingDecisionPort:
    """An engine that fails — proves routing degrades instead of breaking a turn."""

    def evaluate(self, request: RoutingRequest, mode: RoutingMode) -> RouteEvaluation:
        raise RuntimeError("assessment store is corrupt")


class FakeModeResolver:
    """Per-surface mode lookup, standing in for the workspace settings."""

    def __init__(self, mode) -> None:
        self.mode = mode
        self.surfaces: list = []

    def mode_for(self, surface: str):
        self.surfaces.append(surface)
        return self.mode


def make_request(**overrides) -> RoutingRequest:
    """A representative turn: Cowork chat, currently on a cheap OpenAI model."""
    fields = dict(
        surface="cowork",
        prompt="Refactor this function",
        current_provider="codex",
        current_model="gpt-4o-mini",
    )
    fields.update(overrides)
    return RoutingRequest(**fields)


def switch_evaluation(**overrides) -> RouteEvaluation:
    """An engine verdict that proposes a switch to a better coding model."""
    fields = dict(
        task_type="coding",
        should_switch=True,
        target_provider="anthropic",
        target_model="claude-sonnet-4-6",
        score_gain=0.21,
        reason="coding fit 0.88 > current 0.67",
        decision=object(),
    )
    fields.update(overrides)
    return RouteEvaluation(**fields)


# --------------------------------------------------------------------------- #
# Off
# --------------------------------------------------------------------------- #
def test_off_mode_never_consults_the_engine() -> None:
    """Off must be free: no ranking, no store read, no decision at all."""
    port = FakeDecisionPort(switch_evaluation())
    service = RoutingApplicationService(port, FakeModeResolver(RoutingMode.OFF))

    outcome = service.resolve(make_request())

    assert outcome.switched is False
    assert outcome.provider is None and outcome.model is None
    assert port.calls == [], "Off mode must not call the routing engine"


def test_missing_mode_resolver_defaults_to_off() -> None:
    """Routing stays opt-in: with no way to read the mode, never switch."""
    port = FakeDecisionPort(switch_evaluation())
    service = RoutingApplicationService(port)

    outcome = service.resolve(make_request())

    assert outcome.mode is RoutingMode.OFF
    assert outcome.switched is False


def test_empty_prompt_is_not_routed() -> None:
    """An empty message carries no signal to classify, so the engine is skipped."""
    port = FakeDecisionPort(switch_evaluation())
    service = RoutingApplicationService(port, FakeModeResolver(RoutingMode.AUTO))

    outcome = service.resolve(make_request(prompt="   "))

    assert outcome.switched is False
    assert port.calls == []


# --------------------------------------------------------------------------- #
# Auto
# --------------------------------------------------------------------------- #
def test_auto_mode_switches_silently() -> None:
    """Auto applies the engine's verdict without asking the user."""
    port = FakeDecisionPort(switch_evaluation())
    service = RoutingApplicationService(port, FakeModeResolver(RoutingMode.AUTO))

    outcome = service.resolve(make_request())

    assert outcome.switched is True
    assert outcome.provider == "anthropic"
    assert outcome.model == "claude-sonnet-4-6"
    assert outcome.task_type == "coding"
    assert outcome.score_gain == pytest.approx(0.21)
    assert outcome.should_notify is True


def test_auto_mode_keeps_current_when_nothing_is_better() -> None:
    """No proposed switch means the surface's own selection is untouched."""
    port = FakeDecisionPort(switch_evaluation(
        should_switch=False, reason="current model is already best-fit"))
    service = RoutingApplicationService(port, FakeModeResolver(RoutingMode.AUTO))

    outcome = service.resolve(make_request())

    assert outcome.switched is False
    assert outcome.provider is None
    assert "already best-fit" in outcome.reason


def test_switch_without_a_target_is_ignored() -> None:
    """A verdict that says "switch" but names nothing is not actionable — a
    surface must never be handed an empty model id."""
    port = FakeDecisionPort(switch_evaluation(target_provider=None, target_model=None))
    service = RoutingApplicationService(port, FakeModeResolver(RoutingMode.AUTO))

    outcome = service.resolve(make_request())

    assert outcome.switched is False


def test_same_provider_switch_keeps_the_current_provider() -> None:
    """A model-only switch must not blank out the provider the surface uses."""
    port = FakeDecisionPort(switch_evaluation(target_provider=None, target_model="o3"))
    service = RoutingApplicationService(port, FakeModeResolver(RoutingMode.AUTO))

    outcome = service.resolve(make_request())

    assert outcome.switched is True
    assert outcome.provider == "codex"      # unchanged, from the request
    assert outcome.model == "o3"


# --------------------------------------------------------------------------- #
# Manual
# --------------------------------------------------------------------------- #
def test_manual_mode_switches_only_after_approval() -> None:
    """Manual's contract: ask first, then apply exactly what was approved."""
    port = FakeDecisionPort(switch_evaluation())
    service = RoutingApplicationService(
        port, FakeModeResolver(RoutingMode.MANUAL),
        confirm_timeout_sec=lambda: 30.0,
    )
    asked: list = []

    def confirm(decision, timeout):
        asked.append((decision, timeout))
        return True

    outcome = service.resolve(make_request(), confirm=confirm)

    assert outcome.switched is True
    assert len(asked) == 1
    # The configured timeout must reach the dialog, not a hard-coded default.
    assert asked[0][1] == pytest.approx(30.0)


def test_manual_mode_decline_is_reported_distinctly() -> None:
    """"The user said no" must be distinguishable from "nothing better found",
    so a surface can stay quiet in one case and explain itself in the other."""
    port = FakeDecisionPort(switch_evaluation())
    service = RoutingApplicationService(port, FakeModeResolver(RoutingMode.MANUAL))

    outcome = service.resolve(make_request(), confirm=lambda decision, timeout: False)

    assert outcome.switched is False
    assert outcome.declined is True


def test_manual_mode_without_a_callback_never_switches() -> None:
    """Silently switching in Manual mode would violate the mode's promise."""
    port = FakeDecisionPort(switch_evaluation())
    service = RoutingApplicationService(port, FakeModeResolver(RoutingMode.MANUAL))

    outcome = service.resolve(make_request(), confirm=None)

    assert outcome.switched is False


def test_manual_mode_treats_a_broken_dialog_as_a_decline() -> None:
    """A crashing confirm dialog must not auto-approve a model change."""
    port = FakeDecisionPort(switch_evaluation())
    service = RoutingApplicationService(port, FakeModeResolver(RoutingMode.MANUAL))

    def confirm(decision, timeout):
        raise RuntimeError("dialog blew up")

    outcome = service.resolve(make_request(), confirm=confirm)

    assert outcome.switched is False
    assert outcome.declined is True


# --------------------------------------------------------------------------- #
# Fallback
# --------------------------------------------------------------------------- #
def test_fallback_keeps_a_healthy_model_even_when_a_better_one_exists() -> None:
    """Fallback is a resilience mode, not an optimiser: a usable pinned model
    wins over a higher-scoring candidate."""
    port = FakeDecisionPort(switch_evaluation(current_is_usable=True))
    service = RoutingApplicationService(port, FakeModeResolver(RoutingMode.FALLBACK))

    outcome = service.resolve(make_request())

    assert outcome.switched is False
    assert "healthy" in outcome.reason


def test_fallback_switches_when_the_current_model_cannot_serve_the_turn() -> None:
    """The one case Fallback exists for: rescue an unusable selection."""
    port = FakeDecisionPort(switch_evaluation(current_is_usable=False))
    service = RoutingApplicationService(port, FakeModeResolver(RoutingMode.FALLBACK))

    outcome = service.resolve(make_request())

    assert outcome.switched is True
    assert outcome.model == "claude-sonnet-4-6"


def test_fallback_asks_the_engine_with_auto_semantics() -> None:
    """The engine only understands off/auto/manual, so Fallback must reach it as
    Auto — otherwise the engine would reject the unknown mode and rank nothing."""
    port = FakeDecisionPort(switch_evaluation(current_is_usable=False))
    service = RoutingApplicationService(port, FakeModeResolver(RoutingMode.FALLBACK))

    service.resolve(make_request())

    assert port.calls[0][1] is RoutingMode.AUTO


def test_fallback_never_confirms_with_the_user() -> None:
    """Rescuing an unusable model is not a proposal — it happens silently."""
    port = FakeDecisionPort(switch_evaluation(current_is_usable=False))
    service = RoutingApplicationService(port, FakeModeResolver(RoutingMode.FALLBACK))
    asked: list = []

    outcome = service.resolve(
        make_request(), confirm=lambda decision, timeout: asked.append(1) or True)

    assert outcome.switched is True
    assert asked == []


def test_fallback_with_no_replacement_keeps_current() -> None:
    """Nothing to fall back to means keep going with what we have and let the
    provider surface the real error, rather than blanking the model."""
    port = FakeDecisionPort(switch_evaluation(
        current_is_usable=False, target_provider=None, target_model=None))
    service = RoutingApplicationService(port, FakeModeResolver(RoutingMode.FALLBACK))

    outcome = service.resolve(make_request())

    assert outcome.switched is False


# --------------------------------------------------------------------------- #
# Robustness & plumbing
# --------------------------------------------------------------------------- #
def test_engine_failure_degrades_to_keep_current() -> None:
    """A broken assessment store must never stop a user sending a message."""
    service = RoutingApplicationService(
        ExplodingDecisionPort(), FakeModeResolver(RoutingMode.AUTO))

    outcome = service.resolve(make_request())

    assert isinstance(outcome, RoutingOutcome)
    assert outcome.switched is False
    assert "error" in outcome.reason


def test_mode_resolver_failure_degrades_to_off() -> None:
    """An unreadable workspace config must not enable routing by accident."""
    class BrokenResolver:
        def mode_for(self, surface):
            raise OSError("workspace file unreadable")

    port = FakeDecisionPort(switch_evaluation())
    service = RoutingApplicationService(port, BrokenResolver())

    outcome = service.resolve(make_request())

    assert outcome.mode is RoutingMode.OFF
    assert port.calls == []


def test_explicit_request_mode_overrides_the_resolver() -> None:
    """A surface may pin the mode for one turn (tests, replay, admin actions)."""
    resolver = FakeModeResolver(RoutingMode.OFF)
    port = FakeDecisionPort(switch_evaluation())
    service = RoutingApplicationService(port, resolver)

    outcome = service.resolve(make_request(mode=RoutingMode.AUTO))

    assert outcome.switched is True
    assert resolver.surfaces == [], "an explicit mode must skip the resolver"


def test_request_is_forwarded_to_the_engine_unchanged() -> None:
    """Surface, prompt and pinned task type must survive the hand-off — AI-Edit
    relies on its "coding" pin reaching the engine."""
    port = FakeDecisionPort(switch_evaluation())
    service = RoutingApplicationService(port, FakeModeResolver(RoutingMode.AUTO))
    request = make_request(surface="ai_edit", task_type="coding",
                           required_capabilities=("vision",))

    service.resolve(request)

    forwarded = port.calls[0][0]
    assert forwarded is request
    assert forwarded.surface == "ai_edit"
    assert forwarded.task_type == "coding"
    assert forwarded.required_capabilities == ("vision",)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("auto", RoutingMode.AUTO),
        ("MANUAL", RoutingMode.MANUAL),
        (" fallback ", RoutingMode.FALLBACK),
        ("nonsense", RoutingMode.OFF),
        ("", RoutingMode.OFF),
        (None, RoutingMode.OFF),
    ],
)
def test_mode_parsing_is_forgiving(raw, expected) -> None:
    """Config values are hand-edited; an unknown one must degrade, not raise."""
    assert RoutingMode.parse(raw) is expected


def test_confirm_timeout_falls_back_to_the_default_when_unusable() -> None:
    """A corrupted timeout must not produce a zero-second dialog that declines
    every switch before the user can read it."""
    service = RoutingApplicationService(
        FakeDecisionPort(switch_evaluation()),
        FakeModeResolver(RoutingMode.MANUAL),
        confirm_timeout_sec=lambda: 0.0,
    )

    assert service.confirm_timeout() == RoutingApplicationService.DEFAULT_CONFIRM_TIMEOUT_SEC


def test_routing_request_is_immutable() -> None:
    """The snapshot must not change under a turn that is already in flight."""
    request = make_request()

    with pytest.raises(Exception):
        request.prompt = "something else"  # type: ignore[misc]
