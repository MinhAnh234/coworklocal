"""EPIC R08-T11: ScheduleTaskTab shell + KanbanBoardWidget, real Qt offscreen.

Drives the real widgets end to end (build -> refresh -> drag-drop rule via
TaskApplicationService -> refresh) against a tmp_path task repository, the
way ``test_history_dir_race.py`` proves R06-T04 against real Qt rather than
a double. ``TaskApplicationService``'s own business rules are already unit
tested (R07-T04); this file exists to prove the WIDGET is actually wired to
that service, not to re-test the rules themselves.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cowork_local.config import AppConfig  # noqa: E402
from cowork_local.infrastructure.persistence.json.task_repository_impl import (  # noqa: E402
    TaskRepository,
)
from cowork_local.state import AppContext  # noqa: E402

pytest.importorskip("PySide6", reason="Qt is required for the integration suite")


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def ctx(qt_app, tmp_path: Path):
    return AppContext(AppConfig.load(tmp_path / "config.json"))


@pytest.fixture
def tasks_dir(tmp_path: Path) -> Path:
    d = tmp_path / "tasks"
    d.mkdir()
    return d


def test_schedule_task_tab_builds_and_refreshes_with_no_tasks(ctx, tasks_dir):
    from cowork_local.presentation.scheduling.schedule_task_tab import ScheduleTaskTab

    tab = ScheduleTaskTab(ctx, scheduler=None, tasks_dir=tasks_dir)
    tab.refresh()   # must not raise against an empty repo

    assert tab.kanban.columns.keys()   # 7 lanes were built


def test_kanban_renders_a_task_into_its_status_lane(ctx, tasks_dir):
    from cowork_local.presentation.scheduling.kanban_board_widget import KanbanBoardWidget

    repo = TaskRepository(tasks_dir)
    task = repo.create("My Task", task_type="cowork")
    task["status"] = "backlog"
    repo.save(task)

    board = KanbanBoardWidget(ctx, tasks_dir=tasks_dir)
    board.refresh()

    from PySide6.QtCore import Qt

    backlog_ids = [board.columns["backlog"].item(i).data(Qt.UserRole)
                   for i in range(board.columns["backlog"].count())]
    assert task["task_id"] in backlog_ids


def test_dropping_a_card_on_done_disables_its_schedule_through_the_real_widget(ctx, tasks_dir):
    """Same rule TaskApplicationService.move_to_status covers at the unit
    level (R07-T04) — this proves the Kanban widget's drop handler actually
    calls it, end to end, with a real TaskRepository on disk."""
    from cowork_local.presentation.scheduling.kanban_board_widget import KanbanBoardWidget

    repo = TaskRepository(tasks_dir)
    task = repo.create("Recurring", task_type="cowork")
    task["schedule"]["enabled"] = True
    task["schedule"]["run_at"] = "2026-08-28 09:00"
    task["schedule"]["repeat_type"] = "daily"
    task["status"] = "scheduled"
    repo.save(task)

    board = KanbanBoardWidget(ctx, tasks_dir=tasks_dir)
    board.refresh()

    board._on_task_dropped(task["task_id"], "done")

    on_disk = repo.get(task["task_id"])
    assert on_disk["status"] == "done"
    assert on_disk["schedule"]["enabled"] is False


def test_kanban_edit_requested_is_wired_to_the_shells_edit_task(ctx, tasks_dir, monkeypatch):
    """Proves ScheduleTaskTab actually connects
    ``kanban.edit_requested -> self._edit_task`` (not just that the Kanban
    widget emits the signal in isolation) by monkeypatching the dialog class
    ``_edit_task`` opens and checking it was constructed for the right task."""
    import cowork_local.ui.task_editor_dialog as task_editor_dialog_module
    from cowork_local.presentation.scheduling.schedule_task_tab import ScheduleTaskTab

    repo = TaskRepository(tasks_dir)
    task = repo.create("Editable")
    repo.save(task)

    seen_task_ids = []

    class _FakeDialog:
        def __init__(self, task, all_tasks, parent, ctx):
            seen_task_ids.append(task["task_id"] if task else None)
            self.edited_task = None

        def exec(self):
            return False   # Cancel — nothing further should happen

    monkeypatch.setattr(task_editor_dialog_module, "TaskEditorDialog", _FakeDialog)

    tab = ScheduleTaskTab(ctx, scheduler=None, tasks_dir=tasks_dir)
    tab.kanban.edit_requested.emit(task["task_id"])

    assert seen_task_ids == [task["task_id"]]
