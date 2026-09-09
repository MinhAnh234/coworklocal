"""Màn giới thiệu của khung chat khi hội thoại còn rỗng.

Bấm "Cuộc trò chuyện mới" trước đây để lại một khung trắng: không có gì nói
người dùng đang làm trong project nào, thư mục có bao nhiêu tệp, hay bắt đầu từ
đâu. Đây là trạng thái RỖNG — trạng thái duy nhất người dùng nhìn thấy trước khi
họ gõ chữ đầu tiên.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="cần PySide6 để dựng widget thật")


@pytest.fixture
def welcome(qapp):
    from cowork_local.presentation.chat.chat_welcome import ChatWelcome
    w = ChatWelcome()
    yield w
    w.deleteLater()


# ---- bốn thẻ gợi ý -------------------------------------------------------

def test_co_dung_bon_the(welcome):
    assert len(welcome.cards) == 4


def test_bam_the_thi_phat_cau_goi_y(welcome):
    nhan = []
    welcome.suggestion_picked.connect(nhan.append)

    welcome.cards[0].click()

    assert len(nhan) == 1
    assert len(nhan[0]) > 20, "câu gợi ý phải là một câu thật, không phải nhãn thẻ"


def test_bon_the_cho_bon_cau_khac_nhau(welcome):
    nhan = []
    welcome.suggestion_picked.connect(nhan.append)

    for card in welcome.cards:
        card.click()

    assert len(set(nhan)) == 4


def test_the_co_tieu_de_va_mo_ta(welcome):
    for card in welcome.cards:
        assert card.title_label.text().strip()
        assert card.sub_label.text().strip()
        # Nhãn của chính QPushButton phải rỗng — chữ do hai QLabel bên trong vẽ,
        # đặt cả hai chỗ sẽ in đè lên nhau.
        assert card.text() == ""


def test_the_khong_bi_bop_thanh_khung_rong(qapp, welcome):
    """Regression: bốn thẻ hiện ra nhưng RỖNG — không chữ, không icon.

    ``QPushButton`` tự tính ``sizeHint``/``minimumSizeHint`` từ text và icon
    CỦA CHÍNH NÓ và bỏ qua layout con. Thẻ để cả hai thứ đó rỗng có chủ ý (chữ
    do hai QLabel bên trong vẽ), nên nút báo 54x15 trong khi layout con đòi
    258x48 — hai QLabel và ô icon được chia 0px chiều cao và không có gì được
    vẽ ra. Đặt ``text()`` không rỗng thì chữ in đè, nên hai override là đường
    duy nhất.
    """
    welcome.resize(900, 700)
    welcome.show()
    qapp.processEvents()
    try:
        for card in welcome.cards:
            can = card.layout().minimumSize()
            assert card.width() >= can.width(), (
                f"thẻ rộng {card.width()}px, layout con cần {can.width()}px")
            assert card.height() >= can.height(), (
                f"thẻ cao {card.height()}px, layout con cần {can.height()}px")
            assert card.title_label.height() > 0, "tiêu đề bị chia 0px chiều cao"
            assert card.sub_label.height() > 0, "dòng mô tả bị chia 0px chiều cao"
            assert card._icon.height() > 0, "ô icon bị chia 0px chiều cao"
    finally:
        welcome.hide()


# ---- dòng bối cảnh: KHÔNG BIẾT khác 0 ------------------------------------

def test_khong_biet_so_tep_thi_bo_manh_do(welcome):
    """Hiện "0 tệp" khi người dùng vừa thấy có tệp trong thư mục còn tệ hơn là
    bỏ mảnh đó khỏi dòng meta."""
    welcome.refresh(user_name="local", project="p", files=-1)

    meta = welcome.meta_label.text()
    assert "p" in meta
    assert "0" not in meta


def test_khong_co_tep_that_thi_van_hien_so_0(welcome):
    """Khác với KHÔNG BIẾT: thư mục rỗng thật thì nói rõ là rỗng."""
    welcome.refresh(user_name="local", project="p", files=0)

    assert "0" in welcome.meta_label.text()


def test_khong_co_gi_de_noi_thi_an_dong_meta(welcome):
    welcome.refresh()

    assert welcome.meta_label.isHidden() is True


def test_co_ten_thi_chao_ten(welcome):
    welcome.refresh(user_name="Mynt4")

    assert "Mynt4" in welcome.greeting_label.text()


def test_khong_co_ten_thi_khong_chao_rong(welcome):
    """Không được ra "Chào  — bắt đầu từ đâu?" với một khoảng trống."""
    from cowork_local.i18n import tr

    welcome.refresh(user_name="")

    assert welcome.greeting_label.text() == tr("welcome.greeting_anon")


# ---- i18n ----------------------------------------------------------------

@pytest.mark.parametrize("key", [
    "welcome.greeting", "welcome.greeting_anon", "welcome.meta_project",
    "welcome.meta_files",
    "welcome.card_docs", "welcome.card_docs_sub", "welcome.prompt_docs",
    "welcome.card_data", "welcome.card_data_sub", "welcome.prompt_data",
    "welcome.card_schedule", "welcome.card_schedule_sub", "welcome.prompt_schedule",
    "welcome.card_graph", "welcome.card_graph_sub", "welcome.prompt_graph",
])
def test_key_co_du_ba_ngon_ngu(key):
    from cowork_local import i18n

    for lang in ("en", "ja", "vi"):
        assert i18n.STRINGS[key].get(lang), f"{key} thiếu {lang}"


def test_doi_ngon_ngu_thi_the_doi_theo(welcome):
    from cowork_local import i18n

    truoc = i18n.get_language()
    try:
        i18n.set_language("vi")
        welcome.refresh(user_name="x", project="p")
        vi = welcome.cards[0].title_label.text()
        i18n.set_language("ja")
        ja = welcome.cards[0].title_label.text()
    finally:
        i18n.set_language(truoc)

    assert vi != ja, "thẻ không được áp lại khi đổi ngôn ngữ"


# ---- màu lấy từ theme ----------------------------------------------------

def test_duoc_style_bang_token_trong_theme():
    """Guardrail G4: ngoài theme/ không file nào được đặt tên một màu."""
    from pathlib import Path
    from cowork_local.theme.qss import _TEMPLATE

    for rule in ("QWidget#chatWelcome", "QPushButton#welcomeCard",
                 "QLabel#welcomeGreeting"):
        assert rule in _TEMPLATE.template, f"{rule} chưa được style trong theme"
    src = (Path(__file__).resolve().parents[2]
           / "presentation" / "chat" / "chat_welcome.py").read_text(encoding="utf-8")
    assert "setStyleSheet" not in src
