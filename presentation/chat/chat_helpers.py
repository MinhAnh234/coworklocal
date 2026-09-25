"""Hàm và bảng tra dùng chung trong khung chat — R08-T06.

Thuần hàm, không widget. Gom về đây vì cả năm file trong gói đều hỏi tới.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

_PLAN_ICONS = {"pending": "○", "running": "▶", "done": "✓", "error": "✗"}

HEADER_TITLE_MAX_CHARS = 10  # thanh tiêu đề khung chat chỉ hiện tối đa ngần này ký tự


def clip_chars(text: str, limit: int = HEADER_TITLE_MAX_CHARS) -> str:
    """Giữ tối đa ``limit`` ký tự, dư thì cắt và thêm "…"."""
    return text if len(text) <= limit else text[:limit].rstrip() + "…"



def _format_plan_steps(steps) -> str:
    """Render plan steps ``[{title, status}]`` as an icon checklist for the chat."""
    lines = []
    for s in steps or []:
        title = str((s or {}).get("title", "")).strip()
        if not title:
            continue
        icon = _PLAN_ICONS.get(str((s or {}).get("status", "pending")).lower(), "○")
        lines.append(f"{icon} {title}")
    return "\n".join(lines)


def _is_scratch(path: str) -> bool:
    """True for helper/intermediate files (kept out of the Output list)."""
    try:
        return ".scratch" in Path(path).parts
    except Exception:  # noqa: BLE001
        return False


_TOOL_STATUS = {
    "save_file": "chat.creating",
    "write_file": "chat.creating",
    "run_command": "chat.creating",
    "edit_file": "chat.editing",
    "install_package": "chat.installing",
    "read_file": "chat.reading",
}
