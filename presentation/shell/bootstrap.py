"""Composition Root — R08-T10.

Một chỗ duy nhất quyết định app chạy bằng những mảnh nào. Trước đây quyết định
đó nằm rải trong ``app.py::run``, lẫn với việc dựng cửa sổ; tách ra để đổi một
mảnh (ví dụ thay kho bí mật) không phải đụng vào mã giao diện.

Đây cũng là chỗ hoàn tất R02: từ đây app chạy bằng :class:`JsonConfigRepository`
chứ không còn ``config.py::AppConfig``. Hai thứ đổi thật sự:

* ghi cấu hình qua ``AtomicJsonFile`` — mất điện giữa lúc lưu không làm hỏng file
* API key nằm trong kho bí mật của hệ điều hành, không nằm trong ``config.json``

Máy không có kho bí mật (Linux headless, CI, hoặc keyring hỏng) vẫn chạy bình
thường: repository nhận ``secrets=None`` và đọc khoá thẳng từ file như cũ. Thà
để khoá trong file còn hơn xoá đi rồi người dùng mất khoá mà không hiểu vì sao.
"""
from __future__ import annotations

from pathlib import Path

from ...infrastructure.config.json_config_repository import JsonConfigRepository
from ...infrastructure.secrets.keyring_adapter import KeyringAdapter
from ...state import AppContext


def build_secret_store():
    """Kho bí mật của hệ điều hành, hoặc None nếu máy này không có.

    ``KeyringAdapter`` không bao giờ ném lỗi — nó tự báo ``available``. Trả về
    None thay vì một adapter chết để chỗ gọi khỏi phải đoán.
    """
    store = KeyringAdapter()
    return store if store.available else None


def build_config(path: Path | None = None) -> JsonConfigRepository:
    """Dựng repository cấu hình đã nối sẵn kho bí mật của hệ điều hành.

    Đây là Composition Root: chỗ DUY NHẤT quyết định app chạy bằng mảnh nào.
    """
    return JsonConfigRepository.load(path, secrets=build_secret_store())


def build_context(path: Path | None = None) -> AppContext:
    """Dựng AppContext hoàn chỉnh — điểm vào cho ``app.run()`` và cho checker."""
    return AppContext(build_config(path))
