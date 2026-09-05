"""Read-only project-knowledge adapter for search_project_knowledge.

Retrieval reuses what Cowork already owns rather than adding a vector store,
an embedding pipeline, or a new RAG framework:

* core.projects already defines a project's *knowledge* as the files at its
  workspace root, and already confines one project's agent to that folder.
  That same folder is the only corpus this provider will ever read, which is
  what makes project isolation structural instead of a filter applied later.
* core.doc_extract.extract_text already turns docx/pptx/xlsx/pdf/text into
  plain text for prompt building, so this provider inherits format support.

Ranking is a bounded lexical (term-overlap) scan over those files. It is a
deliberate floor, not a claim of semantic search -- see the ponytail note on
_score_chunk.

Target and access resolution stay separate here, exactly as in the issue
provider, so a pilot workspace root can later become a served knowledge base
without changing the tool or the provider contract.
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from ..foundation import IdentityContext, ProviderError, decode_offset_cursor

# ---- tunables (documented, not hardcoded secrets) -------------------------
_PAGE_SIZE_BY_DETAIL = {"summary": 3, "standard": 5, "full": 10}
_EXCERPT_CHARS_BY_DETAIL = {"summary": 200, "standard": 600, "full": 1200}
_MAX_FILES_SCANNED = 200
_MAX_FILE_BYTES = 2_000_000
_MAX_CHARS_PER_DOCUMENT = 200_000
_CHUNK_CHARS = 1_200
_MAX_CANDIDATES = 500
_MAX_QUERY_TERMS = 32

_KNOWLEDGE_SUFFIXES = frozenset({
    ".md", ".markdown", ".txt", ".rst", ".csv", ".json", ".yaml", ".yml",
    ".docx", ".docm", ".pptx", ".xlsx", ".xlsm", ".pdf", ".odt", ".odp", ".ods",
})
_WORD_PATTERN = re.compile(r"\w+", re.UNICODE)
_HEADING_PATTERN = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*$", re.MULTILINE)


class KnowledgeProvider(Protocol):
    """Nguồn cấp bối cảnh tri thức nội bộ cho một project.

    Chỉ là hợp đồng: bản cài đặt thật được nối vào qua ``build_provider``.
    """
    def search_knowledge(self, **arguments: Any) -> dict[str, Any]:
        """Trả về bối cảnh tri thức nội bộ theo tham số của tool."""
        ...


class UnconfiguredKnowledgeProvider:
    """Bản thay thế khi chưa cấu hình nguồn tri thức nội bộ thật.

    Luôn ném lỗi ``UNAVAILABLE`` thay vì trả dữ liệu rỗng — rỗng sẽ bị Agent
    hiểu nhầm là "tra rồi, không có gì", còn lỗi thì nói đúng sự thật là
    chưa có nguồn nào được nối.
    """
    def search_knowledge(self, **arguments: Any) -> dict[str, Any]:
        """Luôn báo chưa cấu hình; không cho thử lại."""
        raise ProviderError(
            "UNAVAILABLE",
            "The knowledge provider is not configured for this environment.",
            retryable=False,
        )


@dataclass(frozen=True)
class _WorkspaceTarget:
    """One project's approved knowledge root. The provider never reads outside it."""

    root: Path
    project_id: str


class KnowledgeTargetResolver(Protocol):
    def resolve(self, identity: IdentityContext) -> _WorkspaceTarget: ...


class KnowledgeAccessResolver(Protocol):
    def resolve(self, identity: IdentityContext, target: _WorkspaceTarget) -> None: ...


def _is_safe_segment(value: str) -> bool:
    return (
        bool(value)
        and value not in {".", ".."}
        and not set(value) & set("/\\")
        and "\x00" not in value
    )


@dataclass(frozen=True)
class ProjectWorkspaceTargetResolver:
    """Resolve the workspace root from the *identity*, never from the request.

    project_id in the request is only ever verified against this result; it is
    never routing authority.
    """

    def resolve(self, identity: IdentityContext) -> _WorkspaceTarget:
        configured = os.environ.get("PROJECT_CONTEXT_KNOWLEDGE_ROOT", "").strip()
        if not configured:
            raise ProviderError(
                "UNAVAILABLE",
                "PROJECT_CONTEXT_KNOWLEDGE_ROOT is not configured for this environment.",
                retryable=False,
            )
        base = Path(configured).expanduser()
        # The identity's project name is a path *segment*, never a path, so a
        # traversal-shaped project can never escape the configured base.
        if not _is_safe_segment(identity.project):
            raise ProviderError(
                "UNAVAILABLE",
                "This identity is not mapped to an approved knowledge workspace.",
                retryable=False,
            )
        try:
            resolved = (base / identity.project).resolve()
            resolved_base = base.resolve()
        except OSError as exc:
            raise ProviderError(
                "UNAVAILABLE",
                "The approved knowledge workspace could not be opened.",
                retryable=False,
            ) from exc
        if resolved_base not in resolved.parents or not resolved.is_dir():
            raise ProviderError(
                "UNAVAILABLE",
                "This identity is not mapped to an approved knowledge workspace.",
                retryable=False,
            )
        return _WorkspaceTarget(root=resolved, project_id=identity.project)


