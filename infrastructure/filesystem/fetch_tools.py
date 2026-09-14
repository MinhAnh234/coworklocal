"""Fetch tools - fetch_url, jira_search, jira_get_issue (R05-T02).

Moved verbatim out of ``core/tools.py`` (see ``file_tools.py`` for why). The
network access these three carry is exactly what the ``ToolCapability.NETWORK``
tag added in R05-T01/domain/tools/tool_registry.py describes.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .tool_context import ToolContext


def _network_refusal(ctx: ToolContext, tool: str) -> Optional[Dict[str, Any]]:
    """Lời từ chối khi Sandbox Security Layer đang chặn mạng; None nếu được đi.

    ``block_network`` trước đây chỉ được đọc ở ``command_tools.py`` (lệnh shell),
    nên ba tool mang ``ToolCapability.NETWORK`` ở file này vẫn ra internet bình
    thường trong khi Monitoring báo "Mạng: Bị chặn". Kiểm ở đây, TRƯỚC mọi lời
    gọi mạng, để công tắc chặn đúng thứ nó nói là chặn.
    """
    if not ctx.block_network:
        return None
    return {"ok": False, "output": (
        f"{tool}: network access is blocked by the Sandbox Security Layer "
        "(\"Block network for agent-run commands\" is on in Settings).")}


def fetch_url(ctx: ToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch a URL's text content (web page / online document / SharePoint-
    OneDrive share link) via link_fetch — the same parser task-link attachments
    use. Honors the Sandbox Security Layer's "Block network" policy."""
    url = str(args.get("url", "")).strip()
    if not url:
        return {"ok": False, "output": "fetch_url: 'url' is required."}
    if not url.lower().startswith(("http://", "https://")):
        return {"ok": False, "output": f"fetch_url: not an http(s) URL: {url}"}
    blocked = _network_refusal(ctx, "fetch_url")
    if blocked is not None:
        return blocked
    if not ctx.allow_url_fetch:
        return {"ok": False,
                "output": ("fetch_url: URL fetching is turned off in Settings → Security "
                           "(\"Allow the agent to fetch URLs\").")}
    # A pasted Jira issue link on the CONNECTED Jira host is read via the
    # authenticated API (so private issues resolve, not a login page). Public
    # links / any other URL fall through to the normal fetcher below.
    from cowork_local.core import jira_tool
    if jira_tool.is_jira_issue_url(ctx.jira, url):
        return {"ok": True, "output": jira_tool.get_issue_by_url(ctx.jira, url)}
    from cowork_local.core.link_fetch import fetch_link_preview

    return {"ok": True, "output": fetch_link_preview(url)}


def jira_search(ctx: ToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    """Tìm issue trên Jira bằng JQL."""
    blocked = _network_refusal(ctx, "jira_search")
    if blocked is not None:
        return blocked
    from cowork_local.core import jira_tool

    out = jira_tool.search(ctx.jira, str(args.get("jql", "")),
                           int(args.get("max_results", 25) or 25))
    return {"ok": not out.lower().startswith(("jira is not configured", "jira search failed")),
            "output": out}


def jira_get_issue(ctx: ToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    """Lấy chi tiết một issue Jira theo mã."""
    blocked = _network_refusal(ctx, "jira_get_issue")
    if blocked is not None:
        return blocked
    from cowork_local.core import jira_tool

    out = jira_tool.get_issue(ctx.jira, str(args.get("key", "")))
    return {"ok": not out.lower().startswith(("jira is not configured", "could not fetch")),
            "output": out}


__all__ = ["fetch_url", "jira_search", "jira_get_issue"]
