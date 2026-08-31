"""ConversationRepository - an object-shaped, atomic-write-backed facade over
``core/history.py`` (R06-T02).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from cowork_local.core.history import (
    delete_conversation,
    list_conversations,
    load_conversation,
    new_session_id,
    rename_conversation,
    save_conversation,
    set_pinned,
)


class ConversationRepository:
    """CRUD + search over conversation JSON files, scoped to one
    ``directory`` (defaults to the app's real ``HISTORY_DIR``)."""

    def __init__(self, directory: Optional[Path] = None) -> None:
        """``directory`` để None thì dùng thư mục lịch sử mặc định.

        Import muộn ngay trong thân hàm để nạp module này không kéo theo cả cây cấu
        hình — test trỏ thẳng vào ``tmp_path``.
        """
        if directory is not None:
            self._directory = Path(directory)
        else:
            from cowork_local.config import HISTORY_DIR
            self._directory = HISTORY_DIR

    def new_session_id(self) -> str:
        """Sinh id phiên mới cho một cuộc hội thoại."""
        return new_session_id()

    def save(self, kind: str, session_id: str, messages: List[Dict[str, Any]], **kwargs) -> Path:
        """Ghi hội thoại xuống đĩa (ghi nguyên tử) và trả về đường dẫn file."""
        return save_conversation(self._directory, kind, session_id, messages, **kwargs)

    def load(self, path: Path) -> Dict[str, Any]:
        """Đọc một hội thoại từ đường dẫn file."""
        return load_conversation(path)

    def list(self, query: str = "", **kwargs) -> List[Dict[str, Any]]:
        """Liệt kê hội thoại trong thư mục; ``query`` lọc theo tiêu đề và nội dung."""
        return list_conversations(self._directory, query=query)

    def _resolve_path(self, target: Any) -> Path:
        """Đổi id phiên (hoặc đường dẫn) thành đường dẫn file thật.

        Nhận cả ba dạng: Path sẵn, đường dẫn tuyệt đối, và id phiên trần —
        id trần thì dò theo mẫu ``*__<id>.json`` vì tiền tố là loại hội thoại
        (cowork/co4e/...) mà chỗ gọi không phải lúc nào cũng biết.
        """
        if isinstance(target, Path):
            return target
        p = Path(str(target))
        if p.exists() or p.is_absolute():
            return p
        for file in self._directory.glob(f"*__{target}.json"):
            return file
        return self._directory / f"cowork__{target}.json"

    def rename(self, target: Any, new_title: str) -> None:
        """Đổi tiêu đề một hội thoại."""
        rename_conversation(self._resolve_path(target), new_title)

    def delete(self, target: Any) -> None:
        """Xoá hẳn một hội thoại khỏi đĩa."""
        delete_conversation(self._resolve_path(target))

    def set_pinned(self, target: Any, pinned: bool) -> None:
        """Ghim/bỏ ghim một hội thoại để nó nằm trên đầu danh sách lịch sử."""
        set_pinned(self._resolve_path(target), pinned)


__all__ = ["ConversationRepository"]
