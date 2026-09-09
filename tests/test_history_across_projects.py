"""Lịch sử hội thoại nằm trong thư mục của TỪNG project, không nằm chung.

``WorkspaceTab._bind_project`` đặt ``config._project_history_dir`` thành
``<workspace của project>/.cowork_history`` mỗi lần người dùng chọn project khác.
Hệ quả: một lần gọi ``list_conversations()`` chỉ thấy hội thoại của project đang
mở — và gọi KHÔNG tham số thì không thấy cái nào cả, vì nó đọc ``HISTORY_DIR``
toàn cục.

Hai lỗi đã xảy ra vì đúng chuyện này:

* Khung "Tất cả project…" dựng đủ tiêu đề nhóm cho mọi project nhưng mọi nhóm
  trừ một đều rỗng.
* Mọi dòng project đều đếm "0 đoạn chat · 0 task" dù người dùng đã chat.

Test không chạm ``~/.cowork_local``: ``core/projects.py`` gắn ``PROJECTS_DIR``
vào thư mục dữ liệu THẬT, nên mọi thứ ở đây dùng ``tmp_path`` và fake.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cowork_local.core.history import (
    list_conversations, list_conversations_by_project,
)


def _viet_hoi_thoai(directory: Path, session_id: str, title: str,
                    project_id: str = "", mtime: float | None = None) -> Path:
    """Ghi một file hội thoại tối thiểu mà ``list_conversations`` đọc được."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{session_id}.json"
    path.write_text(json.dumps({
        "kind": "cowork",
        "title": title,
        "created": "2026-09-07T10:00:00",
        "session_id": session_id,
        "project_id": project_id,
        "messages": [{"role": "user", "content": title}],
    }), encoding="utf-8")
    if mtime is not None:
        import os
        os.utime(path, (mtime, mtime))
    return path


@pytest.fixture
def hai_project(tmp_path):
    """Hai project, mỗi cái một đoạn chat — đúng tình huống người dùng báo."""
    a = tmp_path / "test" / ".cowork_history"
    b = tmp_path / "test1" / ".cowork_history"
    _viet_hoi_thoai(a, "s-a", "chat cua test", mtime=1000)
    _viet_hoi_thoai(b, "s-b", "chat cua test1", mtime=2000)
    return [("p-test", a), ("p-test1", b)]


# ---- triệu chứng gốc -----------------------------------------------------

def test_mot_lan_goi_chi_thay_mot_project(hai_project):
    """Chốt lại chính nguyên nhân, để nó không bị coi là chuyện đương nhiên."""
    _pid_a, dir_a = hai_project[0]

    chi_mot = list_conversations(dir_a)

    assert len(chi_mot) == 1
    assert chi_mot[0]["title"] == "chat cua test"


def test_gop_nhieu_thu_muc_thi_thay_du(hai_project):
    tat_ca = list_conversations_by_project(hai_project)

    assert {c["title"] for c in tat_ca} == {"chat cua test", "chat cua test1"}


def test_moi_hoi_thoai_thuoc_dung_project(hai_project):
    """Thư mục là chủ sở hữu có thẩm quyền, không phải trường project_id trong file."""
    theo_pid = {c["project_id"]: c["title"] for c in list_conversations_by_project(hai_project)}

    assert theo_pid == {"p-test": "chat cua test", "p-test1": "chat cua test1"}


def test_project_id_cu_trong_file_bi_ghi_de(tmp_path):
    """Project bị đổi thư mục thì trường trong file đã cũ — thư mục vẫn đúng."""
    d = tmp_path / "moi" / ".cowork_history"
    _viet_hoi_thoai(d, "s1", "x", project_id="pid-cu-roi")

    ket_qua = list_conversations_by_project([("pid-that", d)])

    assert ket_qua[0]["project_id"] == "pid-that"


# ---- thứ tự và trùng lặp -------------------------------------------------

def test_giu_dung_thu_tu_moi_nhat_truoc(hai_project):
    tat_ca = list_conversations_by_project(hai_project)

    assert [c["title"] for c in tat_ca] == ["chat cua test1", "chat cua test"]


def test_ghim_len_dau_bat_ke_thoi_gian(tmp_path):
    d1 = tmp_path / "a" / ".cowork_history"
    d2 = tmp_path / "b" / ".cowork_history"
    _viet_hoi_thoai(d1, "cu", "cu ma ghim", mtime=1000)
    _viet_hoi_thoai(d2, "moi", "moi ma khong ghim", mtime=9000)
    data = json.loads((d1 / "cu.json").read_text(encoding="utf-8"))
    data["pinned"] = True
    (d1 / "cu.json").write_text(json.dumps(data), encoding="utf-8")

    tat_ca = list_conversations_by_project([("a", d1), ("b", d2)])

    assert tat_ca[0]["title"] == "cu ma ghim"


def test_cung_mot_thu_muc_hai_lan_khong_dem_doi(hai_project):
    """``history_dirs()`` có thể trả về trùng thư mục khi cấu hình chồng nhau."""
    _pid, d = hai_project[0]

    assert len(list_conversations_by_project([("x", d), ("y", d)])) == 1


# ---- đầu vào xấu ---------------------------------------------------------

def test_thu_muc_chua_ton_tai_thi_bo_qua(tmp_path, hai_project):
    tat_ca = list_conversations_by_project(
        hai_project + [("rong", tmp_path / "chua-he-co")])

    assert len(tat_ca) == 2


def test_thu_muc_None_thi_bo_qua(hai_project):
    assert len(list_conversations_by_project(hai_project + [("x", None)])) == 2


def test_khong_co_project_nao_thi_tra_rong():
    assert list_conversations_by_project([]) == []


# ---- tìm kiếm vẫn hoạt động khi đã gộp -----------------------------------

def test_tim_kiem_ap_cho_moi_thu_muc(hai_project):
    assert len(list_conversations_by_project(hai_project, query="test1")) == 1
    assert len(list_conversations_by_project(hai_project, query="chat cua")) == 2
    assert list_conversations_by_project(hai_project, query="khong-he-co") == []


# ---- một định nghĩa duy nhất cho đường dẫn -------------------------------

def test_duong_dan_lich_su_chi_dinh_nghia_mot_cho():
    """Chuỗi ".cowork_history" từng nằm rải ở ``ui/workspace_tab.py``."""
    from cowork_local.core.projects import HISTORY_SUBDIR

    repo = Path(__file__).resolve().parents[1]
    src = (repo / "ui" / "workspace_tab.py").read_text(encoding="utf-8")

    assert HISTORY_SUBDIR == ".cowork_history"
    assert ".cowork_history" not in src, "phải dùng project_history_dir()"
