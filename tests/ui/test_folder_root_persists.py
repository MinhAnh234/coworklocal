"""Thư mục người dùng tự chọn ở tab Thư mục không được biến mất khi chuyển tab.

Hai lỗi riêng biệt cùng gây ra triệu chứng "chọn folder khác, sang tab khác rồi
quay lại thì về folder cũ":

1. ``WorkspaceFileTree.root_changed`` **không có ai lắng nghe**. Người dùng chọn
   thư mục trong cây thì chỉ cái cây đổi gốc; ``_root``, khung xem và terminal ở
   lại thư mục cũ. Tín hiệu chết.
2. ``WorkspaceTab._load_current`` gọi ``set_root(project.workspace_dir())`` vô
   điều kiện, và ``_goto`` gọi ``workspace.refresh()`` mỗi lần vào lại màn
   Workspace — nên mỗi cú chuyển tab kéo thư mục về workspace của project.

Đổi sang project KHÁC thì vẫn phải re-root: thư mục của màn này thuộc về project.
Chỉ có lần refresh trong cùng một project là không được đụng.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="cần PySide6 để dựng widget thật")


class _Cfg:
    """Đủ cho FolderTab, không hơn."""

    def __init__(self, out_dir):
        self._out = str(out_dir)
        self.data = {}

    def cowork_output_dir(self):
        from pathlib import Path
        return Path(self._out)


class _Ctx:
    def __init__(self, out_dir):
        self.config = _Cfg(out_dir)


@pytest.fixture
def folder_tab(qapp, tmp_path):
    from cowork_local.presentation.folder.folder_tab import FolderTab

    goc = tmp_path / "goc-ban-dau"
    goc.mkdir()
    tab = FolderTab(_Ctx(goc))
    yield tab, tmp_path
    tab.deleteLater()


# ---- lỗi 1: tín hiệu chết ------------------------------------------------

def test_nguoi_dung_chon_thu_muc_thi_khung_xem_va_terminal_theo_kip(folder_tab, tmp_path):
    """``root_changed`` phải được nối, không thì ba widget con lệch nhau."""
    tab, base = folder_tab
    moi = base / "nguoi-dung-chon"
    moi.mkdir()

    tab.tree.set_root(str(moi))       # phát root_changed như khi bấm chọn thư mục

    assert tab._root == str(moi)
    assert tab.preview._root == str(moi)


# ---- lỗi 2: refresh không được ghi đè lựa chọn tay ----------------------

def test_refresh_cung_project_khong_keo_ve_thu_muc_cu(folder_tab, tmp_path):
    """Đây chính là triệu chứng: chuyển tab rồi quay lại là mất lựa chọn."""
    tab, base = folder_tab
    ws = base / "workspace-cua-project"
    ws.mkdir()
    tab.set_project_root(str(ws))          # vào màn lần đầu

    nguoi_dung_chon = base / "folder-khac"
    nguoi_dung_chon.mkdir()
    tab.tree.set_root(str(nguoi_dung_chon))

    tab.set_project_root(str(ws))          # chuyển tab rồi quay lại -> refresh

    assert tab._root == str(nguoi_dung_chon), "lựa chọn tay bị ghi đè"


def test_doi_sang_project_khac_thi_van_re_root(folder_tab, tmp_path):
    """Thư mục của màn này thuộc về project — đổi project là phải đổi theo."""
    tab, base = folder_tab
    ws_a = base / "ws-a"
    ws_b = base / "ws-b"
    ws_a.mkdir()
    ws_b.mkdir()

    tab.set_project_root(str(ws_a))
    khac = base / "tu-chon"
    khac.mkdir()
    tab.tree.set_root(str(khac))

    tab.set_project_root(str(ws_b))        # người dùng đổi project

    assert tab._root == str(ws_b)


def test_quay_lai_project_cu_thi_ve_workspace_cua_no(folder_tab, tmp_path):
    tab, base = folder_tab
    ws_a = base / "ws-a"
    ws_b = base / "ws-b"
    ws_a.mkdir()
    ws_b.mkdir()

    tab.set_project_root(str(ws_a))
    tab.set_project_root(str(ws_b))
    tab.set_project_root(str(ws_a))

    assert tab._root == str(ws_a)


def test_lan_dau_vao_man_van_ap_duoc_goc(folder_tab, tmp_path):
    """``_project_root`` khởi tạo rỗng nên lần gọi đầu không bị bỏ qua."""
    tab, base = folder_tab
    ws = base / "ws"
    ws.mkdir()

    tab.set_project_root(str(ws))

    assert tab._root == str(ws)


# ---- chỗ gọi phải dùng hàm mới -------------------------------------------

def test_workspace_tab_goi_set_project_root_chu_khong_set_root():
    from pathlib import Path

    src = (Path(__file__).resolve().parents[2] / "ui" / "workspace_tab.py").read_text(encoding="utf-8")

    assert "_folder.set_project_root(" in src
    assert "_folder.set_root(" not in src, (
        "gọi set_root() vô điều kiện là quay lại đúng lỗi cũ")
