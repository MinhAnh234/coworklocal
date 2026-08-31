"""Khung nhìn có kiểu cho từng nhóm cấu hình — R02-T03.

Vấn đề đang có: khắp nơi viết ``ctx.config.routing.get("switch_mode", "off")``.
Gõ sai một chữ thì lặng lẽ nhận giá trị mặc định, không ai biết cho tới khi
tính năng "không hiểu sao không chạy". Đếm được **156 lời gọi ``ctx.config.*``
trong 29 file** kiểu đó.

Ở đây mỗi nhóm cấu hình có một lớp: gõ sai tên thuộc tính là lỗi ngay, và kiểu
dữ liệu ghi rõ ràng nên đọc code là biết ``confirm_timeout_sec`` là số giây
chứ không phải mili giây.

Cố ý KHÔNG dùng dataclass đông cứng: đây là *khung nhìn* lên dict cấu hình
sống, sửa qua đây là sửa vào dict rồi ``save()`` là xuống đĩa. Sao chép thành
dataclass thì lại sinh chuyện đồng bộ hai chiều.

SEAM · dựng 2026-08-22 · chưa nối dây (F-05)
------------------------------------------------------------
Được nối khi: ít nhất một trong 156 lời gọi ``ctx.config.*`` chuyển sang đọc qua ``Settings``.
Để dormant thì sao: Mục đích của nó là chặn lỗi gõ sai tên khoá. Không ai
dùng thì không chặn được gì cả.

Cổng ``scripts/check_orphan_modules.py`` đếm tuổi seam từ ngày trên
và nhắc khi quá ``SEAM_MAX_AGE_DAYS``. Đổi nội dung dòng đó thì cổng
đọc theo — đừng sửa ngày để làm im lời nhắc.
"""
from __future__ import annotations

from typing import Any, Dict


class _View:
    """Khung nhìn lên một nhánh của dict cấu hình."""

    def __init__(self, data: Dict[str, Any]):
        """Bọc một nhánh dict cấu hình để đọc bằng thuộc tính thay vì tra khoá."""
        self._d = data

    def _get(self, key: str, default: Any) -> Any:
        """Đọc một khoá, coi ``None`` như thiếu.

        Cấu hình cũ có chỗ ghi ``null``; nếu trả thẳng ``None`` ra ngoài thì
        ``str(None)`` thành chuỗi "None" và lỗi hiện ra ở tận nơi dùng.
        """
        value = self._d.get(key, default)
        return default if value is None else value

    def raw(self) -> Dict[str, Any]:
        """Dict gốc — dùng khi cần đọc khoá chưa được đưa vào khung nhìn.

        Có mặt để không ai bị kẹt: thiếu thuộc tính thì dùng tạm ``raw()`` rồi
        mở issue bổ sung, chứ đừng vòng lại ``ctx.config.data``.
        """
        return self._d


class ProviderSettings(_View):
    """Một provider: đi đâu, model nào, khoá nào.

    ``api_key`` ở đây là thứ ``JsonConfigRepository.provider_conf()`` đã ghép
    sẵn từ kho bí mật — xem đường A trong ``GammaTeam_decisions.md``.
    """

    @property
    def base_url(self) -> str:
        """Endpoint của provider. '' nghĩa là chưa cấu hình."""
        return str(self._get("base_url", ""))

    @property
    def model(self) -> str:
        """Model mặc định của provider này. '' nghĩa là chưa chọn."""
        return str(self._get("model", ""))

    @property
    def api_key(self) -> str:
        """Khoá API — đã được ``provider_conf()`` ghép từ kho bí mật của hệ điều hành."""
        return str(self._get("api_key", ""))

    @property
    def configured(self) -> bool:
        """Đủ thông tin để gọi được chưa.

        Ollama chạy cục bộ nên không cần khoá — đó là lý do điều kiện là
        "có base_url và model", không phải "có api_key".
        """
        return bool(self.base_url and self.model)


