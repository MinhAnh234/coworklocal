"""Provider boundary owned with search_project_knowledge."""

from __future__ import annotations

from typing import Any, Protocol

from ..foundation import IdentityContext, ProviderError


class KnowledgeProvider(Protocol):
    """Nguồn cấp bối cảnh tri thức nội bộ cho một project.

    Chỉ là hợp đồng: bản cài đặt thật được nối vào qua ``build_provider``.
    """
    def search_knowledge(self, **arguments: Any) -> dict[str, Any]:
        """Trả về bối cảnh tri thức nội bộ theo tham số của tool."""
        ...


class UnconfiguredKnowledgeProvider:
    """Bản thay thế khi chưa cấu hình nguồn tri thức nội bộ thật.

    Luôn ném lỗi ``UNAVAILABLE`` thay vì trả dữ liệu rỗng — rỗng sẽ bị Agent
    hiểu nhầm là "tra rồi, không có gì", còn lỗi thì nói đúng sự thật là
    chưa có nguồn nào được nối.
    """
    def search_knowledge(self, **arguments: Any) -> dict[str, Any]:
        """Luôn báo chưa cấu hình; không cho thử lại."""
        raise ProviderError(
            "UNAVAILABLE",
            "The knowledge provider is not configured for this environment.",
            retryable=False,
        )


def build_provider(identity: IdentityContext) -> KnowledgeProvider:
    """Replace only this factory when wiring approved project retrieval."""
    return UnconfiguredKnowledgeProvider()
