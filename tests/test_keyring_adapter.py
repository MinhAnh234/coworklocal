"""KeyringAdapter — R02-T04.

Không đụng vào keyring thật của máy chạy test: tiêm một backend giả. Test mà
ghi vào Credential Manager thật thì để lại rác trên máy người khác, và trên CI
thì không có kho nào để ghi.
"""
from __future__ import annotations

import pytest

from cowork_local.infrastructure.secrets.keyring_adapter import KeyringAdapter
from cowork_local.infrastructure.secrets.secret_store import SecretStore, provider_key


class _KeyringGia:
    """Đủ giống thư viện keyring để adapter dùng được."""

    def __init__(self, hong: bool = False):
        self.kho: dict[tuple[str, str], str] = {}
        self.hong = hong

    def get_password(self, service, key):
        if self.hong:
            raise RuntimeError("kho bí mật không phản hồi")
        return self.kho.get((service, key))

    def set_password(self, service, key, value):
        if self.hong:
            raise RuntimeError("kho bí mật không phản hồi")
        self.kho[(service, key)] = value

    def delete_password(self, service, key):
        if self.hong:
            raise RuntimeError("kho bí mật không phản hồi")
        del self.kho[(service, key)]


@pytest.fixture
def store():
    a = KeyringAdapter(service="test-cowork")
    a._backend = _KeyringGia()
    a._available = True
    return a


def test_khop_hop_dong_secret_store(store):
    assert isinstance(store, SecretStore)


def test_luu_doc_xoa(store):
    k = provider_key("openai")
    assert store.get(k) is None
    assert store.has(k) is False

    store.set(k, "sk-that-la-bi-mat")
    assert store.get(k) == "sk-that-la-bi-mat"
    assert store.has(k) is True

    store.delete(k)
    assert store.get(k) is None


def test_moi_provider_mot_khoa_rieng(store):
    store.set(provider_key("openai"), "khoa-openai")
    store.set(provider_key("anthropic"), "khoa-anthropic")
    assert store.get(provider_key("openai")) == "khoa-openai"
    assert store.get(provider_key("anthropic")) == "khoa-anthropic"


def test_may_khong_co_kho_thi_im_lang_chu_khong_sap():
    """Linux headless và CI không có Secret Service. App vẫn phải chạy."""
    a = KeyringAdapter(service="test-cowork")
    a._backend = None
    a._available = False

    assert a.available is False
    assert a.get("bat-ky") is None
    a.set("bat-ky", "gia-tri")      # không ném lỗi
    a.delete("bat-ky")              # không ném lỗi
    assert a.has("bat-ky") is False


def test_kho_loi_giua_chung_thi_khong_lam_sap_app(store):
    """Keyring có thể hỏng lúc đang chạy — mất DBus, người dùng khoá máy."""
    store._backend.hong = True

    assert store.get("x") is None   # nuốt lỗi, trả None
    store.set("x", "y")             # nuốt lỗi
    store.delete("x")               # nuốt lỗi


def test_xoa_khoa_khong_ton_tai_thi_bo_qua(store):
    store.delete(provider_key("chua-bao-gio-luu"))    # không ném lỗi
