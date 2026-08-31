"""R03-T02 — unit tests for ProviderDescriptor and the central ProviderRegistry.

Covers what the rest of the app now relies on the catalogue for: resolving ids
and aliases, resolving a bare model id back to its provider, filling in default
models, and refusing to let a duplicate registration silently hijack a built-in.
"""

from __future__ import annotations

import pytest
from cowork_local.domain.models.provider_descriptor import (
    AuthKind,
    ProviderDescriptor,
    WireProtocol,
)
from cowork_local.infrastructure.providers.provider_registry import (
    BUILTIN_DESCRIPTORS,
    ProviderNotFoundError,
    ProviderRegistry,
)


def make_descriptor(**overrides) -> ProviderDescriptor:
    """A minimal valid descriptor; tests override just the field under test."""
    fields = dict(
        provider_id="demo",
        display_name="Demo provider",
        wire_protocol=WireProtocol.OPENAI_COMPAT,
        default_model="demo-small",
        models=("demo-small", "demo-large"),
    )
    fields.update(overrides)
    return ProviderDescriptor(**fields)


# --------------------------------------------------------------------------- #
# ProviderDescriptor
# --------------------------------------------------------------------------- #
def test_descriptor_rejects_an_empty_id() -> None:
    """An id-less descriptor could never be looked up, so it must not exist."""
    with pytest.raises(ValueError):
        make_descriptor(provider_id="")


def test_descriptor_rejects_a_non_enum_protocol() -> None:
    """The protocol drives adapter selection; a stray string would silently
    fall through to "no adapter" at build time instead of failing here."""
    with pytest.raises(TypeError):
        make_descriptor(wire_protocol="openai_compat")


def test_descriptor_is_immutable() -> None:
    """Descriptors are shared process-wide; a mutation would be visible to every
    other reader mid-iteration."""
    descriptor = make_descriptor()

    with pytest.raises(Exception):
        descriptor.default_model = "hacked"  # type: ignore[misc]


def test_id_matching_ignores_case_and_honours_aliases() -> None:
    """Provider ids come from hand-edited config files and old app versions."""
    descriptor = make_descriptor(aliases=("legacy-demo",))

    assert descriptor.matches("DEMO")
    assert descriptor.matches(" legacy-demo ")
    assert not descriptor.matches("other")


def test_capabilities_use_the_routing_vocabulary() -> None:
    """The set must be feedable straight into the routing selector's filter."""
    descriptor = make_descriptor(supports_vision=True, supports_tools=True,
                                 supports_streaming=False)

    assert descriptor.capabilities == frozenset({"vision", "tools"})
    assert descriptor.has_capability("vision")
    assert not descriptor.has_capability("streaming")


def test_average_cost_is_none_when_a_price_is_unknown() -> None:
    """Unknown prices stay unknown — a guessed number would silently skew the
    routing scorer's cost term."""
    assert make_descriptor(cost_per_1k_input=0.5).avg_cost_per_1k is None
    priced = make_descriptor(cost_per_1k_input=1.0, cost_per_1k_output=3.0)
    # Same 1:3 input:output weighting as ModelMetadata.avg_cost_per_1k.
    assert priced.avg_cost_per_1k == pytest.approx((1.0 + 9.0) / 4.0)


def test_resolve_model_prefers_the_caller_then_the_default() -> None:
    """One place implements the "picked model or provider default" fallback that
    every chat surface used to re-implement inline."""
    descriptor = make_descriptor()

    assert descriptor.resolve_model("demo-large") == "demo-large"
    assert descriptor.resolve_model("") == "demo-small"
    assert descriptor.resolve_model("  ") == "demo-small"


def test_with_models_repoints_a_default_that_vanished() -> None:
    """After discovery, the default must still name a model that exists."""
    descriptor = make_descriptor()

    updated = descriptor.with_models(["demo-v2", "demo-v2", "demo-v3"])

    assert updated.models == ("demo-v2", "demo-v3")   # de-duplicated, order kept
    assert updated.default_model == "demo-v2"
    assert descriptor.models == ("demo-small", "demo-large"), "original was mutated"


