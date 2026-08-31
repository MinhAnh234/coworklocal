"""Vỏ chuyển tiếp — R08-T01.

Phần thân đã chuyển sang ``presentation/chat/chat_history_widget.py``.
Giữ đường import cũ cho ``ui/chat_panel.py`` và checker.
"""
from __future__ import annotations

from ..presentation.chat.chat_bubble_style import (  # noqa: F401
    ThinkingIndicator, _TimelineGutter, diff_to_html, format_status_line,
)
from ..presentation.chat.chat_history_widget import (  # noqa: F401
    ChatView, MessageBubble,
)
