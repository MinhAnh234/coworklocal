"""AtomicJsonFile — R02-T01. Test tiêm lỗi, đúng như cột nghiệm thu của plan.md.

Cách kiểm: cắt ngang giữa lúc ghi rồi khẳng định file cũ **còn nguyên**. Nếu
chỉ test "ghi rồi đọc lại thấy đúng" thì `path.write_text()` cũ cũng qua — mà
đó chính là thứ ta đang thay.
"""
from __future__ import annotations

import json
import os

import pytest

from cowork_local.infrastructure.persistence.json.atomic_json_file import AtomicJsonFile


def test_ghi_roi_doc_lai(tmp_path):
    f = AtomicJsonFile(tmp_path / "cau_hinh.json")
    f.write({"theme": "dark", "ngôn ngữ": "vi"})
    assert f.read() == {"theme": "dark", "ngôn ngữ": "vi"}


def test_chua_co_file_thi_tra_mac_dinh(tmp_path):
    f = AtomicJsonFile(tmp_path / "chua-ton-tai.json")
    assert f.read(default={"theme": "dark"}) == {"theme": "dark"}
    assert f.exists() is False


def test_chet_giua_luc_ghi_thi_file_cu_con_nguyen(tmp_path, monkeypatch):
    """Lõi của R02-T01.

    Giả lập mất điện đúng lúc: cho ``os.replace`` ném lỗi. Đây là bước cuối
    cùng, tức là dữ liệu mới đã nằm trong file tạm rồi — nếu cài đặt sai theo
    kiểu ghi đè thẳng, file đích lúc này đã hỏng.
    """
    path = tmp_path / "cau_hinh.json"
    f = AtomicJsonFile(path)
    f.write({"phiên bản": 1, "quan trọng": "đừng mất"})

    def no_dien(*args, **kwargs):
        raise OSError("mô phỏng mất điện")

    monkeypatch.setattr(os, "replace", no_dien)
    with pytest.raises(OSError):
        f.write({"phiên bản": 2})

    # bản cũ phải còn y nguyên
    assert f.read() == {"phiên bản": 1, "quan trọng": "đừng mất"}


def test_khong_de_lai_rac_tmp_khi_ghi_hong(tmp_path, monkeypatch):
    path = tmp_path / "cau_hinh.json"
    f = AtomicJsonFile(path)
    f.write({"a": 1})

    monkeypatch.setattr(os, "replace", lambda *a, **k: (_ for _ in ()).throw(OSError("x")))
    with pytest.raises(OSError):
        f.write({"a": 2})

    con_lai = [p.name for p in tmp_path.iterdir()]
    assert con_lai == ["cau_hinh.json"], f"còn rác: {con_lai}"


def test_file_hong_thi_cach_ly_va_tra_mac_dinh(tmp_path):
    """Hỏng cấu hình không được chặn khởi động — giữ đúng hành vi config.py
    hiện tại, nhưng thêm phần giữ lại bản hỏng để còn cứu."""
    path = tmp_path / "cau_hinh.json"
    path.write_text("{ đây không phải json", encoding="utf-8")
    f = AtomicJsonFile(path)

    assert f.read(default={"theme": "dark"}) == {"theme": "dark"}
    assert not path.exists(), "file hỏng phải được dời đi"
    bad = list(tmp_path.glob("*.bad-*"))
    assert len(bad) == 1, "phải giữ lại bản hỏng để cứu tay"
    assert "đây không phải json" in bad[0].read_text(encoding="utf-8")


def test_ghi_de_nhieu_lan_van_dung(tmp_path):
    f = AtomicJsonFile(tmp_path / "dem.json")
    for i in range(20):
        f.write({"lần": i})
    assert f.read() == {"lần": 19}
    assert list(tmp_path.glob("*.tmp")) == []


def test_giu_nguyen_tieng_viet_khong_escape(tmp_path):
    """config.py hiện dùng ensure_ascii=False — giữ nguyên để file đọc được
    bằng mắt và git diff không thành một đống \\uXXXX."""
    path = tmp_path / "vi.json"
    AtomicJsonFile(path).write({"tên": "Nguyễn Văn Đức"})
    raw = path.read_text(encoding="utf-8")
    assert "Nguyễn Văn Đức" in raw
    assert "\\u" not in raw


def test_tao_thu_muc_cha_neu_chua_co(tmp_path):
    f = AtomicJsonFile(tmp_path / "sâu" / "hơn" / "nữa" / "c.json")
    f.write({"ok": True})
    assert f.read() == {"ok": True}


def test_json_ghi_ra_doc_duoc_bang_thu_vien_chuan(tmp_path):
    path = tmp_path / "c.json"
    AtomicJsonFile(path).write({"n": [1, 2, {"m": None}]})
    assert json.loads(path.read_text(encoding="utf-8")) == {"n": [1, 2, {"m": None}]}


# ---- Windows: os.replace bị Defender/Indexer chặn tạm thời -----------------

def test_thu_lai_khi_windows_chan_tam_thoi(tmp_path, monkeypatch):
    """Hỏng 2 lần đầu rồi thành công — phải ghi được, không ném lỗi.

    Đây là lỗi thật bắt được ngày 25/08: chạy vòng 20 lần ghi thì cứ 7 lượt
    lại có 1 lượt văng ``PermissionError: [WinError 5]`` ở ``os.replace``.
    """
    that = os.replace
    con_hong = [2]

    def replace_do_dong(src, dst):
        if con_hong[0]:
            con_hong[0] -= 1
            raise PermissionError(5, "Access is denied")
        return that(src, dst)

    monkeypatch.setattr(os, "replace", replace_do_dong)
    AtomicJsonFile(tmp_path / "a.json").write({"x": 1})

    assert con_hong[0] == 0, "phải thật sự có thử lại, không phải may mà qua"
    assert json.loads((tmp_path / "a.json").read_text(encoding="utf-8")) == {"x": 1}
    assert list(tmp_path.glob("*.tmp")) == []


def test_hong_that_thi_van_nem_loi_va_khong_de_lai_rac(tmp_path, monkeypatch):
    """Thử lại không được phép nuốt lỗi quyền thật — hết lượt là ném."""
    def luon_hong(src, dst):
        raise PermissionError(5, "Access is denied")

    monkeypatch.setattr(os, "replace", luon_hong)
    with pytest.raises(PermissionError):
        AtomicJsonFile(tmp_path / "b.json").write({"x": 1})

    assert list(tmp_path.glob("*.tmp")) == [], "phải dọn file tạm"
