"""Member A's own test suite for get_project_issue_context.

Every test mocks the Gitea transport (``requests.get``) and never touches a
real network call or a real credential — per Issue #3 / MCP Contract v2:
unit tests must not call Gitea for real or use a real token.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pytest
import requests
from cowork_local.mcp_servers.project_context.foundation import (
    IdentityContext,
    ProjectContextRuntime,
    ProviderError,
)
from cowork_local.mcp_servers.project_context.providers.issue import (
    EnvironmentTargetResolver,
    GiteaIssueProvider,
    ServiceAccountCredentialResolver,
    UnconfiguredIssueProvider,
    _GiteaRepoTarget,
    build_provider,
)
from cowork_local.mcp_servers.project_context.runtime import ProjectProviderResolver
from cowork_local.mcp_servers.project_context.server import dispatch

FAKE_TOKEN = "super-secret-token-value"  # noqa: S105 - test-only sentinel, never a real credential


# ---------------------------------------------------------------------------
# Shared fixtures / test doubles
# ---------------------------------------------------------------------------
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


class _FakeResponse:
    def __init__(self, status_code: int, json_body: Any = "__missing__") -> None:
        self.status_code = status_code
        self._json_body = json_body

    def json(self) -> Any:
        if self._json_body == "__missing__":
            raise ValueError("no json body")
        return self._json_body


class _FakeTransport:
    """Drop-in replacement for ``requests.get`` that queues canned results
    and records every call it received (url/headers/timeout)."""

    def __init__(self, queue: list[Any]) -> None:
        self._queue = list(queue)
        self.calls: list[dict[str, Any]] = []

    def __call__(self, url: str, headers: dict[str, str] | None = None, timeout: float | None = None):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout})
        item = self._queue.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


@pytest.fixture
def identity() -> IdentityContext:
    return IdentityContext(
        actor_id="member-a",
        org_unit="fsg",
        customer="internal",
        project="cowork-local",
        granted_scopes=frozenset({"read"}),
    )


def _target(**overrides: Any) -> _GiteaRepoTarget:
    base = dict(
        base_url="http://example.test",
        owner="gitea-admin",
        repo="cowork-local",
        project_id="cowork-local",
    )
    base.update(overrides)
    return _GiteaRepoTarget(**base)


def _issue_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "title": "MCP pilot",
        "state": "open",
        "body": "Build verifiable project context.\n\n- [ ] Every result has a source.",
        "html_url": "http://example.test/gitea-admin/cowork-local/issues/1",
        "updated_at": "2026-08-20T10:00:00Z",
    }
    payload.update(overrides)
    return payload


def _runtime(
    identity: IdentityContext, provider: Any, *, allowed: bool = True,
) -> tuple[ProjectContextRuntime, RecordingPolicy, RecordingResolver]:
    policy = RecordingPolicy(allowed=allowed)
    resolver = RecordingResolver(provider=provider)
    return (
        ProjectContextRuntime(identity=identity, policy=policy, credential_resolver=resolver),
        policy,
        resolver,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------
def test_happy_path_returns_full_schema_with_openable_source(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _FakeTransport([_FakeResponse(200, _issue_payload())])
    monkeypatch.setattr(requests, "get", transport)
    provider = GiteaIssueProvider(_target(), FAKE_TOKEN)
    app, policy, resolver = _runtime(identity, provider)

    result = dispatch(
        "get_project_issue_context",
        {"project_id": "cowork-local", "issue_key": "1", "detail": "standard"},
        app,
    )

    assert result.ok is True
    assert policy.calls == 1
    assert resolver.calls == 1
    assert result.payload["project_id"] == "cowork-local"
    assert result.payload["issue_key"] == "1"
    assert result.payload["title"] == "MCP pilot"
    assert result.payload["status"] == "open"
    assert result.payload["acceptance_criteria"] == ["Every result has a source."]
    assert result.payload["correlation_id"]
    source = result.payload["source"]
    assert source["system"] == "gitea"
    assert source["url"].startswith("http://example.test/gitea-admin/cowork-local/issues/1")
    assert source["revision"] == "issue-updated:2026-08-20T10:00:00Z"
    assert source["retrieved_at"]
    # exactly one Gitea call was made, to the expected REST path
    assert len(transport.calls) == 1
    assert transport.calls[0]["url"].endswith("/api/v1/repos/gitea-admin/cowork-local/issues/1")
    assert transport.calls[0]["headers"] == {"Authorization": f"token {FAKE_TOKEN}"}


def test_happy_path_uses_real_project_provider_resolver(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITEA_BASE_URL", "http://example.test")
    monkeypatch.setenv("GITEA_TOKEN", FAKE_TOKEN)
    monkeypatch.setenv(
        "PROJECT_CONTEXT_REPO_MAP",
        '{"cowork-local": "wrong/legacy", '
        '"fsg/internal/cowork-local": "gitea-admin/cowork-local"}',
    )
    transport = _FakeTransport([_FakeResponse(200, _issue_payload())])
    monkeypatch.setattr(requests, "get", transport)
    app = ProjectContextRuntime(
        identity=identity,
        policy=RecordingPolicy(allowed=True),
        credential_resolver=ProjectProviderResolver(),
    )

    result = dispatch(
        "get_project_issue_context",
        {"project_id": "cowork-local", "issue_key": "1"},
        app,
    )

    assert result.ok is True
    assert result.payload["title"] == "MCP pilot"
    assert transport.calls[0]["headers"] == {"Authorization": f"token {FAKE_TOKEN}"}


def test_source_fields_are_all_present_and_well_formed(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(requests, "get", _FakeTransport([_FakeResponse(200, _issue_payload())]))
    provider = GiteaIssueProvider(_target(), FAKE_TOKEN)
    app, _, _ = _runtime(identity, provider)

    result = dispatch(
        "get_project_issue_context", {"project_id": "cowork-local", "issue_key": "1"}, app,
    )

    source = result.payload["source"]
    assert source["url"].startswith("http")
    assert isinstance(source["revision"], str) and source["revision"]
    assert "T" in source["retrieved_at"]  # ISO-8601 timestamp, not a placeholder


# ---------------------------------------------------------------------------
# Invalid input (before any policy/provider call)
# ---------------------------------------------------------------------------
def test_invalid_input_is_rejected_before_policy_or_provider(identity: IdentityContext) -> None:
    app, policy, resolver = _runtime(identity, UnconfiguredIssueProvider())

    result = dispatch("get_project_issue_context", {"project_id": "cowork-local"}, app)

    assert result.ok is False
    assert result.payload["error"]["code"] == "INVALID_INPUT"
    assert policy.calls == 0
    assert resolver.calls == 0


# ---------------------------------------------------------------------------
# DENIED — zero upstream calls, security-critical
# ---------------------------------------------------------------------------
def test_denied_project_never_resolves_credentials_or_calls_gitea(
    identity: IdentityContext,
) -> None:
    # No transport is patched at all: if the provider were ever reached it
    # would hit the real `requests.get` and fail loudly, so this test also
    # proves "zero upstream calls" by construction, not just by call count.
    app, policy, resolver = _runtime(identity, UnconfiguredIssueProvider(), allowed=False)

    result = dispatch(
        "get_project_issue_context",
        {"project_id": "some-other-project", "issue_key": "1"},
        app,
    )

    assert result.ok is False
    assert result.payload["error"]["code"] == "DENIED"
    assert policy.calls == 1
    assert resolver.calls == 0


def test_permission_decision_lives_outside_the_tool(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Acceptance criterion: swapping ONLY the policy must change the
    outcome, proving `tools/issue_context.py` contains no permission logic
    of its own."""
    monkeypatch.setattr(requests, "get", _FakeTransport([_FakeResponse(200, _issue_payload())]))
    provider = GiteaIssueProvider(_target(), FAKE_TOKEN)
    arguments = {"project_id": "cowork-local", "issue_key": "1"}

    allowed_app, _, _ = _runtime(identity, provider, allowed=True)
    denied_app, _, _ = _runtime(identity, provider, allowed=False)

    allowed_result = dispatch("get_project_issue_context", arguments, allowed_app)
    denied_result = dispatch("get_project_issue_context", arguments, denied_app)

    assert allowed_result.ok is True
    assert denied_result.ok is False
    assert denied_result.payload["error"]["code"] == "DENIED"


