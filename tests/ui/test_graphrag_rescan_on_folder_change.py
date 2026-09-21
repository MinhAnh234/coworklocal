"""Đổi thư mục project thì đồ thị giữa màn GraphRAG phải quét lại.

Nối tiếp ``test_graphrag_follows_folder_change.py``. Sau khi đường dẫn trên
thanh đã trỏ đúng thư mục mới, các node ở giữa màn vẫn là của thư mục cũ: không
có lệnh quét lại nào được phát ra.

Nguyên nhân cùng một họ với hai mảnh trước — câu hỏi "có gì đổi không" được trả
lời bằng project id chứ không bằng thứ thật sự quyết định kết quả quét:

    project_changed = pid != self._active_project_id

Đổi thư mục làm việc ở màn Project giữ nguyên id, nên ``project_changed`` là
False và cả khối phát tín hiệu lẫn khối gọi ``_scan()`` đều bị bỏ qua.

Cố ý KHÔNG dựng ``GraphRenderer`` thật: nó kéo theo QtWebEngine, dựng trong bộ
``tests/ui`` làm cả bộ chết giữa chừng (xem docstring của
``test_graphrag_follows_folder_change.py``). ``_on_project_changed`` là Python
thuần trên các thuộc tính của chính nó, nên gọi thẳng với một ``self`` giả là đủ
và đúng hơn — bài test chốt luồng quyết định, không chốt phần vẽ.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="cần PySide6 để nạp module renderer")

from cowork_local.core import projects as projects_mod
from cowork_local.core.projects import Project
from cowork_local.presentation.graph.graph_renderer import GraphRenderer


class _O:
    """Vật thể ghi lại lời gọi, thay cho một widget Qt."""

    def __init__(self, **thuoc_tinh):
        self.__dict__.update(thuoc_tinh)
        self.da_goi = []

    def __getattr__(self, ten):
        def ghi(*args, **kwargs):
            self.da_goi.append((ten, args))
        return ghi


class _ComboGia:
    def __init__(self, pid):
        self._pid = pid

    def currentData(self):
        return self._pid


class _OGia:
    """Ô nhập đường dẫn: giữ được chữ, và ghi lại việc bị khoá."""

    def __init__(self, text=""):
        self._text = text
        self.read_only = False

    def text(self):
        return self._text

    def setText(self, value):
        self._text = value

    def setReadOnly(self, value):
        self.read_only = value


class _Renderer:
    """``self`` giả cho ``GraphRenderer._on_project_changed``."""

    def __init__(self, pid, active_id="", active_path="", hien=True):
        self.project_combo = _ComboGia(pid)
        self.path_edit = _OGia()
        self._pick_btn = _O()
        self.project_changed = _O()
        self._active_project_id = active_id
        self._active_path = active_path
        self._needs_scan = False
        self._hien = hien
        self.lan_quet = 0

    def isVisible(self):
        return self._hien

    def _scan(self):
        self.lan_quet += 1

    # -- tiện cho khẳng định --------------------------------------------- #
    @property
    def so_lan_bao_doi(self):
        """Số lần phát tín hiệu "đã đổi mục tiêu"."""
        return sum(1 for ten, _ in self.project_changed.da_goi if ten == "emit")


@pytest.fixture
def du_an(monkeypatch, tmp_path):
    """Một project duy nhất trong kho giả, trỏ vào ``tmp_path/cu``."""
    p = Project(project_id="p1", name="test", output_dir=str(tmp_path / "cu"))
    monkeypatch.setattr(projects_mod, "load_project",
                        lambda pid, directory=None: p if pid == "p1" else None)
    return p


def _chay(renderer):
    """Gọi đúng hàm thật với ``self`` giả."""
    GraphRenderer._on_project_changed(renderer, 0)


def test_cung_project_thu_muc_moi_thi_quet_lai(du_an, tmp_path):
    """Đây là chỗ hỏng người dùng báo: đường dẫn đổi mà node giữa màn thì không."""
    r = _Renderer("p1")
    _chay(r)                                   # lần đầu: khoá vào project
    assert r.lan_quet == 1

    du_an.output_dir = str(tmp_path / "moi")   # người dùng bấm "Đổi" ở tab Project
    _chay(r)

    assert r.path_edit.text() == str(tmp_path / "moi")
    assert r.lan_quet == 2, "đổi thư mục xong nhưng không quét lại — node vẫn của thư mục cũ"
    assert r.so_lan_bao_doi == 2, (
        "phải báo đổi để khung hỏi-đáp bỏ phần trích xuất của thư mục cũ")


def test_cung_project_cung_thu_muc_thi_khong_quet_lai(du_an):
    """Bảo vệ sẵn có: ``_bind_project`` chạy lại mỗi lần vào lại màn Workspace,
    quét lại vô cớ là vừa giật vừa tốn."""
    r = _Renderer("p1")
    _chay(r)
    assert r.lan_quet == 1

    _chay(r)
    _chay(r)

    assert r.lan_quet == 1


def test_doi_sang_project_khac_van_quet_lai(du_an, tmp_path, monkeypatch):
    """Hành vi vốn có, không được mất."""
    khac = Project(project_id="p2", name="khac", output_dir=str(tmp_path / "cua-p2"))
    monkeypatch.setattr(projects_mod, "load_project",
                        lambda pid, directory=None: du_an if pid == "p1" else khac)
    r = _Renderer("p1")
    _chay(r)

    r.project_combo._pid = "p2"
    _chay(r)

    assert r.lan_quet == 2
    assert r.path_edit.text() == str(tmp_path / "cua-p2")


def test_man_dang_an_thi_hoan_quet_chu_khong_quet_ngay(du_an, tmp_path):
    """Đổi thư mục từ màn Project trong khi GraphRAG đang ẩn: đánh dấu để quét
    ở lần vào sau, đúng luật hoãn mà ``auto_scan_and_fit`` dựa vào."""
    r = _Renderer("p1", hien=False)
    _chay(r)
    # Lần khoá đầu tiên đã đặt cờ rồi; xoá đi để bài này thật sự kiểm được
    # lần ĐỔI THƯ MỤC, chứ không xanh nhờ cờ còn sót của lần trước.
    r._needs_scan = False

    du_an.output_dir = str(tmp_path / "moi")
    _chay(r)

    assert r.lan_quet == 0
    assert r._needs_scan is True
