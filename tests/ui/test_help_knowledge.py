"""Trợ lý Hỗ trợ phải trả lời từ sổ tay, không phải từ trí nhớ về phần mềm khác.

Người dùng thật đã được trợ lý hướng dẫn vào "Dashboard → Add Project" và
"Settings → Project Settings → New Project". Cả hai đều không tồn tại. Prompt cũ
chỉ liệt kê TÊN các màn hình, nên model không có cách nào biết trên mỗi màn có
gì và nó lấp khoảng trống bằng thứ nghe hợp lý.

Nhóm bài quan trọng nhất ở đây là nhóm CHỐNG TRÔI: sổ tay viết tay sẽ lỗi thời
khi ai đó đổi UI, và một sổ tay sai còn tệ hơn không có sổ tay.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from cowork_local.core import help_knowledge

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def guide() -> str:
    return help_knowledge.app_guide()


# ---- sổ tay có thật và được nạp ------------------------------------------

def test_so_tay_ton_tai_va_doc_duoc(guide):
    assert guide, "docs/help/app_guide.md rỗng hoặc không đọc được"
    assert len(guide) > 1500, "sổ tay quá ngắn để trả lời được câu hỏi thật"


def test_thieu_so_tay_thi_khong_lam_hong_tro_ly(monkeypatch):
    """Trợ lý thiếu sổ tay chỉ kém hữu ích đi, không được ném lỗi làm hỏng khung chat."""
    monkeypatch.setattr(help_knowledge, "_GUIDE", Path("khong-ton-tai.md"))
    help_knowledge.app_guide.cache_clear()
    try:
        assert help_knowledge.app_guide() == ""
        assert help_knowledge.build_prompt("vai tro").strip() == "vai tro"
    finally:
        help_knowledge.app_guide.cache_clear()


# ---- CHỐNG TRÔI: sổ tay phải khớp màn hình thật ---------------------------

def _nav_screens() -> set[str]:
    """Tên các màn hình thật, trích tự động từ docs/screens/manifest.json."""
    data = json.loads((REPO / "docs" / "screens" / "manifest.json").read_text(encoding="utf-8"))
    return {e["nav"].strip() for e in data if e.get("nav", "").strip()}


def test_so_tay_nhac_du_moi_man_hinh_that(guide):
    """Thiếu một màn là trợ lý sẽ không biết gì về màn đó."""
    thieu = [s for s in _nav_screens() if s.lower() not in guide.lower()]
    assert not thieu, f"sổ tay chưa nhắc tới: {sorted(thieu)}"


@pytest.mark.parametrize("bia", [
    "Add Project",              # trợ lý từng bịa ra nút này ở Dashboard
    "Project Settings",         # ...và mục này trong Cài đặt
    "New Project",              # tên tiếng Anh của nút không tồn tại
])
def test_so_tay_khong_gioi_thieu_thu_khong_co(guide, bia):
    """Sổ tay chỉ được PHỦ ĐỊNH mấy tên này, không được dùng như hướng dẫn.

    Cho phép chúng xuất hiện trong mục "những chỗ hay hỏi" kèm chữ 'không có',
    vì nói thẳng "app không có nút đó" là đúng việc cần làm.
    """
    for dong in guide.splitlines():
        if bia.lower() in dong.lower():
            assert "không có" in dong.lower() or "⚠️" in dong, (
                f"dòng nhắc {bia!r} mà không phủ định: {dong.strip()!r}")


def test_so_tay_chi_dung_cho_tao_project(guide):
    """Câu hỏi hay nhất — và là câu trợ lý từng trả lời sai."""
    assert "Workspace ▸ Project" in guide
    assert "Project mới" in guide


# ---- ghép prompt ---------------------------------------------------------

def test_prompt_co_du_ba_phan(guide):
    prompt = help_knowledge.build_prompt(
        "VAI TRO", help_knowledge.screen_context("Workspace ▸ Project"))

    assert "VAI TRO" in prompt
    assert "SỔ TAY ỨNG DỤNG" in prompt
    assert "Workspace ▸ Project" in prompt


def test_luat_chong_bia_dung_SAU_so_tay(guide):
    """Luật phải là thứ cuối cùng model đọc về cách dùng sổ tay."""
    prompt = help_knowledge.build_prompt("VAI TRO")

    assert prompt.index("SỔ TAY ỨNG DỤNG") < prompt.index("LUẬT TRẢ LỜI")


def test_man_hinh_dang_mo_dung_cuoi_cung():
    """Nó đổi theo từng lượt hỏi nên đứng cuối, sát câu hỏi nhất."""
    prompt = help_knowledge.build_prompt(
        "VAI TRO", help_knowledge.screen_context("Monitoring"))

    assert prompt.index("LUẬT TRẢ LỜI") < prompt.index("MÀN HÌNH NGƯỜI DÙNG ĐANG MỞ")


def test_khong_biet_man_hinh_thi_khong_bia_ra_mot_cai():
    assert help_knowledge.screen_context("") == ""
    assert help_knowledge.screen_context("", []) == ""
    assert "MÀN HÌNH NGƯỜI DÙNG ĐANG MỞ" not in help_knowledge.build_prompt("VAI TRO")


# ---- danh sách nút đang hiện, đọc từ giao diện đang chạy -----------------

def test_liet_ke_dung_cac_nut_dang_hien():
    """Không có phần này thì "ở đây làm được gì" là câu model buộc phải đoán."""
    ctx = help_knowledge.screen_context("Workspace ▸ Project",
                                        ["Project mới", "Sửa project", "Lưu project"])

    assert "Project mới" in ctx
    assert "Sửa project" in ctx
    assert "CHÍNH XÁC" in ctx, "phải nói rõ đây là danh sách đầy đủ, không phải gợi ý"


def test_nhan_rong_va_trung_khong_lam_ban_prompt():
    ctx = help_knowledge.screen_context("X", ["  ", "", "Lưu", None])

    assert ctx.count("- ") == 1


def test_cat_bot_khi_qua_nhieu_nut():
    """Màn đông như Co4E có hàng chục nút; dồn hết vào chỉ làm loãng prompt."""
    ctx = help_knowledge.screen_context("Co4E", [f"nut-{i}" for i in range(200)])

    assert ctx.count("- ") == help_knowledge._MAX_ACTIONS


def test_chi_co_nut_ma_khong_biet_man_hinh_thi_van_dung_duoc():
    ctx = help_knowledge.screen_context("", ["Lưu"])

    assert "Lưu" in ctx


# ---- ví dụ few-shot chốt đúng lỗi đã xảy ra ------------------------------

def test_luat_co_vi_du_cau_tra_loi_sai_that(guide):
    """Nêu tên đúng thứ nó từng bịa thì hiệu quả hơn một luật chung chung."""
    prompt = help_knowledge.build_prompt("VAI TRO")

    assert "Add Project" in prompt
    assert "SAI:" in prompt and "ĐÚNG:" in prompt


def test_luat_day_cach_noi_khong_biet(guide):
    """Nói không biết là câu trả lời đúng, và phải có ví dụ cho nó."""
    prompt = help_knowledge.build_prompt("VAI TRO")

    assert "không chắc" in prompt


# ---- màn hình đang mở, lấy từ cửa sổ thật --------------------------------

def test_cua_so_bao_dung_ten_man_hinh_dang_mo(qapp, tmp_path):
    from cowork_local.presentation.shell.bootstrap import build_config, build_context
    from cowork_local.presentation.shell.main_window import MainWindow

    config_path = tmp_path / "config.json"
    build_config(config_path)
    win = MainWindow(build_context(config_path))
    try:
        nhan = win.current_screen_label()

        assert nhan, "cửa sổ không nói được nó đang mở màn nào"
        assert "▸" in nhan, f"màn Workspace phải kèm sub-tab, nhận được {nhan!r}"
        # Tên trong nhãn phải là tên THẬT, để trợ lý nhắc lại được cho người dùng
        assert nhan.split("▸")[-1].strip() in help_knowledge.app_guide()

        # Ngữ cảnh sống phải đi qua được toàn bộ đường: widget -> prompt
        ctx = win.help_context()
        assert nhan in ctx
        assert "VAI TRO" in help_knowledge.build_prompt("VAI TRO", ctx)
    finally:
        win.close()
