"""crash_guard ghi lại exception chưa bắt và phát hiện giao diện bị treo."""
from __future__ import annotations

import os
import threading
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from cowork_local.presentation.shell import crash_guard  # noqa: E402


@pytest.fixture
def qt_app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def guard(tmp_path, monkeypatch):
    import faulthandler
    import sys

    from PySide6.QtCore import qInstallMessageHandler

    monkeypatch.setattr(sys, "excepthook", sys.excepthook)
    monkeypatch.setattr(threading, "excepthook", threading.excepthook)
    crash_guard.install(tmp_path)
    yield tmp_path
    qInstallMessageHandler(None)
    faulthandler.disable()
    crash_guard._crash_file.close()
    crash_guard._crash_file = None
    crash_guard._log_dir = None


def test_uncaught_thread_exception_is_logged_not_fatal(guard):
    def boom():
        raise ValueError("lỗi luồng nền")

    t = threading.Thread(target=boom, name="worker-x")
    t.start()
    t.join()
    log = (guard / "crash.log").read_text(encoding="utf-8")
    assert "ValueError: lỗi luồng nền" in log
    assert "worker-x" in log


def test_watchdog_dumps_stacks_and_pops_up_while_gui_is_stalled(guard, qt_app, monkeypatch):
    monkeypatch.setattr(crash_guard, "HANG_SECONDS", 0.6)
    events = []
    monkeypatch.setattr(crash_guard.HangWatchdog, "_show_popup", lambda self: events.append("show"))
    monkeypatch.setattr(crash_guard.HangWatchdog, "_close_popup", lambda self: events.append("close"))
    dog = crash_guard.HangWatchdog("t")
    try:
        qt_app.processEvents()
        time.sleep(1.5)                       # luồng giao diện "đứng"
        assert events == ["show"]
        end = time.time() + 2
        while "close" not in events and time.time() < end:
            qt_app.processEvents()             # giao diện chạy lại
            time.sleep(0.05)
        assert events == ["show", "close"]
    finally:
        dog.stop()
    assert "giao diện đứng" in (guard / "hang.log").read_text(encoding="utf-8")


@pytest.mark.parametrize("lang, expected", [
    ("vi", "Đang xử lý"), ("en", "Processing"), ("ja", "処理中"),
])
def test_popup_text_follows_the_current_app_language(qt_app, monkeypatch, lang, expected):
    import sys
    import types

    from cowork_local.i18n import get_language, set_language

    shown = []
    fake_user32 = types.SimpleNamespace(MessageBoxW=lambda h, msg, title, f: shown.append(msg))
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "ctypes", types.SimpleNamespace(
        windll=types.SimpleNamespace(user32=fake_user32)))
    before = get_language()
    dog = crash_guard.HangWatchdog("t")
    try:
        set_language(lang)
        dog._show_popup()
        dog._popup.join(1)
    finally:
        dog.stop()
        set_language(before)
    assert shown and expected in shown[0]
