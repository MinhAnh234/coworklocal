"""Fail-closed identity, policy, and provider resolution for the template server."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .foundation import IdentityContext, ProjectContextRuntime, ProviderError
from .providers.change import build_provider as build_change_provider
from .providers.issue import build_provider as build_issue_provider
from .providers.knowledge import build_provider as build_knowledge_provider

MINIMUM_PYTHON = (3, 11)


def require_supported_python(version_info: tuple[int, ...] | None = None) -> None:
    """Fail with an actionable message before the MCP server starts."""
    current = version_info or tuple(sys.version_info[:3])
    if current[:2] < MINIMUM_PYTHON:
        raise RuntimeError(
            "Project Context MCP requires Python 3.11 or newer; "
            f"current runtime is {current[0]}.{current[1]}"
        )


@dataclass(frozen=True)
class ProjectScopePolicy:
    """Pilot policy: read scope and exact identity-bound project are both mandatory."""

    def decide(self, identity: IdentityContext, tool_name: str, project_id: str) -> bool:
        """Chỉ cho phép khi danh tính có phạm vi ``read`` VÀ project khớp đúng
        project gắn với danh tính đó — không cho đọc chéo project.
        """
        return "read" in identity.granted_scopes and project_id == identity.project


PROVIDER_FACTORIES: dict[str, Callable[[IdentityContext], Any]] = {
    "get_project_issue_context": build_issue_provider,
    "search_project_knowledge": build_knowledge_provider,
    "get_project_change_context": build_change_provider,
}


@dataclass(frozen=True)
class ProjectProviderResolver:
    """Tra provider thật cho từng tool theo bảng ``PROVIDER_FACTORIES``."""
    def resolve(self, identity: IdentityContext, tool_name: str) -> Any:
        """Dựng provider cho một tool; tool chưa đăng ký thì báo ``NOT_FOUND`` và
        không cho thử lại.
        """
        factory = PROVIDER_FACTORIES.get(tool_name)
        if factory is None:
            raise ProviderError("NOT_FOUND", "The requested tool is not registered.", retryable=False)
        return factory(identity)


def _required_environment(name: str) -> str:
    """Đọc một biến môi trường bắt buộc; thiếu thì dừng ngay lúc khởi động.

    Thà không chạy còn hơn chạy với cấu hình khuyết rồi lỗi giữa chừng ở một
    lượt gọi tool nào đó.
    """
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Project Context MCP cannot start: required setting {name} is missing")
    return value


def default_runtime() -> ProjectContextRuntime:
    """Build immutable runtime state; missing identity configuration fails at boot."""
    require_supported_python()
    identity = IdentityContext(
        actor_id=_required_environment("COWORK_MCP_ACTOR_ID"),
        org_unit=_required_environment("COWORK_MCP_ORG_UNIT"),
        customer=_required_environment("COWORK_MCP_CUSTOMER"),
        project=_required_environment("COWORK_MCP_PROJECT"),
        granted_scopes=frozenset({"read"}),
    )
    return ProjectContextRuntime(
        identity=identity,
        policy=ProjectScopePolicy(),
        credential_resolver=ProjectProviderResolver(),
    )
