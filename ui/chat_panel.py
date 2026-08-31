"""Vỏ chuyển tiếp — R08-T06.

Phần thân đã chuyển sang ``presentation/chat/chat_panel.py``. Giữ đường import
cũ vì ``ui/cowork_tab.py`` và vài checker gọi qua đúng đường dẫn này.
"""
from __future__ import annotations

from ..presentation.chat.chat_helpers import (  # noqa: F401
    _TOOL_STATUS, _format_plan_steps, _is_scratch,
)
from ..presentation.chat.chat_panel import ChatPanel  # noqa: F401

__all__ = ["ChatPanel"]
