"""Chạy một lượt chat, từ lúc bấm Gửi tới lúc kết thúc — R08-T06.

``_start_turn`` (144 dòng) và ``_on_event`` (127) là hai hàm dài nhất
trong màn này, và cố ý để nguyên: cái đầu dựng trọn ngữ cảnh một lượt
rồi giao cho luồng nền, cái sau phân nhánh theo từng loại sự kiện phát
về. Cắt nhỏ thì phải chuyền hàng chục biến trạng thái qua lại.

Mỗi lượt có luồng riêng và ngữ cảnh riêng, nên chạy song song nhiều lượt
trong cùng một khung chat được.
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


class ChatTurnRunnerMixin:
    """Trộn vào ChatPanel."""

    def submit(self, text: str, attachments: Optional[List[str]] = None) -> None:
        # Composer only emits 'submitted' when not busy; queued items are
        # drained from here after each turn completes.
        """Gửi một tin nhắn mới.

        Composer chỉ phát ``submitted`` khi khung chat đang rảnh; tin xếp hàng được
        rút dần trong :meth:`_drain_queue` sau mỗi lượt xong.
        """
        self._start_turn(text, attachments or [])

    def run_prompts(self, prompts: List[str]) -> None:
        """Enqueue several prompts and run them (used by flows). They start up to
        the parallel limit; the rest stay queued and start as slots free up."""
        prompts = [p for p in prompts if p and p.strip()]
        if not prompts:
            return
        for p in prompts:
            self.composer.enqueue(p)
        self._drain_queue()

    def build_job(self, text: str, messages: List[Dict[str, Any]],
                  out_dir: Optional[Path]):
        """Return the agent job for this turn.

        ``messages`` is the turn's OWN message list (a snapshot of the history so
        far plus the new user message) — the job must read/append to it, never to
        ``self.messages``, so parallel turns don't race. ``out_dir`` is the turn's
        isolated output folder (or None when the tab produces no files)."""
        raise NotImplementedError

    def _start_turn(self, text: str, attachments: Optional[List[str]] = None) -> None:
        """Khởi động một lượt chat: xử lý lệnh ``/skill``, dựng snapshot yêu cầu, rồi
        chạy agent ở luồng nền.

        Lệnh ``/skill`` dạng liệt kê/chọn được trả lời tại chỗ, không tốn một lượt
        gọi model nào.
        """
        attachments = attachments or []
        typed = text
        prefix, request, info = self._apply_skill_command(text)
        # Moi duong tra ve som duoi day cung them mot bong nguoi dung vao khung,
        # nen man gioi thieu phai nhuong cho ngay tai day — dat sau tung
        # add_user() thi de sot dung mot nhanh, va nhanh do se hien ca hai thu.
        self.show_welcome(False)
        if info is not None:
            # A local /skill command (list / select / error) — answer inline.
            self.chat_view.add_user(typed)
            self.chat_view.add_assistant(self.assistant_title()).set_markdown(info)
            self._drain_queue()
            return
        text = request
        # /agent directive → apply a named agent persona to this turn (parity with
        # the Co4E chat). Combined with any /skill prefix already parsed above.
        agent_prefix, text, agent_info = self._apply_agent_command(text)
        if agent_info is not None:
            self.chat_view.add_user(typed)
            self.chat_view.add_assistant(self.assistant_title()).set_markdown(agent_info)
            self._drain_queue()
            return
        if agent_prefix:
            prefix = f"{prefix}\n\n{agent_prefix}" if prefix else agent_prefix
        if not self.title:
            base = text or (Path(attachments[0]).name if attachments else "(attachment)")
            self.title = (base[:60] + "…") if len(base) > 60 else base
            self._notify_title()

        # Reset the Plan panel so each message starts from a clean checklist (the
        # previous message's plan never lingers/flickers into this one).
        self.plan_section.clear()

        # Each turn works on its OWN message list: a snapshot of the history so far
        # plus the new user message, merged back into self.messages when the turn
        # finishes (see _finalize_turn). This keeps concurrent turns from racing on
        # the shared list. The user content is filled in by the worker (below) —
        # reading attachment text can pip-install a parser or call LibreOffice,
        # which must not run on the UI thread.
        snapshot = list(self.messages)
        user_msg: Dict[str, Any] = {"role": "user", "content": prefix or text}
        local_messages = snapshot + [user_msg]

        # Consume the pending switch-review flag exactly once, for THIS turn —
        # and record what's running it so the next genuine switch is detected
        # against this, not against the selection that was current mid-turn.
        review_switch = self._pending_agent_switch_review
        self._pending_agent_switch_review = False
        self._last_turn_agent_signature = self._agent_signature()

        bubble = self.chat_view.add_user(text or "(attachment)")
        turn: Dict[str, Any] = {"bubbles": [bubble], "messages": [],
                                "inputs": list(attachments), "outputs": []}
        if review_switch:
            # Make the mid-conversation model switch VISIBLE (it was silent
            # before): a one-line notice so the user sees the run continued
            # smoothly on the newly-picked model rather than wondering.
            notice = self.chat_view.add_status(
                tr("chat.model_switched", model=self._current_agent_label()))
            turn["bubbles"].append(notice)
        self.turns.append(turn)
        bubble.add_delete_link(lambda t=turn: self._delete_turn(t))
        if attachments:
            bubble.add_attachments(attachments)
            self.on_inputs_added(attachments)
        folder = self.workspace_dir()
        if folder:
            bubble.add_folder_link(str(folder))

        self.graph_event.emit(self.session_name, {"type": "user", "content": text})

        # Auto Model Routing: may switch this turn's provider/model (Auto), or
        # ask first (Manual). Runs before build_job so build_provider() sees the
        # routed choice. No-op when the toggle is Off.
        self._apply_routing(text, turn)

        self._turn_seq += 1
        out_dir = self._turn_output_dir(f"t{self._turn_seq}")
        base_job = self.build_job(text, local_messages, out_dir)

        def job(worker, _m=user_msg, _t=text, _a=attachments, _p=prefix, _j=base_job,
                _review=review_switch):
            # Worker thread: do the (possibly slow) attachment extraction here so
            # the UI stays responsive, then run the real agent job.
            """Chạy nền: trích nội dung tệp đính kèm rồi mới chạy agent.

            Trích ở luồng nền vì tệp lớn (PDF, Office) mất vài giây — làm ở luồng giao
            diện là cả cửa sổ đứng hình.
            """
            from ...core import usage_tracker
            usage_tracker.set_context(self.kind, self.title or self.session_id)
            body = self._augment(_t, _a, notify=worker.emit_event)
            notes = self._session_notes()
            if notes:
                body = f"{body}\n\n{notes}" if body else notes
            _m["content"] = (_p + "\n\n---\n\n" + body) if _p else body
            if _review:
                # Invisible to the chat bubble (that already shows the plain
                # typed text) — only the payload actually sent to the model
                # carries the note.
                _m["content"] = f"{self._MODEL_SWITCH_REVIEW_NOTE}\n\n{_m['content']}"
            return _j(worker)

        worker = AgentWorker(job)
        # A self-contained context for THIS turn, so its streaming events and files
        # never touch another running turn's state. Signals bind the context via a
        # default-arg so the right ctx is delivered on the UI thread. The "home_*"
        # fields pin the turn to the conversation it started in, so it keeps saving
        # there even if the user switches to another chat while it runs.
        ctx: Dict[str, Any] = {
            "worker": worker, "user_msg": user_msg, "assistant": None,
            "record": turn, "messages": local_messages,
            "snapshot_len": len(snapshot), "out_dir": out_dir,
            "home_id": self.session_id, "home_messages": self.messages,
            "home_title": self.title, "home_out_root": self.workspace_dir(),
            # R06-T04: captured NOW, at submit time — see _persist_session's
            # use of this. Without it, a background turn (this session isn't
            # the one currently displayed) saves into whatever
            # ctx.config.history_dir() resolves to AT THE TIME IT FINISHES,
            # which is the *currently viewed* project's history folder if the
            # user switched projects (ui/workspace_tab.py::_load_current)
            # while this turn was still running — silently saving one
            # project's conversation into another project's history folder.
            "home_history_dir": self.ctx.config.history_dir(),
            "detached": False,
            # For re-rendering the in-progress turn if the user reopens this chat:
            "display_text": text, "partial": "", "plan_steps": [],
            # token/cost accounting: cumulative session usage BEFORE this turn, so
            # the turn's own tokens are (after − before).
            "usage_base": self._usage_snapshot(),
        }
        self._sessions_live[self.session_id] = self.messages
        self._active[worker] = ctx
        self.worker = worker
        # Record the conversation in History right away (with the new user message,
        # so it has a title) — it shows up and can be selected while it's running.
        self._save_snapshot(self.session_id, local_messages, self.title)
        self.history_changed.emit()
        worker.event.connect(lambda ev, c=ctx: self._on_event(c, ev))
        worker.permission_requested.connect(lambda a, c=ctx: self._on_permission(c, a))
        worker.finished_ok.connect(lambda r, c=ctx: self._on_finished(c, r))
        worker.failed.connect(lambda e, c=ctx: self._on_failed(c, e))

        self.composer.set_running(True)
        # One turn at a time PER conversation: this conversation now has a running
        # turn, so further sends here go to the Queue (in order, no interleaving).
        # Other conversations can still run in parallel up to the global cap.
        if self._view_busy() or len(self._active) >= self._max_parallel():
            self.composer.set_busy(True)
        self.status_message.emit(tr("chatpanel.working", name=tr(f"app.tab.{self.kind}")))
        self.thinking.start("chat.running")
        worker.start()



    def _cleanup_turn(self, ctx: Dict[str, Any], ok: bool) -> None:
        """Hook: a turn just ended (``ok`` = finished vs failed). Given the turn
        context, so a tab can promote/discard that turn's isolated output folder.
        No-op in the base."""

    def _session_notes(self) -> str:
        """Extra context folded into the outgoing user message (same layer as
        attachment content) — e.g. Cowork lists files already produced earlier
        in this conversation so the agent can reference/revise them by name
        without the user re-uploading. No-op in the base."""
        return ""




    def _turn_is_live(self, ctx: Dict[str, Any]) -> bool:
        """True when the turn belongs to the currently-viewed conversation."""
        return ctx.get("home_id") == self.session_id and not ctx.get("detached")


    def _on_finished(self, ctx: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Lượt chạy xong: dọn sandbox, giữ lại kế hoạch đã hoàn thành, rồi rút tiếp
        tin trong hàng đợi.

        Chỉ vẽ lên màn khi lượt này vẫn thuộc hội thoại ĐANG mở — người dùng có thể
        đã chuyển sang hội thoại khác trong lúc chờ.
        """
        live = self._turn_is_live(ctx)
        self._end_turn(ctx)
        self._cleanup_turn(ctx, True)   # promote this turn's output folder, if any
        self.status_message.emit(tr("chatpanel.done", name=tr(f"app.tab.{self.kind}")))
        if live:
            self._finalize_plan(ctx)                       # keep the completed plan shown
            try:
                self._show_usage(ctx)                      # per-turn + conversation token/cost
            except Exception:  # noqa: BLE001 — usage display must never break a turn
                pass
            done = self.chat_view.add_success(tr("chat.done_marker"))   # green done marker in the chat box
            folder = self.workspace_dir()
            if folder:
                done.add_folder_link(str(folder), tr("chat.open_output_folder"))
            ctx["record"]["bubbles"].append(done)
            self._autosave()
        else:
            self._persist_session(ctx)   # save the background conversation by id
        self.turn_finished.emit(result)
        # Notify only once EVERYTHING is done (no running turns, empty queue).
        if not self._active and not self.composer.has_queue():
            self._maybe_notify_teams(result)
        self._drain_queue()

    def _on_failed(self, ctx: Dict[str, Any], err: str) -> None:
        """Lượt chạy lỗi: huỷ thư mục kết quả tạm và hiện lỗi (nếu hội thoại còn đang mở)."""
        live = self._turn_is_live(ctx)
        self._end_turn(ctx)
        self._cleanup_turn(ctx, False)   # discard this turn's output sandbox
        if live:
            self.chat_view.add_error(err)
            self.graph_event.emit(self.session_name, {"type": "error", "content": err})
            from ...providers.base import is_model_not_found_error

            if is_model_not_found_error(err) and ctx.get("display_text"):
                # A "soft" failure, not a crash: the selected model itself is
                # invalid/unavailable. Put the message back in the composer so
                # the user can just pick a different model in Settings and hit
                # Send again, instead of having to retype the whole prompt.
                self.composer.set_text(ctx["display_text"])
        else:
            self._persist_session(ctx)
        self.status_message.emit(tr("chatpanel.failed", name=tr(f"app.tab.{self.kind}")))
        self.turn_finished.emit({"error": err})
        self._drain_queue()

    def _drain_queue(self) -> None:
        # Start the NEXT queued message only while THIS conversation is idle (one
        # turn at a time here) and the global cap allows. Starting one flips
        # _view_busy() to True, so exactly one runs — the queue drains in order.
        """Rút tin nhắn kế tiếp trong hàng đợi.

        Chỉ chạy khi hội thoại NÀY đang rảnh và chưa chạm trần số lượt song song
        toàn cục. Khởi động một lượt làm ``_view_busy()`` thành True nên đúng một
        tin được lấy mỗi vòng — hàng đợi rút theo đúng thứ tự.
        """
        while (not self._view_busy() and len(self._active) < self._max_parallel()
               and self.composer.has_queue()):
            nxt = self.composer.pop_next()
            if not nxt:
                break
            self._start_turn(nxt.get("text", ""), nxt.get("attachments", []))

    def stop(self) -> None:
        """Dừng mọi lượt đang chạy của hội thoại này và xoá sạch hàng đợi."""
        if not self._active:
            return
        for w in list(self._active):
            if w.isRunning():
                w.request_stop()
        self.composer.clear_queue()   # don't start anything still waiting
        self.status_message.emit(tr("chatpanel.stopping", name=tr(f"app.tab.{self.kind}")))
