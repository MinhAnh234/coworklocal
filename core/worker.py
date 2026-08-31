"""Background worker (QThread) that runs an agent job off the UI thread.

Each chat tab owns its own worker, so the Cowork and Code tabs (and any number
of tabs) run concurrently — true multitasking. All UI updates happen via Qt
signals, which are delivered to the main thread as queued connections.
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Optional

from PySide6.QtCore import QThread, Signal

from .permissions import PermissionGate

# A job receives the worker and returns a result dict (or None).
Job = Callable[["AgentWorker"], Optional[Dict[str, Any]]]


class AgentWorker(QThread):
    """Luồng nền chạy một lượt agent, nối kết quả về giao diện qua signal Qt.

    Mọi việc chậm (gọi model, chạy tool, trích tệp) đều phải nằm trong đây —
    chạy ở luồng giao diện là cả cửa sổ đứng hình.
    """
    event = Signal(dict)                 # streaming/agent events
    permission_requested = Signal(dict)  # confirm-mode tool action awaiting approval
    finished_ok = Signal(dict)           # job completed
    failed = Signal(str)                 # job raised

    def __init__(self, job: Job, parent=None):
        """Bọc một hàm thành luồng nền.

        ``stop_event`` để công khai vì provider cần truyền thẳng nó vào
        ``Event.wait()`` — nhờ vậy bấm Dừng là dừng ngay, không phải đợi hết lượt
        chờ mạng hiện tại.
        """
        super().__init__(parent)
        self._job = job
        self.stop_event = threading.Event()  # public for provider Event.wait() — immediate Stop
        self.gate: Optional[PermissionGate] = None

    # -- helpers used from inside the job (worker thread) --------------
    def is_cancelled(self) -> bool:
        """``True`` khi người dùng đã bấm Dừng — job phải tự thoát sớm."""
        return self.stop_event.is_set()

    def emit_event(self, ev: Dict[str, Any]) -> None:
        """Đẩy một sự kiện tiến độ về giao diện."""
        self.event.emit(ev)

    def new_gate(self, mode: str, agent_role: str = "") -> PermissionGate:
        """Dựng cổng phê duyệt cho lượt này (chế độ hỏi trước khi chạy tool)."""
        self.gate = PermissionGate(
            mode, on_request=lambda action: self.permission_requested.emit(action),
            agent_role=agent_role,
        )
        return self.gate

    # -- control from the UI thread -----------------------------------
    def request_stop(self) -> None:
        """Yêu cầu dừng: bật cờ huỷ và giải phóng cổng phê duyệt đang chờ.

        Phải huỷ cả cổng, nếu không job sẽ kẹt mãi ở chỗ chờ người dùng bấm Đồng ý.
        """
        self.stop_event.set()
        if self.gate:
            self.gate.cancel()

    def resolve_permission(self, approved: bool) -> None:
        """Trả lời một yêu cầu phê duyệt tool đang chờ."""
        if self.gate:
            self.gate.resolve(approved)

    # -- thread body ---------------------------------------------------
    def run(self) -> None:  # noqa: D401
        """Thân luồng: chạy job rồi phát ``finished_ok``, lỗi thì phát ``failed``.

        Bắt mọi ngoại lệ: một lỗi lọt ra khỏi đây sẽ giết luồng mà giao diện không
        nhận được tín hiệu nào — người dùng thấy nút Dừng quay mãi.
        """
        try:
            result = self._job(self)
            self.finished_ok.emit(result or {})
        except Exception as exc:  # surface any failure to the UI
            self.failed.emit(str(exc))
