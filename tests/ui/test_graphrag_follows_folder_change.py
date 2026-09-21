"""Đổi thư mục làm việc thì màn GraphRAG phải trỏ theo thư mục mới.

Triệu chứng: ở tab Project bấm "Đổi" sang một đường dẫn khác — ô Thư mục làm
việc cập nhật ngay, tên project vẫn đúng, nên nhìn qua tưởng xong. Nhưng màn
GraphRAG vẫn giữ đường dẫn cũ và quét nhầm thư mục.

Nguyên nhân có hai mảnh, thiếu mảnh nào cũng vẫn hỏng:

* ``_pick_folder`` ghi ``output_dir`` rồi dừng — đổi thư mục không làm project
  id đổi nên không có gì trong luồng chọn project chạy lại.
* Kể cả có chạy lại, ``StructureGraphView.set_workspace_project`` ngày trước
  chốt theo MỖI project id, nên cùng một project là nó thoát ra ngay. Tab Thư
  mục vốn đã chốt theo ĐƯỜNG DẪN — hai nơi tưởng cùng luật mà thật ra không.

Giống ``test_graphrag_project_persists.py``: KHÔNG dựng renderer thật, vì nó
kéo theo QtWebEngine — dựng nó trong bộ ``tests/ui`` làm cả bộ chết giữa chừng.
Thứ cần chốt ở đây là luồng điều khiển, không phải phần vẽ.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="cần PySide6 để dựng widget thật")

from cowork_local.core import projects as projects_mod
from cowork_local.core.projects import Project


class _RendererGhi:
    """Thay GraphRenderer — chỉ ghi lại nó bị áp project mấy lần."""

    def __init__(self):
        self.lan_ap = []

    def set_project(self, project_id):
        self.lan_ap.append(project_id)


@pytest.fixture
def view(qapp):
    """``StructureGraphView`` với renderer bị thay, dựng qua ``__new__``."""
    from cowork_local.presentation.graph.structure_graph_view import StructureGraphView

    v = StructureGraphView.__new__(StructureGraphView)
    v._workspace_project = None
    v._workspace_dir = None
    v.renderer = _RendererGhi()
    return v


def _kho_mot_project(monkeypatch, thu_muc) -> Project:
    """Kho project giả gồm đúng một project trỏ vào ``thu_muc``."""
    du_an = Project(project_id="p1", name="Mynt4Project1", output_dir=str(thu_muc))
    monkeypatch.setattr(projects_mod, "list_projects", lambda directory=None: [du_an])
    monkeypatch.setattr(projects_mod, "load_project",
                        lambda pid, directory=None: du_an if pid == "p1" else None)
    monkeypatch.setattr(projects_mod, "save_project", lambda p, directory=None: None)
    return du_an


# ---- mảnh 1: chốt của GraphRAG phải nhìn cả đường dẫn -------------------

def test_cung_project_nhung_thu_muc_moi_thi_ap_lai(view, monkeypatch, tmp_path):
    """Đây là chỗ chốt cũ bỏ lọt: id giống nhau nhưng đường dẫn đã khác."""
    du_an = _kho_mot_project(monkeypatch, tmp_path / "cu")
    view.set_workspace_project("p1")
    assert view.renderer.lan_ap == ["p1"]

    du_an.output_dir = str(tmp_path / "moi")
    view.set_workspace_project("p1")

    assert view.renderer.lan_ap == ["p1", "p1"], (
        "đổi thư mục xong mà GraphRAG không được áp lại — sẽ quét nhầm chỗ")


def test_cung_project_cung_thu_muc_thi_khong_ap_lai(view, monkeypatch, tmp_path):
    """Chốt cũ phải giữ nguyên: mỗi lần vào lại màn Workspace,
    ``_bind_project`` chạy lại — áp vô điều kiện là kéo bộ chọn project của
    chính màn GraphRAG về theo, chọn xong chuyển tab là mất."""
    _kho_mot_project(monkeypatch, tmp_path / "yen")
    view.set_workspace_project("p1")

    view.set_workspace_project("p1")
    view.set_workspace_project("p1")

    assert view.renderer.lan_ap == ["p1"]


def test_doi_sang_project_khac_van_ap(view, monkeypatch, tmp_path):
    """Hành vi vốn có: đổi sang project khác thì vẫn phải áp."""
    _kho_mot_project(monkeypatch, tmp_path / "a")
    view.set_workspace_project("p1")

    view.set_workspace_project("p2")

    assert view.renderer.lan_ap == ["p1", "p2"]


# ---- mảnh 2: đổi thư mục phải kích hoạt việc trỏ lại --------------------

class _StructureGhi:
    """Thay cả màn GraphRAG — ghi lại nó được trỏ lại vào project nào."""

    def __init__(self):
        self.lan_tro = []

    def set_workspace_project(self, project_id):
        self.lan_tro.append(project_id)


class _FolderGhi:
    """Thay tab Thư mục — ghi lại nó được trỏ vào đường dẫn nào."""

    def __init__(self):
        self.lan_tro = []

    def set_project_root(self, path):
        self.lan_tro.append(path)


@pytest.fixture(scope="module")
def ws(qapp, tmp_path_factory):
    """Màn Workspace thật, nhưng KHÔNG mở tab GraphRAG (xem docstring đầu file)."""
    from cowork_local.presentation.shell.bootstrap import build_config, build_context
    from cowork_local.presentation.shell.main_window import MainWindow

    config_path = tmp_path_factory.mktemp("cfg") / "config.json"
    build_config(config_path)
    window = MainWindow(build_context(config_path))
    yield window.workspace
    window.close()


def test_bam_doi_thu_muc_thi_graphrag_duoc_tro_lai(qapp, ws, monkeypatch, tmp_path):
    """Đúng thao tác người dùng báo: bấm "Đổi" ở tab Project."""
    from PySide6.QtWidgets import QFileDialog

    from cowork_local.ui import workspace_tab as wt

    cu, moi = tmp_path / "thu-muc-cu", tmp_path / "thu-muc-moi"
    cu.mkdir()
    moi.mkdir()
    du_an = _kho_mot_project(monkeypatch, cu)
    structure, folder = _StructureGhi(), _FolderGhi()
    monkeypatch.setattr(ws, "_structure", structure, raising=False)
    monkeypatch.setattr(ws, "_folder", folder, raising=False)
    ws._current_id = "p1"

    monkeypatch.setattr(QFileDialog, "getExistingDirectory",
                        staticmethod(lambda *a, **k: str(moi)))
    wt.WorkspaceTab._pick_folder(ws)

    assert du_an.output_dir == str(moi), "chưa ghi thư mục mới"
    assert ws.folder_lbl.text() == str(moi)
    assert structure.lan_tro == ["p1"], (
        "GraphRAG không được trỏ lại — sẽ giữ đường dẫn cũ và quét nhầm")
    assert folder.lan_tro == [str(moi)], "tab Thư mục cũng phải trỏ theo"
