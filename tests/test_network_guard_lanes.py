"""Công tắc "Chặn mạng" phải chặn mọi đường ra mạng của app, TRỪ nhà cung cấp AI.

Bản đồ ``infura/network-map.html`` liệt kê các làn trước đây "không kiểm soát"
hoặc chỉ chặn một phần: M365, Teams và nút Test, connector/MCP đang chạy,
task script và link đính kèm task, tự cài thư viện, xem trước HTML, lệnh shell
chỉ bị proxy giả. Mỗi làn có ít nhất một bài ở đây:

* **bật** — làn từ chối TRƯỚC khi chạm mạng (mọi lời gọi HTTP thật đều nổ);
* **tắt** — đường cũ giữ nguyên, vì chặn một chiều là hỏng tính năng.
"""
from __future__ import annotations

import socket
import sys
import threading
from pathlib import Path

import pytest

from cowork_local.application.network import network_guard


def _no_network(*args, **kwargs):
    raise AssertionError("đã chạm mạng dù 'Chặn mạng' đang bật")


@pytest.fixture
def chan_mang(monkeypatch):
    """Bật công tắc qua cổng chung và làm nổ mọi lời gọi HTTP thật."""
    import requests

    from cowork_local.core import tls_trust

    for name in ("request", "get", "post", "put", "patch", "delete"):
        monkeypatch.setattr(requests, name, _no_network)
    monkeypatch.setattr(tls_trust, "request", _no_network)
    monkeypatch.setattr(tls_trust, "request_any_method", _no_network)
    network_guard.bind(lambda: True)
    yield
    network_guard.bind(None)


@pytest.fixture(autouse=True)
def _go_cong_sau_moi_bai():
    yield
    network_guard.bind(None)


# ---- cổng chung ------------------------------------------------------------

def test_chua_noi_day_thi_khong_chan():
    network_guard.bind(None)
    assert network_guard.is_blocked() is False
    network_guard.ensure_allowed("x")


def test_doc_cong_tac_loi_thi_coi_nhu_dang_chan():
    """Không đọc được công tắc thì đóng cửa, không mở toang."""
    def hong():
        raise KeyError("agent_security")

    network_guard.bind(hong)
    with pytest.raises(network_guard.NetworkBlockedError):
        network_guard.ensure_allowed("Teams")


def test_cong_doc_cau_hinh_song_khong_chup_lai(tmp_path):
    """Đổi công tắc trong Settings có hiệu lực ngay, không cần mở lại app."""
    from cowork_local.presentation.shell.bootstrap import build_context

    ctx = build_context(tmp_path / "config.json")
    ctx.config.agent_security["block_network"] = True
    assert network_guard.is_blocked() is True
    ctx.config.agent_security["block_network"] = False
    assert network_guard.is_blocked() is False


# ---- Microsoft 365 -----------------------------------------------------------

def test_graph_tu_choi_bang_loi_ma_noi_goi_da_bat(chan_mang):
    from cowork_local.core import ms365_graph

    with pytest.raises(ms365_graph.Ms365GraphError, match="Sandbox Security Layer"):
        ms365_graph.list_onedrive_files("token")


def test_dang_nhap_va_lay_token_tu_choi(chan_mang, monkeypatch):
    from cowork_local.core import ms365_auth

    monkeypatch.setattr(ms365_auth, "_app", _no_network)
    with pytest.raises(ms365_auth.Ms365AuthError, match="blocked"):
        ms365_auth.get_access_token("", "")
    with pytest.raises(ms365_auth.Ms365AuthError, match="blocked"):
        ms365_auth.sign_in_device_code("", "", lambda flow: None)


def test_kiem_tra_da_dang_nhap_khong_dung_msal_khi_chan(chan_mang, monkeypatch):
    """Dựng app MSAL là tải cấu hình OpenID của tenant — phải đọc kho token trực tiếp."""
    from cowork_local.core import ms365_auth

    monkeypatch.setattr(ms365_auth, "_app", _no_network)
    monkeypatch.setattr(ms365_auth, "_cached_account_offline",
                        lambda: {"username": "a@b.c"})
    assert ms365_auth.signed_in_account("", "") == {"username": "a@b.c"}


