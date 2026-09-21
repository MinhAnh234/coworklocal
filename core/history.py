"""Conversation persistence with a per-conversation file model.

Each conversation is stored as one JSON file::

    {"kind": "cowork"|"code", "session_id": str, "title": str,
     "created": ISO8601, "messages": [...canonical...]}

File name: ``<kind>__<session_id>.json`` so the sidebar can group by kind and
sort by recency. History can live locally or in a OneDrive folder (resolved by
``AppConfig.history_dir``).
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ..performance import span

_LIST_CACHE: dict[tuple[str, str, int], List[Dict[str, Any]]] = {}


def _invalidate_history_cache(directory: Path) -> None:
    prefix = str(Path(directory).resolve())
    for key in list(_LIST_CACHE):
        if key[0] == prefix:
            _LIST_CACHE.pop(key, None)


def new_session_id() -> str:
    """Id phiên mới theo mốc thời gian, chính xác tới mili giây."""
    return datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]


#: Độ dài mong muốn của một tiêu đề hội thoại, tính bằng ký tự.
TITLE_MAX_CHARS = 60
#: Số ký tự được phép vượt ``TITLE_MAX_CHARS`` để viết nốt từ đang bị cắt dở.
#: Cỡ một từ tiếng Việt — đủ để cứu chữ cuối, không đủ để kéo dài tiêu đề.
_TITLE_SLACK = 12

_KHOANG_TRANG = re.compile(r"\s")


def shorten_title(text: str, limit: int = TITLE_MAX_CHARS) -> str:
    """Rút gọn tiêu đề mà KHÔNG cắt vào giữa một từ.

    Cắt cứng ở ký tự thứ ``limit`` đọc rất khó chịu khi mốc đó rơi vào giữa từ:
    "…tóm tắt từng tệp" thành "…tóm tắt từng tệ…" — trông như lỗi gõ chứ không
    như một câu bị rút gọn. Nên khi mốc cắt rơi vào giữa từ thì viết nốt từ đó.

    Ba lối ra, theo thứ tự ưu tiên:

    * Viết nốt từ đang dở, nếu chỉ phải vượt thêm tối đa ``_TITLE_SLACK`` ký tự.
      Viết nốt mà vừa hết chuỗi thì **không** thêm dấu ba chấm — không còn chữ
      nào bị bỏ thì dấu ba chấm là nói dối.
    * Từ dài bất thường (đường dẫn, URL) thì lùi về ranh giới từ ngay trước mốc,
      để một token dài không kéo tiêu đề dài ra tuỳ ý.
    * Cả tiêu đề chỉ là một từ dài thì đành cắt cứng — không còn ranh giới nào.
    """
    if len(text) <= limit:
        return text
    if text[limit].isspace():          # mốc cắt vốn đã nằm giữa hai từ
        return text[:limit].rstrip() + "…"
    sau = _KHOANG_TRANG.search(text, limit)
    het_tu = sau.start() if sau is not None else len(text)
    if het_tu - limit <= _TITLE_SLACK:
        return text if het_tu == len(text) else text[:het_tu] + "…"
    truoc = [m.start() for m in _KHOANG_TRANG.finditer(text, 0, limit)]
    if truoc:
        return text[:truoc[-1]] + "…"
    return text[:limit] + "…"


def derive_title(messages: List[Dict[str, Any]]) -> str:
    """Suy tiêu đề hội thoại từ tin nhắn đầu tiên của người dùng.

    Dùng khi người dùng chưa tự đặt tên — cắt gọn cho vừa một dòng danh sách.
    """
    for m in messages:
        if m.get("role") == "user" and m.get("content"):
            return shorten_title(" ".join(m["content"].split()))
    return "(empty)"


def save_conversation(
    directory: Path,
    kind: str,
    session_id: str,
    messages: List[Dict[str, Any]],
    title: str = "",
    created: str = "",
    inputs: List[str] | None = None,
    outputs: List[str] | None = None,
    project_id: str = "",
) -> Path:
    """Ghi một hội thoại xuống ``<kind>__<session_id>.json``.

    Ghi nguyên tử (R06-T02). Cờ ghim và project_id của lần lưu trước được GIỮ
    LẠI: hàm này bị gọi tự động sau mỗi lượt chat, ghi đè chúng sẽ âm thầm bỏ
    ghim và đẩy hội thoại ra khỏi project của nó.
    """
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{kind}__{session_id}.json"
    pinned = False  # preserve pin flag + project across autosaves
    prev_project = ""
    if path.exists():
        try:
            prev = json.loads(path.read_text(encoding="utf-8"))
            pinned = bool(prev.get("pinned", False))
            prev_project = prev.get("project_id", "")
        except (OSError, json.JSONDecodeError):
            pinned = False
    payload = {
        "kind": kind,
        "session_id": session_id,
        "title": title or derive_title(messages),
        "created": created or datetime.now().isoformat(timespec="seconds"),
        "pinned": pinned,
        # A conversation belongs to a project (Claude-Projects style); legacy
        # files without one fall back to the default project.
        "project_id": project_id or prev_project or "default",
        "inputs": list(inputs or []),
        "outputs": list(outputs or []),
        "messages": messages,
    }
    # R06-T02: atomic write - see infrastructure/persistence/json/atomic_write.py.
    from ..infrastructure.persistence.json.atomic_write import write_json
    write_json(path, payload)
    _invalidate_history_cache(directory)
    return path


def delete_conversation(path) -> None:
    """Xoá file hội thoại; không có thì bỏ qua."""
    try:
        Path(path).unlink()
        _invalidate_history_cache(Path(path).parent)
    except OSError:
        pass


def rename_conversation(path, new_title: str) -> None:
    """Đổi tiêu đề một hội thoại và ghi lại (nguyên tử)."""
    from ..infrastructure.persistence.json.atomic_write import write_json

    data = load_conversation(path)
    data["title"] = new_title
    write_json(Path(path), data)
    _invalidate_history_cache(Path(path).parent)


def set_pinned(path, pinned: bool) -> None:
    """Ghim/bỏ ghim một hội thoại để nó nằm trên đầu danh sách."""
    from ..infrastructure.persistence.json.atomic_write import write_json

    data = load_conversation(path)
    data["pinned"] = bool(pinned)
    write_json(Path(path), data)
    _invalidate_history_cache(Path(path).parent)


def load_conversation(path: Path) -> Dict[str, Any]:
    """Đọc một hội thoại; file hỏng hoặc không đọc được thì trả về dict rỗng thay
    vì ném lỗi — một file hỏng không được phép làm chết cả danh sách lịch sử.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"kind": "", "title": "(read error)", "messages": []}
    if isinstance(data, list):  # tolerate legacy format
        data = {"kind": "", "title": derive_title(data), "messages": data}
    return data


