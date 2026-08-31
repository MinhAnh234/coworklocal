"""TaskRepository - an object-shaped, atomic-write-backed facade over
``core/tasks.py`` (R07-T01).

``core/tasks.py``'s module-level functions (``list_tasks``, ``load_task``,
``save_task``, ``delete_task``, ``new_task``, ``duplicate_task``) are still
what every existing call site (``core/task_scheduler.py``,
``core/task_executors.py``, ``ui/schedule_task_tab.py``) uses, and stay that
way - ``save_task`` now writes through :func:`atomic_write.write_json`
itself (R07-T01, same class of durability fix already applied to
``core/projects.py``/``core/history.py`` at R06-T02), so the fix applies
whether or not a caller ever touches this class.

This repository exists for the application layer
(``application/scheduling``, R07-T04) to depend on an interface instead of
reaching into ``core/`` directly. It is a thin pass-through today, not a
re-implementation: same on-disk format, same directory, same functions
underneath.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional


class TaskRepository:
    """CRUD over task dicts (see ``core/tasks.py::DEFAULT_TASK`` for shape),
    scoped to one ``directory`` (defaults to the app's real ``TASKS_DIR``;
    tests pass a ``tmp_path`` so nothing touches the user's real config
    folder)."""

    def __init__(self, directory: Optional[Path] = None) -> None:
        """``directory`` để None thì dùng thư mục task mặc định.

        Hai đường import cho cùng một hằng số: gói có thể được nạp dưới tên đầy đủ
        ``cowork_local`` hoặc dưới dạng tương đối tuỳ cách chạy.
        """
        if directory is None:
            try:
                from cowork_local.core.tasks import TASKS_DIR
            except ImportError:
                from ...core.tasks import TASKS_DIR
            self._directory = TASKS_DIR
        else:
            self._directory = directory

    def list(self) -> List[Dict[str, Any]]:
        """Liệt kê mọi task trong thư mục."""
        try:
            from cowork_local.core.tasks import list_tasks
        except ImportError:
            from ...core.tasks import list_tasks
        return list_tasks(self._directory)

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Đọc một task theo id; trả về ``None`` nếu không có."""
        try:
            from cowork_local.core.tasks import load_task
        except ImportError:
            from ...core.tasks import load_task
        return load_task(task_id, self._directory)

    def save(self, task: Dict[str, Any]) -> Path:
        """Ghi task xuống đĩa (ghi nguyên tử) và trả về đường dẫn file."""
        try:
            from cowork_local.core.tasks import save_task
        except ImportError:
            from ...core.tasks import save_task
        return save_task(task, self._directory)

    def create(self, title: str = "", **overrides: Any) -> Dict[str, Any]:
        """Tạo một task mới trong bộ nhớ theo mẫu mặc định; chưa ghi đĩa."""
        try:
            from cowork_local.core.tasks import new_task
        except ImportError:
            from ...core.tasks import new_task
        return new_task(title, **overrides)

    def duplicate(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Nhân bản một task (id mới, trạng thái và lịch sử chạy được đặt lại)."""
        try:
            from cowork_local.core.tasks import duplicate_task
        except ImportError:
            from ...core.tasks import duplicate_task
        return duplicate_task(task)

    def delete(self, task_id: str) -> None:
        """Xoá hẳn một task khỏi đĩa."""
        try:
            from cowork_local.core.tasks import delete_task
        except ImportError:
            from ...core.tasks import delete_task
        delete_task(task_id, self._directory)


__all__ = ["TaskRepository"]
