"""EPIC R06-T04: the race in ``ui/workspace_tab.py::_load_current``.

``_load_current`` sets ``ctx.config._project_history_dir`` on the SHARED
``AppConfig`` every time the user switches projects in the Workspace screen.
A background turn (one that isn't the conversation currently displayed) used
to resolve its save directory by calling ``ctx.config.history_dir()`` at
``_persist_session`` time - i.e. whenever the turn actually finished, not
when it started. If the user switched projects while it was still running,
the turn's conversation got written into the NEW project's history folder
instead of the one it actually belongs to.

The fix threads a ``home_history_dir`` captured at submit time (same "home_*"
snapshot convention ``ui/chat_panel.py`` already uses for session id/title/
messages) through to the save call. This test drives the real
``ChatPanel._persist_session`` - the actual save path - offscreen.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cowork_local.config import AppConfig             # noqa: E402
from cowork_local.core.history import list_conversations  # noqa: E402
from cowork_local.state import AppContext              # noqa: E402

pytest.importorskip("PySide6", reason="Qt is required for the integration suite")


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def chat_panel(qt_app, tmp_path: Path):
    from cowork_local.ui.chat_panel import ChatPanel

    ctx = AppContext(AppConfig.load(tmp_path / "config.json"))
    return ChatPanel(ctx, "cowork", "Test")


def test_background_turn_saves_into_the_project_it_started_in(chat_panel, tmp_path):
    project_a_dir = tmp_path / "project-a-history"
    project_b_dir = tmp_path / "project-b-history"
    chat_panel.ctx.config._project_history_dir = project_a_dir

    # What ChatPanel._start_turn captures into the per-turn ctx dict at
    # submit time (see the "home_history_dir" entry added there for R06-T04).
    turn_ctx = {
        "home_id": chat_panel.session_id,
        "home_messages": [{"role": "user", "content": "hi"}],
        "home_title": "Background turn",
        "home_history_dir": chat_panel.ctx.config.history_dir(),
        "record": {},
    }
    assert turn_ctx["home_history_dir"] == project_a_dir

    # The user switches projects in the Workspace screen WHILE this turn is
    # still running - exactly what ui/workspace_tab.py::_load_current does.
    chat_panel.ctx.config._project_history_dir = project_b_dir

    chat_panel._persist_session(turn_ctx)

    assert len(list_conversations(project_a_dir)) == 1
    assert list_conversations(project_b_dir) == []


def test_the_currently_viewed_conversation_still_follows_live_selection(chat_panel, tmp_path):
    """_save_snapshot's OTHER caller (the initial "register it in History right
    away" call, and _autosave) has no captured history_dir and must keep
    resolving it live - that path is for the conversation ACTUALLY on screen,
    which should follow whatever project the user has selected right now."""
    project_dir = tmp_path / "currently-viewed"
    chat_panel.ctx.config._project_history_dir = project_dir

    chat_panel._save_snapshot(chat_panel.session_id,
                              [{"role": "user", "content": "hi"}], "Live view")

    assert len(list_conversations(project_dir)) == 1
