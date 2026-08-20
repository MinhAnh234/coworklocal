"""Provider boundary owned with get_project_change_context."""

from __future__ import annotations

from typing import Any, Protocol

from ..foundation import IdentityContext, ProviderError


class ChangeProvider(Protocol):
    def get_change_context(self, **arguments: Any) -> dict[str, Any]: ...


class UnconfiguredChangeProvider:
    def get_change_context(self, **arguments: Any) -> dict[str, Any]:
        raise ProviderError(
            "UNAVAILABLE",
            "The change provider is not configured for this environment.",
            retryable=False,
        )


def build_provider(identity: IdentityContext) -> ChangeProvider:
    """Replace only this factory when wiring the approved read-only Git adapter."""
    return UnconfiguredChangeProvider()
