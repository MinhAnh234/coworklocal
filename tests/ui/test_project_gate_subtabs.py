"""Cổng project: Cowork và GraphRAG chỉ hiện khi đã chọn một project cụ thể.

Cổng có hai mặt và trước đây chỉ mặt thứ nhất làm đúng:

* **Sub-tab trong màn Workspace** — ``_update_tab_visibility`` vốn đã ẩn/hiện
  đúng. Chỗ hỏng nằm ở ``refresh()``: nó mặc định ``row_to_select = 0`` nên lúc
  mở app (chưa ai bấm gì) danh sách tự chọn hộ project đầu tiên, mở cổng cho một
  project người dùng chưa hề chọn.
* **Hàng trên menu trái** — ``NavRailMixin._rebuild_nav`` từng dựng hàng ở dạng
  mờ kèm tooltip thay vì bỏ đi ("shown instead of hidden"), nên người dùng vẫn
  thấy Cowork/GraphRAG trên menu dù cổng đang đóng.

Các bài dưới đây chốt cả hai mặt, ở cả ba trạng thái: chưa chọn → ẩn, chọn rồi →
hiện, bỏ chọn → ẩn lại.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="cần PySide6 để dựng cửa sổ thật")


@pytest.fixture
def win(qapp, tmp_path):
    """MainWindow thật — cần cả cửa sổ vì phải kiểm cả menu trái.

    Đọc project từ ``~/.cowork_local`` như bản cài thật (``core/projects.py``
    gắn ``PROJECTS_DIR`` vào đó) nên các bài này KHÔNG tạo/xoá project nào.
    Bài nào cần cổng MỞ thì gọi thẳng ``_update_tab_visibility(True)`` thay vì
    tạo project trên đĩa của người chạy test.
    """
    from cowork_local.presentation.shell.bootstrap import build_config, build_context
    from cowork_local.presentation.shell.main_window import MainWindow

    config_path = tmp_path / "config.json"
    build_config(config_path)
    window = MainWindow(build_context(config_path))
    yield window
    window.close()


def _cong(ws):
    """Hai sub-tab nằm sau cổng project, bỏ qua bản dựng không có chúng."""
    return [(ten, idx) for ten, idx in
            (("Cowork", ws._cowork_tab_idx), ("GraphRAG", ws._graphrag_tab_idx))
            if idx >= 0]


def _hang_menu(win):
    """Nhãn của mọi hàng đang có trên cột menu trái."""
    return [win.nav.topLevelItem(i).text(0) for i in range(win.nav.topLevelItemCount())]


# ---- mặt 1: không tự chọn hộ project ------------------------------------

def test_mo_app_len_chua_chon_thi_khong_tu_chon_ho(win):
    """Đây là nguyên nhân gốc: ``refresh()`` từng mặc định chọn dòng 0."""
    ws = win.workspace

    assert ws._current_id == ""
    assert ws.project_list.currentRow() == -1


def test_chua_chon_project_thi_hai_sub_tab_deu_an(win):
    ws = win.workspace

    for ten, idx in _cong(ws):
        assert ws.tabs.isTabVisible(idx) is False, f"{ten} hiện khi chưa chọn project"
        assert ws.subtab_available(idx) is False, f"{ten} vẫn mở cổng"


def test_chua_chon_project_thi_dung_o_tab_project(win):
    """Ẩn hai tab kia mà lại đứng ở một tab đã ẩn thì màn hình trống trơn."""
    ws = win.workspace

    assert ws.current_subtab() == ws._project_tab_idx


def test_refresh_giu_nguyen_project_dang_chon(win):
    """Sửa cổng không được làm mất lựa chọn hiện có: ``keep`` vẫn phải thắng."""
    ws = win.workspace
    if ws.project_list.count() == 0:
        pytest.skip("máy chạy test chưa có project nào để chọn")

    ws.project_list.setCurrentRow(0)
    dang_chon = ws._current_id

    ws.refresh()

    assert ws._current_id == dang_chon
    assert ws.project_list.currentRow() >= 0


# ---- mặt 2: menu trái bỏ hẳn hàng, không hiện dạng mờ -------------------

def test_chua_chon_project_thi_menu_trai_khong_co_hai_hang(win):
    """Đây là thứ người dùng nhìn thấy — trước đây hai hàng vẫn nằm đó, chỉ mờ."""
    nhan = _hang_menu(win)

    assert "Cowork" not in nhan, f"Cowork vẫn trên menu: {nhan}"
    assert "GraphRAG" not in nhan, f"GraphRAG vẫn trên menu: {nhan}"


def test_mo_cong_thi_hai_hang_quay_lai_menu_trai(win):
    """Bỏ hàng phải đảo ngược được, nếu không thì chọn project xong vẫn kẹt."""
    ws = win.workspace
    ws._current_id = "gia-lap"
    ws._update_tab_visibility(True)

    nhan = _hang_menu(win)
    assert "Cowork" in nhan, f"Cowork không quay lại: {nhan}"
    assert "GraphRAG" in nhan, f"GraphRAG không quay lại: {nhan}"


def test_mo_cong_thi_hai_sub_tab_cung_hien_lai(win):
    ws = win.workspace
    ws._current_id = "gia-lap"
    ws._update_tab_visibility(True)

    for ten, idx in _cong(ws):
        assert ws.tabs.isTabVisible(idx) is True, f"{ten} vẫn ẩn khi cổng đã mở"


def test_dong_cong_lai_thi_hai_hang_bien_mat(win):
    """Cổng phải đóng lại được, không chỉ mở một chiều."""
    ws = win.workspace
    ws._current_id = "gia-lap"
    ws._update_tab_visibility(True)
    ws._current_id = ""
    ws._update_tab_visibility(False)

    nhan = _hang_menu(win)
    assert "Cowork" not in nhan and "GraphRAG" not in nhan, nhan


def test_cac_hang_khac_khong_bi_anh_huong(win):
    """Chỉ hai hàng sau cổng bị bỏ — phần còn lại của menu giữ nguyên."""
    nhan = _hang_menu(win)

    for bat_buoc in ("Project", "Co4E"):
        assert bat_buoc in nhan, f"{bat_buoc} biến mất khỏi menu: {nhan}"
