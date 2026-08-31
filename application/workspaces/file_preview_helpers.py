"""Pure helpers for previewing a file (R08-T12, moved out of
``ui/folder_tab.py`` — that file's module-level functions
``_read_text``/``_is_probably_text``/``_pptx_available``, lines 1519-1533 and
1565-1587 of the original 1587-line file). No Qt, no widget state — the
"is this file text? is pptx editing available?" questions the preview
manager asks before it decides how to render something.
"""
from __future__ import annotations

from pathlib import Path

_PPTX_READY = None   # cached: pptx-editing library available (after auto-install)


def pptx_available() -> bool:
    """True when python-pptx is importable. If it's MISSING, auto-download &
    install it (via deps.ensure_module) so pptx editing 'just works' — cached
    so the (one-time) install is attempted only once."""
    global _PPTX_READY
    if _PPTX_READY is None:
        try:
            from cowork_local.core.deps import ensure_module

            _PPTX_READY = ensure_module("pptx", "python-pptx") is not None
        except Exception:  # noqa: BLE001
            _PPTX_READY = False
    return _PPTX_READY


def read_text(path: str) -> str:
    """Đọc tệp dạng văn bản, thay ký tự hỏng thay vì ném lỗi; không đọc được thì
    trả về chuỗi rỗng.
    """
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"[could not read file: {exc}]"


def is_probably_text(path: str) -> bool:
    """Đoán tệp này có phải văn bản không, bằng cách tìm byte NUL trong phần đầu.

    Đoán sai theo hướng "là văn bản" sẽ hiện một màn hình ký tự rác, nên phép
    thử cố tình bảo thủ.
    """
    try:
        with open(path, "rb") as f:
            chunk = f.read(4096)
    except OSError:
        return False
    if b"\x00" in chunk:
        return False
    try:
        chunk.decode("utf-8")
        return True
    except UnicodeDecodeError:
        # Latin-ish text still edits fine via errors="replace"; only reject on
        # a hard binary signal (NUL above), so most source files pass.
        return True


__all__ = ["pptx_available", "read_text", "is_probably_text"]
