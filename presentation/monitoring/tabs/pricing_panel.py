"""Model Pricing panel — the editable price-table card on the Overview page
(currency picker, import/export/add/auto-link/delete, and the table itself).
Extracted from ``ui/monitoring_tab.py``'s pricing-table construction and
``_reload_pricing_table``/``_import_pricing``/``_export_pricing``/
``_add_pricing_row``/``_autolink_pricing``/``_delete_pricing_row``.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QComboBox, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from ....core import usage_tracker as ut
from ....i18n import tr
from ....ui.icons import icon


class PricingPanel(QGroupBox):
    """Bảng đơn giá model trong màn Giám sát: nhập, xuất, tự dò và sửa tay.

    Đơn giá ở đây là thứ Dashboard dùng để quy token ra tiền, nên sửa ở đây là
    mọi con số chi phí trong app đổi theo.
    """
    def __init__(self, ctx, on_status_message: Callable[[str], None]):
        """Bảng đơn giá theo model, sửa được ngay tại chỗ."""
        super().__init__()
        self.ctx = ctx
        self._on_status_message = on_status_message
        self._worker = None
        self.setObjectName("monSection")

        pg = QVBoxLayout(self)
        phdr = QHBoxLayout()
        self.ccy_lbl = QLabel()
        self.ccy_lbl.setObjectName("hint")
        self.ccy = QComboBox()
        for cur in ut.SUPPORTED_CURRENCIES:
            self.ccy.addItem(cur, cur)
        pidx = self.ccy.findData((self.ctx.config.data.get("usage") or {}).get("currency", "USD"))
        self.ccy.setCurrentIndex(max(0, pidx))
        self.ccy.currentIndexChanged.connect(self._reload_table)
        phdr.addWidget(self.ccy_lbl)
        phdr.addWidget(self.ccy)
        phdr.addStretch(1)
        self.import_btn = QPushButton()
        self.import_btn.setIcon(icon("download"))
        self.import_btn.clicked.connect(self._import_pricing)
        self.export_btn = QPushButton()
        self.export_btn.setIcon(icon("upload"))
        self.export_btn.clicked.connect(self._export_pricing)
        self.add_btn = QPushButton()
        self.add_btn.setIcon(icon("plus"))
        self.add_btn.clicked.connect(self._add_pricing_row)
        self.link_btn = QPushButton()
        self.link_btn.setIcon(icon("refresh"))
        self.link_btn.clicked.connect(self._autolink_pricing)
        self.del_btn = QPushButton()
        self.del_btn.setIcon(icon("trash"))
        self.del_btn.clicked.connect(self._delete_pricing_row)
        for b in (self.import_btn, self.export_btn, self.add_btn, self.link_btn, self.del_btn):
            phdr.addWidget(b)
        pg.addLayout(phdr)

        self.table = QTableWidget(0, 5)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        pg.addWidget(self.table, 1)

        self._reload_table()

    def retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn cho tiêu đề, nút và tên cột."""
        self.setTitle(tr("monitoring.pricing_title").upper())
        self.ccy_lbl.setText(tr("monitoring.pricing_currency"))
        self.import_btn.setText(tr("monitoring.pricing_import"))
        self.export_btn.setText(tr("monitoring.pricing_export"))
        self.add_btn.setText(tr("monitoring.pricing_add"))
        self.link_btn.setText(tr("monitoring.pricing_autolink"))
        self.del_btn.setText(tr("monitoring.pricing_delete"))
        self.table.setHorizontalHeaderLabels([
            tr("monitoring.pricing_col_model"), tr("monitoring.pricing_col_context"),
            tr("monitoring.pricing_col_maxout"), tr("monitoring.pricing_col_input"),
            tr("monitoring.pricing_col_output")])

    def _reload_table(self, *_a) -> None:
        """Nạp lại toàn bộ bảng đơn giá từ cấu hình."""
        from ....core import model_pricing as mp
        to_ccy = self.ccy.currentData() or "USD"
        entries = mp.list_entries(self.ctx.config)
        self.table.setRowCount(len(entries))
        for r, e in enumerate(entries):
            in_v = mp.convert(e.get("input_price", 0), e.get("input_ccy", "USD"), to_ccy, self.ctx.config)
            out_v = mp.convert(e.get("output_price", 0), e.get("output_ccy", "USD"), to_ccy, self.ctx.config)
            vals = [e.get("model", ""), e.get("context_length", ""), e.get("max_output", ""),
                    f"{mp.format_price(in_v, to_ccy)} / {e.get('input_unit', '')}",
                    f"{mp.format_price(out_v, to_ccy)} / {e.get('output_unit', '')}"]
            for c, v in enumerate(vals):
                self.table.setItem(r, c, QTableWidgetItem(str(v)))

    def _import_pricing(self) -> None:
        """Nhập đơn giá từ file Excel/CSV, gộp vào bảng hiện có."""
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from ....core import model_pricing as mp
        path, _ = QFileDialog.getOpenFileName(
            self, tr("monitoring.pricing_import"), "", "Pricing (*.xlsx *.csv)")
        if not path:
            return
        default_ccy = self.ccy.currentData() or "USD"
        try:
            imported = mp.import_table(path, default_ccy=default_ccy)
        except ValueError as exc:
            QMessageBox.warning(self, tr("monitoring.pricing_title"), str(exc))
            return
        merged = {e["model"]: e for e in mp.list_entries(self.ctx.config)}
        for e in imported:
            merged[e["model"]] = e
        mp.save_entries(self.ctx.config, list(merged.values()))
        self.ctx.save()
        self._reload_table()
        self._on_status_message(tr("monitoring.pricing_imported", n=len(imported)))

    def _export_pricing(self) -> None:
        """Xuất file mẫu để điền đơn giá rồi nhập ngược lại."""
        from PySide6.QtWidgets import QFileDialog

        from ....core import model_pricing as mp
        path, _ = QFileDialog.getSaveFileName(
            self, tr("monitoring.pricing_export"), "model_pricing_template.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        mp.export_template(path)
        self._on_status_message(tr("monitoring.pricing_exported"))

    def _add_pricing_row(self) -> None:
        """Thêm một dòng đơn giá trống để người dùng điền tay."""
        from ....ui.dialog_buttons import ask_text

        from ....core import model_pricing as mp
        name, ok = ask_text(self, tr("monitoring.pricing_add"),
                            tr("monitoring.pricing_add_prompt"))
        name = (name or "").strip()
        if not ok or not name:
            return
        ccy = self.ccy.currentData() or "USD"
        mp.add_entry(self.ctx.config, mp.entry_from_row(
            [name, "", "", "0", "Million tokens", "0", "Million tokens"], default_ccy=ccy))
        self.ctx.save()
        self._reload_table()

    def _autolink_pricing(self) -> None:
        """Nhờ AI dò đơn giá cho các model đang dùng mà chưa có giá, chạy ở luồng nền."""
        from ....core import model_pricing as mp
        from ....core.worker import AgentWorker
        if self._worker is not None:
            return
        self.link_btn.setEnabled(False)
        ctx = self.ctx
        ccy = self.ccy.currentData() or "USD"

        def job(_w):
            """Chạy nền: nhờ AI dò đơn giá cho các model đang dùng mà chưa có giá."""
            return {"entries": mp.auto_link(ctx, default_ccy=ccy)}

        def done(r):
            """Đổ đơn giá vừa dò được vào bảng và lưu lại."""
            self._worker = None
            self.link_btn.setEnabled(True)
            self.ctx.save()
            self._reload_table()
            self._on_status_message(tr("monitoring.pricing_linked", n=len(r.get("entries", []))))

        def failed(_e):
            """Dò giá lỗi: chỉ mở khoá lại nút, giữ nguyên bảng đang có."""
            self._worker = None
            self.link_btn.setEnabled(True)

        w = AgentWorker(job)
        w.finished_ok.connect(done)
        w.failed.connect(failed)
        self._worker = w
        w.start()

    def _delete_pricing_row(self) -> None:
        """Xoá dòng đơn giá đang chọn."""
        from ....core import model_pricing as mp
        row = self.table.currentRow()
        entries = mp.list_entries(self.ctx.config)
        if 0 <= row < len(entries):
            del entries[row]
            mp.save_entries(self.ctx.config, entries)
            self.ctx.save()
            self._reload_table()
