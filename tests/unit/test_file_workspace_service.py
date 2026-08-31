"""EPIC R06-T05: FileWorkspaceService gives File Explorer / AI Editor the
same safe file operations the agent tool loop already has, via the SAME
``core/tools.py::execute_tool`` dispatch (not a reimplementation)."""
from __future__ import annotations

from cowork_local.application.workspaces import FileWorkspaceService
from cowork_local.domain.workspaces import WorkspaceSession


def _service(tmp_path) -> FileWorkspaceService:
    return FileWorkspaceService(WorkspaceSession.unscoped(tmp_path))


def test_write_then_read_round_trips(tmp_path):
    service = _service(tmp_path)
    written = service.write_file("notes.md", "# Hello")
    assert written["ok"] is True

    read = service.read_preview("notes.md")
    assert read == {"ok": True, "output": "# Hello"}


def test_list_tree_reflects_written_files(tmp_path):
    service = _service(tmp_path)
    service.write_file("a.txt", "x")
    listing = service.list_tree()
    assert listing["ok"] is True and "a.txt" in listing["output"]


def test_apply_edit_uses_the_context_anchored_replace(tmp_path):
    service = _service(tmp_path)
    service.write_file("code.py", "value = 1\n")
    edited = service.apply_edit("code.py", "value = 1", "value = 2")
    assert edited["ok"] is True
    assert service.read_preview("code.py")["output"].strip() == "value = 2"


def test_apply_edit_reports_ambiguous_match_like_the_agent_tool_does(tmp_path):
    service = _service(tmp_path)
    service.write_file("code.py", "x = 1\nx = 1\n")
    edited = service.apply_edit("code.py", "x = 1", "x = 2")
    assert edited["ok"] is False
    assert "appears" in edited["output"]


def test_path_escape_is_refused_not_a_crash(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (tmp_path / "outside.txt").write_text("secret", encoding="utf-8")
    service = FileWorkspaceService(WorkspaceSession.unscoped(workspace))

    result = service.read_preview("../outside.txt")
    assert result["ok"] is False
    assert "outside the working folder" in result["output"]


def test_write_preserves_subfolders_unlike_cowork_flatten_writes(tmp_path):
    """File Explorer must not collapse a write into the workspace root the
    way Cowork's agent context does (flatten_writes=True there, False here)."""
    service = _service(tmp_path)
    service.write_file("sub/dir/file.txt", "content")
    assert (tmp_path / "sub" / "dir" / "file.txt").read_text(encoding="utf-8") == "content"
