"""Thanh menu trái không được kéo mất.

Kéo thanh chia sang trái hết cỡ thì thanh menu biến mất hẳn, và khi đã mất thì
không còn gì đủ rộng để nhận ra, nói gì tới bắt lại mà kéo ra.

Nguyên nhân: ``_nav_wrap.setMinimumWidth(132)`` chỉ chi phối việc BỐ TRÍ, không
chi phối thao tác kéo. ``QSplitter`` mặc định cho phép người dùng kéo một ngăn
vượt qua chính minimum của nó rồi đóng sập về 0 — phải tắt bằng
``setChildrenCollapsible(False)``.

Thu gọn là việc của nút MENU, và nó dừng ở 54px chứ không về 0.
"""
from __future__ import annotations

import pytest

from cowork_local.presentation.shell.rail_metrics import (
    _NAV_COLLAPSED_WIDTH, _NAV_MIN_WIDTH,
)

pytest.importorskip("PySide6", reason="cần PySide6 để dựng cửa sổ thật")


@pytest.fixture(scope="module")
def window(qapp, tmp_path_factory):
    from cowork_local.presentation.shell.bootstrap import build_config, build_context
    from cowork_local.presentation.shell.main_window import MainWindow

    config_path = tmp_path_factory.mktemp("cfg") / "config.json"
    build_config(config_path)
    win = MainWindow(build_context(config_path))
    win.resize(1280, 800)
    yield win
    win.close()


def test_splitter_khong_cho_dong_sap_ngan_nao(window):
    """Chốt trực tiếp thứ đã thiếu.

    Cố ý KHÔNG khẳng định ``isCollapsible(0)``: hàm đó trả về cờ đặt RIÊNG cho
    từng ngăn, và nó vẫn là ``True`` kể cả khi chính sách chung đã tắt — nên
    khẳng định vào đó là chốt một chi tiết cài đặt của Qt, không phải hành vi ta
    cần. Ba bài dưới kiểm bằng thao tác kéo thật.
    """
    assert window.split.childrenCollapsible() is False


def test_thanh_menu_co_san_min_width(window):
    """Không có sàn thì tắt collapsible cũng chẳng chặn được gì."""
    assert window._nav_wrap.minimumWidth() == _NAV_MIN_WIDTH


def test_keo_het_co_sang_trai_van_khong_mat_thanh_menu(window):
    """Kéo thanh chia về 0 — Qt phải kẹp lại ở sàn, không cho về 0."""
    window.split.setSizes([0, 1280])

    assert window.split.sizes()[0] >= _NAV_MIN_WIDTH, (
        f"thanh menu bị thu về {window.split.sizes()[0]}px")


def test_keo_qua_da_van_bi_kep_lai(window):
    """Giá trị âm/cực nhỏ cũng phải bị kẹp, không chỉ đúng số 0."""
    window.split.setSizes([-500, 1780])

    assert window.split.sizes()[0] >= _NAV_MIN_WIDTH


def test_nut_menu_van_thu_gon_duoc_ve_54(window):
    """Bản vá không được chặn mất đường thu gọn hợp lệ.

    Nút MENU thu về ``_NAV_COLLAPSED_WIDTH`` (54px) bằng cách hạ CHÍNH minimum
    của widget, nên ``setChildrenCollapsible(False)`` không cản — nó chỉ cấm đi
    xuống dưới minimum đang có.
    """
    assert window._nav_collapsed is False
    window._toggle_nav()
    try:
        assert window._nav_collapsed is True
        assert window._nav_wrap.minimumWidth() == _NAV_COLLAPSED_WIDTH
        window.split.setSizes([0, 1280])
        assert window.split.sizes()[0] >= _NAV_COLLAPSED_WIDTH
    finally:
        window._toggle_nav()

    assert window._nav_collapsed is False
    assert window._nav_wrap.minimumWidth() == _NAV_MIN_WIDTH
