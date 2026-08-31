"""Test double dùng chung cho cả 3 team — không phụ thuộc Qt.

Gói này cố ý không import sẵn fake nào để tránh kéo theo phụ thuộc khi chạy cô lập.
Hỗ trợ import trực tiếp từ module con hoặc import lười từ package.
"""
from typing import Any


def __getattr__(name: str) -> Any:
    if name in ("FakeProvider", "RecordedCall", "ScriptedTurn"):
        from .fake_provider import FakeProvider, RecordedCall, ScriptedTurn
        return locals()[name]
    if name in ("FakeToolExecutor", "ToolInvocation"):
        from .fake_tool_executor import FakeToolExecutor, ToolInvocation
        return locals()[name]
    if name == "FakeClock":
        from .fake_clock import FakeClock
        return FakeClock
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "FakeClock",
    "FakeProvider",
    "FakeToolExecutor",
    "RecordedCall",
    "ScriptedTurn",
    "ToolInvocation",
]
