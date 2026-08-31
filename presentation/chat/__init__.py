"""Presentation chat package (EPIC R08 - Chat UI Hub).

Contains single-responsibility components and mixins for the unified chat interface:
- ChatPanel: container shell for streaming chat turns, worker thread management, and history.
- ChatHistoryWidget / ChatView / MessageBubble: scrollable message timeline and markdown renderers.
- Composer / ComposerWidget: input box, command dispatch, attachments list, and message queue.
- AttachmentMixin: attachment security check, character limit, and prompt augmentation.
- AudioRecorderWidget: audio/voice recording button and timer status.
- OutputPanelMixin: output files manager and directory watcher.
"""
from __future__ import annotations

from .attachment_picker import AttachmentMixin
from .audio_recorder_widget import AudioRecorderWidget
from .chat_history_widget import ChatHistoryWidget, ChatView, MessageBubble
from .chat_output_panel import OutputPanelMixin
from .chat_panel import ChatPanel
from .composer_widget import Composer, ComposerWidget

# ``ChatOutputPanelMixin`` từng nằm trong danh sách này nhưng module không hề
# export cái tên đó — tên thật là ``OutputPanelMixin`` (đã có ở dưới). Khai một
# tên không tồn tại làm ``from ... import *`` ném AttributeError, và ``__all__``
# thì không có bước kiểm nào bắt được. Đã gỡ.
__all__ = [
    "AttachmentMixin",
    "AudioRecorderWidget",
    "ChatHistoryWidget",
    "ChatPanel",
    "ChatView",
    "Composer",
    "ComposerWidget",
    "MessageBubble",
    "OutputPanelMixin",
]
