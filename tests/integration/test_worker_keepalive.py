"""Luồng nền đang chạy không bao giờ bị dọn rác giữa chừng.

Qt coi "QThread: Destroyed while thread is still running" là lỗi FATAL và huỷ cả
app (mã 0xC0000409). Chỗ gọi thường chỉ giữ worker mới nhất (``self._worker =
w``): bấm chuyển tab nhanh qua GraphRAG khởi động lượt quét này tới lượt quét
khác, worker cũ còn đang chạy mất tham chiếu và app văng.

Nếu bản sửa hỏng, test này làm văng chính tiến trình pytest — ồn ào, nhưng không
thể bị bỏ qua.
"""
from __future__ import annotations

import gc
import os
import threading
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from cowork_local.core.worker import AgentWorker  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _pump_until(app, cond, timeout=3.0):
    end = time.time() + timeout
    while not cond() and time.time() < end:
        app.processEvents()
        time.sleep(0.01)
    return cond()


def test_dropped_running_worker_survives_gc_and_finishes(qt_app):
    release = threading.Event()
    results = []

    def job(_w):
        release.wait(2)
        return {"ok": True}

    w = AgentWorker(job)
    w.finished_ok.connect(results.append)
    w.start()
    del w                                # người gọi thay bằng worker mới
    gc.collect()                         # trước đây: FATAL, app văng
    assert len(AgentWorker._running) >= 1
    release.set()
    assert _pump_until(qt_app, lambda: results == [{"ok": True}])
    assert _pump_until(qt_app, lambda: not AgentWorker._running)   # thả ra sau khi xong


def test_replacing_the_worker_repeatedly_is_safe(qt_app):
    """Giống GraphRAG: mỗi lượt quét mới ghi đè lên ``self._worker``."""
    holder = {}
    for _ in range(20):
        w = AgentWorker(lambda _w: time.sleep(0.05) or {})
        holder["worker"] = w
        w.start()
        gc.collect()
    assert _pump_until(qt_app, lambda: not AgentWorker._running, timeout=5)
