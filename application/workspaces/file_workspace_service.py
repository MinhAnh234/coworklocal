"""FileWorkspaceService - the safe file operations File Explorer and the AI
File Editor need, outside the agent tool loop (R06-T05).

``ui/folder_tab.py`` (File Explorer) and the AI File Editor dialog need the
exact same guarantees the agent's tools already have — path containment
inside the workspace, precise context-anchored edits, syntax warnings on a
bad Python write — but today that logic only exists wired to a model's tool
call (``core/tools.py::execute_tool``). A UI action that isn't a tool call
(browsing the tree, applying an AI-suggested diff from a review dialog) has
no equivalent entry point of its own.

This service IS that entry point. It reuses ``core/tools.py::execute_tool``
verbatim - same dispatch table, same ``ToolContext`` containment check, same
audit-log entry, same Python-syntax warning on write/edit - rather than
re-implementing any of it, so a fix to one path fixes both. It only adds the
:class:`~domain.workspaces.workspace_session.WorkspaceSession` seam: which
workspace root a call is scoped to is decided by the session, not by
whichever folder a widget happens to have open.
"""
from __future__ import annotations

from typing import Any, Dict


class FileWorkspaceService:
    """File operations scoped to one :class:`WorkspaceSession`.

    Read-only by name (``list_tree``/``read_preview``) vs. writing
    (``write_file``/``apply_edit``) mirrors the same READ/WRITE split
    ``domain/tools/tool_registry.py`` uses for the agent's own tools - a
    caller that only wants to browse never accidentally has write access.
    """

    def __init__(self, session) -> None:  # WorkspaceSession - see module docstring
        """Nhận một ``WorkspaceSession`` — mọi đường dẫn về sau đều bị nó chặn trong
        phạm vi cho phép.
        """
        self._session = session

    def list_tree(self, rel: str = ".") -> Dict[str, Any]:
        """Entries at ``rel`` (default: the workspace root)."""
        return self._execute("list_dir", {"path": rel})

    def read_preview(self, rel: str) -> Dict[str, Any]:
        """A text file's content (truncated by
        ``infrastructure/filesystem/file_tools.py::MAX_READ_BYTES``, same as
        the agent's ``read_file`` tool)."""
        return self._execute("read_file", {"path": rel})

    def write_file(self, rel: str, content: str) -> Dict[str, Any]:
        """Create or fully overwrite ``rel``."""
        return self._execute("write_file", {"path": rel, "content": content})

    def apply_edit(self, rel: str, old_string: str, new_string: str,
                   replace_all: bool = False) -> Dict[str, Any]:
        """Replace an exact snippet in an existing file - the same
        context-anchored algorithm the agent's ``edit_file`` tool uses, so an
        AI-suggested diff applies with the same precision and the same
        "old_string not found / ambiguous" failure messages either path
        would give the caller."""
        return self._execute("edit_file", {
            "path": rel, "old_string": old_string, "new_string": new_string,
            "replace_all": replace_all,
        })

    # -- internals --------------------------------------------------------- #
    def _tool_context(self):
        """A ``ToolContext`` scoped to this session's workspace root.
        ``flatten_writes=False`` (unlike Cowork's agent context) - File
        Explorer must preserve whatever subfolder structure the user is
        actually browsing, not collapse every write into the root."""
        from cowork_local.infrastructure.filesystem.tool_context import ToolContext

        return ToolContext(self._session.workspace_root, flatten_writes=False)

    def _execute(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch through ``core/tools.py::execute_tool`` - see the module
        docstring for why this delegates instead of reimplementing."""
        from cowork_local.core.tools import execute_tool

        return execute_tool(self._tool_context(), name, args)


__all__ = ["FileWorkspaceService"]
