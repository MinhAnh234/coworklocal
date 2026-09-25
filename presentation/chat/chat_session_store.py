"""Lưu, nạp lại phiên chat và đếm token — R08-T06.

``_reattach_running_turn`` là phần tinh tế nhất: người dùng chuyển sang
phiên khác rồi quay lại trong khi lượt cũ vẫn đang chạy, thì phải nối
lại đúng luồng đó chứ không được khởi động lại.

``_compress_messages`` nén ngữ cảnh khi hội thoại dài quá cửa sổ model.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt
from ...core.worker import AgentWorker
from ...i18n import tr
from ...ui.dialog_buttons import confirm


class ChatSessionMixin:
    """Trộn vào ChatPanel."""

    def _save_snapshot(self, session_id: str, messages: List[Dict[str, Any]],
                       title: str, inputs: Optional[List[str]] = None,
                       history_dir: Optional[Path] = None) -> None:
        """Persist a conversation by id (used both to register it in History the
        moment it starts and to save a finished background turn). No-op until it has
        a user message. Never raises into the UI.

        ``history_dir``, when given, is used INSTEAD of
        ``self.ctx.config.history_dir()`` — see ``_persist_session`` (R06-T04):
        a background turn must save into the project it started in, not
        whichever project happens to be selected in the Workspace screen by
        the time the turn finishes.
        """
        if not self.ctx.config.history.get("autosave", True):
            return
        if not any(m.get("role") == "user" for m in messages):
            return
        try:
            from ...core.history import save_conversation
            save_conversation(
                history_dir if history_dir is not None else self.ctx.config.history_dir(),
                self.kind, session_id,
                messages, title, inputs=list(inputs or []), outputs=[],
                # Only the CURRENT view knows its project for sure; a background
                # turn's save must not overwrite another conversation's project
                # with whatever the user is viewing now (save_conversation keeps
                # the stored value when '' is passed).
                project_id=self.project_id if session_id == self.session_id else "",
            )
        except Exception:
            pass  # persistence must never disrupt the UI

    def _persist_session(self, ctx: Dict[str, Any]) -> None:
        """Save a BACKGROUND turn's conversation (it isn't the current view, so the
        view-based _autosave can't). Outputs are rebuilt from disk on reopen."""
        self._save_snapshot(ctx["home_id"], ctx["home_messages"],
                            ctx.get("home_title", ""),
                            inputs=ctx.get("record", {}).get("inputs", []),
                            history_dir=ctx.get("home_history_dir"))
        self.history_changed.emit()


    def _usage_label(self) -> str:
        """Nhãn dùng để gom số liệu token của hội thoại này: tiêu đề, hoặc id phiên nếu
        chưa có tiêu đề.
        """
        return self.title or self.session_id

    def _session_events(self):
        """Các bản ghi token thuộc riêng hội thoại này."""
        from ...core import usage_tracker as ut
        label = self._usage_label()
        return [e for e in ut.load_events()
                if e.get("source") == self.kind and e.get("label") == label]

    def refresh_usage(self) -> None:
        """Show what this conversation has already cost.

        The label was written only at the end of a turn, so opening a thread
        from History left the strip blank however much it had spent.
        """
        from ...core import model_pricing as mp
        from ...core import usage_tracker as ut

        cur = self._usage_snapshot()
        if not (cur["in"] or cur["out"] or cur["cache"]):
            self._usage_total_lbl.setText("")
            return
        # same source _show_usage reads, so the two never disagree
        pricing = {**ut.DEFAULT_PRICING, **(self.ctx.config.data.get("usage") or {})}
        self._usage_total_lbl.setText(
            f"↓{mp.format_tokens(cur['in'])} ↑{mp.format_tokens(cur['out'])} "
            f"▤{mp.format_tokens(cur['in'] + cur['out'] + cur['cache'])} "
            f"{ut.format_cost(self._session_cost_usd(), pricing)}")

    def _usage_snapshot(self) -> Dict[str, int]:
        """Cumulative in/out/cache tokens for THIS conversation so far."""
        snap = {"in": 0, "out": 0, "cache": 0}
        for e in self._session_events():
            snap["in"] += int(e.get("in", 0) or 0)
            snap["out"] += int(e.get("out", 0) or 0)
            snap["cache"] += int(e.get("cache", 0) or 0)
        return snap

    def _session_cost_usd(self) -> float:
        """Tổng chi phí (USD) của hội thoại này, tính theo bảng đơn giá hiện hành."""
        from ...core import model_pricing as mp
        return sum(mp.turn_cost_usd(e.get("model", ""), e.get("in", 0), e.get("out", 0),
                                    self.ctx.config) for e in self._session_events())

    def _show_usage(self, ctx: Dict[str, Any]) -> None:
        """Per-turn footer under the assistant message + the running conversation
        total (bottom-left). Cost uses the Monitoring model-price table and the
        display currency, and auto-updates when the model is switched."""
        from ...core import model_pricing as mp, usage_tracker as ut
        cur = self._usage_snapshot()
        base = ctx.get("usage_base") or {"in": 0, "out": 0, "cache": 0}
        d_in = max(0, cur["in"] - base.get("in", 0))
        d_out = max(0, cur["out"] - base.get("out", 0))
        d_cache = max(0, cur["cache"] - base.get("cache", 0))
        pricing = {**ut.DEFAULT_PRICING, **(self.ctx.config.data.get("usage") or {})}
        # Condensed format (tight icon+value, single-space separators) — the
        # old 4-space-wide separators made this label wide enough that it got
        # crowded out of the composer's bottom row by the Local-folder button
        # sharing the same row.
        bub = ctx.get("last_assistant")
        if bub is not None and (d_in or d_out):
            turn_usd = mp.turn_cost_usd(self._model, d_in, d_out, self.ctx.config)
            bub.add_usage(f"↓{mp.format_tokens(d_in)} ↑{mp.format_tokens(d_out)} "
                          f"▤{mp.format_tokens(d_in + d_out + d_cache)} "
                          f"{ut.format_cost(turn_usd, pricing)}")
        self._usage_total_lbl.setText(
            f"↓{mp.format_tokens(cur['in'])} ↑{mp.format_tokens(cur['out'])} "
            f"▤{mp.format_tokens(cur['in'] + cur['out'] + cur['cache'])} "
            f"{ut.format_cost(self._session_cost_usd(), pricing)}")

    def _autosave(self) -> None:
        """Tự lưu hội thoại sau mỗi mốc an toàn.

        Bỏ qua khi người dùng tắt tự lưu, và khi hội thoại chưa có tin nhắn nào của
        người dùng — không tạo file rỗng cho một khung chat vừa mở ra rồi bỏ đấy.
        """
        if not self.ctx.config.history.get("autosave", True):
            return
        if not any(m.get("role") == "user" for m in self.messages):
            return
        try:
            from ...core.history import save_conversation
            path = save_conversation(
                self.ctx.config.history_dir(), self.kind, self.session_id,
                self.messages, self.title,
                inputs=self.input_section.paths(),
                outputs=self.output_section.paths(),
                project_id=self.project_id,
            )
            # Remember this as the session to restore next launch (crash-safe).
            last = self.ctx.config.data.setdefault("last_session", {})
            if last.get(self.kind) != str(path):
                last[self.kind] = str(path)
                self.ctx.save()
        except Exception:
            pass  # autosave must never disrupt the UI

    def _maybe_notify_teams(self, result: Dict[str, Any]) -> None:
        """Gửi nhắc qua Teams khi lượt chạy xong, nếu đã bật và đã cấu hình webhook."""
        teams = self.ctx.config.teams
        notifier = self.ctx.teams_notifier()
        if not (teams.get("notify_on_complete") and notifier.configured):
            return
        summary = self._last_assistant_text() or "Task completed."
        facts = {"Session": self.session_name, "Model": self.ctx.config.model_label()}
        wd = self.workspace_dir()
        if wd:
            facts["Folder"] = str(wd)
        if result.get("error"):
            facts["Status"] = "Error"

        def job(worker: AgentWorker):
            """Chạy nền: gửi thẻ thông báo lên webhook Teams."""
            ok, detail = notifier.send(f"Cowork {self.session_name} — task done", summary[:1200], facts)
            return {"ok": ok, "detail": detail}

        w = AgentWorker(job)
        w.finished_ok.connect(lambda r: self.status_message.emit(r.get("detail", "")))
        self._teams_worker = w
        w.start()

    def new_session(self) -> None:
        """Mở một hội thoại mới.

        Cho phép ngay cả khi đang chạy dở: lượt đang chạy vẫn tiếp tục ở nền và vẫn
        ghi vào hội thoại cũ của nó.
        """
        from ...core.history import new_session_id

        self.show_welcome(True)     # hội thoại rỗng -> màn giới thiệu

        # Allowed while work is running: current turns keep going in the background.
        self._detach_live_turns()
        self.messages = []
        self.session_id = new_session_id()
        self.title = ""
        self.turns = []
        self.chat_view.clear()
        self.composer.clear_queue()
        self.composer.reset_input()   # clear leftover text / "Attached: …" hint
        self.plan_section.clear()
        self.input_section.clear()
        self.output_section.clear()
        self.graph_event.emit(self.session_name, {"type": "reset"})
        self._sync_indicators()
        self.history_changed.emit()   # current view changed → refresh History highlight

    def _notify_title(self) -> None:
        """Let a screen that heads itself with the thread title follow along.

        The thread also decides what the usage strip should read, so refresh
        that here rather than at each of the three places the title changes.
        """
        hook = getattr(self, "refresh_title", None)
        if callable(hook):
            hook()
        if getattr(self, "_usage_total_lbl", None) is not None:
            self.refresh_usage()

    def set_title_label(self, lbl, fallback: str) -> None:
        """Đặt tiêu đề hội thoại lên nhãn: tối đa 10 ký tự, bản đầy đủ ở tooltip."""
        from .chat_helpers import clip_chars

        full = self.title or fallback
        lbl.setText(clip_chars(full))
        lbl.setToolTip(full)

    def apply_renamed_title(self, session_id: str, title: str) -> None:
        """Hội thoại đang mở vừa được đổi tên ở cột lịch sử: đổi luôn ``self.title``.

        Không chỉ để thanh tiêu đề cập nhật ngay — lượt chat kế tiếp lưu bằng
        ``self.title``, giữ tên cũ sẽ ghi đè mất tên người dùng vừa đặt."""
        if session_id and session_id == self.session_id:
            self.title = title
            self._notify_title()

    def load_conversation(self, conv: Dict[str, Any]) -> None:
        """Switch the view to a stored conversation. Allowed while work is running —
        the current turns keep going in the background."""
        sid = conv.get("session_id") or self.session_id
        # Clicking the conversation you're already viewing while it has a running
        # turn must NOT tear down its live rendering — just no-op.
        if sid == self.session_id and self._view_busy():
            return
        # Hoi thoai da luu thi co tin nhan -> khung chat, khong phai man gioi thieu.
        self.show_welcome(not (conv.get("messages") or []))
        self._detach_live_turns()
        self.session_id = sid
        self.title = conv.get("title", "")
        self._notify_title()
        self.project_id = conv.get("project_id", "") or "default"
        # If this conversation still has a turn running in the background, attach to
        # its LIVE message list (not a stale disk copy) so the two never race on save.
        if sid in self._sessions_live:
            self.messages = self._sessions_live[sid]
        else:
            self.messages = list(conv.get("messages", []))
        self.turns = []
        self.chat_view.clear()
        self.composer.clear_queue()
        self.composer.reset_input()   # clear leftover text / "Attached: …" hint
        self.plan_section.clear()
        self.input_section.clear()
        self.output_section.clear()
        self.graph_event.emit(self.session_name, {"type": "reset"})
        for m in self.messages:
            role = m.get("role")
            if role == "user":
                self.chat_view.add_user(m.get("content", ""))
                self.graph_event.emit(self.session_name, {"type": "user", "content": m.get("content", "")})
            elif role == "assistant":
                if m.get("content"):
                    self.chat_view.add_assistant(self.assistant_title()).set_markdown(m["content"])
                    self.graph_event.emit(self.session_name, {"type": "assistant_done", "content": m["content"]})
                for tc in m.get("tool_calls", []) or []:
                    self.graph_event.emit(self.session_name, {
                        "type": "tool_proposed", "name": tc.get("name", ""),
                        "args": tc.get("arguments", {}),
                        "preview": {"text": str(tc.get("arguments", {}))},
                    })
            elif role == "tool":
                self.chat_view.add_tool(m.get("name", "tool"), m.get("content", ""), True)
                self.graph_event.emit(self.session_name, {
                    "type": "tool_result", "name": m.get("name", ""),
                    "ok": True, "output": m.get("content", ""),
                })
        # Restore the Input/Output file lists too.
        for p in conv.get("inputs", []):
            self.input_section.add(p)
        for p in conv.get("outputs", []):
            self.output_section.add(p)
        # If this conversation has a turn running in the background, re-render the
        # in-progress task and re-attach it so it keeps streaming live here.
        running = self._running_ctx_for(sid)
        if running is not None:
            self._reattach_running_turn(running)
        elif self.messages:
            # A past (already finished) session — surface a link to its output
            # folder even though the live "done" marker isn't replayed.
            folder = self.workspace_dir()
            if folder:
                marker = self.chat_view.add_status(tr("chat.session_folder_marker"))
                marker.add_folder_link(str(folder), tr("chat.open_folder_short"))
        # Jump to the newest message after the transcript is rebuilt.
        self.chat_view.scroll_to_bottom()
        self._sync_indicators()
        self.history_changed.emit()   # current view changed → refresh History highlight

    def _delete_turn(self, turn: Dict[str, Any]) -> None:
        """Xoá một lượt khỏi hội thoại, hỏi trước khi xoá cả tệp nó đã tạo ra.

        Liệt kê tối đa 12 tệp trong hộp xác nhận — dài hơn thì người dùng không đọc
        mà chỉ bấm Đồng ý.
        """
        files = [p for p in (turn.get("inputs", []) + turn.get("outputs", [])) if p]
        if files:
            preview = "\n".join("• " + str(p) for p in files[:12])
            prompt = tr("chatpanel.delete_confirm_files", n=len(files), preview=preview)
        else:
            prompt = tr("chatpanel.delete_confirm_plain")
        if not confirm(self, tr("chatpanel.delete_confirm_title"), prompt):
            return
        for bubble in turn.get("bubbles", []):
            bubble.setParent(None)
            bubble.deleteLater()
        ids = {id(m) for m in turn.get("messages", [])}
        if ids:
            self.messages = [m for m in self.messages if id(m) not in ids]
        for p in files:
            try:
                fp = Path(p)
                if fp.is_file():
                    fp.unlink()
            except OSError:
                pass
        if turn in self.turns:
            self.turns.remove(turn)
        self._rebuild_io()
        self._autosave()
        self.status_message.emit(tr("chatpanel.delete_done"))

    def _compress_messages(self) -> None:
        """Manual compress: keep the system prompt + the last 2 turns verbatim and
        DIGEST all older messages into one compact summary, shrinking it until the
        whole conversation is under 25% of its original token size."""
        if self._view_busy():
            self.status_message.emit(tr("chatpanel.compress_busy"))
            return
        from ...core.usage_tracker import estimate_tokens

        msgs = list(self.messages)

        def _tok(ms):
            """Ước lượng tổng token của một danh sách tin nhắn."""
            return sum(estimate_tokens(str(m.get("content", ""))) for m in ms)

        orig = _tok(msgs)
        systems = [m for m in msgs if m.get("role") == "system"]
        rest = [m for m in msgs if m.get("role") != "system"]
        starts = [i for i, m in enumerate(rest) if m.get("role") == "user"]
        if len(starts) <= 2 or orig <= 0:
            self.status_message.emit(tr("chatpanel.compress_short"))
            return
        cut = starts[-2]                       # keep the last 2 turns verbatim
        old, recent = rest[:cut], rest[cut:]
        old_tok = _tok(old) or 1               # target: digest < 25% of the OLD part

        def _digest(per_msg: int):
            """Rút gọn các tin nhắn cũ thành tóm tắt một dòng mỗi tin, mỗi tin không quá
            ``per_msg`` ký tự.
            """
            parts = []
            for m in old:
                c = str(m.get("content", "")).strip().replace("\n", " ")
                if c:
                    parts.append(f"- {m.get('role', '')}: {c[:per_msg]}")
            body = "\n".join(parts)
            return {"role": "user",
                    "content": f"[{tr('chatpanel.compress_digest_header', n=len(old))}]\n{body}"}

        per_msg = 240
        digest = _digest(per_msg)
        # shrink the digest until the OLD conversation is under 25% of its size
        while _tok([digest]) > 0.25 * old_tok and per_msg > 20:
            per_msg = max(20, per_msg // 2)
            digest = _digest(per_msg)
        self.messages = systems + [digest] + recent
        pct = int(_tok([digest]) * 100 / old_tok)
        self.status_message.emit(tr("chatpanel.compress_reduced", pct=pct, n=len(old)))



