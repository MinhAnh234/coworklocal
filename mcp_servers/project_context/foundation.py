"""Shared, stable boundary used by all Project Context tool work packages."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from pydantic import AnyUrl, BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    """Strict immutable model so provider-specific fields cannot leak to the Agent."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class IdentityContext(ContractModel):
    actor_id: str = Field(min_length=1, max_length=256)
    org_unit: str = Field(min_length=1, max_length=128)
    customer: str = Field(min_length=1, max_length=128)
    project: str = Field(min_length=1, max_length=128)
    granted_scopes: frozenset[str]


class SourceCitation(ContractModel):
    system: str = Field(min_length=1, max_length=64)
    url: AnyUrl
    revision: str = Field(min_length=1, max_length=256)
    retrieved_at: datetime


@dataclass(frozen=True)
class DispatchResult:
    ok: bool
    payload: dict[str, Any]


class PolicyDecisionPoint(Protocol):
    def decide(self, identity: IdentityContext, tool_name: str, project_id: str) -> bool: ...


class CredentialResolver(Protocol):
    def resolve(self, identity: IdentityContext, tool_name: str) -> Any: ...


@dataclass(frozen=True)
class ProjectContextRuntime:
    identity: IdentityContext
    policy: PolicyDecisionPoint
    credential_resolver: CredentialResolver


class ProviderError(RuntimeError):
    """A provider failure with a caller-safe message and retry classification."""

    def __init__(self, code: str, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message
        self.retryable = retryable


ToolHandler = Callable[[ContractModel, Any], dict[str, Any]]


@dataclass(frozen=True)
class ToolTemplate:
    name: str
    description: str
    input_model: type[ContractModel]
    output_model: type[ContractModel]
    handler: ToolHandler

    def declaration(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_model.model_json_schema(),
            "outputSchema": self.output_model.model_json_schema(),
        }


def error_result(
    code: str,
    *,
    category: str,
    retryable: bool,
    message: str,
    suggested_action: str,
    correlation_id: str,
) -> DispatchResult:
    return DispatchResult(
        ok=False,
        payload={
            "error": {
                "code": code,
                "category": category,
                "retryable": retryable,
                "message": message,
                "suggested_action": suggested_action,
                "correlation_id": correlation_id,
            }
        },
    )
