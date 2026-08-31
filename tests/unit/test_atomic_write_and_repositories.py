"""EPIC R06-T02: atomic JSON writes + the WorkspaceRepository/
ConversationRepository facades over core/projects.py and core/history.py.

The motivating bug: ``core/projects.py::save_project`` used to
``path.write_text(json.dumps(...))`` — two syscalls, no atomicity. A failure
between them must never leave a half-written file on disk; that is the one
property these tests exist to pin.
"""
from __future__ import annotations

import json

import pytest

from cowork_local.infrastructure.persistence.json import (
    ConversationRepository,
    WorkspaceRepository,
    write_json,
)
from cowork_local.infrastructure.persistence.json.atomic_write import write_json as _write_json


def test_write_json_round_trips(tmp_path):
    path = tmp_path / "a.json"
    write_json(path, {"hello": "world", "n": 3})
    assert json.loads(path.read_text(encoding="utf-8")) == {"hello": "world", "n": 3}


def test_write_json_leaves_no_temp_file_behind(tmp_path):
    write_json(tmp_path / "a.json", {"x": 1})
    assert list(tmp_path.iterdir()) == [tmp_path / "a.json"]


def test_a_failed_write_never_corrupts_the_existing_file(tmp_path, monkeypatch):
    """The whole point of write-temp-then-replace: if the replace step blows
    up, the ORIGINAL file must still be there and still be readable — not
    truncated, not half-written."""
    path = tmp_path / "a.json"
    write_json(path, {"version": 1})

    import cowork_local.infrastructure.persistence.json.atomic_write as mod

    def boom(*_a, **_k):
        raise OSError("simulated crash between write and replace")

    monkeypatch.setattr(mod.os, "replace", boom)
    with pytest.raises(OSError):
        write_json(path, {"version": 2})

    assert json.loads(path.read_text(encoding="utf-8")) == {"version": 1}
    # the abandoned temp file was cleaned up, not left orphaned
    assert list(tmp_path.iterdir()) == [path]


def test_workspace_repository_crud_round_trip(tmp_path):
    repo = WorkspaceRepository(tmp_path)
    project = repo.create("My Project", description="d")

    assert [p.project_id for p in repo.list()] == [project.project_id]

    project.description = "updated"
    repo.save(project)
    assert repo.get(project.project_id).description == "updated"

    assert repo.delete(project.project_id) is True
    assert repo.get(project.project_id) is None


def test_conversation_repository_crud_round_trip(tmp_path):
    repo = ConversationRepository(tmp_path)
    session_id = repo.new_session_id()
    path = repo.save("cowork", session_id, [{"role": "user", "content": "hi"}])

    assert [c["session_id"] for c in repo.list()] == [session_id]

    repo.rename(path, "Renamed")
    repo.set_pinned(path, True)
    data = repo.load(path)
    assert data["title"] == "Renamed"
    assert data["pinned"] is True

    repo.delete(path)
    assert repo.list() == []
