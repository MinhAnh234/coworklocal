"""Đặc tả hành vi SettingsDialog TRƯỚC khi tách — R08-T07.

Không phải test tính năng mới. Đây là lưới an toàn: chốt lại dialog hiện
đang làm gì, để khi bóc 727 dòng thành các widget con còn biết mình có làm
lệch đi chỗ nào không. Bài nào ở đây đỏ sau khi tách nghĩa là tách sai.
"""
from __future__ import annotations

import pytest


class _Config:
    """Đủ dùng cho SettingsDialog, không hơn — xem danh sách ctx.* nó chạm."""

    def __init__(self):
        self.data = {
            "active_provider": "openai_compat",
            "language": "vi",
            "theme": "dark",
            "providers": {
                "openai_compat": {"base_url": "https://api.openai.com/v1",
                                  "api_key": "khoa-cu", "model": "gpt-4o"},
                "ollama": {"base_url": "http://localhost:11434",
                           "api_key": "ollama", "model": "qwen2.5-coder"},
            },
            "tray": {"minimize_on_close": True, "notify_on_done": False},
            "agent_security": {
                "enabled": True, "cowork_confirm_commands": False,
                "block_network": True, "command_ai_check": False,
                "resource_limit_cpu_percent": 55,
                "resource_limit_memory_mb": 1024,
                "resource_limit_disk_mb": 2048,
            },
            "attachments": {"max_tokens": 32000, "max_files": 7},
            "structure": {"max_nodes": 300, "max_edges": 600},
            "routing": {"switch_mode": "auto", "policy": "cost",
                        "min_score_gain": 0.05, "confirm_timeout_sec": 90,
                        "reassess_interval_hours": 12,
                        "per_provider_concurrency": 3,
                        "judge_model": "gpt-4o-mini"},
        }
        self._data = self.data
        self._agent_security = self.data["agent_security"]

    language = property(lambda self: self.data["language"])
    theme = property(lambda self: self.data["theme"])
    active_provider = property(lambda self: self.data["active_provider"])
    agent_security = property(lambda self: self.data["agent_security"])
    routing = property(lambda self: self.data["routing"])


class _Ctx:
    def __init__(self):
        self.config = _Config()
        self.routing = None
        self.saves = 0

    def save(self):
        self.saves += 1


@pytest.fixture
def dialog(qapp):
    from cowork_local.ui.settings_dialog import SettingsDialog
    ctx = _Ctx()
    dlg = SettingsDialog(ctx)
    yield dlg, ctx
    dlg.deleteLater()


# ---- dialog gồm những mục nào -------------------------------------------

def test_co_dung_sau_muc(dialog):
    """Sáu mục thật trên màn hình.

    Plan R08-T07 ghi bốn widget và có một cái tên `connector`, nhưng UI
    connector đã dời khỏi Settings từ trước (xem ghi chú ở
    settings_dialog.py:180) — nên con số thật là năm, không bốn.

    Mục thứ sáu là "Giới thiệu", thêm ngày 2026-09-07 cùng lúc với việc gỡ dòng
    ghi công tác giả khỏi góc dưới phải cửa sổ. Đây là thay đổi CÓ CHỦ Ý, không
    phải tách nhầm."""
    dlg, _ = dialog
    labels = [dlg.section_list.item(i).text()
              for i in range(dlg.section_list.count())]
    assert len(labels) == 6, labels
    assert dlg.section_stack.count() == 6


def test_moi_muc_deu_bam_duoc(dialog):
    dlg, _ = dialog
    for i in range(dlg.section_list.count()):
        dlg.section_list.setCurrentRow(i)
        assert dlg.section_stack.currentIndex() == i


# ---- nạp giá trị từ config ----------------------------------------------

def test_nap_dung_gia_tri_dang_co(dialog):
    dlg, ctx = dialog
    assert dlg.language_combo.currentData() == "vi"
    assert dlg.theme_combo.currentData() == "dark"
    assert dlg.provider_combo.currentData() == "openai_compat"
    assert dlg.prov_base.text() == "https://api.openai.com/v1"
    assert dlg.tray_chk.isChecked() is True
    assert dlg.notify_chk.isChecked() is False
    assert dlg.routing_mode.currentData() == "auto"
    assert dlg.routing_policy.currentData() == "cost"
    assert dlg.routing_timeout.value() == 90
    assert dlg.attach_files.value() == 7
    assert dlg.struct_nodes.value() == 300
    assert dlg.sandbox_cpu.value() == 55


def test_khoa_api_khong_hien_ro(dialog):
    """QLineEdit.Password — khoá không được đọc được bằng mắt qua vai."""
    from PySide6.QtWidgets import QLineEdit
    dlg, _ = dialog
    assert dlg.prov_key.echoMode() == QLineEdit.Password


# ---- lưu ghi ra đúng chỗ -------------------------------------------------

def test_luu_ghi_dung_moi_o(dialog):
    dlg, ctx = dialog
    dlg.language_combo.setCurrentIndex(
        dlg.language_combo.findData("en") if dlg.language_combo.findData("en") >= 0 else 0)
    dlg.tray_chk.setChecked(False)
    dlg.routing_timeout.setValue(120)
    dlg.attach_files.setValue(3)
    dlg.sandbox_cpu.setValue(80)

    dlg._save()
    d = ctx.config.data

    assert d["tray"]["minimize_on_close"] is False
    assert d["routing"]["confirm_timeout_sec"] == 120
    assert d["attachments"]["max_files"] == 3
    assert d["agent_security"]["resource_limit_cpu_percent"] == 80
    assert ctx.saves == 1


def test_luu_doi_min_gain_tu_phan_tram_sang_phan_le(dialog):
    """Ô nhập là %, config lưu số thập phân. Đây là chỗ dễ tách sai nhất."""
    dlg, ctx = dialog
    dlg.routing_min_gain.setValue(25)
    dlg._save()
    assert ctx.config.data["routing"]["min_score_gain"] == 0.25


def test_luu_xoa_cache_de_app_doc_lai_ngay(dialog):
    dlg, ctx = dialog
    dlg._save()
    assert ctx.config._data is None
    assert ctx.config._agent_security is None
