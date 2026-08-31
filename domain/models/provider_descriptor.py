"""Provider catalog metadata — the domain-layer description of ONE LLM provider.

Before R03 the answer to "which providers exist, what do they cost, what can
they do?" was spread over three places: the class table in
``providers/factory.py``, the hand-maintained pricing table in
``core/routing/metadata.py`` and a handful of ``if provider == "anthropic"``
branches in the UI. :class:`ProviderDescriptor` is the single declarative
record those call sites now read from.

Layer rules (see ``docs/architecture/ADR-001-layered-architecture.md``): this
module is 100% pure Python — no PySide6, no ``requests``, no filesystem, and no
import of the concrete ``providers/*`` adapters. It only *describes* a provider;
constructing one is the infrastructure layer's job
(``infrastructure/providers/provider_registry.py``).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Dict, Optional, Tuple


class AuthKind(str, Enum):
    """How a provider authenticates, so Settings/onboarding can ask for the
    right thing instead of hard-coding per-provider form fields.

    Inherits ``str`` so a descriptor round-trips through JSON unchanged (the
    value is written as a plain string), matching how the routing models in
    ``core/routing/models.py`` already serialize their enums.
    """

    NONE = "none"          # local runtimes (Ollama) — nothing to supply
    API_KEY = "api_key"    # bearer/x-api-key style secret
    OAUTH_TOKEN = "oauth"  # token minted by an external login flow (Copilot)


class WireProtocol(str, Enum):
    """The on-the-wire dialect a provider speaks.

    Several *distinct* providers share one protocol (Ollama, Codex, GitHub
    Copilot and generic gateways are all OpenAI Chat Completions), which is
    exactly why protocol is a separate field from the provider id: the registry
    picks the adapter class from the protocol, while everything user-facing
    keys off the id.
    """

    OPENAI_COMPAT = "openai_compat"
    ANTHROPIC = "anthropic"


@dataclass(frozen=True)
class ProviderDescriptor:
    """Immutable metadata for one provider the app can route work to.

    Frozen because descriptors are shared process-wide by the registry, the
    routing service and (eventually) the Settings screen; making them read-only
    removes any chance one caller mutates the catalog another caller is
    iterating. Use :meth:`with_models` to derive an updated copy instead.

    Unknown pricing/context values stay ``None`` rather than being guessed —
    the routing scorer needs to distinguish "free" from "we don't know", the
    same contract ``core/routing/models.py::ModelMetadata`` already follows.
    """

    provider_id: str                              # config key, e.g. "anthropic"
    display_name: str                             # human label for Settings/UI
    wire_protocol: WireProtocol                   # which adapter class implements it
    auth_kind: AuthKind = AuthKind.API_KEY
    default_model: str = ""                       # used when no model is selected
    models: Tuple[str, ...] = ()                  # known model ids (may be empty)
    max_context: Optional[int] = None             # tokens; None = unknown
    cost_per_1k_input: Optional[float] = None     # USD per 1K input tokens
    cost_per_1k_output: Optional[float] = None    # USD per 1K output tokens
    supports_vision: bool = False
    supports_tools: bool = True
    supports_streaming: bool = True
    requires_base_url: bool = False               # gateway endpoints must be configured
    # Extra ids that should resolve to this descriptor (renames/aliases kept for
    # backwards compatibility with configs written by older app versions).
    aliases: Tuple[str, ...] = ()
    # Free-form extension point so a team can attach provider-specific hints
    # without another schema migration.
    extras: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Reject descriptors that could never be looked up.

        Raising here (rather than at registration time) means a malformed
        descriptor cannot exist at all, so every consumer downstream may assume
        ``provider_id`` is a usable dict key.
        """
        if not self.provider_id:
            raise ValueError("ProviderDescriptor.provider_id must not be empty")
        if not isinstance(self.wire_protocol, WireProtocol):
            raise TypeError("ProviderDescriptor.wire_protocol must be a WireProtocol")

    # -- identity ------------------------------------------------------- #
    @property
    def identifiers(self) -> Tuple[str, ...]:
        """Every id this descriptor answers to (canonical id first)."""
        return (self.provider_id, *self.aliases)

    def matches(self, provider_id: str) -> bool:
        """Case-insensitive id/alias match — config files and CLI flags are
        typed by humans, so lookup must not be case sensitive."""
        needle = (provider_id or "").strip().lower()
        return any(needle == known.lower() for known in self.identifiers)

    # -- capability queries --------------------------------------------- #
    def knows_model(self, model_id: str) -> bool:
        """Whether ``model_id`` is in this provider's declared catalog.

        A miss is NOT proof the model is unusable: gateways expose models we
        cannot enumerate offline, so callers treat this as a hint (used to
        resolve a bare model id back to its provider) and never as a gate that
        blocks a request.
        """
        needle = (model_id or "").strip().lower()
        return any(needle == known.strip().lower() for known in self.models)

    def has_capability(self, capability: str) -> bool:
        """Capability check by name, mirroring the vocabulary the routing
        selector already filters on (``"vision"``, ``"tools"``, ``"streaming"``)
        so a descriptor can be fed straight into ``rank_models``."""
        return capability in self.capabilities

    @property
    def capabilities(self) -> frozenset:
        """Capability set in the same vocabulary as
        ``core/routing/models.py::ModelMetadata.capabilities``."""
        caps = set()
        if self.supports_vision:
            caps.add("vision")
        if self.supports_tools:
            caps.add("tools")
        if self.supports_streaming:
            caps.add("streaming")
        return frozenset(caps)

    @property
    def avg_cost_per_1k(self) -> Optional[float]:
        """Blended input/output price, or ``None`` when either side is unknown.

        Uses the same 1:3 input:output weighting as
        ``ModelMetadata.avg_cost_per_1k`` so a descriptor and an assessment
        never disagree about what a model costs.
        """
        ci, co = self.cost_per_1k_input, self.cost_per_1k_output
        if ci is None or co is None:
            return None
        return (ci + 3.0 * co) / 4.0

    def resolve_model(self, requested: str = "") -> str:
        """The model id to actually call: the caller's choice when they made
        one, otherwise this provider's default. Centralised here because every
        surface (chat, Co4E, AI-Edit) previously re-implemented the same
        ``model or config_default`` fallback inline."""
        return (requested or "").strip() or self.default_model

    # -- derivation / serialization ------------------------------------- #
    def with_models(self, models, *, default_model: str = "") -> "ProviderDescriptor":
        """A copy carrying a freshly discovered model list.

        Providers can enumerate their models at runtime (``list_models()``);
        because the descriptor is frozen, discovery produces a NEW descriptor
        that the registry swaps in atomically instead of mutating one that other
        threads may be reading.
        """
        ordered = tuple(dict.fromkeys(m for m in models if m))  # de-dup, keep order
        chosen = default_model or self.default_model
        # Keep the default pointing at something real: fall back to the first
        # discovered model when the configured default vanished from the catalog.
        if ordered and chosen not in ordered:
            chosen = ordered[0]
        return replace(self, models=ordered, default_model=chosen)

    def to_dict(self) -> Dict[str, Any]:
        """JSON-friendly view for config persistence and the Settings UI."""
        return {
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "wire_protocol": self.wire_protocol.value,
            "auth_kind": self.auth_kind.value,
            "default_model": self.default_model,
            "models": list(self.models),
            "max_context": self.max_context,
            "cost_per_1k_input": self.cost_per_1k_input,
            "cost_per_1k_output": self.cost_per_1k_output,
            "capabilities": sorted(self.capabilities),
            "requires_base_url": self.requires_base_url,
            "aliases": list(self.aliases),
        }


__all__ = ["AuthKind", "WireProtocol", "ProviderDescriptor"]