def test_mail_canh_bao_khong_gui_khi_chan(chan_mang, monkeypatch):
    from types import SimpleNamespace

    from cowork_local.core import agent_security_alert, ms365_auth
    from cowork_local.core.agent_security_types import SecurityVerdict

    monkeypatch.setattr(ms365_auth, "_app", _no_network)
    config = SimpleNamespace(data={"agent_security": {"admin_email": "admin@x.y"}}, ms365={})
    verdict = SecurityVerdict(allowed=False, layer="command", reason="test")
    sent, note = agent_security_alert.notify_admin(config, verdict)
    assert sent is False
    assert "blocked" in note


# ---- Teams, connector REST, Jira, nút Test ---------------------------------

def test_teams_tu_choi(chan_mang):
    from cowork_local.core.teams import TeamsNotifier

    ok, detail = TeamsNotifier("https://x.webhook.office.com/hook").send("t", "b")
    assert ok is False
    assert "blocked" in detail


def test_connector_rest_va_nut_test_tu_choi(chan_mang):
    from cowork_local.core.ext_connectors import RestApiConnector

    rc = RestApiConnector({"id": "erp", "name": "ERP", "base_url": "https://erp.example"})
    assert rc.call({"method": "GET", "path": "items"})["ok"] is False
    ok, message = rc.test_connection()
    assert ok is False and "blocked" in message


def test_nut_test_jira_tu_choi(chan_mang):
    from cowork_local.core import jira_tool

    cfg = {"base_url": "https://jira.example", "email": "a@b.c", "api_token": "t"}
    out = jira_tool.search(cfg, "order by created DESC", 1)
    assert out.startswith("Jira search failed") and "blocked" in out


# ---- MCP -------------------------------------------------------------------

def test_mcp_khong_khoi_dong_va_khong_goi_khi_chan(chan_mang):
    from cowork_local.core.mcp_client import McpServerConnection, McpServerError

    conn = McpServerConnection("srv", "definitely-not-run")
    with pytest.raises(McpServerError, match="blocked"):
        conn.start(timeout=1)
    assert conn.call_tool("srv__search", {})["ok"] is False


def _context(tmp_path, block: bool):
    from cowork_local.config import AppConfig
    from cowork_local.state import AppContext

    ctx = AppContext(AppConfig.load(tmp_path / "config.json"))
    ctx.config.agent_security["block_network"] = block
    return ctx


def test_chuan_bi_connector_dung_mcp_dang_chay_va_giu_onedrive_cuc_bo(tmp_path, monkeypatch):
    from cowork_local.core import ms365_local

    ctx = _context(tmp_path, block=True)
    stopped = []
    monkeypatch.setattr(ctx, "stop_mcp_connections", lambda: stopped.append(True))
    local = (["ms365_local__onedrive_list"], object())
    monkeypatch.setattr(ms365_local, "build_ms365_local_tools", lambda config: local)
    monkeypatch.setattr(ctx._mcp_manager, "ensure", _no_network)

    assert ctx.build_mcp_tools() == local
    assert stopped == [True]


# ---- task lập lịch -----------------------------------------------------------

def test_link_dinh_kem_task_khong_tai(chan_mang):
    from cowork_local.core.tasks import resolve_input_text

    text = resolve_input_text({"input": {"mode": "empty", "links": ["https://example.com/a"]}})
    assert "not fetched" in text


def test_task_script_chay_trong_tien_trinh_khong_mang(chan_mang, monkeypatch, tmp_path):
    from cowork_local.core import deps, task_script

    calls = []

    def fake_run(command, **kwargs):
        calls.append(kwargs)
        return 0, "done", False, False, False

    monkeypatch.setattr(deps, "run_cancellable", fake_run)
    assert task_script.run_script("echo hi", tmp_path, 30) == "done"
    assert calls and calls[0]["isolate_network"] is True


