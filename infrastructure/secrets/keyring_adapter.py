"""SecretStore chạy trên OS Keyring — R02-T04.

Windows dùng Credential Manager, macOS dùng Keychain, Linux dùng Secret
Service. Người dùng cuối không thấy gì khác, nhưng API key thôi nằm trong
``config.json`` — đó là điều kiện để qua CASAN Check 1.

Không phải máy nào cũng có keyring dùng được: Linux chạy headless không có
Secret Service, và CI thì gần như chắc chắn không. Nên adapter này **không bao
giờ ném lỗi** — không dùng được thì tự báo ``available = False`` và trả về
None, để tầng trên hiển thị "chưa lưu được khoá" thay vì sập cả app.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

#: Tên "dịch vụ" trong keyring — mọi khoá của app nằm dưới đây.
SERVICE = "cowork-local"


class KeyringAdapter:
    """Cài đặt :class:`SecretStore` bằng thư viện ``keyring``.

    >>> store = KeyringAdapter()
    >>> if store.available:
    ...     store.set("provider:openai", "sk-...")
    """

    def __init__(self, service: str = SERVICE):
        """Dò xem máy có kho khoá dùng được không.

        Backend ``fail`` của keyring vẫn import trót lọt nhưng ném lỗi ở mọi lượt
        gọi, nên phải nhận ra nó ngay tại đây và coi như không có kho khoá.
        """
        self.service = service
        self._backend = None
        self._available = False
        try:
            import keyring
            from keyring.backends.fail import Keyring as FailKeyring

            backend = keyring.get_keyring()
            # backend "fail" là cái keyring trả về khi không tìm được kho nào
            # dùng được — gọi vào chỉ tổ ném lỗi.
            if not isinstance(backend, FailKeyring):
                self._backend = keyring
                self._available = True
            else:
                log.info("keyring không có kho khả dụng trên máy này")
        except Exception as exc:      # noqa: BLE001 — thiếu thư viện, thiếu DBus…
            log.info("keyring không dùng được: %s", exc)

    @property
    def available(self) -> bool:
        """Có kho bí mật dùng được không.

        Tầng giao diện đọc cờ này để nói cho người dùng biết vì sao ô API key
        không lưu được, thay vì im lặng làm mất khoá họ vừa nhập.
        """
        return self._available

    # ---- SecretStore ----------------------------------------------------
    def get(self, key: str) -> str | None:
        """Đọc một bí mật; máy không có kho bí mật thì trả ``None``."""
        if not self._available:
            return None
        try:
            return self._backend.get_password(self.service, key)
        except Exception as exc:      # noqa: BLE001
            log.warning("đọc khoá %r thất bại: %s", key, exc)
            return None

    def set(self, key: str, value: str) -> None:
        """Lưu một bí mật; không có kho thì chỉ ghi cảnh báo, KHÔNG ném lỗi.

        App phải chạy được trên máy thiếu keyring — lúc đó khoá nằm lại trong file
        cấu hình như trước.
        """
        if not self._available:
            log.warning("không lưu được %r: máy này không có kho bí mật", key)
            return
        try:
            self._backend.set_password(self.service, key, value)
        except Exception as exc:      # noqa: BLE001
            log.warning("lưu khoá %r thất bại: %s", key, exc)

    def delete(self, key: str) -> None:
        """Xoá một bí mật khỏi kho; không có kho thì bỏ qua."""
        if not self._available:
            return
        try:
            self._backend.delete_password(self.service, key)
        except Exception:             # noqa: BLE001 — xoá cái không có: bỏ qua
            pass

    def has(self, key: str) -> bool:
        """Kho có chứa bí mật này không."""
        return self.get(key) is not None