def test_with_models_keeps_a_default_that_survived() -> None:
    """Discovery must not reshuffle a user's working selection."""
    updated = make_descriptor().with_models(["demo-large", "demo-small"])

    assert updated.default_model == "demo-small"


# --------------------------------------------------------------------------- #
# ProviderRegistry
# --------------------------------------------------------------------------- #
def test_registry_resolves_ids_aliases_and_reports_unknowns() -> None:
    """Lookup must be forgiving about form, but loud about genuinely unknown
    providers — a typo should fail at the call site, not as a None later."""
    registry = ProviderRegistry([make_descriptor(aliases=("legacy-demo",))])

    assert registry.get("demo").provider_id == "demo"
    assert registry.get("legacy-demo").provider_id == "demo"
    assert registry.find("missing") is None
    assert "demo" in registry
    with pytest.raises(ProviderNotFoundError):
        registry.get("missing")


def test_registry_refuses_to_overwrite_silently_but_replace_works() -> None:
    """A second registration of the same id is almost always a bug; updating a
    descriptor is a deliberate act with its own method."""
    registry = ProviderRegistry([make_descriptor()])

    with pytest.raises(ValueError):
        registry.register(make_descriptor(display_name="Impostor"))

    registry.replace(make_descriptor(display_name="Renamed"))
    assert registry.get("demo").display_name == "Renamed"
    assert len(registry) == 1


def test_registry_re_registering_an_identical_descriptor_is_a_no_op() -> None:
    """Idempotent registration keeps repeated bootstrap calls harmless."""
    registry = ProviderRegistry([make_descriptor()])

    registry.register(make_descriptor())

    assert len(registry) == 1


def test_find_by_model_resolves_a_bare_model_id() -> None:
    """Routing decisions and saved conversations sometimes carry only a model
    name; the registry is what turns that back into a provider."""
    registry = ProviderRegistry([make_descriptor()])

    assert registry.find_by_model("demo-large").provider_id == "demo"
    # A gateway model we cannot enumerate offline is a miss, not an error — the
    # caller falls back to the configured active provider.
    assert registry.find_by_model("unknown-model") is None
    assert registry.find_by_model("") is None


def test_builtin_catalogue_covers_every_configured_provider() -> None:
    """The catalogue and DEFAULT_CONFIG must not drift: a provider users can
    configure but the registry cannot build is a dead Settings entry."""
    from cowork_local.config import DEFAULT_CONFIG

    registry = ProviderRegistry(BUILTIN_DESCRIPTORS)

    for provider_id in DEFAULT_CONFIG["providers"]:
        assert registry.find(provider_id) is not None, f"{provider_id} missing from registry"


def test_build_fills_in_the_default_model() -> None:
    """A half-written config must still produce a usable provider rather than an
    empty model id that only fails once the request reaches the gateway."""
    registry = ProviderRegistry(BUILTIN_DESCRIPTORS)

    provider = registry.build("anthropic", {"api_key": "k"})

    assert provider.model == registry.get("anthropic").default_model


def test_build_respects_an_explicit_model() -> None:
    """Per-tab model selection must win over the catalogue default."""
    registry = ProviderRegistry(BUILTIN_DESCRIPTORS)

    provider = registry.build("anthropic", {"api_key": "k", "model": "claude-opus-4-8"})

    assert provider.model == "claude-opus-4-8"


def test_factory_still_raises_provider_error_for_unknown_ids() -> None:
    """Existing call sites catch ProviderError; routing lookups through the
    registry must not change the exception type they see."""
    from cowork_local.providers import build_provider
    from cowork_local.providers.base import ProviderError

    with pytest.raises(ProviderError):
        build_provider("definitely-not-a-provider", {})
