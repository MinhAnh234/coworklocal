"""AiEditPipeline — the plan-then-edit-then-apply state machine behind the
AI-Edit panel (R08-T12, extracted from ``ui/folder_tab.py::FolderTab``,
lines 1068-1097/1119-1146/1147-1467 of the original 1587-line file:
``_ai_start`` through ``_ai_failed``, minus the queue/busy-badge bookkeeping
which stays on ``ai_file_editor_dialog.py::AiFileEditorDialog`` — see that
module's docstring for the split rationale).

A plain (non-Qt-widget) helper composed BY ``AiFileEditorDialog`` — same
composition-to-respect-the-400-line-cap pattern as
``office_document_renderer.py``. Talks to the file only through
``document_preview_manager.py``'s public API (``ensure_editable_for_ai``,
``write_content``, ``create_new_file``) — it never touches disk itself.
"""
from __future__ import annotations

import difflib
import os
from pathlib import Path
from typing import Optional

from cowork_local.application.workspaces.ai_edit_output import parse_ai_output
from cowork_local.core.worker import AgentWorker
from cowork_local.i18n import tr
from cowork_local.theme import current_palette


class AiEditPipeline:
    """Runs one instruction through PLAN -> EDIT -> (review) -> APPLY/DISCARD.

    Args:
        owner: the ``AiFileEditorDialog`` — supplies ``ai_chat``, ``preview``
            (``DocumentPreviewManager``), ``resolver``
            (``AiEditModelResolver``), ``ctx``, ``cowork_context()``, and is
            told about status changes via ``on_busy_changed``/``on_flag_done``
            so the panel's queue/badge bookkeeping stays in one place.
    """

    def __init__(self, owner) -> None:
        """Vòng chạy một lượt sửa tệp bằng AI.

        ``pending`` giữ nội dung model đề xuất cho tới khi người dùng đồng ý: không
        bao giờ ghi đè tệp trước khi có xác nhận.
        """
        self._owner = owner
        self.worker: Optional[AgentWorker] = None
        self.pending: Optional[dict] = None   # proposed content awaiting confirmation
        self._ctx: dict = {}
        self._prompt_usage: dict = {"in": 0, "out": 0, "cache": 0, "cost": 0.0}
        self._running_file = ""

    def start(self, instruction: str) -> None:
        """Begin processing one instruction. Assumes the pipeline is idle
        (the panel's queue calls this when the previous run finishes)."""
        o = self._owner
        preview = o.preview
        editable = preview.stack.currentWidget() is preview.editor
        if not editable:
            editable = preview.ensure_editable_for_ai()
        o.resolver.maybe_suggest_image_model(instruction)
        o.resolver.apply_routing(instruction)   # may switch to the best coding model
        has_file = editable and bool(preview.current_file)
        self._running_file = Path(preview.current_file).name if has_file else tr("folder.ai_new_file")
        o.set_busy(True)
        o.status_message.emit(tr("folder.ai_running", name=self._running_file))
        # Two phases so the PLAN is shown INLINE *before* the edit runs.
        self._ctx = {
            "filename": Path(preview.current_file).name if has_file else "",
            "content": preview.editor.toPlainText() if has_file else "",
            "convo": o.cowork_context(),
            "instruction": instruction,
            "provider": o.resolver.provider(),
            "plan": "",
            "edit_kind": preview.edit_kind,
        }
        self._prompt_usage = {"in": 0, "out": 0, "cache": 0, "cost": 0.0}
        self._run_plan()

    # ---- usage accounting (like Cowork's per-message footer) --------------- #
    def _add_usage(self, usage) -> None:
        """Cộng dồn token của một lượt gọi vào tổng của cả phiên sửa file."""
        if not isinstance(usage, dict):
            return
        tot = self._prompt_usage
        tot["in"] += int(usage.get("in", 0) or 0)
        tot["out"] += int(usage.get("out", 0) or 0)
        tot["cache"] += int(usage.get("cache", 0) or 0)
        tot["cost"] += float(usage.get("cost_usd", 0.0) or 0.0)

    def _show_usage(self, bubble) -> None:
        """Gắn dòng token/chi phí dưới bong bóng trả lời; chưa dùng token nào thì bỏ qua."""
        tot = self._prompt_usage
        if bubble is None or not (tot["in"] or tot["out"]):
            return
        from cowork_local.core import model_pricing as mp, usage_tracker as ut
        pricing = {**ut.DEFAULT_PRICING, **(self._owner.ctx.config.data.get("usage") or {})}
        line = (f"↓{mp.format_tokens(int(tot['in']))} ↑{mp.format_tokens(int(tot['out']))} "
                f"▤{mp.format_tokens(int(tot['in'] + tot['out'] + tot['cache']))} "
                f"{ut.format_cost(tot['cost'], pricing)}")
        try:
            bubble.add_usage(line)
        except Exception:  # noqa: BLE001 - a usage footer must never break the edit
            pass

    # ---- phase 1: plan ------------------------------------------------------- #
    def _run_plan(self) -> None:
        """Bước 1 — nhờ model lập kế hoạch sửa trước khi động vào nội dung."""
        o = self._owner
        c = self._ctx
        plan_bubble = o.ai_chat.add_plan(tr("folder.ai_planning"))
        o.ai_chat.scroll_to_bottom()

        def job(worker):
            """Chạy nền: gọi model sinh kế hoạch và đo token đã dùng."""
            from cowork_local.core import usage_tracker as ut
            from cowork_local.core.co4e_runner import _usage_delta
            provider = c["provider"]
            messages = [{"role": "system", "content":
                         "You are an AI file editor. Give a SHORT numbered plan (2-4 steps) for "
                         "the requested change. Plan ONLY — do NOT output any code."}]
            if c["convo"]:
                messages.append({"role": "system",
                                 "content": "Context from the user's Cowork conversation:\n" + c["convo"]})
            messages.append({"role": "user", "content":
                             f"File: {c['filename']}\n\nCurrent content:\n```\n{c['content']}\n```\n\n"
                             f"Request: {c['instruction']}"})
            ut.set_context("folder", c.get("filename") or "AI edit")
            ut.begin_accumulation(); base = ut.accumulated()
            try:
                r = provider.chat(messages, tools=None, cancel=worker.is_cancelled)
                txt = r.get("content", "") if isinstance(r, dict) else str(r)
                usage = _usage_delta(base, o.ctx.config)
            finally:
                ut.end_accumulation()
            return {"plan": provider.strip_think(txt) or "", "usage": usage}

        worker = AgentWorker(job)
        worker.finished_ok.connect(lambda res, b=plan_bubble: self._plan_done(res, b))
        worker.failed.connect(lambda err, b=plan_bubble: self._failed(err, b))
        self.worker = worker
        worker.start()

    def _plan_done(self, result, plan_bubble) -> None:
        """Có kế hoạch: hiện ra rồi chuyển sang bước sửa thật."""
        self._add_usage((result or {}).get("usage"))
        plan = ((result or {}).get("plan") or "").strip()
        self._ctx["plan"] = plan
        plan_bubble.set_plain(plan or tr("folder.ai_empty"))
        self._owner.ai_chat.scroll_to_bottom()
        self._run_edit()

    # ---- phase 2: execute (edit the file) ------------------------------------ #
    def _run_edit(self) -> None:
        """Bước 2 — sinh nội dung mới, phát dần vào bong bóng trả lời."""
        o = self._owner
        c = self._ctx
        bubble = o.ai_chat.add_assistant(tr("folder.ai_edit"))
        o.ai_chat.scroll_to_bottom()

        pptx_note = ("\nThis is a PPTX shown as marker blocks '### Slide N / Box M', where N is the "
                     "1-based SLIDE NUMBER and M the box on that slide. When the user refers to a "
                     "slide by number (e.g. 'edit slide 3'), change ONLY the blocks under '### Slide "
                     "3' and leave every other slide's block exactly as-is. Each block has fields "
                     "type/pos/size/font/text (and image for pictures). To change TEXT COLOUR or "
                     "FONT edit the `font:` line — e.g. `font: name=Arial size=28 bold=1 "
                     "color=FF0000`. Keep all block markers and structure.") if c["edit_kind"] == "pptx" else ""

        _pptx_words = ("pptx", "powerpoint", "slide", "presentation", "deck",
                       "スライド", "プレゼン", "trình chiếu", "trinh chieu", "bài thuyết trình")
        wants_new_pptx = (c["edit_kind"] != "pptx"
                          and any(w in c["instruction"].lower() for w in _pptx_words))
        new_pptx_note = ("\nTo CREATE a PowerPoint, name it `FILE: <name>.pptx` and output the slides "
                         "as marker blocks — one block per shape:\n"
                         "### Slide 1 / Box 1\ntype: text\npos: 0.5, 0.4\nsize: 9.0, 1.2\n"
                         "font: name=Calibri size=32 bold=1 color=1F3864\ntext:\nTitle here\n\n"
                         "### Slide 1 / Box 2\ntype: text\npos: 0.5, 1.8\nsize: 9.0, 4.5\n"
                         "text:\nBullet one\nBullet two\n\n"
                         "Increment the Slide number for each new slide; pos/size are in inches; "
                         "font color is RRGGBB hex.") if wants_new_pptx else ""

        imggen_note = ""
        try:
            from cowork_local.core import image_gen
            if image_gen.is_configured(o.ctx.config):
                imggen_note = ("\nYou can also GENERATE an illustration image: add a line "
                               "`IMAGE_GEN: <describe the image> => <relative/path.png>`. Use a "
                               "generated image e.g. as a new picture, or (for pptx) set a picture "
                               "box's `image:` field to that same path to insert it.")
        except Exception:  # noqa: BLE001
            pass

        def job(worker):
            """Chạy nền: gọi model sinh nội dung sửa, kèm ngữ cảnh tệp đang mở."""
            provider = c["provider"]
            open_note = (f"the currently-open file '{c['filename']}'" if c["filename"]
                         else "no file is open")
            messages = [{"role": "system", "content":
                         "You are an AI file editor inside an app. Following the plan, output the "
                         "COMPLETE file content in ONE fenced code block (```), and nothing after "
                         "it. Preserve everything you were not asked to change.\n"
                         "If the request is to CREATE A NEW file (or a different file than the one "
                         "open), put a line `FILE: <relative/path/name.ext>` (relative to the "
                         "current folder) immediately before the code block. Omit FILE to edit the "
                         f"open file. Right now, {open_note}." + pptx_note + new_pptx_note + imggen_note}]
            if c["convo"]:
                messages.append({"role": "system",
                                 "content": "Context from the user's Cowork conversation:\n" + c["convo"]})
            if c["plan"]:
                messages.append({"role": "system", "content": "Plan to follow:\n" + c["plan"]})
            cur = (f"File: {c['filename']}\n\nCurrent content:\n```\n{c['content']}\n```\n\n"
                   if c["filename"] else "No file is currently open.\n\n")
            messages.append({"role": "user", "content": cur + f"Request: {c['instruction']}"})

            def on_text(piece: str) -> None:
                """Đẩy từng mẩu nội dung ra ngoài để giao diện vẽ dần."""
                worker.emit_event({"type": "text", "delta": piece})

            from cowork_local.core import usage_tracker as ut
            from cowork_local.core.co4e_runner import _usage_delta
            ut.set_context("folder", c.get("filename") or "AI edit")
            ut.begin_accumulation(); base = ut.accumulated()
            try:
                r = provider.chat(messages, tools=None, on_text=on_text, cancel=worker.is_cancelled)
                txt = r.get("content", "") if isinstance(r, dict) else str(r)
                usage = _usage_delta(base, o.ctx.config)
            finally:
                ut.end_accumulation()
            return {"text": provider.strip_think(txt) or "", "usage": usage}

        worker = AgentWorker(job)
        worker.event.connect(lambda ev, b=bubble: self._stream(ev, b))
        worker.finished_ok.connect(lambda res, b=bubble: self._done(res, b))
        worker.failed.connect(lambda err, b=bubble: self._failed(err, b))
        self.worker = worker
        worker.start()

    def _stream(self, ev, bubble) -> None:
        """Vẽ từng mẩu nội dung đang phát dần và cuộn theo."""
        if isinstance(ev, dict) and ev.get("type") == "text":
            bubble.append_delta(ev.get("delta", ""))
            self._owner.ai_chat.scroll_to_bottom()

    def _done(self, result, bubble) -> None:
        """Sinh xong: tách phần mã khỏi phần giải thích và dựng bản xem trước.

        KHÔNG bao giờ ghi thẳng ra tệp ở đây — chỉ ``_finalize_apply`` mới chạm đĩa,
        và chỉ sau khi người dùng bấm Áp dụng.
        """
        o = self._owner
        self.worker = None
        o.set_busy(False)
        self._add_usage((result or {}).get("usage"))
        self._show_usage(bubble)
        text = ((result or {}).get("text") or "").strip()
        target, new_content, summary, image_gens = parse_ai_output(text)
        if new_content is None and not image_gens:
            bubble.set_markdown(text or tr("folder.ai_empty"))
            o.ai_chat.scroll_to_bottom()
            o.flag_done()
            return
        create = bool(target) and (not o.preview.current_file
                                   or Path(target).name != Path(o.preview.current_file).name)
        self.pending = {"content": new_content, "target": target if create else None,
                        "image_gens": image_gens}
        hint = tr("folder.ai_review_hint")
        bubble.set_markdown((summary + "\n\n" if summary else "") + "_" + hint + "_")
        if new_content is not None:
            old = "" if create else o.preview.editor.toPlainText()
            diff = "".join(difflib.unified_diff(
                old.splitlines(keepends=True), new_content.splitlines(keepends=True),
                fromfile=("(new file)" if create else "current"),
                tofile=(target if create else "proposed"))) or "(no textual difference)"
            title = tr("folder.ai_proposed_new", name=target) if create else tr("folder.ai_proposed")
            o.ai_chat.add_diff(title, diff)
        if image_gens:
            listing = "\n".join(f"• {p}  ({prompt[:60]})" for prompt, p in image_gens)
            o.ai_chat.add_status(tr("folder.ai_image_plan") + "\n" + listing)
        o.show_confirm_row(True)
        o.ai_chat.scroll_to_bottom()
        name = target if create else self._running_file
        o.status_message.emit(tr("folder.ai_proposed_status", name=name))
        o.set_review_status("● " + hint, current_palette().warning)

    # ---- apply / discard ------------------------------------------------------ #
    def apply(self) -> None:
        """Confirmed by the user. If the edit GENERATES images, ask the
        image gate then generate them (off-thread) before finalising."""
        if not self.pending:
            return
        p = self.pending
        self.pending = None
        self._owner.show_confirm_row(False)
        if p.get("image_gens"):
            from ...ui.dialog_buttons import confirm
            if not confirm(self._owner, tr("folder.ai_image_confirm_title"),
                           tr("folder.ai_image_confirm_gen")):
                self._owner.status_message.emit(tr("folder.ai_image_declined"))
                return
            self._generate_then_finalize(p)
            return
        self._finalize_apply(p)

    def _generate_then_finalize(self, p: dict) -> None:
        """Lượt sửa có yêu cầu sinh ảnh: tạo ảnh trước rồi mới ghi nội dung.

        Phải theo thứ tự đó vì nội dung có thể tham chiếu tới đường dẫn ảnh vừa tạo.
        """
        o = self._owner
        imgs = p.get("image_gens") or []
        root = os.path.normpath(o.preview.root)
        img_model, img_base, img_key = o.resolver.image_model()
        o.set_busy(True)
        o.status_message.emit(tr("folder.ai_generating"))

        def job(worker):
            """Chạy nền: sinh lần lượt từng ảnh được yêu cầu."""
            from cowork_local.core import image_gen
            results = []
            for prompt, rel in imgs:
                dest = rel if os.path.isabs(rel) else os.path.join(root, rel)
                dest = os.path.normpath(dest)
                if os.path.commonpath([dest, root]) != root:
                    results.append((rel, False, "path escapes the folder"))
                    continue
                try:
                    os.makedirs(os.path.dirname(dest) or root, exist_ok=True)
                except OSError as exc:
                    results.append((rel, False, str(exc)))
                    continue
                ok, msg = image_gen.generate_image(o.ctx.config, prompt, dest,
                                                   model=img_model, base_url=img_base, api_key=img_key)
                results.append((dest, ok, msg))
            return {"results": results}

        worker = AgentWorker(job)
        worker.finished_ok.connect(lambda res, pp=p: self._images_done(res, pp))
        worker.failed.connect(lambda err, pp=p: self._images_done({"results": [], "err": err}, pp))
        self.worker = worker
        worker.start()

    def _images_done(self, res: dict, p: dict) -> None:
        """Ảnh đã sinh xong: ghi nội dung ra đĩa."""
        o = self._owner
        self.worker = None
        o.set_busy(False)
        created = []
        for dest, ok, msg in res.get("results", []):
            if ok:
                created.append(dest)
                o.ai_chat.add_success("✓ " + tr("folder.ai_image_created", name=Path(dest).name))
            else:
                o.ai_chat.add_error(tr("folder.ai_image_failed", err=msg))
        self._finalize_apply(p, images_done=True)
        if p.get("content") is None and not p.get("target") and created:
            o.preview.open_file(created[0], reset_ai=False)

    def _finalize_apply(self, p: dict, images_done: bool = False) -> None:
        """Ghi nội dung đã được duyệt xuống đĩa và làm mới khung xem."""
        o = self._owner
        content = p.get("content")
        target = p.get("target")
        if content is None:
            o.ai_chat.scroll_to_bottom()
            o.flag_done()
            o.status_message.emit(tr("folder.ai_done", name=self._running_file))
            return
        if target:
            dest = o.preview.create_new_file(target, content)
            if dest is None:
                return
            o.ai_chat.add_success("✓ " + tr("folder.ai_created", name=Path(dest).name))
            o.status_message.emit(tr("folder.ai_created", name=Path(dest).name))
        else:
            o.preview.editor.setPlainText(content)     # live update in the editor/preview
            o.preview.write_content(content, skip_image_confirm=images_done)
            o.ai_chat.add_success("✓ " + tr("folder.ai_applied"))
            o.status_message.emit(tr("folder.ai_done", name=self._running_file))
        o.ai_chat.scroll_to_bottom()
        o.flag_done()

    def discard(self) -> None:
        """Bỏ bản đề xuất đang chờ, không chạm vào tệp."""
        o = self._owner
        self.pending = None
        o.show_confirm_row(False)
        o.ai_chat.add_status(tr("folder.ai_discarded"))
        o.ai_chat.scroll_to_bottom()
        o.set_review_status("", None)
        o.maybe_dequeue()   # discarding resolves the gate → run the next queued edit

    def _failed(self, err, bubble) -> None:
        """Lượt sửa lỗi: hiện lỗi trong bong bóng và mở khoá lại panel."""
        o = self._owner
        self.worker = None
        bubble.set_markdown(tr("folder.ai_error", err=err))
        o.set_busy(False)
        o.status_message.emit(tr("folder.ai_error", err=err))
        o.flag_done()


__all__ = ["AiEditPipeline"]
