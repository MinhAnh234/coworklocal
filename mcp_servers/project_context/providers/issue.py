"""Read-only Gitea adapter for ``get_project_issue_context``.

Policy runs before ``build_provider``. Target and credential resolution stay
separate so the pilot service account can later be replaced by on-behalf-of
credentials without changing the tool or provider contract.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

import requests

from ..foundation import IdentityContext, ProviderError, decode_offset_cursor

# ---- tunables (documented, not hardcoded secrets) -------------------------
_REQUEST_TIMEOUT_SECONDS = 10
_STANDARD_RELATED_PAGE_SIZE = 20
_FULL_RELATED_PAGE_SIZE = 100
_SUMMARY_DESCRIPTION_CHARS = 280
_MAX_DESCRIPTION_CHARS = 20_000
_MAX_SCAN_CHARS = 200_000  # hard cap on regex work, independent of the display cap above
_TRUNCATION_NOTICE = "\n\n[description truncated: exceeds the display size limit]"

_ISSUE_KEY_PATTERN = re.compile(r"^[1-9][0-9]*$")
_CHECKLIST_PATTERN = re.compile(r"^[-*]\s+\[[ xX]\]\s+(.+)$", re.MULTILINE)
_MENTION_PATTERN = re.compile(r"(?<!\w)#([1-9][0-9]*)\b")
_URL_PATTERN = re.compile(r"https?://\S+")
# A whole Markdown link span, label + target together — stripped as ONE unit
# so a `#<number>` that is only the link's label text (often a cross-repo or
# pull-request reference) is never re-guessed as a same-repo issue mention.
_MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]*\]\([^)]*\)")
# ATX heading line, e.g. "# Acceptance Criteria" / "## Acceptance Criteria".
_HEADING_PATTERN = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*$", re.MULTILINE)
_ACCEPTANCE_HEADING_NAMES = (
    "acceptance criteria",
    "tiêu chí hoàn thành",
    "tiêu chí chấp nhận",
)


def _extract_heading_section(text: str, heading_names: tuple[str, ...]) -> str | None:
    """Return the body of the first ATX heading whose title case-insensitively
    matches one of ``heading_names``, up to the next heading of equal or
    shallower depth (or the end of ``text``). Returns ``None`` when no such
    heading exists, so the caller can fall back to the whole body."""
    wanted = {name.strip().casefold() for name in heading_names}
    headings = list(_HEADING_PATTERN.finditer(text))
    for index, match in enumerate(headings):
        heading = match.group(2).strip().rstrip("#").strip().casefold()
        if heading not in wanted:
            continue
        level = len(match.group(1))
        end = len(text)
        for later in headings[index + 1 :]:
            if len(later.group(1)) <= level:
                end = later.start()
                break
        return text[match.end() : end]
    return None


class IssueProvider(Protocol):
    """Nguồn cấp bối cảnh issue/ticket cho một project.

    Chỉ là hợp đồng: bản cài đặt thật được nối vào qua ``build_provider``.
    """
    def get_issue_context(self, **arguments: Any) -> dict[str, Any]:
        """Trả về bối cảnh issue/ticket theo tham số của tool."""
        ...


class UnconfiguredIssueProvider:
    """Bản thay thế khi chưa cấu hình nguồn issue/ticket thật.

    Luôn ném lỗi ``UNAVAILABLE`` thay vì trả dữ liệu rỗng — rỗng sẽ bị Agent
    hiểu nhầm là "tra rồi, không có gì", còn lỗi thì nói đúng sự thật là
    chưa có nguồn nào được nối.
    """
    def get_issue_context(self, **arguments: Any) -> dict[str, Any]:
        """Luôn báo chưa cấu hình; không cho thử lại."""
        raise ProviderError(
            "UNAVAILABLE",
            "The issue provider is not configured for this environment.",
            retryable=False,
        )


@dataclass(frozen=True)
class _GiteaRepoTarget:
    base_url: str
    owner: str
    repo: str
    project_id: str


class GiteaTargetResolver(Protocol):
    def resolve(self, identity: IdentityContext) -> _GiteaRepoTarget: ...


class GiteaCredentialResolver(Protocol):
    def resolve(self, identity: IdentityContext, target: _GiteaRepoTarget) -> str: ...


def _load_repo_map() -> dict[str, str]:
    raw = os.environ.get("PROJECT_CONTEXT_REPO_MAP", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProviderError(
            "UNAVAILABLE",
            "PROJECT_CONTEXT_REPO_MAP is not valid JSON.",
            retryable=False,
        ) from exc
    if not isinstance(parsed, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in parsed.items()
    ):
        raise ProviderError(
            "UNAVAILABLE",
            "PROJECT_CONTEXT_REPO_MAP must map identity or project keys to 'owner/repo'.",
            retryable=False,
        )
    return parsed


@dataclass(frozen=True)
class EnvironmentTargetResolver:
    def resolve(self, identity: IdentityContext) -> _GiteaRepoTarget:
        base_url = os.environ.get("GITEA_BASE_URL", "").strip().rstrip("/")
        if not base_url:
            raise ProviderError(
                "UNAVAILABLE",
                "GITEA_BASE_URL is not configured for this environment.",
                retryable=False,
            )
        repo_map = _load_repo_map()
        identity_key = f"{identity.org_unit}/{identity.customer}/{identity.project}"
        slug = repo_map.get(identity_key) or repo_map.get(identity.project, "")
        parts = slug.split("/")
        if len(parts) != 2 or not all(parts):
            raise ProviderError(
                "UNAVAILABLE",
                "This identity is not mapped to an approved Gitea repository.",
                retryable=False,
            )
        owner, repo = parts
        return _GiteaRepoTarget(
            base_url=base_url,
            owner=owner,
            repo=repo,
            project_id=identity.project,
        )


@dataclass(frozen=True)
class ServiceAccountCredentialResolver:
    def resolve(self, identity: IdentityContext, target: _GiteaRepoTarget) -> str:
        del identity, target
        token = os.environ.get("GITEA_TOKEN", "").strip()
        if not token:
            raise ProviderError(
                "UNAVAILABLE",
                "GITEA_TOKEN is not configured for this environment.",
                retryable=False,
            )
        return token


def build_provider(
    identity: IdentityContext,
    *,
    target_resolver: GiteaTargetResolver | None = None,
    credential_resolver: GiteaCredentialResolver | None = None,
) -> IssueProvider:
    """Compose routing and credentials only after the policy has allowed the call."""
    target = (target_resolver or EnvironmentTargetResolver()).resolve(identity)
    token = (credential_resolver or ServiceAccountCredentialResolver()).resolve(identity, target)
    return GiteaIssueProvider(target, token)


class GiteaIssueProvider:
    """Read-only adapter mapping one Gitea issue/PR onto the neutral schema."""

    def __init__(self, target: _GiteaRepoTarget, token: str) -> None:
        self._target = target
        self._token = token

    def get_issue_context(
        self,
        *,
        project_id: str,
        issue_key: str,
        detail: str,
        cursor: str | None,
        **_: Any,
    ) -> dict[str, Any]:
        if project_id != self._target.project_id:
            # Defense in depth: the runtime's policy already guarantees this
            # can never happen (DENIED would have fired first), but the
            # provider never trusts caller-supplied routing regardless.
            raise ProviderError(
                "INTERNAL",
                "Resolved provider does not match the requested project.",
                retryable=False,
            )
        if not _ISSUE_KEY_PATTERN.match(issue_key):
            raise ProviderError(
                "INVALID_INPUT",
                "issue_key must be a positive work item number.",
                retryable=False,
            )
        offset = decode_offset_cursor(cursor)

        payload = self._fetch_issue(issue_key)

        title = str(payload.get("title") or "")
        raw_state = str(payload.get("state") or "")
        status = raw_state if raw_state in {"open", "closed"} else "unknown"
        body = str(payload.get("body") or "")
        description = self._build_description(body, detail)
        # Bounded regardless of the actual body size: caps worst-case regex
        # cost, independently of `description`'s own display-only cap.
        scan_text = body[:_MAX_SCAN_CHARS]
        acceptance_section = _extract_heading_section(scan_text, _ACCEPTANCE_HEADING_NAMES)
        acceptance_text = acceptance_section
        if acceptance_text is None:
            acceptance_text = "" if _HEADING_PATTERN.search(scan_text) else scan_text
        acceptance_criteria = tuple(
            _CHECKLIST_PATTERN.findall(acceptance_text)
        )
        related_all = self._extract_related(scan_text, issue_key)

        related_page, returned, remaining, truncated, next_cursor = self._paginate_related(
            related_all, detail, offset,
        )

        html_url = str(
            payload.get("html_url")
            or f"{self._target.base_url}/{self._target.owner}/{self._target.repo}/issues/{issue_key}"
        )
        updated_at = str(payload.get("updated_at") or "")
        retrieved_at = datetime.now(timezone.utc).isoformat()

        return {
            "project_id": project_id,
            "issue_key": issue_key,
            "title": title,
            "status": status,
            "description": description,
            "acceptance_criteria": acceptance_criteria,
            "related": related_page,
            "source": {
                "system": "gitea",
                "url": html_url,
                "revision": f"issue-updated:{updated_at or retrieved_at}",
                "retrieved_at": retrieved_at,
            },
            "truncated": truncated,
            "returned": returned,
            "remaining": remaining,
            "next_cursor": next_cursor,
        }

    # ---- internals ---------------------------------------------------
    def _build_description(self, body: str, detail: str) -> str:
        text = body.strip()
        if detail == "summary":
            return text.split("\n\n", 1)[0][:_SUMMARY_DESCRIPTION_CHARS]
        if len(text) > _MAX_DESCRIPTION_CHARS:
            return text[:_MAX_DESCRIPTION_CHARS] + _TRUNCATION_NOTICE
        return text

    def _extract_related(self, body: str, issue_key: str) -> tuple[dict[str, str], ...]:
        # Strip whole `[label](url)` spans FIRST (as one unit) so a `#<number>`
        # that only appears as a Markdown link's label — often a cross-repo or
        # pull-request reference with its own, possibly different, URL right
        # there — is never re-guessed as "issue #<number> in this repo".
        text_without_links = _MARKDOWN_LINK_PATTERN.sub(" ", body)
        # Then strip any remaining bare URLs so a doc-anchor link like
        # ".../guide#42" is never mistaken for a cross-reference to issue #42.
        text_without_urls = _URL_PATTERN.sub(" ", text_without_links)
        numbers = sorted({int(n) for n in _MENTION_PATTERN.findall(text_without_urls) if n != issue_key})
        return tuple(
            {
                "item_id": str(number),
                "relation": "mentioned",
                "title": f"Referenced item #{number}",
                "url": f"{self._target.base_url}/{self._target.owner}/{self._target.repo}/issues/{number}",
            }
            for number in numbers
        )

    def _paginate_related(
        self,
        related_all: tuple[dict[str, str], ...],
        detail: str,
        offset: int,
    ) -> tuple[tuple[dict[str, str], ...], int, int, bool, str | None]:
        if detail == "summary":
            # Summary mode intentionally omits related items outright; it is
            # not a size-limit truncation, so callers who need them must
            # call again with detail="standard"/"full".
            remaining = len(related_all)
            return (), 0, remaining, remaining > 0, None

        page_size = _FULL_RELATED_PAGE_SIZE if detail == "full" else _STANDARD_RELATED_PAGE_SIZE
        page = related_all[offset : offset + page_size]
        remaining = max(0, len(related_all) - (offset + page_size))
        truncated = remaining > 0
        next_cursor = str(offset + page_size) if truncated else None
        return page, len(page), remaining, truncated, next_cursor

    def _fetch_issue(self, issue_key: str) -> dict[str, Any]:
        url = (
            f"{self._target.base_url}/api/v1/repos/{self._target.owner}/"
            f"{self._target.repo}/issues/{issue_key}"
        )
        headers = {"Authorization": f"token {self._token}"}
        try:
            response = requests.get(url, headers=headers, timeout=_REQUEST_TIMEOUT_SECONDS)
        except requests.exceptions.Timeout as exc:
            raise ProviderError(
                "UPSTREAM_TIMEOUT", "The Gitea request timed out.", retryable=True,
            ) from exc
        except requests.exceptions.RequestException as exc:
            # Never surface str(exc) — it can embed the request URL/host and,
            # in some transport errors, request headers.
            raise ProviderError(
                "UPSTREAM_ERROR", "The Gitea request failed.", retryable=True,
            ) from exc

        if response.status_code == 404:
            raise ProviderError(
                "NOT_FOUND",
                "The work item was not found or is not accessible.",
                retryable=False,
            )
        if response.status_code == 429:
            raise ProviderError("RATE_LIMITED", "Gitea rate-limited this request.", retryable=True)
        if response.status_code in (401, 403):
            raise ProviderError(
                "UPSTREAM_ERROR",
                "The read-only Gitea credential could not access the repository.",
                retryable=False,
            )
        if response.status_code >= 500:
            raise ProviderError("UPSTREAM_ERROR", "Gitea returned a server error.", retryable=True)
        if response.status_code != 200:
            raise ProviderError(
                "UPSTREAM_ERROR", "Gitea returned an unexpected response.", retryable=False,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError(
                "UPSTREAM_ERROR",
                "Gitea returned a response that could not be parsed.",
                retryable=False,
            ) from exc
        if not isinstance(data, dict):
            raise ProviderError(
                "UPSTREAM_ERROR", "Gitea returned an unexpected response shape.", retryable=False,
            )
        return data
