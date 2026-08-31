"""File tools - read_file, list_dir, write_file, edit_file (R05-T02).

Moved verbatim out of ``core/tools.py``, whose ``execute_tool`` used to
dispatch to these via a hand-written if/elif chain over every tool name it
knew about. Splitting the built-in handlers into per-concern modules
(this one, ``command_tools.py``, ``fetch_tools.py``) means adding a tool no
longer means growing that one function; ``core/tools.py::execute_tool`` now
looks the name up in a dict built from these modules instead.

Behavior is unchanged from before the split - this is a pure move, not a
rewrite. Every existing characterization/contract test that exercises
read_file/write_file/edit_file/list_dir through ``core.tools.execute_tool``
still exercises the exact same code, just imported from here.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict

from .tool_context import ToolContext

MAX_READ_BYTES = 200_000


def _flatten_rel(rel: str) -> str:
    """Collapse a sub-folder path down to a bare filename so the file lands in the
    workdir root — EXCEPT the ``.scratch`` sandbox subtree, which is preserved.

    Used by the Cowork agent (flatten_writes=True) so it can never create a
    per-session / per-chat / per-task output sub-folder: every deliverable stays
    directly in the single configured Output folder."""
    parts = Path(rel).parts
    if parts and parts[0] == ".scratch":
        return rel  # temporary sandbox is allowed (and cleaned up afterwards)
    return Path(rel).name or rel


def _check_python_syntax(target: Path, content: str) -> str:
    """Return a short warning if ``content`` is invalid Python, else ''.

    Catches syntax errors the instant a .py file is written/edited — before the
    agent wastes a whole run_command round-trip just to get the same error back
    from a traceback."""
    if target.suffix.lower() not in (".py", ".pyw"):
        return ""
    try:
        ast.parse(content, filename=str(target))
        return ""
    except SyntaxError as exc:
        return f"\n⚠ Syntax error at line {exc.lineno}: {exc.msg} — fix this before running the file."


def read_file(ctx: ToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    """Đọc một tệp trong thư mục làm việc, cắt ở ``MAX_READ_BYTES``.

    Đường dẫn được ``ctx.resolve`` kiểm trước — thoát ra ngoài thư mục là bị từ chối.
    """
    target = ctx.resolve(str(args.get("path", "")))
    if not target.exists():
        return {"ok": False, "output": f"File not found: {args.get('path')}"}
    data = target.read_bytes()[:MAX_READ_BYTES]
    text = data.decode("utf-8", errors="replace")
    return {"ok": True, "output": text}


def list_dir(ctx: ToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    """Liệt kê tệp và thư mục con tại một đường dẫn (mặc định là gốc thư mục làm việc)."""
    rel = str(args.get("path", ".") or ".")
    target = ctx.resolve(rel)
    # A missing/not-yet-created path is NOT a tool failure — report it as an
    # ordinary result so the agent can create it or pick another path and keep
    # going. Returning ok=False here surfaced a false "tool failed: list_dir" in
    # Co4E flows and could stall a step on a recoverable situation.
    if not target.exists():
        return {"ok": True, "output": f"(path '{rel}' does not exist yet — create it or use another path)"}
    if target.is_file():
        return {"ok": True, "output": f"('{rel}' is a file, not a directory)"}
    entries = []
    for child in sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
        marker = "/" if child.is_dir() else ""
        entries.append(f"{child.name}{marker}")
    return {"ok": True, "output": "\n".join(entries) or "(empty folder)"}


def write_file(ctx: ToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    """Tạo mới hoặc ghi đè một tệp, tự tạo thư mục cha.

    ``ctx.flatten_writes`` ép mọi tệp ghi thẳng vào gốc — dùng cho lượt chạy mà
    cấu trúc thư mục do agent bịa ra không có ý nghĩa gì.
    """
    rel = str(args.get("path", ""))
    if ctx.flatten_writes:
        rel = _flatten_rel(rel)
    target = ctx.resolve(rel)
    content = str(args.get("content", ""))
    target.parent.mkdir(parents=True, exist_ok=True)
    # A .xlsx is a binary package — build a REAL workbook from the content
    # (CSV/TSV/Markdown-table/JSON) rather than writing raw text (which corrupts it).
    if target.suffix.lower() in (".xlsx", ".xlsm"):
        from cowork_local.core import xlsx_write
        if xlsx_write.build_xlsx_from_text(target, content):
            return {"ok": True, "path": str(target),
                    "output": f"Wrote spreadsheet {rel} ({target.name})."}
        return {"ok": False, "output": "Could not build the .xlsx (openpyxl unavailable) — "
                "write a .csv instead, or use a generator script."}
    target.write_text(content, encoding="utf-8")
    warning = _check_python_syntax(target, content)
    return {"ok": True, "path": str(target),
            "output": f"Wrote {len(content)} chars to {rel}.{warning}"}


def edit_file(ctx: ToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    """Replace an exact snippet inside an existing file (precise patch edit)."""
    rel = str(args.get("path", ""))
    if ctx.flatten_writes:
        rel = _flatten_rel(rel)
    target = ctx.resolve(rel)
    if not target.exists():
        return {"ok": False,
                "output": f"File not found: {rel} — use write_file to create it."}
    old = str(args.get("old_string", ""))
    new = str(args.get("new_string", ""))
    replace_all = bool(args.get("replace_all", False))
    if not old:
        return {"ok": False, "output": "old_string is empty — provide the exact text to replace."}
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"ok": False, "output": f"Could not read file: {exc}"}
    count = text.count(old)
    if count == 0:
        return {"ok": False, "output": ("old_string not found. Read the file and copy the exact "
                                        "text to replace, including indentation/whitespace.")}
    if count > 1 and not replace_all:
        return {"ok": False, "output": (f"old_string appears {count} times — add surrounding "
                                        "context to make it unique, or set replace_all=true.")}
    updated = text.replace(old, new) if replace_all else text.replace(old, new, 1)
    target.write_text(updated, encoding="utf-8")
    n = count if replace_all else 1
    warning = _check_python_syntax(target, updated)
    return {"ok": True,
            "output": f"Edited {args.get('path')} ({n} replacement{'' if n == 1 else 's'}).{warning}"}


__all__ = ["MAX_READ_BYTES", "read_file", "list_dir", "write_file", "edit_file"]
