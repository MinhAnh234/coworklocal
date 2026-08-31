"""WorkspaceSession - an immutable snapshot of which project a turn belongs
to and where it may touch the filesystem (R06-T01).

``state.py::AppContext.active_project_id`` is a single mutable field read by
every background worker thread. ``ui/workspace_tab.py::_load_current`` writes
it (and the related ``config._project_history_dir``) on the UI thread the
moment the user switches projects - while a turn already running on a
worker thread may read either field mid-switch and end up acting on the
OTHER project's workspace/history for the rest of its run (the race
R06-T04 fixes).

The fix, same shape as R04's ``ConversationExecutionRequest``: capture the
workspace facts a turn needs ONCE, on the thread that knows which project is
selected, into one frozen object. Whatever the user does to the UI afterwards,
the turn keeps using the workspace it was handed at submit time.

Pure domain code: stdlib only, no Qt, no network. It does touch ``Path`` (not
plain strings, unlike ``ConversationExecutionRequest``) because its whole job
is path-containment checking - a snapshot with no room to answer "is this
path mine" would not replace what ``ToolContext.resolve`` currently does
inline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple


@dataclass(frozen=True)
class WorkspaceSession:
    """Everything a turn needs to know about ITS workspace, fixed at the
    moment it was submitted.

    Attributes:
        project_id: the project this turn belongs to (``""`` when no project
            is selected - e.g. the Code tab, which has no project concept).
        workspace_root: the project's sandbox root (``Project.workspace_dir()``).
        sandbox_dir: the ``.scratch`` subtree inside ``workspace_root`` used for
            generator/helper scripts, never a final deliverable (see
            ``infrastructure/filesystem/file_tools.py::_flatten_rel``).
        allowed_paths: every root a tool call may read/write under. Almost
            always just ``(workspace_root,)``; a project with a custom
            ``output_dir`` outside the managed workspace tree still resolves
            to exactly one root - the tuple exists so a future caller (e.g. a
            step scoped to a shared input folder) can widen it without a
            shape change.
    """

    project_id: str
    workspace_root: Path
    sandbox_dir: Path
    allowed_paths: Tuple[Path, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Không khai đường dẫn cho phép thì mặc định đúng một đường: thư mục gốc của
        phiên. Để rỗng nghĩa là KHÔNG cho phép gì cả, không phải cho phép tất.
        """
        if not self.allowed_paths:
            object.__setattr__(self, "allowed_paths", (self.workspace_root,))

    @classmethod
    def from_project(cls, project) -> "WorkspaceSession":
        """Build a session from a ``core.projects.Project``. ``project`` is
        typed loosely (not imported) so this module has no dependency on
        ``core/`` - the caller (``core/projects.py`` itself, or
        ``application/conversations``) already has the Project in hand."""
        root = Path(project.workspace_dir())
        return cls(project_id=project.project_id, workspace_root=root,
                   sandbox_dir=root / ".scratch", allowed_paths=(root,))

    @classmethod
    def unscoped(cls, workspace_root: Path) -> "WorkspaceSession":
        """A session for callers with no project concept (e.g. the Code tab,
        which sandboxes to a plain folder rather than a ``Project``)."""
        root = Path(workspace_root)
        return cls(project_id="", workspace_root=root, sandbox_dir=root / ".scratch")

    def is_allowed(self, path: Path) -> bool:
        """True when ``path`` resolves inside one of :attr:`allowed_paths`.

        Same containment rule as ``ToolContext.resolve`` (an exact root match
        or a real descendant), but side-effect-free: it reports the answer
        instead of raising, so a caller (``FileWorkspaceService``, R06-T05)
        can decide what "not allowed" means for its own UI instead of
        catching a ``ToolError``.
        """
        try:
            resolved = Path(path).expanduser().resolve()
        except OSError:
            return False
        for allowed in self.allowed_paths:
            root = Path(allowed).resolve()
            if resolved == root or root in resolved.parents:
                return True
        return False


__all__ = ["WorkspaceSession"]
