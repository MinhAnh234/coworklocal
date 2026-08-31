"""Sandbox capability matrix — which isolation backends exist on which OS,
and which one a given risk tier should prefer.

Pure policy/data: no subprocess execution, no PySide6, no dependency on
``core/sandbox_manager.py`` (that module owns the actual execution and isn't
in this task's editable scope — this matrix is a standalone, independently
testable module ready for that module's owner to wire in later).

The Windows entries mirror what ``core/sandbox_manager.py`` +
``core/appcontainer_sandbox.py``/``core/windows_sandbox_vm.py``/
``core/integrity_sandbox.py`` already implement today. Linux/macOS entries
are declared but marked ``implemented=False`` — today those platforms have no
real isolation backend (confirmed: ``core/appcontainer_sandbox.py`` and
``core/windows_sandbox_vm.py`` both hard-return ``False`` off Windows) — so
this matrix reports that honestly instead of pretending capabilities that
don't exist yet. Adding a real Linux/macOS backend later is a 1-line flip of
``implemented`` plus whatever backend module implements it; adding a whole
new OS is a call to :func:`register_profile`, no changes to
:class:`SandboxCapabilityMatrix` itself.

SEAM · dựng 2026-08-25 · chưa nối dây (F-05)
------------------------------------------------------------
Được nối khi: ``core/sandbox_manager.py`` chọn backend bằng ma trận này thay cho chuỗi ``if`` theo hệ điều hành.
Để dormant thì sao: Ma trận mô tả cả những backend CHƯA có bản cài. Không ai
đọc thì nó lệch với thực tế lúc nào không biết.

Cổng ``scripts/check_orphan_modules.py`` đếm tuổi seam từ ngày trên
và nhắc khi quá ``SEAM_MAX_AGE_DAYS``. Đổi nội dung dòng đó thì cổng
đọc theo — đừng sửa ngày để làm im lời nhắc.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

# Plain string constants (like core/audit_log.py's ``Kind``) rather than an
# Enum, so a brand-new OS can be registered without editing a closed type.
WINDOWS = "windows"
LINUX = "linux"
MACOS = "macos"
UNKNOWN = "unknown"

# Risk tiers — same vocabulary as security/command_risk_classifier.RiskLevel,
# kept as plain strings here so this module has zero dependency on the
# ``security/`` package (out of scope for this task).
SAFE = "SAFE"
MODERATE = "MODERATE"
HIGH = "HIGH"
CRITICAL = "CRITICAL"

BLOCKED = "blocked"
DIRECT = "direct"


def detect_os(platform_name: Optional[str] = None) -> str:
    """``platform_name`` defaults to ``sys.platform`` but can be injected for
    testing (e.g. ``detect_os("linux")``, ``detect_os("darwin")``)."""
    name = platform_name if platform_name is not None else sys.platform
    if name.startswith("win"):
        return WINDOWS
    if name.startswith("linux"):
        return LINUX
    if name.startswith("darwin"):
        return MACOS
    return UNKNOWN


@dataclass(frozen=True)
class SandboxBackend:
    """Một cơ chế cách ly cụ thể của hệ điều hành.

    ``implemented`` phân biệt cái đã có bản cài thật với cái mới chỉ khai báo —
    ma trận này mô tả cả những gì CHƯA làm, nên thiếu cờ đó thì nó nói dối.
    """
    name: str
    isolation_level: str   # "none" | "resource_limits" | "restricted_token" | "namespace" | "seatbelt" | "full_vm"
    implemented: bool      # whether a real backend exists today, vs. a declared placeholder


@dataclass(frozen=True)
class OsSandboxProfile:
    """Hồ sơ sandbox của một hệ điều hành: có những backend nào và mức rủi ro nào
    thì ưu tiên backend nào.
    """
    operating_system: str
    backends: Tuple[SandboxBackend, ...]
    # risk tier -> ordered list of preferred backend names (first available wins)
    routing: Dict[str, Tuple[str, ...]]


def _profile(operating_system: str, backends: Tuple[SandboxBackend, ...],
            routing: Dict[str, Tuple[str, ...]]) -> OsSandboxProfile:
    """Dựng một ``OsSandboxProfile`` — chỉ để bảng khai báo bên dưới đọc gọn hơn."""
    return OsSandboxProfile(operating_system=operating_system, backends=backends, routing=routing)


_WINDOWS_PROFILE = _profile(
    WINDOWS,
    backends=(
        SandboxBackend(DIRECT, "none", True),
        SandboxBackend("integrity_job_wfp", "resource_limits", True),
        SandboxBackend("appcontainer", "restricted_token", True),
        SandboxBackend("windows_sandbox", "full_vm", True),
    ),
    routing={
        SAFE: ("integrity_job_wfp", DIRECT),
        MODERATE: ("integrity_job_wfp", DIRECT),
        HIGH: ("appcontainer", "integrity_job_wfp"),
        CRITICAL: ("windows_sandbox", "appcontainer", BLOCKED),
    },
)

_LINUX_PROFILE = _profile(
    LINUX,
    backends=(
        SandboxBackend(DIRECT, "none", True),
        SandboxBackend("namespaces_bubblewrap", "namespace", False),  # not implemented yet
    ),
    routing={
        SAFE: (DIRECT,),
        MODERATE: (DIRECT,),
        HIGH: ("namespaces_bubblewrap", BLOCKED),
        CRITICAL: (BLOCKED,),
    },
)

_MACOS_PROFILE = _profile(
    MACOS,
    backends=(
        SandboxBackend(DIRECT, "none", True),
        SandboxBackend("sandbox_exec", "seatbelt", False),  # not implemented yet
    ),
    routing={
        SAFE: (DIRECT,),
        MODERATE: (DIRECT,),
        HIGH: ("sandbox_exec", BLOCKED),
        CRITICAL: (BLOCKED,),
    },
)

_UNKNOWN_PROFILE = _profile(
    UNKNOWN,
    backends=(),
    routing={SAFE: (BLOCKED,), MODERATE: (BLOCKED,), HIGH: (BLOCKED,), CRITICAL: (BLOCKED,)},
)

_PROFILES: Dict[str, OsSandboxProfile] = {
    WINDOWS: _WINDOWS_PROFILE,
    LINUX: _LINUX_PROFILE,
    MACOS: _MACOS_PROFILE,
    UNKNOWN: _UNKNOWN_PROFILE,
}


def register_profile(profile: OsSandboxProfile) -> None:
    """Extension point for a brand-new OS: build an :class:`OsSandboxProfile`
    and register it once — no change to :class:`SandboxCapabilityMatrix`
    needed. Overwrites any existing profile for the same
    ``operating_system`` name (lets a caller override the built-in Windows/
    Linux/macOS profiles too, e.g. once a real Linux backend ships)."""
    _PROFILES[profile.operating_system] = profile


class SandboxCapabilityMatrix:
    """Answers, for one OS: which backends are actually available today, and
    which one a given risk tier should prefer. Read-only policy — does not
    execute anything."""

    def __init__(self, operating_system: Optional[str] = None,
                allow_direct_fallback: bool = True) -> None:
        """``operating_system`` để None thì tự dò hệ điều hành đang chạy.

        Hệ không có hồ sơ rơi về hồ sơ "không biết": thà chạy ở mức bảo thủ còn hơn
        coi như không có ràng buộc nào.
        """
        self.operating_system = operating_system if operating_system is not None else detect_os()
        self._profile = _PROFILES.get(self.operating_system, _UNKNOWN_PROFILE)
        self.allow_direct_fallback = allow_direct_fallback

    def all_backends(self) -> Tuple[SandboxBackend, ...]:
        """Every backend declared for this OS, implemented or not."""
        return self._profile.backends

    def available_backends(self) -> Tuple[SandboxBackend, ...]:
        """Only backends with a real implementation today."""
        return tuple(b for b in self._profile.backends if b.implemented)

    def select_backend(self, risk_level: str) -> str:
        """The backend name to use for ``risk_level`` on this OS — the first
        available (implemented) backend in that tier's preference order, else
        ``"direct"`` when allowed for a non-CRITICAL tier, else ``"blocked"``."""
        available_names = {b.name for b in self.available_backends()}
        preferred = self._profile.routing.get(risk_level.upper(), ())
        for name in preferred:
            if name == BLOCKED:
                return BLOCKED
            if name in available_names:
                return name
        if (self.allow_direct_fallback and DIRECT in available_names
                and risk_level.upper() != CRITICAL):
            return DIRECT
        return BLOCKED
