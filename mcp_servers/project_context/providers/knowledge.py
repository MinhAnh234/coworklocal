"""Provider boundary owned with search_project_knowledge."""

from __future__ import annotations

from typing import Any, Protocol

from ..foundation import IdentityContext, ProviderError


class KnowledgeProvider(Protocol):
    def search_knowledge(self, **arguments: Any) -> dict[str, Any]: ...


class UnconfiguredKnowledgeProvider:
    def search_knowledge(self, **arguments: Any) -> dict[str, Any]:
        raise ProviderError(
            "UNAVAILABLE",
            "The knowledge provider is not configured for this environment.",
            retryable=False,
        )


def build_provider(identity: IdentityContext) -> KnowledgeProvider:
    """Replace only this factory when wiring approved project retrieval."""
    return UnconfiguredKnowledgeProvider()
