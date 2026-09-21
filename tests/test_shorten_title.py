"""Tiêu đề hội thoại không được cắt vào giữa một từ.

Triệu chứng người dùng báo: thanh tiêu đề màn Cowork hiện

    Đọc các tệp trong thư mục của project này và tóm tắt từng tệ…

Câu gốc dài 61 ký tự, mốc cắt cứng ở 60 rơi đúng vào giữa chữ "tệp" và bỏ mất
đúng một chữ cái. Người đọc thấy "tệ…" chứ không thấy "tệp", nên nó đọc ra như
lỗi gõ chứ không như một câu bị rút gọn.

``shorten_title`` viết nốt từ đang dở thay vì cắt ngang nó, và chỉ thêm dấu ba
chấm khi thật sự có chữ bị bỏ đi.
"""
from __future__ import annotations

import pytest

from cowork_local.core.history import (
    TITLE_MAX_CHARS, _TITLE_SLACK, derive_title, shorten_title,
)

#: Đúng câu trong ảnh người dùng gửi — 61 ký tự, vượt giới hạn đúng 1.
CAU_TRONG_ANH = "Đọc các tệp trong thư mục của project này và tóm tắt từng tệp"


def test_dung_ca_nguoi_dung_bao():
    """Bài đỏ trước khi sửa: cắt cứng cho ra "…từng tệ…"."""
    assert len(CAU_TRONG_ANH) == TITLE_MAX_CHARS + 1

    ket_qua = shorten_title(CAU_TRONG_ANH)

    assert ket_qua.endswith("tệp"), ket_qua
    assert "tệ…" not in ket_qua
    # Không chữ nào bị bỏ thì không được thêm dấu ba chấm — dấu đó là nói dối.
    assert ket_qua == CAU_TRONG_ANH


def test_ngan_hon_gioi_han_thi_giu_nguyen():
    assert shorten_title("Tiêu đề ngắn") == "Tiêu đề ngắn"


def test_dung_bang_gioi_han_thi_giu_nguyen():
    text = "x" * TITLE_MAX_CHARS
    assert shorten_title(text) == text


def test_moc_cat_roi_dung_giua_hai_tu_thi_cat_ngay_do():
    text = "x" * TITLE_MAX_CHARS + " còn nữa"

    assert shorten_title(text) == "x" * TITLE_MAX_CHARS + "…"


def test_viet_not_tu_roi_van_con_chu_phia_sau_thi_co_ba_cham():
    text = "x" * 57 + " abcdefgh ijk"

    ket_qua = shorten_title(text)

    assert ket_qua == "x" * 57 + " abcdefgh…"


def test_tu_dai_bat_thuong_thi_lui_ve_ranh_gioi_truoc():
    """Một đường dẫn hay URL dài không được kéo tiêu đề dài ra tuỳ ý."""
    text = "x" * 57 + " " + "y" * 40 + " z"

    ket_qua = shorten_title(text)

    assert ket_qua == "x" * 57 + "…"
    assert len(ket_qua) <= TITLE_MAX_CHARS + 1


def test_ca_tieu_de_chi_la_mot_tu_dai_thi_danh_cat_cung():
    """Không còn ranh giới từ nào để bám — cắt cứng là lối ra duy nhất."""
    text = "y" * 100

    assert shorten_title(text) == "y" * TITLE_MAX_CHARS + "…"


def test_khong_bao_gio_vuot_qua_gioi_han_cong_slack():
    text = "x" * 55 + " " + "y" * 11 + " phần đuôi còn dài nữa"

    assert len(shorten_title(text)) <= TITLE_MAX_CHARS + _TITLE_SLACK + 1


@pytest.mark.parametrize("text", [
    CAU_TRONG_ANH,
    "Phân tích bảng tính doanh thu quý bốn và lập báo cáo tổng hợp cho ban giám đốc",
    "Tóm tắt toàn bộ tài liệu kỹ thuật trong thư mục rồi xuất ra một tệp markdown",
    "a bb ccc dddd eeeee ffffff ggggggg hhhhhhhh iiiiiiiii jjjjjjjjjj kkkkkkkkkkk",
])
def test_ket_qua_luon_ket_thuc_o_ranh_gioi_tu(text):
    """Bất biến của cả hàm: phần chữ giữ lại phải là một tiền tố kết thúc đúng
    chỗ một từ kết thúc trong câu gốc — không bao giờ là nửa từ."""
    ket_qua = shorten_title(text)
    giu_lai = ket_qua[:-1] if ket_qua.endswith("…") else ket_qua

    assert text.startswith(giu_lai), "kết quả không còn là tiền tố của câu gốc"
    assert len(giu_lai) == len(text) or text[len(giu_lai)].isspace(), (
        f"cắt vào giữa từ: ...{giu_lai[-12:]!r} | còn lại {text[len(giu_lai):][:8]!r}"
    )


def test_derive_title_dung_cung_mot_luat():
    """Tiêu đề lưu vào lịch sử và tiêu đề trên thanh tiêu đề phải khớp nhau."""
    messages = [{"role": "user", "content": CAU_TRONG_ANH}]

    assert derive_title(messages) == shorten_title(CAU_TRONG_ANH)


def test_derive_title_van_gom_khoang_trang_thua():
    """Hành vi cũ phải giữ: xuống dòng và khoảng trắng thừa gộp về một dấu cách."""
    tin_nhan = """  Dòng một

  Dòng hai  """
    messages = [{"role": "user", "content": tin_nhan}]

    assert derive_title(messages) == "Dòng một Dòng hai"
