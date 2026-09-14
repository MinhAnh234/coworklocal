"""Màn hình app mở lên lần đầu.

Trước đây `MainWindow.__init__` gọi `_goto(ROW_WORKSPACE, current_subtab())` rồi
ngay sau đó `_restore_sessions()` lại `_show_cowork_tab()` để mở lại hội thoại
lần trước. Kết quả: thứ người dùng thấy khi bật app là cuộc trò chuyện cũ, không
phải danh sách project — và dòng landing ở trên trông như đang quyết định điều đó
trong khi thực ra bị ghi đè vài chục dòng sau.

Giờ landing được chốt SAU restore: hội thoại cũ vẫn được nạp lại (đó là mục đích
của restore — phục hồi sau khi thoát đột ngột), nhưng khung nhìn đầu tiên là
"Tất cả project…".
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="cần PySide6 để dựng cửa sổ thật")


@pytest.fixture
def window(qapp, tmp_path):
    from cowork_local.presentation.shell.bootstrap import build_config, build_context
    from cowork_local.presentation.shell.main_window import MainWindow

    config_path = tmp_path / "config.json"
    build_config(config_path)
    win = MainWindow(build_context(config_path))
    yield win
    win.close()


def test_mo_app_len_thi_dung_o_man_workspace(window):
    """Vẫn là màn Workspace, không phải Dashboard/Lịch/Giám sát."""
    assert window.pages.currentIndex() == window._ROW_WORKSPACE


def test_mo_app_len_thi_o_khung_tat_ca_project(window):
    """Đúng khung mà link "Tất cả project…" ở thanh menu mở ra.

    Trừ khi cổng project đang giữ nó đóng: chưa có project nào thì sub-tab
    Cowork bị ẩn, và màn hình đúng cho người dùng đó là màn quản lý project.
    Ép mở bằng cửa sau sẽ để nội dung ở Cowork trong khi cổng nói là Project.
    """
    ws = window.workspace
    if ws.subtab_available(ws._cowork_tab_idx):
        assert ws.current_subtab() == ws._cowork_tab_idx
        assert ws._history_opened is True
    else:
        assert ws.current_subtab() == ws._project_tab_idx


def test_bang_lich_su_khong_bi_an_di(window):
    """Danh sách phải nhìn thấy được — mở đúng tab mà bảng vẫn gập là vô nghĩa.

    Dùng ``isHidden()`` chứ không ``isVisible()``: test không gọi ``show()`` trên
    cửa sổ (bật cửa sổ thật lên sẽ nhảy ra trước mặt người đang làm việc), mà
    ``isVisible()`` của widget con chỉ True khi đã có tổ tiên được hiện.
    ``isHidden()`` phản ánh đúng thứ ta quan tâm: có ai gọi ``setVisible(False)``
    lên nó hay không.
    """
    ws = window.workspace
    if not ws.subtab_available(ws._cowork_tab_idx):
        pytest.skip("cổng project đang đóng — bảng lịch sử không thuộc màn này")
    assert ws._sidebar.isHidden() is False


# ---- vệt sáng thanh menu phải khớp nội dung ------------------------------
#
# Bug: mở app lên ở khung "Tất cả project…" thì bấm "Project" trên thanh menu
# KHÔNG có tác dụng; phải bấm sang mục khác rồi bấm về mới được.
#
# Nguyên nhân: landing gọi thẳng ``workspace.show_history_pane()``, đổi nội dung
# sang sub-tab Cowork nhưng bỏ qua ``_goto`` — chỗ duy nhất dời vệt sáng. Vệt
# sáng ở lại "Project", mà QTreeWidget không phát ``currentItemChanged`` khi bấm
# lại đúng dòng đang chọn, nên cú bấm rơi vào hư không.

def _hang_dang_chon(window):
    """(page, sub) mà thanh menu đang tô sáng, hoặc None."""
    from PySide6.QtCore import Qt

    for tree in (window.nav, window.nav_bottom):
        item = tree.currentItem()
        if item is not None:
            data = item.data(0, Qt.UserRole) or {}
            return data.get("page"), data.get("sub")
    return None


def test_vet_sang_thanh_menu_khop_voi_noi_dung_dang_hien(window):
    """Không khớp là cú bấm đầu tiên vào đúng mục đó sẽ rơi vào hư không."""
    dang_chon = _hang_dang_chon(window)

    assert dang_chon is not None, "thanh menu không tô sáng dòng nào"
    page, sub = dang_chon
    assert page == window._ROW_WORKSPACE
    # Bat bien that su quan trong: vet sang KHOP noi dung. Man hinh ha canh la
    # cai nao thi tuy cong project, nhung hai thu nay khong bao gio duoc lech.
    assert sub == window.workspace.current_subtab(), (
        f"nội dung ở sub-tab {window.workspace.current_subtab()} "
        f"nhưng thanh menu đang sáng ở {sub}")


def test_bam_project_tren_thanh_menu_an_ngay_lan_dau(window):
    """Tái hiện đúng thao tác của người dùng: mở app xong bấm ngay "Project"."""
    from PySide6.QtCore import Qt

    project_sub = window.workspace._project_tab_idx
    muc_project = None
    for i in range(window.nav.topLevelItemCount()):
        it = window.nav.topLevelItem(i)
        data = it.data(0, Qt.UserRole) or {}
        if data.get("page") == window._ROW_WORKSPACE and data.get("sub") == project_sub:
            muc_project = it
            break
    if muc_project is None:
        pytest.skip("thanh menu chưa dựng mục con cho sub-tab Project")

    if window.workspace.current_subtab() == project_sub:
        pytest.skip("cổng project đang đóng — app đã hạ cánh sẵn ở màn Project")

    assert window.nav.currentItem() is not muc_project, (
        "mục Project đang được tô sáng sẵn dù nội dung ở Cowork — "
        "bấm vào nó sẽ không phát tín hiệu nào")

    window.nav.setCurrentItem(muc_project)

    assert window.workspace.current_subtab() == project_sub


def test_khi_cong_project_MO_thi_ha_canh_o_cowork_va_vet_sang_theo(window):
    """Nhánh của người dùng ĐÃ chọn một project — nhánh mà bug được báo.

    Trước đây bài này mở cổng bằng cửa sau ``setTabVisible(True)`` vì môi trường
    test không có project nào (``core/projects.py`` ghi vào ``~/.cowork_local``
    thật, nên test không tạo project). Cửa sau đó hết tác dụng từ khi cổng được
    điều khiển bằng ``_current_id``: ``refresh()``/``goto_all_projects()`` đóng
    lại ngay. Giờ mở cổng bằng đúng đường thật — chọn một project — và bỏ qua
    bài này trên máy chưa có project nào.
    """
    from PySide6.QtCore import Qt

    ws = window.workspace
    if ws._cowork_tab_idx < 0:
        pytest.skip("bản dựng này không có sub-tab Cowork")
    if ws.project_list.count() == 0:
        pytest.skip("máy chạy test chưa có project nào — cổng không mở được")

    ws.project_list.setCurrentRow(0)
    try:
        window.goto_all_projects()

        assert ws.current_subtab() == ws._cowork_tab_idx
        assert ws._history_opened is True

        item = window.nav.currentItem()
        assert item is not None, "thanh menu không tô sáng dòng nào"
        data = item.data(0, Qt.UserRole) or {}
        assert data.get("sub") == ws._cowork_tab_idx, (
            f"nội dung ở Cowork ({ws._cowork_tab_idx}) "
            f"nhưng thanh menu sáng ở {data.get('sub')}")
    finally:
        ws.project_list.setCurrentRow(-1)   # đóng cổng lại đúng đường thật
        window.goto_all_projects()
