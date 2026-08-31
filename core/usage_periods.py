"""Gộp mức dùng theo khoảng thời gian — R09-T02.

Ngày / tuần / tháng / quý: ranh giới khoảng, nhãn hiển thị, chuỗi số vẽ biểu
đồ. Thuần tính toán trên danh sách sự kiện, không đụng đĩa.
"""
from __future__ import annotations

import json
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..config import CONFIG_DIR
from . import model_pricing as mp
from .usage_cost import cost_usd_events

def bucketed_series(events: List[Dict[str, Any]], granularity: str = "day",
                    pricing: Dict[str, Any] = None, last: int = None) -> List[tuple]:
    """Group usage events into time buckets → ordered ``[(label, tokens, cost_usd)]``.

    ``granularity``: ``day`` (YYYY-MM-DD) · ``month`` (YYYY-MM) · ``year`` (YYYY).
    ``last`` keeps only the most recent N buckets (for the dashboard chart)."""
    from collections import OrderedDict
    pricing = pricing or {}

    def _key(ts: Any) -> str:
        """Khoá gom nhóm của một mốc thời gian theo độ mịn (tuần/tháng/năm)."""
        s = str(ts or "")[:10]
        if granularity == "year":
            return s[:4]
        if granularity == "month":
            return s[:7]
        return s

    buckets: "OrderedDict[str, List[Dict[str, Any]]]" = OrderedDict()
    for e in sorted(events, key=lambda ev: str(ev.get("ts", ""))):
        k = _key(e.get("ts"))
        if k:
            buckets.setdefault(k, []).append(e)
    out = []
    for k, evs in buckets.items():
        tokens = sum(int(e.get("in", 0) or 0) + int(e.get("out", 0) or 0)
                     + int(e.get("cache", 0) or 0) for e in evs)
        cost = sum(cost_usd_events(evs, pricing).values())
        out.append((k, tokens, cost))
    if last and len(out) > last:
        out = out[-last:]
    return out

def period_bounds(gran: str, offset: int, today: Optional[date] = None) -> tuple:
    """[start, end) dates of the period ``offset`` periods from the current one
    (0 = current, -1 = the previous week/month/year). Weeks run Mon→Sun."""
    from datetime import timedelta
    today = today or date.today()
    if gran == "week":
        monday = today - timedelta(days=today.weekday())     # Monday of this week
        start = monday + timedelta(weeks=offset)
        return start, start + timedelta(days=7)
    if gran == "year":
        y = today.year + offset
        return date(y, 1, 1), date(y + 1, 1, 1)
    # month (default)
    base = today.year * 12 + (today.month - 1) + offset
    y, m = divmod(base, 12)
    y2, m2 = divmod(base + 1, 12)
    return date(y, m + 1, 1), date(y2, m2 + 1, 1)

def _period_label(gran: str, start: date) -> str:
    """Nhãn hiển thị của một kỳ: thứ Hai đầu tuần, YYYY-MM, hoặc năm."""
    if gran == "week":
        return start.isoformat()          # the week's Monday (YYYY-MM-DD)
    if gran == "year":
        return str(start.year)
    return start.strftime("%Y-%m")

def _sum_between(events: List[Dict[str, Any]], start: date, end: date,
                 pricing: Dict[str, Any]) -> tuple:
    """Tổng token và chi phí của các sự kiện trong khoảng ``[start, end)``."""
    lo, hi = start.isoformat(), end.isoformat()
    evs = [e for e in events if lo <= str(e.get("ts", ""))[:10] < hi]
    tokens = sum(int(e.get("in", 0) or 0) + int(e.get("out", 0) or 0)
                 + int(e.get("cache", 0) or 0) for e in evs)
    cost = sum(cost_usd_events(evs, pricing).values()) if evs else 0.0
    return tokens, cost

def period_totals(events: List[Dict[str, Any]], gran: str, pricing: Dict[str, Any],
                  offset: int = 0, today: Optional[date] = None) -> tuple:
    """(tokens, cost_usd) for the single period ``offset`` periods from now."""
    start, end = period_bounds(gran, offset, today)
    return _sum_between(events, start, end, pricing)

def period_window(events: List[Dict[str, Any]], gran: str, pricing: Dict[str, Any],
                  count: int, offset: int = 0, today: Optional[date] = None) -> List[tuple]:
    """``count`` consecutive, ZERO-FILLED periods ending at (current + offset),
    ordered oldest→newest → ``[(label, tokens, cost_usd)]``. ``offset`` (≤ 0)
    pages the window into the past for the Dashboard's prev/next navigation."""
    out = []
    for i in range(count - 1, -1, -1):
        start, end = period_bounds(gran, offset - i, today)
        tok, cost = _sum_between(events, start, end, pricing)
        out.append((_period_label(gran, start), tok, cost))
    return out

def period_breakdown(events: List[Dict[str, Any]], gran: str, pricing: Dict[str, Any],
                     offset: int = 0, today: Optional[date] = None) -> List[tuple]:
    """Break the SELECTED period (``offset`` periods from now) into its sub-parts
    → ``[(label, tokens, cost_usd)]``:
      · week  → 7 days Mon→Sun (label ``MM/DD``)
      · month → weeks W1…Wn (7-day chunks from the 1st)
      · year  → 12 months (label ``01``…``12``)."""
    from datetime import timedelta
    start, end = period_bounds(gran, offset, today)
    out = []
    if gran == "week":
        for i in range(7):
            d = start + timedelta(days=i)
            tok, cost = _sum_between(events, d, d + timedelta(days=1), pricing)
            out.append((d.strftime("%m/%d"), tok, cost))
    elif gran == "year":
        for m in range(1, 13):
            ms = date(start.year, m, 1)
            me = date(start.year + 1, 1, 1) if m == 12 else date(start.year, m + 1, 1)
            tok, cost = _sum_between(events, ms, me, pricing)
            out.append((f"{m:02d}", tok, cost))
    else:  # month → weeks W1..Wn
        ndays = (end - start).days
        wk, day = 1, 1
        while day <= ndays:
            ws = date(start.year, start.month, day)
            we = date(start.year, start.month, day + 7) if day + 7 <= ndays else end
            tok, cost = _sum_between(events, ws, we, pricing)
            out.append((f"W{wk}", tok, cost))
            wk += 1
            day += 7
    return out

def period_range_label(gran: str, offset: int, today: Optional[date] = None) -> str:
    """Human label for the selected period (shown in the Dashboard header) —
    week → MM/DD – MM/DD, month → YYYY/MM, year → YYYY."""
    from datetime import timedelta
    start, end = period_bounds(gran, offset, today)
    if gran == "week":
        last_day = end - timedelta(days=1)
        return f"{start.strftime('%m/%d')} – {last_day.strftime('%m/%d')}"
    if gran == "year":
        return str(start.year)
    return start.strftime("%Y/%m")
