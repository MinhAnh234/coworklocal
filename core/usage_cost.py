"""Bảng giá và quy đổi token thành tiền — R09-T02.

Tách khỏi ``usage_tracker.py``: ghi nhận mức dùng và tính tiền là hai việc
khác nhau. Bảng giá đổi theo nhà cung cấp, cách ghi nhận thì không.
"""
from __future__ import annotations

import json
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..config import CONFIG_DIR
from . import model_pricing as mp

DEFAULT_PRICING = {
    "price_per_mtok_in_usd": 0.5,     # USD per 1M input tokens (flat fallback rate)
    "price_per_mtok_out_usd": 1.5,    # USD per 1M output tokens
    "price_per_mtok_cache_usd": 0.1,  # USD per 1M cached tokens
    "currency": "USD",                # display currency: USD | VND | JPY
    "usd_to_vnd": 25000.0,
    "usd_to_jpy": 150.0,
    # Per-model price table (USD / 1M tokens): {model: {"in","out","cache"}}.
    # Events whose model has an entry are costed with ITS rates; everything
    # else falls back to the flat price_per_mtok_* rates above. Edited in the
    # Monitoring Overview's pricing table.
    "model_prices": {},
    # Reference URL of the price list the table was filled from (set in
    # Settings; shown as a link beside the table — informational only, the
    # app never scrapes it).
    "pricing_url": "",
}

_CURRENCY_FMT = {"USD": ("$", 4), "VND": ("₫", 0), "JPY": ("¥", 1)}

SUPPORTED_CURRENCIES = tuple(_CURRENCY_FMT)

def cost_usd(summary: Dict[str, Any], pricing: Dict[str, Any]) -> Dict[str, float]:
    """Quy số token thành tiền (USD) theo bảng đơn giá, tách riêng vào/ra/cache."""
    p = {**DEFAULT_PRICING, **(pricing or {})}
    return {
        "in": summary.get("in", 0) / 1e6 * float(p["price_per_mtok_in_usd"]),
        "out": summary.get("out", 0) / 1e6 * float(p["price_per_mtok_out_usd"]),
        "cache": summary.get("cache", 0) / 1e6 * float(p["price_per_mtok_cache_usd"]),
    }

def cost_usd_events(events: List[Dict[str, Any]], pricing: Dict[str, Any]) -> Dict[str, float]:
    """Per-bucket USD cost computed EVENT BY EVENT so the per-model price
    table applies: an event whose ``model`` has an entry in
    ``pricing["model_prices"]`` is costed with that model's own rates; any
    other event uses the flat ``price_per_mtok_*`` rates. With an empty
    table this equals ``cost_usd(summarize(events), pricing)`` exactly."""
    p = {**DEFAULT_PRICING, **(pricing or {})}
    table = p.get("model_prices") or {}
    flat = {"in": float(p["price_per_mtok_in_usd"]),
            "out": float(p["price_per_mtok_out_usd"]),
            "cache": float(p["price_per_mtok_cache_usd"])}
    out = {"in": 0.0, "out": 0.0, "cache": 0.0}
    for e in events:
        rates = table.get(e.get("model", "")) or {}
        for bucket in ("in", "out", "cache"):
            try:
                rate = float(rates.get(bucket, flat[bucket]))
            except (TypeError, ValueError):
                rate = flat[bucket]
            out[bucket] += e.get(bucket, 0) / 1e6 * rate
    return out

def format_cost(usd: float, pricing: Dict[str, Any], digits: Optional[int] = None) -> str:
    """Format a USD amount in the display currency. ``digits`` caps the number
    of decimal places (e.g. ``digits=2`` for the Total cost / Budget cards, so
    USD shows $1.23 not the default up-to-4 $1.2345) — never ADDS decimals to a
    currency that uses fewer (VND stays whole, JPY one place)."""
    p = {**DEFAULT_PRICING, **(pricing or {})}
    cur = p.get("currency", "USD")
    rate = {"USD": 1.0, "VND": float(p["usd_to_vnd"]), "JPY": float(p["usd_to_jpy"])}.get(cur, 1.0)
    symbol, cur_digits = _CURRENCY_FMT.get(cur, ("$", 2))
    if digits is not None:
        cur_digits = min(cur_digits, digits)
    value = usd * rate
    return f"{symbol}{value:,.{cur_digits}f}"

def format_cost_compact(usd: float, pricing: Dict[str, Any]) -> str:
    """Compact cost format for the Dashboard chart's y-axis/endpoint labels —
    always 2 decimals (not format_cost's up-to-4 for USD) and abbreviated with
    K/M above 1,000/1,000,000, same convention as ``fmt_tokens``. The chart's
    y-axis label box is narrow; the longer full-precision string used to
    overflow it, visually clipping/obscuring the leading currency symbol."""
    p = {**DEFAULT_PRICING, **(pricing or {})}
    cur = p.get("currency", "USD")
    rate = {"USD": 1.0, "VND": float(p["usd_to_vnd"]), "JPY": float(p["usd_to_jpy"])}.get(cur, 1.0)
    symbol, _digits = _CURRENCY_FMT.get(cur, ("$", 2))
    value = usd * rate
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000:
        body = f"{value / 1_000_000:,.2f}M"
    elif value >= 1_000:
        body = f"{value / 1_000:,.2f}K"
    else:
        body = f"{value:,.2f}"
    return f"{sign}{symbol}{body}"
