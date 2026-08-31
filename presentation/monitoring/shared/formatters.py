"""Formatting helpers shared by the Monitoring tabs — timestamps, byte
counts, and the per-agent colour-coded initials avatar.

Extracted from ``ui/monitoring_tab.py`` verbatim (same output for the same
input); the three timestamp formatters used to each repeat their own
``datetime.fromisoformat`` + ``try/except (TypeError, ValueError)`` guard —
that parse step is now a single shared ``_parse_iso`` helper.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap

from ....i18n import tr


def _parse_iso(ts: str) -> Optional[datetime]:
    """Đọc chuỗi thời gian ISO; sai định dạng thì trả ``None``."""
    try:
        return datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None


def fmt_bytes(n: float) -> str:
    """Đổi số byte sang chuỗi dễ đọc (B / KB / MB / GB)."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def fmt_event_time(ts: str) -> str:
    """"dd/MM hh:mm" for the Time column — e.g. 25/05 15:03."""
    dt = _parse_iso(ts)
    return dt.strftime("%d/%m %H:%M") if dt else ts


_MIDDLE_DOT = chr(0xB7)


def fmt_event_time_full(ts: str) -> str:
    """"dd/MM/yyyy [middle dot] HH:mm:ss" — the detail panel's Thoi gian field."""
    dt = _parse_iso(ts)
    return dt.strftime(f"%d/%m/%Y {_MIDDLE_DOT} %H:%M:%S") if dt else ts


def relative_time(ts: str) -> str:
    """A short "Xm ago"-style string for an audit-log ``ts``; "" if
    unparsable."""
    dt = _parse_iso(ts)
    if dt is None:
        return ""
    delta = (datetime.now() - dt).total_seconds()
    if delta < 60:
        return tr("monitoring.time_just_now")
    if delta < 3600:
        return tr("monitoring.time_minutes_ago", n=int(delta // 60))
    if delta < 86400:
        return tr("monitoring.time_hours_ago", n=int(delta // 3600))
    return tr("monitoring.time_days_ago", n=int(delta // 86400))


def event_id(ts: str, row: int) -> str:
    """A display-only id in the ``evt_<timestamp digits>_<row>`` shape the
    mockup uses — the real audit log has no native event id, so this is
    derived from the timestamp and the row's position in the currently
    displayed (sorted) table, not persisted anywhere."""
    digits = "".join(ch for ch in ts if ch.isdigit())[:12]
    return f"evt_{digits}_{row:03d}"


def agent_initials(name: str) -> str:
    """First letter of each word, max 2."""
    return "".join(w[0] for w in name.split() if w)[:2].upper()


def agent_avatar_colour(name: str) -> str:
    """A fixed identity colour per agent kind, unchanged by theme."""
    if "Security" in name:
        return "#D13438"
    if "Cowork" in name:
        return "#0078D4"
    if name == "schedule" or "Task" in name:
        return "#FFB900"
    if name == "graphrag" or "Knowledge" in name:
        return "#8764B8"
    if "Code" in name:
        return "#107C10"
    if "Planner" in name or "Reasoning" in name:
        return "#8A8886"
    return "#0078D4"


def agent_avatar_icon(name: str, size: int = 20) -> QIcon:
    """A small round initials badge for the Agent column."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(agent_avatar_colour(name)))
    p.drawEllipse(0, 0, size, size)
    font = QFont()
    font.setPixelSize(max(7, size // 2))
    font.setBold(True)
    p.setFont(font)
    p.setPen(QColor("#FFFFFF"))
    p.drawText(pm.rect(), Qt.AlignCenter, agent_initials(name))
    p.end()
    return QIcon(pm)
