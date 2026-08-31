"""Provider boundary owned with get_project_change_context."""

from __future__ import annotations

from typing import Any, Protocol

from ..foundation import IdentityContext, ProviderError


class ChangeProvider(Protocol):
    """Nguồn cấp bối cảnh thay đổi (commit, PR) cho một project.

    Chỉ là hợp đồng: bản cài đặt thật được nối vào qua ``build_provider``.
    """
    def get_change_context(self, **arguments: Any) -> dict[str, Any]:
        """Trả về bối cảnh thay đổi (commit, PR) theo tham số của tool."""
        ...


class UnconfiguredChangeProvider:
    """Bản thay thế khi chưa cấu hình nguồn thay đổi (commit, PR) thật.

    Luôn ném lỗi ``UNAVAILABLE`` thay vì trả dữ liệu rỗng — rỗng sẽ bị Agent
    hiểu nhầm là "tra rồi, không có gì", còn lỗi thì nói đúng sự thật là
    chưa có nguồn nào được nối.
    """
    def get_change_context(self, **arguments: Any) -> dict[str, Any]:
        """Luôn báo chưa cấu hình; không cho thử lại."""
        raise ProviderError(
            "UNAVAILABLE",
            "The change provider is not configured for this environment.",
            retryable=False,
        )


def build_provider(identity: IdentityContext) -> ChangeProvider:
    """Replace only this factory when wiring the approved read-only Git adapter."""
    return UnconfiguredChangeProvider()
