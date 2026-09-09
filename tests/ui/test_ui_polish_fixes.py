"""Sáu chỗ chỉnh nhỏ trên giao diện, mỗi bài chốt đúng một triệu chứng đã báo.

Gom một file vì chúng không chia sẻ gì ngoài việc đều là phản hồi từ người dùng
trong cùng một vòng; tách sáu file cho sáu khẳng định chỉ tạo thêm chỗ để tìm.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


# ---- bỏ nhãn "provider · model" cạnh chữ Cowork --------------------------

def test_thanh_cong_cu_cowork_khong_con_nhan_provider():
    """Nó lặp lại thứ bộ chọn provider ở thanh trên đang hiển thị."""
    src = (REPO / "ui" / "cowork_tab.py").read_text(encoding="utf-8")

    assert "model_lbl" not in src
    assert "PROVIDER_LABELS" not in src, "import đã thành vô dụng thì phải gỡ"


# ---- không báo trạng thái khi đổi provider -------------------------------

def test_doi_provider_khong_bao_o_thanh_trang_thai():
    """Bộ chọn nằm ngay trên màn hình và đã hiện thứ vừa chọn."""
    src = (REPO / "presentation" / "shell" / "top_bar.py").read_text(encoding="utf-8")
    than_ham = src.split("def _on_provider_changed")[1].split("def _on_language_changed")[0]

    assert "showMessage" not in than_ham
    assert "using_provider" not in than_ham


# ---- tên project mặc định không gắn ngôn ngữ ----------------------------

def test_ten_project_mac_dinh_khong_qua_tr():
    """Tên project được GHI XUỐNG ĐĨA.

    Tạo project lúc đang ở tiếng Nhật thì tên nó thành "新規プロジェクト" vĩnh
    viễn, và đổi ngôn ngữ về tiếng Việt không sửa được — đó là dữ liệu, không
    phải chữ giao diện. Người dùng nhìn thấy chữ Nhật trên màn tiếng Việt và
    tưởng là lỗi hiển thị.
    """
    from cowork_local.presentation.workspace import project_editing as pe

    assert pe._DEFAULT_PROJECT_NAME.isascii(), "tên mặc định phải trung tính"
    src = (REPO / "presentation" / "workspace" / "project_editing.py").read_text(encoding="utf-8")
    than_ham = src.split("def _create")[1].split("def _delete")[0]
    assert 'tr("workspace.default_new_name")' not in than_ham


def test_ten_mac_dinh_khong_trung_nhau(monkeypatch):
    """Bấm "Project mới" hai lần liên tiếp không được ra hai tên giống nhau."""
    from cowork_local.presentation.workspace.project_editing import (
        ProjectEditingMixin, _DEFAULT_PROJECT_NAME,
    )
    import cowork_local.core.projects as projects

    class _P:
        def __init__(self, pid, name):
            self.project_id, self.name = pid, name

    da_co = [_P("p1", _DEFAULT_PROJECT_NAME)]
    monkeypatch.setattr(projects, "list_projects", lambda: da_co)

    class _K:
        _name_taken = ProjectEditingMixin._name_taken

    assert _K()._name_taken(_DEFAULT_PROJECT_NAME) is True
    assert _K()._name_taken(f"{_DEFAULT_PROJECT_NAME} (2)") is False


# ---- "Tất cả project…" phải hiện MỌI project ----------------------------

def test_tat_ca_project_xoa_bo_loc_theo_project():
    """Bảng lịch sử nhúng trong Cowork của MỘT project nên bị lọc theo project đó.

    Vào bằng link "Tất cả project…" mà còn bộ lọc thì tạo 5 project chỉ thấy 1.
    """
    src = (REPO / "presentation" / "shell" / "rail_project.py").read_text(encoding="utf-8")
    than_ham = src.split("def goto_all_projects")[1].split("def _on_rail_recent")[0]

    assert 'set_project_filter("")' in than_ham


# ---- ba nút quản lý project về cùng một hàng ----------------------------

def test_sua_va_luu_project_cung_hang_voi_project_moi(qapp, tmp_path):
    """Trước đó "Lưu project" nằm dưới cùng khung bên phải, cách "Project mới"
    gần hết chiều cao màn hình."""
    from cowork_local.presentation.shell.bootstrap import build_config, build_context
    from cowork_local.presentation.shell.main_window import MainWindow
    from cowork_local.presentation.workspace.project_editing import _row_layout_of

    config_path = tmp_path / "config.json"
    build_config(config_path)
    win = MainWindow(build_context(config_path))
    try:
        ws = win.workspace
        hang = _row_layout_of(ws._new_btn)

        assert hang is not None, "không tìm được hàng chứa nút Project mới"
        assert _row_layout_of(ws._edit_btn) is hang
        assert _row_layout_of(ws._save_btn) is hang
        # Thu tu doc tu trai sang: tao moi -> sua -> luu
        assert (hang.indexOf(ws._new_btn)
                < hang.indexOf(ws._edit_btn)
                < hang.indexOf(ws._save_btn))
    finally:
        win.close()


def test_hai_nut_project_khong_hien_ngoai_sub_tab_project(qapp, tmp_path):
    """Hàng tiêu đề vắt ngang CẢ màn Workspace.

    Chuyển "Sửa project" + "Lưu project" lên đó (bug 10) làm chúng hiện luôn ở
    Cowork, Co4E, Thư mục và GraphRAG — nơi không có biểu mẫu project nào để sửa
    hay lưu. Đúng luật mà ``_new_btn`` đã theo từ trước.
    """
    from cowork_local.presentation.shell.bootstrap import build_config, build_context
    from cowork_local.presentation.shell.main_window import MainWindow

    config_path = tmp_path / "config.json"
    build_config(config_path)
    win = MainWindow(build_context(config_path))
    try:
        ws = win.workspace
        ws._current_id = "gia-lap"

        ws.tabs.setCurrentIndex(ws._project_tab_idx)
        ws._sync_project_buttons()
        assert ws._edit_btn.isHidden() is False
        assert ws._save_btn.isHidden() is False

        if ws._cowork_tab_idx < 0:
            pytest.skip("bản dựng này không có sub-tab Cowork")
        ws.tabs.setTabVisible(ws._cowork_tab_idx, True)
        ws.tabs.setCurrentIndex(ws._cowork_tab_idx)
        ws._sync_project_buttons()

        assert ws._edit_btn.isHidden() is True, "nút Sửa project lọt sang tab Cowork"
        assert ws._save_btn.isHidden() is True, "nút Lưu project lọt sang tab Cowork"
    finally:
        win.close()


def test_chua_chon_project_thi_hai_nut_cung_an(qapp, tmp_path):
    """Không có project nào đang mở thì cả Sửa lẫn Lưu đều vô nghĩa."""
    from cowork_local.presentation.shell.bootstrap import build_config, build_context
    from cowork_local.presentation.shell.main_window import MainWindow

    config_path = tmp_path / "config.json"
    build_config(config_path)
    win = MainWindow(build_context(config_path))
    try:
        ws = win.workspace
        ws._current_id = ""
        ws.tabs.setCurrentIndex(ws._project_tab_idx)
        ws._sync_project_buttons()

        assert ws._edit_btn.isHidden() is True
        assert ws._save_btn.isHidden() is True
    finally:
        win.close()
