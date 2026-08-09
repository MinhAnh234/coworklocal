#!/usr/bin/env python3
"""Idempotently configure the lightweight Gitea surface for Cowork Local.

The script never stores a credential. Supply GITEA_TOKEN or GITEA_API_TOKEN in
the process environment. Run it after the stable branch has been pushed when
using --protect-branch.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_DESCRIPTION = (
    "Cowork Local — internal AI cowork platform and shared foundation for "
    "FSG AI capabilities."
)

LABELS = {
    "type:feature": ("0e8a16", "New Cowork capability"),
    "type:bug": ("d73a4a", "Defect or regression"),
    "type:test": ("1d76db", "Tests and hardening"),
    "type:security": ("b60205", "Security-sensitive change"),
    "type:performance": ("fbca04", "Performance work"),
    "type:core-ai-contribution": ("5319e7", "Selected FSG AI Core contribution"),
    "area:agent": ("006b75", "Agent capability"),
    "area:mcp": ("006b75", "MCP or connector integration"),
    "area:workflow": ("006b75", "Cowork workflow"),
    "area:security": ("006b75", "Security controls"),
    "area:retrieval": ("006b75", "Knowledge or retrieval integration"),
    "area:model-routing": ("006b75", "Model routing and fallback"),
    "review:cowork": ("c2e0c6", "Cowork Team review"),
    "review:core-ai": ("c2e0c6", "Core AI pre-review"),
    "source:core-ai": ("bfdadc", "Originated from the Core AI task system"),
    "needs:cowork-review": ("d4c5f9", "Waiting for Cowork Team review"),
}


class ApiError(RuntimeError):
    pass


@dataclass
class GiteaApi:
    base_url: str
    token: str

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        expected: tuple[int, ...] = (200,),
    ) -> Any:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url.rstrip('/')}/api/v1{path}",
            data=body,
            method=method,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"token {self.token}",
            },
        )
        try:
            with urlopen(request, timeout=20) as response:
                raw = response.read()
                if response.status not in expected:
                    raise ApiError(f"Gitea returned HTTP {response.status} for {method} {path}")
                return json.loads(raw) if raw else None
        except HTTPError as exc:
            detail = ""
            try:
                detail = json.loads(exc.read()).get("message", "")
            except (json.JSONDecodeError, AttributeError):
                pass
            suffix = f": {detail}" if detail else ""
            raise ApiError(f"Gitea returned HTTP {exc.code} for {method} {path}{suffix}") from None
        except URLError as exc:
            raise ApiError(f"Cannot reach Gitea for {method} {path}: {exc.reason}") from None


def repo_path(owner: str, repo: str) -> str:
    return f"/repos/{quote(owner, safe='')}/{quote(repo, safe='')}"


def ensure_repo(api: GiteaApi, owner: str, repo: str, description: str) -> None:
    path = repo_path(owner, repo)
    try:
        api.request("GET", path)
        print(f"Repository exists: {owner}/{repo}")
    except ApiError as exc:
        if "HTTP 404" not in str(exc):
            raise
        api.request(
            "POST",
            "/user/repos",
            {
                "name": repo,
                "description": description,
                "private": True,
                "auto_init": False,
                "default_branch": "main",
                "has_issues": True,
                "has_pull_requests": True,
            },
            expected=(201,),
        )
        print(f"Repository created: {owner}/{repo} (private)")

    api.request(
        "PATCH",
        path,
        {
            "description": description,
            "private": True,
            "default_branch": "main",
            "has_issues": True,
            "has_pull_requests": True,
            "has_actions": True,
        },
    )
    print("Repository settings verified")


def ensure_labels(api: GiteaApi, owner: str, repo: str) -> None:
    path = f"{repo_path(owner, repo)}/labels"
    labels = api.request("GET", f"{path}?limit=50") or []
    existing = {item["name"]: item for item in labels}
    for name, (color, description) in LABELS.items():
        current = existing.get(name)
        payload = {"name": name, "color": color, "description": description}
        if current is None:
            api.request("POST", path, payload, expected=(201,))
            print(f"Label created: {name}")
        elif current.get("color", "").lstrip("#").lower() != color or current.get("description", "") != description:
            api.request("PATCH", f"{path}/{current['id']}", payload)
            print(f"Label updated: {name}")


def ensure_protection(api: GiteaApi, owner: str, repo: str, branch: str) -> None:
    base = f"{repo_path(owner, repo)}/branch_protections"
    encoded_branch = quote(branch, safe="")
    payload = {
        "rule_name": branch,
        "branch_name": branch,
        "enable_push": False,
        "enable_push_whitelist": False,
        "enable_force_push": False,
        "enable_force_push_allowlist": False,
        "enable_merge_whitelist": False,
        "enable_status_check": False,
        "status_check_contexts": [],
        "required_approvals": 1,
        "dismiss_stale_approvals": True,
        "block_on_rejected_reviews": True,
        "block_on_official_review_requests": True,
        "block_on_outdated_branch": False,
        "require_signed_commits": False,
        "block_admin_merge_override": False,
    }
    try:
        api.request("GET", f"{base}/{encoded_branch}")
    except ApiError as exc:
        if "HTTP 404" not in str(exc):
            raise
        api.request("POST", base, payload, expected=(201,))
        print(f"Branch protection created: {branch}")
    else:
        edit_payload = dict(payload)
        edit_payload.pop("branch_name", None)
        edit_payload.pop("rule_name", None)
        api.request("PATCH", f"{base}/{encoded_branch}", edit_payload)
        print(f"Branch protection updated: {branch}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://34.143.229.138")
    parser.add_argument("--owner", default="gitea-admin")
    parser.add_argument("--repo", default="cowork-local")
    parser.add_argument("--description", default=DEFAULT_DESCRIPTION)
    parser.add_argument(
        "--protect-branch",
        metavar="BRANCH",
        help="Create/update protection after this branch has been pushed",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = os.getenv("GITEA_TOKEN") or os.getenv("GITEA_API_TOKEN")
    if not token:
        print("Set GITEA_TOKEN or GITEA_API_TOKEN in the process environment.", file=sys.stderr)
        return 2

    api = GiteaApi(args.base_url, token)
    try:
        ensure_repo(api, args.owner, args.repo, args.description)
        ensure_labels(api, args.owner, args.repo)
        if args.protect_branch:
            ensure_protection(api, args.owner, args.repo, args.protect_branch)
    except ApiError as exc:
        print(f"bootstrap failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
