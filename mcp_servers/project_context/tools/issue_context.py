"""Member A work package: get_project_issue_context."""

# ruff: noqa: UP045 -- Optional keeps Pydantic model evaluation compatible with Python 3.9.

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import Field

from ..foundation import ContractModel, SourceCitation, ToolTemplate


class IssueContextInput(ContractModel):
    """Tham số vào của ``get_project_issue_context``: project và mã issue.

    ``detail`` chọn độ dài kết quả, ``cursor`` để lấy trang tiếp khi bị cắt bớt.
    """
    project_id: str = Field(min_length=1, max_length=128)
    issue_key: str = Field(min_length=1, max_length=128)
    detail: Literal["summary", "standard", "full"] = "standard"
    cursor: Optional[str] = Field(default=None, max_length=2048)


class RelatedItem(ContractModel):
    """Một mục liên quan tới issue (issue khác, PR, tài liệu) kèm loại quan hệ."""
    item_id: str
    relation: str
    title: str
    url: str


class IssueContextOutput(ContractModel):
    """Kết quả trả về: tiêu đề, trạng thái, mô tả, tiêu chí nghiệm thu và các mục liên quan.

    ``source`` là trích dẫn nguồn bắt buộc; ``truncated``/``next_cursor`` cho
    Agent biết còn dữ liệu chưa lấy hết.
    """
    correlation_id: str
    project_id: str
    issue_key: str
    title: str
    status: str
    description: str
    acceptance_criteria: tuple[str, ...]
    related: tuple[RelatedItem, ...]
    source: SourceCitation
    truncated: bool
    returned: int = Field(ge=0)
    remaining: int = Field(ge=0)
    next_cursor: Optional[str] = None


def _handle(arguments: ContractModel, provider: Any) -> dict[str, Any]:
    """Kiểm tham số theo schema rồi chuyển sang provider đã được cấp cho lượt gọi này."""
    request = IssueContextInput.model_validate(arguments)
    return provider.get_issue_context(**request.model_dump())


TOOL = ToolTemplate(
    name="get_project_issue_context",
    description=(
        "Returns one authorized work item's title, state, description, acceptance criteria, "
        "related items, and pinned source. Use when an exact issue key is known. Do not use for "
        "free-text knowledge search or Git change review."
    ),
    input_model=IssueContextInput,
    output_model=IssueContextOutput,
    handler=_handle,
)
