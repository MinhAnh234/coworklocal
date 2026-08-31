"""Permission gate for the Code agent.

In ``auto`` mode every action is approved immediately. In ``confirm`` mode the
agent thread blocks on a threading event while the UI shows a preview dialog and
the user approves or rejects. Cancelling the task releases any pending wait.
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Optional

RequestFn = Callable[[Dict[str, Any]], None]


class PermissionGate:
    """Cổng phê duyệt tool: chặn lượt chạy lại và chờ người dùng đồng ý.

    Ba chế độ: 'auto' cho qua hết, 'confirm' hỏi trước mỗi lệnh có rủi ro, và
    'deny' chặn thẳng. Dùng ``threading.Event`` để luồng nền đứng chờ trong khi
    luồng giao diện hiện hộp thoại.
    """
    def __init__(self, mode: str = "confirm", on_request: Optional[RequestFn] = None,
                agent_role: str = ""):
        """``mode`` quyết định cách xử: hỏi, cho qua hết, hay chặn hết.

        ``on_request`` là hàm hiện hộp thoại; để None (không có giao diện) thì cổng
        rơi về quyết định mặc định của ``mode`` thay vì treo mãi.
        """
        self.mode = mode
        self.on_request = on_request
        self.agent_role = agent_role
        self._event = threading.Event()
        self._approved = False

    def set_mode(self, mode: str) -> None:
        """Đổi chế độ phê duyệt giữa chừng."""
        self.mode = mode

    def request(self, action: Dict[str, Any]) -> bool:
        """Block (in confirm mode) until the action is approved or rejected."""
        from . import audit_log

        if self.mode == "auto":
            audit_log.record("permission", str(action.get("name", "")), True,
                             "auto mode", agent_role=self.agent_role)
            return True
        self._approved = False
        self._event.clear()
        if self.on_request:
            self.on_request(action)
        self._event.wait()
        audit_log.record("permission", str(action.get("name", "")), self._approved,
                         "user approved" if self._approved else "user rejected",
                         agent_role=self.agent_role)
        return self._approved

    def resolve(self, approved: bool) -> None:
        """Người dùng đã trả lời: ghi kết quả và đánh thức luồng đang chờ."""
        self._approved = approved
        self._event.set()

    def cancel(self) -> None:
        """Unblock any pending request, treating it as rejected."""
        self._approved = False
        self._event.set()
