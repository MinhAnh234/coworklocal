"""Cấu hình ứng dụng — interface, chưa phải cài đặt.

Hợp đồng số 2 của mục chung. Đây là thứ gỡ chốt lớn nhất: **156 lời gọi
``ctx.config.*`` nằm rải trong 29 file**, nên nếu N2 và N3 phải đợi
``ConfigRepository`` bản thật (R02-T02, hạn 23/08) thì hai người mất mấy ngày
đầu ngồi không.

Danh sách thuộc tính dưới đây không bịa ra: đếm trực tiếp chỗ đang gọi trong
``core/``, ``ui/``, ``providers/`` và ``app.py`` rồi lấy những cái được dùng
thật, xếp theo số lần gọi.

Một chỗ cố ý KHÔNG đưa vào: ``config.data`` (36 lần gọi, nhiều nhất). Đó là
đống dict thô — cho nó vào interface là bê nguyên vấn đề cũ sang kiến trúc mới.
Ai đang cần ``data`` thì mở issue để bổ sung một thuộc tính có kiểu rõ ràng.

SEAM · dựng 2026-08-21 · chưa nối dây (F-05)
------------------------------------------------------------
Được nối khi: một chỗ chú thích kiểu thật sự nhận ``ConfigRepository`` thay vì ``AppConfig``.
Để dormant thì sao: Protocol không ai chú thích tới thì không có bộ kiểm
kiểu nào đối chiếu nó với ``JsonConfigRepository``, nên hai bên lệch nhau
lúc nào không hay.

Cổng ``scripts/check_orphan_modules.py`` đếm tuổi seam từ ngày trên
và nhắc khi quá ``SEAM_MAX_AGE_DAYS``. Đổi nội dung dòng đó thì cổng
đọc theo — đừng sửa ngày để làm im lời nhắc.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Protocol, runtime_checkable


@runtime_checkable
class ConfigRepository(Protocol):
    """Đọc/ghi cấu hình. Cài đặt thật dùng ``AtomicJsonFile`` (R02-T01/T02)."""

    # ---- provider ------------------------------------------------------
    @property
    def active_provider(self) -> str:
        """Tên provider đang chọn (24 lời gọi)."""
        ...

    def set_active_provider(self, name: str) -> None:
        """Đổi provider đang dùng."""
        ...

    def provider_conf(self, name: str | None = None) -> Dict[str, Any]:
        """Cấu hình của một provider (9 lời gọi).

        CHÚ Ý — điểm còn bỏ ngỏ, xem ``docs/refactor/GammaTeam_decisions.md``:
        dict này còn chứa ``api_key`` hay không là quyết định chưa chốt. Có 5
        nơi đang đọc trực tiếp, 3 trong số đó thuộc ``providers/`` của Team Duy.
        """
        ...

    # ---- đường dẫn -----------------------------------------------------
    @property
    def shared_dir(self) -> str:
        """Thư mục dùng chung cho telemetry nhiều máy (10 lời gọi)."""
        ...

    def history_dir(self) -> Path:
        """Thư mục lịch sử chat của project đang chọn (7 lời gọi)."""
        ...

    def cowork_output_dir(self) -> Path:
        """Thư mục Cowork ghi kết quả ra (6 lời gọi)."""
        ...

    # ---- giao diện -----------------------------------------------------
    @property
    def theme(self) -> str:
        """``"dark"`` | ``"light"`` | ``"system"`` (8 lời gọi)."""
        ...

    def set_theme(self, value: str) -> None:
        """Đổi giao diện sáng/tối."""
        ...

    @property
    def language(self) -> str:
        """``"vi"`` | ``"en"`` | ``"ja"`` (4 lời gọi)."""
        ...

    def set_language(self, value: str) -> None:
        """Đổi ngôn ngữ hiển thị."""
        ...

    # ---- các nhóm cấu hình còn lại -------------------------------------
    @property
    def routing(self) -> Dict[str, Any]:
        """Cấu hình định tuyến model (7 lời gọi)."""
        ...

    @property
    def auth(self) -> Dict[str, Any]:
        """Cấu hình đăng nhập (6 lời gọi)."""
        ...

    @property
    def agent_security(self) -> Dict[str, Any]:
        """Chính sách an toàn cho agent (5 lời gọi)."""
        ...

    @property
    def tools_disabled(self) -> list[str]:
        """Tool bị tắt (2 lời gọi)."""
        ...

    def set_tool_enabled(self, name: str, enabled: bool) -> None:
        """Bật/tắt một tool theo tên."""
        ...

    # ---- ghi ------------------------------------------------------------
    def save(self) -> None:
        """Ghi xuống đĩa. Bản thật ghi atomic — tạm + fsync + thay thế —
        nên tắt máy giữa chừng không làm hỏng file (R02-T01).
        """
        ...
