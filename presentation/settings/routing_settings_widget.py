"""Mục Auto Model Routing trong Cài đặt — R08-T07.

Bóc từ ``ui/settings_dialog.py`` (khối dòng 254-309 của bản trước khi tách).
Widget tự dựng control, tự nạp giá trị, tự ghi trả về dict cấu hình. Dialog
chỉ còn việc đặt nó vào chỗ và gọi ``apply_to`` lúc lưu.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QFormLayout, QGroupBox, QLabel, QLineEdit, QPushButton, QSpinBox,
)

from ...i18n import tr

#: Các chế độ định tuyến. Danh sách này phải khớp ``config.py::AppConfig
#: .ROUTING_MODES`` — Delta thêm "fallback" ở R03-T03 và nếu quên đồng bộ
#: chỗ này thì người dùng không chọn được chế độ đó, mà không có lỗi nào báo.
MODE_KEYS = (("off", "routing.mode_off"), ("auto", "routing.mode_auto"),
             ("manual", "routing.mode_manual"))

POLICY_KEYS = (("quality", "routing.policy_quality"), ("cost", "routing.policy_cost"),
               ("latency", "routing.policy_latency"),
               ("balanced", "routing.policy_balanced"))


class RoutingSettingsWidget(QGroupBox):
    """Nhóm "Định tuyến model" trong Cài đặt: chế độ, chính sách, ngưỡng đổi và
    cấu hình trọng tài chấm điểm.
    """
    def __init__(self, ctx, parent=None):
        """Nhóm Định tuyến: chế độ tự chọn model và các tham số thăm dò."""
        super().__init__(tr("routing.settings_group"), parent)
        self.ctx = ctx
        routing = ctx.config.routing
        form = QFormLayout(self)

        self.mode = QComboBox()
        for value, key in MODE_KEYS:
            self.mode.addItem(tr(key), value)
        _select(self.mode, routing.get("switch_mode", "off"))
        form.addRow(tr("routing.settings_mode"), self.mode)

        self.policy = QComboBox()
        for value, key in POLICY_KEYS:
            self.policy.addItem(tr(key), value)
        _select(self.policy, routing.get("policy", "balanced"))
        form.addRow(tr("routing.settings_policy"), self.policy)

        # Lưu dạng phân lẻ (0..1) nhưng hiện dạng phần trăm.
        self.min_gain = QSpinBox()
        self.min_gain.setRange(0, 100)
        self.min_gain.setSuffix(" %")
        self.min_gain.setValue(int(round(float(routing.get("min_score_gain", 0.05)) * 100)))
        form.addRow(tr("routing.settings_min_gain"), self.min_gain)

        self.timeout = QSpinBox()
        self.timeout.setRange(5, 600)
        self.timeout.setSuffix(" s")
        self.timeout.setValue(int(routing.get("confirm_timeout_sec", 60) or 60))
        form.addRow(tr("routing.settings_timeout"), self.timeout)

        self.interval = QSpinBox()
        self.interval.setRange(0, 720)
        self.interval.setSpecialValueText(tr("routing.mode_off"))   # 0 = tắt
        self.interval.setSuffix(" h")
        self.interval.setValue(int(routing.get("reassess_interval_hours", 24) or 0))
        form.addRow(tr("routing.settings_interval"), self.interval)

        self.concurrency = QSpinBox()
        self.concurrency.setRange(1, 16)
        self.concurrency.setValue(int(routing.get("per_provider_concurrency", 2) or 2))
        form.addRow(tr("routing.settings_concurrency"), self.concurrency)

        self.judge = QLineEdit(routing.get("judge_model", ""))
        form.addRow(tr("routing.settings_judge"), self.judge)

        self.reassess_btn = QPushButton(tr("routing.settings_reassess_now"))
        self.reassess_btn.clicked.connect(self._reassess_now)
        form.addRow("", self.reassess_btn)

        hint = QLabel(tr("routing.settings_hint"))
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        form.addRow(hint)

    # ---- lưu ------------------------------------------------------------

    def apply_to(self, data: dict) -> None:
        """Ghi cấu hình định tuyến từ form vào dict cấu hình."""
        r = data.setdefault("routing", {})
        r["switch_mode"] = self.mode.currentData()
        r["policy"] = self.policy.currentData()
        r["min_score_gain"] = self.min_gain.value() / 100.0
        r["confirm_timeout_sec"] = self.timeout.value()
        r["reassess_interval_hours"] = self.interval.value()
        r["per_provider_concurrency"] = self.concurrency.value()
        r["judge_model"] = self.judge.text().strip()

    # ---- đánh giá lại ngay ----------------------------------------------

    def _reassess_now(self) -> None:
        """Chạy đánh giá lại model ở nền."""
        try:
            service = self.ctx.routing()
            if service.is_reassessing():
                return
            self.reassess_btn.setEnabled(False)
            self.reassess_btn.setText(tr("routing.reassessing"))

            def _done(result) -> None:
                self.reassess_btn.setEnabled(True)
                self.reassess_btn.setText(
                    tr("routing.reassess_done", count=len(result or {})))

            service.reassess_background(on_done=_done)
        except Exception:  # noqa: BLE001 — bấm đánh giá lại không được làm sập Cài đặt
            self.reassess_btn.setEnabled(True)
            self.reassess_btn.setText(tr("routing.settings_reassess_now"))


def _select(combo: QComboBox, value: str) -> None:
    """Chọn mục mang dữ liệu ``value`` trong một combo; không có thì để nguyên."""
    i = combo.findData(value)
    if i >= 0:
        combo.setCurrentIndex(i)
