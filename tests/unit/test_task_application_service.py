"""EPIC R07-T04: TaskApplicationService — CRUD + dispatch rules, no Qt.

Everything here used to be exercised only by driving the real
``ui/schedule_task_tab.py`` widget (a QListWidget drag gesture, a QMenu
click). These tests drive the same rules directly through the service.
"""
from __future__ import annotations

from cowork_local.application.scheduling.task_application_service import (
    TaskApplicationService,
)
from cowork_local.infrastructure.persistence.json import TaskRepository


def _service(tmp_path, run_now=None):
    return TaskApplicationService(TaskRepository(tmp_path), run_now=run_now)


def _new_saved_task(repo: TaskRepository, **overrides):
    task = repo.create("T", **overrides)
    repo.save(task)
    return task


def test_run_now_rejects_manual_task_type(tmp_path):
    repo = TaskRepository(tmp_path)
    task = _new_saved_task(repo, task_type="manual")
    service = TaskApplicationService(repo, run_now=lambda tid: True)

    result = service.run_now(task["task_id"])

    assert result.ok is False
    assert result.reason == "manual_task"


def test_run_now_without_scheduler_wired_reports_no_scheduler(tmp_path):
    repo = TaskRepository(tmp_path)
    task = _new_saved_task(repo, task_type="cowork")
    service = TaskApplicationService(repo, run_now=None)

    result = service.run_now(task["task_id"])

    assert result.ok is False
    assert result.reason == "no_scheduler"


def test_run_now_delegates_to_injected_scheduler(tmp_path):
    repo = TaskRepository(tmp_path)
    task = _new_saved_task(repo, task_type="cowork")
    seen = []
    service = TaskApplicationService(repo, run_now=lambda tid: seen.append(tid) or True)

    result = service.run_now(task["task_id"])

    assert result.ok is True
    assert seen == [task["task_id"]]


def test_run_now_missing_task_reports_not_found(tmp_path):
    service = _service(tmp_path, run_now=lambda tid: True)
    result = service.run_now("does-not-exist")
    assert result.ok is False
    assert result.reason == "not_found"


def test_duplicate_saves_a_copy_with_fresh_identity(tmp_path):
    repo = TaskRepository(tmp_path)
    task = _new_saved_task(repo, description="d")
    service = TaskApplicationService(repo)

    dup = service.duplicate(task["task_id"])

    assert dup is not None
    assert dup["task_id"] != task["task_id"]
    assert dup["description"] == "d"
    assert repo.get(dup["task_id"]) is not None   # actually persisted, not just returned


def test_toggle_pause_then_resume_goes_to_backlog(tmp_path):
    repo = TaskRepository(tmp_path)
    task = _new_saved_task(repo)
    service = TaskApplicationService(repo)

    paused = service.toggle_pause(task["task_id"])
    assert paused["status"] == "paused"

    resumed = service.toggle_pause(task["task_id"])
    assert resumed["status"] == "backlog"


def test_delete_reports_whether_the_task_existed(tmp_path):
    repo = TaskRepository(tmp_path)
    task = _new_saved_task(repo)
    service = TaskApplicationService(repo)

    assert service.delete(task["task_id"]) is True
    assert repo.get(task["task_id"]) is None
    assert service.delete(task["task_id"]) is False   # already gone


def test_bulk_delete_counts_only_tasks_that_existed(tmp_path):
    repo = TaskRepository(tmp_path)
    a = _new_saved_task(repo)
    b = _new_saved_task(repo)
    service = TaskApplicationService(repo)

    count = service.bulk_delete([a["task_id"], b["task_id"], "ghost-id"])

    assert count == 2
    assert repo.list() == []


def test_move_to_status_running_task_is_blocked(tmp_path):
    repo = TaskRepository(tmp_path)
    task = _new_saved_task(repo)
    task["status"] = "running"
    repo.save(task)
    service = TaskApplicationService(repo)

    result = service.move_to_status(task["task_id"], "backlog")

    assert result.blocked is True
    assert repo.get(task["task_id"])["status"] == "running"   # untouched


def test_move_to_status_running_lane_dispatches_run_now(tmp_path):
    repo = TaskRepository(tmp_path)
    task = _new_saved_task(repo, task_type="cowork")
    seen = []
    service = TaskApplicationService(repo, run_now=lambda tid: seen.append(tid) or True)

    result = service.move_to_status(task["task_id"], "running")

    assert result.ran_now is True
    assert result.run_now_result.ok is True
    assert seen == [task["task_id"]]


def test_move_to_status_done_disables_the_schedule(tmp_path):
    repo = TaskRepository(tmp_path)
    task = _new_saved_task(repo)
    task["schedule"]["enabled"] = True
    task["schedule"]["run_at"] = "2026-08-28 09:00"
    repo.save(task)
    service = TaskApplicationService(repo)

    result = service.move_to_status(task["task_id"], "done")

    assert result.task["status"] == "done"
    assert result.task["schedule"]["enabled"] is False
    assert repo.get(task["task_id"])["schedule"]["enabled"] is False


def test_move_to_status_scheduled_without_run_at_needs_schedule(tmp_path):
    repo = TaskRepository(tmp_path)
    task = _new_saved_task(repo)   # fresh task has schedule.run_at = None
    service = TaskApplicationService(repo)

    result = service.move_to_status(task["task_id"], "scheduled")

    assert result.needs_schedule is True
    assert repo.get(task["task_id"])["status"] == "scheduled"
    assert repo.get(task["task_id"])["schedule"]["enabled"] is False


def test_move_to_status_scheduled_with_run_at_enables_it(tmp_path):
    repo = TaskRepository(tmp_path)
    task = _new_saved_task(repo)
    task["schedule"]["run_at"] = "2026-08-28 09:00"
    repo.save(task)
    service = TaskApplicationService(repo)

    result = service.move_to_status(task["task_id"], "scheduled")

    assert result.needs_schedule is False
    assert repo.get(task["task_id"])["schedule"]["enabled"] is True


def test_move_to_status_plain_change(tmp_path):
    repo = TaskRepository(tmp_path)
    task = _new_saved_task(repo)
    service = TaskApplicationService(repo)

    result = service.move_to_status(task["task_id"], "backlog")

    assert result.task["status"] == "backlog"


def test_move_to_status_missing_task_returns_none(tmp_path):
    service = _service(tmp_path)
    assert service.move_to_status("does-not-exist", "backlog") is None
