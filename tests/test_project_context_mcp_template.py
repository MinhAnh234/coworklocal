from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from cowork_local.mcp_servers.project_context.foundation import (
    IdentityContext,
    ProjectContextRuntime,
)
from cowork_local.mcp_servers.project_context.registry import (
    TOOL_NAMES,
    tool_declarations,
)
from cowork_local.mcp_servers.project_context.runtime import require_supported_python
from cowork_local.mcp_servers.project_context.server import dispatch

EXPECTED_TOOLS = {
    "get_project_issue_context",
    "search_project_knowledge",
    "get_project_change_context",
}


@dataclass
class RecordingPolicy:
    allowed: bool
    calls: int = 0

    def decide(self, identity: IdentityContext, tool_name: str, project_id: str) -> bool:
        self.calls += 1
        return self.allowed


@dataclass
class RecordingResolver:
    provider: Any
    calls: int = 0

    def resolve(self, identity: IdentityContext, tool_name: str) -> Any:
        self.calls += 1
        return self.provider


@dataclass(frozen=True)
class FakeProvider:
    response: dict[str, Any]

    def get_issue_context(self, **_: Any) -> dict[str, Any]:
        return dict(self.response)

    def search_knowledge(self, **_: Any) -> dict[str, Any]:
        return dict(self.response)

    def get_change_context(self, **_: Any) -> dict[str, Any]:
        return dict(self.response)


@pytest.fixture
def identity() -> IdentityContext:
    return IdentityContext(
        actor_id="member-a",
        org_unit="fsg",
        customer="internal",
        project="cowork-local",
        granted_scopes=frozenset({"read"}),
    )


def runtime(identity: IdentityContext, response: dict[str, Any], *, allowed: bool = True):
    policy = RecordingPolicy(allowed=allowed)
    resolver = RecordingResolver(provider=FakeProvider(response))
    return ProjectContextRuntime(
        identity=identity,
        policy=policy,
        credential_resolver=resolver,
    ), policy, resolver


def source() -> dict[str, str]:
    return {
        "system": "gitea",
        "url": "http://example.test/gitea-admin/cowork-local/issues/1",
        "revision": "main@abc123",
        "retrieved_at": "2026-08-20T10:00:00Z",
    }


def test_template_exposes_exactly_three_provider_neutral_tools() -> None:
    # Importing the MCP SDK at module scope aborted collection for the ENTIRE
    # suite whenever the SDK was missing, so the guard lives here, inside the only
    # test that touches it. Guarding per-test rather than per-module keeps the
    # other cases -- pure-Python contract checks that need no SDK -- running
    # instead of silently skipping with it.
    #
    # ``mcp`` is in requirements.txt, so a correctly installed checkout runs this
    # test for real; the guard only covers an environment installed by hand.
    types = pytest.importorskip("mcp.types")

    assert set(TOOL_NAMES) == EXPECTED_TOOLS
    declarations = tool_declarations()
    assert {item["name"] for item in declarations} == EXPECTED_TOOLS
    assert all(item["inputSchema"]["additionalProperties"] is False for item in declarations)
    assert all(item["outputSchema"]["additionalProperties"] is False for item in declarations)
    assert all(types.Tool(**item).name in EXPECTED_TOOLS for item in declarations)


def test_runtime_fails_fast_below_python_311() -> None:
    with pytest.raises(RuntimeError, match="requires Python 3.11"):
        require_supported_python((3, 9, 0))


def test_denied_request_never_resolves_credentials_or_calls_provider(
    identity: IdentityContext,
) -> None:
    app, policy, resolver = runtime(identity, {}, allowed=False)

    result = dispatch(
        "get_project_issue_context",
        {"project_id": "other-project", "issue_key": "1"},
        app,
    )

    assert result.ok is False
    assert result.payload["error"]["code"] == "DENIED"
    assert policy.calls == 1
    assert resolver.calls == 0


def test_invalid_input_is_rejected_before_policy(identity: IdentityContext) -> None:
    app, policy, resolver = runtime(identity, {})

    result = dispatch("get_project_issue_context", {"project_id": "cowork-local"}, app)

    assert result.ok is False
    assert result.payload["error"]["code"] == "INVALID_INPUT"
    assert policy.calls == 0
    assert resolver.calls == 0


@pytest.mark.parametrize(
    ("tool_name", "arguments", "response"),
    [
        (
            "get_project_issue_context",
            {"project_id": "cowork-local", "issue_key": "1"},
            {
                "project_id": "cowork-local",
                "issue_key": "1",
                "title": "MCP pilot",
                "status": "open",
                "description": "Build verifiable project context.",
                "acceptance_criteria": ["Every result has a source."],
                "related": [],
                "source": source(),
                "truncated": False,
                "returned": 1,
                "remaining": 0,
                "next_cursor": None,
            },
        ),
        (
            "search_project_knowledge",
            {"project_id": "cowork-local", "query": "MCP setup"},
            {
                "project_id": "cowork-local",
                "query": "MCP setup",
                "items": [
                    {
                        "document_id": "README.md",
                        "chunk_id": "README.md#setup",
                        "title": "Setup",
                        "excerpt": "Install the approved dependencies.",
                        "score": 0.9,
                        "source": source(),
                    }
                ],
                "truncated": False,
                "returned": 1,
                "remaining": 0,
                "next_cursor": None,
            },
        ),
        (
            "get_project_change_context",
            {"project_id": "cowork-local", "change_id": "1"},
            {
                "project_id": "cowork-local",
                "change_id": "1",
                "change_type": "pull-request",
                "title": "Add MCP contract",
                "state": "merged",
                "summary": "Introduces the project context contract.",
                "authors": ["member-c"],
                "files": ["mcp/contract.yaml"],
                "commits": ["abc123"],
                "related_issues": ["1"],
                "source": source(),
                "truncated": False,
                "returned": 1,
                "remaining": 0,
                "next_cursor": None,
            },
        ),
    ],
)
def test_each_member_template_has_a_valid_success_path(
    identity: IdentityContext,
    tool_name: str,
    arguments: dict[str, Any],
    response: dict[str, Any],
) -> None:
    app, policy, resolver = runtime(identity, response)

    result = dispatch(tool_name, arguments, app)

    assert result.ok is True
    assert result.payload["project_id"] == "cowork-local"
    assert result.payload["correlation_id"]
    assert policy.calls == 1
    assert resolver.calls == 1


def test_provider_output_must_match_contract(identity: IdentityContext) -> None:
    app, _, _ = runtime(identity, {"project_id": "cowork-local"})

    result = dispatch(
        "get_project_issue_context",
        {"project_id": "cowork-local", "issue_key": "1"},
        app,
    )

    assert result.ok is False
    assert result.payload["error"]["code"] == "UPSTREAM_ERROR"


def test_unexpected_provider_error_does_not_leak_exception(identity: IdentityContext) -> None:
    class LeakingProvider:
        def get_issue_context(self, **_: Any) -> dict[str, Any]:
            raise RuntimeError("secret provider-token-value")

    policy = RecordingPolicy(allowed=True)
    resolver = RecordingResolver(provider=LeakingProvider())
    app = ProjectContextRuntime(identity=identity, policy=policy, credential_resolver=resolver)

    result = dispatch(
        "get_project_issue_context",
        {"project_id": "cowork-local", "issue_key": "1"},
        app,
    )

    assert result.ok is False
    assert result.payload["error"]["code"] == "UPSTREAM_ERROR"
    assert "secret" not in str(result.payload)
