"""Ghi lại mọi lần app chết hoặc treo, và báo "Đang xử lý…" khi giao diện đứng.

Trước đây app văng ra (mã 0xC0000409) mà không để lại dấu vết gì: lỗi ở tầng
native không in traceback Python, còn cửa sổ console thì đóng ngay theo app. Mô-đun
này ghi mọi thứ vào ``~/.cowork_local/logs/``:

* ``crash.log``: stack của mọi luồng lúc tiến trình chết (``faulthandler``), kèm
  exception Python không ai bắt, ở luồng chính lẫn luồng nền. Exception Python
  chỉ được ghi lại, app vẫn chạy tiếp.
* ``qt.log``: cảnh báo, lỗi và lỗi nghiêm trọng của Qt (cũng vẫn in ra console).
* ``hang.log``: stack của mọi luồng mỗi khi luồng giao diện đứng quá
  ``HANG_SECONDS`` giây, để biết app đang kẹt ở dòng nào.

Luồng giao diện đang đứng thì không thể tự vẽ popup, nên popup "Đang xử lý…" do một
luồng canh riêng mở bằng hộp thoại gốc của Windows. Giao diện chạy lại thì hộp
thoại tự đóng.
"""
from __future__ import annotations

import datetime
import faulthandler
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer, QtMsgType, qInstallMessageHandler

HANG_SECONDS = 5.0       # luồng giao diện đứng quá ngần này giây thì coi là treo
_BEAT_MS = 500           # nhịp luồng giao diện báo "vẫn sống"

_crash_file = None       # giữ file mở suốt đời app: faulthandler ghi vào lúc chết
_log_dir: Optional[Path] = None


def _stamp() -> str:
    """Mốc giờ hiện tại, dùng làm tiêu đề mỗi mục trong log."""
    return datetime.datetime.now().isoformat(timespec="seconds")


def _append(name: str, text: str) -> None:
    """Ghi thêm vào một file log. Ghi log hỏng thì bỏ qua, không kéo app theo."""
    if _log_dir is None:
        return
    try:
        with open(_log_dir / name, "a", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        pass


def _log_exception(where: str, exc_type, exc, tb) -> None:
    """Ghi một exception không ai bắt vào crash.log và in ra console."""
    body = "".join(traceback.format_exception(exc_type, exc, tb))
    _append("crash.log", f"\n=== {_stamp()} exception chưa bắt ({where}) ===\n{body}")
    if sys.__stderr__:
        sys.__stderr__.write(body)


def _qt_message(mode, context, message) -> None:
    """Chuyển thông báo của Qt vào qt.log, vẫn in ra console như trước."""
    level = {QtMsgType.QtWarningMsg: "WARNING", QtMsgType.QtCriticalMsg: "CRITICAL",
             QtMsgType.QtFatalMsg: "FATAL"}.get(mode)
    if sys.__stderr__:
        sys.__stderr__.write(message + "\n")
    if level is None:
        return                      # debug/info: chỉ in, không ghi file
    _append("qt.log", f"{_stamp()} {level}: {message}\n")
    if mode == QtMsgType.QtFatalMsg and _crash_file is not None:
        faulthandler.dump_traceback(_crash_file, all_threads=True)


def install(log_dir: Path) -> None:
    """Bật ghi log crash. Gọi một lần, sớm nhất có thể sau khi có QApplication."""
    global _crash_file, _log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    _log_dir = log_dir
    _crash_file = open(log_dir / "crash.log", "a", encoding="utf-8")  # noqa: SIM115
    _crash_file.write(f"\n=== {_stamp()} app khởi động ===\n")
    _crash_file.flush()
    faulthandler.enable(file=_crash_file, all_threads=True)
    sys.excepthook = lambda t, e, tb: _log_exception("luồng chính", t, e, tb)
    threading.excepthook = lambda a: _log_exception(
        f"luồng {a.thread.name if a.thread else '?'}", a.exc_type, a.exc_value, a.exc_traceback)
    qInstallMessageHandler(_qt_message)


class HangWatchdog:
    """Canh luồng giao diện: đứng quá ``HANG_SECONDS`` giây thì ghi stack vào
    hang.log và mở popup "Đang xử lý…", chạy lại thì đóng popup.

    Luồng giao diện đều đặn cập nhật nhịp qua một ``QTimer``; một luồng nền kiểm tra
    nhịp đó. Luồng nền không đụng vào widget Qt nào.
    """

    def __init__(self, title: str, parent=None) -> None:
        self._title = title
        self._last_beat = time.monotonic()
        self._timer = QTimer(parent)
        self._timer.timeout.connect(self._beat)
        self._timer.start(_BEAT_MS)
        self._stop = threading.Event()
        self._popup: Optional[threading.Thread] = None
        self._popup_title = title
        threading.Thread(target=self._watch, name="hang-watchdog", daemon=True).start()

    def stop(self) -> None:
        """Dừng canh (khi app thoát)."""
        self._stop.set()
        self._timer.stop()

    def _beat(self) -> None:
        self._last_beat = time.monotonic()

    def _watch(self) -> None:
        stalled = False
        while not self._stop.wait(0.5):
            lag = time.monotonic() - self._last_beat
            if lag >= HANG_SECONDS and not stalled:
                stalled = True
                self._dump_stacks(lag)
                self._show_popup()
            elif lag < HANG_SECONDS and stalled:
                stalled = False
                self._close_popup()

    def _dump_stacks(self, lag: float) -> None:
        if _log_dir is None:
            return
        try:
            with open(_log_dir / "hang.log", "a", encoding="utf-8") as f:
                f.write(f"\n=== {_stamp()} giao diện đứng {lag:.1f}s ===\n")
                f.flush()
                faulthandler.dump_traceback(f, all_threads=True)
        except OSError:
            pass

    def _show_popup(self) -> None:
        if sys.platform != "win32":
            return
        import ctypes

        from ...i18n import tr

        # Đọc chữ NGAY LÚC hiện popup: luôn khớp ngôn ngữ đang chọn trong app,
        # kể cả khi người dùng vừa đổi ngôn ngữ.
        title, message = self._title, tr("app.hang.message")
        # MB_ICONINFORMATION | MB_TOPMOST | MB_SETFOREGROUND. MessageBoxW có vòng
        # thông điệp riêng trên luồng này, nên hiện được dù luồng giao diện đang đứng.
        flags = 0x40 | 0x40000 | 0x10000
        self._popup_title = title
        self._popup = threading.Thread(
            target=lambda: ctypes.windll.user32.MessageBoxW(None, message, title, flags),
            name="hang-popup", daemon=True)
        self._popup.start()

    def _close_popup(self) -> None:
        if self._popup is None or sys.platform != "win32":
            return
        import ctypes

        user32 = ctypes.windll.user32
        for _ in range(10):   # hộp thoại có thể chưa kịp hiện ra
            hwnd = user32.FindWindowW(None, self._popup_title)
            if hwnd:
                user32.PostMessageW(hwnd, 0x0010, 0, 0)   # WM_CLOSE
                break
            time.sleep(0.05)
        self._popup = None
