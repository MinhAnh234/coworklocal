"""Project chọn ở tab GraphRAG không được biến mất khi chuyển tab.

Cùng khuôn với ``test_folder_root_persists.py``: ``WorkspaceTab._bind_project``
gọi ``self._structure.set_project(pid)`` vô điều kiện, và nó chạy lại mỗi lần
người dùng vào lại màn Workspace (``_goto`` → ``refresh`` → ``_load_current`` →
``_bind_project``). Nên bộ chọn project của chính màn GraphRAG bị kéo về giá trị
của Workspace mỗi cú chuyển tab.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="cần PySide6 để dựng widget thật")


class _Ghi:
    """Thay GraphRenderer — chỉ ghi lại nó bị áp project mấy lần, với giá trị gì."""

    def __init__(self):
        self.lan_ap = []

    def set_project(self, project_id):
        self.lan_ap.append(project_id)


@pytest.fixture
def view(qapp, monkeypatch):
    """StructureGraphView với renderer bị thay — dựng renderer thật kéo theo
    QtWebEngine, quá đắt cho một khẳng định về luồng điều khiển."""
    from cowork_local.presentation.graph.structure_graph_view import StructureGraphView

    v = StructureGraphView.__new__(StructureGraphView)
    v._workspace_project = None
    v.renderer = _Ghi()
    return v


def test_lan_dau_van_ap_du_project_la_rong(view):
    """``None`` khởi tạo để lần gọi đầu không bị bỏ qua khi pid là chuỗi rỗng."""
    view.set_workspace_project("")

    assert view.renderer.lan_ap == [""]


def test_refresh_cung_project_khong_ap_lai(view):
    """Đây chính là triệu chứng: chuyển tab rồi quay lại là mất lựa chọn."""
    view.set_workspace_project("p-a")
    view.set_workspace_project("p-a")      # chuyển tab rồi quay lại -> refresh
    view.set_workspace_project("p-a")

    assert view.renderer.lan_ap == ["p-a"], "áp lại là kéo bộ chọn về, xoá lựa chọn tay"


def test_doi_project_o_workspace_thi_van_ap(view):
    """Đổi project thật thì GraphRAG phải theo."""
    view.set_workspace_project("p-a")
    view.set_workspace_project("p-b")

    assert view.renderer.lan_ap == ["p-a", "p-b"]


def test_quay_lai_project_cu_thi_ap_lai(view):
    view.set_workspace_project("p-a")
    view.set_workspace_project("p-b")
    view.set_workspace_project("p-a")

    assert view.renderer.lan_ap == ["p-a", "p-b", "p-a"]


def test_bo_khoa_van_di_qua_duoc(view):
    """Bỏ chọn project ở Workspace là một thay đổi thật, không phải refresh."""
    view.set_workspace_project("p-a")
    view.set_workspace_project("")

    assert view.renderer.lan_ap == ["p-a", ""]


# ---- chỗ gọi phải dùng hàm mới -------------------------------------------

def test_workspace_tab_goi_set_workspace_project():
    from pathlib import Path

    src = (Path(__file__).resolve().parents[2] / "ui" / "workspace_tab.py").read_text(encoding="utf-8")

    assert "_structure.set_workspace_project(pid)" in src
    assert "_structure.set_project(pid)" not in src, (
        "gọi set_project() vô điều kiện là quay lại đúng lỗi cũ")
