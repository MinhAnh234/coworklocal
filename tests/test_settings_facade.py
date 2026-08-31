"""Typed Settings Facade — R02-T03."""
from __future__ import annotations

from cowork_local.infrastructure.config.settings_facade import (
    ProviderSettings, RoutingSettings, SecuritySettings, Settings,
)
from cowork_local.tests.fakes.fake_config import FakeConfigRepository


def test_provider_doc_duoc_ba_truong():
    p = ProviderSettings({"base_url": "http://x/v1", "model": "llama3",
                          "api_key": "sk-abc"})
    assert p.base_url == "http://x/v1"
    assert p.model == "llama3"
    assert p.api_key == "sk-abc"
    assert p.configured is True


def test_ollama_khong_can_khoa_van_tinh_la_da_cau_hinh():
    """Điều kiện là có base_url và model, không phải có api_key — Ollama chạy
    cục bộ nên không cần khoá."""
    p = ProviderSettings({"base_url": "http://localhost:11434/v1", "model": "llama3"})
    assert p.api_key == ""
    assert p.configured is True


def test_thieu_model_thi_chua_cau_hinh():
    assert ProviderSettings({"base_url": "http://x/v1"}).configured is False
    assert ProviderSettings({}).configured is False


def test_gia_tri_None_tra_ve_mac_dinh_chu_khong_None():
    """File cấu hình cũ hay có khoá để null. Đọc ra None rồi đem so sánh số là
    vỡ — nên khung nhìn phải nuốt luôn trường hợp này."""
    r = RoutingSettings({"switch_mode": None, "min_score_gain": None,
                         "confirm_timeout_sec": None})
    assert r.switch_mode == "off"
    assert r.min_score_gain == 0.05
    assert r.confirm_timeout_sec == 60


def test_routing_kieu_du_lieu_dung():
    r = RoutingSettings({"switch_mode": "auto", "min_score_gain": "0.2",
                         "confirm_timeout_sec": "90"})
    assert r.enabled is True
    assert isinstance(r.min_score_gain, float) and r.min_score_gain == 0.2
    assert isinstance(r.confirm_timeout_sec, int) and r.confirm_timeout_sec == 90


def test_tat_dinh_tuyen():
    assert RoutingSettings({"switch_mode": "off"}).enabled is False
    assert RoutingSettings({}).enabled is False


def test_sua_qua_khung_nhin_la_sua_vao_dict_that():
    """Khung nhìn, không phải bản sao — sửa xong gọi save() là xuống đĩa."""
    d = {"switch_mode": "off"}
    RoutingSettings(d).switch_mode = "auto"
    assert d["switch_mode"] == "auto"


def test_raw_de_khong_ai_bi_ket():
    d = {"switch_mode": "auto", "khoa_chua_dua_vao_khung_nhin": 1}
    assert RoutingSettings(d).raw()["khoa_chua_dua_vao_khung_nhin"] == 1


def test_security_mac_dinh_la_bat():
    """Mặc định an toàn: thiếu cấu hình thì bật kiểm tra, không phải tắt."""
    s = SecuritySettings({})
    assert s.enabled is True
    assert s.validate_prompt is True
    assert s.validate_commands is True
    assert s.cowork_confirm_commands is True
    assert s.command_ai_check is False       # trừ cái này: gọi AI, tốn tiền


def test_settings_noi_vao_repo():
    repo = FakeConfigRepository(active_provider="openai",
                                routing={"switch_mode": "auto"},
                                agent_security={"cowork_confirm_commands": False})
    s = Settings(repo)
    assert s.provider().model == "gpt-4o-mini"
    assert s.routing.enabled is True
    assert s.security.cowork_confirm_commands is False


def test_doi_provider_thi_khung_nhin_theo_ngay():
    repo = FakeConfigRepository(active_provider="ollama")
    s = Settings(repo)
    assert s.provider().model == "llama3"
    repo.set_active_provider("openai")
    assert s.provider().model == "gpt-4o-mini"
