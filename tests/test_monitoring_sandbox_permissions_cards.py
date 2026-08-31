"""Task 1 (sub-step 6e) — SandboxDetailsCard / PermissionsCard.

Verifies the Permissions card is nested INSIDE the Sandbox card's fold
(matching the pre-refactor layout exactly) and that refresh()/retranslate()
compute the same values the original MonitoringTab methods did.
"""
from __future__ import annotations

import copy
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from cowork_local.config import AppConfig, DEFAULT_CONFIG
from cowork_local.presentation.monitoring.tabs.sandbox_tab import SandboxDetailsCard


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class _FakeCtx:
    def __init__(self, tmp_path, block_network=False):
        self.config = AppConfig(data=copy.deepcopy(DEFAULT_CONFIG), path=tmp_path / "c.json")
        self.config.data["agent_security"]["block_network"] = block_network
        self.config.data["agent_security"]["resource_limit_cpu_percent"] = 50
        import time
        self.started_at = time.time() - 65   # ~1m5s uptime


def test_permissions_card_nested_inside_sandbox_fold(qapp, tmp_path) -> None:
    card = SandboxDetailsCard(_FakeCtx(tmp_path), on_settings_changed=lambda: None)
    assert card.permissions_card.parent() is card._detail


def test_refresh_computes_uptime_and_resource_limits(qapp, tmp_path) -> None:
    card = SandboxDetailsCard(_FakeCtx(tmp_path), on_settings_changed=lambda: None)
    card.retranslate()
    card.refresh()
    assert "CPU 50%" in card.limits_lbl.text()
    assert "m" in card.uptime_val.text()


def test_refresh_reflects_network_blocked_on_both_cards(qapp, tmp_path) -> None:
    card = SandboxDetailsCard(_FakeCtx(tmp_path, block_network=True), on_settings_changed=lambda: None)
    card.retranslate()
    card.refresh()
    assert card.net_val.objectName() == "badgeWarn"
    assert card.permissions_card.network_val.objectName() == "badgeWarn"


def test_refresh_reflects_network_allowed(qapp, tmp_path) -> None:
    card = SandboxDetailsCard(_FakeCtx(tmp_path, block_network=False), on_settings_changed=lambda: None)
    card.retranslate()
    card.refresh()
    assert card.net_val.objectName() == "badgeSuccess"
    assert card.permissions_card.network_val.objectName() == "badgeSuccess"


def test_fold_starts_collapsed(qapp, tmp_path) -> None:
    # isVisible() alone can't tell (it also depends on ancestors actually
    # being shown on screen, which nothing here is) — isHidden() reflects
    # the explicit setVisible(False) call regardless of the parent chain.
    card = SandboxDetailsCard(_FakeCtx(tmp_path), on_settings_changed=lambda: None)
    assert card._detail.isHidden() is True
    card.more_btn.setChecked(True)
    assert card._detail.isHidden() is False
