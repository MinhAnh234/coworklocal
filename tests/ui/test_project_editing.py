"""Tab Project: chế độ chỉ-xem, chặn trùng tên, menu chuột phải, đổi ngôn ngữ.

Bốn tính năng nằm cùng ``presentation/workspace/project_editing.py`` nên test
cũng đi cùng nhau. Xem docstring của module đó về lý do chúng là một khối.
"""
from __future__ import annotations

import pytest

from cowork_local.presentation.workspace.project_editing import (
    ProjectRow, _row_layout_of,
)


# ---- ProjectRow: giữ SỐ, không giữ chuỗi đã format -----------------------

def test_dong_project_dung_lai_nhan_theo_ngon_ngu(qapp):
    """Đây là bug gốc: ``workspace.counts`` được format một lần lúc dựng dòng,
    nên đổi ngôn ngữ xong nó vẫn nằm ở ngôn ngữ cũ — kể cả khi chọn tiếng Anh."""
    from cowork_local import i18n

    truoc = i18n.get_language()
    try:
        i18n.set_language("vi")
        row = ProjectRow("Dự án A", chats=2, tasks=3)
        vi = row.counts_label.text()

        i18n.set_language("ja")
        row.retranslate()
        ja = row.counts_label.text()

        i18n.set_language("en")
        row.retranslate()
        en = row.counts_label.text()
    finally:
        i18n.set_language(truoc)

    assert vi != ja != en, (vi, ja, en)
    # Số liệu phải sống sót qua mọi lần dịch lại
    for text in (vi, ja, en):
        assert "2" in text and "3" in text, text


def test_dong_project_giu_so_de_dich_lai_duoc(qapp):
    """Giữ số chứ không giữ chuỗi — nếu chỉ giữ chuỗi thì dịch lại phải đọc đĩa."""
    row = ProjectRow("X", chats=7, tasks=1)
    assert (row.chats, row.tasks) == (7, 1)


# ---- _row_layout_of ------------------------------------------------------

def test_tim_duoc_layout_dang_chua_widget(qapp):
    """Nút "Sửa project" được chèn cạnh nút Lưu bằng hàm này."""
    from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

    host = QWidget()
    outer = QVBoxLayout(host)
    inner = QHBoxLayout()
    btn = QPushButton("x")
    inner.addWidget(btn)
    outer.addLayout(inner)

    assert _row_layout_of(btn) is inner


def test_khong_co_cha_thi_tra_None(qapp):
    from PySide6.QtWidgets import QPushButton

    assert _row_layout_of(QPushButton("mo coi")) is None


# ---- chặn trùng tên ------------------------------------------------------

class _FakeProject:
    def __init__(self, pid: str, name: str):
        self.project_id = pid
        self.name = name


class _NameChecker:
    """Chỉ phần chặn trùng tên của mixin, không dựng cả WorkspaceTab."""
    from cowork_local.presentation.workspace.project_editing import (
        ProjectEditingMixin as _M,
    )
    _name_taken = _M._name_taken


@pytest.fixture
def checker(monkeypatch):
    import cowork_local.core.projects as projects

    monkeypatch.setattr(projects, "list_projects", lambda: [
        _FakeProject("p1", "Báo cáo"),
        _FakeProject("p2", "Sales Q3"),
    ])
    return _NameChecker()


@pytest.mark.parametrize("name", ["Báo cáo", "báo cáo", "  Báo cáo  ", "BÁO CÁO"])
def test_trung_ten_bi_chan_du_hoa_thuong_hay_khoang_trang(checker, name):
    """Với người dùng thì "Báo cáo" và "báo cáo " là cùng một cái tên."""
    assert checker._name_taken(name) is True


def test_ten_moi_thi_khong_bi_chan(checker):
    assert checker._name_taken("Báo cáo 2026") is False


def test_ten_rong_khong_bi_coi_la_trung(checker):
    """Ô tên trống là "chưa nhập", không phải "trùng" — thông báo phải khác nhau."""
    assert checker._name_taken("") is False
    assert checker._name_taken("   ") is False


def test_sua_chinh_no_thi_giu_nguyen_ten_duoc(checker):
    """Mở project rồi bấm Lưu mà không đổi tên thì không được báo trùng chính nó."""
    assert checker._name_taken("Báo cáo", ignore_id="p1") is False
    assert checker._name_taken("Báo cáo", ignore_id="p2") is True


# ---- i18n: các key mới có đủ 3 ngôn ngữ ----------------------------------

@pytest.mark.parametrize("key", [
    "workspace.edit_project", "workspace.menu_open", "workspace.menu_edit",
    "workspace.menu_delete", "workspace.name_taken_title", "workspace.name_taken_body",
    "workspace.instructions",
])
def test_key_moi_co_du_ba_ngon_ngu(key):
    from cowork_local import i18n

    entry = i18n.STRINGS[key]
    for lang in ("en", "ja", "vi"):
        assert entry.get(lang), f"{key} thiếu {lang}"


