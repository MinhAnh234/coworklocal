"""EPIC R06-T03: ExecutionWorkspace names the output-dir/scratch-dir split
that already exists in ``core/chat_agent.py`` (``.scratch`` under the
workspace root) without changing where anything lands."""
from __future__ import annotations

from cowork_local.domain.workspaces import WorkspaceSession
from cowork_local.infrastructure.filesystem.execution_workspace import ExecutionWorkspace


def test_output_dir_is_the_workspace_root_itself(tmp_path):
    session = WorkspaceSession.unscoped(tmp_path)
    workspace = ExecutionWorkspace(session, turn_id="turn-1")

    assert workspace.output_dir == tmp_path


def test_scratch_dir_matches_the_existing_flat_convention(tmp_path):
    """core/chat_agent.py::_cleanup_cowork_intermediates operates on
    ``output_dir / ".scratch"`` with no per-turn subfolder — this must agree,
    or cleanup_scratch() would target a directory nothing ever wrote to."""
    session = WorkspaceSession.unscoped(tmp_path)
    workspace = ExecutionWorkspace(session, turn_id="turn-1")

    assert workspace.scratch_dir == tmp_path / ".scratch"


def test_ensure_dirs_creates_both_folders(tmp_path):
    session = WorkspaceSession.unscoped(tmp_path / "root")
    workspace = ExecutionWorkspace(session, turn_id="t")
    workspace.ensure_dirs()

    assert workspace.output_dir.is_dir()
    assert workspace.scratch_dir.is_dir()


def test_cleanup_scratch_removes_it_and_leaves_output_dir_alone(tmp_path):
    session = WorkspaceSession.unscoped(tmp_path)
    workspace = ExecutionWorkspace(session, turn_id="t")
    workspace.ensure_dirs()
    (workspace.scratch_dir / "helper.py").write_text("print(1)", encoding="utf-8")
    (workspace.output_dir / "deliverable.txt").write_text("done", encoding="utf-8")

    workspace.cleanup_scratch()

    assert not workspace.scratch_dir.exists()
    assert (workspace.output_dir / "deliverable.txt").exists()


def test_cleanup_scratch_is_a_no_op_when_never_created(tmp_path):
    workspace = ExecutionWorkspace(WorkspaceSession.unscoped(tmp_path), turn_id="t")
    workspace.cleanup_scratch()  # must not raise
