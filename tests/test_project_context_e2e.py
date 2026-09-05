"""End-to-end flow across BOTH Project Context MCP tools.

    Issue -> get_project_issue_context -> requirement context
          -> search_project_knowledge -> related project knowledge -> evidence

No LLM is involved: the "agent" is deterministic test code that takes the
requirement text tool #1 returned and feeds it to tool #2, which is exactly the
hand-off the two tools exist to support. Gitea is mocked; knowledge is a
synthetic workspace under tmp_path.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import requests
from cowork_local.mcp_servers.project_context.foundation import (
    IdentityContext,
    ProjectContextRuntime,
)
from cowork_local.mcp_servers.project_context.runtime import (
    ProjectProviderResolver,
    ProjectScopePolicy,
)
from cowork_local.mcp_servers.project_context.server import dispatch

PROJECT = "cowork-local"
OTHER_PROJECT = "other-customer"
FAKE_TOKEN = "e2e-test-token"  # noqa: S105 - test-only sentinel, never a real credential

ISSUE_BODY = """The login screen must lock an account after repeated failed attempts.

# Acceptance Criteria

- [ ] The account locks after five failed login attempts.
- [ ] An operator can clear the lock from the admin console.

# Definition of Done

- [ ] Release notes updated.
"""


@dataclass
class _Response:
    status_code: int
    payload: dict[str, Any]

    def json(self) -> dict[str, Any]:
        return self.payload


@pytest.fixture
def identity() -> IdentityContext:
    return IdentityContext(
        actor_id="agent-e2e",
        org_unit="fsg",
        customer="internal",
        project=PROJECT,
        granted_scopes=frozenset({"read"}),
    )


@pytest.fixture
def wired_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Both providers wired: a mocked Gitea issue and a synthetic knowledge base."""
    base = tmp_path / "workspaces"
    (base / PROJECT).mkdir(parents=True)
    (base / OTHER_PROJECT).mkdir(parents=True)

    (base / PROJECT / "authentication-basic-design.md").write_text(
        "# Authentication Basic Design\n"
        "The account lock engages after five failed login attempts and is recorded "
        "in the audit log.\n\n"
        "# Unlock Procedure\n"
        "An operator clears the account lock from the admin console.\n",
        encoding="utf-8",
    )
    (base / OTHER_PROJECT / "other-auth.md").write_text(
        "# Other Customer Auth\n"
        "This other-customer account lock policy uses failed login thresholds too.\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("PROJECT_CONTEXT_KNOWLEDGE_ROOT", str(base))
    monkeypatch.setenv("GITEA_BASE_URL", "http://gitea.test")
    monkeypatch.setenv("GITEA_TOKEN", FAKE_TOKEN)
    monkeypatch.setenv(
        "PROJECT_CONTEXT_REPO_MAP", json.dumps({PROJECT: "gitea-admin/cowork-local"}),
    )

    def _fake_get(url: str, headers: dict[str, str] | None = None, timeout: float | None = None):
        del headers, timeout
        assert "/issues/7" in url
        return _Response(
            status_code=200,
            payload={
                "title": "Lock the account after repeated failed logins",
                "state": "open",
                "body": ISSUE_BODY,
                "html_url": "http://gitea.test/gitea-admin/cowork-local/issues/7",
                "updated_at": "2026-09-01T09:00:00Z",
            },
        )

    monkeypatch.setattr(requests, "get", _fake_get)
    return base


def production_runtime(identity: IdentityContext) -> ProjectContextRuntime:
    """The real policy and the real provider resolver — no injected doubles."""
    return ProjectContextRuntime(
        identity=identity,
        policy=ProjectScopePolicy(),
        credential_resolver=ProjectProviderResolver(),
    )


def derive_query(issue_context: dict[str, Any]) -> str:
    """Stand-in for the agent: turn the requirement into a knowledge query."""
    first_criterion = issue_context["acceptance_criteria"][0]
    words = re.findall(r"[A-Za-z]+", first_criterion.casefold())
    stopwords = {"the", "a", "an", "after", "can", "from", "is", "must", "and"}
    return " ".join(word for word in words if word not in stopwords)


def test_issue_context_feeds_knowledge_search_with_evidence(
    identity: IdentityContext, wired_environment: Path,
) -> None:
    runtime = production_runtime(identity)

    # ---- Step 1: Issue -> requirement context ---------------------------
    issue_result = dispatch(
        "get_project_issue_context",
        {"project_id": PROJECT, "issue_key": "7"},
        runtime,
    )
    assert issue_result.ok is True, issue_result.payload
    issue = issue_result.payload

    assert issue["title"] == "Lock the account after repeated failed logins"
    assert issue["status"] == "open"
    # Acceptance criteria are scoped to their own heading — Definition of Done
    # items must not bleed in.
    assert issue["acceptance_criteria"] == [
        "The account locks after five failed login attempts.",
        "An operator can clear the lock from the admin console.",
    ]
    assert "Release notes updated." not in issue["acceptance_criteria"]
    assert issue["source"]["url"].startswith("http://gitea.test/")
    assert issue["source"]["revision"]

    # ---- Step 2: requirement -> related project knowledge ---------------
    query = derive_query(issue)
    knowledge_result = dispatch(
        "search_project_knowledge",
        {"project_id": PROJECT, "query": query},
        runtime,
    )
    assert knowledge_result.ok is True, knowledge_result.payload
    knowledge = knowledge_result.payload

    assert knowledge["items"], f"the design doc must be found for query {query!r}"
    top = knowledge["items"][0]
    assert top["document_id"] == "authentication-basic-design.md"
    assert "account lock" in top["excerpt"].casefold()

    # ---- Step 3: every answer carries openable evidence -----------------
    assert top["source"]["system"] == "cowork-workspace"
    assert top["source"]["url"].startswith("file://")
    assert top["source"]["revision"].startswith("mtime:")
    assert top["chunk_id"].startswith(top["document_id"])

    # ---- The two tools stay inside the same project ---------------------
    retrieved = json.dumps(knowledge["items"])
    assert OTHER_PROJECT not in retrieved
    assert "other-auth.md" not in retrieved
    for item in knowledge["items"]:
        assert f"/{PROJECT}/" in item["source"]["url"]

    # ---- Both steps are independently traceable -------------------------
    assert issue["correlation_id"] != knowledge["correlation_id"]

    # ---- Neither step leaked the credential -----------------------------
    combined = json.dumps(issue) + json.dumps(knowledge)
    assert FAKE_TOKEN not in combined


def test_the_same_flow_is_denied_for_an_out_of_scope_project(
    identity: IdentityContext, wired_environment: Path,
) -> None:
    """Both tools refuse the same out-of-scope project the same way."""
    runtime = production_runtime(identity)

    issue_result = dispatch(
        "get_project_issue_context",
        {"project_id": OTHER_PROJECT, "issue_key": "7"},
        runtime,
    )
    knowledge_result = dispatch(
        "search_project_knowledge",
        {"project_id": OTHER_PROJECT, "query": "account lock"},
        runtime,
    )

    assert issue_result.ok is False
    assert knowledge_result.ok is False
    assert issue_result.payload["error"]["code"] == "DENIED"
    assert knowledge_result.payload["error"]["code"] == "DENIED"


def test_both_tools_are_advertised_as_read_only_context_tools() -> None:
    """The MVP surface is exactly two production-oriented read tools."""
    from cowork_local.mcp_servers.project_context.registry import TOOLS_BY_NAME

    for name in ("get_project_issue_context", "search_project_knowledge"):
        tool = TOOLS_BY_NAME[name]
        schema = tool.input_model.model_json_schema()
        assert schema.get("additionalProperties") is False
        # No write-shaped argument exists anywhere on the input contract.
        for field in schema["properties"]:
            assert not any(
                verb in field
                for verb in ("write", "update", "create", "delete", "comment", "body")
            ), f"{name}.{field} looks like a write surface"
