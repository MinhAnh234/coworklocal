"""ExecutionWorkspace - the output folder vs. the scratch folder for one
turn, as two distinct properties instead of a name convention (R06-T03).

Today the ``.scratch`` subtree is a special case buried inside
``_flatten_rel`` (``infrastructure/filesystem/file_tools.py``): a generator
script writes there, the deliverable lands in the output root, and
``core/chat_agent.py`` cleans ``.scratch`` up after the turn — but nothing
NAMES "the scratch folder" as a thing; every call site re-derives
``workdir / ".scratch"`` (or checks ``Path(rel).parts[0] == ".scratch"``) by
hand. This class gives that convention one home.

It does not change WHERE files land - ``workspace_root/.scratch`` stays
exactly what it always was. It exists so a caller (an application service,
R06-T05's ``FileWorkspaceService``, or a future turn-cleanup step) can ask
for "the output dir" / "the scratch dir" instead of hand-building the path
and hoping the convention hasn't drifted.

SEAM · dựng 2026-08-21 · chưa nối dây (F-05)
------------------------------------------------------------
Được nối khi: một chỗ gọi thật hỏi ``output_dir``/``scratch_dir`` thay vì tự ghép ``workdir / ".scratch"``.
Để dormant thì sao: Quy ước ``.scratch`` vẫn nằm rải trong ``file_tools.py``
và ``core/chat_agent.py``. File này đặt tên cho nó nhưng chưa ai dùng, nên
quy ước vẫn trôi được.

Cổng ``scripts/check_orphan_modules.py`` đếm tuổi seam từ ngày trên
và nhắc khi quá ``SEAM_MAX_AGE_DAYS``. Đổi nội dung dòng đó thì cổng
đọc theo — đừng sửa ngày để làm im lời nhắc.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from cowork_local.domain.workspaces import WorkspaceSession

SCRATCH_DIRNAME = ".scratch"


@dataclass(frozen=True)
class ExecutionWorkspace:
    """The two folders a turn actually writes to, derived from a
    :class:`WorkspaceSession`.

    ``output_dir`` is always the session's ``workspace_root`` itself, not a
    per-turn subfolder - Cowork's whole design is that every deliverable lands
    directly in the one configured Output folder (see
    ``infrastructure/filesystem/file_tools.py::_flatten_rel``'s docstring).
    ``scratch_dir`` is the SAME flat ``workspace_root/.scratch`` every turn on
    that workspace already shares today (``core/chat_agent.py``'s
    ``_cleanup_cowork_intermediates`` operates on that exact path) - this
    class does not introduce per-turn namespacing that doesn't exist in the
    engine yet, only names the existing convention.

    ``turn_id`` is kept as metadata for callers that want to attribute a
    workspace to the turn that used it (logging, future per-turn scratch
    namespacing); it does not affect either path today.
    """

    session: WorkspaceSession
    turn_id: str

    @property
    def output_dir(self) -> Path:
        """Thư mục agent được phép ghi kết quả — chính là gốc của phiên làm việc."""
        return self.session.workspace_root

    @property
    def scratch_dir(self) -> Path:
        """Thư mục nháp bên trong phiên, cho file tạm không phải kết quả cuối."""
        return self.session.workspace_root / SCRATCH_DIRNAME

    def ensure_dirs(self) -> None:
        """Create both folders if they don't exist yet. Callers that only
        need one (most do) can skip this and let ``write_file`` create parents
        on demand, same as today."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scratch_dir.mkdir(parents=True, exist_ok=True)

    def cleanup_scratch(self) -> None:
        """Unconditionally remove the scratch subtree.

        Coarser than ``core/chat_agent.py::_cleanup_cowork_intermediates``,
        which rescues any real deliverable a generator script wrote INSIDE
        ``.scratch`` before wiping it - that rescue logic stays there. This
        is for callers that only need "make the scratch folder go away"
        (e.g. before starting a fresh run) and know it holds nothing worth
        saving.
        """
        shutil.rmtree(self.scratch_dir, ignore_errors=True)


__all__ = ["ExecutionWorkspace", "SCRATCH_DIRNAME"]
