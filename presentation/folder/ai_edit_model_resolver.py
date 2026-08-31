"""AiEditModelResolver — model picker + Auto Model Routing + image-model
discovery for the AI-Edit panel (R08-T12, extracted from
``ui/folder_tab.py::FolderTab``, lines 802-1036/911-961 of the original
1587-line file: ``refresh_ai_models``, ``_scan_all_image_models``,
``_ai_provider``, ``_ai_apply_routing``, ``_confirm_routing_switch``,
``_ai_image_model``, ``_maybe_suggest_image_model``,
``_suggest_cross_provider_image``).

A plain (non-Qt-widget) helper composed BY
``ai_file_editor_dialog.py::AiFileEditorDialog`` — this is genuinely a
distinct concern (which provider/model answers THIS run) from the panel's
send/plan/edit orchestration, and splitting it out is also what keeps
``ai_file_editor_dialog.py`` under the 400-line cap.
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

from cowork_local.core.worker import AgentWorker
from cowork_local.i18n import tr


class AiEditModelResolver:
    """Owns the AI-edit model combo's contents and every "which provider/
    model should THIS run use" decision — independent of the Cowork/Settings
    agent, exactly like the original panel's own picker was.

    Args:
        ctx: ``AppContext``.
        model_combo: the ``QComboBox`` populated by :meth:`refresh`.
        on_status: ``(text) -> None`` — posts a status line into the AI
            chat (production passes ``ai_chat.add_status``).
        confirm_switch: ``(self, decision, timeout) -> bool`` — the Qt
            confirm dialog for Manual routing mode (kept as a callback so
            this class never imports a dialog itself).
    """

    def __init__(self, ctx, model_combo, on_status, confirm_switch) -> None:
        """Bộ chọn model của panel AI-Edit.

        ``on_status`` và ``confirm_switch`` được tiêm vào để lớp này không tự mở hộp
        thoại — nhờ vậy test chạy được nó mà không cần giao diện.
        """
        self.ctx = ctx
        self._combo = model_combo
        self._on_status = on_status
        self._confirm_switch = confirm_switch
        self._models: List[str] = []
        self._models_provider = ""
        self._all_image_models: List[Tuple[str, str]] = []   # [(provider_key, model)]
        self._img_scan_worker = None
        self._pending_img_suggest = False
        self._routed_provider: Optional[str] = None
        self._routed_model: Optional[str] = None

    @property
    def models(self) -> List[str]:
        """Danh sách model đã nạp cho provider hiện tại."""
        return self._models

    @property
    def models_provider(self) -> str:
        """Provider mà danh sách model đang thuộc về; '' nếu chưa nạp lần nào."""
        return self._models_provider

    @property
    def routed_provider(self) -> Optional[str]:
        """The provider :meth:`apply_routing` switched to for the current
        run, or ``None`` when it didn't switch (routing off/declined)."""
        return self._routed_provider

    @property
    def routed_model(self) -> Optional[str]:
        """Model do định tuyến tự động chọn cho lượt này; ``None`` nếu dùng model người dùng chọn."""
        return self._routed_model

    def should_refresh(self) -> bool:
        """True on first open, or when the active provider changed since
        the model list was last loaded — a stale list would resolve a pick
        to the wrong/default model at the new endpoint."""
        return self._combo.count() <= 1 or self._models_provider != self.ctx.config.active_provider

    def refresh(self) -> None:
        """Fetch the active provider's model list (background) into the
        picker. Also proactively scans ALL providers for image-capable
        models so a suggestion is ready the moment one is needed."""
        name = self.ctx.config.active_provider
        setting_model = self.ctx.config.provider_conf(name).get("model", "")

        def job(worker):
            """Chạy nền: hỏi provider danh sách model, lỗi thì trả về list rỗng."""
            prov = self.ctx.build_provider_for(name)
            try:
                models = list(getattr(prov, "list_models", lambda: [])() or [])
            except Exception:  # noqa: BLE001
                models = []
            return {"models": models}

        def done(res):
            """Đổ danh sách vào ô chọn, giữ nguyên model đang chọn.

            Luôn đưa model cấu hình trong Settings lên đầu, kể cả khi provider không
            liệt kê được — để ô chọn không bao giờ chỉ có mỗi "(tự động)".
            """
            fetched = list(res.get("models", []))
            # Always offer the Settings-configured model as an explicit
            # choice, even when the provider can't list models.
            self._models = list(dict.fromkeys(
                ([setting_model] if setting_model else []) + [m for m in fetched if m]))
            self._models_provider = name
            cur = self._combo.currentData()
            self._combo.blockSignals(True)
            self._combo.clear()
            self._combo.addItem(tr("folder.ai_model_auto"), None)
            for m in self._models:
                self._combo.addItem(m, m)
            idx = self._combo.findData(cur)
            self._combo.setCurrentIndex(idx if idx >= 0 else 0)
            self._combo.blockSignals(False)

        w = AgentWorker(job)
        w.finished_ok.connect(done)
        self._models_worker = w
        w.start()
        self._scan_all_image_models()

    def _scan_all_image_models(self, then_suggest: bool = False) -> None:
        """Dò khắp mọi provider đã cấu hình xem cái nào có model sinh ảnh.

        Chạy sẵn ở nền để lúc cần gợi ý là có ngay. Đang dò dở mà bị gọi lại thì
        chỉ ghi nhận yêu cầu gợi ý, không dò chồng lên nhau.
        """
        if self._img_scan_worker is not None:
            if then_suggest:
                self._pending_img_suggest = True
            return
        providers = dict(self.ctx.config.data.get("providers", {}))
        candidates = [k for k, c in providers.items()
                      if (c.get("base_url") or c.get("api_key"))]

        def job(worker):
            """Chạy nền: duyệt từng provider, lọc ra model sinh ảnh được."""
            from cowork_local.core import image_gen
            found = []
            for key in candidates:
                try:
                    prov = self.ctx.build_provider_for(key)
                    models = list(getattr(prov, "list_models", lambda: [])() or [])
                except Exception:  # noqa: BLE001 - a broken provider must not block the scan
                    models = []
                for m in models:
                    if image_gen.looks_like_image_model(m):
                        found.append((key, m))
            return {"found": found}

        def done(res):
            """Ghi lại kết quả dò; có yêu cầu gợi ý đang chờ thì trả lời luôn."""
            self._img_scan_worker = None
            self._all_image_models = list(res.get("found", []))
            if self._pending_img_suggest:
                self._pending_img_suggest = False
                self._suggest_cross_provider_image()

        w = AgentWorker(job)
        w.finished_ok.connect(done)
        w.failed.connect(self._on_image_scan_failed)
        self._img_scan_worker = w
        if then_suggest:
            self._pending_img_suggest = True
        w.start()

    def _on_image_scan_failed(self, _err) -> None:
        """Dò model ảnh thất bại: chỉ xoá cờ đang chạy, không báo lỗi ra màn hình —
        đây là việc chạy ngầm mà người dùng không yêu cầu.
        """
        self._img_scan_worker = None

    def provider(self) -> Any:
        """Build a provider using the model chosen in the picker ('(auto)'
        -> the active provider's default), or an Auto/Manual routing
        override set by :meth:`apply_routing` for the current run."""
        if self._routed_provider or self._routed_model:
            provider = self._routed_provider or self.ctx.config.active_provider
            return self.ctx.build_provider_for(provider, self._routed_model or None)
        model = self._combo.currentData()
        return self.ctx.build_provider_for(self.ctx.config.active_provider, model or None)

    def apply_routing(self, instruction: str) -> None:
        """Auto Model Routing for the AI-Edit surface (always a CODING
        task). Sets the routing override :meth:`provider` honours.

        Never raises — a routing failure must never block an edit."""
        self._routed_provider = None
        self._routed_model = None
        try:
            from cowork_local.application.model_routing import (
                RoutingRequest,
                build_routing_application_service,
            )
            from cowork_local.core.routing.models import TaskType

            cur_provider = self.ctx.config.active_provider
            picked = self._combo.currentData()
            cur_model = picked or self.ctx.config.provider_conf(cur_provider).get("model", "")
            outcome = build_routing_application_service(self.ctx).resolve(
                RoutingRequest(
                    surface="ai_edit",
                    prompt=instruction,
                    current_provider=cur_provider,
                    current_model=cur_model,
                    # An edit instruction is never a QA question, so the task
                    # type is pinned rather than classified from the prompt.
                    task_type=TaskType.CODING,
                ),
                confirm=self._confirm_switch,
            )
            if not outcome.switched:
                return
            self._routed_provider = outcome.provider
            self._routed_model = outcome.model
            self._on_status(tr(
                "routing.switched_notice",
                model=outcome.model, task=outcome.task_type,
                gain=f"{outcome.score_gain:.2f}"))
        except Exception:  # noqa: BLE001 — routing must never block an edit
            self._routed_provider = None
            self._routed_model = None

    _IMAGE_WORDS = ("image", "picture", "photo", "illustration", "icon", "logo", "diagram",
                    "ảnh", "hình", "minh họa", "biểu tượng", "画像", "イラスト")

    def maybe_suggest_image_model(self, instruction: str) -> None:
        """If the request looks image-related, suggest a suitable image
        model BEFORE running — active provider first, then ALL providers."""
        from cowork_local.core import image_gen
        low = (instruction or "").lower()
        if not any(w in low for w in self._IMAGE_WORDS):
            return
        picked = self._combo.currentData()
        if picked and image_gen.looks_like_image_model(picked):
            return
        local = image_gen.suggest_image_model(self._models)
        if local:
            self._on_status(tr("folder.ai_image_suggest", model=local))
            return
        if self._all_image_models:
            self._suggest_cross_provider_image()
        elif self._img_scan_worker is not None:
            self._pending_img_suggest = True
        else:
            self._scan_all_image_models(then_suggest=True)

    def _suggest_cross_provider_image(self) -> None:
        """Gợi ý một model sinh ảnh, kể cả khi nó thuộc provider KHÁC provider đang chọn.

        Đây là chỗ duy nhất trong màn Thư mục biết tới nhiều provider cùng lúc.
        """
        from cowork_local.config import PROVIDER_LABELS
        if not self._all_image_models:
            picked = self._combo.currentData()
            if picked:
                self._on_status(tr("folder.ai_image_use_selected", model=picked))
            else:
                self._on_status(tr("folder.ai_image_none"))
            return
        seen, lines = set(), []
        for key, model in self._all_image_models:
            tag = (key, model)
            if tag in seen:
                continue
            seen.add(tag)
            lines.append(f"• {model}  ({PROVIDER_LABELS.get(key, key)})")
            if len(lines) >= 5:
                break
        self._on_status(tr("folder.ai_image_suggest_all") + "\n" + "\n".join(lines))

    def image_model(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Resolve ``(model, base_url, api_key)`` for image generation,
        searching ALL providers — see the module docstring for priority
        order (picked model if image-capable -> active provider's image
        model -> any other provider's -> fall back to the picked model)."""
        from cowork_local.core import image_gen
        picked = self._combo.currentData()
        if picked and image_gen.looks_like_image_model(picked):
            return picked, None, None
        local = image_gen.suggest_image_model(self._models)
        if local:
            return local, None, None
        for key, model in self._all_image_models:
            conf = self.ctx.config.provider_conf(key)
            return model, (conf.get("base_url") or None), (conf.get("api_key") or None)
        return (picked or None), None, None


__all__ = ["AiEditModelResolver"]
