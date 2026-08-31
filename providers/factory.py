"""Build a provider instance from the application config.

Kept as the historic entry point (``providers.build_provider``) that call sites
across the app already import, but it no longer owns a provider table of its
own: since R03-T02 the catalogue lives in
``infrastructure/providers/provider_registry.py`` so provider ids, wire
protocols, default models and capabilities are declared exactly once.
"""
from __future__ import annotations

from typing import Any, Dict

from .base import Provider, ProviderError


def build_provider(name: str, conf: Dict[str, Any]) -> Provider:
    """Construct the adapter registered for ``name``.

    Delegates to the central registry and translates its lookup failure into
    :class:`ProviderError`, because every existing call site (chat turns,
    Settings' connection test, the routing prober) already handles that type —
    changing the exception would ripple into unrelated error handling.
    """
    from ..infrastructure.providers.provider_registry import (
        ProviderNotFoundError,
        default_registry,
    )

    try:
        return default_registry().build(name, conf)
    except ProviderNotFoundError as exc:
        raise ProviderError(f"Unsupported provider: {name}") from exc
