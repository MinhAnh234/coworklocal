"""Provider boundary owned with get_project_issue_context."""

from __future__ import annotations

from typing import Any, Protocol

from ..foundation import IdentityContext, ProviderError


class IssueProvider(Protocol):
    """Nguồn cấp bối cảnh issue/ticket cho một project.

    Chỉ là hợp đồng: bản cài đặt thật được nối vào qua ``build_provider``.
    """
    def get_issue_context(self, **arguments: Any) -> dict[str, Any]:
        """Trả về bối cảnh issue/ticket theo tham số của tool."""
        ...


class UnconfiguredIssueProvider:
    """Bản thay thế khi chưa cấu hình nguồn issue/ticket thật.

    Luôn ném lỗi ``UNAVAILABLE`` thay vì trả dữ liệu rỗng — rỗng sẽ bị Agent
    hiểu nhầm là "tra rồi, không có gì", còn lỗi thì nói đúng sự thật là
    chưa có nguồn nào được nối.
    """
    def get_issue_context(self, **arguments: Any) -> dict[str, Any]:
        """Luôn báo chưa cấu hình; không cho thử lại."""
        raise ProviderError(
            "UNAVAILABLE",
            "The issue provider is not configured for this environment.",
            retryable=False,
        )


def build_provider(identity: IdentityContext) -> IssueProvider:
    """Replace only this factory when wiring the approved read-only issue adapter."""
    return UnconfiguredIssueProvider()
