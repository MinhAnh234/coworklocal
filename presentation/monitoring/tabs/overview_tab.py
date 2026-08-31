"""Overview tab — the card-based dashboard (Token Usage & Cost, Resource
Usage, Recent Activity, Sandbox Details + nested Permissions, Model Pricing,
Audit Log preview). Extracted from ``ui/monitoring_tab.py``'s
``_build_overview_page`` and the refresh/pricing/budget methods it wires to.
"""
from __future__ import annotations

import time
from typing import Callable, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from ....core import usage_tracker as ut
from ....i18n import tr
from ....theme import current_palette
from ....ui.icons import DOT_AMBER, DOT_GREEN, DOT_RED, icon
from ....ui.widgets import BudgetCard, StatCard, fmt_tokens
from ..shared.formatters import fmt_bytes, relative_time
from .pricing_panel import PricingPanel
from .sandbox_tab import SandboxDetailsCard


class OverviewTab(QWidget):
    """Tab "Tổng quan" của màn Giám sát: tài nguyên máy, thẻ token/chi phí, ngân
    sách, trạng thái sandbox, hoạt động gần đây và trích nhật ký kiểm toán.

    Một cột dọc duy nhất, mỗi phần là một mục có tiêu đề — bố cục này là chủ ý
    để mắt quét từ trên xuống thay vì phải nhảy giữa hai cột.
    """
    def __init__(self, ctx, *, on_status_message: Callable[[str], None],
                on_settings_changed: Callable[[], None],
                on_view_all_action_logs: Callable[[], None],
                action_logs_tab_visible: bool):
        """Tab Tổng quan.

        Mọi việc ra ngoài tab (báo trạng thái, mở màn khác) đều đi qua callback
        truyền vào, nên tab này không cần biết cửa sổ chính.
        """
        super().__init__()
        self.ctx = ctx
        self._on_status_message = on_status_message
        self._on_view_all_action_logs = on_view_all_action_logs
        self._last_io_sample = None
        self._res_first = True

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll)

        # ONE main column, scrolled vertically, sections in a fixed order.
        root = QVBoxLayout(content)
        root.setSpacing(12)

        self._build_usage_section(root)
        self._build_activity_section()   # added to `root` further down, beside the audit log
        self._build_resource_section(root)

        self.sandbox_card = SandboxDetailsCard(ctx, on_settings_changed)
        root.addWidget(self.sandbox_card)

        self.pricing_panel = PricingPanel(ctx, on_status_message)
        root.addWidget(self.pricing_panel)
        root.addWidget(self.activity_group)
        self._build_audit_section(root, action_logs_tab_visible)
        root.addStretch(1)

    # ---- Token Usage & Cost ------------------------------------------------
    def _build_usage_section(self, root: QVBoxLayout) -> None:
        """Dựng mục thẻ token/chi phí kèm thẻ ngân sách."""
        self.usage_group = QGroupBox()
        self.usage_group.setObjectName("monSection")
        usage_lay = QGridLayout(self.usage_group)
        usage_lay.setSpacing(8)
        self.usage_total = StatCard()
        self.usage_in = StatCard()
        self.usage_out = StatCard()
        self.usage_cache = StatCard()
        self.usage_cost = StatCard()
        self.usage_calls = StatCard()
        for i, card in enumerate((self.usage_cost, self.usage_total,
                                  self.usage_in, self.usage_out, self.usage_cache)):
            usage_lay.addWidget(card, 0, i)
        self.usage_calls.setVisible(False)   # rides on the cost tile's label
        self.budget_card = BudgetCard()
        self.budget_card.apply_btn.setIcon(icon("check"))
        self.budget_card.apply_btn.clicked.connect(self._apply_budget)
        usage_lay.addWidget(self.budget_card, 0, 3)
        for col in range(4):
            usage_lay.setColumnStretch(col, 1)
        root.addWidget(self.usage_group)

    # ---- Recent Activity ----------------------------------------------------
    def _build_activity_section(self) -> None:
        """Dựng mục "Hoạt động gần đây" (thêm vào cột ở dưới, cạnh nhật ký kiểm toán)."""
        self.activity_group = QGroupBox()
        self.activity_group.setObjectName("monSection")
        act_lay = QVBoxLayout(self.activity_group)
        self.activity_lbl = QLabel()
        self.activity_lbl.setWordWrap(True)
        self.activity_lbl.setTextFormat(Qt.RichText)
        act_lay.addWidget(self.activity_lbl)

    # ---- Resource Usage -------------------------------------------------------
    def _build_resource_section(self, root: QVBoxLayout) -> None:
        """Dựng mục tài nguyên: CPU, bộ nhớ, đĩa, mạng và trạng thái sandbox."""
        self.resource_group = QGroupBox()
        self.resource_group.setObjectName("monSection")
        res_lay = QHBoxLayout(self.resource_group)
        res_lay.setSpacing(6)

        def _pair():
            """Thêm một cặp nhãn–giá trị vào hàng tài nguyên, tự chèn dấu phân cách giữa
            các cặp.
            """
            if not self._res_first:
                sep = QLabel(chr(0xB7))
                sep.setObjectName("hint")
                res_lay.addWidget(sep)
            self._res_first = False
            lbl = QLabel()
            lbl.setObjectName("hint")
            val = QLabel()
            res_lay.addWidget(lbl)
            res_lay.addWidget(val)
            return lbl, val

        def _bar_row():
            """Thêm một cặp nhãn–giá trị kèm thanh tiến độ (CPU, bộ nhớ)."""
            lbl, val = _pair()
            bar = QProgressBar()
            bar.setVisible(False)
            return lbl, bar, val

        self.cpu_lbl, self.cpu_bar, self.cpu_val = _bar_row()
        self.mem_lbl, self.mem_bar, self.mem_val = _bar_row()
        self.diskfree_lbl, self.diskfree_val = _pair()
        self.disk_lbl, self.disk_val = QLabel(), QLabel()
        self.network_lbl, self.network_val = QLabel(), QLabel()
        res_lay.addStretch(1)
        root.addWidget(self.resource_group)

    # ---- Audit Log preview --------------------------------------------------
    def _build_audit_section(self, root: QVBoxLayout, action_logs_tab_visible: bool) -> None:
        """Dựng mục trích nhật ký kiểm toán; ẩn hẳn khi tab Nhật ký hành động bị tắt."""
        self.audit_group = QGroupBox()
        self.audit_group.setObjectName("monSection")
        audit_lay = QVBoxLayout(self.audit_group)
        self.audit_lbl = QLabel()
        self.audit_lbl.setWordWrap(True)
        self.audit_lbl.setTextFormat(Qt.RichText)
        audit_lay.addWidget(self.audit_lbl)
        self.view_all_btn = QPushButton()
        self.view_all_btn.setFlat(True)
        self.view_all_btn.clicked.connect(lambda: self._on_view_all_action_logs())
        audit_lay.addWidget(self.view_all_btn, 0, Qt.AlignRight)
        self.audit_group.setVisible(action_logs_tab_visible)
        root.addWidget(self.audit_group)

    # ---- budget --------------------------------------------------------------
    def _apply_budget(self) -> None:
        """Persist the spin box's value as the new budget — starts a fresh
        remaining-balance window (spend before now is no longer counted)."""
        ccy = (self.ctx.config.data.get("usage") or {}).get("currency", "USD")
        ut.set_budget(self.ctx.config, self.budget_card.budget_spin.value(), ccy)
        self.ctx.save()
        self._refresh_budget()

    def _refresh_budget(self) -> None:
        """Cập nhật thẻ ngân sách: còn lại / tổng, phần trăm đã dùng, cảnh báo khi vượt 85%.

        Không ghi đè ô nhập khi người dùng đang gõ trong đó.
        """
        from ....core import model_pricing as mp
        pricing = {**ut.DEFAULT_PRICING, **(self.ctx.config.data.get("usage") or {})}
        status = ut.budget_status(self.ctx.config)
        if status is None:
            self.budget_card.set(tr("usage.budget_title"), "—", tr("usage.budget_no_budget"))
            self.budget_card.budget_spin.setValue(0.0)
            return
        amount_disp = mp.convert(status["amount_usd"], "USD",
                                 pricing.get("currency", "USD"), self.ctx.config)
        value = (f"{ut.format_cost(status['remaining_usd'], pricing, digits=2)}"
                 f" / {ut.format_cost(status['amount_usd'], pricing, digits=2)}")
        pct = int(round(status["pct_used"] * 100))
        sub = tr("usage.budget_over_warning") if status["over_85"] else tr("usage.budget_used_pct", pct=pct)
        self.budget_card.set(tr("usage.budget_title"), value, sub, warn=status["over_85"])
        if not self.budget_card.budget_spin.hasFocus():
            self.budget_card.budget_spin.setValue(round(amount_disp, 2))

    # ---- resource usage --------------------------------------------------------
    def _refresh_resource_usage(self) -> None:
        """Đọc CPU/RAM/đĩa/mạng của CHÍNH tiến trình app.

        Đĩa và mạng là tốc độ tức thời, tính bằng hiệu hai lần lấy mẫu chia cho
        khoảng thời gian giữa chúng — nên lần đo đầu tiên luôn hiện "—". Không có
        ``psutil`` thì cả mục chuyển sang "—" chứ không làm vỡ màn hình.
        """
        try:
            import psutil
        except ImportError:
            self._set_resource_na()
            return

        try:
            own = psutil.Process()
            own_cpu = own.cpu_percent(interval=None)
            own_mem = own.memory_info().rss
        except Exception:
            own, own_cpu, own_mem = None, 0.0, 0

        self.cpu_bar.setValue(int(min(own_cpu, 100)))
        self.cpu_val.setText(f"{own_cpu:.0f}%")
        try:
            total_mem = psutil.virtual_memory().total
            mem_pct = int(own_mem * 100 / total_mem) if total_mem else 0
        except Exception:
            mem_pct = 0
        self.mem_bar.setValue(min(mem_pct, 100))
        try:
            self.mem_val.setText(f"{fmt_bytes(own_mem)}/{fmt_bytes(total_mem)}")
        except Exception:                                    # noqa: BLE001
            self.mem_val.setText(fmt_bytes(own_mem))
        try:
            free = psutil.disk_usage(str(self.ctx.config.cowork_output_dir())).free
            self.diskfree_val.setText(tr("monitoring.overview_disk_free", size=fmt_bytes(free)))
        except Exception:                                    # noqa: BLE001
            self.diskfree_val.setText(tr("monitoring.na"))

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
            self.disk_val.setText(f"{fmt_bytes(rate)}/s")
        else:
            self.disk_val.setText(na)
        if prev and net_bytes is not None and prev[2] is not None and now > prev[0]:
            rate = max(0.0, (net_bytes - prev[2]) / (now - prev[0]))
            self.network_val.setText(f"{fmt_bytes(rate)}/s")
        else:
            self.network_val.setText(na)

    def _set_resource_na(self) -> None:
        """Đặt mọi chỉ số tài nguyên về "—" (khi thiếu ``psutil``)."""
        na = tr("monitoring.na")
        self.cpu_bar.setValue(0)
        self.cpu_val.setText(na)
        self.mem_bar.setValue(0)
        self.mem_val.setText(na)
        self.disk_val.setText(na)
        self.network_val.setText(na)

    # ---- usage cards -----------------------------------------------------------
    def _activity_line(self, event: dict) -> str:
        """Một dòng hoạt động: dấu ✓/!/✗ theo kết quả, tên việc, và thời gian tương đối."""
        ok = event.get("ok", True)
        if ok:
            mark = f"<span style='color:{DOT_GREEN};'>✓</span>"
        elif event.get("kind") == "security_block":
            mark = f"<span style='color:{DOT_AMBER};'>!</span>"
        else:
            mark = f"<span style='color:{DOT_RED};'>✗</span>"
        name = event.get("name", "") or event.get("kind", "")
        rel = relative_time(event.get("ts", ""))
        muted = current_palette().text_muted
        suffix = f" <span style='color:{muted};'>— {rel}</span>" if rel else ""
        return f"{mark} {name}{suffix}"

    def _refresh_usage_cards(self) -> None:
        """Cập nhật các thẻ token và chi phí.

        Đồng bộ bảng đơn giá trước rồi mới tính tiền, để con số chi phí luôn khớp
        với bảng giá người dùng vừa sửa.
        """
        from ....core import model_pricing as mp
        mp.sync_to_usage(self.ctx.config)   # cost total comes straight from the price table
        pricing = {**ut.DEFAULT_PRICING, **(self.ctx.config.data.get("usage") or {})}
        events = ut.load_events()
        s = ut.summarize(events)
        costs = ut.cost_usd_events(events, pricing)
        self.usage_total.set(tr("dashboard.card_total"), fmt_tokens(s["total"]))
        self.usage_calls.set(tr("monitoring.overview_calls"), str(s["turns"]), "")
        self.usage_in.set(tr("dashboard.card_in"), fmt_tokens(s["in"]),
                          ut.format_cost(costs["in"], pricing))
        self.usage_out.set(tr("dashboard.card_out"), fmt_tokens(s["out"]),
                           ut.format_cost(costs["out"], pricing))
        self.usage_cache.set(tr("dashboard.card_cache"), fmt_tokens(s["cache"]),
                             ut.format_cost(costs["cache"], pricing))
        self.usage_cost.set(
            f'{tr("dashboard.card_cost")} · {s["turns"]} {tr("monitoring.overview_calls")}',
            ut.format_cost(sum(costs.values()), pricing, digits=2))
        self._refresh_budget()

    # ---- public API used by the container ---------------------------------
    def refresh(self, events: List[dict]) -> None:
        """Full refresh — resource usage + usage cards + sandbox/permissions
        + recent activity + audit preview. ``events`` is the already-loaded
        (local-or-shared) audit log, shared with the event-table tabs so the
        decision of which source to read from is made exactly once per
        refresh tick."""
        self._refresh_resource_usage()
        self._refresh_usage_cards()
        self.sandbox_card.refresh()

        recent = sorted(events, key=lambda e: e.get("ts", ""), reverse=True)
        if recent:
            self.activity_lbl.setText("<br>".join(self._activity_line(e) for e in recent[:6]))
            self.audit_lbl.setText("<br>".join(
                f"{e.get('ts', '')} — {e.get('name', '')}" for e in recent[:4]))
        else:
            self.activity_lbl.setText(tr("monitoring.overview_no_activity"))
            self.audit_lbl.setText(tr("monitoring.overview_no_activity"))

    def retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn cho mọi tiêu đề mục và nhãn."""
        self.usage_group.setTitle(tr("monitoring.overview_usage_title").upper().replace("&", "&&"))
        self.budget_card.apply_btn.setToolTip(tr("usage.budget_apply_tooltip"))
        self.budget_card.budget_spin.setToolTip(tr("usage.budget_spin_tooltip"))
        self.activity_group.setTitle(tr("monitoring.overview_activity_title").upper())
        self.resource_group.setTitle(tr("monitoring.overview_resource_title").upper())
        self.cpu_lbl.setText(tr("monitoring.overview_res_cpu"))
        self.mem_lbl.setText(tr("monitoring.overview_res_mem"))
        self.diskfree_lbl.setText(tr("monitoring.overview_disk_label"))
        self.disk_lbl.setText(tr("monitoring.overview_res_disk"))
        self.network_lbl.setText(tr("monitoring.overview_res_network"))
        self.pricing_panel.retranslate()
        self.sandbox_card.retranslate()
        self.audit_group.setTitle(tr("monitoring.overview_audit_title").upper())
        self.view_all_btn.setText(tr("monitoring.overview_view_all"))
