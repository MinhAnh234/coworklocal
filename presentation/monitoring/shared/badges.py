"""Badge/label vocabulary shared by the Monitoring event tables and detail
panel — human labels for a raw audit ``name``, and the (QSS object name,
i18n key) pair for the "Trạng thái"/"Mức độ" pills.

``apply_badge`` replaces the two byte-identical
``_EventDetailPanel._apply_badge`` / ``MonitoringTab._set_badge`` static
methods the original file duplicated.
"""
from __future__ import annotations

from typing import Tuple

from PySide6.QtWidgets import QLabel

from ....i18n import tr

# Human label for the raw ``name`` an audit event is recorded under — the
# "Loại" field in the detail panel. Anything not in this map (custom tool
# names, etc.) just shows its raw name, same as the table's Hành động column.
_ACTION_LABEL_KEYS = {
    "prompt": "monitoring.action_prompt",
    "dangerous_command": "monitoring.action_dangerous_command",
    "run_command": "monitoring.action_dangerous_command",
    "install_package": "monitoring.action_install_package",
    "path_outside_sandbox": "monitoring.action_path_outside_sandbox",
    "network_blocked": "monitoring.action_network_blocked",
    "secret_in_output": "monitoring.action_secret_in_output",
}


def action_label(name: str) -> str:
    """Nhãn đã dịch của một loại hành động; không có trong bảng thì trả nguyên tên."""
    key = _ACTION_LABEL_KEYS.get(name)
    return tr(key) if key else name


# (badge QSS object name, i18n key) for the "Trạng thái" pill, mapped onto
# the app's existing badge* tones (theme.py).
_STATUS_INFO = {
    "path_outside_sandbox": ("badgeSuccess", "monitoring.status_path"),
    "network_blocked": ("badge", "monitoring.status_network"),
    "secret_in_output": ("badgeWarn", "monitoring.status_secret"),
}
_STATUS_DEFAULT = ("badgePurple", "monitoring.status_blocked")


def status_info(name: str, kind: str = "security_block", ok: bool = False) -> Tuple[str, str]:
    """Cặp (tên style, khoá dịch) cho huy hiệu trạng thái của một sự kiện."""
    if name in _STATUS_INFO:
        return _STATUS_INFO[name]
    if kind == "security_block":
        # Security Events rows are always ok=False — an unmapped name here
        # still means "blocked by some rule", never a plain failure.
        return _STATUS_DEFAULT
    # MCP calls / generic Action Logs rows: no fixed enforcement-rule
    # vocabulary applies, so fall back to the event's own ok/fail outcome.
    return ("badgeSuccess", "monitoring.status_ok") if ok else ("badgeDanger", "monitoring.status_failed")


def severity_info(name: str, kind: str = "security_block", ok: bool = False) -> Tuple[str, str]:
    # An unapproved shell command is the one CRITICAL case; everything else
    # blocked is MEDIUM.
    """Cặp (tên style, khoá dịch) cho huy hiệu mức nghiêm trọng.

    Lệnh shell chạy mà chưa được duyệt là trường hợp NGHIÊM TRỌNG duy nhất; mọi
    thứ bị chặn khác đều ở mức trung bình.
    """
    if name in ("dangerous_command", "run_command"):
        return "badgeDanger", "monitoring.severity_critical"
    if kind == "security_block":
        return "badgeWarn", "monitoring.severity_medium"
    # A successful MCP call / action is routine (INFO); a failed one still
    # deserves the same MEDIUM tone Security Events uses for a blocked rule.
    return ("badge", "monitoring.severity_info") if ok else ("badgeWarn", "monitoring.severity_medium")


def agent_badge_name(name: str) -> str:
    """Badge tone for the Agent field's pill — the same identity-colour
    mapping ``formatters.agent_avatar_colour`` uses, expressed as one of the
    shared badge* QSS classes (theme.py) instead of a literal hex."""
    if "Security" in name:
        return "badgeDanger"
    if "Cowork" in name:
        return "badge"
    if name == "schedule":
        return "badgeWarn"
    if name == "graphrag":
        return "badgePurple"
    if "Code" in name:
        return "badgeSuccess"
    return "badge"


def apply_badge(label: QLabel, object_name: str) -> None:
    """Gán style cho một nhãn huy hiệu và ép Qt vẽ lại.

    Phải ``unpolish``/``polish`` vì Qt không tự áp lại QSS khi ``objectName`` đổi.
    """
    label.setObjectName(object_name)
    label.style().unpolish(label)
    label.style().polish(label)