def _matches_query(query: str, title: str, messages: List[Dict[str, Any]]) -> bool:
    """True if ``query`` (already lowercased) appears in the title or in any
    message's text content — a conversation "matches" by title OR content."""
    if query in (title or "").lower():
        return True
    for m in messages or []:
        content = m.get("content")
        if isinstance(content, str) and query in content.lower():
            return True
    return False


def history_dirs() -> list:
    """Các cặp ``(project_id, thư mục lịch sử)`` của MỌI project, cộng thư mục
    mặc định cho hội thoại chưa thuộc project nào.

    Có hàm này vì lịch sử KHÔNG nằm chung một chỗ, mà nằm trong thư mục làm việc
    của từng project. Ai chỉ gọi ``list_conversations()`` một lần sẽ chỉ thấy
    hội thoại của project đang mở — hoặc, nếu gọi không tham số, không thấy cái
    nào cả. Đó chính là hai lỗi đã xảy ra: khung "Tất cả project…" hiện nhóm
    rỗng cho mọi project trừ một, và mọi dòng project đều đếm "0 đoạn chat".
    """
    from ..config import HISTORY_DIR
    from .projects import list_projects, project_history_dir

    pairs = [("default", HISTORY_DIR)]
    for project in list_projects():
        pairs.append((project.project_id, project_history_dir(project)))
    return pairs


