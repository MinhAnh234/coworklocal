"""EPIC R07-T01: TaskRepository + core/tasks.py::save_task atomic write.

The motivating bug: ``core/tasks.py::save_task`` used to
``path.write_text(json.dumps(...))`` — two syscalls, no atomicity, same class
of bug already fixed for projects/conversations at R06-T02. A failure between
the write and the replace must never leave a half-written task JSON file on
disk; that is the one property the crash-injection test exists to pin.
"""
from __future__ import annotations

import json

import pytest

from cowork_local.core.tasks import new_task
from cowork_local.infrastructure.persistence.json import TaskRepository


def test_task_repository_crud_round_trip(tmp_path):
    repo = TaskRepository(tmp_path)
    task = repo.create("My Task")
    repo.save(task)

    assert [t["task_id"] for t in repo.list()] == [task["task_id"]]
    assert repo.get(task["task_id"])["title"] == "My Task"

    task["title"] = "Renamed"
    repo.save(task)
    assert repo.get(task["task_id"])["title"] == "Renamed"

    repo.delete(task["task_id"])
    assert repo.get(task["task_id"]) is None
    assert repo.list() == []


def test_task_repository_duplicate_keeps_config_resets_identity(tmp_path):
    repo = TaskRepository(tmp_path)
    task = repo.create("Original", description="d")
    repo.save(task)

    dup = repo.duplicate(task)
    repo.save(dup)

    assert dup["task_id"] != task["task_id"]
    assert dup["description"] == "d"
    assert {t["task_id"] for t in repo.list()} == {task["task_id"], dup["task_id"]}


def test_save_task_never_corrupts_existing_file_on_crash(tmp_path, monkeypatch):
    """Same guarantee as ``test_atomic_write_and_repositories.py``'s crash
    test, exercised through ``core/tasks.py::save_task`` directly (not just
    through the repository) since that is the function every existing
    scheduler/executor call site still uses."""
    from cowork_local.core.tasks import save_task, task_path

    task = new_task("Stable")
    save_task(task, tmp_path)

    import cowork_local.infrastructure.persistence.json.atomic_write as mod

    def boom(*_a, **_k):
        raise OSError("simulated crash between write and replace")

    monkeypatch.setattr(mod.os, "replace", boom)
    task["title"] = "Corrupted?"
    with pytest.raises(OSError):
        save_task(task, tmp_path)

    on_disk = json.loads(task_path(task["task_id"], tmp_path).read_text(encoding="utf-8"))
    assert on_disk["title"] == "Stable"
