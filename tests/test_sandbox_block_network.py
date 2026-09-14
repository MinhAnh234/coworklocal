"""Công tắc "Chặn mạng cho lệnh do agent chạy" phải chặn MỌI đường ra mạng của
agent, không riêng ``run_command``.

Trước đây ``block_network`` chỉ được đọc ở đúng một chỗ —
``infrastructure/filesystem/command_tools.py`` trong ``run_command`` — nên bốn
tool mang ``ToolCapability.NETWORK`` (``fetch_url``, ``jira_search``,
``jira_get_issue``, ``install_package``) vẫn ra internet bình thường trong khi
màn Monitoring báo "Mạng: Bị chặn" và docstring của ``fetch_tools`` tự nhận là
*"Honors the Sandbox Security Layer's Block network policy"*. Người dùng bật
công tắc rồi thấy agent vẫn search web được — đúng triệu chứng được báo.

Hai nhóm bài:

* **hành vi** — bật thì mọi tool NETWORK từ chối TRƯỚC khi chạm mạng, tắt thì
  đường cũ giữ nguyên (chặn một chiều là hỏng tính năng);
* **guardrail** — thêm tool mạng mới mà quên chặn thì bài ở đây đỏ ngay.
"""
from __future__ import annotations

from typing import Dict

import pytest

from cowork_local.core.tools import ToolContext
from cowork_local.domain.tools import BUILT_IN_CAPABILITIES, ToolCapability
from cowork_local.infrastructure.filesystem import command_tools, fetch_tools

# tên tool -> (handler, args hợp lệ tối thiểu). Args phải hợp lệ, nếu không bài
# test sẽ đỏ vì lỗi thiếu tham số chứ không vì cổng chặn mạng.
_TOOL_MANG: Dict[str, tuple] = {
    "fetch_url": (fetch_tools.fetch_url, {"url": "https://example.com/"}),
    "jira_search": (fetch_tools.jira_search, {"jql": "project = ABC"}),
    "jira_get_issue": (fetch_tools.jira_get_issue, {"key": "ABC-1"}),
    "install_package": (command_tools.install_package, {"package": "requests"}),
}


@pytest.fixture
def cam_ra_mang(monkeypatch):
    """Mọi đường ra mạng thật đều nổ.

    Vừa giữ cho bộ test không chạm internet, vừa làm lộ tool nào lọt qua cổng
    chặn: nó sẽ đỏ ngay tại lời gọi mạng thay vì im lặng đi ra ngoài.
    """
    def no_ra_mang(*args, **kwargs):
        raise AssertionError("tool đã chạm mạng dù 'Chặn mạng' đang bật")

    from cowork_local.core import deps, jira_tool, link_fetch

    monkeypatch.setattr(link_fetch, "fetch_link_preview", no_ra_mang)
    monkeypatch.setattr(jira_tool, "search", no_ra_mang)
    monkeypatch.setattr(jira_tool, "get_issue", no_ra_mang)
    monkeypatch.setattr(jira_tool, "get_issue_by_url", no_ra_mang)
    monkeypatch.setattr(deps, "pip_install", no_ra_mang)


# ---- hành vi: bật công tắc thì mọi tool mạng đều bị chặn -----------------

@pytest.mark.parametrize("ten", sorted(_TOOL_MANG))
def test_bat_chan_mang_thi_tool_tu_choi_truoc_khi_cham_mang(tmp_path, cam_ra_mang, ten):
    """Đây là chính triệu chứng người dùng báo: bật rồi mà vẫn ra được web."""
    handler, args = _TOOL_MANG[ten]
    ctx = ToolContext(tmp_path, block_network=True)

    ket_qua = handler(ctx, args)

    assert ket_qua["ok"] is False, f"{ten} vẫn chạy khi đang chặn mạng"
    assert "Sandbox Security Layer" in ket_qua["output"], ket_qua["output"]


def test_allow_url_fetch_khong_lach_duoc_chan_mang(tmp_path, cam_ra_mang):
    """Hai công tắc vẫn độc lập, nhưng "Chặn mạng" là cái mạnh hơn: bật nó thì
    "Cho phép agent lấy dữ liệu từ URL" không mở lại đường được."""
    ctx = ToolContext(tmp_path, block_network=True, allow_url_fetch=True)

    ket_qua = fetch_tools.fetch_url(ctx, {"url": "https://example.com/"})

    assert ket_qua["ok"] is False


# ---- hành vi: tắt công tắc thì đường cũ giữ nguyên -----------------------

def test_tat_chan_mang_thi_fetch_url_van_doc_duoc(tmp_path, monkeypatch):
    """Chặn một chiều là hỏng tính năng — cổng phải mở lại được."""
    from cowork_local.core import link_fetch

    monkeypatch.setattr(link_fetch, "fetch_link_preview",
                        lambda url: f"nội dung của {url}")
    ctx = ToolContext(tmp_path, block_network=False)

    ket_qua = fetch_tools.fetch_url(ctx, {"url": "https://example.com/"})

    assert ket_qua["ok"] is True
    assert "example.com" in ket_qua["output"]


def test_tat_chan_mang_thi_install_package_van_chay(tmp_path, monkeypatch):
    from cowork_local.core import deps

    da_goi = []

    def gia_lap_pip(package, **kwargs):
        da_goi.append(package)
        return True, "ok"

    monkeypatch.setattr(deps, "pip_install", gia_lap_pip)
    ctx = ToolContext(tmp_path, block_network=False)

    ket_qua = command_tools.install_package(ctx, {"package": "requests"})

    assert da_goi == ["requests"]
    assert ket_qua["ok"] is True


# ---- guardrail: danh sách tool mạng không được lệch ----------------------

def test_moi_tool_mang_deu_co_bai_o_day():
    """``BUILT_IN_CAPABILITIES`` là nơi duy nhất khai báo tool nào chạm mạng.
    Thêm một tool NETWORK mới mà quên chặn thì bài này đỏ ngay."""
    tag_mang = {ten for ten, cap in BUILT_IN_CAPABILITIES.items()
                if cap & ToolCapability.NETWORK}

    assert tag_mang == set(_TOOL_MANG), (
        "danh sách tool mạng đã đổi — chặn tool mới ở cổng block_network "
        "rồi bổ sung vào _TOOL_MANG")
