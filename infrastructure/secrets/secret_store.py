"""Nơi cất credential — interface, chưa phải cài đặt.

Hợp đồng số 1 của mục chung: chốt hôm nay để N2 và N3 code được ngay, không
phải đợi bản Keyring thật (R02-T04, hạn 26/08).

Vì sao là interface chứ không phải hàm tiện ích: bản thật sẽ gọi OS Keyring —
chậm, có thể ném lỗi, và trong test thì không được đụng vào keyring máy thật.
Có interface thì test tiêm ``FakeSecretStore`` vào, chạy trong bộ nhớ.

Quy ước đặt key: ``"provider:<tên>"`` cho API key của provider, ví dụ
``"provider:openai"``. Đặt sẵn để không mỗi người tự nghĩ một kiểu.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


def provider_key(name: str) -> str:
    """Key chuẩn cho API key của một provider."""
    return f"provider:{name}"


@runtime_checkable
class SecretStore(Protocol):
    """Đọc/ghi bí mật. Cài đặt thật: ``KeyringAdapter`` (R02-T04)."""

    def get(self, key: str) -> str | None:
        """Giá trị của ``key``, hoặc None nếu chưa có.

        Không được ném lỗi khi thiếu key — thiếu là chuyện bình thường (người
        dùng chưa nhập API key), không phải sự cố.
        """
        ...

    def set(self, key: str, value: str) -> None:
        """Lưu ``value``. Ghi đè nếu key đã tồn tại."""
        ...

    def delete(self, key: str) -> None:
        """Xoá ``key``. Không có sẵn thì im lặng bỏ qua, không ném lỗi."""
        ...

    def has(self, key: str) -> bool:
        """Có key này chưa — dùng cho màn Cài đặt hiển thị trạng thái mà không
        cần đọc chính giá trị bí mật ra."""
        ...
