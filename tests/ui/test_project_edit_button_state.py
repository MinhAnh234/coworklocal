"""Nút "Sửa project" phải sáng ngay khi đã có project đang mở.

Triệu chứng: mở app, chọn một project rồi vào sub-tab Project — biểu mẫu hiện
đủ tên, mô tả, thư mục làm việc, nhưng nút "Sửa project" vẫn mờ, không bấm được.

Nguyên nhân: trạng thái bật/mờ của ba nút chỉ được tính trong
``set_project_editable``, mà đổi project KHÔNG đi qua hàm đó — ``_load_current``
chỉ nạp lại biểu mẫu. ``_sync_project_buttons`` có chạy khi đổi sub-tab nhưng
ngày trước chỉ chỉnh ẩn/hiện, nên nút hiện ra mang theo trạng thái mờ tính từ
lúc dựng cửa sổ, khi chưa project nào được chọn.

Các bài dưới đây chốt cả bốn trạng thái: chưa có project → mờ; có project →
sáng; đi vòng qua sub-tab khác rồi quay lại → vẫn sáng; đang sửa dở → mờ lại
(nếu không thì "đang sửa" và "chưa sửa" trông giống hệt nhau).

Hai quy ước bắt buộc, lấy từ ``test_project_editing.py`` và
``test_project_gate_subtabs.py`` ngay cạnh:

* **Không tạo, không xoá project nào.** ``core/projects.py`` gắn
  ``PROJECTS_DIR`` vào ``~/.cowork_local`` THẬT, nên tạo project trong test là
  ghi vào dữ liệu đang dùng của người chạy test. Trạng thái "đã có project"
  được đặt thẳng vào ``_current_id`` — đúng biến mà ba nút đọc.
* **Một cửa sổ cho cả module.** Dựng ``MainWindow`` cho từng bài làm cả bộ
  ``tests/ui`` chết giữa chừng (Qt đổ stack trace, không phải test nào fail),
  nên fixture ở đây là ``scope="module"`` và mỗi bài tự đặt trạng thái đầu vào
  của mình.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="cần PySide6 để dựng cửa sổ thật")

_PID_GIA = "project-test-khong-ghi-dia"


@pytest.fixture(scope="module")
def ws(qapp, tmp_path_factory):
    """Màn Workspace của một MainWindow thật, dùng chung cho cả module."""
    from cowork_local.presentation.shell.bootstrap import build_config, build_context
    from cowork_local.presentation.shell.main_window import MainWindow

    config_path = tmp_path_factory.mktemp("cfg") / "config.json"
    build_config(config_path)
    window = MainWindow(build_context(config_path))
    yield window.workspace
    window.close()


def _nap_project(qapp, ws, pid: str) -> None:
    """Đi đúng đường ``_load_current`` đi khi người dùng chọn một project.

    Cố ý KHÔNG gọi ``set_project_editable``: chính vì ``_load_current`` không
    gọi nó mà lỗi mới tồn tại. Gọi nó ở đây là bài test tự tay bật lại nút rồi
    khẳng định nút đang bật — nó sẽ xanh cả trên bản chưa sửa.

    ``_project_editable`` đặt thẳng về ``False`` vì cửa sổ dùng chung cho cả
    module: bài trước có thể đã để form ở chế độ sửa, mà nạp một project mới
    thì form luôn ở chế độ chỉ-xem.
    """
    ws.tabs.setCurrentIndex(ws._project_tab_idx)
    ws._project_editable = False
    ws._current_id = pid
    ws.project_selected.emit(pid)
    qapp.processEvents()


def _chua_co_project(qapp, ws) -> None:
    """Trạng thái chưa chọn project nào, đang ở sub-tab Project."""
    _nap_project(qapp, ws, "")


def _mo_mot_project(qapp, ws) -> None:
    """Trạng thái đang mở một project."""
    _nap_project(qapp, ws, _PID_GIA)


def test_chua_co_project_thi_nut_sua_mo(qapp, ws):
    """Chưa chọn project thì không có gì để sửa — đây là hành vi phải giữ."""
    _chua_co_project(qapp, ws)

    assert ws._edit_btn.isEnabled() is False
    assert ws._edit_btn.isHidden() is True


def test_da_co_project_thi_nut_sua_sang(qapp, ws):
    """Bài đỏ trước khi sửa: nút hiện ra nhưng vẫn mờ."""
    _mo_mot_project(qapp, ws)

    assert ws._edit_btn.isHidden() is False, "nút phải hiện khi đã có project"
    assert ws._edit_btn.isEnabled() is True, "nút phải bấm được khi đã có project"


def test_quay_lai_tab_project_thi_nut_van_sang(qapp, ws):
    """Đúng thao tác trong ảnh người dùng gửi: rời tab Project rồi quay lại."""
    if ws.tabs.count() < 2:
        pytest.skip("bản dựng này chỉ có một sub-tab, không đi vòng được")
    _mo_mot_project(qapp, ws)

    ws.tabs.setCurrentIndex(1 if ws._project_tab_idx == 0 else 0)
    qapp.processEvents()
    ws.tabs.setCurrentIndex(ws._project_tab_idx)
    qapp.processEvents()

    assert ws._edit_btn.isHidden() is False
    assert ws._edit_btn.isEnabled() is True


def test_dang_sua_thi_nut_sua_mo_lai_va_nut_luu_sang(qapp, ws):
    """Chống sửa quá tay: "Sửa project" chỉ sáng khi CHƯA ở chế độ sửa."""
    _mo_mot_project(qapp, ws)
    ws.set_project_editable(True)
    qapp.processEvents()

    assert ws._edit_btn.isEnabled() is False
    assert ws._save_btn.isEnabled() is True
    assert ws._browse_btn.isEnabled() is True


def test_bo_chon_project_thi_nut_sua_mo_lai(qapp, ws):
    """Xoá project đang mở đưa ``_current_id`` về rỗng — nút phải mờ lại."""
    _mo_mot_project(qapp, ws)
    ws._current_id = ""
    ws.project_selected.emit("")
    qapp.processEvents()

    assert ws._edit_btn.isEnabled() is False
    assert ws._edit_btn.isHidden() is True
