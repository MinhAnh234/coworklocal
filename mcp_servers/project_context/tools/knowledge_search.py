"""Member B work package: search_project_knowledge."""

# ruff: noqa: UP045 -- Optional keeps Pydantic model evaluation compatible with Python 3.9.

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import Field

from ..foundation import ContractModel, SourceCitation, ToolTemplate


class KnowledgeSearchInput(ContractModel):
    """Tham số vào của ``search_project_knowledge``: project và câu truy vấn.

    ``top_k`` chặn trong 1..20 để một lượt tra không nuốt hết cửa sổ ngữ cảnh.
    """
    project_id: str = Field(min_length=1, max_length=128)
    query: str = Field(min_length=2, max_length=1000)
    detail: Literal["summary", "standard", "full"] = "standard"
    top_k: int = Field(default=5, ge=1, le=20)
    language: Optional[Literal["en", "ja", "vi"]] = None
    cursor: Optional[str] = Field(default=None, max_length=2048)


class KnowledgeItem(ContractModel):
    """Một đoạn tài liệu khớp truy vấn: trích đoạn, điểm số 0..1 và nguồn."""
    document_id: str
    chunk_id: str
    title: str
    excerpt: str
    score: float = Field(ge=0, le=1)
    source: SourceCitation


class KnowledgeSearchOutput(ContractModel):
    """Kết quả trả về: danh sách đoạn khớp đã xếp hạng, mỗi đoạn kèm trích dẫn nguồn."""
    correlation_id: str
    project_id: str
    query: str
    items: tuple[KnowledgeItem, ...]
    truncated: bool
    returned: int = Field(ge=0)
    remaining: int = Field(ge=0)
    next_cursor: Optional[str] = None


def _handle(arguments: ContractModel, provider: Any) -> dict[str, Any]:
    """Kiểm tham số theo schema rồi chuyển sang provider đã được cấp cho lượt gọi này."""
    request = KnowledgeSearchInput.model_validate(arguments)
    return provider.search_knowledge(**request.model_dump())


TOOL = ToolTemplate(
    name="search_project_knowledge",
    description=(
        "Searches approved knowledge for one authorized project and returns ranked excerpts with "
        "pinned citations. Use for requirements, design notes, or runbooks when no exact issue is "
        "known. Do not use for issue details or Git change review."
    ),
    input_model=KnowledgeSearchInput,
    output_model=KnowledgeSearchOutput,
    handler=_handle,
)
