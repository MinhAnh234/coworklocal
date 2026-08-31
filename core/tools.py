"""Sandboxed file/command tools used by the Code agent.

Every path is resolved relative to the working directory and must stay inside
it (path-traversal is rejected). ``run_command`` executes inside the workdir
with a timeout and captured output.

R05-T02: the actual handlers (``read_file``/``list_dir``/``write_file``/
``edit_file``/``run_command``/``install_package``/``fetch_url``/
``jira_search``/``jira_get_issue``) now live in
``infrastructure/filesystem/{file_tools,command_tools,fetch_tools}.py``, split
out of what used to be one big if/elif chain here. This module is the
strangler-fig shim (ADR-001 section 4): it re-exports ``ToolContext``/
``ToolError`` (actually defined in
``infrastructure/filesystem/tool_context.py`` now) so every existing
``from .tools import ToolContext`` keeps working, and ``execute_tool``
dispatches through a small ``{name: handler}`` table built from the moved
modules instead of the chain itself.
"""
from __future__ import annotations

import difflib
from typing import Any, Callable, Dict, List, Optional

from ..infrastructure.filesystem import command_tools, fetch_tools, file_tools
from ..infrastructure.filesystem.command_tools import _snapshot  # noqa: F401 - re-export, core/chat_agent.py imports this name
from ..infrastructure.filesystem.tool_context import CancelFn, ToolContext, ToolError  # noqa: F401 - re-export
from ..providers.base import ToolSpec

# --------------------------------------------------------------------------
# Tool specs advertised to the model
# --------------------------------------------------------------------------
TOOL_SPECS: List[ToolSpec] = [
    ToolSpec(
        name="read_file",
        description="Read the contents of a text file in the working folder.",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Relative path"}},
            "required": ["path"],
        },
    ),
    ToolSpec(
        name="list_dir",
        description="List files and subfolders at a path (defaults to the workdir root).",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Relative path, default '.'"}},
        },
    ),
    ToolSpec(
        name="write_file",
        description=("Create a NEW file or fully rewrite one. Creates parent folders if needed. "
                     "For small changes to an existing file, prefer edit_file."),
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string", "description": "Full file content"},
            },
            "required": ["path", "content"],
        },
    ),
    ToolSpec(
        name="edit_file",
        description=("Make a precise in-place edit to an EXISTING file by replacing an exact "
                     "snippet — preferred over write_file for small changes. 'old_string' must "
                     "match the file byte-for-byte (include enough surrounding context to be "
                     "unique). Set 'replace_all' to replace every occurrence."),
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path to an existing file"},
                "old_string": {"type": "string", "description": "Exact text to find (with context)"},
                "new_string": {"type": "string", "description": "Replacement text"},
                "replace_all": {"type": "boolean", "description": "Replace all occurrences (default false)"},
            },
            "required": ["path", "old_string", "new_string"],
        },
    ),
    ToolSpec(
        name="run_command",
        description="Run a shell command in the working folder and return stdout/stderr.",
        parameters={
            "type": "object",
            "properties": {"command": {"type": "string", "description": "Command to run"}},
            "required": ["command"],
        },
    ),
    ToolSpec(
        name="install_package",
        description=("Install a Python package (pip) into the app's environment so the task can "
                     "use it. Use this to add any missing library yourself — never ask the user "
                     "to install libraries by hand."),
        parameters={
            "type": "object",
            "properties": {
                "package": {"type": "string",
                            "description": "pip package spec, e.g. 'requests' or 'pandas==2.2.0'"},
            },
            "required": ["package"],
        },
    ),
    ToolSpec(
        name="fetch_url",
        description=("Fetch a web page or an online document by URL and return its text content. "
                     "Use this whenever the user shares a link or the task needs information from "
                     "the web. Supports normal http(s) pages, direct document links (PDF/Office — "
                     "parsed to text), SharePoint/OneDrive share links, and Jira issue links — a "
                     "pasted Jira URL is read via the connected Jira account automatically (no need "
                     "to ask for the issue key)."),
        parameters={
            "type": "object",
            "properties": {"url": {"type": "string", "description": "The http(s) URL to fetch"}},
            "required": ["url"],
        },
    ),
    ToolSpec(
        name="jira_search",
        description=("Search Jira issues with a JQL query and return a summary list. Use this to "
                     "read/gather info from Jira (e.g. 'project = ABX AND status = \"In Progress\"'). "
                     "Read-only."),
        parameters={
            "type": "object",
            "properties": {
                "jql": {"type": "string", "description": "Jira Query Language expression"},
                "max_results": {"type": "integer", "description": "Max issues to return (default 25)"},
            },
            "required": ["jql"],
        },
    ),
    ToolSpec(
        name="jira_get_issue",
        description="Read one Jira issue's details (summary, status, assignee, description) by key, e.g. ABX-123.",
        parameters={
            "type": "object",
            "properties": {"key": {"type": "string", "description": "Issue key, e.g. ABX-123"}},
            "required": ["key"],
        },
    ),
]

