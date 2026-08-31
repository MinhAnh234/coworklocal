"""Nhận sự kiện phát về từ luồng chạy nền — R08-T06.

Agent chạy ở luồng khác và bắn sự kiện dần: chữ, lời gọi tool, kế hoạch, xin
quyền. ``_on_event`` phân nhánh theo loại rồi cập nhật đúng bong bóng.

``_on_permission`` là chỗ giao diện hỏi người dùng — cổng chính sách chỉ trả
lời ALLOW/DENY/ASK, còn hỏi thế nào là việc của tầng này (xem
``docs/architecture/security-policy.md`` mục 5).

Cùng kiểu mixin, xem ghi chú ở đầu ``presentation/shell/nav_rail.py``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, Signal
from ...core.worker import AgentWorker
from ...i18n import tr
from ...state import AppContext
# Nhập thẳng từ chỗ ở thật, không đi qua vỏ chuyển tiếp ``ui/composer.py``:
# vỏ ấy lại nhập ngược vào gói này, nên đi vòng qua nó tạo một chu trình
# import — ``import cowork_local.ui.composer`` khi chưa nạp gói này sẽ hỏng.
from .composer_widget import Composer


class ChatEventStreamMixin:
    """Xử lý sự kiện của một lượt. Trộn vào ChatPanel."""

    def _on_event(self, ctx: Dict[str, Any], ev: Dict[str, Any]) -> None:
        """Nhận một sự kiện từ lượt chạy và vẽ vào dòng thời gian.

        Trạng thái của lượt vẫn được cập nhật kể cả khi hội thoại này không còn hiện
        trên màn — người dùng có thể quay lại và phải thấy đúng những gì đã xảy ra.
        """
        etype = ev.get("type")
        # Track the in-progress state even while this turn is a detached background
        # job, so reopening its conversation can re-render the CURRENT task (partial
        # answer + live plan) — see _reattach_running_turn.
        if etype == "text":
            ctx["partial"] = ctx.get("partial", "") + ev.get("delta", "")
        elif etype == "assistant_done":
            ctx["partial"] = ""
        elif etype == "plan_set":
            ctx["plan_steps"] = ev.get("steps") or []
        # A turn only RENDERS into the transcript/sidebar of the conversation it was
        # started in. If the user navigated away, skip live rendering (the data is
        # tracked above and shown when the conversation is reopened).
        if ctx.get("detached") or ctx.get("home_id") != self.session_id:
            return
        record = ctx["record"]
        if etype == "text":
            self.thinking.stop()  # real output is streaming now
            if ctx["assistant"] is None:
                ctx["assistant"] = self.chat_view.add_assistant(self.assistant_title())
                ctx["last_assistant"] = ctx["assistant"]   # for the per-turn usage footer
                record["bubbles"].append(ctx["assistant"])
                folder = self.workspace_dir()
                if folder:
                    ctx["assistant"].add_folder_link(str(folder))
            ctx["assistant"].append_delta(ev.get("delta", ""))
        elif etype == "assistant_done":
            self.graph_event.emit(self.session_name, ev)
            ctx["assistant"] = None
            ctx["reasoning"] = None   # next step starts a fresh Thinking box
            self._autosave()  # persist latest result (crash-safe, mid-turn)
        elif etype == "tool_proposed":
            # Show WHAT it's doing (e.g. "Creating…" while a document is generated).
            from ...ui.chat_panel import _TOOL_STATUS
            self.thinking.start(_TOOL_STATUS.get(ev.get("name"), "chat.running"))
            if ev.get("name") == "update_plan":
                return  # the plan tool drives the Plan view, not a chat bubble
            # Show the step in the transcript (the code being written / diff /
            # command being run) so the whole process is visible, CLI-style.
            preview = ev.get("preview") or {}
            body = preview.get("text", "")
            if body:
                icons = {"diff": "✎", "command": "▶"}
                title = preview.get("title") or ev.get("name", "tool")
                label = f"{icons.get(preview.get('kind'), '⚙')} {title}"
                # A diff/create/edit preview renders as a colored before/after
                # (additions/deletions), not a flat text block.
                if preview.get("kind") == "diff":
                    step = self.chat_view.add_diff(label, body, True)
                else:
                    step = self.chat_view.add_tool(label, body, True)
                record["bubbles"].append(step)
                # Remember this step's bubble so live stdout/stderr ("tool_output")
                # can be appended to it in real time while the command runs.
                ctx.setdefault("step_bubbles", {})[ev.get("id")] = step
            self.graph_event.emit(self.session_name, ev)
        elif etype == "tool_output":
            # Live output from a running command/install (see run_cancellable) —
            # append to its step bubble so progress is visible before it finishes.
            step = ctx.get("step_bubbles", {}).get(ev.get("id"))
            if step is not None:
                step.append_plain(ev.get("delta", ""))
        elif etype == "notice":
            # A UI-visible aside outside the model's own turn: either a live
            # "reading page X/Y" progress line, or a warning that something
            # (e.g. an attachment) could not be processed.
            if ev.get("level") == "progress":
                self.thinking.set_progress_text(ev.get("text", ""))
            else:
                bubble = self.chat_view.add_tool(
                    tr("chat.attachment_warning_title"), ev.get("text", ""), False)
                record["bubbles"].append(bubble)
        elif etype == "tool_result":
            ctx.get("step_bubbles", {}).pop(ev.get("id"), None)
            self.thinking.start("chat.running")  # back to the model for the next step
            if ev.get("name") == "update_plan":
                return  # plan tool: no chat bubble (Plan view already updated)
            mark = "✓" if ev.get("ok") else "✗"
            tool_bubble = self.chat_view.add_tool(
                f"{ev.get('name')} {mark}", ev.get("output", ""), ev.get("ok", True))
            record["bubbles"].append(tool_bubble)
            folder = ev.get("path") or self.workspace_dir()
            if folder:
                tool_bubble.add_folder_link(str(folder), tr("chat.open_folder"))
            if ev.get("path"):
                record["outputs"].append(ev["path"])
                self.on_file_written(ev["path"])
            # Files produced by a command (e.g. a script that builds a .pptx) —
            # surface the real deliverable, not the generator script.
            for pr in ev.get("produced", []) or []:
                record["outputs"].append(pr)
                self.register_output(pr)
            self.graph_event.emit(self.session_name, ev)
            self._autosave()  # persist after each tool result (crash-safe)
        elif etype == "outputs_removed":
            # Intermediate/generator files were cleaned up — drop them from Output.
            for p in ev.get("paths", []) or []:
                self.output_section.remove(p)
                if p in record.get("outputs", []):
                    record["outputs"].remove(p)
        elif etype == "outputs_added":
            # Deliverables flattened out of a sub-folder into the Output root.
            for p in ev.get("paths", []) or []:
                if p not in record.get("outputs", []):
                    record["outputs"].append(p)
                self.register_output(p)
        elif etype == "reasoning":
            # A reasoning model is "thinking" (Qwen3/DeepSeek-R1 etc.). Relabel the
            # indicator AND stream the reasoning into a collapsed "🧠 Thinking" box
            # so the process is visible without flooding the chat.
            self.thinking.set_label("chat.thinking")
            piece = ev.get("delta", "")
            if piece:
                if ctx.get("reasoning") is None:
                    ctx["reasoning"] = self.chat_view.add_reasoning()
                    record["bubbles"].append(ctx["reasoning"])
                ctx["reasoning"].append_delta(piece)
        elif etype == "plan_set":
            steps = ev.get("steps") or []
            self.on_plan(steps)   # Plan panel (right sidebar)
            # Also show the checklist inline in the chat, updated in place.
            from ...ui.chat_panel import _format_plan_steps
            body = _format_plan_steps(steps)
            if ctx.get("plan_bubble") is None:
                ctx["plan_bubble"] = self.chat_view.add_plan(body)
                record["bubbles"].append(ctx["plan_bubble"])
            else:
                ctx["plan_bubble"].set_plain(body)

    def on_plan(self, steps) -> None:
        """Render the current message's step checklist in the Plan panel above the
        Output list. The agent sends the full list on each ``update_plan`` call."""
        self.plan_section.set_steps(steps)

    def _on_permission(self, ctx: Dict[str, Any], action: Dict[str, Any]) -> None:
        # Auto-approves UNLESS this workspace requires confirming commands —
        # a per-workspace Auto-run override (see AppContext.project_confirm_commands),
        # falling back to the global "confirm before running commands" setting.
        # Resolve on THIS turn's worker, never the latest — several turns may
        # be awaiting approval at once.
        """Một tool cần phê duyệt trước khi chạy.

        Tự đồng ý TRỪ KHI workspace này bật "hỏi trước khi chạy lệnh" (đặt riêng theo
        workspace, không có thì lấy cấu hình chung). Trả lời phải gửi đúng worker của
        LƯỢT NÀY, không phải worker mới nhất — có thể nhiều lượt cùng đang chờ duyệt.
        """
        if self.ctx.project_confirm_commands():
            from ...ui.permission_dialog import PermissionDialog

            approved, _remember = PermissionDialog.ask(action, parent=self)
            ctx["worker"].resolve_permission(approved)
            return
        ctx["worker"].resolve_permission(True)

    def _finalize_plan(self, ctx: Dict[str, Any]) -> None:
        """On a successful finish, keep the plan visible with every step ticked
        'done' (so a completed plan can be reviewed) — it is cleared only when the
        NEXT message starts a fresh plan (see _start_turn)."""
        steps = ctx.get("plan_steps")
        if not steps:
            return
        changed = False
        for s in steps:
            if s.get("status") != "done":
                s["status"] = "done"
                changed = True
        if changed:
            self.on_plan(steps)   # re-render (Plan panel for Cowork / preview for Code)
            pb = ctx.get("plan_bubble")
            if pb is not None:
                pb.set_plain(_format_plan_steps(steps))

    def _finalize_turn(self, ctx: Dict[str, Any]) -> None:
        """Merge one turn's new messages into its OWN conversation's history.

        "New" = everything the job appended after this turn's snapshot. Drop any
        system prompt the agent inserted when the history already carries one, so
        two turns started from an empty history don't leave a duplicate system
        message. Merges into ``home_messages`` (the list of the conversation the
        turn started in) so a background turn saves to the right chat even after the
        user switched away. Same object refs are reused, so _delete_turn's id-based
        removal still finds them."""
        home = ctx["home_messages"]
        local = ctx["messages"]
        new = local[ctx["snapshot_len"]:]
        if any(m.get("role") == "system" for m in home):
            new = [m for m in new if m.get("role") != "system"]
        home.extend(new)
        ctx["record"]["messages"] = new

    def _end_turn(self, ctx: Dict[str, Any]) -> None:
        """Shared teardown for a finished/failed turn: merge history, drop the
        worker, release the conversation once nothing else is running for it, and
        refresh the (global) running/capacity indicators."""
        self._finalize_turn(ctx)
        self._active.pop(ctx["worker"], None)
        home_id = ctx.get("home_id")
        if home_id and not any(c.get("home_id") == home_id for c in self._active.values()):
            self._sessions_live.pop(home_id, None)
        # Update the chat-box indicator for the CURRENT view: stop it once the viewed
        # conversation is idle (a live turn's own streaming manages it otherwise, so
        # we don't restart it here and disturb streaming).
        if not self._view_busy():
            self.thinking.stop()
        self.composer.set_running(bool(self._active))   # Stop shows while anything runs
        # Re-evaluate the per-conversation gate: sends dispatch again only when THIS
        # conversation is idle and the global cap allows.
        self.composer.set_busy(self._view_busy() or len(self._active) >= self._max_parallel())
