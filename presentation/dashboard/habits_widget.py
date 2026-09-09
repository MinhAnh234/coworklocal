"""HabitsWidget — the usage-habits summary + AI recommendations panel of the
Dashboard (R08-T13, extracted from ``ui/dashboard_tab.py::DashboardTab``,
lines 154-184/348-372/376-438 of the original 437-line file: the habits/AI
layout, ``refresh()``'s habits-HTML section, ``_apply_saving_strategy``,
``_ai_analyze``).
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextBrowser, QVBoxLayout, QWidget
from PySide6.QtCore import Signal

from cowork_local.application.monitoring import DashboardQueryService
from cowork_local.core.worker import AgentWorker
from cowork_local.i18n import tr
from cowork_local.ui.icons import icon
from cowork_local.ui.widgets import fmt_tokens


class HabitsWidget(QWidget):
    """Thẻ "Thói quen dùng model" của Dashboard, kèm phần AI phân tích.

    Chỉ gửi SỐ LIỆU đã tổng hợp lên provider, không bao giờ gửi nội dung
    prompt thật — xem :meth:`_ai_analyze`.
    """
    status_message = Signal(str)

    def __init__(self, ctx, query: DashboardQueryService, parent=None):
        """Bảng thói quen dùng model, kèm nút nhờ model tự nhận xét.

        Kỳ đang xem được nhớ lại ở mỗi lần ``refresh()`` để nút nhận xét dùng đúng
        khoảng thời gian đang hiện trên màn hình.
        """
        super().__init__(parent)
        self.ctx = ctx
        self._query = query
        self._ai_worker: Optional[AgentWorker] = None
        self._period_range = (None, None)   # set on each refresh(); _ai_analyze reuses it

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self._habits_title = QLabel()
        self._habits_title.setStyleSheet("font-weight:600;")
        habits_head = QHBoxLayout()
        self.ai_analyze_btn = QPushButton()
        self.ai_analyze_btn.setIcon(icon("sparkle"))
        self.ai_analyze_btn.clicked.connect(self._ai_analyze)
        # Apply an AI-suggested cost-saving strategy — only after the user
        # clicks to approve it.
        self.apply_strategy_btn = QPushButton()
        self.apply_strategy_btn.setIcon(icon("bolt"))
        self.apply_strategy_btn.setVisible(False)
        self.apply_strategy_btn.clicked.connect(self._apply_saving_strategy)
        habits_head.addWidget(self._habits_title, 1)
        habits_head.addWidget(self.apply_strategy_btn)
        habits_head.addWidget(self.ai_analyze_btn)
        root.addLayout(habits_head)
        self.habits = QTextBrowser()
        self.habits.setOpenExternalLinks(False)
        self.habits.setMinimumHeight(160)
        root.addWidget(self.habits, 1)
        self._ai_title = QLabel()
        self._ai_title.setStyleSheet("font-weight:600;")
        self._ai_title.setVisible(False)
        root.addWidget(self._ai_title)
        self.ai_advice = QTextBrowser()
        self.ai_advice.setOpenExternalLinks(False)
        self.ai_advice.setMinimumHeight(140)
        self.ai_advice.setVisible(False)
        root.addWidget(self.ai_advice, 1)

        self.retranslate()

    def retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn."""
        self.ai_analyze_btn.setText(tr("dashboard.ai_analyze_btn"))
        self.ai_analyze_btn.setToolTip(tr("dashboard.ai_analyze_tooltip"))
        self.apply_strategy_btn.setText(tr("dashboard.strategy_btn"))
        self.apply_strategy_btn.setToolTip(tr("dashboard.strategy_tooltip"))
        self._habits_title.setText(tr("dashboard.habits_title"))

    def refresh(self, start: date, end: date) -> None:
        """Vẽ lại bảng thói quen dùng model cho một kỳ, và nhớ kỳ đó cho nút AI phân tích."""
        self._period_range = (start, end)
        summary = self._query.summary(start, end)
        s, events = summary["stats"], summary["events"]

        lines: List[str] = []
        if not events:
            lines.append(f"<i>{tr('dashboard.no_data')}</i>")
        else:
            lines.append(f"<b>{tr('dashboard.h_top')}</b>")
            lines.append("<ol>")
            for label, tok in s["top_labels"]:
                pct = int(tok * 100 / s["total"]) if s["total"] else 0
                lines.append(f"<li>{label[:60]} — {fmt_tokens(tok)} tokens ({pct}%)</li>")
            lines.append("</ol>")
            src_parts = ", ".join(
                f"{tr(f'app.tab.{k}') if k in ('cowork', 'code') else k}: {fmt_tokens(v)}"
                for k, v in s["by_source"])
            lines.append(f"<b>{tr('dashboard.h_by_source')}</b>: {src_parts}<br>")
            lines.append(f"<b>{tr('dashboard.h_avg')}</b>: "
                         f"{fmt_tokens(s['avg_per_turn'])} tokens<br>")
            if s["busiest_day"]:
                lines.append(f"<b>{tr('dashboard.h_busiest_day')}</b>: {s['busiest_day']}<br>")
            if s["busiest_hour"] is not None:
                lines.append(f"<b>{tr('dashboard.h_busiest_hour')}</b>: "
                             f"{s['busiest_hour']:02d}:00–{s['busiest_hour']:02d}:59<br>")
            if s["estimated_share"] > 0:
                lines.append(f"<i>{tr('dashboard.estimated_note', pct=int(s['estimated_share'] * 100))}</i>")
        self.habits.setHtml("".join(lines))

    def _apply_saving_strategy(self) -> None:
        """Apply an AI-suggested cost-saving strategy AFTER the user
        approves: turn on auto-compress and compress earlier (lower
        threshold) + compress content before sending it to the agent."""
        from ...ui.dialog_buttons import confirm
        if not confirm(self, tr("dashboard.strategy_title"),
                       tr("dashboard.strategy_confirm")):
            return
        cx = self.ctx.config.data.setdefault("context", {})
        cx["auto_compact"] = True
        cx["compact_threshold"] = 0.6          # compress at 60% of the window (was ~80%)
        cx["compress_before_send"] = True      # digest context before each turn
        self.ctx.save()
        self.status_message.emit(tr("dashboard.strategy_applied"))

    def _ai_analyze(self) -> None:
        """✨ Send the aggregated numbers (never raw prompt text) to the
        active provider and show habit feedback + token-saving
        recommendations."""
        if self._ai_worker is not None:
            return
        start, end = self._period_range
        if start is None:
            return
        summary = self._query.summary(start, end)
        if not summary["events"]:
            self.status_message.emit(tr("dashboard.no_data"))
            return
        stats = summary["stats"]
        self.ai_analyze_btn.setEnabled(False)
        self.ai_analyze_btn.setText(tr("dashboard.ai_analyzing"))
        ctx = self.ctx

        def job(worker: AgentWorker):
            """Chạy nền: gửi SỐ LIỆU đã tổng hợp (không bao giờ gửi nội dung prompt thật)
            cho model và xin nhận xét cùng gợi ý tiết kiệm token.
            """
            from cowork_local.core import usage_tracker as ut
            from cowork_local.i18n import get_language

            prompt = ut.build_ai_analysis_prompt(stats, get_language())
            provider = ctx.build_active_provider()
            reply = provider.chat([{"role": "user", "content": prompt}],
                                  cancel=worker.stop_event)
            return {"text": (reply.get("content") or "").strip()}

        def done(result: dict) -> None:
            """Hiện nhận xét của AI và mở nút "Áp dụng chiến lược tiết kiệm"."""
            self._ai_worker = None
            self.ai_analyze_btn.setEnabled(True)
            self.ai_analyze_btn.setText(tr("dashboard.ai_analyze_btn"))
            text = result.get("text") or ""
            if text:
                self._ai_title.setText(tr("dashboard.ai_advice_title"))
                self._ai_title.setVisible(True)
                self.ai_advice.setMarkdown(text)
                self.ai_advice.setVisible(True)
                self.apply_strategy_btn.setVisible(True)

        def failed(err: str) -> None:
            """Phân tích lỗi: hiện lý do và mở khoá lại nút."""
            self._ai_worker = None
            self.ai_analyze_btn.setEnabled(True)
            self.ai_analyze_btn.setText(tr("dashboard.ai_analyze_btn"))
            self.status_message.emit(str(err))

        w = AgentWorker(job)
        w.finished_ok.connect(done)
        w.failed.connect(failed)
        self._ai_worker = w
        w.start()


__all__ = ["HabitsWidget"]
