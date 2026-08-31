"""Token-usage tracking for the Dashboard tab.

Every provider turn records one event (JSON line, one file per day under
``~/.cowork_local/usage/``): when, which tab/task ("source" + "label"),
provider/model, input/output/cached token counts. Real counts come from the
server's ``usage`` block when the stream includes one; otherwise a ~4 chars ≈
1 token estimate keeps the dashboard useful on gateways that never report
usage (events carry ``"estimated": true`` so the UI can say so).

The turn's source/label is set by the caller ON THE WORKER THREAD via
:func:`set_context` (thread-local — concurrent turns don't mix labels).
"""
from __future__ import annotations

# Giữ đường vào cũ: nhiều nơi import mấy tên này thẳng từ usage_tracker.
from .usage_ai_report import build_ai_analysis_prompt  # noqa: F401
from .usage_cost import (  # noqa: F401
    DEFAULT_PRICING, SUPPORTED_CURRENCIES, cost_usd, cost_usd_events,
    format_cost, format_cost_compact,
)
from .usage_periods import (  # noqa: F401
    bucketed_series, period_bounds, period_breakdown, period_range_label,
    period_totals, period_window,
)

import json
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import CONFIG_DIR
from . import model_pricing as mp

USAGE_DIR = CONFIG_DIR / "usage"

_local = threading.local()

# Process-global identity (NOT thread-local — who's logged in and which
# machine this is are fixed for the whole process, set once right after
# login in app.py::run(), unlike source/label which vary per worker turn).
_identity_account = ""
_identity_machine = ""
_identity_shared_dir = ""


def set_identity(account: str, machine: str, shared_dir: str = "") -> None:
    """Called once after login succeeds. ``shared_dir``, when reachable,
    makes every subsequent :func:`record` ALSO best-effort-append to the
    shared cross-machine telemetry store (see :mod:`telemetry_shared`)."""
    global _identity_account, _identity_machine, _identity_shared_dir
    _identity_account = account or ""
    _identity_machine = machine or ""
    _identity_shared_dir = shared_dir or ""


def set_context(source: str, label: str = "") -> None:
    """Tag subsequent :func:`record` calls on THIS thread (e.g. ("cowork",
    "chat title") / ("task", "task title"))."""
    _local.source = source
    _local.label = label


def current_context() -> tuple:
    """The ``(source, label)`` currently tagged on THIS thread.

    Public counterpart to :func:`set_context`, added for
    ``infrastructure/telemetry/usage_sink.py``: a subscriber that needs to
    attribute one event to a different surface must be able to save the
    caller's context and put it back afterwards, instead of leaving the worker
    thread permanently retagged.
    """
    return getattr(_local, "source", "") or "", getattr(_local, "label", "") or ""


# ---- per-thread usage accumulator -----------------------------------------
# A step/run that wants to know its OWN token/cost (not the all-time file total)
# calls begin_accumulation(), reads accumulated() before/after a unit of work,
# and diffs the two. Because record() runs on the same worker thread that drives
# the work (providers are called synchronously inside it), the thread-local
# total is exactly that thread's usage — concurrent flows on other threads
# accumulate independently, with no locking or label collisions. Used by the
# Co4E runner to attach per-step token/cost to each node's output event.
def begin_accumulation() -> None:
    """Start (or reset) this thread's usage accumulator."""
    _local.acc = {"in": 0, "out": 0, "cache": 0, "events": []}


def accumulated() -> Dict[str, Any]:
    """Snapshot of this thread's accumulated usage since :func:`begin_accumulation`
    (all zeros / empty if never started). ``events`` is a per-turn list of
    ``{model, in, out}`` so a caller can price a delta with the per-model table."""
    acc = getattr(_local, "acc", None)
    if acc is None:
        return {"in": 0, "out": 0, "cache": 0, "events": []}
    return {"in": acc["in"], "out": acc["out"], "cache": acc["cache"],
            "events": list(acc["events"])}


