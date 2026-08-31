"""Parse an AI file-edit reply into its parts (R08-T12, moved out of
``ui/folder_tab.py`` — that file's module-level ``_split_code_block``/
``_parse_ai_output``, lines 1536-1562 of the original 1587-line file). Pure
string parsing, no Qt — used by ``presentation/folder/ai_file_editor_dialog.py``
to turn a model's raw reply into a proposed edit.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple


def split_code_block(text: str) -> Tuple[Optional[str], str]:
    """Split an AI reply into ``(file_content, summary)``. ``file_content``
    is the first fenced code block (the edited file); ``summary`` is any
    prose before it. Returns ``(None, text)`` when there's no code block."""
    m = re.search(r"```[^\n]*\n(.*?)```", text or "", re.DOTALL)
    if not m:
        return None, (text or "")
    return m.group(1), (text[:m.start()].strip())


def parse_ai_output(text: str) -> Tuple[Optional[str], Optional[str], str, List[Tuple[str, str]]]:
    """Parse an AI edit reply into ``(target, content, summary, image_gens)``.
    ``FILE: <path>`` names a NEW file to create; ``IMAGE_GEN: <prompt> =>
    <path>`` lines request generated illustration images (relative paths)."""
    content, summary = split_code_block(text)
    target = None
    m = re.search(r"(?mi)^\s*FILE:\s*(.+?)\s*$", text or "")
    if m:
        target = m.group(1).strip().strip("`\"'")
    image_gens = []
    for gm in re.finditer(r"(?mi)^\s*IMAGE_GEN:\s*(.+?)\s*=>\s*(\S+)\s*$", text or ""):
        image_gens.append((gm.group(1).strip(), gm.group(2).strip().strip("`\"'")))
    # Strip the directive lines out of the shown summary.
    summary = re.sub(r"(?mi)^\s*(FILE|IMAGE_GEN):\s*.+?$", "", summary).strip()
    return target, content, summary, image_gens


__all__ = ["split_code_block", "parse_ai_output"]
