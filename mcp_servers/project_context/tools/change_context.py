"""Member C work package: get_project_change_context."""

# ruff: noqa: UP045 -- Optional keeps Pydantic model evaluation compatible with Python 3.9.

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import Field

from ..foundation import ContractModel, SourceCitation, ToolTemplate


class ChangeContextInput(ContractModel):
    """Tham số vào của ``get_project_change_context``: project và mã thay đổi.

    ``detail`` chọn độ dài kết quả, ``cursor`` để lấy trang tiếp khi bị cắt bớt.
    """
    project_id: str = Field(min_length=1, max_length=128)
    change_id: str = Field(min_length=1, max_length=128)
    detail: Literal["summary", "standard", "full"] = "standard"
    cursor: Optional[str] = Field(default=None, max_length=2048)


class ChangeContextOutput(ContractModel):
    """Kết quả trả về: mô tả một commit/PR/MR kèm file, commit và issue liên quan.

    ``source`` là trích dẫn nguồn bắt buộc; ``truncated``/``next_cursor`` cho
    Agent biết còn dữ liệu chưa lấy hết.
    """
    correlation_id: str
    project_id: str
    change_id: str
    change_type: Literal["commit", "pull-request", "merge-request"]
    title: str
    state: str
    summary: str
    authors: tuple[str, ...]
    files: tuple[str, ...]
    commits: tuple[str, ...]
    related_issues: tuple[str, ...]
    source: SourceCitation
    truncated: bool
    returned: int = Field(ge=0)
    remaining: int = Field(ge=0)
    next_cursor: Optional[str] = None


def _handle(arguments: ContractModel, provider: Any) -> dict[str, Any]:
    """Kiểm tham số theo schema rồi chuyển sang provider đã được cấp cho lượt gọi này."""
    request = ChangeContextInput.model_validate(arguments)
    return provider.get_change_context(**request.model_dump())


TOOL = ToolTemplate(
    name="get_project_change_context",
    description=(
        "Returns provider-neutral context for one authorized commit, pull request, or merge request "
        "with changed files, commits, related issues, and a pinned source. Use when an exact change "
        "identifier is known. Do not use for issue details or free-text document search."
    ),
    input_model=ChangeContextInput,
    output_model=ChangeContextOutput,
    handler=_handle,
)
