"""UsageChartWidget — the period pager + granularity/metric/currency
controls + spline chart of the Dashboard (R08-T13, extracted from
``ui/dashboard_tab.py::DashboardTab``, lines 53-114/143-152/201-207/
263-323 of the original 437-line file).

Owns the period SELECTOR (granularity + prev/next offset) that the whole
screen follows — ``token_usage_card_widget.py`` and ``habits_widget.py``
read :meth:`period_range`/:meth:`granularity` rather than keeping their own
copy, and the shell re-refreshes them on :attr:`period_changed`.
"""
from __future__ import annotations

from typing import Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from cowork_local.application.monitoring import DashboardQueryService
from cowork_local.i18n import tr
from cowork_local.theme import current_palette
from cowork_local.ui.icons import icon
from cowork_local.ui.spline_chart import SplineChart
from cowork_local.ui.widgets import fmt_tokens


class UsageChartWidget(QWidget):
    """Thẻ biểu đồ chi phí/token của Dashboard: hàng điều khiển + đồ thị spline.

    Đây cũng là nơi giữ *kỳ đang xem* (độ mịn tuần/tháng/năm + độ lệch kỳ)
    cho cả màn hình: các thẻ khác không tự chọn kỳ mà nghe tín hiệu
    ``period_changed`` rồi hỏi lại :meth:`period_range`.
    """
    period_changed = Signal()     # granularity or offset changed — re-run every widget
    currency_changed = Signal()   # display currency changed — same, cost text depends on it

    def __init__(self, ctx, query: DashboardQueryService, parent=None):
        """Dựng hàng điều khiển kỳ và biểu đồ spline."""
        super().__init__(parent)
        self.ctx = ctx
        self._query = query
        self._chart_offset = 0    # 0 = current period; <0 = a past period

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        # Hàng điều khiển nằm trong một widget riêng chứ không đổ thẳng vào layout,
        # để vỏ ngoài gỡ được nó ra và đặt lên đầu màn hình — xem
        # :meth:`detach_controls_bar`.
        self.controls_bar = QWidget(self)
        controls = QHBoxLayout(self.controls_bar)
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(6)
        self.chart_prev_btn = QPushButton()
        self.chart_prev_btn.setIcon(icon("chevron-left"))
        self.chart_prev_btn.setFixedWidth(30)
        self.chart_prev_btn.clicked.connect(self._chart_prev)
        controls.addWidget(self.chart_prev_btn)
        self._chart_period_lbl = QLabel()
        self._chart_period_lbl.setObjectName("hint")
        self._chart_period_lbl.setAlignment(Qt.AlignCenter)
        self._chart_period_lbl.setMinimumWidth(170)
        controls.addWidget(self._chart_period_lbl)
        self.chart_next_btn = QPushButton()
        self.chart_next_btn.setIcon(icon("chevron-right"))
        self.chart_next_btn.setFixedWidth(30)
        self.chart_next_btn.clicked.connect(self._chart_next)
        controls.addWidget(self.chart_next_btn)
        controls.addSpacing(12)
        self.gran_combo = QComboBox()
        for g in ("week", "month", "year"):
            self.gran_combo.addItem(tr(f"dashboard.gran_{g}"), g)
        self.gran_combo.currentIndexChanged.connect(self._on_gran_changed)
        controls.addWidget(self.gran_combo)
        self.metric_combo = QComboBox()
        for m in ("cost", "tokens"):
            self.metric_combo.addItem(tr(f"dashboard.metric_{m}"), m)
        self.metric_combo.currentIndexChanged.connect(self.refresh)
        controls.addWidget(self.metric_combo)
        controls.addStretch(1)
        # Display-currency picker — both Dashboard and Monitoring read/write
        # the same usage.currency config key, so changing it here updates
        # cost text everywhere.
        self.currency_lbl = QLabel()
        self.currency_lbl.setObjectName("hint")
        controls.addWidget(self.currency_lbl)
        self.currency_combo = QComboBox()
        from cowork_local.core import usage_tracker as ut
        for cur in ut.SUPPORTED_CURRENCIES:
            self.currency_combo.addItem(cur, cur)
        idx = self.currency_combo.findData(
            (self.ctx.config.data.get("usage") or {}).get("currency", "USD"))
        self.currency_combo.setCurrentIndex(max(0, idx))
        self.currency_combo.currentIndexChanged.connect(self._on_currency_changed)
        controls.addWidget(self.currency_combo)
        self._root.addWidget(self.controls_bar)

        chart_head = QHBoxLayout()
        self._chart_title = QLabel()
        self._chart_title.setStyleSheet("font-weight:600;")
        chart_head.addWidget(self._chart_title, 1)
        self._root.addLayout(chart_head)
        self.chart = SplineChart()
        self._root.addWidget(self.chart)

        self.retranslate()

    def detach_controls_bar(self) -> QWidget:
        """Gỡ hàng điều khiển ra khỏi thẻ biểu đồ và trả về cho chỗ khác đặt.

        Hàng này chọn kỳ cho **cả màn hình** chứ không riêng biểu đồ: thẻ số
        liệu và bảng thói quen đều lọc theo nó. Bản trước refactor vì thế đặt nó
        ngay dưới tiêu đề, trên các thẻ số liệu; đợt tách widget (R08-T13) kéo
        nó xuống theo biểu đồ, thành ra người dùng đọc các thẻ số liệu trước khi
        nhìn thấy thứ quyết định những con số ấy (F-07).

        Trạng thái kỳ và toàn bộ dây tín hiệu vẫn thuộc widget này — chỉ có chỗ
        đặt là đổi. Gọi hay không gọi đều chạy đúng: không gọi thì hàng điều khiển
        ở nguyên trong thẻ biểu đồ (widget dùng độc lập trong test vẫn đủ bộ).
        """
        self._root.removeWidget(self.controls_bar)
        return self.controls_bar

    def retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn cho nhãn và tooltip."""
        self.currency_lbl.setText(tr("monitoring.overview_currency"))
        self.currency_combo.setToolTip(tr("dashboard.currency_tooltip"))
        self._chart_title.setText(tr("dashboard.chart_title"))
        self.chart_prev_btn.setToolTip(tr("dashboard.chart_prev"))
        self.chart_next_btn.setToolTip(tr("dashboard.chart_next"))

    # ---- public: the period selector every other widget follows ------------- #
    def granularity(self) -> str:
        """Độ mịn đang chọn: 'week' | 'month' | 'year'. Mặc định 'week'."""
        return self.gran_combo.currentData() or "week"

    @property
    def chart_offset(self) -> int:
        """Độ lệch kỳ: 0 là kỳ hiện tại, số âm là lùi về quá khứ."""
        return self._chart_offset

    def period_range(self) -> Tuple:
        """Khoảng thời gian (đầu, cuối) của kỳ đang xem — thứ mọi thẻ khác dùng để lọc dữ liệu."""
        return self._query.period_range(self.granularity(), self._chart_offset)

    # ---- navigation ------------------------------------------------------------ #
    def _on_gran_changed(self, *_a) -> None:
        """Đổi độ mịn thì nhảy về kỳ hiện tại: giữ nguyên độ lệch cũ sẽ nhảy sang
        một mốc thời gian khác hẳn (lùi 3 tuần ≠ lùi 3 tháng).
        """
        self._chart_offset = 0            # period size changed → back to current
        self.period_changed.emit()

    def _chart_prev(self) -> None:
        """Lùi một kỳ."""
        self._chart_offset -= 1
        self.period_changed.emit()

    def _chart_next(self) -> None:
        """Tiến một kỳ, chặn ở kỳ hiện tại — không cho xem tương lai."""
        self._chart_offset = min(0, self._chart_offset + 1)   # never past the present
        self.period_changed.emit()

    def _on_currency_changed(self, _idx: int) -> None:
        """Đổi tiền tệ hiển thị và ghi vào cấu hình ngay.

        Dashboard và Giám sát dùng chung khoá ``usage.currency`` nên đổi ở đây
        là mọi chỗ hiện tiền đều đổi theo.
        """
        cur = self.currency_combo.currentData()
        if not cur:
            return
        self.ctx.config.data.setdefault("usage", {})["currency"] = cur
        self.ctx.save()
        self.currency_changed.emit()

    @staticmethod
    def _delta_txt(cur: float, prev: float) -> str:
        """▲/▼ percent change of ``cur`` vs ``prev`` (empty if no baseline)."""
        if not prev:
            return ""
        pct = (cur - prev) / prev * 100
        arrow = "▲" if pct > 0.5 else ("▼" if pct < -0.5 else "•")
        return f"{arrow}{abs(pct):.0f}%"

    # ---- rendering --------------------------------------------------------------- #
    def refresh(self, *_a) -> None:
        """Break the SELECTED period into its parts: WEEK -> 7 days (Mon-Sun)
        - MONTH -> weeks W1..Wn - YEAR -> 12 months. A dashed line marks the
        previous same-granularity period's average per point with the %
        change of the totals."""
        from cowork_local.core import usage_tracker as ut

        gran = self.granularity()
        metric = self.metric_combo.currentData() or "cost"
        pts = self._query.chart_series(gran, self._chart_offset, metric)
        pricing = self._query.pricing()
        mi = 0 if metric == "tokens" else 1
        # Compact cost format (2 decimals, K/M above 1,000/1,000,000) — the
        # chart's y-axis label box is narrow; format_cost's full precision
        # overflowed it, clipping/obscuring the amount.
        fmt = fmt_tokens if metric == "tokens" else (lambda v: ut.format_cost_compact(v, pricing))

        cur = self._query.period_totals(gran, self._chart_offset)
        prev = self._query.period_totals(gran, self._chart_offset - 1)
        ref_key = {"week": "dashboard.ref_last_week",
                   "month": "dashboard.ref_last_month",
                   "year": "dashboard.ref_last_year"}.get(gran, "dashboard.ref_last_week")
        n_points = max(1, len(pts))
        refs = []
        if prev[mi] > 0:
            # Muted on purpose: the comparison line is a reference, not the
            # series — it must not compete with the accent-coloured spline.
            refs.append((prev[mi] / n_points,
                         f"{tr(ref_key)} {self._delta_txt(cur[mi], prev[mi])}",
                         current_palette().text_muted))
        self.chart.set_reference_lines(refs)
        self.chart.set_data(pts, fmt, tr(f"dashboard.metric_{metric}"))
        self._chart_period_lbl.setText(self._query.period_range_label(gran, self._chart_offset))
        self.chart_next_btn.setEnabled(self._chart_offset < 0)


__all__ = ["UsageChartWidget"]
