"""Task 4a — model_pricing <-> usage_tracker circular dependency is gone.

Before this fix, ``model_pricing.turn_cost_usd`` deferred-imported
``usage_tracker`` for its flat fallback rates, while ``usage_tracker.set_budget``
deferred-imported ``model_pricing`` for currency conversion — a real
architectural cycle, only avoided at runtime by pushing both imports inside
function bodies. Now ``model_pricing`` is a leaf module (it owns its own
fallback rates) and ``usage_tracker`` imports it at module top level.
"""
from __future__ import annotations

import copy
import sys

from cowork_local.config import AppConfig, DEFAULT_CONFIG
from cowork_local.core import model_pricing, usage_tracker


def test_model_pricing_does_not_depend_on_usage_tracker_module_level() -> None:
    assert "usage_tracker" not in model_pricing.__dict__
    assert "usage_tracker" not in getattr(model_pricing, "__all__", [])


def test_usage_tracker_imports_model_pricing_at_top_level() -> None:
    assert usage_tracker.mp is model_pricing


def test_turn_cost_usd_fallback_matches_pre_refactor_default_rates(tmp_path) -> None:
    config = AppConfig(data=copy.deepcopy(DEFAULT_CONFIG), path=tmp_path / "config.json")
    # No matching row in the price table and no override in config.data["usage"]
    # -> falls back to the flat rates that used to live in
    # usage_tracker.DEFAULT_PRICING (0.5 in / 1.5 out USD per 1M tokens).
    cost = model_pricing.turn_cost_usd("some-unknown-model", 1_000_000, 1_000_000, config)
    assert cost == 0.5 + 1.5


def test_turn_cost_usd_honours_usage_override_like_before(tmp_path) -> None:
    config = AppConfig(data=copy.deepcopy(DEFAULT_CONFIG), path=tmp_path / "config.json")
    config.data.setdefault("usage", {})["price_per_mtok_in_usd"] = 2.0
    config.data["usage"]["price_per_mtok_out_usd"] = 4.0
    cost = model_pricing.turn_cost_usd("some-unknown-model", 1_000_000, 1_000_000, config)
    assert cost == 2.0 + 4.0


def test_set_budget_still_converts_via_model_pricing(tmp_path) -> None:
    config = AppConfig(data=copy.deepcopy(DEFAULT_CONFIG), path=tmp_path / "config.json")
    usage_tracker.set_budget(config, 100.0, currency="USD")
    status = usage_tracker.budget_status(config)
    assert status is not None
    assert status["amount_usd"] == 100.0


def test_no_import_time_cycle_when_loaded_fresh() -> None:
    for name in ("cowork_local.core.model_pricing", "cowork_local.core.usage_tracker"):
        sys.modules.pop(name, None)
    import importlib

    mp = importlib.import_module("cowork_local.core.model_pricing")
    ut = importlib.import_module("cowork_local.core.usage_tracker")
    assert ut.mp is mp
