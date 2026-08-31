"""Task 5 — Sandbox Capability Matrix: pure OS/risk-tier policy, no execution,
no PySide6, no dependency on core/sandbox_manager.py.
"""
from __future__ import annotations

from cowork_local.infrastructure.sandbox import sandbox_capabilities as sc


def test_detect_os_from_injected_platform_name() -> None:
    assert sc.detect_os("win32") == sc.WINDOWS
    assert sc.detect_os("linux") == sc.LINUX
    assert sc.detect_os("darwin") == sc.MACOS
    assert sc.detect_os("some-other-os") == sc.UNKNOWN


def test_windows_matches_todays_real_backends() -> None:
    matrix = sc.SandboxCapabilityMatrix(operating_system=sc.WINDOWS)
    names = {b.name for b in matrix.available_backends()}
    assert names == {"direct", "integrity_job_wfp", "appcontainer", "windows_sandbox"}


def test_windows_routing_matches_core_sandbox_manager_today() -> None:
    matrix = sc.SandboxCapabilityMatrix(operating_system=sc.WINDOWS)
    assert matrix.select_backend(sc.SAFE) == "integrity_job_wfp"
    assert matrix.select_backend(sc.MODERATE) == "integrity_job_wfp"
    assert matrix.select_backend(sc.HIGH) == "appcontainer"
    assert matrix.select_backend(sc.CRITICAL) == "windows_sandbox"


def test_linux_has_no_real_backend_yet() -> None:
    matrix = sc.SandboxCapabilityMatrix(operating_system=sc.LINUX)
    available = {b.name for b in matrix.available_backends()}
    assert available == {"direct"}   # namespaces_bubblewrap declared but not implemented
    assert matrix.select_backend(sc.SAFE) == "direct"        # SAFE/MODERATE only ever wanted direct
    # HIGH's preferred backend (namespaces_bubblewrap) isn't implemented, and
    # HIGH's routing table names "blocked" as the explicit next preference
    # (not a silent fallback to unisolated "direct") — a HIGH-risk command
    # must never quietly downgrade to no isolation just because the real
    # sandbox backend is missing on this OS.
    assert matrix.select_backend(sc.HIGH) == "blocked"
    assert matrix.select_backend(sc.CRITICAL) == "blocked"


def test_macos_has_no_real_backend_yet() -> None:
    matrix = sc.SandboxCapabilityMatrix(operating_system=sc.MACOS)
    available = {b.name for b in matrix.available_backends()}
    assert available == {"direct"}


def test_disallowing_direct_fallback_blocks_instead() -> None:
    # LINUX's own HIGH routing already names "blocked" explicitly, so it
    # doesn't exercise the allow_direct_fallback branch. Register a profile
    # whose HIGH tier names only an unavailable backend (no explicit
    # "direct"/"blocked" entry) to exercise the bottom-of-select_backend
    # fallback path directly.
    os_name = "test-os-fallback"
    profile = sc.OsSandboxProfile(
        operating_system=os_name,
        backends=(sc.SandboxBackend("direct", "none", True),),
        routing={sc.SAFE: ("direct",), sc.MODERATE: ("direct",),
                sc.HIGH: ("not_yet_implemented",), sc.CRITICAL: ("not_yet_implemented",)},
    )
    sc.register_profile(profile)
    try:
        allowed = sc.SandboxCapabilityMatrix(operating_system=os_name, allow_direct_fallback=True)
        disallowed = sc.SandboxCapabilityMatrix(operating_system=os_name, allow_direct_fallback=False)
        assert allowed.select_backend(sc.HIGH) == "direct"
        assert disallowed.select_backend(sc.HIGH) == "blocked"
        # CRITICAL never falls back to direct even when allowed.
        assert allowed.select_backend(sc.CRITICAL) == "blocked"
    finally:
        del sc._PROFILES[os_name]


def test_unknown_os_always_blocks() -> None:
    matrix = sc.SandboxCapabilityMatrix(operating_system=sc.UNKNOWN)
    assert matrix.available_backends() == ()
    for tier in (sc.SAFE, sc.MODERATE, sc.HIGH, sc.CRITICAL):
        assert matrix.select_backend(tier) == "blocked"


def test_registering_a_brand_new_os_requires_no_class_changes() -> None:
    freebsd = "freebsd"
    profile = sc.OsSandboxProfile(
        operating_system=freebsd,
        backends=(sc.SandboxBackend("direct", "none", True),),
        routing={sc.SAFE: ("direct",), sc.MODERATE: ("direct",),
                sc.HIGH: ("blocked",), sc.CRITICAL: ("blocked",)},
    )
    sc.register_profile(profile)
    try:
        matrix = sc.SandboxCapabilityMatrix(operating_system=freebsd)
        assert matrix.select_backend(sc.SAFE) == "direct"
        assert matrix.select_backend(sc.HIGH) == "blocked"
    finally:
        del sc._PROFILES[freebsd]   # don't leak state into other tests


def test_no_pyside6_or_subprocess_dependency() -> None:
    assert "PySide6" not in sc.__dict__
    assert "subprocess" not in sc.__dict__
