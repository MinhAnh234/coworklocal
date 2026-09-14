"""ToolContext / ToolError / CancelFn - the sandboxed execution context every
built-in tool runs against (moved out of ``core/tools.py`` in R05-T02).

Kept as its own leaf module (no dependency on any sibling in this package) so
``file_tools.py``, ``command_tools.py`` and ``fetch_tools.py`` can each import
it without creating an import cycle back through ``core/tools.py``, which
itself re-exports ``ToolContext``/``ToolError`` from here for the existing
callers (``core/chat_agent.py``, ``core/code_agent.py``,
``core/task_executors.py``) that do ``from .tools import ToolContext``.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

CancelFn = Callable[[], bool]


class ToolError(Exception):
    """Lỗi khi chạy một tool — thông điệp được đưa thẳng cho model đọc."""
    pass


@dataclass
class ToolContext:
    """Bối cảnh một lượt chạy tool: thư mục làm việc và các quy tắc ghi.

    ``flatten_writes`` ép mọi tệp ghi thẳng vào gốc — dùng cho Cowork, nơi cấu
    trúc thư mục do model bịa ra không có ý nghĩa với người dùng.
    """
    workdir: Path
    flatten_writes: bool = False  # Cowork: force every write into the workdir root
    sandbox: bool = False  # Code tab: isolate run_command/install_package into <workdir>/.venv
    # Sandbox Security Layer — Settings' "Resource Limits" (cpu_percent/memory_mb/
    # disk_mb), applied to every run_command/install_package this context runs.
    # None (default) = no limits, matching pre-existing behavior.
    resource_limits: Optional[Dict[str, float]] = None
    # Sandbox Security Layer — Settings' "Block network for agent commands"
    # — the proxy-env block for shell commands (deps.py::network_blocked_env)
    # AND a flat refusal from every NETWORK-capability tool, which reaches the
    # net in-process where proxy env vars mean nothing. False (default) =
    # unrestricted, matching pre-existing behavior.
    block_network: bool = False
    # Whether the fetch_url tool may read URLs. Its own toggle, but NOT a way
    # around block_network: with the network blocked every NETWORK-capability
    # tool is refused first (fetch_tools.py::_network_refusal), so this flag only
    # decides anything while the network is open. Defaults True; set from
    # agent_security.allow_url_fetch.
    allow_url_fetch: bool = True
    # Jira read connector config (base_url/email/api_token) — None disables the
    # jira_* tools' ability to connect. Populated from config.data["jira"].
    jira: Optional[Dict[str, Any]] = None

    def resolve(self, rel: str) -> Path:
        """Resolve ``rel`` inside the workdir, rejecting escapes."""
        if rel in ("", "."):
            return self.workdir
        candidate = (self.workdir / rel).expanduser()
        try:
            resolved = candidate.resolve()
        except OSError as exc:
            raise ToolError(f"Invalid path: {rel} ({exc})")
        root = self.workdir.resolve()
        if resolved != root and root not in resolved.parents:
            raise ToolError(
                f"Refused: '{rel}' is outside the working folder ({root})."
            )
        return resolved


__all__ = ["CancelFn", "ToolError", "ToolContext"]
