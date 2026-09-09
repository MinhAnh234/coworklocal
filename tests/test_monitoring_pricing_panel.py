"""Task 1 (sub-step 6f, follow-up) — PricingPanel, split out of overview_tab.py
to keep that file under the 400-line quality rule."""
from __future__ import annotations

import copy
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from cowork_local.config import AppConfig, DEFAULT_CONFIG
from cowork_local.presentation.monitoring.tabs.pricing_panel import PricingPanel


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class _FakeCtx:
    def __init__(self, tmp_path):
        self.config = AppConfig(data=copy.deepcopy(DEFAULT_CONFIG), path=tmp_path / "c.json")

    def save(self):
        pass


def test_construction_and_retranslate(qapp, tmp_path) -> None:
    panel = PricingPanel(_FakeCtx(tmp_path), on_status_message=lambda _m: None)
    panel.retranslate()


def test_add_and_delete_pricing_row_round_trip(qapp, tmp_path, monkeypatch) -> None:
    ctx = _FakeCtx(tmp_path)
    panel = PricingPanel(ctx, on_status_message=lambda _m: None)
    # Panel hỏi tên qua ``ui.dialog_buttons.ask_text`` chứ không gọi thẳng hàm
    # tĩnh ``QInputDialog.getText`` (hàm tĩnh tự dựng hộp thoại bên trong nên
    # nút Cancel của nó luôn tiếng Anh). Patch nhầm chỗ thì hộp thoại THẬT mở
    # ra và test treo cho tới khi hết giờ.
    monkeypatch.setattr("cowork_local.ui.dialog_buttons.ask_text",
                        lambda *a, **k: ("gpt-test", True))
    panel._add_pricing_row()
    assert panel.table.rowCount() == 1
    assert panel.table.item(0, 0).text() == "gpt-test"

    panel.table.selectRow(0)
    panel._delete_pricing_row()
    assert panel.table.rowCount() == 0
