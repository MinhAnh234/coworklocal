"""Right-hand "Chi tiet su kien" detail panel shared by the Security Events /
MCP Call History / Action Logs tabs — the full record behind whichever row is
selected in an :class:`~.event_table.EventTable`. Extracted verbatim from
``ui/monitoring_tab.py``.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from ....core import agent_roles
from ....i18n import tr
from ....ui.icons import icon
from .badges import agent_badge_name, action_label, apply_badge, severity_info, status_info
from .formatters import event_id, fmt_event_time_full
from .layout_helpers import kv_row

# Cosmetic label only — no real policy-versioning system exists yet.
_STATIC_POLICY_LABEL = "security_policy_v2"


class EventDetailPanel(QWidget):
    """Laid out as three labelled sections, a terminal-style block quote for
    the detail text, and a metadata footer, closed by the header close
    button, the footer button, Esc, or a click outside the table/panel (see
    :class:`~.event_table.ClickOutsideCloser`)."""

    closed = Signal()

    def __init__(self):
        """Panel chi tiết hiện đầy đủ một sự kiện đang chọn trong bảng."""
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

        self._section_hdrs: List[Tuple[str, QLabel]] = []
        self._rows: Dict[str, Tuple[QLabel, QLabel]] = {}

        def _section(key: str) -> None:
            """Thêm một dòng tiêu đề mục vào panel."""
            lbl = QLabel()
            lbl.setObjectName("detailSectionHdr")
            self._body_lay.addWidget(lbl)
            self._section_hdrs.append((key, lbl))

        def _field(key: str) -> QLabel:
            """Thêm một hàng nhãn–giá trị và ghi nhớ để cập nhật sau."""
            lbl, val = kv_row(self._body_lay)
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

    def retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn."""
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
        """Hiện chi tiết một sự kiện; trường trống hiển thị dấu "—" thay vì để rỗng."""
        na = "—"
        self._rows["time"][1].setText(fmt_event_time_full(ev.get("ts", "")) or na)

        agent_label = agent_roles.label_for(ev.get("agent_role", "")) or na
        self._agent_val.setText(agent_label)
        apply_badge(self._agent_val,
                   agent_badge_name(agent_label) if agent_label != na else "badge")

        self._rows["account"][1].setText(ev.get("account", "") or na)
        self._machine_val.setText(ev.get("machine", "") or na)

        name = ev.get("name", "")
        kind = ev.get("kind", "security_block")
        ok = ev.get("ok", False)
        self._type_val.setText(action_label(name) or na)
        status_badge, status_key = status_info(name, kind, ok)
        self._status_val.setText(tr(status_key))
        apply_badge(self._status_val, status_badge)

        self._detail_text = ev.get("detail", "") or na
        self._code_text.setText(self._detail_text)
        self._reset_copy_btn()

        self._event_id_val.setText(event_id(ev.get("ts", ""), row))
        # The static policy label names a real enforcement ruleset — only
        # meaningful for a Security Events row; MCP calls/generic actions
        # were never evaluated against it.
        self._policy_val.setText(_STATIC_POLICY_LABEL if kind == "security_block" else na)
        severity_badge, severity_key = severity_info(name, kind, ok)
        self._severity_val.setText(tr(severity_key))
        apply_badge(self._severity_val, severity_badge)

    def _copy_detail(self) -> None:
        """Chép toàn bộ chi tiết vào clipboard và đổi nhãn nút để báo đã chép."""
        QGuiApplication.clipboard().setText(self._detail_text)
        self._copy_btn.setText(tr("monitoring.detail_copied"))
        self._copy_btn.setIcon(icon("check"))
        QTimer.singleShot(1500, self._reset_copy_btn)

    def _reset_copy_btn(self) -> None:
        """Trả nút Sao chép về nhãn ban đầu sau vài giây."""
        self._copy_btn.setText(tr("monitoring.detail_copy"))
        self._copy_btn.setIcon(icon("document"))
