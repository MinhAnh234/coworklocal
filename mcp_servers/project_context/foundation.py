"""Shared, stable boundary used by all Project Context tool work packages."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from pydantic import AnyUrl, BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    """Strict immutable model so provider-specific fields cannot leak to the Agent."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class IdentityContext(ContractModel):
    """Danh tính người gọi kèm phạm vi đã được cấp.

    ``granted_scopes`` là ``frozenset`` để bản ghi danh tính không bị sửa
    trên đường đi giữa các tầng.
    """
    actor_id: str = Field(min_length=1, max_length=256)
    org_unit: str = Field(min_length=1, max_length=128)
    customer: str = Field(min_length=1, max_length=128)
    project: str = Field(min_length=1, max_length=128)
    granted_scopes: frozenset[str]


class SourceCitation(ContractModel):
    """Trích dẫn nguồn cho một mẩu thông tin: hệ thống nào, URL nào, bản nào, lấy lúc nào.

    Bắt buộc có để Agent trả lời kèm nguồn kiểm chứng được, không bịa.
    """
    system: str = Field(min_length=1, max_length=64)
    url: AnyUrl
    revision: str = Field(min_length=1, max_length=256)
    retrieved_at: datetime


@dataclass(frozen=True)
class DispatchResult:
    """Kết quả một lượt gọi tool: thành công hay không, kèm payload trả cho Agent."""
    ok: bool
    payload: dict[str, Any]


class PolicyDecisionPoint(Protocol):
    """Nơi quyết định một danh tính có được gọi một tool trên một project hay không."""
    def decide(self, identity: IdentityContext, tool_name: str, project_id: str) -> bool:
        """``True`` nếu cho phép lượt gọi này."""
        ...


class CredentialResolver(Protocol):
    """Nơi cấp thông tin xác thực cho tool, tách khỏi chỗ dùng nó."""
    def resolve(self, identity: IdentityContext, tool_name: str) -> Any:
        """Trả về thông tin xác thực cho danh tính và tool tương ứng."""
        ...


@dataclass(frozen=True)
class ProjectContextRuntime:
    """Bộ ba mà mọi lượt gọi tool cần: danh tính, cổng chính sách, nơi cấp thông tin xác thực.

    Bất biến (``frozen``) — một lượt gọi không được đổi bối cảnh của lượt khác.
    """
    identity: IdentityContext
    policy: PolicyDecisionPoint
    credential_resolver: CredentialResolver


class ProviderError(RuntimeError):
    """A provider failure with a caller-safe message and retry classification."""

    def __init__(self, code: str, message: str, *, retryable: bool) -> None:
        """``safe_message`` là phần được phép hiện cho người dùng; ``retryable`` cho bên
        gọi biết thử lại có ích không, thay vì bắt họ đoán từ chuỗi lỗi.
        """
        super().__init__(message)
        self.code = code
        self.safe_message = message
        self.retryable = retryable


def decode_offset_cursor(cursor: str | None) -> int:
    """Shared opaque-cursor decoding for every paginated provider.

    Rejected before any backend call so an invalid cursor never costs an
    upstream request.
    """
    if cursor is None:
        return 0
    try:
        offset = int(cursor)
    except ValueError as exc:
        raise ProviderError("INVALID_INPUT", "cursor is not valid.", retryable=False) from exc
    if offset < 0:
        raise ProviderError("INVALID_INPUT", "cursor is not valid.", retryable=False)
    return offset


ToolHandler = Callable[[ContractModel, Any], dict[str, Any]]


@dataclass(frozen=True)
class ToolTemplate:
    """Khai báo một tool MCP: tên, mô tả, kiểu vào/ra, và hàm xử lý."""
    name: str
    description: str
    input_model: type[ContractModel]
    output_model: type[ContractModel]
    handler: ToolHandler

    def declaration(self) -> dict[str, Any]:
        """Bản khai báo theo đúng định dạng MCP, schema sinh thẳng từ model Pydantic."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_model.model_json_schema(),
            "outputSchema": self.output_model.model_json_schema(),
        }


def error_result(
    code: str,
    *,
    category: str,
    retryable: bool,
    message: str,
    suggested_action: str,
    correlation_id: str,
) -> DispatchResult:
    """Dựng một ``DispatchResult`` lỗi theo đúng khuôn chung.

    Mọi lỗi trả cho Agent đều phải có ``correlation_id`` để dò lại trong
    nhật ký, và ``suggested_action`` để Agent biết nên làm gì tiếp thay vì
    chỉ dừng.
    """
    return DispatchResult(
        ok=False,
        payload={
            "error": {
                "code": code,
                "category": category,
                "retryable": retryable,
                "message": message,
                "suggested_action": suggested_action,
                "correlation_id": correlation_id,
            }
        },
    )
