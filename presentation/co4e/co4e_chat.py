"""Khung chat của Co4E và việc đếm token — R08-T09.

Khác chat của Cowork ở một điểm: ở đây câu người dùng gõ có thể mang chỉ thị
chọn agent (``_extract_agent_directive``), và mỗi lượt được định tuyến riêng
theo cấu hình routing của Co4E.
"""
from __future__ import annotations

import re
from typing import Dict, List
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QSplitter, QWidget
from ...core import co4e, skills as skills_mod
from ...core.co4e_builtins import BUILTIN_AGENTS
from ...core.worker import AgentWorker
from ...i18n import tr
from ...ui.chat_view import ChatView
from ...ui.icons import icon
from ...presentation.co4e.co4e_chat_view import ChatPanel


class Co4EChatMixin:
    """Khung chat của Co4E Studio: mỗi luồng có nhật ký hội thoại RIÊNG.

    Hai luồng chạy song song không được trộn tin nhắn vào nhau, nên mọi thứ ở
    đây đều lấy nhật ký qua :meth:`_active_log` thay vì dùng một biến chung.
    """
    def _build_chat(self) -> QWidget:
        """Widget construction lives in ``ChatPanel`` (presentation/co4e/
        co4e_chat_view.py); this method just wires the panel's public
        attributes to the handler methods that know about ``self``
        (``_toggle_messages``, ``_chat_send``) and keeps the state that is
        NOT part of the panel's own construction (``_flow_logs`` — per-flow
        ChatView dict, ``_co4e_routed_provider`` — routing override, and
        ``_vsplit_sizes``/``_msgs_collapsed`` — used by ``_toggle_messages``
        below to restore/collapse the splitter) — the panel itself stays
        ignorant of ``Co4ETab``.
        """
        panel = ChatPanel(self.ctx)
        self._chat_widget = panel
        self.msgs_icon = panel.msgs_icon
        self.msgs_title = panel.msgs_title
        self.chat_toggle_btn = panel.chat_toggle_btn
        self.chat_toggle_btn.clicked.connect(self._toggle_messages)
        self._mhdr = panel.header
        self.chat_stack = panel.chat_stack
        self._flow_logs: Dict[str, ChatView] = {}
        self.chat_input_row = panel.chat_input_row
        self._usage_total_lbl = panel.usage_total_lbl
        self.chat_input = panel.chat_input
        self.chat_input.submit.connect(self._chat_send)
        self.chat_send_btn = panel.chat_send_btn
        self.chat_send_btn.clicked.connect(self._chat_send)
        self.co4e_routing_toggle = panel.co4e_routing_toggle
        self._co4e_routed_provider = None   # routing provider override for the next turn
        self._vsplit_sizes = [540, 220]         # sizes to restore when expanded
        self._msgs_collapsed = True
        return panel
    def _toggle_messages(self) -> None:
        """Show/hide the WHOLE chat box (message list + composer) below the
        header. Collapsing hands the freed height to the canvas.

        A QSplitter's ``setMaximumHeight`` on one side does NOT automatically
        redistribute the freed space to the other side — it just shrinks the
        splitter's own total height, leaving the canvas frozen at its old size
        and blank space below it. So this explicitly calls ``setSizes`` on both
        the collapse AND the expand path, computed from the splitter's CURRENT
        total (not a hardcoded guess) — that total stays constant; only how
        it's split between canvas/chat changes."""
        self._msgs_collapsed = not self._msgs_collapsed
        collapsed_h = self._mhdr.sizeHint().height() + 6
        if self._msgs_collapsed:
            if hasattr(self, "_vsplit"):
                self._vsplit_sizes = self._vsplit.sizes()   # remember to restore
            self.chat_stack.hide()
            self.chat_input_row.hide()
            self._chat_widget.setMaximumHeight(collapsed_h)
            self.chat_toggle_btn.setIcon(icon("chevron-up"))     # collapsed → click to expand
            self.chat_toggle_btn.setToolTip(tr("co4e.tt_expand_msgs"))
            if hasattr(self, "_vsplit"):
                total = sum(self._vsplit.sizes()) or (self._vsplit_sizes and sum(self._vsplit_sizes)) or 760
                self._vsplit.setSizes([max(0, total - collapsed_h), collapsed_h])
        else:
            self._chat_widget.setMaximumHeight(16777215)
            self.chat_stack.show()
            self.chat_input_row.show()
            self.chat_toggle_btn.setIcon(icon("chevron-down"))   # expanded → click to collapse
            self.chat_toggle_btn.setToolTip(tr("co4e.tt_collapse_msgs"))
            if getattr(self, "_vsplit_sizes", None) and hasattr(self, "_vsplit"):
                self._vsplit.setSizes(self._vsplit_sizes)
        return
    def _ensure_flow_log(self, wf_id: str) -> ChatView:
        """The ChatView for a flow, created + added to the stack on first use so
        each flow tab keeps a SEPARATE conversation."""
        log = self._flow_logs.get(wf_id)
        if log is None:
            log = ChatView()
            log._co4e_plan_bubble = None       # per-flow 'current plan' bubble
            self._flow_logs[wf_id] = log
            self.chat_stack.addWidget(log)
        return log
    def _active_log(self) -> ChatView:
        """Nhật ký hội thoại của luồng đang mở, tạo lười nếu chưa có."""
        wf = getattr(self, "_wf", None)
        return self._ensure_flow_log(wf.id if wf is not None else "__none__")
    @property
    def chat_log(self) -> ChatView:
        """The conversation of the CURRENTLY-shown flow (all append/stream calls
        go here). Assignment is not supported — logs are per-flow now."""
        return self._active_log()
    @property
    def _plan_bubble(self):
        """Bong bóng kế hoạch của luồng ĐANG mở; ``None`` nếu lượt này chưa có kế hoạch.

        Cất trên chính nhật ký của luồng chứ không trên mixin, để hai luồng chạy song
        song không ghi đè kế hoạch của nhau.
        """
        return getattr(self._active_log(), "_co4e_plan_bubble", None)
    @_plan_bubble.setter
    def _plan_bubble(self, value) -> None:
        """Gắn bong bóng kế hoạch vào nhật ký của luồng đang mở."""
        self._active_log()._co4e_plan_bubble = value
    def _chat_send(self) -> None:
        """Gửi tin nhắn trong khung chat Co4E; đang chạy dở thì bỏ qua."""
        text = self.chat_input.text().strip()
        if not text or self._chat_worker is not None:
            return
        self.chat_input.clear()
        self._append_chat("user", text)
        skill_prefix, request, info = skills_mod.parse_skill_command(text)
        if info is not None:
            self._append_chat("system", info)
            return
        system_parts = []
        if skill_prefix:
            system_parts.append(skill_prefix)
        agent_name, request = self._extract_agent_directive(request)
        model = ""
        if agent_name:
            persona = self._resolve_agent(agent_name)
            if persona is None:
                self._append_chat("system", tr("co4e.agent_not_found", name=agent_name))
                return
            system_parts.append(persona[0])
            model = persona[1]
        # Auto Model Routing — only when the user hasn't pinned an agent's own
        # model (an explicit pin wins). May switch provider+model for this turn.
        if not model:
            model = self._apply_co4e_routing(request)
        self._run_chat_turn(system_parts, request, model)
    def _apply_co4e_routing(self, request: str) -> str:
        """Route this Co4E turn to the best-fit model. Returns the model id to
        use ('' → provider default) and sets ``self._co4e_routed_provider`` when
        a cross-provider switch is chosen.

        R03-T05: the Off/Auto/Manual/Fallback rules are no longer re-implemented
        here — they come from the shared ``RoutingApplicationService``, so Co4E,
        the Cowork chat and AI-Edit can never drift apart again. This method only
        adapts between Co4E's state and the service's DTOs. Never raises — falls
        back to the default model on any error.
        """
        self._co4e_routed_provider = None
        try:
            from ...application.model_routing import (
                RoutingRequest,
                build_routing_application_service,
            )
            from ...ui.routing_toggle import confirm_switch

            cur_provider = self.ctx.config.active_provider
            cur_model = self.ctx.config.provider_conf(cur_provider).get("model", "")
            outcome = build_routing_application_service(self.ctx).resolve(
                RoutingRequest(
                    surface="co4e",
                    prompt=request,
                    current_provider=cur_provider,
                    current_model=cur_model,
                ),
                confirm=lambda decision, timeout: confirm_switch(self, decision, timeout),
            )
            if not outcome.switched:
                return ""   # '' keeps the provider's configured default model
            # Remembered so the worker's build_provider_for() can follow a
            # cross-provider switch, not just a model change.
            self._co4e_routed_provider = outcome.provider
            self._append_chat("system", tr(
                "routing.switched_notice",
                model=outcome.model, task=outcome.task_type,
                gain=f"{outcome.score_gain:.2f}"))
            return outcome.model
        except Exception:  # noqa: BLE001 — routing must never block a Co4E turn
            self._co4e_routed_provider = None
            return ""
    def _extract_agent_directive(self, text: str):
        """Tách lệnh ``/agent:<tên>`` khỏi câu người dùng gõ.

        Trả về (tên agent, phần câu còn lại).
        """
        m = re.search(r"(?<!\S)/agent:([\w\-.]+)", text)
        if not m:
            return "", text
        name = m.group(1)
        rest = (text[:m.start()] + " " + text[m.end():]).strip()
        return name, rest
    def _resolve_agent(self, name: str):
        """Tìm agent theo slug hoặc tên, ưu tiên agent dựng sẵn rồi tới agent tự tạo."""
        low = name.lower()
        for a in BUILTIN_AGENTS:
            if a.slug == low or a.name.lower() == low:
                return (f"You are the {a.role} agent — {a.name}.\n{a.instructions}", "")
        for ca in co4e.list_custom_agents():
            if co4e.slugify(ca.name) == low or ca.name.lower() == low:
                return (f"You are the {ca.role} agent — {ca.name}.\n{ca.instructions}", ca.model)
        return None
    def _run_chat_turn(self, system_parts: List[str], request: str, model: str) -> None:
        """Chạy một lượt chat ở luồng nền, ghi kết quả vào nhật ký của ĐÚNG luồng đã
        phát lệnh — bắt giữ tham chiếu nhật ký ngay từ đầu, vì người dùng có thể
        chuyển sang luồng khác trong lúc chờ.
        """
        self.chat_send_btn.setEnabled(False)
        log = self.chat_log                 # THIS flow's conversation (captured)
        log._co4e_plan_bubble = None        # a fresh plan for this turn
        ctx = self.ctx
        out_dir = self._out_dir()
        sys_text = "\n\n".join(p for p in system_parts if p)
        prompt = f"{sys_text}\n\n{request}" if sys_text else request
        assistant = log.add_assistant()      # stream into this live bubble
        state = {"text": ""}
        wf = getattr(self, "_wf", None)
        wf_id = wf.id if wf is not None else None
        flow_label = wf.name if wf is not None else "flow"

        def job(worker: AgentWorker):
            """Chạy nền: gọi agent Cowork và ghi nhận token đã dùng."""
            from ...core import agent_roles, usage_tracker as ut
            from ...core.chat_agent import run_cowork
            from ...core.co4e_runner import _usage_delta
            # An Auto/Manual routing switch may target a different provider.
            provider = ctx.build_provider_for(getattr(self, "_co4e_routed_provider", None), model or None)
            messages = [{"role": "user", "content": prompt}]
            ut.set_context("co4e", flow_label)   # attribute + measure this turn's usage
            ut.begin_accumulation()
            base = ut.accumulated()

            def _emit(ev):
                """Chuyển tiếp sự kiện từ agent, lọc bỏ thứ khung chat này không dùng."""
                if not isinstance(ev, dict):
                    return
                t = ev.get("type")
                if t == "text":
                    worker.emit_event({"type": "text", "delta": ev.get("delta", "")})
                elif t == "plan_set":
                    worker.emit_event({"type": "plan_set", "steps": ev.get("steps") or []})
            try:
                run_cowork(provider, messages, out_dir, _emit, worker.is_cancelled,
                           security_config=ctx.config, agent_role=agent_roles.COWORK,
                           run_to_completion=True, enforce_rules=False)
                usage = _usage_delta(base, ctx.config)
            finally:
                ut.end_accumulation()
            for m in reversed(messages):
                if m.get("role") == "assistant" and m.get("content"):
                    return {"text": str(m["content"]), "usage": usage}
            return {"text": "", "usage": usage}

        def on_event(ev):
            """Vẽ dần từng mẩu trả lời vào bong bóng của lượt này."""
            if ev.get("type") == "text":
                state["text"] += ev.get("delta", "")
                assistant.set_markdown(state["text"])
                log.scroll_to_bottom()
            elif ev.get("type") == "plan_set":
                self._append_plan(ev.get("steps") or [], log=log)

        def done(result: dict):
            """Lượt xong: chốt nội dung cuối và mở khoá nút gửi."""
            self._chat_worker = None
            self.chat_send_btn.setEnabled(True)
            final = result.get("text") or state["text"]
            assistant.set_markdown(final or "(no output)")
            self._apply_usage(assistant, wf_id, result.get("usage"))
            log.scroll_to_bottom()

        def failed(err: str):
            """Lượt lỗi: hiện lỗi ngay trong nhật ký và mở khoá nút gửi."""
            self._chat_worker = None
            self.chat_send_btn.setEnabled(True)
            self._append_chat("error", f"[error: {err}]", log=log)

        w = AgentWorker(job)
        w.event.connect(on_event)
        w.finished_ok.connect(done)
        w.failed.connect(failed)
        self._chat_worker = w
        w.start()
    def _append_chat(self, role: str, text: str, log: "ChatView" = None) -> None:
        """Add one message bubble to a flow's conversation. ``log`` defaults to the
        active flow's log; a run/stream passes its OWN captured log so events land
        in the right flow even if the user switches tabs mid-run."""
        log = log or self.chat_log
        if role == "user":
            bub = log.add_user(text)
        elif role == "assistant":
            bub = log.add_assistant()
            bub.set_markdown(text)
        elif role == "error":
            bub = log.add_error(text)
        else:                       # system status marker
            bub = log.add_status(text)
        log.scroll_to_bottom()
        return bub
    def _fmt_usage(self, d_in: int, d_out: int, d_cache: int, cost_usd: float) -> str:
        """The Cowork-style footer string: ↓in ↑out ▤(in+out+cache) $cost, priced
        with the Monitoring model-price table in the app's display currency."""
        from ...core import model_pricing as mp, usage_tracker as ut
        pricing = {**ut.DEFAULT_PRICING, **(self.ctx.config.data.get("usage") or {})}
        return (f"↓{mp.format_tokens(d_in)} ↑{mp.format_tokens(d_out)} "
                f"▤{mp.format_tokens(d_in + d_out + d_cache)} "
                f"{ut.format_cost(cost_usd, pricing)}")
    def _apply_usage(self, bub, wf_id, usage) -> None:
        """Attach a token/cost footer to a step's bubble and add it to the flow's
        running total (mirrors Cowork's per-message + conversation-total display)."""
        if not isinstance(usage, dict):
            return
        d_in = int(usage.get("in", 0) or 0)
        d_out = int(usage.get("out", 0) or 0)
        d_cache = int(usage.get("cache", 0) or 0)
        cost = float(usage.get("cost_usd", 0.0) or 0.0)
        if bub is not None and (d_in or d_out):
            try:
                bub.add_usage(self._fmt_usage(d_in, d_out, d_cache, cost))
            except Exception:  # noqa: BLE001 - a usage footer must never break the run
                pass
        if wf_id is not None:
            tot = self._flow_usage.setdefault(wf_id, {"in": 0, "out": 0, "cache": 0, "cost": 0.0})
            tot["in"] += d_in; tot["out"] += d_out; tot["cache"] += d_cache; tot["cost"] += cost
            self._refresh_usage_total(wf_id)
    def _refresh_usage_total(self, only_wf: str = None) -> None:
        """Update the bottom conversation total to the CURRENT flow's running
        usage (skip if the event is for a different, background flow)."""
        lbl = getattr(self, "_usage_total_lbl", None)
        if lbl is None:
            return
        wf = getattr(self, "_wf", None)
        wf_id = wf.id if wf is not None else None
        if only_wf is not None and only_wf != wf_id:
            return
        tot = self._flow_usage.get(wf_id) if wf_id else None
        if not tot or not (tot["in"] or tot["out"]):
            lbl.setText("")
            return
        lbl.setText(self._fmt_usage(int(tot["in"]), int(tot["out"]),
                                    int(tot["cache"]), float(tot["cost"])))
    def _append_diff(self, title: str, diff: str, log: "ChatView" = None) -> None:
        """Render a before/after diff as a collapsible colored diff bubble."""
        log = log or self.chat_log
        log.add_diff(f"▤ {title}", diff)
        log.scroll_to_bottom()
    def _append_plan(self, steps, log: "ChatView" = None) -> None:
        """Show the plan INLINE in the conversation as an expandable block; update
        the same (per-flow) bubble in place so steps tick off (✓) as they complete."""
        log = log or self.chat_log
        from ...ui.co4e_tab import _fmt_plan
        body = _fmt_plan(steps)
        if not body:
            return
        if getattr(log, "_co4e_plan_bubble", None) is None:
            log._co4e_plan_bubble = log.add_plan(body)
        else:
            log._co4e_plan_bubble.set_plain(body)
        log.scroll_to_bottom()
