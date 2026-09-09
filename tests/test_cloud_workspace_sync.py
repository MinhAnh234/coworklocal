"""DF-007 — core/cloud_workspace_sync.py: mirror a cloud folder to/from a
local directory. All Graph calls are faked (monkeypatch on the ``graph``
module the sync module imports) — no network."""
from __future__ import annotations

from pathlib import Path

import pytest

from cowork_local.core import cloud_workspace_sync as sync
from cowork_local.core import ms365_graph as graph


def _fake_tree():
    """root/
         a.txt
         sub/
           b.txt
    """
    files = {"a.txt": b"hello", "sub/b.txt": b"world"}
    listing = {
        "": [{"name": "a.txt"}, {"name": "sub", "folder": {}}],
        "sub": [{"name": "b.txt"}],
    }
    return files, listing


def test_download_folder_mirrors_tree(tmp_path: Path, monkeypatch) -> None:
    files, listing = _fake_tree()

    def fake_list_onedrive_files(token, path=""):
        return listing.get(path, [])

    def fake_download_bytes(token, path):
        return files[path]

    monkeypatch.setattr(graph, "list_onedrive_files", fake_list_onedrive_files)
    monkeypatch.setattr(graph, "download_onedrive_file_bytes", fake_download_bytes)

    local_dir = tmp_path / "mirror"
    report = sync.download_folder("tok", {"provider": "onedrive", "remote_path": ""}, local_dir)

    assert report.transferred == 2
    assert report.errors == []
    assert (local_dir / "a.txt").read_bytes() == b"hello"
    assert (local_dir / "sub" / "b.txt").read_bytes() == b"world"


def test_download_folder_collects_errors_without_raising(tmp_path: Path, monkeypatch) -> None:
    def fake_list_onedrive_files(token, path=""):
        raise graph.Ms365GraphError("boom")

    monkeypatch.setattr(graph, "list_onedrive_files", fake_list_onedrive_files)

    local_dir = tmp_path / "mirror"
    report = sync.download_folder("tok", {"provider": "onedrive", "remote_path": ""}, local_dir)

    assert report.transferred == 0
    assert len(report.errors) == 1
    assert "boom" in report.errors[0]


def test_upload_folder_pushes_every_file(tmp_path: Path, monkeypatch) -> None:
    local_dir = tmp_path / "mirror"
    (local_dir / "sub").mkdir(parents=True)
    (local_dir / "a.txt").write_bytes(b"hello")
    (local_dir / "sub" / "b.txt").write_bytes(b"world")

    uploaded = {}

    def fake_upload_bytes(token, path, data):
        uploaded[path] = data
        return {}

    monkeypatch.setattr(graph, "upload_onedrive_file_bytes", fake_upload_bytes)

    report = sync.upload_folder("tok", {"provider": "onedrive", "remote_path": "work"}, local_dir)

    assert report.transferred == 2
    assert uploaded == {"work/a.txt": b"hello", "work/sub/b.txt": b"world"}


def test_upload_folder_reports_files_over_the_simple_upload_limit(tmp_path: Path, monkeypatch) -> None:
    local_dir = tmp_path / "mirror"
    local_dir.mkdir()
    (local_dir / "big.bin").write_bytes(b"x")

    def fake_upload_bytes(token, path, data):
        raise graph.Ms365GraphError("File too large for simple upload (huge > 4 bytes)")

    monkeypatch.setattr(graph, "upload_onedrive_file_bytes", fake_upload_bytes)

    report = sync.upload_folder("tok", {"provider": "onedrive", "remote_path": ""}, local_dir)

    assert report.transferred == 0
    assert report.skipped_too_large == ["big.bin"]
    assert report.errors == []


def test_upload_size_guard_rejects_before_any_request(monkeypatch) -> None:
    huge = b"x" * (graph.MAX_SIMPLE_UPLOAD_BYTES + 1)

    def fail_if_called(*a, **k):  # pragma: no cover - must not be reached
        raise AssertionError("_request should not be called for an oversized upload")

    monkeypatch.setattr(graph, "_request", fail_if_called)

    with pytest.raises(graph.Ms365GraphError, match="too large"):
        graph.upload_onedrive_file_bytes("tok", "a.bin", huge)


def test_sharepoint_provider_uses_site_scoped_calls(tmp_path: Path, monkeypatch) -> None:
    seen = {}

    def fake_list_sharepoint_files(token, site_id, path=""):
        seen["list_site_id"] = site_id
        return [{"name": "a.txt"}] if path == "" else []

    def fake_download_sharepoint_bytes(token, site_id, path):
        seen["download_site_id"] = site_id
        return b"hi"

    monkeypatch.setattr(graph, "list_sharepoint_files", fake_list_sharepoint_files)
    monkeypatch.setattr(graph, "download_sharepoint_file_bytes", fake_download_sharepoint_bytes)

    local_dir = tmp_path / "mirror"
    cloud_source = {"provider": "sharepoint", "site_id": "site-123", "remote_path": ""}
    report = sync.download_folder("tok", cloud_source, local_dir)

    assert report.transferred == 1
    assert seen["list_site_id"] == "site-123"
    assert seen["download_site_id"] == "site-123"
