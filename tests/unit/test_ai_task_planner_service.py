"""EPIC R07-T05: AiTaskPlannerService — AI-generate + import, no Qt, no network.

``core/ai_task_planner.py::plan_tasks`` and ``core/task_import.py::
import_tasks`` are exercised through a FakeProvider / real tmp files rather
than reimplemented — this service is a seam, not a new planner.
"""
from __future__ import annotations

import json

import pytest

from cowork_local.application.scheduling.ai_task_planner_service import (
    AiTaskPlannerService,
)
from tests.fakes import FakeProvider, ScriptedTurn

_PLAN_REPLY = json.dumps({
    "tasks": [
        {"title": "Draft report", "description": "d", "task_type": "cowork",
         "priority": "medium", "schedule": {"enabled": False}}
    ]
})


def test_plan_uses_the_constructor_injected_provider_factory():
    provider = FakeProvider([ScriptedTurn(text=_PLAN_REPLY)])
    service = AiTaskPlannerService(provider_factory=lambda: provider)

    tasks = service.plan("Write a weekly report")

    assert len(tasks) == 1
    assert tasks[0]["title"] == "Draft report"
    assert provider.call_count == 1


def test_plan_prefers_an_explicit_provider_over_the_factory():
    factory_provider = FakeProvider([ScriptedTurn(text=_PLAN_REPLY)], strict=False)
    explicit_provider = FakeProvider([ScriptedTurn(text=_PLAN_REPLY)])
    service = AiTaskPlannerService(provider_factory=lambda: factory_provider)

    service.plan("Write a weekly report", provider=explicit_provider)

    assert explicit_provider.call_count == 1
    assert factory_provider.call_count == 0


def test_plan_without_any_provider_raises_runtime_error():
    service = AiTaskPlannerService(provider_factory=None)
    with pytest.raises(RuntimeError):
        service.plan("Write a weekly report")


def test_plan_stamps_attachments_onto_every_generated_task():
    two_tasks_reply = json.dumps({"tasks": [
        {"title": "A", "task_type": "cowork"},
        {"title": "B", "task_type": "cowork"},
    ]})
    provider = FakeProvider([ScriptedTurn(text=two_tasks_reply)])
    service = AiTaskPlannerService(provider_factory=lambda: provider)

    tasks = service.plan("do two things", file_paths=["a.txt"], links=["https://x"])

    assert len(tasks) == 2
    for t in tasks:
        assert t["input"]["file_paths"] == ["a.txt"]
        assert t["input"]["links"] == ["https://x"]


def test_import_file_delegates_to_core_task_import(tmp_path):
    csv_path = tmp_path / "tasks.csv"
    csv_path.write_text("title,task_type,priority\nMy Task,cowork,medium\n", encoding="utf-8")
    service = AiTaskPlannerService()

    tasks = service.import_file(csv_path)

    assert len(tasks) == 1
    assert tasks[0]["title"] == "My Task"


def test_import_file_raises_value_error_on_unsupported_extension(tmp_path):
    bogus = tmp_path / "tasks.txt"
    bogus.write_text("nope", encoding="utf-8")
    service = AiTaskPlannerService()

    with pytest.raises(ValueError):
        service.import_file(bogus)
