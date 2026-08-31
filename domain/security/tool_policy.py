"""Cổng chính sách cho lời gọi tool — hình dạng dữ liệu, chưa phải cài đặt.

BẢN ĐỀ XUẤT, chờ Team Hoa xác nhận
==================================
Sơ đồ phân hệ trong ``plan.md`` giao ``domain/security/`` cho Team Gamma và
``application/conversations/tool_policy_gateway.py`` cho Team Hoa. Nên Gamma
định nghĩa *hình dạng*, Hoa *cài đặt*.

Viết trước vì N3 (Co4E) cần gọi tool và Team Hoa chưa bắt đầu. Không có nó thì
N3 phải tự phỏng đoán rồi sửa lại sau — mà phỏng đoán của một người thì tệ hơn
một đề xuất viết ra để cả hai bên soi.

Nếu Hoa thấy khác, sửa file này chứ đừng đẻ kiểu thứ hai. Đổi sớm rẻ hơn đổi
muộn: hiện chỉ N3 dùng.

Mô hình bám theo code đang chạy, không bịa:
  * ``core/agent_security.py::SecurityVerdict`` — allowed / reason / layer
  * ``ui/permission_dialog.py`` — hộp thoại hỏi người dùng khi
    ``ctx.project_confirm_commands()`` bật (``ui/chat_panel.py:1312``)

Điểm khác biệt duy nhất so với hôm nay: gộp hai thứ đó thành **một câu trả lời
ba trạng thái**, thay vì code gọi phải tự nhớ hỏi cả hai nơi.

SEAM · dựng 2026-08-21 · chưa nối dây (F-05)
------------------------------------------------------------
Được nối khi: ``application/conversations/tool_policy_gateway.py`` trả về ``PolicyDecision`` thay cho ``bool``.
Để dormant thì sao: Hiện gateway chỉ trả đúng/sai nên lý do chặn bị mất —
đúng thứ kiểu dữ liệu này sinh ra để mang theo.

Cổng ``scripts/check_orphan_modules.py`` đếm tuổi seam từ ngày trên
và nhắc khi quá ``SEAM_MAX_AGE_DAYS``. Đổi nội dung dòng đó thì cổng
đọc theo — đừng sửa ngày để làm im lời nhắc.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Protocol, runtime_checkable


class PolicyOutcome(str, Enum):
    """Ba trạng thái. ``ASK`` là thứ hệ thống hiện tại đã có (hộp thoại xin
    phép) nhưng chưa được coi là một kết quả chính thức."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass(frozen=True)
class ToolCallRequest:
    """Một lời gọi tool đang chờ được duyệt.

    ``surface`` cho biết chỗ phát sinh — ``"cowork"``, ``"code"``, ``"co4e"``,
    ``"task"``. Chính sách khác nhau theo màn: Co4E chạy nền nên không thể bật
    hộp thoại hỏi giữa chừng như Cowork.
    """

    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    surface: str = "cowork"
    project_id: str = ""
    #: True nếu tool đến từ MCP server ngoài, False nếu là tool dựng sẵn.
    external: bool = False


@dataclass(frozen=True)
class PolicyDecision:
    """Câu trả lời của cổng.

    ``reason`` bắt buộc có khi DENY hoặc ASK — người dùng phải biết vì sao bị
    chặn, và ``core/audit_log.py`` cần nó để ghi lại.

    ``layer`` giữ đúng từ vựng của ``SecurityVerdict``: ``"prompt"`` |
    ``"attachment"`` | ``"command"``, cộng thêm ``"policy"`` cho quyết định của
    chính cổng này.
    """

    outcome: PolicyOutcome
    reason: str = ""
    layer: str = "policy"

    @property
    def allowed(self) -> bool:
        """Tương thích với chỗ đang đọc ``SecurityVerdict.allowed``.

        Chú ý: ``ASK`` KHÔNG phải allowed — còn phải hỏi người dùng đã.
        """
        return self.outcome is PolicyOutcome.ALLOW

    def __post_init__(self):
        """Ép mọi quyết định DENY/ASK phải kèm lý do.

        Người dùng thấy lý do trên hộp thoại, và nhật ký kiểm toán ghi lại nó — một
        quyết định chặn không lý do là không truy được về sau.
        """
        if self.outcome is not PolicyOutcome.ALLOW and not self.reason:
            raise ValueError("DENY và ASK bắt buộc có reason — người dùng và "
                             "audit log đều cần biết vì sao")


def allow() -> PolicyDecision:
    """Quyết định cho phép. Không cần lý do: đây là đường đi bình thường."""
    return PolicyDecision(PolicyOutcome.ALLOW)


def deny(reason: str, layer: str = "policy") -> PolicyDecision:
    """Quyết định chặn hẳn, kèm lý do và tên lớp đã ra quyết định."""
    return PolicyDecision(PolicyOutcome.DENY, reason, layer)


def ask(reason: str, layer: str = "policy") -> PolicyDecision:
    """Quyết định phải hỏi người dùng, kèm lý do và tên lớp đã ra quyết định."""
    return PolicyDecision(PolicyOutcome.ASK, reason, layer)


@runtime_checkable
class ToolPolicyGateway(Protocol):
    """Hỏi trước khi chạy tool. Cài đặt thật: Team Hoa (R07, hạn 29/08)."""

    def check(self, request: ToolCallRequest) -> PolicyDecision:
        """Được chạy tool này không.

        KHÔNG được tự bật hộp thoại bên trong — cổng chỉ *trả lời*, còn hỏi ai
        và hỏi thế nào là việc của tầng giao diện. Có vậy thì Co4E chạy nền mới
        dùng chung cổng được với Cowork chạy tương tác.
        """
        ...