# Actions gated by the permission gate in confirm mode (auto-approved in Auto-run).
WRITE_TOOLS = {"write_file", "edit_file", "run_command", "install_package"}

# name -> handler(ctx, args[, cancel, on_output]) — built once from the split
# infrastructure modules. Replaces the if/elif chain execute_tool used to be.
_HANDLERS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "read_file": file_tools.read_file,
    "list_dir": file_tools.list_dir,
    "write_file": file_tools.write_file,
    "edit_file": file_tools.edit_file,
    "run_command": command_tools.run_command,
    "install_package": command_tools.install_package,
    "fetch_url": fetch_tools.fetch_url,
    "jira_search": fetch_tools.jira_search,
    "jira_get_issue": fetch_tools.jira_get_issue,
}
# Handlers that accept the long-running (cancel, on_output) signature — every
# other handler takes just (ctx, args).
_CANCELLABLE = {"run_command", "install_package"}


def enabled_tool_specs(security_config=None) -> List[ToolSpec]:
    """The built-in TOOL_SPECS minus any the admin turned OFF in Monitoring →
    Tools (``config.tools_disabled``). Passing None (or a config without the
    field) returns them all — unchanged from before this governance layer."""
    disabled = set(getattr(security_config, "tools_disabled", None) or [])
    if not disabled:
        return list(TOOL_SPECS)
    return [t for t in TOOL_SPECS if t.name not in disabled]


