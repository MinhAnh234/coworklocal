"""JsonConfigRepository — R02-T02.

Hai nhóm bài:
  * **round-trip** — ghi rồi nạp lại phải ra đúng thứ đã ghi (cột nghiệm thu
    của plan.md cho ngày 22-23/08)
  * **đường A** — ``provider_conf()`` vẫn trả ``api_key``, nhưng file JSON
    trên đĩa thì không có, để qua CASAN Check 1
"""
from __future__ import annotations

import json

import pytest

from cowork_local.infrastructure.config.config_repository import ConfigRepository
from cowork_local.infrastructure.config.json_config_repository import (
    JsonConfigRepository,
)
from cowork_local.tests.fakes.fake_config import FakeSecretStore

DEFAULTS = {
    "active_provider": "ollama",
    "providers": {
        "ollama": {"base_url": "http://localhost:11434/v1", "model": "llama3",
                   "api_key": "ollama"},
        "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini",
                   "api_key": ""},
    },
    "theme": "dark", "language": "vi", "shared_dir": "",
    "routing": {"mode": "off"}, "auth": {}, "agent_security": {},
    "tools_disabled": [], "history": {}, "cowork": {}, "ms365": {},
}


def _repo(tmp_path, secrets=None):
    return JsonConfigRepository(tmp_path / "config.json", secrets=secrets,
                                defaults=DEFAULTS, env_overrides=lambda d: d)


def test_khop_hop_dong(tmp_path):
    assert isinstance(_repo(tmp_path), ConfigRepository)


def test_chua_co_file_thi_dung_mac_dinh(tmp_path):
    cfg = _repo(tmp_path)
    assert cfg.active_provider == "ollama"
    assert cfg.theme == "dark"


def test_round_trip(tmp_path):
    cfg = _repo(tmp_path)
    cfg.set_theme("light")
    cfg.set_language("en")
    cfg.set_active_provider("openai")
    cfg.set_tool_enabled("run_command", False)
    cfg.save()

    lai = _repo(tmp_path)
    assert lai.theme == "light"
    assert lai.language == "en"
    assert lai.active_provider == "openai"
    assert lai.tools_disabled == ["run_command"]


def test_gia_tri_luu_trong_file_trum_len_mac_dinh_nhung_giu_phan_con_thieu(tmp_path):
    """Trộn sâu: file cũ thiếu khoá mới thì lấy mặc định, không mất phần cũ."""
    (tmp_path / "config.json").write_text(
        json.dumps({"theme": "light", "providers": {"openai": {"model": "gpt-5"}}}),
        encoding="utf-8")
    cfg = _repo(tmp_path)
    assert cfg.theme == "light"                                   # từ file
    assert cfg.language == "vi"                                   # từ mặc định
    assert cfg.provider_conf("openai")["model"] == "gpt-5"        # từ file
    assert "api.openai.com" in cfg.provider_conf("openai")["base_url"]   # mặc định


# ---- đường A: khoá vào kho bí mật, nhưng dict vẫn có ------------------------

def test_provider_conf_van_tra_api_key_sau_khi_chuyen_vao_kho(tmp_path):
    """Điểm mấu chốt của quyết định A: 5 nơi đọc conf['api_key'] không đổi."""
    secrets = FakeSecretStore()
    cfg = _repo(tmp_path, secrets)
    cfg.set_api_key("openai", "sk-that-bi-mat")

    assert cfg.provider_conf("openai")["api_key"] == "sk-that-bi-mat"


def test_khoa_khong_bao_gio_nam_tren_dia(tmp_path):
    """Điều kiện qua CASAN Check 1."""
    secrets = FakeSecretStore()
    cfg = _repo(tmp_path, secrets)
    cfg.set_api_key("openai", "sk-that-bi-mat")
    cfg.save()

    raw = (tmp_path / "config.json").read_text(encoding="utf-8")
    assert "sk-that-bi-mat" not in raw
    assert secrets.get("provider:openai") == "sk-that-bi-mat"


def test_sua_dict_tra_ve_khong_lam_ban_cau_hinh(tmp_path):
    """provider_conf trả bản sao — nếu trả tham chiếu thì khoá vừa ghép vào sẽ
    lẫn ngược vào self.data rồi theo save() xuống đĩa."""
    secrets = FakeSecretStore()
    cfg = _repo(tmp_path, secrets)
    cfg.set_api_key("openai", "sk-bi-mat")

    conf = cfg.provider_conf("openai")
    conf["model"] = "bị sửa bậy"
    cfg.save()

    raw = (tmp_path / "config.json").read_text(encoding="utf-8")
    assert "bị sửa bậy" not in raw
    assert "sk-bi-mat" not in raw


def test_khong_co_kho_bi_mat_thi_van_chay_nhu_cu(tmp_path):
    """Máy không có keyring: hành vi lùi về đúng như config.py hôm nay."""
    cfg = _repo(tmp_path, secrets=None)
    cfg.set_api_key("openai", "sk-nam-trong-file")
    cfg.save()

    assert cfg.provider_conf("openai")["api_key"] == "sk-nam-trong-file"
    raw = (tmp_path / "config.json").read_text(encoding="utf-8")
    assert "sk-nam-trong-file" in raw     # đúng như cũ, có đánh đổi rõ ràng


# ---- giữ nguyên hành vi cũ --------------------------------------------------

def test_ms365_unlocked_khong_bao_gio_xuong_dia(tmp_path):
    cfg = _repo(tmp_path)
    cfg.data["ms365"]["unlocked"] = True
    cfg.save()

    raw = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert raw["ms365"]["unlocked"] is False
    assert cfg.data["ms365"]["unlocked"] is True    # trong bộ nhớ vẫn giữ

    assert _repo(tmp_path).data["ms365"]["unlocked"] is False


def test_ghi_hong_giua_chung_khong_lam_mat_cau_hinh(tmp_path, monkeypatch):
    """Thừa hưởng từ AtomicJsonFile — kiểm lại ở tầng này cho chắc."""
    import os

    cfg = _repo(tmp_path)
    cfg.set_theme("light")
    cfg.save()

    monkeypatch.setattr(os, "replace",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("mất điện")))
    cfg.set_theme("hỏng")
    with pytest.raises(OSError):
        cfg.save()

    assert _repo(tmp_path).theme == "light"
