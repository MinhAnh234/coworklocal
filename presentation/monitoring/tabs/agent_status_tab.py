"""Agent Status tab — which agent roles are currently running, read from the
existing ``ChatPanel``/``TaskScheduler``/GraphRAG-ask-worker state (no new
runtime tracking of its own). Extracted from ``ui/monitoring_tab.py``'s
status-table wiring + ``_refresh_agent_status``.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QWidget

from ....core import agent_roles
from ....i18n import tr
from ....ui.widgets import badge_pill_widget
from ..shared.filter_scaffold import build_filter_scaffold
from ..shared.formatters import agent_avatar_icon


class AgentStatusTab(QWidget):
    """Tab "Trạng thái Agent": đang có bao nhiêu lượt chat, task và luồng chạy."""
    def __init__(self, ctx, on_refresh_all: Callable[[], None],
                cowork=None, structure=None, task_scheduler=None):
        """Tab Tình trạng agent. Các widget truyền vào có thể là None khi dựng tab lẻ."""
        super().__init__()
        self._ctx = ctx
        self._cowork = cowork
        self._structure = structure
        self._task_scheduler = task_scheduler

        self.table = QTableWidget(0, 3)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        # No detail to open on click, no filtering — a plain read-only table,
        # so selection is off rather than left dangling with no effect.
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(1, 130)   # status is a cell widget — size it explicitly
        self.table.setIconSize(QSize(20, 20))

        parts = build_filter_scaffold(
            self, self.table, on_refresh=on_refresh_all,
            title_key="monitoring.agent_status_title", with_search=False, with_detail=False)
        self.title_lbl = parts["title_lbl"]
        self.title_key = parts["title_key"]
        self.title_refresh_btn = parts["title_refresh_btn"]

    def retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn."""
        self.title_lbl.setText(tr(self.title_key))
        self.title_refresh_btn.setText(tr("monitoring.refresh"))
        self.table.setHorizontalHeaderLabels([
            tr("monitoring.col_agent"), tr("monitoring.detail_status"), tr("monitoring.col_source"),
        ])

    def refresh(self) -> None:
        """Đếm lại số việc đang chạy ở từng phân hệ và cập nhật bảng."""
        cowork_n = len(self._cowork.active_workers()) if self._cowork is not None else 0
        task_n = self._task_scheduler.running_count() if self._task_scheduler is not None else 0
        ask_worker = getattr(self._structure, "_ask_worker", None)
        knowledge_n = 1 if (ask_worker is not None and ask_worker.isRunning()) else 0

        # Security is a system-management agent that runs INLINE on the
        # active turn (agent_security prompt/command validation) — there is
        # no separate worker to count, so its "active" cell shows On/Off
        # from Settings instead of a live count.
        sec_on = bool(self._ctx.config.agent_security.get("enabled"))

        rows = [
            (agent_roles.COWORK, cowork_n, tr("monitoring.source_cowork")),
            (agent_roles.TASK, task_n, tr("monitoring.source_task")),
            (agent_roles.KNOWLEDGE, knowledge_n, tr("monitoring.source_knowledge")),
            (agent_roles.PLANNER, None, tr("monitoring.source_planner")),
            (agent_roles.REASONING, None, tr("monitoring.source_reasoning")),
            (agent_roles.SECURITY, None, tr("monitoring.source_security")),
        ]
        self.table.setRowCount(len(rows))
        for row, (role_key, count, source) in enumerate(rows):
            label = agent_roles.label_for(role_key)
            name_item = QTableWidgetItem(label)
            name_item.setIcon(agent_avatar_icon(label))
            self.table.setItem(row, 0, name_item)

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
            self.table.setCellWidget(row, 1, badge_pill_widget(status_text, badge_tone))
            self.table.setItem(row, 2, QTableWidgetItem(source))
