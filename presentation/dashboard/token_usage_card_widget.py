"""TokenUsageCardWidget — the stat-card grid + budget card of the Dashboard
(R08-T13, extracted from ``ui/dashboard_tab.py::DashboardTab``, lines
116-141/226-254/337-346 of the original 437-line file: the card grid layout,
``_apply_budget``, ``_refresh_budget``, and ``refresh()``'s card-filling
section).
"""
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QGridLayout, QWidget

from cowork_local.application.monitoring import DashboardQueryService
from cowork_local.i18n import tr
from cowork_local.ui.icons import icon
from cowork_local.ui.widgets import BudgetCard, StatCard, fmt_tokens


class TokenUsageCardWidget(QWidget):
    """Cost is the headline this screen exists for, so it gets a card twice
    the height of the rest instead of being the fifth of five identical
    tiles — with six equal cards nothing said which number mattered."""

    def __init__(self, ctx, query: DashboardQueryService, parent=None):
        """Lưới các thẻ số liệu token và chi phí."""
        super().__init__(parent)
        self.ctx = ctx
        self._query = query

        cards_grid = QGridLayout(self)
        # Lề 0 như hai thẻ con còn lại (``habits_widget``, ``usage_chart_widget``):
        # bản trước refactor đổ lưới thẻ THẲNG vào layout của màn hình, nên bọc nó
        # vào một widget kèm lề mặc định 9px đẩy cả hàng thẻ xuống 9px so với bản vẽ.
        cards_grid.setContentsMargins(0, 0, 0, 0)
        cards_grid.setSpacing(8)
        self.card_total = StatCard()
        self.card_in = StatCard()
        self.card_out = StatCard()
        self.card_cache = StatCard()
        self.card_cost = StatCard().as_hero()
        # Hero on the left, spanning both rows; the four supporting figures
        # fill a 2x2 block beside it.
        cards_grid.addWidget(self.card_cost, 0, 0, 2, 1)
        for i, card in enumerate((self.card_total, self.card_in,
                                  self.card_out, self.card_cache)):
            cards_grid.addWidget(card, i // 2, 1 + i % 2)
        # Budget: remaining/budget, direct entry, auto-warns red past 85% used.
        self.budget_card = BudgetCard()
        self.budget_card.apply_btn.setIcon(icon("check"))
        self.budget_card.apply_btn.clicked.connect(self._apply_budget)
        cards_grid.addWidget(self.budget_card, 0, 3, 2, 1)
        for col, stretch in ((0, 3), (1, 2), (2, 2), (3, 3)):
            cards_grid.setColumnStretch(col, stretch)

        self.retranslate()

    def retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn."""
        self.budget_card.apply_btn.setToolTip(tr("usage.budget_apply_tooltip"))
        self.budget_card.budget_spin.setToolTip(tr("usage.budget_spin_tooltip"))

    def refresh(self, start: date, end: date) -> None:
        """Cập nhật mọi thẻ theo số liệu của một kỳ."""
        summary = self._query.summary(start, end)
        s, pricing, costs = summary["stats"], summary["pricing"], summary["costs"]
        from cowork_local.core import usage_tracker as ut

        est_note = (tr("dashboard.estimated_note", pct=int(s["estimated_share"] * 100))
                    if s["estimated_share"] > 0 else "")
        self.card_total.set(tr("dashboard.card_total"), fmt_tokens(s["total"]),
                            tr("dashboard.card_turns", n=s["turns"]))
        self.card_in.set(tr("dashboard.card_in"), fmt_tokens(s["in"]),
                         ut.format_cost(costs["in"], pricing))
        self.card_out.set(tr("dashboard.card_out"), fmt_tokens(s["out"]),
                          ut.format_cost(costs["out"], pricing))
        self.card_cache.set(tr("dashboard.card_cache"), fmt_tokens(s["cache"]),
                            ut.format_cost(costs["cache"], pricing))
        self.card_cost.set(tr("dashboard.card_cost"),
                           ut.format_cost(summary["total_cost"], pricing, digits=2), est_note)
        self._refresh_budget()

    def _apply_budget(self) -> None:
        """Persist the spin box's value as the new budget — starts a fresh
        remaining-balance window (spend before now is no longer counted)."""
        ccy = (self.ctx.config.data.get("usage") or {}).get("currency", "USD")
        self._query.set_budget(self.budget_card.budget_spin.value(), ccy)
        self.ctx.save()
        self._refresh_budget()

    def _refresh_budget(self) -> None:
        """Cập nhật thẻ ngân sách: còn lại / tổng, phần trăm đã dùng, cảnh báo khi vượt."""
        from cowork_local.core import model_pricing as mp
        from cowork_local.core import usage_tracker as ut

        pricing = self._query.pricing()
        status = self._query.budget_status()
        if status is None:
            self.budget_card.set(tr("usage.budget_title"), "—", tr("usage.budget_no_budget"))
            self.budget_card.budget_spin.setValue(0.0)
            return
        remaining_disp = mp.convert(status["remaining_usd"], "USD",
                                    pricing.get("currency", "USD"), self.ctx.config)
        amount_disp = mp.convert(status["amount_usd"], "USD",
                                 pricing.get("currency", "USD"), self.ctx.config)
        value = (f"{ut.format_cost(status['remaining_usd'], pricing, digits=2)}"
                 f" / {ut.format_cost(status['amount_usd'], pricing, digits=2)}")
        pct = int(round(status["pct_used"] * 100))
        sub = tr("usage.budget_over_warning") if status["over_85"] else tr("usage.budget_used_pct", pct=pct)
        self.budget_card.set(tr("usage.budget_title"), value, sub, warn=status["over_85"])
        # keep the entry field showing the CURRENT budget (in display currency)
        # — only when it doesn't already have unsaved focus/edits from the user.
        if not self.budget_card.budget_spin.hasFocus():
            self.budget_card.budget_spin.setValue(round(amount_disp, 2))


__all__ = ["TokenUsageCardWidget"]
