"""Mirror a OneDrive/SharePoint folder to/from a local directory (DF-007).

This is deliberately NOT a general sync engine: every existing tool
(``run_command``, ``read_file``, ``write_file``...) operates on a real local
``Path`` (``Project.output_dir`` — see ``core/projects.py::Project.workspace_dir``),
and that contract does not change here. A cloud-backed project's
``output_dir`` still points at a real local folder; this module only knows how
to pull that folder's content down from Graph once, and push it back up once,
both on explicit user action (a button click) — there is no background
watcher, no continuous sync, no delete propagation, and no conflict
resolution beyond "whichever side ran last wins" for a given file. See the
DF-007 plan for why: OneDrive/SharePoint sync-client detection is unreliable,
so a local mirror + manual sync is the only predictable option that does not
touch the sandboxed command/file tools.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from . import ms365_graph as graph


@dataclass
class SyncReport:
    """Kết quả một lượt tải xuống/đẩy lên — hiển thị cho người dùng sau khi chạy."""
    transferred: int = 0
    skipped_too_large: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def _list_children(token: str, cloud_source: Dict[str, str], remote_path: str) -> List[dict]:
    provider = cloud_source.get("provider")
    if provider == "sharepoint":
        return graph.list_sharepoint_files(token, cloud_source["site_id"], remote_path)
    return graph.list_onedrive_files(token, remote_path)


def _download_file(token: str, cloud_source: Dict[str, str], remote_path: str) -> bytes:
    if cloud_source.get("provider") == "sharepoint":
        return graph.download_sharepoint_file_bytes(token, cloud_source["site_id"], remote_path)
    return graph.download_onedrive_file_bytes(token, remote_path)


def _upload_file(token: str, cloud_source: Dict[str, str], remote_path: str, data: bytes) -> None:
    if cloud_source.get("provider") == "sharepoint":
        graph.upload_sharepoint_file_bytes(token, cloud_source["site_id"], remote_path, data)
    else:
        graph.upload_onedrive_file_bytes(token, remote_path, data)


def download_folder(token: str, cloud_source: Dict[str, str], local_dir: Path) -> SyncReport:
    """Tải toàn bộ cây thư mục ``cloud_source['remote_path']`` xuống ``local_dir``,
    giữ nguyên cấu trúc thư mục con. Ghi đè file local nếu đã tồn tại (một
    chiều: cloud thắng). Không xoá file local nào không còn ở phía cloud."""
    report = SyncReport()
    root_remote = cloud_source.get("remote_path", "")
    local_dir.mkdir(parents=True, exist_ok=True)

    def _walk(remote_path: str, local_sub: Path) -> None:
        try:
            children = _list_children(token, cloud_source, remote_path)
        except graph.Ms365GraphError as exc:
            report.errors.append(f"{remote_path or '/'}: {exc}")
            return
        for item in children:
            name = item.get("name", "")
            if not name:
                continue
            child_remote = f"{remote_path}/{name}" if remote_path else name
            child_local = local_sub / name
            if "folder" in item:
                child_local.mkdir(parents=True, exist_ok=True)
                _walk(child_remote, child_local)
            else:
                try:
                    data = _download_file(token, cloud_source, child_remote)
                    child_local.write_bytes(data)
                    report.transferred += 1
                except graph.Ms365GraphError as exc:
                    report.errors.append(f"{child_remote}: {exc}")

    _walk(root_remote, local_dir)
    return report


def upload_folder(token: str, cloud_source: Dict[str, str], local_dir: Path) -> SyncReport:
    """Đẩy mọi file dưới ``local_dir`` lên đúng đường dẫn tương ứng phía cloud
    (tạo mới hoặc ghi đè). Một chiều: local thắng cho từng file được duyệt qua.
    Không xoá file cloud nào đã bị xoá ở local, không phát hiện xung đột."""
    report = SyncReport()
    root_remote = cloud_source.get("remote_path", "")
    local_dir = Path(local_dir)
    for dirpath, _dirnames, filenames in os.walk(local_dir):
        rel_dir = Path(dirpath).relative_to(local_dir)
        for fname in filenames:
            local_file = Path(dirpath) / fname
            rel_parts = [] if str(rel_dir) == "." else list(rel_dir.parts)
            rel_parts.append(fname)
            child_remote = "/".join(([root_remote] if root_remote else []) + rel_parts)
            try:
                data = local_file.read_bytes()
                _upload_file(token, cloud_source, child_remote, data)
                report.transferred += 1
            except graph.Ms365GraphError as exc:
                if "too large" in str(exc):
                    report.skipped_too_large.append(child_remote)
                else:
                    report.errors.append(f"{child_remote}: {exc}")
            except OSError as exc:
                report.errors.append(f"{child_remote}: {exc}")
    return report
