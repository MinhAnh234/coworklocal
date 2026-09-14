"""Sandbox Security Layer: bốn công tắc luôn sửa được, không còn khoá mật khẩu.

Trước đây nhóm này bị khoá: bốn công tắc dựng ra ở trạng thái ``setEnabled(False)``
và chỉ mở khi nhập đúng mật khẩu qua ``_sandbox_unlock()``. Bộ bài cũ ở file này
(SEC-20260907-01) chốt các đường KHÔNG được mở khoá — chúng mất đối tượng kiểm khi
tính năng khoá bị bỏ theo yêu cầu, nên được thay bằng các bài dưới đây.

Docstring của ``_sandbox_unlock()`` cũ đã tự nói rõ nó là gì: *"khoá phía giao diện
để chặn bấm nhầm vào một mục nhạy cảm, KHÔNG phải cơ chế bảo mật thật"*. Rào thật
nằm ở tầng sandbox lúc chạy lệnh, không ở hộp thoại Cài đặt.

Hai nhóm bài:

* **hành vi mới** — mở hộp thoại là bật/tắt được ngay, không qua bước nào;
* **guardrail** — quét mã nguồn để lần sau không ai lặng lẽ khoá lại.
"""
from __future__ import annotations

from pathlib import Path

import pytest

# Fake ctx dùng chung với đặc tả SettingsDialog: nó đã là "đủ cho SettingsDialog,
# không hơn". Dựng bản thứ hai ở đây chỉ tạo thêm một chỗ để lệch nhau.
from .test_settings_dialog_dac_ta import _Ctx


def _dialog():
    """SettingsDialog dựng đúng như bản cài thật."""
    from cowork_local.ui.settings_dialog import SettingsDialog
    return SettingsDialog(_Ctx())


_CONG_TAC = ("sandbox_confirm", "sandbox_block_network", "sec_enabled", "ai_check")


# ---- hành vi mới: sửa được ngay, không cần mật khẩu ----------------------

@pytest.mark.parametrize("ten", _CONG_TAC)
def test_cong_tac_sua_duoc_ngay_khi_mo_hop_thoai(qapp, ten):
    """Đây là chính yêu cầu: không còn bước nhập mật khẩu nào chắn ở giữa."""
    dlg = _dialog()

    assert getattr(dlg, ten).isEnabled() is True, f"{ten} vẫn bị khoá"


@pytest.mark.parametrize("ten", _CONG_TAC)
def test_bat_tat_duoc_va_luu_dung_gia_tri(qapp, ten):
    """Bật/tắt phải ăn vào widget — khoá cũ chặn đúng ở bước này."""
    dlg = _dialog()
    w = getattr(dlg, ten)

    truoc = w.isChecked()
    w.setChecked(not truoc)
    assert w.isChecked() is (not truoc)
    w.setChecked(truoc)
    assert w.isChecked() is truoc


def test_khong_con_widget_mat_khau_nao(qapp):
    """Ô nhập, nút Mở khoá và nhãn "Đang khoá" phải biến mất khỏi hộp thoại."""
    dlg = _dialog()

    for ten in ("sandbox_pw_edit", "sandbox_unlock_btn", "sandbox_locked_status",
                "sandbox_pw_label"):
        assert not hasattr(dlg, ten), f"{ten} vẫn còn trên hộp thoại"


def test_khong_con_duong_mo_khoa_trong_ma(qapp):
    """Hàm mở khoá và cờ trạng thái khoá không còn tồn tại."""
    import cowork_local.ui.settings_dialog as mod

    dlg = _dialog()
    assert not hasattr(dlg, "_sandbox_unlock")
    assert not hasattr(dlg, "_sandbox_unlocked")
    assert not hasattr(dlg, "_sandbox_widgets")
    assert not hasattr(mod, "_sandbox_password_matches")


# ---- guardrail: không ai khoá lại mà không sửa bài test này --------------

def test_ma_nguon_khong_con_khoa_nhom_sandbox():
    """Chặn cả lớp lỗi: lần sau ai thêm lại ``setEnabled(False)`` cho nhóm này
    thì bài này đỏ ngay, không đợi có người mở app mới thấy."""
    src = (Path(__file__).resolve().parents[2]
           / "ui" / "settings_dialog.py").read_text(encoding="utf-8")
    code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))

    for dau_hieu in ("_sandbox_unlock", "_sandbox_widgets", "_sandbox_unlocked",
                     "sandbox_pw"):
        assert dau_hieu not in code, f"khoá sandbox đã quay lại: {dau_hieu}"


def test_phep_quet_thuc_su_doc_duoc_file():
    """Lưới an toàn: đổi tên file làm bài trên quét rỗng mà vẫn xanh."""
    src = (Path(__file__).resolve().parents[2]
           / "ui" / "settings_dialog.py").read_text(encoding="utf-8")

    assert "class SettingsDialog" in src
    assert len(src) > 2000, f"chỉ đọc được {len(src)} ký tự — đường dẫn đã hỏng"
