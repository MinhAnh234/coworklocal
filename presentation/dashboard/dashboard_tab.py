"""DashboardTab shell (R08-T13) — assembles
``token_usage_card_widget.py::TokenUsageCardWidget``,
``usage_chart_widget.py::UsageChartWidget`` and
``habits_widget.py::HabitsWidget`` behind the scroll area / header / 30s
auto-refresh timer that used to be inline in
``ui/dashboard_tab.py::DashboardTab.__init__`` (lines 40-193 of the original
437-line file).

The one ``DashboardQueryService`` (R08-T13) instance is built here and
shared by all three children so pricing/currency stay consistent across the
whole screen.
"""
from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from cowork_local.application.monitoring import DashboardQueryService
from cowork_local.i18n import on_language_changed, tr
from cowork_local.presentation.dashboard.habits_widget import HabitsWidget
from cowork_local.presentation.dashboard.token_usage_card_widget import TokenUsageCardWidget
from cowork_local.presentation.dashboard.usage_chart_widget import UsageChartWidget
from cowork_local.state import AppContext
from cowork_local.ui.icons import icon


class DashboardTab(QWidget):
    """Màn Bảng điều khiển: ghép thẻ số liệu, biểu đồ và bảng thói quen dùng model.

    Một ``DashboardQueryService`` duy nhất được dựng ở đây và dùng chung cho cả
    ba thẻ con, nên đơn giá và tiền tệ luôn nhất quán trên toàn màn hình.
    """
    status_message = Signal(str)

    def __init__(self, ctx: AppContext):
        """Dựng vỏ Bảng điều khiển và ghép ba thẻ con, dùng chung một
        ``DashboardQueryService``.
        """
        super().__init__()
        self.ctx = ctx
        self._query = DashboardQueryService(ctx)

        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        root = QVBoxLayout(content)

        head = QHBoxLayout()
        self._title = QLabel()
        self._title.setStyleSheet("font-weight:700; font-size:15px;")
        self.refresh_btn = QPushButton("")
        self.refresh_btn.setIcon(icon("refresh"))
        self.refresh_btn.setFixedWidth(34)
        self.refresh_btn.clicked.connect(self.refresh)
        head.addWidget(self._title, 1)
        head.addWidget(self.refresh_btn)
        root.addLayout(head)

        self.chart = UsageChartWidget(ctx, self._query)
        self.chart.period_changed.connect(self.refresh)
        self.chart.currency_changed.connect(self.refresh)

        # Hàng bộ chọn kỳ đặt NGAY DƯỚI TIÊU ĐỀ, trên các thẻ số liệu — đúng
        # chỗ của nó trước refactor. Nó lọc cả ba thẻ con chứ không riêng biểu đồ,
        # nên để nó nằm dưới các thẻ số liệu là bắt người dùng đọc con số trước
        # khi thấy con số đó tính cho kỳ nào (F-07).
        root.addWidget(self.chart.detach_controls_bar())

        self.token_cards = TokenUsageCardWidget(ctx, self._query)
        root.addWidget(self.token_cards)

        root.addWidget(self.chart)

        self.habits = HabitsWidget(ctx, self._query)
        self.habits.status_message.connect(self.status_message.emit)
        root.addWidget(self.habits, 1)

        # Auto-refresh every 30s so numbers follow ongoing work.
        self._timer = QTimer(self)
        self._timer.setInterval(30_000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()

        on_language_changed(self._retranslate)
        self.refresh()

    def _retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn, rồi vẽ lại số liệu."""
        self._title.setText(tr("dashboard.title"))
        self.refresh_btn.setToolTip(tr("dashboard.refresh_tooltip"))
        self.token_cards.retranslate()
        self.chart.retranslate()
        self.habits.retranslate()
        self.refresh()

    def refresh(self, *_a) -> None:
        """Đọc lại số liệu cho kỳ đang chọn và cập nhật cả ba thẻ con."""
        start, end = self.chart.period_range()
        self.token_cards.refresh(start, end)
        self.chart.refresh()
        self.habits.refresh(start, end)


__all__ = ["DashboardTab"]
