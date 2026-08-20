"""Provider boundary owned with get_project_issue_context."""

from __future__ import annotations

from typing import Any, Protocol

from ..foundation import IdentityContext, ProviderError


class IssueProvider(Protocol):
    def get_issue_context(self, **arguments: Any) -> dict[str, Any]: ...


class UnconfiguredIssueProvider:
    def get_issue_context(self, **arguments: Any) -> dict[str, Any]:
        raise ProviderError(
            "UNAVAILABLE",
            "The issue provider is not configured for this environment.",
            retryable=False,
        )


def build_provider(identity: IdentityContext) -> IssueProvider:
    """Replace only this factory when wiring the approved read-only issue adapter."""
    return UnconfiguredIssueProvider()
