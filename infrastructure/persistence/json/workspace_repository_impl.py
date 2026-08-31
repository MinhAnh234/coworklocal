"""WorkspaceRepository - an object-shaped, atomic-write-backed facade over
``core/projects.py`` (R06-T02).
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from cowork_local.core.projects import Project


class WorkspaceRepository:
    """CRUD over :class:`~cowork_local.core.projects.Project`, scoped to one
    ``directory`` (defaults to the app's real ``PROJECTS_DIR``; tests pass a
    ``tmp_path`` so nothing touches the user's real config folder)."""

    def __init__(self, directory: Optional[Path] = None) -> None:
        """``directory`` để None thì dùng thư mục dự án mặc định; import muộn để không
        kéo cấu hình vào lúc nạp module.
        """
        if directory is not None:
            self._directory = Path(directory)
        else:
            from cowork_local.core.projects import PROJECTS_DIR
            self._directory = PROJECTS_DIR

    def list(self) -> List["Project"]:
        """Liệt kê mọi project trong thư mục."""
        from cowork_local.core.projects import list_projects
        return list_projects(self._directory)

    def get(self, project_id: str) -> Optional["Project"]:
        """Đọc một project theo id; trả về ``None`` nếu không có."""
        from cowork_local.core.projects import load_project
        return load_project(project_id, self._directory)

    def save(self, project: "Project") -> None:
        """Ghi project xuống đĩa (ghi nguyên tử)."""
        from cowork_local.core.projects import save_project
        save_project(project, self._directory)

    def create(self, name: str, **kwargs) -> "Project":
        """Tạo project mới và ghi ngay xuống đĩa."""
        from cowork_local.core.projects import new_project
        return new_project(name, directory=self._directory, **kwargs)

    def new(self, name: str, **kwargs) -> "Project":
        """Bí danh của :meth:`create` — giữ cho mã cũ gọi ``new()`` vẫn chạy."""
        return self.create(name, **kwargs)

    def delete(self, project_id: str) -> bool:
        """Xoá project; trả về ``True`` nếu có project để xoá."""
        from cowork_local.core.projects import delete_project
        return delete_project(project_id, self._directory)


__all__ = ["WorkspaceRepository"]
