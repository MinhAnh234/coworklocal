"""Task 1 (sub-step 6a) — presentation/monitoring/shared helpers.

Only the pure-Python functions are covered here (no PySide6 widget
instantiation needed, no pytest-qt required). Values are asserted against
what ``ui/monitoring_tab.py``'s original, now-removed private functions
produced, so this doubles as a characterization test proving the extraction
didn't change output.
"""
from __future__ import annotations

from cowork_local.presentation.monitoring.shared import badges, formatters


def test_fmt_bytes() -> None:
    assert formatters.fmt_bytes(500) == "500 B"
    assert formatters.fmt_bytes(2048) == "2 KB"


def test_fmt_event_time_and_full_and_relative_are_unparsable_safe() -> None:
    assert formatters.fmt_event_time("not-a-timestamp") == "not-a-timestamp"
    assert formatters.fmt_event_time_full("not-a-timestamp") == "not-a-timestamp"
    assert formatters.relative_time("not-a-timestamp") == ""


def test_fmt_event_time_formats_valid_iso_timestamp() -> None:
    assert formatters.fmt_event_time("2026-05-25T15:03:00") == "25/05 15:03"
    # The separator is computed via datetime.strftime with a literal
    # non-ASCII character in the format string, same as the pre-refactor
    # ui/monitoring_tab.py code — on a Windows box whose locale ANSI codepage
    # has no direct mapping for U+00B7 (MIDDLE DOT), strftime's encode/decode
    # round trip through that codepage can substitute a different but
    # visually similar character (observed: U+30FB on a ja_JP/cp932 locale).
    # That behavior is unchanged by this refactor either way, so the test
    # computes the expected separator the exact same way the implementation
    # does, rather than assuming byte 0xB7 survives on every locale.
    import datetime as _dt
    expected_full = _dt.datetime(2026, 5, 25, 15, 3, 7).strftime(
        f"%d/%m/%Y {formatters._MIDDLE_DOT} %H:%M:%S")
    assert formatters.fmt_event_time_full("2026-05-25T15:03:07") == expected_full


def test_event_id_shape() -> None:
    assert formatters.event_id("2026-05-25T15:03:00", 7) == "evt_202605251503_007"


def test_agent_initials() -> None:
    assert formatters.agent_initials("Cowork Agent") == "CA"
    assert formatters.agent_initials("graphrag") == "G"


def test_agent_avatar_colour_identity_mapping() -> None:
    assert formatters.agent_avatar_colour("Security Agent") == "#D13438"
    assert formatters.agent_avatar_colour("Cowork Agent") == "#0078D4"
    assert formatters.agent_avatar_colour("unknown-agent") == "#0078D4"


def test_action_label_falls_back_to_raw_name_when_unmapped() -> None:
    assert badges.action_label("some_custom_tool") == "some_custom_tool"


def test_status_info_security_block_unmapped_defaults_to_blocked() -> None:
    tone, key = badges.status_info("some_new_rule", kind="security_block", ok=False)
    assert (tone, key) == ("badgePurple", "monitoring.status_blocked")


def test_status_info_mcp_call_falls_back_to_ok_flag() -> None:
    assert badges.status_info("search", kind="mcp_call", ok=True) == ("badgeSuccess", "monitoring.status_ok")
    assert badges.status_info("search", kind="mcp_call", ok=False) == ("badgeDanger", "monitoring.status_failed")


def test_severity_info_dangerous_command_is_critical() -> None:
    assert badges.severity_info("run_command") == ("badgeDanger", "monitoring.severity_critical")


def test_agent_badge_name_identity_mapping() -> None:
    assert badges.agent_badge_name("Security Agent") == "badgeDanger"
    assert badges.agent_badge_name("graphrag") == "badgePurple"
    assert badges.agent_badge_name("unknown") == "badge"
