"""Ô định tuyến chỉ còn Auto và Manual; giá trị off/fallback cũ hiện thành Auto."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _toggle(stored: str):
    from cowork_local.ui.routing_toggle import RoutingToggle

    saved = []
    t = RoutingToggle(None, "cowork", get_mode=lambda: stored, set_mode=saved.append)
    return t, saved


def test_only_auto_and_manual_are_offered(qt_app):
    t, _ = _toggle("auto")
    items = [t._combo.itemData(i) for i in range(t._combo.count())]
    assert items == ["auto", "manual"]


@pytest.mark.parametrize("stored", ["off", "fallback", "", "turbo"])
def test_legacy_values_show_as_auto(qt_app, stored):
    t, _ = _toggle(stored)
    assert t.current_mode() == "auto"


def test_choosing_manual_persists_it(qt_app):
    t, saved = _toggle("auto")
    t._combo.setCurrentIndex(t._combo.findData("manual"))
    assert saved == ["manual"]
