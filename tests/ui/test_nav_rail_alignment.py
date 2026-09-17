"""Ba hàng cuối thanh rail phải thẳng hàng: Dashboard, Giám sát, Cài đặt.

Dashboard và Giám sát là hàng của ``QTreeWidget`` (``#navrailBottom``), còn Cài
đặt là một ``QPushButton`` tự dựng lấy icon + chữ trong ``top_bar.py``. Hai cách
vẽ khác nhau nên không có gì tự giữ cho chúng thẳng hàng — phải chốt bằng test.

Lần lệch gần nhất: ``srow.setSpacing(_NAV_ROW_GAP + 4)`` (=10) cộng với 10px lề
trái và hộp icon 22px đặt chữ "Cài đặt" ở x=42, trong khi delegate của cây đặt
chữ ở x=35 — thụt phải 7px, thấy rõ bằng mắt trên thanh rail.

Cách đo: render thanh rail ra ảnh rồi tìm cột mực đầu tiên, vì đó đúng là thứ
người dùng nhìn thấy. Trước khi đo, ba hàng được ép về **cùng một icon và cùng
một chữ** — chữ khác nhau thì phần nhô trái của glyph đầu tiên ("D" so với "G"
so với "C") đã lệch nhau vài pixel, và bài test sẽ đo hình dáng chữ chứ không
đo bố cục.
"""
from __future__ import annotations

import os

import pytest

pytest.importorskip("PySide6", reason="cần PySide6 để dựng cửa sổ thật")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

#: Bỏ qua cột mực nằm sát mép trái: hàng đang được chọn có thêm vạch
#: ``border-left: 2px solid $accent`` (theme/qss.py), không phải icon.
_BO_QUA_MEP_TRAI = 5


@pytest.fixture(scope="module")
def window(qapp, tmp_path_factory):
    """Cửa sổ thật, có nạp stylesheet đúng như ``app.py`` làm.

    Không nạp thì ``QTreeWidget::item { padding: 6px 10px }`` không áp, hàng của
    cây thụt về 0 còn nút Cài đặt vẫn giữ lề 10px của layout — bài test sẽ đỏ vì
    thiếu theme chứ không vì lỗi bố cục.
    """
    from cowork_local.presentation.shell.bootstrap import build_config, build_context
    from cowork_local.presentation.shell.main_window import MainWindow
    from cowork_local.theme import set_active_theme, stylesheet

    config_path = tmp_path_factory.mktemp("cfg") / "config.json"
    build_config(config_path)
    ctx = build_context(config_path)
    css_cu = qapp.styleSheet()
    set_active_theme(ctx.config.theme)
    qapp.setStyleSheet(stylesheet(ctx.config.theme))
    win = MainWindow(ctx)
    win.resize(1280, 800)
    win.show()
    for _ in range(3):
        qapp.processEvents()
    yield win
    win.close()
    qapp.setStyleSheet(css_cu)


def _cum_muc(img, y0: int, y1: int):
    """Các cụm cột có mực trong dải ``[y0, y1)``, dạng ``[(x_đầu, x_cuối), ...]``.

    Màu nền lấy ở cột sát mép phải cùng dòng y, nên hàng đang được tô nền chọn
    vẫn so sánh đúng.
    """
    w = img.width()
    co_muc = [any(img.pixel(x, y) != img.pixel(w - 3, y) for y in range(y0, y1))
              for x in range(w)]
    cum, dau = [], None
    for x, c in enumerate(co_muc):
        if c and dau is None:
            dau = x
        elif not c and dau is not None:
            if x - dau >= 2:
                cum.append((dau, x - 1))
            dau = None
    if dau is not None:
        cum.append((dau, w - 1))
    return [c for c in cum if c[0] >= _BO_QUA_MEP_TRAI]


def _ep_ba_hang_ve_cung_hinh(window):
    """Cho ba hàng cùng icon và cùng chữ, để chỉ còn bố cục là khác biệt."""
    from cowork_local.ui.icons import icon as _icon

    for i in range(2):
        it = window.nav_bottom.topLevelItem(i)
        it.setIcon(0, _icon("gear"))
        it.setText(0, "M")
    window._nav_settings_icon.setPixmap(_icon("gear").pixmap(16, 16))
    window._nav_settings_text.setText("M")


def _vi_tri_ba_hang(qapp, window):
    """``{tên hàng: (x_icon, x_chữ)}`` đo từ ảnh render của thanh rail."""
    from PySide6.QtCore import QPoint

    _ep_ba_hang_ve_cung_hinh(window)
    for _ in range(3):
        qapp.processEvents()
    ref = window._nav_wrap
    img = ref.grab().toImage()

    ket = {}
    for i, ten in ((0, "Dashboard"), (1, "Giám sát")):
        it = window.nav_bottom.topLevelItem(i)
        r = window.nav_bottom.visualItemRect(it)
        y = window.nav_bottom.viewport().mapTo(ref, QPoint(0, r.y())).y()
        cum = _cum_muc(img, y + 4, y + r.height() - 4)
        assert len(cum) >= 2, f"{ten}: không tìm thấy đủ icon và chữ để đo"
        ket[ten] = (cum[0][0], cum[1][0])

    btn = window._nav_settings_btn
    y = btn.mapTo(ref, QPoint(0, 0)).y()
    cum = _cum_muc(img, y + 4, y + btn.height() - 4)
    assert len(cum) >= 2, "Cài đặt: không tìm thấy đủ icon và chữ để đo"
    ket["Cài đặt"] = (cum[0][0], cum[1][0])
    return ket


def test_icon_ba_hang_thang_hang(qapp, window):
    """Icon của ba hàng phải bắt đầu ở cùng một cột."""
    vi_tri = _vi_tri_ba_hang(qapp, window)
    x = {ten: v[0] for ten, v in vi_tri.items()}
    assert len(set(x.values())) == 1, f"icon lệch nhau: {x}"


def test_chu_ba_hang_thang_hang(qapp, window):
    """Chữ của ba hàng phải bắt đầu ở cùng một cột.

    Đây là bài đỏ trước khi sửa: Cài đặt ở 42, hai hàng kia ở 35.
    """
    vi_tri = _vi_tri_ba_hang(qapp, window)
    x = {ten: v[1] for ten, v in vi_tri.items()}
    assert len(set(x.values())) == 1, f"chữ lệch nhau: {x}"
