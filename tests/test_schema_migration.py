"""Đánh số phiên bản + chuyển API key — R02-T06 và R02-T05."""
from __future__ import annotations

import json

from cowork_local.infrastructure.config.json_config_repository import (
    JsonConfigRepository,
)
from cowork_local.infrastructure.config.schema_migration import (
    CURRENT_VERSION, migrate, read_version,
)
from cowork_local.tests.fakes.fake_config import FakeSecretStore

DEFAULTS = {
    "active_provider": "openai",
    "providers": {"openai": {"base_url": "u", "model": "m", "api_key": ""},
                  "ollama": {"base_url": "u", "model": "m", "api_key": "ollama"}},
    "theme": "dark", "language": "vi", "ms365": {},
}


def _repo(tmp_path, secrets=None):
    return JsonConfigRepository(tmp_path / "config.json", secrets=secrets,
                                defaults=DEFAULTS, env_overrides=lambda d: d)


def test_thieu_so_phien_ban_thi_coi_la_v1():
    assert read_version({}) == 1
    assert read_version({"schema_version": 2}) == 2
    assert read_version({"schema_version": "hỏng"}) == 1


def test_v1_sang_v2_chuyen_khoa_vao_kho_bi_mat():
    secrets = FakeSecretStore()
    data = {"providers": {"openai": {"api_key": "sk-cu-nam-trong-file"}}}  # casan: allow - du lieu test

    out, changed = migrate(data, secrets=secrets)

    assert changed is True
    assert out["schema_version"] == 2
    assert out["providers"]["openai"]["api_key"] == ""
    assert secrets.get("provider:openai") == "sk-cu-nam-trong-file"


def test_khong_day_gia_tri_bu_nhin_cua_ollama_vao_kho():
    """Ollama đòi có api_key nhưng bỏ qua nội dung — đẩy vào keyring chỉ tổ rác."""
    secrets = FakeSecretStore()
    out, _ = migrate({"providers": {"ollama": {"api_key": "ollama"}}}, secrets=secrets)
    assert secrets.get("provider:ollama") is None
    assert out["providers"]["ollama"]["api_key"] == "ollama"


def test_khong_co_kho_bi_mat_thi_KHONG_chuyen():
    """Thà để khoá nằm nguyên trong file còn hơn xoá đi rồi người dùng mất
    khoá mà không hiểu vì sao."""
    data = {"providers": {"openai": {"api_key": "sk-quy-gia"}}}
    out, changed = migrate(data, secrets=None)

    assert changed is False
    assert out["providers"]["openai"]["api_key"] == "sk-quy-gia"
    assert read_version(out) == 1        # giữ v1, lần sau có keyring sẽ chuyển


def test_da_v2_thi_khong_lam_gi_them():
    out, changed = migrate({"schema_version": 2}, secrets=FakeSecretStore())
    assert changed is False


def test_file_moi_hon_app_thi_dung_nguyen_trang():
    """App cũ gặp file mới. Đoán ngược là cách nhanh nhất để mất dữ liệu."""
    data = {"schema_version": 99, "thu_gi_do_tuong_lai": True}
    out, changed = migrate(data, secrets=FakeSecretStore())
    assert changed is False
    assert out == data


def test_sao_luu_truoc_khi_nang_cap(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"providers": {"openai": {"api_key": "sk-x"}}}),
                    encoding="utf-8")

    migrate(json.loads(path.read_text(encoding="utf-8")),
            secrets=FakeSecretStore(), path=path)

    backups = list(tmp_path.glob("*.bak"))
    assert len(backups) == 1, "phải có bản sao lưu để còn đường lùi"
    assert "sk-x" in backups[0].read_text(encoding="utf-8")


# ---- nối vào repository ----------------------------------------------------

def test_repository_tu_chuyen_khoa_khi_mo_file_cu(tmp_path):
    """Cảnh thật: người dùng cập nhật app, mở lên, khoá cũ tự vào keyring."""
    (tmp_path / "config.json").write_text(
        json.dumps({"providers": {"openai": {"api_key": "sk-tu-ban-cu"}}}),  # casan: allow - du lieu test
        encoding="utf-8")

    secrets = FakeSecretStore()
    cfg = _repo(tmp_path, secrets)

    # đọc ra vẫn thấy khoá...
    assert cfg.provider_conf("openai")["api_key"] == "sk-tu-ban-cu"
    # ...nhưng trên đĩa thì hết
    raw = (tmp_path / "config.json").read_text(encoding="utf-8")
    assert "sk-tu-ban-cu" not in raw
    assert json.loads(raw)["schema_version"] == CURRENT_VERSION
    # và có bản sao lưu
    assert len(list(tmp_path.glob("*.bak"))) == 1


def test_mo_lai_lan_hai_khong_chuyen_lai(tmp_path):
    (tmp_path / "config.json").write_text(
        json.dumps({"providers": {"openai": {"api_key": "sk-x"}}}), encoding="utf-8")
    secrets = FakeSecretStore()
    _repo(tmp_path, secrets)
    so_ban_sao = len(list(tmp_path.glob("*.bak")))

    _repo(tmp_path, secrets)
    assert len(list(tmp_path.glob("*.bak"))) == so_ban_sao, "không nâng cấp lại"


def test_save_luon_ghi_so_phien_ban(tmp_path):
    cfg = _repo(tmp_path)
    cfg.save()
    raw = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert raw["schema_version"] == CURRENT_VERSION
