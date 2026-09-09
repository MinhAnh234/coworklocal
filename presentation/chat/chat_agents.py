"""Chọn agent, skill và định tuyến model cho khung chat — R08-T06.

``_apply_routing`` quyết định lượt này chạy bằng model nào: người dùng
chọn tay, hay để bộ định tuyến tự chọn theo chính sách.

``_note_agent_switch`` ghi lại việc đổi agent giữa chừng vào chính mạch
hội thoại — không ghi thì đọc lại transcript sẽ thấy giọng đổi đột ngột
mà không hiểu vì sao.
"""
from __future__ import annotations

from typing import Any, Dict
from PySide6.QtCore import Qt, Signal
from ...core.worker import AgentWorker
from ...i18n import tr


class ChatAgentsMixin:
    """Trộn vào ChatPanel."""

    def _agent_signature(self) -> str:
        """Identifies WHAT will run the next turn (admin agent id, or plain
        provider:model) — comparing this across turns is how a genuine
        mid-conversation switch is detected."""
        agent = getattr(self, "_admin_agent", None)
        if agent is not None:
            return f"{self._ADMIN_AGENT_PREFIX}{agent.agent_id}"
        return f"{self.ctx.config.active_provider}:{self._model}"

    def _current_agent_label(self) -> str:
        """Human-friendly name of what will run the next turn — for the visible
        'auto-switched model' notice in the transcript."""
        agent = getattr(self, "_admin_agent", None)
        if agent is not None:
            return agent.name
        return self._model or tr("chat.provider_default_short")

    def _on_agent_changed(self, _i: int) -> None:
        """Đổi agent trong bộ chọn: agent quản trị thì lấy cả provider/model riêng của nó."""
        data = self.agent_combo.currentData() or ""
        if isinstance(data, str) and data.startswith(self._ADMIN_AGENT_PREFIX):
            # An Admin-defined agent preset (Monitoring → Agents Admin): runs
            # on its pinned model (or the Settings default when unpinned) and
            # injects its instructions into every turn of this tab.
            from ...core import admin_agents

            agent_id = data[len(self._ADMIN_AGENT_PREFIX):]
            self._admin_agent = admin_agents.load_agent(
                agent_id, admin_agents.agents_admin_dir(self.ctx.config.shared_dir))
            self._agent_user_override = True
            self._agent_provider = self.ctx.config.active_provider
            self._model = (self._admin_agent.model if self._admin_agent else "") or ""
            if self._admin_agent is not None:
                self.status_message.emit(f"{self.session_name} agent: {self._admin_agent.name}")
            self._note_agent_switch()
            return
        self._admin_agent = None
        new = data or ""   # "" → provider default
        if new != self._model:
            # A deliberate pick by the user — remember it until the provider changes.
            self._agent_user_override = True
            self._agent_provider = self.ctx.config.active_provider
        self._model = new
        if self._model:
            self.status_message.emit(f"{self.session_name} agent: {self._model}")
        self._note_agent_switch()

    def _note_agent_switch(self) -> None:
        """Flag a pending review note for the NEXT turn when the selection
        genuinely changed mid-conversation (there's already history AND this
        isn't just the initial default being applied)."""
        sig = self._agent_signature()
        last = getattr(self, "_last_turn_agent_signature", None)
        if last is not None and sig != last and self.messages:
            self._pending_agent_switch_review = True

    def admin_agent_prompt(self) -> str:
        """The selected admin agent's instructions ('' when a plain model is
        selected) — appended to the project context of every turn."""
        agent = getattr(self, "_admin_agent", None)
        return agent.effective_prompt() if agent is not None else ""

    def refresh_agents(self) -> None:
        """Fetch the model list from the active provider (in the background) and
        fill the per-tab Agent combo — called at start and on provider change.

        The default follows Settings; see state.resolve_agent_default."""
        from ...state import resolve_agent_default

        name = self.ctx.config.active_provider
        setting_model = self.ctx.config.provider_conf(name).get("model", "")
        keep, self._agent_user_override = resolve_agent_default(
            name, setting_model, self._model, self._agent_provider, self._agent_user_override)
        self._model = keep
        self._agent_provider = name

        def job(worker: AgentWorker):
            """Chạy nền: hỏi provider danh sách model để đổ vào bộ chọn agent."""
            error = ""
            try:
                prov = self.ctx.build_provider_for(name)
                models = list(getattr(prov, "list_models", lambda: [])() or [])
                if not models:
                    error = getattr(prov, "last_error", "")
            except Exception as exc:  # noqa: BLE001 - never break the UI over a model list
                models, error = [], str(exc)
            return {"models": models, "keep": keep, "error": error}

        def done(result) -> None:
            """Đổ danh sách vào bộ chọn, giữ nguyên lựa chọn trước đó nếu còn."""
            self._populate_agents(result.get("models", []), result.get("keep", ""))
            # Surface the REAL reason models didn't load (network/auth/config)
            # instead of silently falling back to "(provider default)".
            err = result.get("error", "")
            if err:
                self.status_message.emit(tr("chatpanel.agent_list_error", err=err))

        w = AgentWorker(job)
        w.finished_ok.connect(done)
        self._agent_worker = w
        w.start()

    def _populate_agents(self, models, keep: str) -> None:
        """Đổ danh sách vào bộ chọn Agent.

        Bộ chọn này thực chất là bộ chọn MODEL: danh sách model của provider đang
        dùng, cộng thêm các agent quản trị có provider/model riêng.
        """
        self.agent_combo.blockSignals(True)
        self.agent_combo.clear()
        # The Agent picker is a MODEL picker — the raw model list of the active
        # provider. Admin-defined agents (Monitoring → Agents Admin) are NOT
        # listed here: they are system-management presets, not a model/agent to
        # pick for a Cowork conversation. To apply a work agent's persona, use
        # the /agent command (built-in + custom Flow agents).
        items = list(dict.fromkeys([m for m in models if m]))   # dedupe, keep order
        if keep and keep not in items:
            items.insert(0, keep)
        for m in items:
            self.agent_combo.addItem(m, m)
        if not items and self.agent_combo.count() == 0:
            # No models found and none configured — placeholder with data=None so
            # we fall back to the provider's default model (never a fake name).
            self.agent_combo.addItem(tr("chat.provider_default_item"), None)
        keep_data = (f"{self._ADMIN_AGENT_PREFIX}{self._admin_agent.agent_id}"
                     if getattr(self, "_admin_agent", None) is not None else keep)
        idx = self.agent_combo.findData(keep_data) if keep_data else -1
        if idx >= 0:
            self.agent_combo.setCurrentIndex(idx)
        self.agent_combo.blockSignals(False)
        data = self.agent_combo.currentData() or ""
        if not (isinstance(data, str) and data.startswith(self._ADMIN_AGENT_PREFIX)):
            self._model = data or ""

    def build_provider(self):
        """Provider for THIS tab: the selected admin agent's pinned
        provider/model when one is selected, else the tab's selected model
        (or the provider's configured default when none is chosen)."""
        agent = getattr(self, "_admin_agent", None)
        if agent is not None:
            from ...core.admin_agents import build_agent_provider

            return build_agent_provider(self.ctx, agent)
        # An Auto/Manual routing override (set by _apply_routing for this turn)
        # wins over the tab's own provider/model selection.
        provider = self._routed_provider or self.ctx.config.active_provider
        model = self._routed_model or self._model or None
        return self.ctx.build_provider_for(provider, model)

    def _apply_routing(self, text: str, turn: Dict[str, Any]) -> None:
        """Auto Model Routing hook — run once per outgoing message.

        Since R03-T04 the Off/Auto/Manual/Fallback rules live in
        ``application/model_routing/routing_application_service.py``; the copy
        that used to sit here (and again in Co4E and AI-Edit) is gone. What
        remains is the widget's own job: snapshot the tab's provider/model into
        a request, host the Manual-mode modal, and render the outcome by setting
        ``self._routed_provider``/``self._routed_model`` for THIS turn (honoured
        by :meth:`build_provider`) plus a status bubble.

        Never raises — a routing failure must never block sending a message; it
        just falls back to the tab's own model.
        """
        # Recompute fresh each message; clear any previous turn's override.
        self._routed_provider = None
        self._routed_model = None
        # An explicitly-pinned Admin agent takes precedence over routing.
        if getattr(self, "_admin_agent", None) is not None:
            return
        try:
            from ...application.model_routing import (
                RoutingRequest,
                build_routing_application_service,
            )
            from ...ui.routing_toggle import confirm_switch

            # The model the tab WOULD use without routing — the picker's choice,
            # or the provider's configured default when nothing is picked.
            cur_provider = self.ctx.config.active_provider
            cur_model = self._model or self.ctx.config.provider_conf(cur_provider).get("model", "")
            outcome = build_routing_application_service(self.ctx).resolve(
                RoutingRequest(
                    surface=self.kind,          # per-workspace mode key ("cowork"/…)
                    prompt=text,
                    current_provider=cur_provider,
                    current_model=cur_model,
                ),
                # Manual mode only: the modal stays in the presentation layer so
                # the application service never imports Qt.
                confirm=lambda decision, timeout: confirm_switch(self, decision, timeout),
            )
            if not outcome.switched:
                return  # off / nothing better / declined → keep the tab's model
            self._routed_provider = outcome.provider
            self._routed_model = outcome.model
            notice = self.chat_view.add_status(tr(
                "routing.switched_notice",
                model=outcome.model, task=outcome.task_type,
                gain=f"{outcome.score_gain:.2f}"))
            turn["bubbles"].append(notice)
        except Exception:  # noqa: BLE001 — routing must never block a chat turn
            self._routed_provider = None
            self._routed_model = None

    def _apply_skill_command(self, text: str):
        """Parse a leading ``/skill`` command typed in the chat box.

        Returns ``(prefix, request, info)`` — see ``core.skills.parse_skill_command``."""
        try:
            from ...core.skills import parse_skill_command
            return parse_skill_command(text)
        except Exception:
            return "", text, "Could not read skills from the Skills manager."

    def _apply_agent_command(self, text: str):
        """Parse a ``/agent`` command typed in the chat box (Cowork parity with
        Co4E): apply a named agent PERSONA to the turn. Returns
        ``(prefix, request, info)`` — see ``core.agent_command.parse_agent_command``."""
        try:
            from ...core.agent_command import parse_agent_command
            return parse_agent_command(text, self.ctx.config.shared_dir)
        except Exception:  # noqa: BLE001
            return "", text, "Could not read the agent catalog."

    def _open_skills_manager(self) -> None:
        """Open the Skills manager (add / edit / delete / enable skills)."""
        from ...ui.skills_dialog import SkillsDialog

        SkillsDialog(self, self.ctx).exec()
        self._skills_changed()
        self.status_message.emit(tr("chatpanel.skills_updated"))

    def _skills_changed(self) -> None:
        """Hook after skills were edited (Code tab refreshes its Skills button)."""