class RoutingSettings(_View):
    """Định tuyến model tự động (``core/routing/``)."""

    @property
    def switch_mode(self) -> str:
        """``"off"`` | ``"auto"`` | ``"manual"``."""
        return str(self._get("switch_mode", "off"))

    @switch_mode.setter
    def switch_mode(self, value: str) -> None:
        """Đặt chế độ định tuyến chung. Sửa thẳng vào dict cấu hình sống."""
        self._d["switch_mode"] = value

    @property
    def enabled(self) -> bool:
        """Định tuyến tự động có đang bật không (tức ``switch_mode`` khác "off")."""
        return self.switch_mode != "off"

    @property
    def policy(self) -> str:
        """``"balanced"`` | ``"cheap"`` | ``"quality"``…"""
        return str(self._get("policy", "balanced"))

    @property
    def min_score_gain(self) -> float:
        """Phải hơn model hiện tại bao nhiêu điểm mới đáng đổi."""
        return float(self._get("min_score_gain", 0.05))

    @property
    def confirm_timeout_sec(self) -> int:
        """GIÂY, không phải mili giây — đọc tên là biết, khỏi phải mò."""
        return int(self._get("confirm_timeout_sec", 60))

    @property
    def reassess_interval_hours(self) -> int:
        """GIỜ giữa hai lần chấm điểm lại danh mục model."""
        return int(self._get("reassess_interval_hours", 24))

    @property
    def per_provider_concurrency(self) -> int:
        """Số lượt gọi chạy song song tối đa cho mỗi provider khi dò/chấm điểm."""
        return int(self._get("per_provider_concurrency", 2))

    @property
    def judge_provider(self) -> str:
        """Provider dùng làm trọng tài chấm điểm model. '' nghĩa là dùng provider đang chọn."""
        return str(self._get("judge_provider", ""))

    @property
    def judge_model(self) -> str:
        """Model dùng làm trọng tài chấm điểm. '' nghĩa là dùng model mặc định của trọng tài."""
        return str(self._get("judge_model", ""))


class SecuritySettings(_View):
    """Chính sách an toàn cho agent (``core/agent_security.py``)."""

    @property
    def enabled(self) -> bool:
        """Công tắc tổng của lớp an toàn. Tắt là bỏ qua mọi bước kiểm dưới đây."""
        return bool(self._get("enabled", True))

    @property
    def validate_prompt(self) -> bool:
        """Có quét prompt người dùng tìm dấu hiệu tấn công tiêm lệnh không."""
        return bool(self._get("validate_prompt", True))

    @property
    def validate_attachments(self) -> bool:
        """Có kiểm tệp đính kèm (đuôi/kiểu MIME nguy hiểm) trước khi đưa vào lượt chat không."""
        return bool(self._get("validate_attachments", True))

    @property
    def validate_commands(self) -> bool:
        """Có phân loại rủi ro lệnh shell trước khi chạy không."""
        return bool(self._get("validate_commands", True))

    @property
    def command_ai_check(self) -> bool:
        """Có nhờ thêm AI xét lệnh khi bộ luật tĩnh chưa chắc chắn không. Mặc định tắt vì tốn một lượt gọi."""
        return bool(self._get("command_ai_check", False))

    @property
    def cowork_confirm_commands(self) -> bool:
        """Có hỏi trước khi chạy lệnh không.

        Ứng với ``PolicyOutcome.ASK`` trong
        ``domain/security/tool_policy.py``.
        """
        return bool(self._get("cowork_confirm_commands", True))

    @property
    def rules_onedrive_url(self) -> str:
        """Link OneDrive tới bộ luật an toàn dùng chung. '' nghĩa là dùng bản đóng gói sẵn trong app."""
        return str(self._get("rules_onedrive_url", ""))

    @property
    def admin_email(self) -> str:
        """Email quản trị nhận cảnh báo vi phạm. '' nghĩa là không gửi."""
        return str(self._get("admin_email", ""))


class Settings:
    """Cửa vào duy nhất cho các nhóm cấu hình có kiểu.

    >>> s = Settings(repo)
    >>> if s.routing.enabled and s.provider().configured:
    ...     ...
    """

    def __init__(self, repo):
        """Bọc một ``ConfigRepository`` — mọi lượt đọc/ghi đều đi xuống nó, lớp này chỉ
        đổi cách gọi cho dễ đọc.
        """
        self._repo = repo

    def provider(self, name: str | None = None) -> ProviderSettings:
        """Khung nhìn cấu hình của một provider; bỏ trống thì lấy provider đang chọn."""
        return ProviderSettings(self._repo.provider_conf(name))

    @property
    def routing(self) -> RoutingSettings:
        """Khung nhìn nhóm cấu hình định tuyến model."""
        return RoutingSettings(self._repo.routing)

    @property
    def security(self) -> SecuritySettings:
        """Khung nhìn nhóm cấu hình an toàn cho agent."""
        return SecuritySettings(self._repo.agent_security)
