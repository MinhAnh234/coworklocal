"""Mục "Giới thiệu" trong Cài đặt, và dòng phiên bản ở góc dưới phải.

Dòng "Made by QuanDH14" từng là widget thường trực ở góc dưới phải, rồi chuyển
hẳn vào Cài đặt ▸ Giới thiệu. Nay chỗ đó mang MỘT thông tin khác: số phiên bản —
người dùng muốn tra được ngay mà không phải mở Cài đặt.

Điểm phải chốt là **một nguồn duy nhất**: tiêu đề cửa sổ, tab Giới thiệu và góc
dưới phải đều đọc ``cowork_local.__version__``. Ghi cứng con số ở một trong ba
chỗ thì lần nâng phiên bản sau sẽ để lại một chỗ nói sai.
"""
from __future__ import annotations

import pytest

from .test_settings_dialog_dac_ta import _Ctx


@pytest.fixture
def dialog(qapp):
    from cowork_local.ui.settings_dialog import SettingsDialog
    dlg = SettingsDialog(_Ctx())
    yield dlg
    dlg.deleteLater()


# ---- đầu MỚI: mục Giới thiệu trong Cài đặt -------------------------------

def test_cai_dat_co_muc_gioi_thieu(dialog):
    from cowork_local.i18n import tr

    labels = [dialog.section_list.item(i).text()
              for i in range(dialog.section_list.count())]
    assert tr("settings.group.about") in labels


def test_muc_gioi_thieu_dung_cuoi(dialog):
    """Nó không có gì để đổi, nên đặt trước các mục thao tác được là đẩy chúng
    xuống mà không được gì."""
    from cowork_local.i18n import tr

    last = dialog.section_list.item(dialog.section_list.count() - 1).text()
    assert last == tr("settings.group.about")


def test_muc_gioi_thieu_hien_dong_phien_ban(dialog):
    from cowork_local import __version__
    from cowork_local.i18n import tr

    text = dialog._about_page.version_label.text()
    assert text == tr("app.version", v=__version__)
    assert __version__ in text


def test_muc_gioi_thieu_hien_ten_va_phien_ban(dialog):
    from cowork_local import DISPLAY_NAME, __version__

    text = dialog._about_page.app_label.text()
    assert DISPLAY_NAME in text
    assert __version__ in text


# ---- góc dưới phải: đúng một dòng, và là dòng phiên bản ------------------

def test_goc_duoi_phai_hien_phien_ban_tu_cung_mot_nguon():
    """Thanh trạng thái mang ĐÚNG một widget thường trực, là dòng phiên bản.

    Kiểm trên mã nguồn thay vì dựng ``MainWindow`` — dựng cửa sổ thật mất ~35
    giây cho một khẳng định mà đọc file trả lời được ngay.
    """
    from pathlib import Path

    src = (Path(__file__).resolve().parents[2]
           / "presentation" / "shell" / "main_window.py").read_text(encoding="utf-8")

    assert "_credit" not in src, "widget ghi công tác giả đã chuyển vào Cài đặt"
    assert src.count("addPermanentWidget") == 1, (
        "góc dưới phải chỉ được mang MỘT widget thường trực — nó chiếm một góc "
        "màn hình trên MỌI màn hình, suốt cả phiên làm việc")
    assert 'tr("app.version", v=__version__)' in src, (
        "dòng phiên bản phải đọc __version__ như tiêu đề cửa sổ và tab Giới "
        "thiệu; ghi cứng con số ở đây thì lần nâng phiên bản sau sẽ nói sai")
    assert "setSizeGripEnabled(False)" in src, (
        "size grip vẽ một vệt ngay bên phải dòng phiên bản — góc đó chỉ được "
        "mang mỗi con số; cửa sổ vẫn kéo giãn được từ các cạnh")
