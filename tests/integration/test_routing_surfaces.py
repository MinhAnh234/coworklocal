"""The three chat surfaces really route through the shared service (R03-T04/T05).

The unit suite proves ``RoutingApplicationService`` decides correctly against a
fake router. This file proves the three widgets that used to own a private copy
of that algorithm now call it, on real (offscreen) widgets:

* ``ui/chat_panel.py::_apply_routing``      (Cowork)
* ``ui/co4e_tab.py::_apply_co4e_routing``   (Co4E)
* ``presentation/folder/ai_edit_model_resolver.py::AiEditModelResolver.apply_routing``   (AI-Edit)

On this branch the Manual-mode confirm dialog (``ui/routing_toggle.py::
confirm_switch``) still reads its decision straight off the engine's own
``core/routing/models.py::SwitchDecision`` - ``RoutingOutcome.decision`` passes
it through unwrapped rather than translating it into an application-layer
type, so there is no separate field contract to pin here.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, List, Optional, Tuple

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cowork_local.application.model_routing import (   # noqa: E402
    RoutingApplicationService,
    RoutingMode,
)
from cowork_local.config import AppConfig               # noqa: E402
from cowork_local.state import AppContext               # noqa: E402

pytest.importorskip("PySide6", reason="Qt is required for the integration suite")


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def ctx(qt_app, tmp_path: Path) -> AppContext:
    return AppContext(AppConfig.load(tmp_path / "config.json"))


class _FakeDecisionPort:
    """A :class:`RoutingDecisionPort` that always proposes the same switch and
    records the surface (and task type) it was asked to evaluate."""

    def __init__(self, provider="anthropic", model="claude-sonnet-4-6",
                 gain: float = 0.4) -> None:
        self.provider = provider
        self.model = model
        self.gain = gain
        self.surfaces: List[str] = []

    def evaluate(self, request, mode):
        from cowork_local.application.model_routing import RouteEvaluation

        self.surfaces.append(request.surface)
        return RouteEvaluation(
            task_type=request.task_type or "coding",
            should_switch=True,
            target_provider=self.provider,
            target_model=self.model,
            score_gain=self.gain,
            reason="better fit",
        )


class _FixedModeResolver:
    """A :class:`ModeResolver` that reports the same mode for every surface."""

    def __init__(self, mode: str) -> None:
        self._mode = mode

    def mode_for(self, surface: str) -> str:
        return self._mode


def _install(ctx: AppContext, mode: str) -> _FakeDecisionPort:
    """Wire a fake decision port into the context and force ``mode`` on every
    surface.

    Every surface reaches the service through
    ``build_routing_application_service(ctx)``, which memoises its instance on
    ``ctx._routing_app_service`` (see ``core_routing_adapter.py``) — pre-seeding
    that exact attribute is what makes the surfaces under test see this fake
    instead of building a real one against ``ctx.routing()``.
    """
    router = _FakeDecisionPort()
    service = RoutingApplicationService(router, mode_resolver=_FixedModeResolver(mode))
    ctx._routing_app_service = service   # already-built instance; accessor returns it
    return router


# --------------------------------------------------------------------------- #
# Cowork chat
# --------------------------------------------------------------------------- #
def test_cowork_applies_an_auto_switch_to_the_next_turn(ctx):
    from cowork_local.ui.cowork_tab import CoworkTab

    router = _install(ctx, "auto")
    tab = CoworkTab(ctx)
    turn: dict = {"bubbles": []}

    tab._apply_routing("write a function", turn)

    assert router.surfaces == [tab.kind]
    # build_provider() honours these for THIS turn only.
    assert (tab._routed_provider, tab._routed_model) == ("anthropic", "claude-sonnet-4-6")
    assert turn["bubbles"], "the user must be told the model was switched"


def test_cowork_leaves_the_model_alone_when_routing_is_off(ctx):
    from cowork_local.ui.cowork_tab import CoworkTab

    router = _install(ctx, "off")
    tab = CoworkTab(ctx)
    turn: dict = {"bubbles": []}

    tab._apply_routing("write a function", turn)

    assert router.surfaces == []
    assert (tab._routed_provider, tab._routed_model) == (None, None)
    assert turn["bubbles"] == []


def test_cowork_manual_mode_switches_only_after_the_dialog_approves(ctx, monkeypatch):
    """Manual mode's confirm dialog is ``ui/routing_toggle.py::confirm_switch``,
    imported locally inside ``_apply_routing`` at call time — patching the
    source module's attribute is what a local import actually re-reads."""
    from cowork_local.ui.cowork_tab import CoworkTab

    _install(ctx, "manual")
    tab = CoworkTab(ctx)
    asked: List[Any] = []

    def fake_confirm(parent, decision, timeout):
        asked.append(decision)
        return True

    monkeypatch.setattr("cowork_local.ui.routing_toggle.confirm_switch", fake_confirm)
    turn: dict = {"bubbles": []}

    tab._apply_routing("write a function", turn)

    assert len(asked) == 1
    assert (tab._routed_provider, tab._routed_model) == ("anthropic", "claude-sonnet-4-6")


