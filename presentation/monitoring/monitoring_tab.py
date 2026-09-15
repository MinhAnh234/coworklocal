"""Monitoring Dashboard — container only. Builds the tab strip, wires the
auto-refresh timer and language-change retranslation, and forwards nav-rail
sub-tab selection. Each sub-tab is its own class under ``tabs/``; this class
owns no display logic of its own beyond assembling and refreshing them.

Public API preserved exactly for ``app.py`` (which cannot be modified):
``MonitoringTab(ctx, cowork=None, structure=None, task_scheduler=None)``,
the ``status_message`` signal, ``select_subtab(index)``, ``nav_subtabs()``,
``hide_tab_bar()``.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QTabWidget, QVBoxLayout, QWidget

from ...core import audit_log
from ...i18n import on_language_changed, tr
from ...state import AppContext
from ...performance import span
from .tabs.action_logs_tab import ActionLogsTab
from .tabs.agent_status_tab import AgentStatusTab
from .tabs.mcp_tab import McpTab
from .tabs.overview_tab import OverviewTab
from .tabs.security_events_tab import SecurityEventsTab

_REFRESH_MS = 3000
# Comfortably larger than any realistic audit-log size for the WINDOW of
# events _load_events() now actually reads (see _LOG_WINDOW_DAYS below) — this
# is MonitoringQueryService's query-side page size, kept unbounded so it
# always returns every matching event within the window; the user-facing
# "Số dòng/trang" control (DF-006 — see shared/event_table.py::set_page_size,
# shared/filter_scaffold.py::build_filter_scaffold's with_page_size) trims
# that down for DISPLAY, client-side, per event tab.
_UNBOUNDED_PAGE_SIZE = 100_000
# _load_events() re-reads the audit log from disk every _REFRESH_MS (3s) via
# _auto_refresh(), and audit_log.load_events()/load_shared_audit_events() are
# day-sharded JSONL — unbounded start/end means EVERY day file ever written
# gets re-read and re-parsed on EVERY tick, which is what actually made
# Monitoring "gây nặng khi log lớn" (see DF-006): the slowness was never in
# rendering (EventTable paginates client-side, 5-100 rows/page — see
# shared/event_table.py::_DEFAULT_PAGE_SIZE), it was this repeated full-history
# read.
# 30 days is a live-monitoring window, not a hard retention limit — nothing
# is deleted, older days are simply not re-read on every 3s tick.
_LOG_WINDOW_DAYS = 30


class MonitoringTab(QWidget):
    """Vỏ màn Giám sát: dải 8 tab và phần dữ liệu dùng chung cho chúng.

    Nhật ký kiểm toán được đọc MỘT lần mỗi nhịp làm mới rồi chia cho các tab,
    nên quyết định "đọc từ nguồn cục bộ hay nguồn chia sẻ" chỉ xảy ra đúng một
    lần chứ không phải ở từng tab.
    """
    status_message = Signal(str)

    # ---- cầu tương thích sau khi tách 8 tab (R08-T08) --------------------
    # Trước khi tách, 55 control của Tổng quan treo thẳng trên MonitoringTab với
    # tiền tố ov_. Tách xong mỗi cái về đúng tab/thẻ của nó và rụng tiền tố.
    #
    # tools/check_controls_alive.py so với mốc git 291a611 và đòi cả 55 cái phải
    # còn tới được — đó chính là việc của nó: bắt control biến mất trong lúc bóc
    # tách. Lần này control còn đủ, chỉ đổi chỗ ở, nên bắc cầu theo tiền tố.
    #
    # Định tuyến theo tiền tố chứ không dò mờ: overview_tab và permissions_card
    # có những tên trùng nhau (network_lbl nằm ở cả hai — một cái là mức dùng
    # mạng, một cái là quyền truy cập mạng). Dò mờ vớ nhầm cái đầu tiên tìm thấy.
    _OV_TIEN_TO = (
        ("ov_perm_", lambda s: s.overview_tab.sandbox_card.permissions_card),
        ("ov_sbx_", lambda s: s.overview_tab.sandbox_card),
        ("ov_price_", lambda s: s.overview_tab.pricing_panel),
        ("ov_pricing_", lambda s: s.overview_tab.pricing_panel),
        ("ov_", lambda s: s.overview_tab),
    )
    #: Ba hộp nhóm: bản thân widget con CHÍNH LÀ hộp đó, không phải thuộc tính.
    _OV_CHINH_NO = {
        "ov_pricing_group": lambda s: s.overview_tab.pricing_panel,
        "ov_sandbox_details_group": lambda s: s.overview_tab.sandbox_card,
        "ov_permissions_group": lambda s: s.overview_tab.sandbox_card.permissions_card,
    }

    #: Vài control không mang tiền tố ov_ nhưng cũng đã dời đi.
    _KHAC = {
        "status_table": lambda s: s.status_tab.table,
    }

    def __getattr__(self, name):
        """Cầu tương thích cho 55 control cũ mang tiền tố ``ov_``.

        R08-T08 chuyển chúng về đúng tab/thẻ của mình và bỏ tiền tố, nhưng các
        checker trong ``tools/`` vẫn hỏi theo tên cũ. Định tuyến theo TIỀN TỐ chứ
        không dò mờ: ``overview_tab`` và ``permissions_card`` có tên trùng nhau
        (``network_lbl`` ở cả hai — một cái là mức dùng mạng, một cái là quyền truy
        cập mạng), dò mờ sẽ vớ nhầm cái tìm thấy trước.
        """
        lay_khac = self._KHAC.get(name)
        if lay_khac is not None:
            return lay_khac(self)
        # Qt gọi __getattr__ rất nhiều lúc khởi tạo; chặn sớm cho rẻ.
        if not name.startswith("ov_"):
            raise AttributeError(name)
        lay = self._OV_CHINH_NO.get(name)
        if lay is not None:
            return lay(self)
        for tien_to, chu in self._OV_TIEN_TO:
            if name.startswith(tien_to):
                try:
                    return getattr(chu(self), name[len(tien_to):])
                except AttributeError:
                    continue
        raise AttributeError(name)

    def __init__(self, ctx: AppContext, cowork=None, structure=None, task_scheduler=None):
        """Ghép các tab con của màn Giám sát.

        Các widget được truyền vào đều có thể là None (test dựng tab lẻ) — mọi chỗ
        dùng phải kiểm trước.
        """
        super().__init__()
        self.ctx = ctx
        self._cowork = cowork
        self._structure = structure
        self._task_scheduler = task_scheduler

        root = QVBoxLayout(self)
        head = QHBoxLayout()
        self._title = QLabel()
        self._title.setStyleSheet("font-weight:700; font-size:15px;")
        head.addWidget(self._title)
        head.addStretch(1)
        root.addLayout(head)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        visible = self._tab_visible

        self.overview_tab = OverviewTab(
            ctx, on_status_message=self.status_message.emit,
            on_settings_changed=self.refresh,
            on_view_all_action_logs=self._show_action_logs_tab,
            action_logs_tab_visible=visible("action_logs"))
        self.tabs.addTab(self.overview_tab, "")

        self.security_tab = SecurityEventsTab(ctx, on_refresh_all=self.refresh)
        if visible("security_events"):
            self.tabs.addTab(self.security_tab, "")
        self.mcp_tab = McpTab(ctx, on_refresh_all=self.refresh)
        if visible("mcp_history"):
            self.tabs.addTab(self.mcp_tab, "")
        self.action_tab = ActionLogsTab(ctx, on_refresh_all=self.refresh)
        if visible("action_logs"):
            self.tabs.addTab(self.action_tab, "")

        self.status_tab = AgentStatusTab(
            ctx, on_refresh_all=self.refresh,
            cowork=cowork, structure=structure, task_scheduler=task_scheduler)
        if visible("agent_status"):
            self.tabs.addTab(self.status_tab, "")

        # ---- Agents Admin (catalog: assign a role + pinned model per agent) --
        from ...ui.agents_admin_tab import AgentsAdminTab
        self.agents_admin_tab = AgentsAdminTab(ctx)
        if visible("agents_admin"):
            self.tabs.addTab(self.agents_admin_tab, "")

        # ---- Tools (govern built-in tools + Connectors/MCP in one place) -----
        from ...ui.tools_admin_tab import ToolsAdminTab
        self.tools_admin_tab = ToolsAdminTab(ctx)
        if visible("tools_admin"):
            self.tabs.addTab(self.tools_admin_tab, "")

        # ---- Icons (browse built-in icons + add custom icons for agents/flows) --
        from ...ui.icons_admin_tab import IconsAdminTab
        self.icons_admin_tab = IconsAdminTab(ctx)
        self.tabs.addTab(self.icons_admin_tab, "")

        self.tabs.setCurrentIndex(0)

        self._timer = QTimer(self)
        # Only the Overview cards auto-refresh on this tick — Security, MCP,
        # Action Logs, Agent Status (and the admin tabs) are read-only tables
        # a background re-sort would otherwise disturb mid-interaction; the
        # user refreshes them explicitly via a "Refresh" button.
        self._timer.setInterval(_REFRESH_MS)
        self._timer.timeout.connect(self._auto_refresh)
        self._timer.start()

        on_language_changed(self._retranslate)
        self.refresh()

    # ---- nav integration: sub-tabs driven from the left nav rail ------------
    def nav_subtabs(self):
        """(label, index, icon_name) for each sub-tab — the left nav lists
        these as children under 'Monitoring'."""
        by_widget = {self.agents_admin_tab: "robot", self.tools_admin_tab: "wrench",
                     self.icons_admin_tab: "star"}
        for attr, name in (("security_tab", "shield"), ("mcp_tab", "plug"),
                           ("action_tab", "bolt"), ("status_tab", "monitor")):
            w = getattr(self, attr, None)
            if w is not None:
                by_widget[w] = name
        out = []
        for i in range(self.tabs.count()):
            out.append((self.tabs.tabText(i), i, by_widget.get(self.tabs.widget(i), "dashboard")))
        return out

    def select_subtab(self, index: int) -> None:
        """Chuyển sang tab con thứ ``index`` (thanh menu bên trái gọi vào đây)."""
        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)

    def hide_tab_bar(self) -> None:
        """Hide the in-content tab strip; the nav rail drives the sub-tabs."""
        self.tabs.tabBar().hide()

    def _show_action_logs_tab(self) -> None:
        """Nhảy tới tab Nhật ký hành động (dùng khi bấm vào phần trích ở Tổng quan)."""
        self.tabs.setCurrentIndex(self.tabs.indexOf(self.action_tab))

    def _tab_visible(self, key: str) -> bool:
        """Tab này có được hiện không: admin thấy hết, còn lại theo cấu hình
        ``monitoring_visibility``.
        """
        return self.ctx.role == "admin" or bool(self.ctx.config.monitoring_visibility.get(key, True))

    def _set_tab_text_if_present(self, widget, text: str) -> None:
        """Đổi nhãn một tab, bỏ qua nếu tab đó đang bị ẩn theo phân quyền."""
        idx = self.tabs.indexOf(widget)
        if idx >= 0:
            self.tabs.setTabText(idx, text)

    # ---- i18n ---------------------------------------------------------------
    def _retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn cho tiêu đề và nhãn từng tab."""
        self._title.setText(tr("monitoring.title"))
        if self.tabs.count():
            self.tabs.setTabText(0, tr("monitoring.tab_overview"))
        self._set_tab_text_if_present(self.security_tab, tr("monitoring.tab_security"))
        self._set_tab_text_if_present(self.mcp_tab, tr("monitoring.tab_mcp"))
        self._set_tab_text_if_present(self.action_tab, tr("monitoring.tab_actions"))
        self._set_tab_text_if_present(self.status_tab, tr("monitoring.tab_agents"))
        self._set_tab_text_if_present(self.agents_admin_tab, tr("monitoring.tab_agents_admin"))
        self._set_tab_text_if_present(self.tools_admin_tab, tr("monitoring.tab_tools"))
        self._set_tab_text_if_present(self.icons_admin_tab, tr("monitoring.tab_icons"))

        self.overview_tab.retranslate()
        self.security_tab.retranslate()
        self.mcp_tab.retranslate()
        self.action_tab.retranslate()
        self.status_tab.retranslate()

        self.refresh()

    # ---- refresh -------------------------------------------------------------
    def refresh(self) -> None:
        """Full refresh — Overview cards plus every table. Wired to the
        top-of-page and per-section "Refresh" buttons, called once at
        startup/language-change, but NOT to the auto-refresh timer (see
        ``_auto_refresh``)."""
        events = self._load_events()
        self._apply_events_to_event_tabs(events)
        self.status_tab.refresh()
        self.overview_tab.refresh(events)

    def _auto_refresh(self) -> None:
        """3-second timer tick — Overview cards only (see ``refresh``)."""
        self.overview_tab.refresh(self._load_events())

    def _load_events(self) -> List[dict]:
        """Đọc nhật ký kiểm toán, ưu tiên nguồn chia sẻ rồi mới tới nguồn cục bộ.

        Có cấu hình thư mục chia sẻ VÀ đọc ra được dữ liệu thì dùng nó, để cả đội
        nhìn chung một bức tranh; rỗng thì rơi về nhật ký của máy này.

        Chỉ đọc ``_LOG_WINDOW_DAYS`` ngày gần nhất — cả hai nguồn đều lưu theo
        file JSONL từng ngày, nên bounding ở đây tránh việc đọc lại TOÀN BỘ
        lịch sử mỗi 3 giây (xem ``_auto_refresh``), là nguyên nhân thật của
        DF-006 (gây nặng khi log lớn).
        """
        start = date.today() - timedelta(days=_LOG_WINDOW_DAYS)
        shared_dir = self.ctx.config.shared_dir
        with span("monitoring.load_events", window_days=_LOG_WINDOW_DAYS):
            if shared_dir:
                from ...core import telemetry_shared
                shared_events = telemetry_shared.load_shared_audit_events(shared_dir, start=start)
                if shared_events:
                    return shared_events
            return audit_log.load_events(start=start)

    def _apply_events_to_event_tabs(self, events: List[dict]) -> None:
        """Filters the ALREADY-LOADED event list (see ``_load_events`` — one
        shared local-or-shared decision per refresh, not one per tab) three
        ways via :class:`MonitoringQueryService`, mirroring what each
        ``EventTable.set_events`` used to receive directly."""
        from ...application.monitoring.dto.audit_event_dto import AuditEventDTO
        from ...application.monitoring.monitoring_query_service import MonitoringQueryService
        from ...application.monitoring.repository.audit_event_repository import (
            InMemoryAuditEventRepository,
        )

        repository = InMemoryAuditEventRepository([AuditEventDTO.from_raw(e) for e in events])
        service = MonitoringQueryService(repository)

        def _events_for(kind) -> List[dict]:
            """Lấy toàn bộ sự kiện của một loại, không phân trang."""
            page = service.query(kind=kind, page_size=_UNBOUNDED_PAGE_SIZE)
            return [e.to_dict() for e in page.items]

        self.security_tab.set_events(_events_for("security_block"))
        self.mcp_tab.set_events(_events_for("mcp_call"))
        self.action_tab.set_events(_events_for(None))
