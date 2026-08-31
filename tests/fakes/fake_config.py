"""Bản giả của ConfigRepository và SecretStore — chạy trong bộ nhớ.

Dùng để N2 (Giám sát) và N3 (Co4E) code và test ngay từ 21/08, không phải đợi
bản thật xong ngày 23/08 và 26/08.

Không chạm đĩa, không chạm keyring, không cần Qt. Test dùng nó chạy trong vài
mili giây.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


class FakeSecretStore:
    """SecretStore trong bộ nhớ.

    >>> s = FakeSecretStore({"provider:openai": "sk-test"})
    >>> s.get("provider:openai")
    'sk-test'
    >>> s.get("provider:chua-co") is None
    True
    """

    def __init__(self, seed: Dict[str, str] | None = None):
        self._items: Dict[str, str] = dict(seed or {})

    def get(self, key: str) -> str | None:
        return self._items.get(key)

    def set(self, key: str, value: str) -> None:
        self._items[key] = value

    def delete(self, key: str) -> None:
        self._items.pop(key, None)

    def has(self, key: str) -> bool:
        return key in self._items


class FakeConfigRepository:
    """ConfigRepository trong bộ nhớ, có sẵn giá trị mặc định hợp lý.

    Mọi thứ ghi đè được qua tham số khởi tạo, nên test dựng đúng tình huống
    mình cần::

        cfg = FakeConfigRepository(theme="light", shared_dir="/tmp/chung")
    """

    def __init__(self, *, active_provider: str = "ollama",
                 providers: Dict[str, Dict[str, Any]] | None = None,
                 shared_dir: str = "", theme: str = "dark", language: str = "vi",
                 routing: Dict[str, Any] | None = None,
                 auth: Dict[str, Any] | None = None,
                 agent_security: Dict[str, Any] | None = None,
                 tools_disabled: list[str] | None = None,
                 history_dir: Path | None = None,
                 output_dir: Path | None = None):
        self._active_provider = active_provider
        self._providers = providers or {
            "ollama": {"base_url": "http://localhost:11434/v1", "model": "llama3"},
            "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
        }
        self._shared_dir = shared_dir
        self._theme = theme
        self._language = language
        self._routing = routing or {"mode": "off"}
        self._auth = auth or {}
        self._agent_security = agent_security or {"cowork_confirm_commands": True}
        self._tools_disabled = list(tools_disabled or [])
        self._history_dir = history_dir or Path("/fake/history")
        self._output_dir = output_dir or Path("/fake/workspace")
        #: số lần save() được gọi — để test khẳng định "có ghi" mà không cần đĩa
        self.saves = 0

    # ---- provider ------------------------------------------------------
    @property
    def active_provider(self) -> str:
        return self._active_provider

    def set_active_provider(self, name: str) -> None:
        self._active_provider = name

    def provider_conf(self, name: str | None = None) -> Dict[str, Any]:
        return dict(self._providers.get(name or self._active_provider, {}))

    # ---- đường dẫn -----------------------------------------------------
    @property
    def shared_dir(self) -> str:
        return self._shared_dir

    def history_dir(self) -> Path:
        return self._history_dir

    def cowork_output_dir(self) -> Path:
        return self._output_dir

    # ---- giao diện -----------------------------------------------------
    @property
    def theme(self) -> str:
        return self._theme

    def set_theme(self, value: str) -> None:
        self._theme = value

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, value: str) -> None:
        self._language = value

    # ---- nhóm cấu hình --------------------------------------------------
    @property
    def routing(self) -> Dict[str, Any]:
        return self._routing

    @property
    def auth(self) -> Dict[str, Any]:
        return self._auth

    @property
    def agent_security(self) -> Dict[str, Any]:
        return self._agent_security

    @property
    def tools_disabled(self) -> list[str]:
        return list(self._tools_disabled)

    def set_tool_enabled(self, name: str, enabled: bool) -> None:
        if enabled:
            self._tools_disabled = [t for t in self._tools_disabled if t != name]
        elif name not in self._tools_disabled:
            self._tools_disabled.append(name)

    # ---- ghi ------------------------------------------------------------
    def save(self) -> None:
        self.saves += 1
