"""Low-level MCP stdio adapter around the transport-agnostic Project Context core."""

# ruff: noqa: UP045 -- Optional keeps the template importable with Pydantic on Python 3.9.

from __future__ import annotations

import json
from typing import Any, Optional
from uuid import uuid4

from pydantic import ValidationError

from .foundation import (
    DispatchResult,
    ProjectContextRuntime,
    ProviderError,
    error_result,
)
from .registry import TOOLS_BY_NAME, tool_declarations
from .runtime import default_runtime, require_supported_python


def dispatch(
    name: str,
    arguments: dict[str, Any],
    runtime: ProjectContextRuntime,
) -> DispatchResult:
    """Validate → authorize → resolve provider → execute → validate output."""
    correlation_id = str(uuid4())
    tool = TOOLS_BY_NAME.get(name)
    if tool is None:
        return error_result(
            "NOT_FOUND",
            category="NOT_FOUND",
            retryable=False,
            message="The requested MCP tool is not registered.",
            suggested_action="Refresh the tool list and choose one of the advertised tools.",
            correlation_id=correlation_id,
        )

    try:
        validated_input = tool.input_model.model_validate(arguments or {})
    except ValidationError:
        return error_result(
            "INVALID_INPUT",
            category="INVALID_INPUT",
            retryable=False,
            message="The tool arguments do not match the published input contract.",
            suggested_action="Correct the required fields and value bounds, then call again.",
            correlation_id=correlation_id,
        )

    project_id = str(validated_input.project_id)
    if not runtime.policy.decide(runtime.identity, name, project_id):
        return error_result(
            "DENIED",
            category="DENIED",
            retryable=False,
            message="The project is outside the caller's approved scope.",
            suggested_action="Use an approved project or ask the project owner for access.",
            correlation_id=correlation_id,
        )

    try:
        provider = runtime.credential_resolver.resolve(runtime.identity, name)
        raw_output = tool.handler(validated_input, provider)
    except ProviderError as exc:
        return error_result(
            exc.code,
            category=exc.code,
            retryable=exc.retryable,
            message=exc.safe_message,
            suggested_action="Check the approved provider configuration and retry if allowed.",
            correlation_id=correlation_id,
        )
    except Exception:  # noqa: BLE001 - provider failures must not crash or leak into the agent turn
        return error_result(
            "UPSTREAM_ERROR",
            category="UPSTREAM_ERROR",
            retryable=False,
            message="The approved provider could not complete the request.",
            suggested_action="Check the correlation ID in server logs; do not resend credentials.",
            correlation_id=correlation_id,
        )

    try:
        output_with_trace = {**raw_output, "correlation_id": correlation_id}
        validated_output = tool.output_model.model_validate(output_with_trace)
    except ValidationError:
        return error_result(
            "UPSTREAM_ERROR",
            category="UPSTREAM_ERROR",
            retryable=False,
            message="The provider response did not match the published output contract.",
            suggested_action="Fix the provider mapping before retrying the request.",
            correlation_id=correlation_id,
        )
    return DispatchResult(ok=True, payload=validated_output.model_dump(mode="json"))


def build_server(runtime: Optional[ProjectContextRuntime] = None):
    """Dựng máy chủ MCP Project Context.

    ``runtime`` để trống thì lấy bộ mặc định đọc từ biến môi trường; test
    truyền vào bộ giả để không cần cấu hình thật.
    """
    from mcp import types
    from mcp.server.lowlevel import Server

    require_supported_python()
    app_runtime = runtime or default_runtime()
    app = Server("project_context")

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        """Trả về khai báo của mọi tool đã đăng ký."""
        return [types.Tool(**declaration) for declaration in tool_declarations()]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> types.CallToolResult:
        """Chạy một tool và trả kết quả.

        Luôn kèm payload dạng văn bản JSON; chỉ khi thành công mới đính thêm
        ``structuredContent``, còn lỗi thì bật ``isError``.
        """
        result = dispatch(name, arguments or {}, app_runtime)
        return types.CallToolResult(
            content=[types.TextContent(
                type="text",
                text=json.dumps(result.payload, ensure_ascii=False, separators=(",", ":")),
            )],
            structuredContent=result.payload if result.ok else None,
            isError=not result.ok,
        )

    return app


def main() -> None:
    """Điểm vào khi chạy như tiến trình con: phục vụ MCP qua stdio."""
    import anyio
    from mcp.server.stdio import stdio_server

    app = build_server()

    async def _run() -> None:
        """Vòng lặp phục vụ, đọc/ghi trên stdio cho tới khi tiến trình cha đóng."""
        async with stdio_server() as (read, write):
            await app.run(read, write, app.create_initialization_options())

    anyio.run(_run)


if __name__ == "__main__":
    main()