def test_task_script_khong_co_lap_duoc_thi_khong_chay(chan_mang, monkeypatch, tmp_path):
    from cowork_local.core import deps, task_script

    monkeypatch.setattr(deps, "run_cancellable",
                        lambda command, **kw: (None, "no AppContainer", False, False, False))
    with pytest.raises(RuntimeError, match="could not be isolated"):
        task_script.run_script("echo hi", tmp_path, 30)


def test_tat_chan_mang_thi_task_script_chay_nhu_cu(tmp_path):
    from cowork_local.core import task_script

    assert "hi" in task_script.run_script("echo hi", tmp_path, 30)


# ---- tự cài thư viện ---------------------------------------------------------

def test_khong_tu_cai_thu_vien_khi_chan(chan_mang, monkeypatch):
    from cowork_local.core import deps

    monkeypatch.setattr(deps, "run_cancellable", _no_network)
    assert deps.ensure_module("khong_ton_tai_xyz_123") is None
    assert "khong_ton_tai_xyz_123" not in deps._FAILED   # thử lại khi mở mạng
    ok, detail = deps.pip_install("requests")
    assert ok is False and "blocked" in detail


def test_pptx_khong_bi_nho_la_thieu_khi_chi_do_chan_mang(chan_mang, monkeypatch):
    from cowork_local.application.workspaces import file_preview_helpers as fph
    from cowork_local.core import deps

    monkeypatch.setattr(fph, "_PPTX_READY", None)
    monkeypatch.setattr(deps, "ensure_module", lambda *a, **k: None)
    assert fph.pptx_available() is False
    assert fph._PPTX_READY is None


# ---- lệnh shell của agent ----------------------------------------------------

@pytest.mark.parametrize("backend", ["direct", "integrity_job_wfp", "appcontainer", "windows_sandbox"])
def test_moi_backend_deu_chay_co_lap_mang(monkeypatch, tmp_path, backend):
    """Các backend cũ chỉ đặt biến proxy — khi chặn mạng, tất cả đi qua lớp cô lập của OS."""
    from cowork_local.core import deps
    from cowork_local.core.sandbox_manager import SandboxManager

    calls = []

    def fake_run(command, **kwargs):
        calls.append(kwargs)
        return 0, "ok", False, False, False

    monkeypatch.setattr(deps, "run_cancellable", fake_run)
    result = SandboxManager()._execute_with_backend(backend, "echo hi", str(tmp_path), True, 30)
    assert calls and calls[0]["isolate_network"] is True
    assert result["ok"] is True and result["sandbox"] == "network_isolated"


def test_lenh_khong_co_lap_duoc_thi_bi_tu_choi(monkeypatch, tmp_path):
    from cowork_local.core import deps
    from cowork_local.core.sandbox_manager import SandboxManager

    monkeypatch.setattr(deps, "run_cancellable",
                        lambda command, **kw: (None, "no isolation", False, False, False))
    result = SandboxManager()._execute_with_backend("direct", "echo hi", str(tmp_path), True, 30)
    assert result["ok"] is False and result["sandbox"] == "blocked"


def test_he_dieu_hanh_khong_ho_tro_thi_bao_loi_khong_chay(monkeypatch):
    from cowork_local.infrastructure.sandbox import network_isolation

    monkeypatch.setattr(network_isolation.sys, "platform", "sunos5")
    with pytest.raises(network_isolation.NetworkIsolationUnavailable):
        network_isolation.spawn_without_network("echo hi", None, None)


def _listening_socket():
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(4)
    def serve():
        try:
            for _ in range(4):
                server.accept()
        except OSError:
            pass   # socket closed at the end of the test

    threading.Thread(target=serve, daemon=True).start()
    return server


