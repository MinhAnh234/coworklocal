"""Central registry of every LLM provider the app can talk to.

Replaces the bare ``{name: class}`` dict in ``providers/factory.py`` as the
single catalogue of providers. Two responsibilities, kept deliberately narrow:

1. **Lookup** — resolve a provider id (or one of its aliases, or a bare model
   id) to its :class:`~domain.models.provider_descriptor.ProviderDescriptor`.
2. **Construction** — instantiate the concrete adapter class that speaks the
   descriptor's wire protocol.

This is infrastructure, not domain: it is allowed to import the concrete
``providers/*`` adapters (which pull in ``requests``). The adapters are imported
lazily inside :meth:`build` so that merely *reading the catalogue* — which the
pure routing service does on every turn — never drags the HTTP stack into the
process.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Iterable, List, Optional

from ...domain.models.provider_descriptor import (
    AuthKind,
    ProviderDescriptor,
    WireProtocol,
)

# --------------------------------------------------------------------------- #
# Built-in catalogue.
#
# Mirrors DEFAULT_CONFIG["providers"] in config.py (ids + default models) and
# providers/factory.py (id -> wire protocol). Prices are intentionally absent:
# core/routing/metadata.py owns cost, and a guessed price is worse than a
# known-unknown (see that module's docstring).
# --------------------------------------------------------------------------- #
BUILTIN_DESCRIPTORS: tuple = (
    ProviderDescriptor(
        provider_id="openai_compat",
        display_name="OpenAI-compatible gateway",
        wire_protocol=WireProtocol.OPENAI_COMPAT,
        auth_kind=AuthKind.API_KEY,
        default_model="gpt-4o-mini",
        supports_vision=True,
        # A generic gateway has no fixed host, so the endpoint MUST be
        # configured before the provider can be used at all.
        requires_base_url=True,
    ),
    ProviderDescriptor(
        provider_id="anthropic",
        display_name="Anthropic Claude",
        wire_protocol=WireProtocol.ANTHROPIC,
        auth_kind=AuthKind.API_KEY,
        default_model="claude-sonnet-4-6",
        # Kept in sync with AnthropicProvider._FALLBACK_MODELS — the list the
        # provider itself falls back to when /v1/models cannot be reached.
        models=("claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"),
        max_context=200000,
        supports_vision=True,
    ),
    ProviderDescriptor(
        provider_id="ollama",
        display_name="Ollama (local)",
        wire_protocol=WireProtocol.OPENAI_COMPAT,
        # A local runtime needs no credential; Settings must not demand one.
        auth_kind=AuthKind.NONE,
        default_model="llama3.1",
        supports_vision=False,
        requires_base_url=True,
    ),
    ProviderDescriptor(
        provider_id="github_copilot",
        display_name="GitHub Copilot",
        wire_protocol=WireProtocol.OPENAI_COMPAT,
        # The credential is a Copilot token minted by an external login flow,
        # not a self-service API key.
        auth_kind=AuthKind.OAUTH_TOKEN,
        default_model="gpt-4o",
        models=("gpt-4o", "gpt-4o-mini"),
        max_context=128000,
        supports_vision=True,
    ),
    ProviderDescriptor(
        provider_id="codex",
        display_name="OpenAI",
        wire_protocol=WireProtocol.OPENAI_COMPAT,
        auth_kind=AuthKind.API_KEY,
        default_model="gpt-4o-mini",
        models=("gpt-4o", "gpt-4o-mini", "o1", "o3"),
        max_context=128000,
        supports_vision=True,
        # Historic config key: early builds stored this provider as "openai".
        aliases=("openai",),
    ),
)


class ProviderNotFoundError(LookupError):
    """Raised when no descriptor answers to the requested provider id.

    A dedicated type (rather than bare ``KeyError``) lets callers distinguish
    "this provider is not in the catalogue" from an unrelated dict miss, and
    keeps the message actionable by listing what IS registered.
    """


class ProviderRegistry:
    """Thread-safe catalogue of :class:`ProviderDescriptor` records.

    Thread-safety matters because model discovery runs on background worker
    threads (the routing prober, Settings' "Load models") and republishes an
    updated descriptor via :meth:`replace`, while chat turns on other threads
    are reading the catalogue concurrently.
    """

    def __init__(self, descriptors: Optional[Iterable[ProviderDescriptor]] = None) -> None:
        # Keyed by canonical id; alias resolution walks the values so an alias
        # can never shadow a real provider id.
        """Đăng ký sẵn một loạt provider.

        Khoá theo id chuẩn, còn bí danh được dò khi tra: nhờ vậy một bí danh không
        bao giờ che mất một id thật. Có khoá riêng vì sổ đăng ký bị đọc từ nhiều
        luồng.
        """
        self._by_id: Dict[str, ProviderDescriptor] = {}
        self._lock = threading.RLock()
        for descriptor in descriptors or ():
            self.register(descriptor)

    # -- registration --------------------------------------------------- #
    def register(self, descriptor: ProviderDescriptor) -> ProviderDescriptor:
        """Add a descriptor. Refuses to silently overwrite an existing id so a
        typo in a plugin cannot hijack a built-in provider; use :meth:`replace`
        when an update is the actual intent."""
        with self._lock:
            existing = self._by_id.get(descriptor.provider_id)
            if existing is not None and existing != descriptor:
                raise ValueError(
                    f"Provider '{descriptor.provider_id}' is already registered; "
                    "call replace() to update it."
                )
            self._by_id[descriptor.provider_id] = descriptor
            return descriptor

    def replace(self, descriptor: ProviderDescriptor) -> ProviderDescriptor:
        """Register or update a descriptor unconditionally — the path model
        discovery uses to publish a freshly enumerated model list."""
        with self._lock:
            self._by_id[descriptor.provider_id] = descriptor
            return descriptor

    # -- lookup ---------------------------------------------------------- #
    def get(self, provider_id: str) -> ProviderDescriptor:
        """Descriptor for ``provider_id`` (canonical id or alias).

        Raises :class:`ProviderNotFoundError` rather than returning ``None`` so
        a misconfigured provider fails loudly at the call site instead of
        surfacing later as an ``AttributeError`` on ``None``.
        """
        found = self.find(provider_id)
        if found is None:
            known = ", ".join(sorted(self._by_id)) or "<empty registry>"
            raise ProviderNotFoundError(
                f"Unsupported provider: {provider_id!r}. Registered: {known}"
            )
        return found

    def find(self, provider_id: str) -> Optional[ProviderDescriptor]:
        """Non-raising :meth:`get` — ``None`` when nothing matches."""
        needle = (provider_id or "").strip()
        if not needle:
            return None
        with self._lock:
            direct = self._by_id.get(needle)
            if direct is not None:
                return direct
            # Fall back to a case-insensitive id/alias scan; order is stable
            # because dicts preserve insertion order, so the earliest-registered
            # provider wins a tie.
            for descriptor in self._by_id.values():
                if descriptor.matches(needle):
                    return descriptor
        return None

    def find_by_model(self, model_id: str) -> Optional[ProviderDescriptor]:
        """Resolve a bare model id back to the provider that serves it.

        This is the "dynamic lookup by model ID" R03-T02 calls for: routing
        decisions and saved conversations sometimes carry only a model name, and
        the caller still needs to know which provider to build. Returns ``None``
        when the model belongs to a gateway whose catalogue we cannot enumerate
        offline — callers then fall back to the configured active provider.
        """
        needle = (model_id or "").strip()
        if not needle:
            return None
        with self._lock:
            for descriptor in self._by_id.values():
                if descriptor.knows_model(needle):
                    return descriptor
        return None

    def all(self) -> List[ProviderDescriptor]:
        """Every registered descriptor, in registration order (snapshot copy —
        safe to iterate while another thread registers)."""
        with self._lock:
            return list(self._by_id.values())

    def ids(self) -> List[str]:
        """Canonical provider ids, sorted for stable UI/reporting output."""
        with self._lock:
            return sorted(self._by_id)

    def __contains__(self, provider_id: object) -> bool:
        """``"tên" in registry`` — tính cả bí danh, và giá trị không phải chuỗi thì
        trả về False thay vì ném lỗi.
        """
        return isinstance(provider_id, str) and self.find(provider_id) is not None

    def __len__(self) -> int:
        """Số provider đã đăng ký (không đếm bí danh)."""
        with self._lock:
            return len(self._by_id)

    # -- construction ---------------------------------------------------- #
    def adapter_class(self, provider_id: str):
        """Concrete ``Provider`` subclass implementing this provider's protocol.

        The adapters are imported here (not at module import) so the pure
        routing/domain code can consult the catalogue without loading
        ``requests`` and the whole HTTP stack.
        """
        descriptor = self.get(provider_id)
        from ...providers.anthropic import AnthropicProvider
        from ...providers.openai_compat import OpenAICompatProvider

        protocol_to_class = {
            WireProtocol.OPENAI_COMPAT: OpenAICompatProvider,
            WireProtocol.ANTHROPIC: AnthropicProvider,
        }
        adapter = protocol_to_class.get(descriptor.wire_protocol)
        if adapter is None:  # pragma: no cover — unreachable while the map is total
            raise ProviderNotFoundError(
                f"No adapter implements wire protocol {descriptor.wire_protocol!r}"
            )
        return adapter

    def build(self, provider_id: str, conf: Dict[str, Any]):
        """Instantiate a ready-to-use provider adapter.

        The descriptor's ``default_model`` fills in a missing/blank ``model`` so
        a half-written config still produces a working provider instead of an
        empty model id that only fails once the request hits the gateway.
        """
        descriptor = self.get(provider_id)
        adapter = self.adapter_class(descriptor.provider_id)
        merged = dict(conf or {})
        merged["model"] = descriptor.resolve_model(merged.get("model", ""))
        return adapter(merged)


# --------------------------------------------------------------------------- #
# Process-wide default registry.
#
# Built lazily under a lock: several UI screens can ask for it during startup
# from different threads, and double-construction would hand out two catalogues
# whose discovered model lists then drift apart.
# --------------------------------------------------------------------------- #
_default_registry: Optional[ProviderRegistry] = None
_default_lock = threading.Lock()


def default_registry() -> ProviderRegistry:
    """The shared registry seeded with :data:`BUILTIN_DESCRIPTORS`."""
    global _default_registry
    if _default_registry is None:
        with _default_lock:
            if _default_registry is None:
                _default_registry = ProviderRegistry(BUILTIN_DESCRIPTORS)
    return _default_registry


def reset_default_registry() -> None:
    """Drop the cached registry — test-support hook so one test's registrations
    cannot leak into the next."""
    global _default_registry
    with _default_lock:
        _default_registry = None


__all__ = [
    "BUILTIN_DESCRIPTORS",
    "ProviderNotFoundError",
    "ProviderRegistry",
    "default_registry",
    "reset_default_registry",
]