def combine_tool_sources(*sources):
    """Merge several ``(tools, executor)`` pairs — e.g. codebase-memory tools
    plus ``AppContext.build_mcp_tools`` (which since the MCP upgrade already
    includes MS365 via the built-in server) — into the ONE ``extra_tools``/
    ``extra_executor`` pair ``run_cowork``/``run_code`` accept. A source
    with no tools or no executor is skipped."""
    all_tools: List[ToolSpec] = []
    routing: Dict[str, Callable] = {}
    for tools, executor in sources:
        if not tools or executor is None:
            continue
        for spec in tools:
            all_tools.append(spec)
            routing[spec.name] = executor
    if not all_tools:
        return [], None

    def combined_executor(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Định tuyến một lời gọi tool về đúng nguồn của nó (dựng sẵn, MCP hay connector)."""
        executor = routing.get(name)
        if executor is None:
            return {"ok": False, "output": f"Unknown tool: {name}"}
        return executor(name, args)

    return all_tools, combined_executor


# --------------------------------------------------------------------------
# Preview (for the permission dialog) and execution
# --------------------------------------------------------------------------
def describe_action(ctx: ToolContext, name: str, args: Dict[str, Any]) -> Dict[str, str]:
    """Return a human preview of a proposed tool call."""
    if name == "run_command":
        return {"kind": "command", "title": "Run command", "text": str(args.get("command", ""))}
    if name == "fetch_url":
        return {"kind": "info", "title": "Fetch URL", "text": str(args.get("url", ""))}
    if name == "jira_search":
        return {"kind": "info", "title": "Jira search", "text": str(args.get("jql", ""))}
    if name == "jira_get_issue":
        return {"kind": "info", "title": "Jira read issue", "text": str(args.get("key", ""))}
    if name == "install_package":
        return {"kind": "command", "title": "Install Python package",
                "text": f"pip install {args.get('package', '')}"}
    if name == "write_file":
        path = str(args.get("path", ""))
        new = str(args.get("content", ""))
        old = ""
        try:
            target = ctx.resolve(path)
            if target.exists():
                old = target.read_text(encoding="utf-8", errors="replace")
        except (ToolError, OSError):
            pass
        diff = "".join(difflib.unified_diff(
            old.splitlines(keepends=True), new.splitlines(keepends=True),
            fromfile=f"a/{path}", tofile=f"b/{path}",
        )) or f"(new file) {path}\n\n{new[:2000]}"
        verb = "Overwrite" if old else "Create file"
        return {"kind": "diff", "title": f"{verb}: {path}", "text": diff}
    if name == "edit_file":
        path = str(args.get("path", ""))
        old_s = str(args.get("old_string", ""))
        new_s = str(args.get("new_string", ""))
        replace_all = bool(args.get("replace_all", False))
        before = after = ""
        try:
            target = ctx.resolve(path)
            if target.exists():
                before = target.read_text(encoding="utf-8", errors="replace")
        except (ToolError, OSError):
            pass
        if old_s and old_s in before:
            after = before.replace(old_s, new_s) if replace_all else before.replace(old_s, new_s, 1)
        diff = "".join(difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile=f"a/{path}", tofile=f"b/{path}",
        ))
        if not diff:
            diff = f"Edit: {path}\n- {old_s[:1000]}\n+ {new_s[:1000]}"
        return {"kind": "diff", "title": f"Edit: {path}", "text": diff}
    return {"kind": "info", "title": name, "text": _short_json(args)}


def execute_tool(ctx: ToolContext, name: str, args: Dict[str, Any],
                  cancel: Optional[CancelFn] = None,
                  on_output: Optional[Callable[[str], None]] = None,
                  agent_role: str = "") -> Dict[str, Any]:
    """Run a tool and return ``{"ok": bool, "output": str}``.

    ``cancel`` is only used by the long-running tools (``run_command``,
    ``install_package``) so the Stop button can interrupt a running subprocess
    instead of waiting for it to finish or time out. ``on_output``, likewise
    only used by those two, streams live stdout/stderr lines as they arrive.

    ``agent_role`` tags the resulting audit-log entry (see ``audit_log.py`` /
    ``agent_roles.py``) — every call is recorded there regardless, this only
    labels WHICH agent role made it."""
    from . import audit_log

    handler = _HANDLERS.get(name)
    try:
        if handler is None:
            result = {"ok": False, "output": f"Tool not found: {name}"}
        elif name in _CANCELLABLE:
            result = handler(ctx, args, cancel, on_output)
        else:
            result = handler(ctx, args)
    except ToolError as exc:
        result = {"ok": False, "output": str(exc)}
    except Exception as exc:  # defensive: a tool must never crash the agent
        result = {"ok": False, "output": f"Error running {name}: {exc}"}
    audit_log.record("tool_call", name, bool(result.get("ok")),
                     str(result.get("output", ""))[:500], agent_role=agent_role)
    return result


def _short_json(obj: Any, limit: int = 500) -> str:
    """Chuỗi JSON đã cắt ngắn để đưa vào log hoặc bong bóng chat, tránh nhấn chìm
    màn hình bằng một kết quả dài.
    """
    import json
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    return text if len(text) <= limit else text[:limit] + " …"
