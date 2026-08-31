"""EPIC R06-T01: WorkspaceSession is a frozen snapshot, captured once, that a
turn keeps using regardless of what the UI does to the live project
selection afterwards - see the module docstring for the race this replaces.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cowork_local.domain.workspaces import WorkspaceSession


class _FakeProject:
    def __init__(self, project_id: str, root: Path):
        self.project_id = project_id
        self._root = root

    def workspace_dir(self) -> Path:
        return self._root


def test_from_project_derives_sandbox_dir_under_the_workspace_root(tmp_path):
    project = _FakeProject("proj-a", tmp_path)
    session = WorkspaceSession.from_project(project)

    assert session.project_id == "proj-a"
    assert session.workspace_root == tmp_path
    assert session.sandbox_dir == tmp_path / ".scratch"
    assert session.allowed_paths == (tmp_path,)


def test_is_allowed_true_for_the_root_and_descendants(tmp_path):
    session = WorkspaceSession.from_project(_FakeProject("p", tmp_path))
    nested = tmp_path / "sub" / "file.txt"
    nested.parent.mkdir(parents=True)
    nested.write_text("x", encoding="utf-8")

    assert session.is_allowed(tmp_path) is True
    assert session.is_allowed(nested) is True


def test_is_allowed_false_outside_the_workspace(tmp_path):
    session = WorkspaceSession.from_project(_FakeProject("p", tmp_path / "a"))
    outside = tmp_path / "b" / "secret.txt"

    assert session.is_allowed(outside) is False


def test_two_sessions_from_different_projects_stay_independent(tmp_path):
    """The exact race this snapshot exists to prevent: a turn holding session
    A must never start accepting paths that belong to session B, no matter
    what the (mutable, shared) AppContext does after the snapshot was taken."""
    session_a = WorkspaceSession.from_project(_FakeProject("a", tmp_path / "a"))
    session_b = WorkspaceSession.from_project(_FakeProject("b", tmp_path / "b"))

    assert session_a.is_allowed(tmp_path / "b" / "file.txt") is False
    assert session_b.is_allowed(tmp_path / "a" / "file.txt") is False


def test_unscoped_session_has_no_project_id(tmp_path):
    session = WorkspaceSession.unscoped(tmp_path)
    assert session.project_id == ""
    assert session.is_allowed(tmp_path / "code.py") is True