@pytest.mark.skipif(sys.platform != "win32", reason="AppContainer chỉ có trên Windows")
def test_appcontainer_that_su_cat_mang_nhung_van_ghi_duoc_thu_muc(tmp_path):
    """Bài thật, không giả lập: cùng một lệnh Python nối tới một cổng đang nghe,
    ngoài sandbox thì được, trong sandbox thì bị kernel từ chối."""
    from cowork_local.core.deps import run_cancellable

    server = _listening_socket()
    port = server.getsockname()[1]
    probe = (f'"{sys.executable}" -c "import socket;'
             "print('PYTHON'+'_RAN');"
             f"socket.create_connection(('127.0.0.1',{port}),5);print('CONN'+'ECTED')\"")
    try:
        rc, out, *_ = run_cancellable(probe, cwd=str(tmp_path), timeout=60, shell=True)
        assert rc == 0 and "CONNECTED" in out

        rc, out, *_ = run_cancellable(probe + " & echo written> marker.txt",
                                      cwd=str(tmp_path), timeout=60, isolate_network=True)
        assert "PYTHON_RAN" in out, out          # Python itself starts in the sandbox
        assert "CONNECTED" not in out, out
        assert (Path(tmp_path) / "marker.txt").read_text().strip() == "written"
    finally:
        server.close()


# ---- xem trước HTML ------------------------------------------------------------

class _FakeUrl:
    def __init__(self, scheme):
        self._scheme = scheme

    def scheme(self):
        return self._scheme


class _FakeRequest:
    def __init__(self, scheme):
        self._url = _FakeUrl(scheme)
        self.blocked = False

    def requestUrl(self):  # noqa: N802 - Qt name
        return self._url

    def block(self, flag):
        self.blocked = flag


@pytest.mark.parametrize("scheme,expected", [
    ("https", True), ("http", True), ("wss", True), ("file", False), ("data", False),
])
def test_xem_truoc_html_chan_tai_nguyen_web(chan_mang, scheme, expected):
    pytest.importorskip("PySide6.QtWebEngineCore")
    from cowork_local.presentation.folder.offline_web_page import RemoteRequestBlocker

    req = _FakeRequest(scheme)
    RemoteRequestBlocker().interceptRequest(req)
    assert req.blocked is expected


def test_xem_truoc_html_tai_binh_thuong_khi_tat():
    pytest.importorskip("PySide6.QtWebEngineCore")
    from cowork_local.presentation.folder.offline_web_page import RemoteRequestBlocker

    req = _FakeRequest("https")
    RemoteRequestBlocker().interceptRequest(req)
    assert req.blocked is False


@pytest.mark.skipif(sys.platform != "win32", reason="AppContainer chỉ có trên Windows")
def test_khong_cap_quyen_ke_thua_len_thu_muc_chua_qt(tmp_path, monkeypatch):
    """Quyền AppContainer kế thừa xuống Qt6WebEngineCore.dll làm tiến trình render
    của WebEngine không nạp được DLL — tab Graph và xem trước HTML trắng trơn."""
    from cowork_local.infrastructure.sandbox import appcontainer_process as ac

    qt_dir = tmp_path / "venv" / "Lib" / "site-packages" / "PySide6"
    qt_dir.mkdir(parents=True)
    monkeypatch.setattr(ac, "_qt_package_dir", lambda: str(qt_dir))
    monkeypatch.setattr(ac, "_icacls", _no_network)

    with pytest.raises(ac.NetworkIsolationUnavailable, match="Qt runtime"):
        ac.grant_access(str(tmp_path / "venv"), "S-1-15-2-1", "read")
    with pytest.raises(ac.NetworkIsolationUnavailable, match="Qt runtime"):
        ac.grant_access(str(tmp_path), "S-1-15-2-1", "write")


def test_quyen_cho_python_khong_bao_gio_phu_len_thu_vien_qt(monkeypatch, tmp_path):
    from cowork_local.infrastructure.sandbox import appcontainer_process as ac

    venv, base = tmp_path / "venv", tmp_path / "base"
    monkeypatch.setattr(ac.sys, "prefix", str(venv))
    monkeypatch.setattr(ac.sys, "base_prefix", str(base))
    for qt_dir in (venv / "Lib" / "site-packages" / "PySide6",
                   base / "Lib" / "site-packages" / "PySide6"):
        monkeypatch.setattr(ac, "_qt_package_dir", lambda d=qt_dir: str(d))
        for folder, mode in ac._interpreter_grants():
            assert mode == "read_here" or not ac._covers(folder, str(qt_dir)), (folder, mode)