# ---------------------------------------------------------------------------
# Boundary / failure — distinct, non-leaking error codes
# ---------------------------------------------------------------------------
def test_not_found_issue_maps_to_not_found(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(requests, "get", _FakeTransport([_FakeResponse(404)]))
    provider = GiteaIssueProvider(_target(), FAKE_TOKEN)
    app, _, _ = _runtime(identity, provider)

    result = dispatch(
        "get_project_issue_context", {"project_id": "cowork-local", "issue_key": "999999"}, app,
    )

    assert result.ok is False
    assert result.payload["error"]["code"] == "NOT_FOUND"
    assert result.payload["error"]["suggested_action"]


def test_provider_raises_provider_error_directly_for_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unit-level check on the provider class itself (not only through
    dispatch): the raised exception must carry the right `.code`/`.retryable`
    for the runtime to map correctly."""
    monkeypatch.setattr(requests, "get", _FakeTransport([_FakeResponse(404)]))
    provider = GiteaIssueProvider(_target(), FAKE_TOKEN)

    with pytest.raises(ProviderError) as exc_info:
        provider.get_issue_context(
            project_id="cowork-local", issue_key="1", detail="standard", cursor=None,
        )

    assert exc_info.value.code == "NOT_FOUND"
    assert exc_info.value.retryable is False


def test_upstream_timeout_maps_to_upstream_timeout(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(requests, "get", _FakeTransport([requests.exceptions.Timeout("slow")]))
    provider = GiteaIssueProvider(_target(), FAKE_TOKEN)
    app, _, _ = _runtime(identity, provider)

    result = dispatch("get_project_issue_context", {"project_id": "cowork-local", "issue_key": "1"}, app)

    assert result.ok is False
    assert result.payload["error"]["code"] == "UPSTREAM_TIMEOUT"
    assert result.payload["error"]["retryable"] is True


@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    [(500, "UPSTREAM_ERROR"), (503, "UPSTREAM_ERROR"), (429, "RATE_LIMITED"),
     (401, "UPSTREAM_ERROR"), (403, "UPSTREAM_ERROR")],
)
def test_upstream_status_codes_map_to_distinct_error_codes(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch, status_code: int, expected_code: str,
) -> None:
    monkeypatch.setattr(requests, "get", _FakeTransport([_FakeResponse(status_code)]))
    provider = GiteaIssueProvider(_target(), FAKE_TOKEN)
    app, _, _ = _runtime(identity, provider)

    result = dispatch("get_project_issue_context", {"project_id": "cowork-local", "issue_key": "1"}, app)

    assert result.ok is False
    assert result.payload["error"]["code"] == expected_code


def test_malformed_gitea_response_maps_to_upstream_error(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(requests, "get", _FakeTransport([_FakeResponse(200, json_body="__missing__")]))
    provider = GiteaIssueProvider(_target(), FAKE_TOKEN)
    app, _, _ = _runtime(identity, provider)

    result = dispatch("get_project_issue_context", {"project_id": "cowork-local", "issue_key": "1"}, app)

    assert result.ok is False
    assert result.payload["error"]["code"] == "UPSTREAM_ERROR"


def test_provider_output_schema_mismatch_maps_to_upstream_error(identity: IdentityContext) -> None:
    class BrokenProvider:
        def get_issue_context(self, **_: Any) -> dict[str, Any]:
            return {"project_id": "cowork-local"}  # missing every other required field

    app, _, _ = _runtime(identity, BrokenProvider())

    result = dispatch("get_project_issue_context", {"project_id": "cowork-local", "issue_key": "1"}, app)

    assert result.ok is False
    assert result.payload["error"]["code"] == "UPSTREAM_ERROR"


# ---------------------------------------------------------------------------
# Reject before any network call
# ---------------------------------------------------------------------------
def test_invalid_issue_key_format_rejected_before_network_call(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _FakeTransport([])  # empty queue: a real call would raise IndexError
    monkeypatch.setattr(requests, "get", transport)
    provider = GiteaIssueProvider(_target(), FAKE_TOKEN)
    app, _, _ = _runtime(identity, provider)

    result = dispatch(
        "get_project_issue_context", {"project_id": "cowork-local", "issue_key": "not-a-number"}, app,
    )

    assert result.ok is False
    assert result.payload["error"]["code"] == "INVALID_INPUT"
    assert transport.calls == []


def test_invalid_cursor_rejected_before_network_call(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _FakeTransport([])
    monkeypatch.setattr(requests, "get", transport)
    provider = GiteaIssueProvider(_target(), FAKE_TOKEN)
    app, _, _ = _runtime(identity, provider)

    result = dispatch(
        "get_project_issue_context",
        {"project_id": "cowork-local", "issue_key": "1", "cursor": "not-a-number"},
        app,
    )

    assert result.ok is False
    assert result.payload["error"]["code"] == "INVALID_INPUT"
    assert transport.calls == []


# ---------------------------------------------------------------------------
# Fail-closed configuration (build_provider itself, via the real resolver)
# ---------------------------------------------------------------------------
def test_missing_gitea_env_vars_returns_unavailable_with_no_network_call(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GITEA_BASE_URL", raising=False)
    monkeypatch.delenv("GITEA_TOKEN", raising=False)
    monkeypatch.delenv("PROJECT_CONTEXT_REPO_MAP", raising=False)

    def _fail_if_called(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("Gitea must not be called when the provider is unconfigured")

    monkeypatch.setattr(requests, "get", _fail_if_called)
    policy = RecordingPolicy(allowed=True)
    app = ProjectContextRuntime(identity=identity, policy=policy, credential_resolver=ProjectProviderResolver())

    result = dispatch("get_project_issue_context", {"project_id": "cowork-local", "issue_key": "1"}, app)

    assert result.ok is False
    assert result.payload["error"]["code"] == "UNAVAILABLE"


def test_project_without_repo_mapping_returns_unavailable(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITEA_BASE_URL", "http://example.test")
    monkeypatch.setenv("GITEA_TOKEN", FAKE_TOKEN)
    monkeypatch.setenv("PROJECT_CONTEXT_REPO_MAP", '{"some-other-project": "gitea-admin/other"}')
    policy = RecordingPolicy(allowed=True)
    app = ProjectContextRuntime(identity=identity, policy=policy, credential_resolver=ProjectProviderResolver())

    result = dispatch("get_project_issue_context", {"project_id": "cowork-local", "issue_key": "1"}, app)

    assert result.ok is False
    assert result.payload["error"]["code"] == "UNAVAILABLE"


def test_target_resolver_falls_back_to_legacy_project_only_mapping(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Backward compatibility: a repo map keyed only by `project` — the
    format already documented and deployed for the pilot (see
    PLAYBOOK_COWORK_LOCAL_MCP_PILOT.md) — must still resolve, even though
    new deployments should prefer the composite `org_unit/customer/project`
    key so two different customers never collide on the same project name."""
    monkeypatch.setenv("GITEA_BASE_URL", "http://example.test")
    monkeypatch.setenv("PROJECT_CONTEXT_REPO_MAP", '{"cowork-local": "gitea-admin/cowork-local"}')

    target = EnvironmentTargetResolver().resolve(identity)

    assert target.owner == "gitea-admin"
    assert target.repo == "cowork-local"


def test_target_resolver_prefers_composite_key_over_legacy_project_key(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When BOTH a composite `org_unit/customer/project` key and a legacy
    project-only key exist in the map, the composite key must win — this is
    what actually prevents a cross-customer collision, since two customers
    sharing a project name would otherwise both match the same legacy key."""
    monkeypatch.setenv("GITEA_BASE_URL", "http://example.test")
    monkeypatch.setenv(
        "PROJECT_CONTEXT_REPO_MAP",
        '{"cowork-local": "wrong/legacy", '
        '"fsg/internal/cowork-local": "gitea-admin/cowork-local"}',
    )

    target = EnvironmentTargetResolver().resolve(identity)

    assert target.owner == "gitea-admin"
    assert target.repo == "cowork-local"


def test_target_and_credential_resolution_are_separate(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITEA_BASE_URL", "http://example.test")
    monkeypatch.setenv("GITEA_TOKEN", FAKE_TOKEN)
    monkeypatch.setenv(
        "PROJECT_CONTEXT_REPO_MAP",
        '{"fsg/internal/cowork-local": "gitea-admin/cowork-local"}',
    )

    target = EnvironmentTargetResolver().resolve(identity)
    credential = ServiceAccountCredentialResolver().resolve(identity, target)
    provider = build_provider(
        identity,
        target_resolver=EnvironmentTargetResolver(),
        credential_resolver=ServiceAccountCredentialResolver(),
    )

    assert not hasattr(target, "token")
    assert credential == FAKE_TOKEN
    assert isinstance(provider, GiteaIssueProvider)


@pytest.mark.parametrize(
    "raw_map",
    [
        "{not valid json",  # malformed JSON
        '["cowork-local", "gitea-admin/cowork-local"]',  # valid JSON, wrong shape (array)
        '{"cowork-local": 123}',  # valid JSON object, non-string value
    ],
)
def test_malformed_repo_map_returns_unavailable_with_no_network_call(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch, raw_map: str,
) -> None:
    monkeypatch.setenv("GITEA_BASE_URL", "http://example.test")
    monkeypatch.setenv("GITEA_TOKEN", FAKE_TOKEN)
    monkeypatch.setenv("PROJECT_CONTEXT_REPO_MAP", raw_map)

    def _fail_if_called(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("Gitea must not be called when the repo map is malformed")

    monkeypatch.setattr(requests, "get", _fail_if_called)
    policy = RecordingPolicy(allowed=True)
    app = ProjectContextRuntime(identity=identity, policy=policy, credential_resolver=ProjectProviderResolver())

    result = dispatch("get_project_issue_context", {"project_id": "cowork-local", "issue_key": "1"}, app)

    assert result.ok is False
    assert result.payload["error"]["code"] == "UNAVAILABLE"


@pytest.mark.parametrize(
    "slug",
    [
        "gitea-admin/cowork-local/extra",  # too many segments
        "cowork-local",                    # missing owner
        "/cowork-local",                   # empty owner
        "gitea-admin/",                    # empty repo
        "gitea-admin//cowork-local",       # empty middle segment
        "",                                # empty mapping value
    ],
)
def test_malformed_repo_slug_is_rejected_before_any_network_call(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch, slug: str,
) -> None:
    """The mapping value must be exactly 'owner/repo' — nothing else routes."""
    monkeypatch.setenv("GITEA_BASE_URL", "http://example.test")
    monkeypatch.setenv("GITEA_TOKEN", FAKE_TOKEN)
    monkeypatch.setenv("PROJECT_CONTEXT_REPO_MAP", json.dumps({"cowork-local": slug}))

    def _fail_if_called(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("Gitea must not be called for a malformed repo slug")

    monkeypatch.setattr(requests, "get", _fail_if_called)
    app = ProjectContextRuntime(
        identity=identity,
        policy=RecordingPolicy(allowed=True),
        credential_resolver=ProjectProviderResolver(),
    )

    result = dispatch("get_project_issue_context", {"project_id": "cowork-local", "issue_key": "1"}, app)

    assert result.ok is False
    assert result.payload["error"]["code"] == "UNAVAILABLE"


# ---------------------------------------------------------------------------
# Truncation + cursor pagination over `related`
# ---------------------------------------------------------------------------
def test_truncation_and_cursor_paginate_related_items(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    mentions = " ".join(f"#{n}" for n in range(2, 27))  # 25 distinct related items
    payload = _issue_payload(body=f"See also {mentions}.")
    transport = _FakeTransport([_FakeResponse(200, payload), _FakeResponse(200, payload)])
    monkeypatch.setattr(requests, "get", transport)
    provider = GiteaIssueProvider(_target(), FAKE_TOKEN)
    app, _, _ = _runtime(identity, provider)

    first = dispatch(
        "get_project_issue_context", {"project_id": "cowork-local", "issue_key": "1"}, app,
    )
    assert first.ok is True
    assert first.payload["returned"] == 20
    assert first.payload["remaining"] == 5
    assert first.payload["truncated"] is True
    assert first.payload["next_cursor"] == "20"
    assert len(first.payload["related"]) == 20
    assert first.payload["related"][0]["url"].startswith("http://example.test/")

    second = dispatch(
        "get_project_issue_context",
        {"project_id": "cowork-local", "issue_key": "1", "cursor": first.payload["next_cursor"]},
        app,
    )
    assert second.ok is True
    assert second.payload["returned"] == 5
    assert second.payload["remaining"] == 0
    assert second.payload["truncated"] is False
    assert second.payload["next_cursor"] is None


def test_full_detail_uses_a_larger_related_page_than_standard(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression guard: `detail='full'` must genuinely page differently
    from `detail='standard'` (100 vs 20) — this was previously unverified."""
    mentions = " ".join(f"#{n}" for n in range(2, 32))  # 30 distinct related items
    payload = _issue_payload(body=f"See also {mentions}.")
    monkeypatch.setattr(requests, "get", _FakeTransport([_FakeResponse(200, payload)]))
    provider = GiteaIssueProvider(_target(), FAKE_TOKEN)
    app, _, _ = _runtime(identity, provider)

    result = dispatch(
        "get_project_issue_context",
        {"project_id": "cowork-local", "issue_key": "1", "detail": "full"},
        app,
    )

    assert result.ok is True
    assert result.payload["returned"] == 30
    assert result.payload["remaining"] == 0
    assert result.payload["truncated"] is False
    assert result.payload["next_cursor"] is None


def test_url_fragment_is_not_mistaken_for_a_related_issue(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression guard: a doc-anchor link like '.../guide#42' must not be
    reported as a related item pointing to issue #42, while a plain '#7'
    text mention elsewhere in the same body still must be."""
    body = "See http://example.test/gitea-admin/cowork-local/wiki/guide#42 and also #7 directly."
    payload = _issue_payload(body=body)
    monkeypatch.setattr(requests, "get", _FakeTransport([_FakeResponse(200, payload)]))
    provider = GiteaIssueProvider(_target(), FAKE_TOKEN)
    app, _, _ = _runtime(identity, provider)

    result = dispatch("get_project_issue_context", {"project_id": "cowork-local", "issue_key": "1"}, app)

    related_ids = {item["item_id"] for item in result.payload["related"]}
    assert related_ids == {"7"}


def test_related_excludes_number_that_is_only_a_markdown_link_label(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression guard (found via a real Gitea issue during manual smoke
    testing): a Markdown link whose LABEL happens to contain '#<number>' —
    e.g. a cross-repository pull-request reference — must not be re-guessed
    as a same-repo issue mention, because that silently points at the wrong
    resource. A plain '#9' mention elsewhere in the same body must still be
    picked up."""
    body = (
        "See [other-repo PR #4](http://example.test/other-repo/pulls/4) "
        "and also #9 directly."
    )
    payload = _issue_payload(body=body)
    monkeypatch.setattr(requests, "get", _FakeTransport([_FakeResponse(200, payload)]))
    provider = GiteaIssueProvider(_target(), FAKE_TOKEN)
    app, _, _ = _runtime(identity, provider)

    result = dispatch("get_project_issue_context", {"project_id": "cowork-local", "issue_key": "1"}, app)

    related_ids = {item["item_id"] for item in result.payload["related"]}
    assert related_ids == {"9"}


def test_acceptance_criteria_is_scoped_to_its_own_heading_not_definition_of_done(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression guard (found via a real Gitea issue during manual smoke
    testing): a body with a SEPARATE 'Definition of Done' checklist section
    must not have those items folded into acceptance_criteria."""
    body = (
        "# Acceptance Criteria\n\n"
        "- [ ] Real acceptance item one.\n"
        "- [ ] Real acceptance item two.\n\n"
        "# Definition of Done\n\n"
        "- [ ] Unrelated DoD item one.\n"
        "- [ ] Unrelated DoD item two.\n"
    )
    payload = _issue_payload(body=body)
    monkeypatch.setattr(requests, "get", _FakeTransport([_FakeResponse(200, payload)]))
    provider = GiteaIssueProvider(_target(), FAKE_TOKEN)
    app, _, _ = _runtime(identity, provider)

    result = dispatch("get_project_issue_context", {"project_id": "cowork-local", "issue_key": "1"}, app)

    assert result.payload["acceptance_criteria"] == [
        "Real acceptance item one.",
        "Real acceptance item two.",
    ]


@pytest.mark.parametrize("heading", ["Tiêu chí hoàn thành", "Tiêu chí chấp nhận"])
def test_acceptance_criteria_supports_vietnamese_headings(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch, heading: str,
) -> None:
    body = (
        f"## {heading}\n\n"
        "- [ ] Điều kiện đúng.\n\n"
        "## Definition of Done\n\n"
        "- [ ] Checklist không liên quan.\n"
    )
    monkeypatch.setattr(
        requests,
        "get",
        _FakeTransport([_FakeResponse(200, _issue_payload(body=body))]),
    )
    provider = GiteaIssueProvider(_target(), FAKE_TOKEN)
    app, _, _ = _runtime(identity, provider)

    result = dispatch(
        "get_project_issue_context",
        {"project_id": "cowork-local", "issue_key": "1"},
        app,
    )

    assert result.payload["acceptance_criteria"] == ["Điều kiện đúng."]


def test_acceptance_criteria_falls_back_to_whole_body_without_a_heading(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An issue with no 'Acceptance Criteria' heading at all (no fixed
    template) must still get a best-effort result from the whole body,
    rather than always coming back empty."""
    body = "Ad-hoc issue, no headings.\n\n- [ ] Just do the thing.\n"
    payload = _issue_payload(body=body)
    monkeypatch.setattr(requests, "get", _FakeTransport([_FakeResponse(200, payload)]))
    provider = GiteaIssueProvider(_target(), FAKE_TOKEN)
    app, _, _ = _runtime(identity, provider)

    result = dispatch("get_project_issue_context", {"project_id": "cowork-local", "issue_key": "1"}, app)

    assert result.payload["acceptance_criteria"] == ["Just do the thing."]


def test_acceptance_criteria_does_not_scan_unrelated_sections(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = "# Definition of Done\n\n- [ ] Checklist không phải tiêu chí chấp nhận.\n"
    monkeypatch.setattr(
        requests,
        "get",
        _FakeTransport([_FakeResponse(200, _issue_payload(body=body))]),
    )
    provider = GiteaIssueProvider(_target(), FAKE_TOKEN)
    app, _, _ = _runtime(identity, provider)

    result = dispatch(
        "get_project_issue_context",
        {"project_id": "cowork-local", "issue_key": "1"},
        app,
    )

    assert result.payload["acceptance_criteria"] == []


def test_summary_detail_omits_related_and_shortens_description(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    long_paragraph = "First paragraph. " * 40  # > 280 chars
    payload = _issue_payload(body=f"{long_paragraph}\n\nSecond paragraph mentions #2.")
    monkeypatch.setattr(requests, "get", _FakeTransport([_FakeResponse(200, payload)]))
    provider = GiteaIssueProvider(_target(), FAKE_TOKEN)
    app, _, _ = _runtime(identity, provider)

    result = dispatch(
        "get_project_issue_context",
        {"project_id": "cowork-local", "issue_key": "1", "detail": "summary"},
        app,
    )

    assert result.ok is True
    assert len(result.payload["description"]) <= 280
    assert result.payload["related"] == []
    assert result.payload["returned"] == 0
    assert result.payload["remaining"] == 1
    assert result.payload["truncated"] is True
    assert result.payload["next_cursor"] is None


# ---------------------------------------------------------------------------
# No credential/exception leakage
# ---------------------------------------------------------------------------
def test_unexpected_transport_error_does_not_leak_credential_or_raw_exception(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    leaking_exception = requests.exceptions.ConnectionError(
        f"connect failed for token={FAKE_TOKEN} at internal-host:5432"
    )
    monkeypatch.setattr(requests, "get", _FakeTransport([leaking_exception]))
    provider = GiteaIssueProvider(_target(), FAKE_TOKEN)
    app, _, _ = _runtime(identity, provider)

    result = dispatch("get_project_issue_context", {"project_id": "cowork-local", "issue_key": "1"}, app)

    assert result.ok is False
    assert result.payload["error"]["code"] == "UPSTREAM_ERROR"
    payload_text = str(result.payload)
    assert FAKE_TOKEN not in payload_text
    assert "internal-host" not in payload_text


def test_not_found_message_does_not_distinguish_missing_from_inaccessible(
    identity: IdentityContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Security requirement: a denial/miss must not reveal whether the
    underlying resource exists — the safe_message must stay generic."""
    monkeypatch.setattr(requests, "get", _FakeTransport([_FakeResponse(404)]))
    provider = GiteaIssueProvider(_target(), FAKE_TOKEN)
    app, _, _ = _runtime(identity, provider)

    result = dispatch("get_project_issue_context", {"project_id": "cowork-local", "issue_key": "1"}, app)

    message = result.payload["error"]["message"].lower()
    assert "not found or is not accessible" in message
    assert "does not exist" not in message
