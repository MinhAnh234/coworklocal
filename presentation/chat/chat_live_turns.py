"""Nối lại lượt đang chạy khi người dùng quay về phiên cũ — R08-T06.

Phần tinh tế nhất của khung chat. Người dùng mở phiên khác rồi quay lại trong
khi lượt cũ VẪN đang chạy: phải nối vào đúng luồng đó và đúng danh sách tin
nhắn đang sống, chứ không được đọc bản trên đĩa (đã cũ) hay khởi động lại.

``_detach_live_turns`` gỡ ra khi rời phiên, ``_reattach_running_turn`` nối
lại khi quay về. Sai một trong hai thì hoặc mất phần agent viết trong lúc
vắng mặt, hoặc hai bên cùng ghi vào một file.

Cùng kiểu mixin, xem ghi chú ở đầu ``presentation/shell/nav_rail.py``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox
from ...core.worker import AgentWorker
from ...i18n import tr


class ChatLiveTurnsMixin:
    """Nối lại lượt đang chạy. Trộn vào ChatPanel."""

    def _detach_live_turns(self) -> None:
        """Before switching away from the current conversation, turn its running
        turns into background jobs: they stop rendering into the (about-to-be-
        cleared) transcript but keep running and save to their own conversation."""
        for c in self._active.values():
            if c.get("home_id") == self.session_id:
                c["detached"] = True
                c["assistant"] = None   # its bubbles are about to be cleared

    def _running_ctx_for(self, session_id: str) -> Optional[Dict[str, Any]]:
        """The in-progress turn's context for a conversation (one at a time), or None."""
        for c in self._active.values():
            if c.get("home_id") == session_id:
                return c
        return None

    def _reattach_running_turn(self, ctx: Dict[str, Any]) -> None:
        """Re-render an in-progress turn into the current transcript and re-attach it
        so it keeps streaming live — used when reopening a running conversation, so
        the user sees the CURRENT task (message + steps so far + live plan), not just
        the last saved state."""
        record = ctx["record"]
        record["bubbles"] = []   # the old bubbles were cleared on the view switch
        # 1) the user's message that is being processed
        ub = self.chat_view.add_user(ctx.get("display_text") or "(attachment)")
        record["bubbles"].append(ub)
        # 2) steps already completed this turn (assistant text / tool results); found
        #    by identity after the user message (a system prompt may sit before it).
        #    Snapshot the list — the worker thread may still be appending to it.
        msgs = list(ctx.get("messages", []))
        ui = next((i for i, m in enumerate(msgs) if m is ctx.get("user_msg")), -1)
        for m in (msgs[ui + 1:] if ui >= 0 else []):
            role = m.get("role")
            if role == "assistant" and (m.get("content") or "").strip():
                b = self.chat_view.add_assistant(self.assistant_title())
                b.set_markdown(m["content"])
                record["bubbles"].append(b)
            elif role == "tool":
                b = self.chat_view.add_tool(m.get("name", "tool"), m.get("content", ""), True)
                record["bubbles"].append(b)
        # 3) the live plan checklist (if any) — inline, expandable
        steps = ctx.get("plan_steps") or []
        if steps:
            self.on_plan(steps)
            from ...ui.chat_panel import _format_plan_steps
            pb = self.chat_view.add_plan(_format_plan_steps(steps))
            record["bubbles"].append(pb)
            ctx["plan_bubble"] = pb
        # 4) the partial answer of the step currently streaming — re-attach so new
        #    deltas keep appending to this bubble.
        ctx["assistant"] = None
        ctx["reasoning"] = None
        if (ctx.get("partial") or "").strip():
            ab = self.chat_view.add_assistant(self.assistant_title())
            ab.set_markdown(ctx["partial"])
            record["bubbles"].append(ab)
            ctx["assistant"] = ab
        # 5) live again → future events render here
        ctx["detached"] = False
        self.chat_view.scroll_to_bottom()

    def running_session_ids(self):
        """Set of conversation ids that currently have a turn running (for the
        History status markers)."""
        return set(self._sessions_live)
