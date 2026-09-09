"""AudioRecorderWidget - voice recording and input widget for chat (R08-T04).

Provides an interactive audio recording button with animated recording status,
time counter, and cancel/accept controls for sending audio notes or speech inputs
to the chat agent.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QElapsedTimer, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cowork_local.i18n import bind_dynamic, bind_tip, tr
from cowork_local.theme import current_palette
from cowork_local.ui.icons import icon


class AudioRecorderWidget(QWidget):
    """Voice recording panel that can be docked beside or within ComposerWidget.

    Signals:
        recording_started: Emitted when the user starts recording.
        recording_stopped: Emitted when the user finishes recording (passes elapsed seconds).
        audio_cancelled: Emitted when the user cancels the current recording.
        audio_ready: Emitted with recorded audio bytes or duration when completed.
    """

    recording_started = Signal()
    recording_stopped = Signal(int)  # elapsed seconds
    audio_cancelled = Signal()
    audio_ready = Signal(bytes, str)  # audio_data, format (e.g., 'wav')

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Dựng nút ghi âm kèm đồng hồ đếm giây, nhịp 1 giây."""
        super().__init__(parent)
        self._is_recording = False
        self._elapsed_seconds = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Construct the visual hierarchy: toggle button, time counter, and action buttons."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        # Record / Stop toggle button
        self.record_btn = QPushButton()
        self.record_btn.setIcon(icon("microphone"))
        bind_dynamic(self.record_btn, self._sync_record_tip)
        self.record_btn.setFixedSize(32, 32)
        self.record_btn.clicked.connect(self.toggle_recording)
        layout.addWidget(self.record_btn)

        # Status & timer display (hidden until recording starts)
        self.status_container = QWidget()
        status_layout = QHBoxLayout(self.status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(4)

        self.recording_dot = QLabel("●")
        self.recording_dot.setStyleSheet("color: #ef4444; font-size: 14px;")
        status_layout.addWidget(self.recording_dot)

        self.timer_label = QLabel("00:00")
        self.timer_label.setStyleSheet("font-family: monospace; font-weight: 600;")
        status_layout.addWidget(self.timer_label)

        self.cancel_btn = QPushButton()
        self.cancel_btn.setIcon(icon("x"))
        bind_tip(self.cancel_btn, "chat.record_audio_cancel")
        self.cancel_btn.setFixedSize(24, 24)
        self.cancel_btn.clicked.connect(self.cancel_recording)
        status_layout.addWidget(self.cancel_btn)

        self.status_container.setVisible(False)
        layout.addWidget(self.status_container)

    def is_recording(self) -> bool:
        """Check whether recording is currently in progress."""
        return self._is_recording

    def toggle_recording(self) -> None:
        """Toggle recording state between start and stop."""
        if self._is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self) -> None:
        """Begin audio capture and start the elapsed duration timer."""
        if self._is_recording:
            return
        self._is_recording = True
        self._elapsed_seconds = 0
        self.timer_label.setText("00:00")
        self.status_container.setVisible(True)
        self.record_btn.setIcon(icon("square"))
        self._sync_record_tip()
        self.record_btn.setStyleSheet("background-color: #fca5a5; color: #991b1b;")
        self._timer.start()
        self.recording_started.emit()

    def stop_recording(self) -> None:
        """Stop audio capture and finalize recorded data."""
        if not self._is_recording:
            return
        self._is_recording = False
        self._timer.stop()
        elapsed = self._elapsed_seconds
        self._reset_ui()
        self.recording_stopped.emit(elapsed)
        # Emit audio payload (placeholder stub for backend recording service)
        self.audio_ready.emit(b"", "wav")

    def cancel_recording(self) -> None:
        """Abort audio capture without emitting ready signal."""
        if not self._is_recording:
            return
        self._is_recording = False
        self._timer.stop()
        self._reset_ui()
        self.audio_cancelled.emit()

    def _reset_ui(self) -> None:
        """Restore UI components to default idle state."""
        self.status_container.setVisible(False)
        self.record_btn.setIcon(icon("microphone"))
        self.record_btn.setStyleSheet("")
        self._sync_record_tip()

    def _sync_record_tip(self) -> None:
        """Tooltip nút ghi âm nói việc nó sẽ làm tiếp, theo trạng thái hiện tại."""
        self.record_btn.setToolTip(tr("chat.record_audio_stop" if self._is_recording
                                      else "chat.record_audio_start"))

    def _on_tick(self) -> None:
        """Update recording duration display every second."""
        self._elapsed_seconds += 1
        mins = self._elapsed_seconds // 60
        secs = self._elapsed_seconds % 60
        self.timer_label.setText(f"{mins:02d}:{secs:02d}")


__all__ = ["AudioRecorderWidget"]
