"""Command tools - run_command, install_package (R05-T02).

Moved verbatim out of ``core/tools.py`` (see ``file_tools.py`` for why). These
two are the ones today's hand-written permission gate in
``core/chat_agent.py`` singles out by literal name
(``name in ("run_command", "install_package")``) — R05-T03 replaces that
tuple with a capability lookup, but the tools themselves are unchanged here.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from .tool_context import CancelFn, ToolContext

COMMAND_TIMEOUT = 120  # seconds

_SNAPSHOT_SKIP = {".git", "__pycache__", "node_modules", ".scratch", ".venv",
                  ".idea", ".mypy_cache", ".pytest_cache"}


def _snapshot(workdir: Path) -> Dict[str, Any]:
    """Map of file path -> (mtime, size) under the workdir (noise dirs skipped)."""
    snap: Dict[str, Any] = {}
    try:
        for dirpath, dirnames, filenames in os.walk(str(workdir)):
            dirnames[:] = [d for d in dirnames if d not in _SNAPSHOT_SKIP]
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                try:
                    st = os.stat(full)
                    snap[full] = (st.st_mtime_ns, st.st_size)
                except OSError:
                    pass
            if len(snap) > 5000:
                return snap
    except OSError:
        pass
    return snap


def _sandbox_python(ctx: ToolContext, cancel: Optional[CancelFn] = None,
                     on_output=None) -> Optional[str]:
    """Lazily create/reuse this ctx's project sandbox venv (Code tab only —
    ``ctx.sandbox``); returns its python path, or None to use the app's own."""
    if not ctx.sandbox:
        return None
    from cowork_local.core.deps import ensure_project_venv

    py = ensure_project_venv(ctx.workdir, cancel=cancel, on_output=on_output)
    return str(py) if py else None


def run_command(ctx: ToolContext, args: Dict[str, Any],
                 cancel: Optional[CancelFn] = None,
                 on_output=None) -> Dict[str, Any]:
    """Chạy một lệnh shell trong thư mục làm việc, có hạn giờ và có sandbox.

    Biến môi trường được lọc và mạng bị chặn theo cấu hình an toàn — agent chạy
    lệnh không được thừa hưởng toàn bộ môi trường của người dùng.
    """
    from cowork_local.core.deps import network_blocked_env, run_cancellable, sandbox_env
    from cowork_local.core.sandbox_manager import ExecutionConfig, SandboxManager
    from cowork_local.security.command_risk_classifier import classify_command

    command = str(args.get("command", "")).strip()
    if not command:
        return {"ok": False, "output": "Empty command."}

    # --- Security validation pipeline ---
    risk = classify_command(command, is_cowork_mode=ctx.flatten_writes)
    if risk.blocked:
        denial = "Command blocked by security policy: " + "; ".join(risk.reasons)
        return {"ok": False, "output": denial}

    # Route through SandboxManager for risk-based isolation
    mgr = SandboxManager(ExecutionConfig(
        enabled=True,
        block_network_by_default=ctx.block_network,
        is_cowork_mode=ctx.flatten_writes,
    ))
    sandbox_result = mgr.run(
        command=command,
        workdir=str(ctx.workdir),
        block_network=ctx.block_network,
        timeout_sec=COMMAND_TIMEOUT,
        cancel=cancel,
    )
    # Sandbox ALWAYS executes (never double-run). Return its result directly.
    if sandbox_result.get("sandbox") == "blocked":
        return {"ok": False, "output": sandbox_result.get("stderr", "Command blocked")}
    out = sandbox_result.get("stdout", "").strip() or "(no output)"
    err = sandbox_result.get("stderr", "")
    rc = sandbox_result.get("returncode", -1)
    if err:
        out = f"{out}\n{err}" if out else err
    return {"ok": sandbox_result.get("ok", False), "output": f"[exit {rc}]\n{out}"}


def install_package(ctx: ToolContext, args: Dict[str, Any],
                     cancel: Optional[CancelFn] = None,
                     on_output=None) -> Dict[str, Any]:
    """Cài một gói Python vào môi trường phụ trợ của lượt chạy.

    Cài vào venv riêng chứ không vào Python của hệ thống — một task không được
    phép làm hỏng môi trường của cả máy.
    """
    from cowork_local.core.deps import pip_install

    package = str(args.get("package", "")).strip()
    if not package:
        return {"ok": False, "output": "No package specified."}
    python = _sandbox_python(ctx, cancel, on_output)
    ok, detail = pip_install(package, cancel=cancel, on_output=on_output, python=python)
    head = f"Installed {package}." if ok else f"Could not install {package}."
    return {"ok": ok, "output": f"{head}\n{detail}"}


__all__ = ["COMMAND_TIMEOUT", "run_command", "install_package", "_snapshot"]
