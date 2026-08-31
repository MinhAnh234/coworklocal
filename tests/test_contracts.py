"""Hợp đồng của mục chung có thật sự gỡ chốt cho N2 và N3 không.

Đây là bài nghiệm thu, không phải test cho vui: nếu ba bài dưới đây xanh thì
hai nhánh kia code được ngay hôm nay mà không cần chờ ``ConfigRepository`` hay
``KeyringAdapter`` bản thật.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from cowork_local.infrastructure.config.config_repository import ConfigRepository
from cowork_local.infrastructure.secrets.secret_store import SecretStore, provider_key
from cowork_local.tests.fakes.fake_config import FakeConfigRepository, FakeSecretStore

REPO_PARENT = Path(__file__).resolve().parents[2]


def test_fake_config_khop_hop_dong():
    """Fake phải cài đủ interface — thiếu một hàm là hai nhánh kia gọi vào sẽ vỡ."""
    assert isinstance(FakeConfigRepository(), ConfigRepository)


def test_fake_secret_store_khop_hop_dong():
    assert isinstance(FakeSecretStore(), SecretStore)


def test_secret_store_thieu_key_thi_tra_none_chu_khong_nem_loi():
    """Thiếu API key là chuyện thường (người dùng chưa nhập), không phải sự cố."""
    store = FakeSecretStore()
    assert store.get(provider_key("openai")) is None
    assert store.has(provider_key("openai")) is False
    store.delete(provider_key("openai"))       # xoá cái không có: im lặng

    store.set(provider_key("openai"), "sk-test")
    assert store.get(provider_key("openai")) == "sk-test"
    assert store.has(provider_key("openai")) is True


def test_config_gia_ghi_nhan_save_ma_khong_cham_dia():
    cfg = FakeConfigRepository(theme="light")
    assert cfg.theme == "light"
    cfg.set_theme("dark")
    cfg.save()
    assert cfg.theme == "dark"
    assert cfg.saves == 1


def test_bat_duoc_tool_bi_tat():
    cfg = FakeConfigRepository(tools_disabled=["run_command"])
    assert cfg.tools_disabled == ["run_command"]
    cfg.set_tool_enabled("run_command", True)
    assert cfg.tools_disabled == []
    cfg.set_tool_enabled("write_file", False)
    assert cfg.tools_disabled == ["write_file"]


def test_dung_duoc_fake_ma_khong_hề_nap_config_that():
    """Bài nghiệm thu chính của mục chung.

    N2 và N3 phải dựng được màn hình và chạy test của mình mà KHÔNG kéo theo
    ``cowork_local.config`` — module nặng, đọc đĩa, và đang bị N1 viết lại.
    Kiểm bằng tiến trình riêng để không dính module đã nạp sẵn ở test khác.
    """
    snippet = (
        "import sys\n"
        "from cowork_local.tests.fakes.fake_config import "
        "FakeConfigRepository, FakeSecretStore\n"
        "cfg = FakeConfigRepository(active_provider='openai')\n"
        "assert cfg.provider_conf()['model'] == 'gpt-4o-mini'\n"
        "assert FakeSecretStore().get('x') is None\n"
        "assert 'cowork_local.config' not in sys.modules, "
        "'fake keo theo config that -> van con phu thuoc'\n"
        "assert 'PySide6' not in sys.modules, 'fake keo theo Qt -> test se cham'\n"
        "print('OK')\n"
    )
    out = subprocess.run([sys.executable, "-c", snippet], cwd=REPO_PARENT,
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert "OK" in out.stdout


# ---------------------------------------------------------------------------
# ToolPolicyGateway — bản đề xuất Gamma viết hộ, chờ Team Hoa xác nhận.
# N3 (Co4E) code dựa vào đây từ hôm nay thay vì tự phỏng đoán.
# ---------------------------------------------------------------------------

from cowork_local.domain.security.tool_policy import (  # noqa: E402
    PolicyOutcome, ToolCallRequest, ToolPolicyGateway, allow, ask, deny,
)
from cowork_local.tests.fakes.fake_tool_policy import (  # noqa: E402
    FakeToolPolicyGateway,
)


def test_fake_gateway_khop_hop_dong():
    assert isinstance(FakeToolPolicyGateway(), ToolPolicyGateway)


def test_mac_dinh_cho_qua_va_co_ghi_lai_da_hoi():
    gate = FakeToolPolicyGateway()
    d = gate.check(ToolCallRequest(name="read_file", surface="co4e"))
    assert d.outcome is PolicyOutcome.ALLOW
    assert d.allowed is True
    assert gate.asked_for("read_file")
    assert gate.call_count == 1


def test_chan_theo_ten_tool():
    gate = FakeToolPolicyGateway(rules={"run_command": deny("cấm trong Co4E")})
    assert gate.check(ToolCallRequest(name="run_command")).outcome is PolicyOutcome.DENY
    assert gate.check(ToolCallRequest(name="read_file")).allowed is True


def test_ask_khong_phai_la_duoc_phep():
    """Bẫy dễ mắc nhất: coi ASK như ALLOW thì tool chạy mà chưa ai đồng ý."""
    d = ask("cần người dùng xác nhận")
    assert d.outcome is PolicyOutcome.ASK
    assert d.allowed is False


def test_deny_va_ask_bat_buoc_co_ly_do():
    """Người dùng phải biết vì sao bị chặn, và audit log cần ghi lại."""
    import pytest

    with pytest.raises(ValueError):
        deny("")
    with pytest.raises(ValueError):
        ask("")
    allow()          # ALLOW thì không cần lý do


def test_chinh_sach_khac_nhau_theo_man():
    """Co4E chạy nền nên không bật được hộp thoại — chặn thẳng thay vì hỏi."""
    def by_surface(req: ToolCallRequest):
        if req.surface == "co4e" and req.name == "run_command":
            return deny("Co4E chạy nền, không hỏi được người dùng")
        return ask("cần xác nhận") if req.name == "run_command" else allow()

    gate = FakeToolPolicyGateway(decide=by_surface)
    assert gate.check(ToolCallRequest("run_command", surface="co4e")).outcome is PolicyOutcome.DENY
    assert gate.check(ToolCallRequest("run_command", surface="cowork")).outcome is PolicyOutcome.ASK
