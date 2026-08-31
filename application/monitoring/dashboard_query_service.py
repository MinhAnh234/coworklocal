"""DashboardQueryService - read-only usage/cost queries for the Dashboard
screen (R08-T13, extracted from ``ui/dashboard_tab.py::DashboardTab``, lines
196-199/256-261/284-322 of the original 437-line file: ``_pricing``,
``_period_range``'s date-math, and the ``period_totals``/``period_breakdown``
calls ``_refresh_chart`` made directly).

``ui/dashboard_tab.py`` called ``core/usage_tracker.py``/``core/model_
pricing.py`` directly from FIVE different methods spread across what is now
three widgets (``token_usage_card_widget.py``, ``usage_chart_widget.py``,
``habits_widget.py``) — each recomputing the same merged pricing dict. This
service is the one place that merge happens now; the three widgets share it
instead of each calling ``core.usage_tracker``/``core.model_pricing`` on
their own.

Pure Python: no Qt. Wraps ``core/usage_tracker.py`` (a plain-Python module
already) rather than reimplementing any of its date/cost math.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Tuple


class DashboardQueryService:
    """Usage/cost queries scoped to one ``AppContext``.

    Args:
        ctx: ``AppContext`` — read for ``ctx.config`` (pricing table,
            currency, budget) and nothing else; this class does no I/O of
            its own beyond what ``core.usage_tracker`` already does.
        directory: Optional custom usage directory. If None, uses default USAGE_DIR.
    """

    def __init__(self, ctx: Any, directory: Optional[Path] = None) -> None:
        """``directory`` để None thì đọc thư mục telemetry mặc định; test trỏ nó vào
        ``tmp_path`` để không chạm dữ liệu thật.
        """
        self.ctx = ctx
        self._directory = directory

    def pricing(self) -> Dict[str, Any]:
        """The merged price table (defaults + user overrides), synced from
        Monitoring's model-pricing table first so cost figures always agree
        between the two screens."""
        from cowork_local.core import model_pricing as mp
        from cowork_local.core import usage_tracker as ut

        mp.sync_to_usage(self.ctx.config)
        return {**ut.DEFAULT_PRICING, **(self.ctx.config.data.get("usage") or {})}

    def period_range(self, granularity: str, offset: int) -> Tuple[date, date]:
        """The SELECTED period as an inclusive ``(start, end)`` date range —
        drives every widget on the screen (cards, chart, habits)."""
        from cowork_local.core import usage_tracker as ut

        start, end = ut.period_bounds(granularity, offset)
        return start, end - timedelta(days=1)   # load_events end is inclusive

    def summary(self, start: date, end: date) -> Dict[str, Any]:
        """Everything the stat cards + habits panel need for one period:
        the raw events, ``usage_tracker.summarize``'s aggregate stats, the
        per-bucket costs, and their total — computed once so both widgets
        read the same numbers instead of loading events twice."""
        from cowork_local.core import usage_tracker as ut

        events = ut.load_events(start, end, directory=self._directory)
        pricing = self.pricing()
        stats = ut.summarize(events)
        costs = ut.cost_usd_events(events, pricing)
        return {
            "events": events,
            "pricing": pricing,
            "stats": stats,
            "costs": costs,
            "total_cost": sum(costs.values()),
        }

    def chart_series(self, granularity: str, offset: int, metric: str
                     ) -> List[Tuple[str, float]]:
        """``(label, value)`` points for the spline chart — WEEK -> 7 days,
        MONTH -> weeks, YEAR -> 12 months, in whichever ``metric``
        ("tokens" | "cost") was selected."""
        from cowork_local.core import usage_tracker as ut

        events = ut.load_events(directory=self._directory)   # all events; breakdown slices by period
        pricing = self.pricing()
        parts = ut.period_breakdown(events, granularity, pricing, offset=offset)
        mi = 0 if metric == "tokens" else 1   # (label, tokens, cost) -> +1 for the value
        return [(row[0], float(row[mi + 1])) for row in parts]

    def period_totals(self, granularity: str, offset: int) -> Tuple[float, float]:
        """``(tokens, cost)`` totals for one period — used to compute the
        vs-previous-period delta the chart's reference line shows."""
        from cowork_local.core import usage_tracker as ut

        events = ut.load_events(directory=self._directory)
        return ut.period_totals(events, granularity, self.pricing(), offset)

    def period_range_label(self, granularity: str, offset: int) -> str:
        """Nhãn hiển thị của một kỳ (tuần/tháng/năm cộng độ lệch)."""
        from cowork_local.core import usage_tracker as ut

        return ut.period_range_label(granularity, offset)

    def budget_status(self):
        """Tình trạng ngân sách: đã dùng bao nhiêu, còn lại bao nhiêu, có vượt ngưỡng chưa."""
        from cowork_local.core import usage_tracker as ut

        return ut.budget_status(self.ctx.config)

    def set_budget(self, amount: float, currency: str) -> None:
        """Đặt hạn mức ngân sách mới — mở một chu kỳ đếm mới, chi tiêu trước đó không
        còn được tính vào.
        """
        from cowork_local.core import usage_tracker as ut

        ut.set_budget(self.ctx.config, amount, currency)


__all__ = ["DashboardQueryService"]
