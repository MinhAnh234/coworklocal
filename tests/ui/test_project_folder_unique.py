"""Mỗi thư mục làm việc chỉ được thuộc về MỘT project.

Thư mục làm việc vừa là sandbox (agent chỉ được đọc/ghi bên trong nó) vừa là
kho kiến thức chung của project (file ở gốc thư mục được mọi đoạn chat tự đọc).
Hai project trỏ vào cùng một thư mục là đọc lẫn dữ liệu của nhau và ghi đè lên
nhau — đúng điều mà docstring đầu ``core/projects.py`` nói sandbox sinh ra để
ngăn, nhưng trước đây không có gì chặn.

Hai nhóm bài:

* **Luật** — ``folder_conflict`` nhận diện trùng, kể cả khác hoa thường, khác
  kiểu dấu phân cách, và LỒNG NHAU (đứng ở thư mục cha thì vẫn với tới được
  file của project con).
* **Giao diện** — nhãn cảnh báo dưới ô "Thư mục làm việc" hiện đúng lúc, vì dữ
  liệu cũ có thể đã trùng sẵn và luật mới chỉ chặn từ lúc chọn trở đi.
"""
from __future__ import annotations

import os

import pytest

from cowork_local.core import projects as projects_mod
from cowork_local.core.projects import Project, WORKSPACES_DIR, folder_conflict


def _kho(monkeypatch, *ds: Project) -> None:
    """Giả lập kho project, không đụng ``~/.cowork_local`` thật."""
    monkeypatch.setattr(projects_mod, "list_projects", lambda directory=None: list(ds))


# ---- luật: nhận diện trùng ----------------------------------------------

def test_trung_y_het_thi_bi_bat(monkeypatch, tmp_path):
    _kho(monkeypatch, Project(project_id="a", name="A", output_dir=str(tmp_path)))

    khac = folder_conflict(str(tmp_path), ignore_id="b")

    assert khac is not None and khac.project_id == "a"


def test_khac_hoa_thuong_va_dau_phan_cach_van_la_trung(monkeypatch, tmp_path):
    """Trên Windows ``D:/Work`` và ``d:/work`` là cùng một thư mục."""
    _kho(monkeypatch, Project(project_id="a", name="A", output_dir=str(tmp_path)))

    lech = str(tmp_path).replace(os.sep, "/")
    if os.name == "nt":
        lech = lech.upper()

    assert folder_conflict(lech, ignore_id="b") is not None


def test_thu_muc_con_nam_trong_thu_muc_cua_project_khac_la_trung(monkeypatch, tmp_path):
    """Project kia đứng ở thư mục cha thì vẫn đọc/ghi được thư mục con này."""
    _kho(monkeypatch, Project(project_id="a", name="A", output_dir=str(tmp_path)))

    assert folder_conflict(str(tmp_path / "con"), ignore_id="b") is not None


def test_thu_muc_cha_chua_thu_muc_cua_project_khac_la_trung(monkeypatch, tmp_path):
    """Chiều ngược lại cũng phải bắt: chọn thư mục cha là ôm trọn project kia."""
    _kho(monkeypatch, Project(project_id="a", name="A",
                              output_dir=str(tmp_path / "con")))

    assert folder_conflict(str(tmp_path), ignore_id="b") is not None


def test_ten_na_na_nhung_khong_long_nhau_thi_khong_trung(monkeypatch, tmp_path):
    """Bẫy của so sánh tiền tố: ``work2`` KHÔNG nằm trong ``work``."""
    _kho(monkeypatch, Project(project_id="a", name="A",
                              output_dir=str(tmp_path / "work")))

    assert folder_conflict(str(tmp_path / "work2"), ignore_id="b") is None


def test_project_chua_dat_thu_muc_rieng_van_dang_chiem_thu_muc_quan_ly(monkeypatch):
    """``output_dir`` rỗng không có nghĩa là "chưa chiếm chỗ nào": project vẫn
    đang dùng thư mục quản lý sẵn, và chính nó hay bị chọn nhầm."""
    _kho(monkeypatch, Project(project_id="a", name="A", output_dir=""))

    assert folder_conflict(str(WORKSPACES_DIR / "a"), ignore_id="b") is not None


def test_giu_nguyen_thu_muc_cua_chinh_no_thi_khong_phai_trung(monkeypatch, tmp_path):
    _kho(monkeypatch, Project(project_id="a", name="A", output_dir=str(tmp_path)))

    assert folder_conflict(str(tmp_path), ignore_id="a") is None


def test_thu_muc_chua_ai_dung_thi_di_qua(monkeypatch, tmp_path):
    _kho(monkeypatch, Project(project_id="a", name="A",
                              output_dir=str(tmp_path / "cua-a")))

    assert folder_conflict(str(tmp_path / "cua-b"), ignore_id="b") is None


def test_duong_dan_rong_khong_bi_coi_la_trung(monkeypatch, tmp_path):
    """Ô trống là "chưa chọn", không phải "trùng" — khác hẳn nhau."""
    _kho(monkeypatch, Project(project_id="a", name="A", output_dir=str(tmp_path)))

    assert folder_conflict("", ignore_id="b") is None
    assert folder_conflict("   ", ignore_id="b") is None


# ---- i18n: ba key mới phải đủ ba ngôn ngữ -------------------------------

@pytest.mark.parametrize("key", [
    "workspace.folder_taken_title", "workspace.folder_taken_body",
    "workspace.folder_shared_warning",
])
def test_key_moi_co_du_ba_ngon_ngu(key):
    from cowork_local import i18n

    entry = i18n.STRINGS[key]
    for lang in ("en", "ja", "vi"):
        assert entry.get(lang), f"{key} thiếu {lang}"