def list_conversations_by_project(pairs, query: str = "") -> List[Dict[str, Any]]:
    """Gộp lịch sử hội thoại của NHIỀU project. ``pairs`` là các cặp
    ``(project_id, directory)``.

    Lịch sử KHÔNG nằm chung một chỗ: ``WorkspaceTab`` đặt
    ``config._project_history_dir`` thành ``<workspace của project>/.cowork_history``
    mỗi lần người dùng chọn project khác, nên ``config.history_dir()`` chỉ trả về
    thư mục của project ĐANG mở. Một lần gọi :func:`list_conversations` vì thế
    chỉ thấy được hội thoại của project đó — khung "Tất cả project…" dựng đủ
    tiêu đề nhóm cho mọi project nhưng mọi nhóm trừ một đều rỗng.

    Thư mục là chủ sở hữu có thẩm quyền: hội thoại nằm trong thư mục làm việc của
    project nào thì thuộc project đó, kể cả khi trường ``project_id`` ghi trong
    file đã cũ (project bị đổi thư mục chẳng hạn).
    """
    seen: set = set()
    items: List[Dict[str, Any]] = []
    for project_id, directory in pairs:
        if directory is None:
            continue
        for meta in list_conversations(directory, query=query):
            key = str(meta["path"])
            if key in seen:
                continue
            seen.add(key)
            if project_id:
                meta["project_id"] = project_id
            items.append(meta)
    # Cùng thứ tự mà list_conversations dùng: ghim lên đầu, rồi mới nhất trước.
    items.sort(key=lambda d: (not d["pinned"], -d["mtime"]))
    return items


def list_conversations(directory: Optional[Path] = None, query: str = "") -> List[Dict[str, Any]]:
    """List saved conversations, most recent first (pinned always on top).

    ``query`` (from the sidebar's search box), when non-empty, keeps only
    conversations whose title OR any message's content contains it
    (case-insensitive) — since every file is already parsed to build the
    metadata below, this search costs no extra I/O over listing alone."""
    if directory is None:
        from ..config import HISTORY_DIR
        directory = HISTORY_DIR
    if not directory or not directory.exists():
        return []
    q = (query or "").strip().lower()
    try:
        cache_key = (str(directory.resolve()), q, directory.stat().st_mtime_ns)
    except OSError:
        return []
    cached = _LIST_CACHE.get(cache_key)
    if cached is not None:
        return [dict(item) for item in cached]
    items: List[Dict[str, Any]] = []
    with span("history.list", query=bool(q)):
      for path in directory.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, list):
            data = {"kind": "", "title": derive_title(data), "messages": data}
        title = data.get("title", path.stem)
        if q and not _matches_query(q, title, data.get("messages", [])):
            continue
        items.append({
            "path": path,
            "kind": data.get("kind", ""),
            "title": title,
            "created": data.get("created", ""),
            "session_id": data.get("session_id", path.stem),
            "pinned": bool(data.get("pinned", False)),
            "project_id": data.get("project_id", "") or "default",
            "count": len(data.get("messages", [])),
            "mtime": path.stat().st_mtime,
        })
    # pinned first, then most recent
    items.sort(key=lambda d: (not d["pinned"], -d["mtime"]))
    _LIST_CACHE[cache_key] = [dict(item) for item in items]
    # Keep this bounded; old directory signatures become unreachable after a
    # write and should not grow process memory forever.
    if len(_LIST_CACHE) > 256:
        for old in list(_LIST_CACHE)[:64]:
            _LIST_CACHE.pop(old, None)
    return items
