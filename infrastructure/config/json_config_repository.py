"""ConfigRepository chạy trên file JSON — R02-T02.

Thay cho ``config.py::AppConfig``. Hai khác biệt duy nhất về hành vi, cả hai
đều là thứ ta muốn:

1. Ghi qua :class:`AtomicJsonFile` — mất điện giữa lúc lưu không còn làm hỏng
   cấu hình (R02-T01).
2. API key đọc từ :class:`SecretStore` rồi **ghép vào** dict do
   ``provider_conf()`` trả về — đúng đường A đã chốt 21/08
   (``docs/refactor/GammaTeam_decisions.md``). Nhờ vậy 5 nơi đang đọc
   ``conf["api_key"]`` không phải sửa dòng nào, trong đó 3 nơi thuộc Team Duy.

Mọi thứ còn lại giữ nguyên có chủ đích: trộn sâu với mặc định, đọc biến môi
trường, ``ms365.unlocked`` không bao giờ chạm đĩa. Đây là refactor — hành vi
nhìn từ ngoài phải y hệt.
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict

from ..persistence.json.atomic_json_file import AtomicJsonFile
from ..secrets.secret_store import SecretStore, provider_key
from .config_sections import ConfigSectionsMixin
from .schema_migration import CURRENT_VERSION, migrate


class JsonConfigRepository(ConfigSectionsMixin):
    """Cấu hình đọc/ghi từ một file JSON, bí mật để trong ``SecretStore``.

    ``secrets`` để None nghĩa là không có kho bí mật — mọi thứ vẫn chạy, chỉ
    là ``api_key`` lấy nguyên từ file như trước. Cần vậy để chuyển dần
    (R02-T05) chứ không phải đổi một phát cả app.

    Các nhóm cấu hình đọc thẳng từ dict (``code``, ``teams``, ``history``,
    connector, những thứ đã gieo sẵn…) nằm ở
    ``config_sections.py::ConfigSectionsMixin``: chúng không có logic nào
    riêng, chỉ đặt tên cho một khoá và một giá trị mặc định, nên để chung chỉ
    làm trôi mất phần thật sự có hành vi của lớp này.
    """

    def __init__(self, path: Path, *, secrets: SecretStore | None = None,
                 defaults: Dict[str, Any] | None = None,
                 env_overrides=None):
        """Mở một file cấu hình.

        ``defaults``/``env_overrides`` để None thì lấy thẳng từ ``config.py`` — hai
        bên phải dùng chung một bộ mặc định trong suốt giai đoạn chuyển, nếu không
        ứng dụng sẽ thấy hai bộ cấu hình khác nhau tuỳ đường nào gọi tới.
        """
        self._file = AtomicJsonFile(path)
        self._secrets = secrets
        # Lấy thẳng từ config.py để hai bên không lệch nhau trong lúc chuyển.
        if defaults is None or env_overrides is None:
            from ... import config as legacy
            defaults = defaults if defaults is not None else legacy.DEFAULT_CONFIG
            env_overrides = env_overrides or legacy._apply_env_overrides
        self._defaults = defaults
        self._env_overrides = env_overrides
        self.data: Dict[str, Any] = self._load()

    @classmethod
    def from_data(cls, data: Dict[str, Any], path: Path):
        """Dựng từ dict có sẵn — KHÔNG đọc đĩa, KHÔNG nâng cấp schema.

        Dành cho test: chúng dựng cấu hình trong bộ nhớ rồi mới ghi. Đi qua
        ``__init__`` thường thì nó đọc file (chưa có) và có thể chạy migration
        trên dữ liệu test, tức là test đo nhầm thứ khác.
        """
        obj = cls.__new__(cls)
        obj._file = AtomicJsonFile(Path(path))
        obj._secrets = None
        from ... import config as legacy
        obj._defaults = legacy.DEFAULT_CONFIG
        obj._env_overrides = legacy._apply_env_overrides
        obj.data = data
        return obj

    # ---- nạp ------------------------------------------------------------
    def _load(self) -> Dict[str, Any]:
        """Đọc file JSON, nâng cấp schema rồi trộn lên trên bộ mặc định."""
        merged = copy.deepcopy(self._defaults)
        stored = self._file.read(default=None)
        if isinstance(stored, dict):
            # Nâng cấp TRƯỚC khi trộn với mặc định: bước v1→v2 gỡ api_key khỏi
            # đĩa, mà mặc định thì không có khoá nào để gỡ.
            stored, changed = migrate(stored, secrets=self._secrets,
                                      path=self._file.path)
            merged = _deep_merge(merged, stored)
            if changed:
                self.data = merged
                self.save()      # ghi ngay, để lần sau khỏi chuyển lại
        merged = self._env_overrides(merged)
        # Trạng thái mở khoá ms365 chỉ tồn tại lúc chạy — mỗi lần mở app đều
        # bắt đầu ở trạng thái khoá, không tin giá trị đọc từ đĩa.
        merged.setdefault("ms365", {})["unlocked"] = False
        return merged

    def reload(self) -> None:
        """Đọc lại toàn bộ cấu hình từ đĩa, bỏ mọi sửa đổi chưa ``save()``."""
        self.data = self._load()

    # ---- provider --------------------------------------------------------
    @property
    def active_provider(self) -> str:
        """Id provider đang chọn ('openai_compat', 'anthropic', ...); '' nếu chưa đặt."""
        return self.data.get("active_provider", "")

    @active_provider.setter
    def active_provider(self, name: str) -> None:
        """``AppConfig`` cũ cho gán thẳng, và 3 chỗ trong app.py đang gán. Bỏ
        setter đi thì Qt nuốt AttributeError trong slot và triệu chứng là
        "bấm không ăn", không có lỗi nào hiện ra — mất hẳn một buổi mới truy
        ra. Refactor thì hành vi nhìn từ ngoài phải y hệt."""
        self.data["active_provider"] = name

    def set_active_provider(self, name: str) -> None:
        """Đổi provider đang dùng. Bản hàm của property cùng tên, cho chỗ gọi thích
        gọi hàm hơn gán thuộc tính.
        """
        self.data["active_provider"] = name

    def provider_conf(self, name: str | None = None) -> Dict[str, Any]:
        """Cấu hình provider, có sẵn ``api_key``.

        Trả về BẢN SAO: chỗ gọi sửa dict này thì không được âm thầm ghi ngược
        vào cấu hình — và quan trọng hơn, khoá vừa ghép vào không được lẫn
        ngược vào ``self.data`` rồi theo ``save()`` xuống đĩa.
        """
        name = name or self.active_provider
        conf = dict(self.data.get("providers", {}).get(name, {}))
        if self._secrets is not None:
            stored = self._secrets.get(provider_key(name))
            if stored:
                conf["api_key"] = stored
        return conf

    def set_api_key(self, name: str, value: str) -> None:
        """Lưu khoá vào kho bí mật, và xoá khỏi cấu hình trên đĩa.

        Đây là nửa còn lại của đường A: dict *đọc ra* vẫn có ``api_key``,
        nhưng file JSON *trên đĩa* thì không — điều kiện để qua CASAN Check 1.
        """
        if self._secrets is not None:
            self._secrets.set(provider_key(name), value)
            self.data.setdefault("providers", {}).setdefault(name, {})["api_key"] = ""
        else:
            self.data.setdefault("providers", {}).setdefault(name, {})["api_key"] = value

    # ---- đường dẫn -------------------------------------------------------
    @property
    def shared_dir(self) -> str:
        """Thư mục dùng chung (OneDrive/mạng) chứa tài khoản và agent quản trị; '' là
        chưa cấu hình.
        """
        return self.data.get("shared_dir", "")

    def history_dir(self) -> Path:
        """Thư mục chứa lịch sử hội thoại."""
        rt = getattr(self, "_project_history_dir", None) or self.data.get("_project_history_dir")
        if rt:
            return Path(rt)
        custom = (self.data.get("history", {}).get("custom_dir") or "").strip()
        if custom:
            return Path(custom).expanduser()
        from ...config import CONFIG_DIR
        return CONFIG_DIR / "history"

    def cowork_output_dir(self) -> Path:
        """Thư mục agent ghi kết quả ra."""
        custom = (self.data.get("cowork", {}).get("output_dir") or "").strip()
        if custom:
            return Path(custom).expanduser()
        from ... import paths
        from ...config import CONFIG_DIR
        root = paths.primary_onedrive_root()
        if root is not None:
            return root / "CoworkLocal" / "output"
        return CONFIG_DIR / "output" / "cowork"

    # ---- giao diện -------------------------------------------------------
    @property
    def theme(self) -> str:
        """Giao diện đang chọn: 'dark' | 'light' | 'system'. Mặc định 'dark'."""
        return self.data.get("theme", "dark")

    @theme.setter
    def theme(self, value: str) -> None:
        """Đổi giao diện. Chỉ ghi vào bộ nhớ — phải ``save()`` mới xuống đĩa."""
        self.data["theme"] = value

    def set_theme(self, value: str) -> None:
        """Đổi giao diện sáng/tối. Bản hàm của property ``theme``."""
        self.data["theme"] = value

    @property
    def language(self) -> str:
        """Mã ngôn ngữ đang chọn: 'vi' | 'en' | 'ja'. Mặc định 'vi'."""
        return self.data.get("language", "vi")

    @language.setter
    def language(self, value: str) -> None:
        """Đổi ngôn ngữ. Chỉ ghi vào bộ nhớ — phải ``save()`` mới xuống đĩa."""
        self.data["language"] = value

    def set_language(self, value: str) -> None:
        """Đổi ngôn ngữ. Bản hàm của property ``language``."""
        self.data["language"] = value

    # ---- nhóm cấu hình ---------------------------------------------------
    @property
    def routing(self) -> Dict[str, Any]:
        """Nhóm ``routing``: chế độ tự chọn model và các thiết lập riêng theo bề mặt chat."""
        return self.data.setdefault("routing", {})

    @property
    def auth(self) -> Dict[str, Any]:
        """Nhóm ``auth``: thiết lập đăng nhập. Bản này không có lớp đăng nhập nên
        thường rỗng.
        """
        return self.data.setdefault("auth", {})

    @property
    def agent_security(self) -> Dict[str, Any]:
        """Nhóm ``agent_security``: ngưỡng rủi ro và các mục agent phải xin phép."""
        return self.data.setdefault("agent_security", {})

    @property
    def tools_disabled(self) -> list[str]:
        """Danh sách tool BỊ TẮT.

        Lưu theo chiều "bị tắt" chứ không phải "được bật": tool mới thêm vào bản
        cập nhật sẽ tự chạy được mà không cần ai vào bật thủ công.

        Trả về BẢN SAO — sửa danh sách phải đi qua ``set_tool_enabled`` để còn ghi
        đĩa.
        """
        return list(self.data.get("tools_disabled", []))

    def set_tool_enabled(self, name: str, enabled: bool) -> None:
        """Bật/tắt một tool. Lưu dưới dạng danh sách tool BỊ TẮT nên tool mới"""
        disabled = list(self.data.get("tools_disabled", []))
        if enabled:
            disabled = [t for t in disabled if t != name]
        elif name not in disabled:
            disabled.append(name)
        self.data["tools_disabled"] = disabled


    # ---- phần bù để thay được AppConfig ----------------------------------
    # 21 thành viên dưới đây chép nguyên ngữ nghĩa từ ``config.py::AppConfig``.
    # Không phải thiết kế mới: chừng nào 29 file còn gọi qua ``ctx.config`` thì
    # repository phải trả lời được đúng những câu hỏi cũ, nếu không thì không
    # tráo được. Dọn lại là việc của các R sau, không phải của R02.

    #: Các chế độ định tuyến. Delta thêm "fallback" ở R03-T03. Định nghĩa ở đây
    #: là bản chính; ``tests/test_config_repository.py`` có bài đối chiếu với
    #: ``config.py`` để hai bên lệch nhau là đỏ ngay.
    ROUTING_MODES = ("off", "auto", "manual", "fallback")
    #: Chế độ người dùng còn chọn được. "off"/"fallback" đã bỏ khỏi giao diện;
    #: giá trị cũ còn lưu trong config/project (hoặc giá trị lạ) đều hiểu là "auto".
    USER_ROUTING_MODES = ("auto", "manual")

    @classmethod
    def user_routing_mode(cls, mode: str) -> str:
        """Quy một giá trị đã lưu về chế độ người dùng chọn được (mặc định "auto")."""
        return mode if mode in cls.USER_ROUTING_MODES else "auto"

    @classmethod
    def load(cls, path: Path | None = None, *, secrets: SecretStore | None = None):
        """Dựng repository từ đường dẫn mặc định — thay ``AppConfig.load()``."""
        if path is None:
            from ... import config as legacy
            path = legacy.CONFIG_PATH
        return cls(Path(path), secrets=secrets)

    @property
    def path(self) -> Path:
        """Đường dẫn file config.json đang dùng."""
        return self._file.path

    # ---- TLS -------------------------------------------------------------

    @property
    def ca_bundle(self) -> str:
        """Đường dẫn file PEM riêng, hoặc '' để kiểm chứng chỉ như bình thường.

        Dùng làm tham số ``verify=`` của ``requests`` cho mọi lượt gọi HTTPS."""
        return (self.data.get("tls_ca_bundle") or "").strip()

    @ca_bundle.setter
    def ca_bundle(self, value: str) -> None:
        """Đặt file PEM riêng; chuỗi rỗng nghĩa là quay về kiểm chứng chỉ mặc định."""
        self.data["tls_ca_bundle"] = (value or "").strip()

    # ---- MS365 -----------------------------------------------------------

    @property
    def ms365(self) -> Dict[str, Any]:
        """Nhóm ``ms365``: thiết lập Microsoft 365 kèm mã mở khoá phía giao diện."""
        return self.data.setdefault("ms365", copy.deepcopy(self._defaults["ms365"]))

    def ms365_try_unlock(self, code: str) -> bool:
        """Mở khoá nhóm MS365 trong Cài đặt cho phiên này.

        Đây là khoá phía giao diện (chặn bấm nhầm vào một mục nhạy cảm), KHÔNG
        phải xác thực Microsoft. Không bao giờ được lưu ở trạng thái đã mở."""
        if (code or "") and code == self.ms365.get("unlock_code", ""):
            self.data["ms365"]["unlocked"] = True
            return True
        return False

    def ms365_lock(self) -> None:
        """Khoá lại nhóm MS365 trong Cài đặt. Trạng thái khoá chỉ tồn tại lúc chạy."""
        self.data.setdefault("ms365", {})["unlocked"] = False

    # ---- định tuyến theo từng bề mặt chat --------------------------------

    def routing_mode_for(self, surface: str) -> str:
        """Chế độ có hiệu lực cho một bề mặt chat.

        Đặt riêng cho bề mặt thì thắng; để trống thì lấy ``switch_mode`` chung.
        Chỉ còn Auto/Manual: "off", "fallback" cũ hay giá trị lạ đều hiểu là "auto"."""
        routing = self.routing
        override = (routing.get("surface_modes", {}) or {}).get(surface, "")
        return self.user_routing_mode(override or routing.get("switch_mode", ""))

    def set_routing_mode_for(self, surface: str, mode: str) -> None:
        """Đặt chế độ định tuyến riêng cho một bề mặt chat, ghi đĩa ngay."""
        mode = self.user_routing_mode(mode)
        self.routing.setdefault("surface_modes", {})[surface] = mode
        self.save()

    # ---- tiện ích --------------------------------------------------------

    def model_label(self) -> str:
        """Tên model đang dùng, để hiện trên thanh trạng thái; '?' nếu chưa đặt."""
        return str(self.provider_conf().get("model", "?"))

    # ---- ghi -------------------------------------------------------------
    def save(self) -> None:
        """Ghi nguyên tử. Không bao giờ để lộ trạng thái mở khoá ms365."""
        to_write = self.data
        if self.data.get("ms365", {}).get("unlocked"):
            to_write = copy.deepcopy(self.data)
            to_write["ms365"]["unlocked"] = False
        to_write.pop("_project_history_dir", None)
        to_write["schema_version"] = CURRENT_VERSION
        self._file.write(to_write)


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Trộn sâu — giống hệt ``config.py::_deep_merge``.

    Không import lại từ đó vì file này phải sống được sau khi ``config.py``
    biến mất; giữ bản sao 6 dòng còn hơn giữ một sợi dây phụ thuộc.
    """
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out