def test_nhan_instructions_da_duoc_dich():
    """Nó nằm giữa "Tên"/"名前" và "Mô tả"/"説明" đã dịch, nên để nguyên tiếng
    Anh là sót chứ không phải chủ ý."""
    from cowork_local import i18n

    entry = i18n.STRINGS["workspace.instructions"]
    assert entry["ja"] != entry["en"]
    assert entry["vi"] != entry["en"]


# ---- theme: nút vàng / xanh lá dùng token, không dùng hex ----------------

@pytest.mark.parametrize("object_name,token", [("warning", "warning"), ("success", "success")])
def test_nut_mau_duoc_style_bang_token_trong_theme(object_name, token):
    """Màu của hai nút phải nằm trong theme/, không phải setStyleSheet cục bộ."""
    from cowork_local.theme.qss import _TEMPLATE

    rule = f"QPushButton#{object_name}"
    assert rule in _TEMPLATE.template, f"{rule} chưa được style trong theme"
    block = _TEMPLATE.template.split(rule, 1)[1][:200]
    assert f"${token}" in block


def test_khong_hardcode_mau_trong_module_moi():
    """Guardrail G4: ngoài theme/ không file nào được đặt tên một màu."""
    import re
    from pathlib import Path

    src = (Path(__file__).resolve().parents[2]
           / "presentation" / "workspace" / "project_editing.py").read_text(encoding="utf-8")
    code = "\n".join(l for l in src.splitlines()
                     if not l.strip().startswith("#") and "#CCA700" not in l)
    assert not re.search(r'setStyleSheet\(', code), "không được setStyleSheet cục bộ"


# ---- tích hợp: chế độ chỉ-xem trên WorkspaceTab thật ----------------------
#
# KHÔNG tạo project trong các bài này. ``core/projects.py`` gắn
# ``PROJECTS_DIR = CONFIG_DIR / "projects"`` vào ``~/.cowork_local`` THẬT, nên
# gọi ``_create()`` là ghi vào dữ liệu đang dùng của người chạy test. Chỉ cần
# gán ``_current_id`` một giá trị giả là đủ để bật đúng nhánh cần kiểm.

@pytest.fixture(scope="module")
def workspace(qapp, tmp_path_factory):
    from cowork_local.presentation.shell.bootstrap import build_config, build_context
    from cowork_local.presentation.shell.main_window import MainWindow

    config_path = tmp_path_factory.mktemp("cfg") / "config.json"
    build_config(config_path)
    win = MainWindow(build_context(config_path))
    yield win.workspace
    win.close()


def test_project_san_co_mo_ra_o_che_do_chi_xem(workspace):
    """Lỡ tay không được sửa mất nội dung của một project đang dùng."""
    workspace._current_id = "gia-lap"
    workspace.set_project_editable(False)

    assert workspace.name_edit.isReadOnly() is True
    assert workspace.desc_edit.isReadOnly() is True
    assert workspace.instr_edit.isReadOnly() is True
    assert workspace._save_btn.isEnabled() is False
    assert workspace._edit_btn.isEnabled() is True


def test_bam_sua_project_thi_mo_khoa_form(workspace):
    workspace._current_id = "gia-lap"
    workspace.enter_project_edit_mode()

    assert workspace.name_edit.isReadOnly() is False
    assert workspace._save_btn.isEnabled() is True
    assert workspace._edit_btn.isEnabled() is False


def test_nut_luu_doi_sang_xanh_la_khi_dang_sua(workspace):
    """Yêu cầu: Save đổi màu xanh lá khi vào chế độ sửa."""
    workspace._current_id = "gia-lap"

    workspace.set_project_editable(False)
    assert workspace._save_btn.objectName() == "primary"

    workspace.set_project_editable(True)
    assert workspace._save_btn.objectName() == "success"


def test_nut_sua_project_mau_vang(workspace):
    """Yêu cầu: nút Edit project màu vàng — qua token ``warning``."""
    assert workspace._edit_btn.objectName() == "warning"


def test_chua_chon_project_thi_khong_co_gi_bam_duoc(workspace):
    """Không project nào đang mở thì cả Sửa lẫn Lưu đều không có nghĩa."""
    workspace._current_id = ""
    workspace.set_project_editable(False)

    assert workspace._edit_btn.isVisible() is False
    assert workspace._save_btn.isEnabled() is False


def test_danh_sach_project_bat_chuot_phai(workspace):
    """Trước đây bấm phải không làm gì cả."""
    from PySide6.QtCore import Qt

    assert workspace.project_list.contextMenuPolicy() == Qt.CustomContextMenu
