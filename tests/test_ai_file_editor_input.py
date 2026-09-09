"""DF-008 — presentation/folder/ai_file_editor_dialog.py::_AutoExpandInput.

The AI-edit instruction box was a fixed-height single-line QLineEdit (read as
cramped); it is now a QPlainTextEdit that grows with content, submits on
Enter, and inserts a newline on Shift+Enter — same convention as the Cowork
composer's input (presentation/chat/chat_input_box.py::_Input)."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtCore import QEvent

from cowork_local.presentation.folder.ai_file_editor_dialog import _AutoExpandInput


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _press_enter(widget, shift: bool = False) -> None:
    mods = Qt.ShiftModifier if shift else Qt.NoModifier
    event = QKeyEvent(QEvent.KeyPress, Qt.Key_Return, mods)
    widget.keyPressEvent(event)


def test_starts_at_min_height(qapp) -> None:
    box = _AutoExpandInput()
    assert box.height() == _AutoExpandInput.MIN_HEIGHT


def test_grows_with_multiline_content(qapp) -> None:
    box = _AutoExpandInput()
    start_height = box.height()
    box.setPlainText("\n".join(f"line {i}" for i in range(10)))
    assert box.height() > start_height
    assert box.height() <= _AutoExpandInput.MAX_HEIGHT


def test_enter_emits_submit_and_does_not_insert_newline(qapp) -> None:
    box = _AutoExpandInput()
    box.setPlainText("hello")
    received = []
    box.submit.connect(lambda: received.append(True))
    _press_enter(box)
    assert received == [True]
    assert box.toPlainText() == "hello"   # Enter did not add a newline


def test_shift_enter_inserts_newline_without_submitting(qapp) -> None:
    box = _AutoExpandInput()
    box.setPlainText("hello")
    cursor = box.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    box.setTextCursor(cursor)
    received = []
    box.submit.connect(lambda: received.append(True))
    _press_enter(box, shift=True)
    assert received == []
    assert box.toPlainText() == "hello\n"
