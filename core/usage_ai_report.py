"""Dựng câu nhắc cho AI phân tích mức dùng — R09-T02.

Chỉ sinh văn bản. Tách riêng vì đây là phần dễ đổi nhất (câu chữ, cột hiển
thị) và không liên quan tới việc ghi nhận hay tính tiền.
"""
from __future__ import annotations

import json
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..config import CONFIG_DIR
from . import model_pricing as mp
from .usage_periods import period_breakdown, period_range_label

_AI_ANALYSIS_HEADERS = {
    "vi": ("Nhận xét thói quen", "Cách viết prompt tiết kiệm hơn", "Hành động giảm token"),
    "en": ("Usage habits", "Writing more efficient prompts", "Actions to cut token usage"),
    "ja": ("利用傾向", "より効率的なプロンプトの書き方", "トークン削減のためのアクション"),
}

def build_ai_analysis_prompt(summary: Dict[str, Any], language: str = "vi") -> str:
    """The prompt sent to the model for '✨ AI analyze my usage': aggregated
    numbers only — never raw prompt contents — asking for concrete habits
    feedback and token-saving recommendations, in the CURRENTLY SELECTED
    display language (headers included — not just the model's free-text reply,
    which would otherwise leave the section titles in Vietnamese regardless of
    the app's language setting)."""
    lang_names = {"vi": "Vietnamese", "ja": "Japanese", "en": "English"}
    h1, h2, h3 = _AI_ANALYSIS_HEADERS.get(language, _AI_ANALYSIS_HEADERS["vi"])
    top = "\n".join(f"- {label}: {tok:,} tokens"
                    for label, tok in summary.get("top_labels", []))
    by_source = ", ".join(f"{k}={v:,}" for k, v in summary.get("by_source", []))
    return (
        "You are a token-efficiency coach for an AI desktop app (chat tabs + "
        "scheduled agent tasks). Analyze this usage summary and give the user "
        "practical advice, replying in "
        f"{lang_names.get(language, 'Vietnamese')}.\n\n"
        f"Period stats: {summary.get('turns', 0)} turns, "
        f"input={summary.get('in', 0):,} tokens, output={summary.get('out', 0):,}, "
        f"cache={summary.get('cache', 0):,}, "
        f"avg per prompt={summary.get('avg_per_turn', 0):,}.\n"
        f"Top consumers:\n{top or '- (none)'}\n"
        f"By area: {by_source or '(none)'}\n"
        f"Busiest day: {summary.get('busiest_day')} · busiest hour: {summary.get('busiest_hour')}\n\n"
        "Reply with EXACTLY these 3 short sections, in markdown, using THESE "
        f"section headers verbatim (already in {lang_names.get(language, 'Vietnamese')}):\n"
        f"1. **{h1}** — 2-3 bullet points about the usage pattern.\n"
        f"2. **{h2}** — 3 concrete prompt-writing tips "
        "tailored to the numbers above (e.g. long inputs → attach less / summarize "
        "first; many small turns → batch questions).\n"
        f"3. **{h3}** — 2-3 app-level actions (compact history, "
        "smaller model for simple tasks, reuse task outputs instead of re-asking).\n"
        "Keep the whole reply under 250 words."
    )