@dataclass(frozen=True)
class LocalWorkspaceAccessResolver:
    """Pilot access check for a local workspace root.

    The local corpus needs no fetch credential, so this resolver only asserts
    the workspace is readable. It exists as its own seam so an on-behalf-of
    credential for a served knowledge base can replace it without touching the
    tool or the provider.
    """

    def resolve(self, identity: IdentityContext, target: _WorkspaceTarget) -> None:
        del identity
        if not os.access(target.root, os.R_OK):
            raise ProviderError(
                "UNAVAILABLE",
                "The approved knowledge workspace is not readable.",
                retryable=False,
            )


def build_provider(
    identity: IdentityContext,
    *,
    target_resolver: KnowledgeTargetResolver | None = None,
    access_resolver: KnowledgeAccessResolver | None = None,
) -> KnowledgeProvider:
    """Compose routing and access only after the policy has allowed the call."""
    target = (target_resolver or ProjectWorkspaceTargetResolver()).resolve(identity)
    (access_resolver or LocalWorkspaceAccessResolver()).resolve(identity, target)
    return WorkspaceKnowledgeProvider(target)


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold()


def _terms(text: str) -> list[str]:
    return _WORD_PATTERN.findall(_normalize(text))[:_MAX_QUERY_TERMS]


class WorkspaceKnowledgeProvider:
    """Ranked, bounded, read-only lexical search over ONE project's workspace."""

    def __init__(self, target: _WorkspaceTarget, *, extractor: Any = None) -> None:
        self._target = target
        self._extractor = extractor

    def search_knowledge(
        self,
        *,
        project_id: str,
        query: str,
        detail: str,
        top_k: int,
        language: str | None = None,
        cursor: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        del language  # accepted by the contract; the lexical scan is language-neutral
        if project_id != self._target.project_id:
            # Defense in depth: the runtime's policy already guarantees this
            # (DENIED fires first), but the provider never trusts
            # caller-supplied routing regardless.
            raise ProviderError(
                "INTERNAL",
                "Resolved provider does not match the requested project.",
                retryable=False,
            )
        terms = _terms(query)
        if not terms:
            # Whitespace/punctuation-only queries pass the contract's length
            # bound but carry no search intent -- reject before any file read.
            raise ProviderError(
                "INVALID_INPUT",
                "query must contain at least one searchable term.",
                retryable=False,
            )
        offset = decode_offset_cursor(cursor)

        scored = self._scan(terms)
        page_size = min(_PAGE_SIZE_BY_DETAIL.get(detail, 5), top_k)
        excerpt_chars = _EXCERPT_CHARS_BY_DETAIL.get(detail, 600)

        page = scored[offset : offset + page_size]
        remaining = max(0, len(scored) - (offset + page_size))
        truncated = remaining > 0
        retrieved_at = datetime.now(timezone.utc).isoformat()

        items = tuple(
            {
                "document_id": hit["document_id"],
                "chunk_id": hit["chunk_id"],
                "title": hit["title"][:200],
                "excerpt": hit["text"][:excerpt_chars],
                "score": hit["score"],
                "source": {
                    "system": "cowork-workspace",
                    "url": hit["url"],
                    "revision": hit["revision"],
                    "retrieved_at": retrieved_at,
                },
            }
            for hit in page
        )

        return {
            "project_id": project_id,
            "query": query,
            "items": items,
            "truncated": truncated,
            "returned": len(items),
            "remaining": remaining,
            "next_cursor": str(offset + page_size) if truncated else None,
        }

    # ---- internals ---------------------------------------------------
    def _scan(self, terms: list[str]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for path in self._knowledge_files():
            text = self._read(path)
            if not text:
                continue
            document_id = path.relative_to(self._target.root).as_posix()
            revision = self._revision(path)
            url = path.as_uri()
            for index, (heading, chunk) in enumerate(_chunk(text)):
                score = _score_chunk(chunk, heading, document_id, terms)
                if score <= 0:
                    continue
                candidates.append({
                    "document_id": document_id,
                    "chunk_id": f"{document_id}#{index}",
                    "title": heading or path.name,
                    "text": chunk.strip(),
                    "score": score,
                    "url": url,
                    "revision": revision,
                })
                if len(candidates) >= _MAX_CANDIDATES:
                    break
            if len(candidates) >= _MAX_CANDIDATES:
                break
        # Deterministic order: best score first, then a stable identity tiebreak
        # so pagination cursors stay meaningful across calls.
        candidates.sort(key=lambda hit: (-hit["score"], hit["chunk_id"]))
        return candidates

    def _knowledge_files(self) -> list[Path]:
        try:
            entries = sorted(
                p for p in self._target.root.rglob("*")
                if p.is_file() and p.suffix.lower() in _KNOWLEDGE_SUFFIXES
            )
        except OSError as exc:
            raise ProviderError(
                "UNAVAILABLE",
                "The approved knowledge workspace could not be listed.",
                retryable=False,
            ) from exc
        approved: list[Path] = []
        for path in entries:
            # A symlink can point outside the workspace: resolve and re-check
            # containment so project isolation survives a planted link.
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if self._target.root not in resolved.parents:
                continue
            try:
                if path.stat().st_size > _MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            approved.append(path)
            if len(approved) >= _MAX_FILES_SCANNED:
                break
        return approved

    def _read(self, path: Path) -> str:
        extractor = self._extractor or _default_extractor()
        try:
            text, _note = extractor(path)
        except Exception:  # noqa: BLE001 - one unreadable document must not fail the search
            return ""
        return (text or "")[:_MAX_CHARS_PER_DOCUMENT]

    def _revision(self, path: Path) -> str:
        try:
            stat = path.stat()
        except OSError:
            return "unknown"
        modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        return f"mtime:{modified};size:{stat.st_size}"


def _default_extractor():
    """Reuse Cowork's existing text extraction; fall back to plain-text reads.

    The fallback keeps the MCP server importable as a standalone process (the
    app package pulls in UI-oriented dependencies) without duplicating any of
    the format handling when the app package is present.
    """
    try:
        from ....core.doc_extract import extract_text
    except Exception:  # noqa: BLE001 - standalone server run outside the app package
        def _plain(path: Path) -> tuple[str | None, str]:
            try:
                return path.read_text(encoding="utf-8", errors="replace"), ""
            except OSError as exc:
                return None, f"could not read ({exc})"
        return _plain
    return lambda path: extract_text(path)


def _chunk(text: str) -> list[tuple[str, str]]:
    """Split a document into (heading, body) chunks.

    Markdown headings give a citable section; unheaded text falls back to
    fixed-size windows so every chunk stays bounded.
    """
    headings = list(_HEADING_PATTERN.finditer(text))
    if not headings:
        return [("", text[i : i + _CHUNK_CHARS]) for i in range(0, len(text), _CHUNK_CHARS)]
    chunks: list[tuple[str, str]] = []
    preamble = text[: headings[0].start()].strip()
    if preamble:
        chunks.append(("", preamble[:_CHUNK_CHARS]))
    for index, match in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        body = text[match.end() : end]
        heading = match.group(2).strip().rstrip("#").strip()
        for start in range(0, max(len(body), 1), _CHUNK_CHARS):
            chunks.append((heading, body[start : start + _CHUNK_CHARS]))
    return chunks


def _score_chunk(chunk: str, heading: str, document_id: str, terms: list[str]) -> float:
    """Term-coverage score in [0, 1], weighted toward heading/title matches.

    ponytail: lexical term overlap, not embeddings. It needs no index, no
    model, and no new dependency, and it is honest about what it is -- the
    score is coverage, never a fabricated similarity. Upgrade path: swap this
    one function for a Cowork-provided semantic ranker when the project corpus
    is large enough that recall (not plumbing) is the bottleneck.
    """
    body = _normalize(chunk)
    label = _normalize(f"{heading} {document_id}")
    matched = 0
    weighted = 0.0
    for term in terms:
        in_body = term in body
        in_label = term in label
        if not (in_body or in_label):
            continue
        matched += 1
        weighted += 1.0 if in_label else 0.6
    if not matched:
        return 0.0
    coverage = matched / len(terms)
    emphasis = weighted / len(terms)
    # Bounded to the contract's [0, 1] score range.
    return round(min(1.0, 0.7 * coverage + 0.3 * emphasis), 4)