# ---- giao diện: cảnh báo cho dữ liệu đã trùng sẵn -----------------------

pytest.importorskip("PySide6", reason="cần PySide6 để dựng cửa sổ thật")


@pytest.fixture(scope="module")
def ws(qapp, tmp_path_factory):
    """Một cửa sổ cho cả module — dựng nhiều MainWindow làm Qt chết giữa chừng."""
    from cowork_local.presentation.shell.bootstrap import build_config, build_context
    from cowork_local.presentation.shell.main_window import MainWindow

    config_path = tmp_path_factory.mktemp("cfg") / "config.json"
    build_config(config_path)
    window = MainWindow(build_context(config_path))
    yield window.workspace
    window.close()


def _mo_project(qapp, ws, monkeypatch, dang_mo: Project, *nhung_cai_khac: Project):
    """Mở ``dang_mo`` trên biểu mẫu, với kho chứa cả các project còn lại."""
    _kho(monkeypatch, dang_mo, *nhung_cai_khac)
    monkeypatch.setattr(projects_mod, "load_project",
                        lambda pid, directory=None: dang_mo if pid == dang_mo.project_id else None)
    ws._current_id = dang_mo.project_id
    ws.project_selected.emit(dang_mo.project_id)
    qapp.processEvents()


def test_canh_bao_hien_khi_project_dang_dung_chung_thu_muc(qapp, ws, monkeypatch, tmp_path):
    """Đúng trạng thái trong ảnh người dùng gửi: hai project cùng một thư mục."""
    _mo_project(qapp, ws, monkeypatch,
                Project(project_id="b", name="test3", output_dir=str(tmp_path)),
                Project(project_id="a", name="test2", output_dir=str(tmp_path)))

    assert ws._folder_warn_lbl.isHidden() is False
    assert "test2" in ws._folder_warn_lbl.text()


def test_khong_canh_bao_khi_thu_muc_rieng(qapp, ws, monkeypatch, tmp_path):
    _mo_project(qapp, ws, monkeypatch,
                Project(project_id="b", name="test3", output_dir=str(tmp_path / "b")),
                Project(project_id="a", name="test2", output_dir=str(tmp_path / "a")))

    assert ws._folder_warn_lbl.isHidden() is True


def test_nhan_canh_bao_nam_ngay_duoi_o_thu_muc_lam_viec(ws):
    """Cảnh báo phải ở cạnh thứ nó nói tới, không rơi xuống cuối biểu mẫu."""
    from cowork_local.presentation.workspace.project_editing import _row_layout_of
    from cowork_local.presentation.workspace.project_folder_rules import _layout_chua

    hang = _row_layout_of(ws.folder_lbl)
    layout, vi_tri = _layout_chua(ws.folder_lbl.parentWidget().layout(), hang)

    assert layout.itemAt(vi_tri + 1).widget() is ws._folder_warn_lbl

# ---- hành vi: chọn thư mục đã thuộc project khác thì KHÔNG được ghi ------

def test_chon_thu_muc_trung_thi_khong_ghi_gi(qapp, ws, monkeypatch, tmp_path):
    """Đây là cổng chặn thật, ở đúng nút "Đổi" mà người dùng bấm."""
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    from cowork_local.ui import workspace_tab as wt

    cua_toi = Project(project_id="b", name="test3", output_dir=str(tmp_path / "b"))
    cua_nguoi_khac = Project(project_id="a", name="test2", output_dir=str(tmp_path / "a"))
    _mo_project(qapp, ws, monkeypatch, cua_toi, cua_nguoi_khac)

    da_ghi = []
    monkeypatch.setattr(projects_mod, "save_project",
                        lambda project, directory=None: da_ghi.append(project))
    da_bao = []
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: da_bao.append(a)))
    # Người dùng chọn đúng thư mục của project kia.
    monkeypatch.setattr(QFileDialog, "getExistingDirectory",
                        staticmethod(lambda *a, **k: str(tmp_path / "a")))

    wt.WorkspaceTab._pick_folder(ws)

    assert da_ghi == [], "đã ghi đè output_dir dù thư mục thuộc project khác"
    assert cua_toi.output_dir == str(tmp_path / "b"), "thư mục cũ bị đổi mất"
    assert da_bao, "chặn im lặng — người dùng không biết vì sao không đổi được"


def test_chon_thu_muc_tu_do_thi_van_doi_duoc(qapp, ws, monkeypatch, tmp_path):
    """Chặn một chiều là hỏng tính năng — thư mục chưa ai dùng phải đổi được."""
    from PySide6.QtWidgets import QFileDialog

    from cowork_local.ui import workspace_tab as wt

    cua_toi = Project(project_id="b", name="test3", output_dir=str(tmp_path / "b"))
    cua_nguoi_khac = Project(project_id="a", name="test2", output_dir=str(tmp_path / "a"))
    _mo_project(qapp, ws, monkeypatch, cua_toi, cua_nguoi_khac)

    da_ghi = []
    monkeypatch.setattr(projects_mod, "save_project",
                        lambda project, directory=None: da_ghi.append(project))
    monkeypatch.setattr(QFileDialog, "getExistingDirectory",
                        staticmethod(lambda *a, **k: str(tmp_path / "hoan-toan-moi")))

    wt.WorkspaceTab._pick_folder(ws)

    assert len(da_ghi) == 1
    assert cua_toi.output_dir == str(tmp_path / "hoan-toan-moi")
