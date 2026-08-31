"""ToolPolicyGateway giả — để N3 (Co4E) chạy được khi Team Hoa chưa cài đặt.

Mặc định cho qua hết, vì phần lớn test Co4E quan tâm tới luồng workflow chứ
không phải chính sách. Test nào cần kiểm nhánh bị chặn thì lập trình câu trả
lời::

    gate = FakeToolPolicyGateway(rules={"run_command": deny("cấm trong Co4E")})
"""
from __future__ import annotations

from typing import Callable, Dict

from cowork_local.domain.security.tool_policy import (
    PolicyDecision, ToolCallRequest, allow,
)


class FakeToolPolicyGateway:
    """Cổng chính sách trong bộ nhớ, có ghi lại đã hỏi những gì."""

    def __init__(self, rules: Dict[str, PolicyDecision] | None = None,
                 default: PolicyDecision | None = None,
                 decide: Callable[[ToolCallRequest], PolicyDecision] | None = None):
        #: {tên tool: quyết định} — tra trước default
        self.rules = dict(rules or {})
        self.default = default or allow()
        #: hàm tự quyết, dùng khi cần logic phức tạp hơn tra bảng
        self._decide = decide
        #: mọi lời gọi đã đi qua — để test khẳng định "có hỏi cổng không"
        self.seen: list[ToolCallRequest] = []

    def check(self, request: ToolCallRequest) -> PolicyDecision:
        self.seen.append(request)
        if self._decide is not None:
            return self._decide(request)
        return self.rules.get(request.name, self.default)

    # ---- tiện cho test --------------------------------------------------
    def asked_for(self, name: str) -> bool:
        return any(r.name == name for r in self.seen)

    @property
    def call_count(self) -> int:
        return len(self.seen)