def end_accumulation() -> None:
    """Stop accumulating on this thread (subsequent records aren't tallied)."""
    _local.acc = None


def estimate_tokens(text: str) -> int:
    """Ước lượng số token của một đoạn văn bản theo tỉ lệ 4 ký tự ≈ 1 token.

    Ước lượng thô là đủ: con số này chỉ dùng để quyết định khi nào nén lịch sử,
    không dùng để tính tiền (tiền lấy từ số token thật provider trả về).
    """
    return max(0, len(text or "") // 4)


def record(provider: str, model: str, input_tokens: int, output_tokens: int,
           cached_tokens: int = 0, estimated: bool = False) -> None:
    """Append one usage event. Never raises — usage tracking must never break
    a chat turn."""
    try:
        now = datetime.now()
        event = {
            "ts": now.isoformat(timespec="seconds"),
            "source": getattr(_local, "source", "") or "other",
            "label": getattr(_local, "label", "") or "",
            "provider": provider or "",
            "model": model or "",
            "in": int(input_tokens or 0),
            "out": int(output_tokens or 0),
            "cache": int(cached_tokens or 0),
            "estimated": bool(estimated),
            "account": _identity_account,
            "machine": _identity_machine,
        }
        USAGE_DIR.mkdir(parents=True, exist_ok=True)
        path = USAGE_DIR / f"{now.strftime('%Y-%m-%d')}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        _write_shared(event, now)
        # Feed this thread's live accumulator, if one is active (see above).
        acc = getattr(_local, "acc", None)
        if acc is not None:
            acc["in"] += event["in"]
            acc["out"] += event["out"]
            acc["cache"] += event["cache"]
            acc["events"].append({"model": event["model"], "in": event["in"], "out": event["out"]})
    except Exception:  # noqa: BLE001
        pass


def _write_shared(event: Dict[str, Any], now: datetime) -> None:
    """Best-effort mirror of ``event`` into the shared cross-machine store —
    one file PER MACHINE per day, so no two machines ever write the same
    file (avoids any read-modify-write race). Never raises."""
    if not _identity_shared_dir or not _identity_machine:
        return
    try:
        shared = Path(_identity_shared_dir).expanduser() / "telemetry" / "usage"
        shared.mkdir(parents=True, exist_ok=True)
        path = shared / f"{_identity_machine}-{now.strftime('%Y-%m-%d')}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass


def load_events(start: Optional[date] = None, end: Optional[date] = None,
                directory: Path = None) -> List[Dict[str, Any]]:
    """Events between ``start`` and ``end`` (inclusive; None = unbounded)."""
    directory = directory or USAGE_DIR
    if not directory.exists():
        return []
    events: List[Dict[str, Any]] = []
    for path in sorted(directory.glob("*.jsonl")):
        try:
            day = datetime.strptime(path.stem, "%Y-%m-%d").date()
        except ValueError:
            continue
        if (start and day < start) or (end and day > end):
            continue
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    events.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            continue
    return events


def summarize(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate a list of events into dashboard numbers + habit stats."""
    total_in = sum(e.get("in", 0) for e in events)
    total_out = sum(e.get("out", 0) for e in events)
    total_cache = sum(e.get("cache", 0) for e in events)
    by_label: Dict[str, int] = {}
    by_source: Dict[str, int] = {}
    by_hour: Dict[int, int] = {}
    by_day: Dict[str, int] = {}
    for e in events:
        tok = e.get("in", 0) + e.get("out", 0)
        key = e.get("label") or e.get("source") or "?"
        by_label[key] = by_label.get(key, 0) + tok
        by_source[e.get("source", "?")] = by_source.get(e.get("source", "?"), 0) + tok
        try:
            dt = datetime.fromisoformat(e.get("ts", ""))
            by_hour[dt.hour] = by_hour.get(dt.hour, 0) + tok
            by_day[dt.strftime("%Y-%m-%d")] = by_day.get(dt.strftime("%Y-%m-%d"), 0) + tok
        except ValueError:
            pass
    return {
        "turns": len(events),
        "in": total_in, "out": total_out, "cache": total_cache,
        "total": total_in + total_out,
        "avg_per_turn": (total_in + total_out) // len(events) if events else 0,
        "estimated_share": (sum(1 for e in events if e.get("estimated")) / len(events)
                            if events else 0.0),
        "top_labels": sorted(by_label.items(), key=lambda kv: -kv[1])[:5],
        "by_source": sorted(by_source.items(), key=lambda kv: -kv[1]),
        "busiest_hour": max(by_hour.items(), key=lambda kv: kv[1])[0] if by_hour else None,
        "busiest_day": max(by_day.items(), key=lambda kv: kv[1])[0] if by_day else None,
    }


# ---- cost ------------------------------------------------------------------


# Currencies the display picker offers — exactly the ones format_cost() can
# actually convert to (symbol/precision above + a usd_to_* rate below).






















def set_budget(config, amount: float, currency: Optional[str] = None) -> None:
    """Set (or reset) the spending budget. ``amount`` is read in ``currency``
    (defaults to the current display currency) and converted + stored as USD.

    Remaining balance is always DERIVED fresh from the usage log — never
    incrementally decremented — so re-entering a budget starts a clean window
    instead of double-subtracting spend the old budget had already accounted
    for. The cutoff is an EVENT-COUNT baseline (how many usage events existed
    at the moment of setting), not a timestamp: events append in chronological
    order and ``budget_set_at`` only has 1-second resolution, so a timestamp
    cutoff could mis-include/exclude an event recorded in that same second —
    the count baseline is exact regardless of timing."""
    usage = config.data.setdefault("usage", {})
    ccy = (currency or usage.get("currency") or "USD").upper()
    usage["budget_amount_usd"] = mp.convert(float(amount or 0), ccy, "USD", config)
    usage["budget_set_at"] = datetime.now().isoformat(timespec="seconds")   # display only
    usage["budget_baseline_count"] = len(load_events())                     # the real cutoff


def clear_budget(config) -> None:
    """Remove the budget entirely (Remaining/Budget box goes back to unset)."""
    usage = config.data.setdefault("usage", {})
    usage.pop("budget_amount_usd", None)
    usage.pop("budget_set_at", None)
    usage.pop("budget_baseline_count", None)


def budget_status(config) -> Optional[Dict[str, Any]]:
    """``None`` when no budget is configured. Else a dict with ``amount_usd``,
    ``spent_usd`` (cost of events recorded AFTER the budget was last set — NOT
    the all-time total, so a reset budget never inherits older spend),
    ``remaining_usd``, ``pct_used`` and ``over_85`` (⚠ the Overview/Dashboard
    balance turns red at this point)."""
    usage = (getattr(config, "data", {}) or {}).get("usage") or {}
    amount = usage.get("budget_amount_usd")
    set_at = usage.get("budget_set_at")
    if not amount or not set_at:
        return None
    all_events = load_events()
    baseline = usage.get("budget_baseline_count")
    if baseline is None:
        # backward-compat: a budget set before this field existed — fall back
        # to the timestamp cutoff (best-effort, may double-count a same-second event).
        events = [e for e in all_events if str(e.get("ts", "")) >= str(set_at)]
    else:
        events = all_events[int(baseline):]
    pricing = {**DEFAULT_PRICING, **usage}
    spent = sum(cost_usd_events(events, pricing).values())
    amount = float(amount)
    pct = (spent / amount) if amount else 0.0
    return {
        "amount_usd": amount, "spent_usd": spent, "remaining_usd": amount - spent,
        "pct_used": pct, "over_85": pct >= 0.85, "set_at": set_at,
    }