def test_cowork_manual_mode_keeps_the_model_when_the_dialog_is_declined(ctx, monkeypatch):
    from cowork_local.ui.cowork_tab import CoworkTab

    _install(ctx, "manual")
    tab = CoworkTab(ctx)
    monkeypatch.setattr("cowork_local.ui.routing_toggle.confirm_switch",
                         lambda parent, decision, timeout: False)
    turn: dict = {"bubbles": []}

    tab._apply_routing("write a function", turn)

    assert (tab._routed_provider, tab._routed_model) == (None, None)
    assert turn["bubbles"] == []


def test_a_pinned_admin_agent_still_wins_over_routing(ctx):
    """An explicitly chosen Admin agent pins its own provider/model; routing must
    not override a deliberate user choice."""
    from cowork_local.ui.cowork_tab import CoworkTab

    router = _install(ctx, "auto")
    tab = CoworkTab(ctx)
    tab._admin_agent = object()
    turn: dict = {"bubbles": []}

    tab._apply_routing("write a function", turn)

    assert router.surfaces == []
    assert (tab._routed_provider, tab._routed_model) == (None, None)


# --------------------------------------------------------------------------- #
# Co4E
# --------------------------------------------------------------------------- #
def test_co4e_routes_on_its_own_surface_key_and_returns_the_model(ctx):
    from cowork_local.ui.co4e_tab import Co4ETab

    router = _install(ctx, "auto")
    tab = Co4ETab(ctx)

    model = tab._apply_co4e_routing("build me a flow")

    assert router.surfaces == ["co4e"]
    assert model == "claude-sonnet-4-6"
    assert tab._co4e_routed_provider == "anthropic"


def test_co4e_returns_an_empty_model_when_routing_is_off(ctx):
    """'' means "use the provider default" - the contract _run_chat_turn expects."""
    from cowork_local.ui.co4e_tab import Co4ETab

    _install(ctx, "off")
    tab = Co4ETab(ctx)

    assert tab._apply_co4e_routing("build me a flow") == ""
    assert tab._co4e_routed_provider is None


# --------------------------------------------------------------------------- #
# AI-Edit
# --------------------------------------------------------------------------- #
def test_ai_edit_routes_on_its_own_surface_key(ctx):
    """R08-T12: the routing call this test pins moved from
    ``ui/folder_tab.py::FolderTab._ai_apply_routing`` to
    ``presentation/folder/ai_edit_model_resolver.py::AiEditModelResolver.
    apply_routing`` - same RoutingApplicationService call, same surface key,
    now independently testable without the whole FolderTab widget tree."""
    from cowork_local.presentation.folder.folder_tab import FolderTab

    router = _install(ctx, "auto")
    tab = FolderTab(ctx)

    tab.ai_panel.resolver.apply_routing("rename this variable")

    assert router.surfaces == ["ai_edit"]
    assert (tab.ai_panel.resolver.routed_provider, tab.ai_panel.resolver.routed_model) == (
        "anthropic", "claude-sonnet-4-6")


def test_ai_edit_pins_the_coding_task_type(ctx):
    """An edit instruction is never a QA question, so AI-Edit skips
    classification entirely - the constraint has to survive the move into the
    shared service or it is silently dropped."""
    from cowork_local.core.routing.models import TaskType
    from cowork_local.presentation.folder.folder_tab import FolderTab

    seen: List[Any] = []

    class _Recorder(_FakeDecisionPort):
        def evaluate(self, request, mode):
            seen.append(request.task_type)
            return super().evaluate(request, mode)

    ctx._routing_app_service = RoutingApplicationService(
        _Recorder(), mode_resolver=_FixedModeResolver("auto"))
    tab = FolderTab(ctx)

    tab.ai_panel.resolver.apply_routing("rename this variable")

    assert seen == [TaskType.CODING]
