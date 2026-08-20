"""📊 Monitoring Dashboard — live view over the Sandbox / MCP / Agent Core
layers, built entirely from data those layers already produce:

- **Overview**       — a card-based dashboard (Token Usage & Cost, Resource
  Usage, Recent Activity, Sandbox Details, Permissions, Audit Log), using
  only real state from the panels below (no fabricated numbers).
- **Security Events**  — the audit log (``core/audit_log.py``) filtered to
  ``kind="security_block"``.
- **MCP Call History** — the audit log filtered to ``kind="mcp_call"``.
- **Action Logs**      — the full audit log, newest first.
- **Agent Status**     — which ``agent_roles`` (see ``core/agent_roles.py``)
  are currently running, read from the existing ``ChatPanel._active``/
  ``TaskScheduler._workers``/GraphRAG-ask-worker state — no new runtime
  tracking of its own.

Each panel is a thin, read-only VIEW — this module owns no state that
outlives a refresh tick (besides a one-sample I/O cache used to compute
instantaneous disk/network rates between ticks).
"""
from __future__ import annotations

import os
import time
from datetime import datetime
from typing import List

from PySide6.QtCore import Qt, QEvent, QObject, QRect, QSize, QTimer, Signal
from PySide6.QtGui import (
    QBrush, QColor, QFont, QGuiApplication, QIcon, QKeySequence, QPainter,
    QPixmap, QShortcut,
)
from PySide6.QtWidgets import (
    QApplication, QComboBox, QGridLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QProgressBar, QPushButton, QScrollArea,
    QSplitter, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from ..core import agent_roles, audit_log
from ..core import usage_tracker as ut
from ..i18n import on_language_changed, tr
from ..state import AppContext
from ..theme import current_palette
from .icons import icon, DOT_GREEN, DOT_RED, DOT_AMBER
from .widgets import BudgetCard, StatCard, badge_pill_widget, fmt_tokens

_REFRESH_MS = 3000
_MAX_ROWS = 300


def _fmt_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _fmt_event_time(ts: str) -> str:
    """"dd/MM hh:mm" for the Time column — e.g. 25/05 15:03."""
    try:
        dt = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return ts
    return dt.strftime("%d/%m %H:%M")


def _agent_initials(name: str) -> str:
    """First letter of each word, max 2 — ``ini()`` in ui-audit_v2.html."""
    return "".join(w[0] for w in name.split() if w)[:2].upper()


def _agent_avatar_colour(name: str) -> str:
    """Same mapping as ``ac()`` in ui-audit_v2.html — a fixed identity colour
    per agent kind, unchanged by theme (like the mockup's badge colours)."""
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


def _agent_avatar_icon(name: str, size: int = 20) -> QIcon:
    """A small round initials badge for the Agent column — 1:1 with the
    ``.wf .av`` avatar in ui-audit_v2.html (colour-coded circle + up to
    2-letter initials, drawn to the left of the agent's name)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(_agent_avatar_colour(name)))
    p.drawEllipse(0, 0, size, size)
    font = QFont()
    font.setPixelSize(max(7, size // 2))
    font.setBold(True)
    p.setFont(font)
    p.setPen(QColor("#FFFFFF"))
    p.drawText(pm.rect(), Qt.AlignCenter, _agent_initials(name))
    p.end()
    return QIcon(pm)


def _relative_time(ts: str) -> str:
    """A short "Xm ago"-style string for an audit-log ``ts`` (naive local
    ISO timestamp, see ``audit_log.record``); "" if unparsable."""
    try:
        then = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return ""
    delta = (datetime.now() - then).total_seconds()
    if delta < 60:
        return tr("monitoring.time_just_now")
    if delta < 3600:
        return tr("monitoring.time_minutes_ago", n=int(delta // 60))
    if delta < 86400:
        return tr("monitoring.time_hours_ago", n=int(delta // 3600))
    return tr("monitoring.time_days_ago", n=int(delta // 86400))


class _TimeItem(QTableWidgetItem):
    """The Time column shows "dd/MM hh:mm", which does not sort correctly as
    text (day-of-month leads, not year/month) — so sorting compares the raw
    ISO ``ts`` each item is built from instead of its displayed text."""

    def __init__(self, raw_ts: str, display: str):
        super().__init__(display)
        self._raw_ts = raw_ts

    def __lt__(self, other):
        if isinstance(other, _TimeItem):
            return self._raw_ts < other._raw_ts
        return super().__lt__(other)


class _EventTable(QTableWidget):
    """A read-only table of audit-log events — newest-first by default, and
    every column header is click-to-sort (ascending/descending toggle; the
    Time column sorts by the underlying ISO timestamp, not its "dd/MM hh:mm"
    display text — see :class:`_TimeItem`)."""

    # What each blocked action is, as a colour. Security events all record
    # ok=False, so the tick/cross column said the same thing on every row; the
    # useful distinction is WHICH rule fired.
    _ACTION_TINTS = {
        "prompt": "accent",
        "dangerous_command": "danger",
        "run_command": "danger",
        "install_package": "warning",
        "path_outside_sandbox": "success",
        "network_blocked": "accent",
        "secret_in_output": "warning",
    }

    def __init__(self, show_result: bool = True):
        # Security Events drops the result column entirely (see _ACTION_TINTS).
        self._show_result = show_result
        super().__init__(0, 7 if show_result else 6)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setIconSize(QSize(20, 20))   # ~1.25x the mockup's 16x16 avatar badge
        self.verticalHeader().setVisible(False)
        # Fixed row height — letting Qt auto-size rows from content fought with
        # the Hành động column's cell widget (its layout would settle on a
        # stale, oversized geometry from an intermediate sizing pass, clipping
        # the pill's text). A fixed height sidesteps that entirely.
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.verticalHeader().setDefaultSectionSize(32)
        self.setSortingEnabled(True)
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        for col in range(self.columnCount() - 1):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)

    def retranslate(self) -> None:
        # Security Events (show_result=False) is the ui-audit_v2.html
        # wireframe's table 1:1 — "Agent" and "Chi tiết chặn", not the
        # longer generic wording MCP/Action Logs share.
        cols = [tr("monitoring.col_time"),
                tr("monitoring.col_agent") if not self._show_result else tr("monitoring.col_role"),
                tr("monitoring.col_account"), tr("monitoring.col_machine")]
        if self._show_result:
            cols += [tr("monitoring.col_name"), tr("monitoring.col_result")]
        else:
            cols += [tr("monitoring.col_action")]
        cols += [tr("monitoring.col_detail_block") if not self._show_result else tr("monitoring.col_detail")]
        self.setHorizontalHeaderLabels(cols)

    def set_events(self, events: List[dict]) -> None:
        events = sorted(events, key=lambda e: e.get("ts", ""), reverse=True)[:_MAX_ROWS]
        self.setSortingEnabled(False)
        self.setRowCount(len(events))
        for row, ev in enumerate(events):
            is_admin_violation = ev.get("role") == "admin" and not ev.get("ok", True)
            cells = [
                ev.get("ts", ""), agent_roles.label_for(ev.get("agent_role", "")),
                ev.get("account", "") or "—", ev.get("machine", "") or "—",
                ev.get("name", ""),
            ]
            if self._show_result:
                cells.append("")
            cells.append((ev.get("detail") or "")[:300])
            pal = current_palette()
            for col, text in enumerate(cells):
                item = (_TimeItem(str(text), _fmt_event_time(str(text))) if col == 0
                        else QTableWidgetItem(str(text)))
                if col == 0:
                    # Stash the full event (untruncated detail included) on the
                    # Time cell, so a click-to-open detail panel survives the
                    # user re-sorting the table by any column.
                    item.setData(Qt.UserRole, ev)
                if col == 1:
                    # Agent — colour-coded initials avatar (see ui-audit_v2.html).
                    item.setIcon(_agent_avatar_icon(str(text)))
                if self._show_result and col == 5:
                    # Result — green check / red close icon (no emoji)
                    item.setIcon(icon("check", color=DOT_GREEN) if ev.get("ok")
                                 else icon("close", color=DOT_RED))
                if not self._show_result and col == 4:
                    # Human-readable label ("Path ngoài sandbox"), not the raw
                    # audit_log name ("path_outside_sandbox") — same wording as
                    # the detail panel's Loại field (_action_label). Tinted by
                    # which rule fired, via the ITEM's own colours — NOT a
                    # setCellWidget() pill: a cell widget is pinned to a (row,
                    # column) screen position, not to the item that travels
                    # with a sort, so the table's OWN re-sort (every refresh()
                    # re-applies the active sort indicator, and a user click on
                    # any column header does too) left a stale pill floating
                    # over whatever row ended up at that position instead —
                    # the "wrong colour/text peeking out" glitch.
                    tint = getattr(pal, self._ACTION_TINTS.get(
                        ev.get("name", ""), "text_muted"), pal.text_muted)
                    item.setText(_action_label(str(text)))
                    colour = QColor(tint)
                    item.setForeground(QBrush(colour))
                    soft = QColor(colour)
                    soft.setAlpha(38)
                    item.setBackground(QBrush(soft))
                if is_admin_violation:
                    item.setBackground(QBrush(QColor(229, 72, 77, 60)))
                self.setItem(row, col, item)
        self.setSortingEnabled(True)
        self.apply_filter(getattr(self, "_filter_needle", ""))

    def apply_filter(self, needle: str) -> None:
        self._filter_needle = (needle or "").strip().lower()
        for row in range(self.rowCount()):
            if not self._filter_needle:
                self.setRowHidden(row, False)
                continue
            match = any(
                self._filter_needle in (self.item(row, col).text().lower()
                                        if self.item(row, col) else "")
                for col in range(self.columnCount()))
            self.setRowHidden(row, not match)

    def event_at_row(self, row: int) -> dict | None:
        item = self.item(row, 0)
        return item.data(Qt.UserRole) if item else None


def _fmt_event_time_full(ts: str) -> str:
    """"dd/MM/yyyy · HH:mm:ss" — the detail panel's Thời gian field, per
    ``fmtFull()`` in ui-audit_v2.html (the table's own Time column uses the
    shorter ``_fmt_event_time`` instead)."""
    try:
        dt = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return ts
    return dt.strftime("%d/%m/%Y · %H:%M:%S")


def _event_id(ts: str, row: int) -> str:
    """A display-only id in the ``evt_<timestamp digits>_<row>`` shape the
    mockup uses — the real audit log has no native event id, so this is
    derived from the timestamp and the row's position in the currently
    displayed (sorted) table, not persisted anywhere."""
    digits = "".join(ch for ch in ts if ch.isdigit())[:12]
    return f"evt_{digits}_{row:03d}"


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


def _action_label(name: str) -> str:
    key = _ACTION_LABEL_KEYS.get(name)
    return tr(key) if key else name


# (badge QSS object name, i18n key) for the "Trạng thái" pill — statusInfo()
# in ui-audit_v2.html, mapped onto the app's existing badge* tones (theme.py)
# rather than adding the mockup's one-off teal/orange hues.
_STATUS_INFO = {
    "path_outside_sandbox": ("badgeSuccess", "monitoring.status_path"),
    "network_blocked": ("badge", "monitoring.status_network"),
    "secret_in_output": ("badgeWarn", "monitoring.status_secret"),
}
_STATUS_DEFAULT = ("badgePurple", "monitoring.status_blocked")


def _status_info(name: str, kind: str = "security_block", ok: bool = False) -> tuple[str, str]:
    if name in _STATUS_INFO:
        return _STATUS_INFO[name]
    if kind == "security_block":
        # Security Events rows are always ok=False (see _EventTable's
        # _ACTION_TINTS comment) — an unmapped name here still means "blocked
        # by some rule", never a plain failure.
        return _STATUS_DEFAULT
    # MCP calls / generic Action Logs rows: no fixed enforcement-rule
    # vocabulary applies, so fall back to the event's own ok/fail outcome.
    return ("badgeSuccess", "monitoring.status_ok") if ok else ("badgeDanger", "monitoring.status_failed")


def _severity_info(name: str, kind: str = "security_block", ok: bool = False) -> tuple[str, str]:
    # Same two-tier read as ui-audit_v2.html's mock: an unapproved shell
    # command is the one CRITICAL case; everything else blocked is MEDIUM.
    if name in ("dangerous_command", "run_command"):
        return "badgeDanger", "monitoring.severity_critical"
    if kind == "security_block":
        return "badgeWarn", "monitoring.severity_medium"
    # A successful MCP call / action is routine (INFO); a failed one still
    # deserves the same MEDIUM tone Security Events uses for a blocked rule.
    return ("badge", "monitoring.severity_info") if ok else ("badgeWarn", "monitoring.severity_medium")


def _agent_badge_name(name: str) -> str:
    """Badge tone for the Agent field's pill — the same identity-colour
    mapping ``_agent_avatar_colour``/``ac()`` (ui-audit_v2.html) uses,
    expressed as one of the shared badge* QSS classes (theme.py) instead of a
    literal hex, since this pill lives on a themed label, not a custom swatch."""
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


_STATIC_POLICY_LABEL = "security_policy_v2"  # cosmetic label only — no real policy-versioning system exists yet


class _EventDetailPanel(QWidget):
    """Right-hand "Chi tiết sự kiện" panel — the full record behind whichever
    row is selected in an :class:`_EventTable`, laid out to match the
    "Đề xuất" detail panel in ui-audit_v2.html (openDetail()): three labelled
    sections, a terminal-style block quote for the detail text, and a
    METADATA footer, closed by the header ✕, the footer button, Esc, or a
    click outside the table/panel (see :class:`_ClickOutsideCloser`)."""

    closed = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("monSection")
        self._detail_text = ""
        outer = QVBoxLayout(self)

        hdr = QHBoxLayout()
        self._title_lbl = QLabel()
        self._title_lbl.setStyleSheet("font-weight:700;")
        hdr.addWidget(self._title_lbl, 1)
        self._close_btn = QPushButton()
        self._close_btn.setIcon(icon("close"))
        self._close_btn.setFlat(True)
        self._close_btn.setFixedWidth(28)
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.clicked.connect(self.closed.emit)
        hdr.addWidget(self._close_btn)
        outer.addLayout(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        body = QWidget()
        self._body_lay = QVBoxLayout(body)
        self._body_lay.setContentsMargins(0, 0, 4, 0)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        self._section_hdrs: list[tuple[str, QLabel]] = []
        self._rows: dict[str, tuple[QLabel, QLabel]] = {}

        def _section(key: str) -> None:
            lbl = QLabel()
            lbl.setObjectName("detailSectionHdr")
            self._body_lay.addWidget(lbl)
            self._section_hdrs.append((key, lbl))

        def _field(key: str) -> QLabel:
            r = QHBoxLayout()
            lbl = QLabel()
            lbl.setObjectName("hint")
            val = QLabel()
            r.addWidget(lbl)
            r.addStretch(1)
            r.addWidget(val)
            self._body_lay.addLayout(r)
            self._rows[key] = (lbl, val)
            return val

        _section("general")
        _field("time")
        self._agent_val = _field("agent")
        _field("account")
        self._machine_val = _field("machine")
        self._machine_val.setObjectName("monoChip")

        _section("action")
        self._type_val = _field("type")
        self._type_val.setObjectName("neutralTag")
        self._status_val = _field("status")

        _section("block")
        code_box = QWidget()
        code_box.setObjectName("detailCodeBlock")
        code_lay = QHBoxLayout(code_box)
        code_lay.setContentsMargins(8, 6, 8, 6)
        self._code_text = QLabel()
        self._code_text.setObjectName("detailCodeText")
        self._code_text.setWordWrap(True)
        self._code_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        code_lay.addWidget(self._code_text, 1)
        self._copy_btn = QPushButton()
        self._copy_btn.setObjectName("detailCopyBtn")
        self._copy_btn.setCursor(Qt.PointingHandCursor)
        self._copy_btn.clicked.connect(self._copy_detail)
        code_lay.addWidget(self._copy_btn, 0, Qt.AlignVCenter)
        self._body_lay.addWidget(code_box)

        _section("metadata")
        self._event_id_val = _field("event_id")
        self._event_id_val.setObjectName("monoChip")
        self._policy_val = _field("policy")
        self._severity_val = _field("severity")

        self._body_lay.addStretch(1)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 6, 0, 0)
        self._footer_close_btn = QPushButton()
        self._footer_close_btn.setObjectName("primary")
        self._footer_close_btn.setCursor(Qt.PointingHandCursor)
        self._footer_close_btn.clicked.connect(self.closed.emit)
        footer.addWidget(self._footer_close_btn, 1)
        outer.addLayout(footer)

    @staticmethod
    def _apply_badge(label: QLabel, object_name: str) -> None:
        label.setObjectName(object_name)
        label.style().unpolish(label)
        label.style().polish(label)

    def retranslate(self) -> None:
        self._title_lbl.setText(tr("monitoring.security_detail_title"))
        self._close_btn.setToolTip(tr("monitoring.security_detail_close"))
        self._footer_close_btn.setText(tr("monitoring.security_detail_close"))
        self._footer_close_btn.setIcon(icon("close"))
        section_keys = {
            "general": "monitoring.detail_section_general",
            "action": "monitoring.detail_section_action",
            "block": "monitoring.col_detail_block",
            "metadata": "monitoring.detail_section_metadata",
        }
        for key, lbl in self._section_hdrs:
            lbl.setText(tr(section_keys[key]).upper())
        self._rows["time"][0].setText(tr("monitoring.col_time"))
        self._rows["agent"][0].setText(tr("monitoring.col_agent"))
        self._rows["account"][0].setText(tr("monitoring.col_account"))
        self._rows["machine"][0].setText(tr("monitoring.col_machine"))
        self._rows["type"][0].setText(tr("monitoring.detail_type"))
        self._rows["status"][0].setText(tr("monitoring.detail_status"))
        self._rows["event_id"][0].setText(tr("monitoring.detail_event_id"))
        self._rows["policy"][0].setText(tr("monitoring.detail_policy"))
        self._rows["severity"][0].setText(tr("monitoring.detail_severity"))
        if not self._copy_btn.text() or self._copy_btn.text() != tr("monitoring.detail_copied"):
            self._reset_copy_btn()

    def show_event(self, ev: dict, row: int) -> None:
        na = "—"
        self._rows["time"][1].setText(_fmt_event_time_full(ev.get("ts", "")) or na)

        agent_label = agent_roles.label_for(ev.get("agent_role", "")) or na
        self._agent_val.setText(agent_label)
        self._apply_badge(self._agent_val,
                          _agent_badge_name(agent_label) if agent_label != na else "badge")

        self._rows["account"][1].setText(ev.get("account", "") or na)
        self._machine_val.setText(ev.get("machine", "") or na)

        name = ev.get("name", "")
        kind = ev.get("kind", "security_block")
        ok = ev.get("ok", False)
        self._type_val.setText(_action_label(name) or na)
        status_badge, status_key = _status_info(name, kind, ok)
        self._status_val.setText(tr(status_key))
        self._apply_badge(self._status_val, status_badge)

        self._detail_text = ev.get("detail", "") or na
        self._code_text.setText(self._detail_text)
        self._reset_copy_btn()

        self._event_id_val.setText(_event_id(ev.get("ts", ""), row))
        # The static policy label names a real enforcement ruleset — only
        # meaningful for a Security Events row; MCP calls/generic actions
        # were never evaluated against it.
        self._policy_val.setText(_STATIC_POLICY_LABEL if kind == "security_block" else na)
        severity_badge, severity_key = _severity_info(name, kind, ok)
        self._severity_val.setText(tr(severity_key))
        self._apply_badge(self._severity_val, severity_badge)

    def _copy_detail(self) -> None:
        QGuiApplication.clipboard().setText(self._detail_text)
        self._copy_btn.setText(tr("monitoring.detail_copied"))
        self._copy_btn.setIcon(icon("check"))
        QTimer.singleShot(1500, self._reset_copy_btn)

    def _reset_copy_btn(self) -> None:
        self._copy_btn.setText(tr("monitoring.detail_copy"))
        self._copy_btn.setIcon(icon("document"))


class _ClickOutsideCloser(QObject):
    """Closes the event-detail panel on a click anywhere outside the
    table/panel splitter — a row click changes the selection instead (its
    own handler), so this only needs to catch everything else: the search
    box, another tab, the nav rail… mirrors the document-level "click
    outside the panel" listener in ui-audit_v2.html.

    Judged by screen-space GEOMETRY (is the click's global position inside
    the splitter's on-screen rectangle), not by which exact widget object
    received the event. Two earlier attempts both broke on the splitter's
    drag handle: ``QApplication.widgetAt(globalPos)`` re-hit-tests through
    the window server rather than using what Qt actually delivered the event
    to, and even the delivered ``obj`` isn't reliable mid-drag — the handle
    grabs the mouse and Qt's internal drag bookkeeping doesn't always hand
    back the same widget identity a plain ``isAncestorOf`` check expects.
    A geometric rect containment check has neither problem: it doesn't care
    which sub-widget (viewport, cell widget, scrollbar, handle) the event
    was actually delivered to, only whether the click landed on-screen
    within the container's bounds."""

    def __init__(self, table: "_EventTable", panel: "_EventDetailPanel", container: QWidget):
        super().__init__(container)
        self._table = table
        self._panel = panel
        self._container = container

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.MouseButtonPress and self._panel.isVisible():
            global_pos = event.globalPosition().toPoint()
            top_left = self._container.mapToGlobal(self._container.rect().topLeft())
            rect = QRect(top_left, self._container.size())
            if not rect.contains(global_pos):
                self._table.clearSelection()
        return False


class MonitoringTab(QWidget):
    status_message = Signal(str)

    def __init__(self, ctx: AppContext, cowork=None, structure=None, task_scheduler=None):
        super().__init__()
        self.ctx = ctx
        self._cowork = cowork
        self._structure = structure
        self._task_scheduler = task_scheduler
        self._last_io_sample = None

        root = QVBoxLayout(self)
        head = QHBoxLayout()
        self._title = QLabel()
        self._title.setStyleSheet("font-weight:700; font-size:15px;")
        head.addWidget(self._title)
        head.addStretch(1)
        root.addLayout(head)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        # ---- Overview (card dashboard) ----------------------------------
        self.tabs.addTab(self._build_overview_page(), "")

        visible = self._tab_visible
        # Security events are always ok=False, so this table trades the
        # tick/cross column for a tinted Action column (see _EventTable).
        self.security_table = _EventTable(show_result=False)
        self.security_page = self._wrap_with_filter(
            self.security_table, with_detail=True, title_key="monitoring.security_events_title")
        if visible("security_events"):
            self.tabs.addTab(self.security_page, "")
        self.mcp_table = _EventTable()
        self.mcp_page = self._wrap_with_filter(
            self.mcp_table, with_detail=True, title_key="monitoring.mcp_history_title")
        if visible("mcp_history"):
            self.tabs.addTab(self.mcp_page, "")
        self.action_table = _EventTable()
        self.action_page = self._wrap_with_filter(
            self.action_table, with_detail=True, title_key="monitoring.action_logs_title")
        if visible("action_logs"):
            self.tabs.addTab(self.action_page, "")

        # ---- Agent Status -------------------------------------------------
        self.status_table = QTableWidget(0, 3)
        self.status_table.setEditTriggers(QTableWidget.NoEditTriggers)
        # No detail to open on click, no filtering — a plain read-only table,
        # so selection is off rather than left dangling with no effect (and it
        # sidesteps the Trạng thái badge's dark-theme rgba() background ever
        # compositing differently selected vs not — see badge_pill_widget).
        self.status_table.setSelectionMode(QTableWidget.NoSelection)
        self.status_table.verticalHeader().setVisible(False)
        self.status_table.horizontalHeader().setStretchLastSection(True)
        self.status_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.status_table.setColumnWidth(1, 130)   # Trạng thái is a cell widget — size it explicitly
        self.status_table.setIconSize(QSize(20, 20))
        self.status_page = self._wrap_with_filter(
            self.status_table, title_key="monitoring.agent_status_title", with_search=False)
        if visible("agent_status"):
            self.tabs.addTab(self.status_page, "")

        # ---- Agents Admin (catalog: assign a role + pinned model per agent) --
        # The system-management agents (Security, GraphRAG/Knowledge, Monitor…)
        # are defined here — each gets a task_kind (role) and an optional pinned
        # provider/model. Admin-only; since the app runs with full admin access
        # this is always shown.
        from .agents_admin_tab import AgentsAdminTab
        self.agents_admin_tab = AgentsAdminTab(ctx)
        if visible("agents_admin"):
            self.tabs.addTab(self.agents_admin_tab, "")

        # ---- Tools (govern built-in tools + Connectors/MCP in one place) -----
        from .tools_admin_tab import ToolsAdminTab
        self.tools_admin_tab = ToolsAdminTab(ctx)
        if visible("tools_admin"):
            self.tabs.addTab(self.tools_admin_tab, "")

        # ---- Icons (browse built-in icons + add custom icons for agents/flows) --
        from .icons_admin_tab import IconsAdminTab
        self.icons_admin_tab = IconsAdminTab(ctx)
        self.tabs.addTab(self.icons_admin_tab, "")

        self.tabs.setCurrentIndex(0)

        self._timer = QTimer(self)
        # (nav integration methods defined below)
        # Only the Overview cards auto-refresh on this tick — Security, MCP,
        # Action Logs, Agent Status (and the Agents Admin/Tools/Icons tabs,
        # which were never wired to this timer) are read-only tables that a
        # background re-sort would otherwise disturb mid-interaction (e.g.
        # while a row is selected or the detail-panel splitter is being
        # dragged); the user refreshes them explicitly via a "Làm mới" button.
        self._timer.setInterval(_REFRESH_MS)
        self._timer.timeout.connect(self._auto_refresh)
        self._timer.start()

        on_language_changed(self._retranslate)
        self.refresh()

    # ---- nav integration: sub-tabs driven from the left nav rail ------------
    def nav_subtabs(self):
        """(label, index, icon_name) for each sub-tab — the left nav lists these
        as children under 'Monitoring'. Icons are keyed by widget identity so
        they're correct in every language."""
        by_widget = {self.agents_admin_tab: "robot", self.tools_admin_tab: "wrench",
                     self.icons_admin_tab: "star"}
        for attr, name in (("security_page", "shield"), ("mcp_page", "plug"),
                           ("action_page", "bolt"), ("status_page", "monitor")):
            w = getattr(self, attr, None)
            if w is not None:
                by_widget[w] = name
        out = []
        for i in range(self.tabs.count()):
            out.append((self.tabs.tabText(i), i, by_widget.get(self.tabs.widget(i), "dashboard")))
        return out

    def select_subtab(self, index: int) -> None:
        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)

    def hide_tab_bar(self) -> None:
        """Hide the in-content tab strip; the nav rail drives the sub-tabs."""
        self.tabs.tabBar().hide()

    # ---- model pricing list (Overview) --------------------------------------
    def _reload_pricing_table(self, *_a) -> None:
        from ..core import model_pricing as mp
        to_ccy = self.ov_pricing_ccy.currentData() or "USD"
        entries = mp.list_entries(self.ctx.config)
        t = self.ov_pricing_table
        t.setRowCount(len(entries))
        for r, e in enumerate(entries):
            in_v = mp.convert(e.get("input_price", 0), e.get("input_ccy", "USD"), to_ccy, self.ctx.config)
            out_v = mp.convert(e.get("output_price", 0), e.get("output_ccy", "USD"), to_ccy, self.ctx.config)
            vals = [e.get("model", ""), e.get("context_length", ""), e.get("max_output", ""),
                    f"{mp.format_price(in_v, to_ccy)} / {e.get('input_unit', '')}",
                    f"{mp.format_price(out_v, to_ccy)} / {e.get('output_unit', '')}"]
            for c, v in enumerate(vals):
                t.setItem(r, c, QTableWidgetItem(str(v)))

    def _import_pricing(self) -> None:
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from ..core import model_pricing as mp
        path, _ = QFileDialog.getOpenFileName(
            self, tr("monitoring.pricing_import"), "", "Pricing (*.xlsx *.csv)")
        if not path:
            return
        default_ccy = self.ov_pricing_ccy.currentData() or "USD"
        try:
            imported = mp.import_table(path, default_ccy=default_ccy)
        except ValueError as exc:
            QMessageBox.warning(self, tr("monitoring.pricing_title"), str(exc))
            return
        merged = {e["model"]: e for e in mp.list_entries(self.ctx.config)}
        for e in imported:
            merged[e["model"]] = e
        mp.save_entries(self.ctx.config, list(merged.values()))
        self.ctx.save()
        self._reload_pricing_table()
        self.status_message.emit(tr("monitoring.pricing_imported", n=len(imported)))

    def _export_pricing(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        from ..core import model_pricing as mp
        path, _ = QFileDialog.getSaveFileName(
            self, tr("monitoring.pricing_export"), "model_pricing_template.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        mp.export_template(path)
        self.status_message.emit(tr("monitoring.pricing_exported"))

    def _add_pricing_row(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        from ..core import model_pricing as mp
        name, ok = QInputDialog.getText(self, tr("monitoring.pricing_add"),
                                        tr("monitoring.pricing_add_prompt"))
        name = (name or "").strip()
        if not ok or not name:
            return
        ccy = self.ov_pricing_ccy.currentData() or "USD"
        mp.add_entry(self.ctx.config, mp.entry_from_row(
            [name, "", "", "0", "Million tokens", "0", "Million tokens"], default_ccy=ccy))
        self.ctx.save()
        self._reload_pricing_table()

    def _autolink_pricing(self) -> None:
        from ..core import model_pricing as mp
        from ..core.worker import AgentWorker
        if getattr(self, "_pricing_worker", None) is not None:
            return
        self.ov_price_link_btn.setEnabled(False)
        ctx = self.ctx
        ccy = self.ov_pricing_ccy.currentData() or "USD"

        def job(_w):
            return {"entries": mp.auto_link(ctx, default_ccy=ccy)}

        def done(r):
            self._pricing_worker = None
            self.ov_price_link_btn.setEnabled(True)
            self.ctx.save()
            self._reload_pricing_table()
            self.status_message.emit(tr("monitoring.pricing_linked", n=len(r.get("entries", []))))

        def failed(_e):
            self._pricing_worker = None
            self.ov_price_link_btn.setEnabled(True)

        w = AgentWorker(job)
        w.finished_ok.connect(done)
        w.failed.connect(failed)
        self._pricing_worker = w
        w.start()

    def _delete_pricing_row(self) -> None:
        from ..core import model_pricing as mp
        row = self.ov_pricing_table.currentRow()
        entries = mp.list_entries(self.ctx.config)
        if 0 <= row < len(entries):
            del entries[row]
            mp.save_entries(self.ctx.config, entries)
            self.ctx.save()
            self._reload_pricing_table()

    def _wrap_with_filter(self, table: QTableWidget, with_detail: bool = False,
                          title_key: str | None = None, with_search: bool = True) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)

        if title_key:
            # The wireframe titles this tab's content on its own row — "Sự kiện
            # bảo mật" + a primary Refresh button — separately from the section
            # tab strip above (which just says "Bảo mật").
            hdr = QHBoxLayout()
            title_lbl = QLabel(tr(title_key))
            title_lbl.setStyleSheet("font-weight:700; font-size:14px;")
            hdr.addWidget(title_lbl)
            hdr.addStretch(1)
            refresh_btn = QPushButton(tr("monitoring.refresh"))
            refresh_btn.setIcon(icon("refresh"))
            refresh_btn.setObjectName("primary")
            refresh_btn.setCursor(Qt.PointingHandCursor)
            refresh_btn.clicked.connect(self.refresh)
            hdr.addWidget(refresh_btn)
            lay.addLayout(hdr)
            page.title_lbl = title_lbl
            page.title_key = title_key
            page.title_refresh_btn = refresh_btn

        if with_search:
            row = QHBoxLayout()
            search = QLineEdit()
            search.setPlaceholderText(tr("monitoring.filter_placeholder"))
            search.textChanged.connect(table.apply_filter)
            ai_btn = QPushButton(tr("monitoring.ai_filter_btn"))
            ai_btn.setIcon(icon("sparkle"))
            ai_btn.setToolTip(tr("monitoring.ai_filter_tooltip"))
            ai_btn.setCursor(Qt.PointingHandCursor)
            ai_btn.clicked.connect(lambda: self._ai_filter(search, ai_btn))
            row.addWidget(search, 1)
            row.addWidget(ai_btn)
            lay.addLayout(row)
            page.filter_edit = search
            page.ai_filter_btn = ai_btn

        if with_detail:
            # Click a row → its full record opens in a "Chi tiết sự kiện" panel
            # on the right (the table itself clips the detail text to 300 chars).
            # A pointing-hand cursor over the rows signals that they're clickable.
            table.setCursor(Qt.PointingHandCursor)
            detail = _EventDetailPanel()
            detail.setVisible(False)
            detail.closed.connect(table.clearSelection)
            table.itemSelectionChanged.connect(lambda: self._sync_event_detail(table, detail))
            split = QSplitter(Qt.Horizontal)
            split.addWidget(table)
            split.addWidget(detail)
            split.setStretchFactor(0, 1)
            split.setStretchFactor(1, 0)
            split.setChildrenCollapsible(False)
            split.setSizes([700, 320])
            lay.addWidget(split, 1)
            page.detail_panel = detail

            # Esc, anywhere focus is inside this page, closes the panel the
            # same way the close button does.
            esc = QShortcut(QKeySequence(Qt.Key_Escape), page)
            esc.setContext(Qt.WidgetWithChildrenShortcut)
            esc.activated.connect(table.clearSelection)
            page.detail_esc_shortcut = esc

            # A click outside both the table and the panel also closes it —
            # mirrors ui-audit_v2.html's document-level click-outside listener.
            click_filter = _ClickOutsideCloser(table, detail, split)
            QApplication.instance().installEventFilter(click_filter)
            page.detail_click_filter = click_filter
        else:
            lay.addWidget(table, 1)
        return page

    def _sync_event_detail(self, table: "_EventTable", panel: "_EventDetailPanel") -> None:
        # currentRow() alone is not enough: clearSelection() (used by the
        # panel's close button) drops the selection but leaves the current
        # cell in place, so a stale currentRow() would keep the panel open.
        row = table.currentRow()
        has_selection = bool(table.selectedItems())
        ev = table.event_at_row(row) if (has_selection and row >= 0) else None
        if ev:
            panel.show_event(ev, row)
        panel.setVisible(bool(ev))

    def _ai_filter(self, search: QLineEdit, ai_btn: QPushButton) -> None:
        query = search.text().strip()
        if not query or getattr(self, "_ai_filter_worker", None) is not None:
            return
        ai_btn.setEnabled(False)
        ctx = self.ctx

        def job(worker):
            provider = ctx.build_active_provider()
            reply = provider.chat([
                {"role": "system", "content":
                    "Turn the user's natural-language question about an audit/security event "
                    "log into ONE short search keyword. Reply with ONLY the keyword."},
                {"role": "user", "content": query},
            ], cancel=worker.is_cancelled)
            return {"keyword": (reply.get("content") or "").strip().splitlines()[0][:60]}

        def done(result: dict) -> None:
            self._ai_filter_worker = None
            ai_btn.setEnabled(True)
            search.setText(result.get("keyword") or query)

        def failed(_err: str) -> None:
            self._ai_filter_worker = None
            ai_btn.setEnabled(True)

        from ..core.worker import AgentWorker
        w = AgentWorker(job)
        w.finished_ok.connect(done)
        w.failed.connect(failed)
        self._ai_filter_worker = w
        w.start()

    # ---- Overview page construction ------------------------------------
    def _build_overview_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll)

        # ONE main column, scrolled vertically, sections in a fixed order — the
        # two-column grid put six group boxes side by side and mixed three
        # unrelated concerns (cost, machine resources, security) at the same
        # level, which made this the densest screen in the app. Each section now
        # spans the full width and lays its own contents out horizontally, so a
        # wide window is still used well.
        root = QVBoxLayout(content)
        root.setSpacing(12)
        left = root                     # sections are appended in reading order
        right = root

        # ---- Token Usage & Cost --------------------------------------------
        self.ov_usage_group = QGroupBox()
        self.ov_usage_group.setObjectName("monSection")
        usage_lay = QGridLayout(self.ov_usage_group)
        usage_lay.setSpacing(8)
        self.ov_usage_total = StatCard()
        self.ov_usage_in = StatCard()
        self.ov_usage_out = StatCard()
        self.ov_usage_cache = StatCard()
        self.ov_usage_cost = StatCard()
        self.ov_usage_calls = StatCard()
        # The wireframe's usage block is five figures: cost (with the turn
        # count on its label), then Tổng token / Input / Output / Cache. Folding
        # the last three into a sub-line took their PER-PART COST off screen —
        # the total tile has room for the token counts but not for three more
        # prices — and the drawing asks for the tiles anyway.
        for i, card in enumerate((self.ov_usage_cost, self.ov_usage_total,
                                  self.ov_usage_in, self.ov_usage_out,
                                  self.ov_usage_cache)):
            usage_lay.addWidget(card, 0, i)
        self.ov_usage_calls.setVisible(False)   # rides on the cost tile's label
        # Budget: remaining/budget, direct entry, auto-warns red past 85% used —
        # same box (and same usage.budget_* config) as the Dashboard's.
        self.ov_budget_card = BudgetCard()
        self.ov_budget_card.apply_btn.setIcon(icon("check"))
        self.ov_budget_card.apply_btn.clicked.connect(self._apply_budget)
        usage_lay.addWidget(self.ov_budget_card, 0, 3)
        # Equal stretch on every column — otherwise the grid sizes each column
        # to its widest cell's natural content (Budget's longer "$X / $Y" value
        # + entry row makes its column wider than the plain stat cards).
        for col in range(4):
            usage_lay.setColumnStretch(col, 1)

        # Unit prices are NOT entered here anymore — the cost total is computed
        # straight from the model pricing table (below). The display-currency
        # picker moved to the Dashboard (beside its refresh button) — both
        # screens still read/write the SAME usage.currency config key.
        left.addWidget(self.ov_usage_group)

        # ---- Recent Activity ----------------------------------------------
        self.ov_activity_group = QGroupBox()
        self.ov_activity_group.setObjectName("monSection")
        act_lay = QVBoxLayout(self.ov_activity_group)
        self.ov_activity_lbl = QLabel()
        self.ov_activity_lbl.setWordWrap(True)
        self.ov_activity_lbl.setTextFormat(Qt.RichText)
        act_lay.addWidget(self.ov_activity_lbl)
        # added near the bottom, beside the audit log — see below

        # ---- Resource Usage -------------------------------------------------
        self.ov_resource_group = QGroupBox()
        self.ov_resource_group.setObjectName("monSection")
        # ONE compact line, as the wireframe writes it: name and value sit
        # together and the pairs are separated by a middle dot, packed left —
        # spread across the full width they read as four unrelated columns with
        # the value stranded at the far edge of a 1900px screen.
        res_lay = QHBoxLayout(self.ov_resource_group)
        res_lay.setSpacing(6)
        self._res_first = True

        def _pair():
            if not self._res_first:
                sep = QLabel("·")
                sep.setObjectName("hint")
                res_lay.addWidget(sep)
            self._res_first = False
            lbl = QLabel(); lbl.setObjectName("hint")
            val = QLabel()
            res_lay.addWidget(lbl)
            res_lay.addWidget(val)
            return lbl, val

        def _bar_row():
            # The gauge is kept and updated, but off the line: at a glance the
            # number is what is read, and the bar was drawing a 700px rule.
            lbl, val = _pair()
            bar = QProgressBar()
            bar.setVisible(False)
            return lbl, bar, val

        def _text_row():
            return _pair()

        self.ov_cpu_lbl, self.ov_cpu_bar, self.ov_cpu_val = _bar_row()
        self.ov_mem_lbl, self.ov_mem_bar, self.ov_mem_val = _bar_row()
        self.ov_diskfree_lbl, self.ov_diskfree_val = _text_row()
        # I/O and network rates keep working; they are read from the detail
        # fold rather than the summary line the wireframe draws.
        self.ov_disk_lbl, self.ov_disk_val = QLabel(), QLabel()
        self.ov_network_lbl, self.ov_network_val = QLabel(), QLabel()
        res_lay.addStretch(1)

        # ---- Model pricing (beside the CPU/resource group) ------------------
        self.ov_pricing_group = QGroupBox()
        self.ov_pricing_group.setObjectName("monSection")
        pg = QVBoxLayout(self.ov_pricing_group)
        phdr = QHBoxLayout()
        self.ov_pricing_ccy_lbl = QLabel(); self.ov_pricing_ccy_lbl.setObjectName("hint")
        self.ov_pricing_ccy = QComboBox()
        for cur in ut.SUPPORTED_CURRENCIES:
            self.ov_pricing_ccy.addItem(cur, cur)
        pidx = self.ov_pricing_ccy.findData(
            (self.ctx.config.data.get("usage") or {}).get("currency", "USD"))
        self.ov_pricing_ccy.setCurrentIndex(max(0, pidx))
        self.ov_pricing_ccy.currentIndexChanged.connect(self._reload_pricing_table)
        phdr.addWidget(self.ov_pricing_ccy_lbl)
        phdr.addWidget(self.ov_pricing_ccy)
        phdr.addStretch(1)
        self.ov_price_import_btn = QPushButton(); self.ov_price_import_btn.setIcon(icon("download"))
        self.ov_price_import_btn.clicked.connect(self._import_pricing)
        self.ov_price_export_btn = QPushButton(); self.ov_price_export_btn.setIcon(icon("upload"))
        self.ov_price_export_btn.clicked.connect(self._export_pricing)
        self.ov_price_add_btn = QPushButton(); self.ov_price_add_btn.setIcon(icon("plus"))
        self.ov_price_add_btn.clicked.connect(self._add_pricing_row)
        self.ov_price_link_btn = QPushButton(); self.ov_price_link_btn.setIcon(icon("refresh"))
        self.ov_price_link_btn.clicked.connect(self._autolink_pricing)
        self.ov_price_del_btn = QPushButton(); self.ov_price_del_btn.setIcon(icon("trash"))
        self.ov_price_del_btn.clicked.connect(self._delete_pricing_row)
        for b in (self.ov_price_import_btn, self.ov_price_export_btn, self.ov_price_add_btn,
                  self.ov_price_link_btn, self.ov_price_del_btn):
            phdr.addWidget(b)
        pg.addLayout(phdr)
        self.ov_pricing_table = QTableWidget(0, 5)
        self.ov_pricing_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ov_pricing_table.verticalHeader().setVisible(False)
        self.ov_pricing_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.ov_pricing_table.setSelectionBehavior(QTableWidget.SelectRows)
        pg.addWidget(self.ov_pricing_table, 1)

        # Resources keep the row to themselves; the model price table gets its
        # own full-width section further down (it is a reference table, not a
        # live meter, and squeezing it next to the CPU bars made both unreadable).
        left.addWidget(self.ov_resource_group)
        self._reload_pricing_table()

        # ---- Sandbox Details --------------------------------------------
        self.ov_sandbox_details_group = QGroupBox()
        self.ov_sandbox_details_group.setObjectName("monSection")
        sbx_lay = QVBoxLayout(self.ov_sandbox_details_group)
        self.ov_sbx_summary = QLabel()
        self.ov_sbx_summary.setWordWrap(True)
        sbx_lay.addWidget(self.ov_sbx_summary)
        self.ov_sbx_more_btn = QPushButton()
        self.ov_sbx_more_btn.setObjectName("co4eSectionAction")
        self.ov_sbx_more_btn.setFlat(True)
        self.ov_sbx_more_btn.setCheckable(True)
        self.ov_sbx_more_btn.setCursor(Qt.PointingHandCursor)
        sbx_lay.addWidget(self.ov_sbx_more_btn, 0, Qt.AlignLeft)
        self._sbx_detail = QWidget()
        self._sbx_detail.setVisible(False)
        self.ov_sbx_more_btn.toggled.connect(self._sbx_detail.setVisible)
        self.ov_sbx_more_btn.toggled.connect(self._sync_sbx_more_label)
        sbx_lay.addWidget(self._sbx_detail)
        sbx_lay = QVBoxLayout(self._sbx_detail)
        sbx_lay.setContentsMargins(0, 4, 0, 0)

        def _kv():
            row = QHBoxLayout()
            lbl = QLabel(); lbl.setObjectName("hint")
            val = QLabel()
            row.addWidget(lbl); row.addStretch(1); row.addWidget(val)
            sbx_lay.addLayout(row)
            return lbl, val

        self.ov_sbx_id_lbl, self.ov_sbx_id_val = _kv()
        self.ov_sbx_status_lbl, self.ov_sbx_status_val = _kv()
        self.ov_sbx_status_val.setObjectName("badgeSuccess")
        self.ov_sbx_created_lbl, self.ov_sbx_created_val = _kv()
        self.ov_sbx_uptime_lbl, self.ov_sbx_uptime_val = _kv()

        limits_row = QHBoxLayout()
        self.ov_sbx_limits_lbl = QLabel()
        self.ov_sbx_limits_lbl.setObjectName("hint")
        self.ov_sbx_limits_lbl.setWordWrap(True)
        self.ov_sbx_edit_btn = QPushButton()
        self.ov_sbx_edit_btn.setFlat(True)
        self.ov_sbx_edit_btn.clicked.connect(self._open_settings_and_refresh)
        limits_row.addWidget(self.ov_sbx_limits_lbl, 1)
        limits_row.addWidget(self.ov_sbx_edit_btn)
        sbx_lay.addLayout(limits_row)

        self.ov_sbx_net_lbl, self.ov_sbx_net_val = _kv()
        # Sandbox and Permissions answer the same question ("what is the agent
        # allowed to touch?"), so they share one full-width row.
        root.addWidget(self.ov_sandbox_details_group)

        # ---- Permissions -----------------------------------------------
        self.ov_permissions_group = QGroupBox()
        self.ov_permissions_group.setObjectName("monSection")
        perm_lay = QVBoxLayout(self.ov_permissions_group)

        def _pkv():
            row = QHBoxLayout()
            lbl = QLabel(); lbl.setObjectName("hint")
            val = QLabel()
            row.addWidget(lbl); row.addStretch(1); row.addWidget(val)
            perm_lay.addLayout(row)
            return lbl, val

        self.ov_perm_fs_lbl, self.ov_perm_fs_val = _pkv()
        self.ov_perm_network_lbl, self.ov_perm_network_val = _pkv()
        self.ov_perm_process_lbl, self.ov_perm_process_val = _pkv()
        self.ov_perm_env_lbl, self.ov_perm_env_val = _pkv()
        self.ov_perm_edit_btn = QPushButton()
        self.ov_perm_edit_btn.setFlat(True)
        self.ov_perm_edit_btn.clicked.connect(self._open_settings_and_refresh)
        perm_lay.addWidget(self.ov_perm_edit_btn, 0, Qt.AlignLeft)
        # Inside the same fold as the sandbox rows — one section, one line.
        self._sbx_detail.layout().addWidget(self.ov_permissions_group)

        # ---- Model pricing — its own section, full width ------------------
        root.addWidget(self.ov_pricing_group)

        # ---- What actually happened, last ---------------------------------
        root.addWidget(self.ov_activity_group)

        # ---- Audit Log ----------------------------------------------------
        self.ov_audit_group = QGroupBox()
        self.ov_audit_group.setObjectName("monSection")
        audit_lay = QVBoxLayout(self.ov_audit_group)
        self.ov_audit_lbl = QLabel()
        self.ov_audit_lbl.setWordWrap(True)
        self.ov_audit_lbl.setTextFormat(Qt.RichText)
        audit_lay.addWidget(self.ov_audit_lbl)
        self.ov_view_all_btn = QPushButton()
        self.ov_view_all_btn.setFlat(True)
        self.ov_view_all_btn.clicked.connect(
            lambda: self.tabs.setCurrentIndex(self.tabs.indexOf(self.action_page)))
        audit_lay.addWidget(self.ov_view_all_btn, 0, Qt.AlignRight)
        self.ov_audit_group.setVisible(self._tab_visible("action_logs"))
        right.addWidget(self.ov_audit_group)
        right.addStretch(1)

        return page

    def _open_settings_and_refresh(self) -> None:
        from .settings_dialog import SettingsDialog
        dlg = SettingsDialog(self.ctx, self)
        dlg.exec()
        self.refresh()

    @staticmethod
    def _set_badge(label: QLabel, object_name: str) -> None:
        label.setObjectName(object_name)
        label.style().unpolish(label)
        label.style().polish(label)

    def _tab_visible(self, key: str) -> bool:
        return self.ctx.role == "admin" or bool(self.ctx.config.monitoring_visibility.get(key, True))

    def _set_tab_text_if_present(self, widget, text: str) -> None:
        idx = self.tabs.indexOf(widget)
        if idx >= 0:
            self.tabs.setTabText(idx, text)

    # ---- i18n ------------------------------------------------------------
    def _retranslate(self) -> None:
        self._title.setText(tr("monitoring.title"))
        if self.tabs.count():
            self.tabs.setTabText(0, tr("monitoring.tab_overview"))
        self._set_tab_text_if_present(self.security_page, tr("monitoring.tab_security"))
        self._set_tab_text_if_present(self.mcp_page, tr("monitoring.tab_mcp"))
        self._set_tab_text_if_present(self.action_page, tr("monitoring.tab_actions"))
        self._set_tab_text_if_present(self.status_page, tr("monitoring.tab_agents"))
        self._set_tab_text_if_present(self.agents_admin_tab, tr("monitoring.tab_agents_admin"))
        self._set_tab_text_if_present(self.tools_admin_tab, tr("monitoring.tab_tools"))
        self._set_tab_text_if_present(self.icons_admin_tab, tr("monitoring.tab_icons"))
        self.security_table.retranslate()
        self.mcp_table.retranslate()
        self.action_table.retranslate()
        self.status_table.setHorizontalHeaderLabels([
            tr("monitoring.col_agent"), tr("monitoring.detail_status"), tr("monitoring.col_source"),
        ])

        # A QGroupBox title treats "&" as a mnemonic marker, so "token & Chi
        # phí" rendered as "token _Chi phí". Double it to show a literal "&".
        self.ov_usage_group.setTitle(
            tr("monitoring.overview_usage_title").upper().replace("&", "&&"))
        self.ov_budget_card.apply_btn.setToolTip(tr("usage.budget_apply_tooltip"))
        self.ov_budget_card.budget_spin.setToolTip(tr("usage.budget_spin_tooltip"))

        self.ov_activity_group.setTitle(tr("monitoring.overview_activity_title").upper())
        self.ov_resource_group.setTitle(tr("monitoring.overview_resource_title").upper())
        for page in (self.security_page, self.mcp_page, self.action_page):
            page.filter_edit.setPlaceholderText(tr("monitoring.filter_placeholder"))
            page.detail_panel.retranslate()
            page.title_lbl.setText(tr(page.title_key))
            page.title_refresh_btn.setText(tr("monitoring.refresh"))
        # status_page has no search box and no detail panel (with_search=False,
        # with_detail=False) — just the title + Làm mới header.
        self.status_page.title_lbl.setText(tr(self.status_page.title_key))
        self.status_page.title_refresh_btn.setText(tr("monitoring.refresh"))
        self.ov_cpu_lbl.setText(tr("monitoring.overview_res_cpu"))
        self.ov_mem_lbl.setText(tr("monitoring.overview_res_mem"))
        self.ov_diskfree_lbl.setText(tr("monitoring.overview_disk_label"))
        self.ov_disk_lbl.setText(tr("monitoring.overview_res_disk"))
        self.ov_network_lbl.setText(tr("monitoring.overview_res_network"))
        # model pricing panel
        self.ov_pricing_group.setTitle(tr("monitoring.pricing_title").upper())
        self.ov_pricing_ccy_lbl.setText(tr("monitoring.pricing_currency"))
        self.ov_price_import_btn.setText(tr("monitoring.pricing_import"))
        self.ov_price_export_btn.setText(tr("monitoring.pricing_export"))
        self.ov_price_add_btn.setText(tr("monitoring.pricing_add"))
        self.ov_price_link_btn.setText(tr("monitoring.pricing_autolink"))
        self.ov_price_del_btn.setText(tr("monitoring.pricing_delete"))
        self.ov_pricing_table.setHorizontalHeaderLabels([
            tr("monitoring.pricing_col_model"), tr("monitoring.pricing_col_context"),
            tr("monitoring.pricing_col_maxout"), tr("monitoring.pricing_col_input"),
            tr("monitoring.pricing_col_output")])

        self.ov_sandbox_details_group.setTitle(
            # "&" is a mnemonic marker in a group-box title — double it.
            tr("monitoring.overview_sandbox_details_title").upper().replace("&", "&&"))
        self.ov_sbx_id_lbl.setText(tr("monitoring.overview_sandbox_id"))
        self.ov_sbx_status_lbl.setText(tr("monitoring.overview_status"))
        self.ov_sbx_created_lbl.setText(tr("monitoring.overview_created"))
        self.ov_sbx_uptime_lbl.setText(tr("monitoring.overview_uptime"))
        self.ov_sbx_edit_btn.setText(tr("monitoring.overview_edit"))
        self.ov_sbx_net_lbl.setText(tr("monitoring.overview_network_label"))

        self.ov_permissions_group.setTitle(tr("monitoring.overview_permissions_title").upper())
        self.ov_perm_fs_lbl.setText(tr("monitoring.overview_perm_fs"))
        self.ov_perm_fs_val.setText(tr("monitoring.overview_perm_fs_value"))
        self.ov_perm_network_lbl.setText(tr("monitoring.overview_perm_network"))
        self.ov_perm_process_lbl.setText(tr("monitoring.overview_perm_process"))
        self.ov_perm_process_val.setText(tr("monitoring.overview_perm_process_value"))
        self.ov_perm_env_lbl.setText(tr("monitoring.overview_perm_env"))
        self.ov_perm_env_val.setText(tr("monitoring.overview_perm_env_value"))
        self.ov_perm_edit_btn.setText(tr("monitoring.overview_edit"))

        self.ov_audit_group.setTitle(tr("monitoring.overview_audit_title").upper())
        self.ov_view_all_btn.setText(tr("monitoring.overview_view_all"))

        self.refresh()

    # ---- refresh -----------------------------------------------------------
    def refresh(self) -> None:
        """Full refresh — Overview cards plus every table. Wired to the
        top-of-page and per-section "Làm mới" buttons, called once at
        startup/language-change, but NOT to the auto-refresh timer (see
        ``_auto_refresh``)."""
        self._refresh_resource_usage()
        events = self._load_events()
        self.security_table.set_events([e for e in events if e.get("kind") == "security_block"])
        self.mcp_table.set_events([e for e in events if e.get("kind") == "mcp_call"])
        self.action_table.set_events(events)
        self._refresh_agent_status()
        self._refresh_overview(events)

    def _auto_refresh(self) -> None:
        """3-second timer tick — Overview cards only (see ``refresh``)."""
        self._refresh_resource_usage()
        self._refresh_overview(self._load_events())

    def _load_events(self) -> List[dict]:
        shared_dir = self.ctx.config.shared_dir
        if shared_dir:
            from ..core import telemetry_shared
            shared_events = telemetry_shared.load_shared_audit_events(shared_dir)
            if shared_events:
                return shared_events
        return audit_log.load_events()

    def _refresh_resource_usage(self) -> None:
        try:
            import psutil
        except ImportError:
            self._set_overview_resource_na()
            return

        try:
            own = psutil.Process()
            own_cpu = own.cpu_percent(interval=None)
            own_mem = own.memory_info().rss
        except Exception:
            own, own_cpu, own_mem = None, 0.0, 0

        self.ov_cpu_bar.setValue(int(min(own_cpu, 100)))
        self.ov_cpu_val.setText(f"{own_cpu:.0f}%")
        try:
            total_mem = psutil.virtual_memory().total
            mem_pct = int(own_mem * 100 / total_mem) if total_mem else 0
        except Exception:
            mem_pct = 0
        self.ov_mem_bar.setValue(min(mem_pct, 100))
        try:
            self.ov_mem_val.setText(f"{_fmt_bytes(own_mem)}/{_fmt_bytes(total_mem)}")
        except Exception:                                    # noqa: BLE001
            self.ov_mem_val.setText(_fmt_bytes(own_mem))
        # Free disk on the workspace drive — a capacity fact, unlike the I/O
        # rate that used to sit here, and the one the drawing shows.
        try:
            free = psutil.disk_usage(str(self.ctx.config.cowork_output_dir())).free
            self.ov_diskfree_val.setText(
                tr("monitoring.overview_disk_free", size=_fmt_bytes(free)))
        except Exception:                                    # noqa: BLE001
            self.ov_diskfree_val.setText(tr("monitoring.na"))

        now = time.monotonic()
        try:
            io = own.io_counters() if own is not None else None
            disk_bytes = (io.read_bytes + io.write_bytes) if io is not None else None
        except Exception:
            disk_bytes = None
        try:
            net = psutil.net_io_counters()
            net_bytes = net.bytes_sent + net.bytes_recv
        except Exception:
            net_bytes = None

        prev = self._last_io_sample
        self._last_io_sample = (now, disk_bytes, net_bytes)
        na = tr("monitoring.na")
        if prev and disk_bytes is not None and prev[1] is not None and now > prev[0]:
            rate = max(0.0, (disk_bytes - prev[1]) / (now - prev[0]))
            self.ov_disk_val.setText(f"{_fmt_bytes(rate)}/s")
        else:
            self.ov_disk_val.setText(na)
        if prev and net_bytes is not None and prev[2] is not None and now > prev[0]:
            rate = max(0.0, (net_bytes - prev[2]) / (now - prev[0]))
            self.ov_network_val.setText(f"{_fmt_bytes(rate)}/s")
        else:
            self.ov_network_val.setText(na)

    def _set_overview_resource_na(self) -> None:
        na = tr("monitoring.na")
        self.ov_cpu_bar.setValue(0)
        self.ov_cpu_val.setText(na)
        self.ov_mem_bar.setValue(0)
        self.ov_mem_val.setText(na)
        self.ov_disk_val.setText(na)
        self.ov_network_val.setText(na)

    def _refresh_agent_status(self) -> None:
        cowork_n = len(self._cowork.active_workers()) if self._cowork is not None else 0
        task_n = self._task_scheduler.running_count() if self._task_scheduler is not None else 0
        ask_worker = getattr(self._structure, "_ask_worker", None)
        knowledge_n = 1 if (ask_worker is not None and ask_worker.isRunning()) else 0

        # Security is a system-management agent that runs INLINE on the active
        # turn (agent_security prompt/command validation) — there is no separate
        # worker to count, so its "active" cell shows On/Off from Settings
        # instead of a live count.
        sec_on = bool(self.ctx.config.agent_security.get("enabled"))

        rows = [
            (agent_roles.COWORK, cowork_n, tr("monitoring.source_cowork")),
            (agent_roles.TASK, task_n, tr("monitoring.source_task")),
            (agent_roles.KNOWLEDGE, knowledge_n, tr("monitoring.source_knowledge")),
            (agent_roles.PLANNER, None, tr("monitoring.source_planner")),
            (agent_roles.REASONING, None, tr("monitoring.source_reasoning")),
            (agent_roles.SECURITY, None, tr("monitoring.source_security")),
        ]
        self.status_table.setRowCount(len(rows))
        for row, (role_key, count, source) in enumerate(rows):
            label = agent_roles.label_for(role_key)
            name_item = QTableWidgetItem(label)
            name_item.setIcon(_agent_avatar_icon(label))
            self.status_table.setItem(row, 0, name_item)

            if role_key == agent_roles.SECURITY:
                running = sec_on
                status_text = tr("monitoring.on") if sec_on else tr("monitoring.off")
            elif count is not None:
                running = count > 0
                status_text = tr("monitoring.active_n", n=count) if running else tr("monitoring.idle")
            else:
                running = False
                status_text = "—"
            badge_tone = "badgeSuccess" if running else "badgeNeutral"
            self.status_table.setCellWidget(row, 1, badge_pill_widget(status_text, badge_tone))
            self.status_table.setItem(row, 2, QTableWidgetItem(source))

    def _activity_line(self, event: dict) -> str:
        # Monochrome colored mark (no emoji) — an HTML label can't host a QIcon,
        # so a thin ✓ / ✗ / ! tinted by state is the line-style equivalent.
        ok = event.get("ok", True)
        if ok:
            mark = f"<span style='color:{DOT_GREEN};'>✓</span>"
        elif event.get("kind") == "security_block":
            mark = f"<span style='color:{DOT_AMBER};'>!</span>"
        else:
            mark = f"<span style='color:{DOT_RED};'>✗</span>"
        name = event.get("name", "") or event.get("kind", "")
        rel = _relative_time(event.get("ts", ""))
        muted = current_palette().text_muted
        suffix = f" <span style='color:{muted};'>— {rel}</span>" if rel else ""
        return f"{mark} {name}{suffix}"

    def _refresh_usage_cards(self) -> None:
        from ..core import model_pricing as mp
        mp.sync_to_usage(self.ctx.config)   # cost total comes straight from the price table
        pricing = {**ut.DEFAULT_PRICING, **(self.ctx.config.data.get("usage") or {})}
        events = ut.load_events()
        s = ut.summarize(events)
        costs = ut.cost_usd_events(events, pricing)
        self.ov_usage_total.set(tr("dashboard.card_total"), fmt_tokens(s["total"]))
        self.ov_usage_calls.set(tr("monitoring.overview_calls"), str(s["turns"]), "")
        self.ov_usage_in.set(tr("dashboard.card_in"), fmt_tokens(s["in"]),
                             ut.format_cost(costs["in"], pricing))
        self.ov_usage_out.set(tr("dashboard.card_out"), fmt_tokens(s["out"]),
                              ut.format_cost(costs["out"], pricing))
        self.ov_usage_cache.set(tr("dashboard.card_cache"), fmt_tokens(s["cache"]),
                                ut.format_cost(costs["cache"], pricing))
        # "Tổng chi phí · 57 lượt", exactly as the wireframe labels it.
        self.ov_usage_cost.set(
            f'{tr("dashboard.card_cost")} · {s["turns"]} {tr("monitoring.overview_calls")}',
            ut.format_cost(sum(costs.values()), pricing, digits=2))
        self._refresh_budget()

    def _sync_sbx_more_label(self, *_a) -> None:
        """Label the fold with what it will do next."""
        open_ = self.ov_sbx_more_btn.isChecked()
        self.ov_sbx_more_btn.setText(
            ("▾ " if open_ else "▸ ") + tr("monitoring.overview_sbx_detail"))

    def _apply_budget(self) -> None:
        """Persist the spin box's value as the new budget — starts a fresh
        remaining-balance window (spend before now is no longer counted)."""
        ccy = (self.ctx.config.data.get("usage") or {}).get("currency", "USD")
        ut.set_budget(self.ctx.config, self.ov_budget_card.budget_spin.value(), ccy)
        self.ctx.save()
        self._refresh_budget()

    def _refresh_budget(self) -> None:
        from ..core import model_pricing as mp
        pricing = {**ut.DEFAULT_PRICING, **(self.ctx.config.data.get("usage") or {})}
        status = ut.budget_status(self.ctx.config)
        if status is None:
            self.ov_budget_card.set(tr("usage.budget_title"), "—", tr("usage.budget_no_budget"))
            self.ov_budget_card.budget_spin.setValue(0.0)
            return
        amount_disp = mp.convert(status["amount_usd"], "USD",
                                 pricing.get("currency", "USD"), self.ctx.config)
        value = (f"{ut.format_cost(status['remaining_usd'], pricing, digits=2)}"
                 f" / {ut.format_cost(status['amount_usd'], pricing, digits=2)}")
        pct = int(round(status["pct_used"] * 100))
        sub = tr("usage.budget_over_warning") if status["over_85"] else tr("usage.budget_used_pct", pct=pct)
        self.ov_budget_card.set(tr("usage.budget_title"), value, sub, warn=status["over_85"])
        if not self.ov_budget_card.budget_spin.hasFocus():
            self.ov_budget_card.budget_spin.setValue(round(amount_disp, 2))

    def _refresh_overview(self, events: List[dict]) -> None:
        sec = self.ctx.config.agent_security
        self._refresh_usage_cards()
        net_blocked = bool(sec.get("block_network"))

        recent = sorted(events, key=lambda e: e.get("ts", ""), reverse=True)
        if recent:
            self.ov_activity_lbl.setText("<br>".join(self._activity_line(e) for e in recent[:6]))
            self.ov_audit_lbl.setText("<br>".join(
                f"{e.get('ts', '')} — {e.get('name', '')}" for e in recent[:4]))
        else:
            self.ov_activity_lbl.setText(tr("monitoring.overview_no_activity"))
            self.ov_audit_lbl.setText(tr("monitoring.overview_no_activity"))

        self.ov_sbx_id_val.setText(f"sbx_{os.getpid():x}")
        self.ov_sbx_status_val.setText(tr("monitoring.overview_status_running"))
        self.ov_sbx_created_val.setText(datetime.fromtimestamp(self.ctx.started_at).strftime("%H:%M:%S"))
        uptime_s = max(0, int(time.time() - self.ctx.started_at))
        h, rem = divmod(uptime_s, 3600)
        m, s = divmod(rem, 60)
        self.ov_sbx_uptime_val.setText(f"{h}h {m}m {s}s" if h else f"{m}m {s}s")
        limit_parts = []
        if sec.get("resource_limit_cpu_percent"):
            limit_parts.append(f"CPU {sec['resource_limit_cpu_percent']}%")
        if sec.get("resource_limit_memory_mb"):
            limit_parts.append(f"MEM {sec['resource_limit_memory_mb']}MB")
        if sec.get("resource_limit_disk_mb"):
            limit_parts.append(f"DISK {sec['resource_limit_disk_mb']}MB")
        self.ov_sbx_limits_lbl.setText(
            tr("monitoring.overview_resource_limits") + ": "
            + (", ".join(limit_parts) if limit_parts else tr("monitoring.na")))
        self.ov_sbx_net_val.setText(
            tr("monitoring.overview_network_disabled") if net_blocked
            else tr("monitoring.overview_network_enabled"))
        self._set_badge(self.ov_sbx_net_val, "badgeWarn" if net_blocked else "badgeSuccess")
        # The one line the wireframe shows; the detail above stays a fold away.
        self.ov_sbx_summary.setText(" · ".join([
            f'{tr("monitoring.overview_perm_fs")}: '
            f'{tr("monitoring.overview_perm_fs_value")}',
            f'{tr("monitoring.overview_perm_network")}: '
            f'{tr("monitoring.overview_network_disabled") if net_blocked else tr("monitoring.overview_network_enabled")}',
            f'{tr("monitoring.overview_perm_process")}: '
            f'{tr("monitoring.overview_perm_process_value")}',
            f'{tr("monitoring.overview_resource_limits")}: '
            f'{", ".join(limit_parts) if limit_parts else tr("monitoring.na")}',
        ]))
        self._sync_sbx_more_label()

        self.ov_perm_network_val.setText(
            tr("monitoring.overview_perm_network_blocked") if net_blocked
            else tr("monitoring.overview_perm_network_allowed"))
        self._set_badge(self.ov_perm_network_val, "badgeWarn" if net_blocked else "badgeSuccess")