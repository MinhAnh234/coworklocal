"""EPIC R08 - Chat UI Hub integration tests.

Tests the lifecycle, UI component assembly, and event wiring of the refactored
presentation/chat/ sub-package (ChatPanel, ComposerWidget, AudioRecorderWidget,
ChatHistoryWidget, OutputPanelMixin).
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cowork_local.config import AppConfig
from cowork_local.presentation.chat import (
    AudioRecorderWidget,
    ChatHistoryWidget,
    ChatPanel,
    ChatView,
    Composer,
    ComposerWidget,
    MessageBubble,
)
from cowork_local.state import AppContext

pytest.importorskip("PySide6", reason="Qt required for chat UI integration tests")


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def ctx(qt_app, tmp_path):
    config_file = tmp_path / "config.json"
    config = AppConfig.load(config_file)
    return AppContext(config)


def test_chat_history_widget_adds_and_clears_bubbles(qt_app):
    """Verify ChatHistoryWidget / ChatView can append different bubble types and clear them."""
    view = ChatHistoryWidget()
    assert isinstance(view, ChatView)

    b_user = view.add_user("Hello agent")
    assert isinstance(b_user, MessageBubble)
    assert b_user.role == "user"

    b_assistant = view.add_assistant()
    assert isinstance(b_assistant, MessageBubble)
    assert b_assistant.role == "assistant"
    b_assistant.set_markdown("**Bold response**")

    b_status = view.add_status("Processing task...")
    assert isinstance(b_status, MessageBubble)

    b_error = view.add_error("Network timeout")
    assert isinstance(b_error, MessageBubble)

    # Clear transcript
    view.clear()
    assert view._lay.count() == 1  # only trailing stretch item remains


def test_composer_widget_queue_and_submission(qt_app):
    """Verify ComposerWidget / Composer handles text submission and parallel queueing."""
    composer = ComposerWidget()
    assert isinstance(composer, Composer)

    submitted_events = []
    composer.submitted.connect(lambda text, atts: submitted_events.append((text, atts)))

    # Direct submission via _on_submit
    composer.set_text("Run command ls")
    composer._on_submit()
    assert len(submitted_events) == 1
    assert submitted_events[0][0] == "Run command ls"
    assert submitted_events[0][1] == []

    # Submit when busy puts message in queue
    composer.set_busy(True)
    composer.enqueue("Queued task 1")
    composer.enqueue("Queued task 2", attachments=["/tmp/file.txt"])

    assert len(composer._queue) == 2
    assert composer.has_queue() is True

    # Free up slot via pop_next
    next_msg = composer.pop_next()
    assert next_msg is not None
    assert next_msg["text"] == "Queued task 1"
    assert len(composer._queue) == 1


def test_audio_recorder_widget_state_transitions(qt_app):
    """Verify AudioRecorderWidget transitions from idle -> recording -> stopped."""
    recorder = AudioRecorderWidget()
    assert recorder.is_recording() is False

    started_signal = MagicMock()
    stopped_signal = MagicMock()
    audio_ready_signal = MagicMock()

    recorder.recording_started.connect(started_signal)
    recorder.recording_stopped.connect(stopped_signal)
    recorder.audio_ready.connect(audio_ready_signal)

    # Start recording
    recorder.start_recording()
    assert recorder.is_recording() is True
    started_signal.assert_called_once()

    # Simulate timer tick
    recorder._on_tick()
    assert recorder.timer_label.text() == "00:01"

    # Stop recording
    recorder.stop_recording()
    assert recorder.is_recording() is False
    stopped_signal.assert_called_once_with(1)
    audio_ready_signal.assert_called_once_with(b"", "wav")


def test_chat_panel_initialization(ctx, qt_app):
    """Verify ChatPanel builds correctly with its mixed-in panels and sub-widgets."""
    panel = ChatPanel(ctx, kind="cowork", session_name="test_session")
    assert panel.ctx is ctx
    assert panel.kind == "cowork"
    assert panel.session_name == "test_session"
    assert hasattr(panel, "chat_view")
    assert hasattr(panel, "composer")
    assert hasattr(panel, "input_section")
    assert hasattr(panel, "output_section")
    assert isinstance(panel.composer, Composer)
