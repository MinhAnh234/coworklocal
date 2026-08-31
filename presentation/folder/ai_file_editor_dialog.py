"""AiFileEditorDialog — the collapsible AI-edit panel of the Folder Explorer
(R08-T12, extracted from ``ui/folder_tab.py::FolderTab``, lines 701-800/
1039-1066/1099-1118/1468-1517 of the original 1587-line file:
``_build_ai_panel``, panel open/reset, the instruction queue, and the busy/
done status line).

Despite the name (matching ``docs/refactor/Feature_Architecture_Proposal.md``'s
R08-T12 file list), this is an inline collapsible ``QWidget`` panel, not a
modal ``QDialog`` — exactly like the original ``_ai_panel`` was.

Composes two helpers to stay under the 400-line cap:
``ai_edit_model_resolver.py::AiEditModelResolver`` (which provider/model
answers a run) and ``ai_edit_pipeline.py::AiEditPipeline`` (the actual
plan-then-edit-then-apply state machine). This class owns the widget itself,
the instruction queue, and the busy/done status line/badge — the parts that
needed to stay together because the queue decides when the pipeline's next
``start()`` call happens.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Signal

from cowork_local.i18n import on_language_changed, tr
from cowork_local.presentation.folder.ai_edit_model_resolver import AiEditModelResolver
from cowork_local.presentation.folder.ai_edit_pipeline import AiEditPipeline
from cowork_local.theme import current_palette
from cowork_local.ui.chat_view import ChatView


class AiFileEditorDialog(QWidget):
    """Collapsible panel: a Cowork-style inline chat timeline, this panel's
    OWN model picker + routing toggle, an instruction box, and an Apply/
    Discard confirmation bar for the proposed edit.

    Args:
        ctx: ``AppContext``.
        preview: ``document_preview_manager.py::DocumentPreviewManager`` —
            every read/write of the actual file content goes through it.
        cowork: the shared Cowork tab (optional) — its recent messages are
            included as background context for the edit.
    """

    status_message = Signal(str)
    badge_changed = Signal(str)   # "" | " ⏳" | " ✓" — the shell mirrors this onto its toggle button

    def __init__(self, ctx, preview, cowork=None, parent=None):
        """Hộp thoại sửa tệp bằng AI.

        ``resolver`` dựng sau, vì nó cần chính ô chọn model mà hàm này mới tạo.
        """
        super().__init__(parent)
        self.ctx = ctx
        self.preview = preview
        self._cowork = cowork
        self._ai_queue: List[str] = []
        self.pipeline = AiEditPipeline(self)
        self.resolver: Optional[AiEditModelResolver] = None   # built after ai_model_combo exists

        preview.ai_reset_requested.connect(self.reset_conversation)
        preview.status_message.connect(self.status_message.emit)

        v = QVBoxLayout(self)
        v.setContentsMargins(6, 0, 0, 0)
        v.setSpacing(4)
        title_row = QHBoxLayout()
        self._ai_title = QLabel(tr("folder.ai_edit"))
        self._ai_title.setStyleSheet("font-weight:600;")
        title_row.addWidget(self._ai_title)
        title_row.addStretch(1)
        self._ai_status = QLabel("")
        self._ai_status.setObjectName("hint")
        title_row.addWidget(self._ai_status)
        v.addLayout(title_row)
        self.ai_chat = ChatView()
        v.addWidget(self.ai_chat, 1)

        model_row = QHBoxLayout()
        self._ai_model_lbl = QLabel(tr("folder.ai_model_label"))
        self._ai_model_lbl.setObjectName("hint")
        model_row.addWidget(self._ai_model_lbl)
        self.ai_model_combo = QComboBox()
        self.ai_model_combo.addItem(tr("folder.ai_model_auto"), None)
        model_row.addWidget(self.ai_model_combo, 1)
        from cowork_local.ui.routing_toggle import RoutingToggle
        self.ai_routing_toggle = RoutingToggle(self.ctx, "ai_edit")
        model_row.addWidget(self.ai_routing_toggle)
        v.addLayout(model_row)
        self.resolver = AiEditModelResolver(
            ctx, self.ai_model_combo, self.ai_chat.add_status, self._confirm_routing_switch)

        row = QHBoxLayout()
        self.ai_input = QLineEdit()
        self.ai_input.setPlaceholderText(tr("folder.ai_placeholder"))
        self.ai_input.returnPressed.connect(self._ai_send)
        row.addWidget(self.ai_input, 1)
        self.ai_send_btn = QPushButton(tr("folder.ai_send"))
        self.ai_send_btn.setObjectName("primary")
        self.ai_send_btn.clicked.connect(self._ai_send)
        row.addWidget(self.ai_send_btn)
        v.addLayout(row)

        self._ai_confirm_row = QWidget()
        cf = QHBoxLayout(self._ai_confirm_row)
        cf.setContentsMargins(0, 0, 0, 0)
        cf.addStretch(1)
        self._ai_discard_btn = QPushButton(tr("folder.ai_discard"))
        self._ai_discard_btn.clicked.connect(self.pipeline.discard)
        cf.addWidget(self._ai_discard_btn)
        self._ai_apply_btn = QPushButton(tr("folder.ai_apply"))
        self._ai_apply_btn.setObjectName("primary")
        self._ai_apply_btn.clicked.connect(self.pipeline.apply)
        cf.addWidget(self._ai_apply_btn)
        self._ai_confirm_row.setVisible(False)
        v.addWidget(self._ai_confirm_row)

        on_language_changed(self.retranslate)
        self.retranslate()

    def retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn."""
        self._ai_title.setText(tr("folder.ai_edit"))
        self.ai_input.setPlaceholderText(tr("folder.ai_placeholder"))
        self.ai_send_btn.setText(tr("folder.ai_send"))
        self._ai_model_lbl.setText(tr("folder.ai_model_label"))
        if self.ai_model_combo.count() >= 1 and self.ai_model_combo.itemData(0) is None:
            self.ai_model_combo.setItemText(0, tr("folder.ai_model_auto"))
        self._ai_apply_btn.setText(tr("folder.ai_apply"))
        self._ai_discard_btn.setText(tr("folder.ai_discard"))

    # ---- called by the shell (header button, splitter owner) --------------- #
    def on_opened(self) -> None:
        """The shell's AI toggle button was just checked ON."""
        self.ai_input.setFocus()
        if self.resolver.should_refresh():
            self.resolver.refresh()
        if self.pipeline.worker is None:
            self.badge_changed.emit("")
            self._ai_status.setText("")

    def reset_conversation(self) -> None:
        """Clear the AI-edit chat so each file starts a clean conversation. A
        run in progress (editing the previous file) is left untouched — the
        reset applies the next time a file is opened while idle."""
        if self.pipeline.worker is not None:
            return
        self.ai_chat.clear()
        self.badge_changed.emit("")
        self.pipeline.pending = None
        self._ai_confirm_row.setVisible(False)
        self._ai_status.setText("")

    def cowork_context(self) -> str:
        """The whole Cowork conversation (recent turns) as background context."""
        cw = self._cowork
        msgs = getattr(cw, "messages", None) if cw is not None else None
        if not msgs:
            return ""
        lines = [f"{m['role']}: {str(m['content'])[:1000]}"
                 for m in msgs if m.get("role") in ("user", "assistant") and m.get("content")]
        return "\n".join(lines[-12:])

    # ---- send / queue -------------------------------------------------------- #
    def _ai_send(self) -> None:
        """Gửi một yêu cầu sửa; chưa chọn thư mục làm việc thì báo lỗi ngay."""
        if not self.preview.root:
            self.ai_chat.add_error(tr("folder.ai_no_file"))
            return
        instruction = self.ai_input.text().strip()
        if not instruction:
            return
        self.ai_input.clear()
        self.ai_chat.add_user(instruction)
        # QUEUE: while a run is active OR a proposal is awaiting Apply/Discard,
        # hold the new instruction and run it once the pipeline goes idle.
        if self.pipeline.worker is not None or self.pipeline.pending is not None:
            self._ai_queue.append(instruction)
            self.ai_chat.add_status(tr("folder.ai_queued", n=len(self._ai_queue)))
            self._update_queue_status()
            return
        self.pipeline.start(instruction)

    def _update_queue_status(self) -> None:
        """Cập nhật dòng trạng thái theo số yêu cầu còn xếp hàng."""
        n = len(self._ai_queue)
        if n:
            self._ai_status.setText("⏳ " + tr("folder.ai_status_running")
                                    + "  ·  " + tr("folder.ai_queue_count", n=n))
            self._ai_status.setStyleSheet(f"color:{current_palette().accent};")

    def maybe_dequeue(self) -> None:
        """When the pipeline is fully idle, start the next queued instruction."""
        if self.pipeline.worker is not None or self.pipeline.pending is not None:
            return
        if not self._ai_queue:
            return
        nxt = self._ai_queue.pop(0)
        self._update_queue_status()
        self.pipeline.start(nxt)

    # ---- pipeline callbacks (see ai_edit_pipeline.py) ------------------------- #
    def set_busy(self, busy: bool) -> None:
        """Khoá/mở ô nhập và nút gửi trong lúc một lượt sửa đang chạy."""
        self.ai_input.setEnabled(not busy)
        self.ai_send_btn.setEnabled(not busy)
        if busy:
            self._ai_status.setText("⏳ " + tr("folder.ai_status_running"))
            self._ai_status.setStyleSheet(f"color:{current_palette().accent};")
            self.badge_changed.emit(" ⏳")   # visible even when collapsed
        else:
            self._ai_status.setText("")
            self.badge_changed.emit("")

    def flag_done(self) -> None:
        """After a background run, show a 'done' badge so the user notices
        the result when they return to the tab; cleared on reopen. If more
        instructions are queued, start the next one instead."""
        if self.pipeline.worker is None and self.pipeline.pending is None and self._ai_queue:
            self.maybe_dequeue()
            return
        self._ai_status.setText("✓ " + tr("folder.ai_status_done"))
        self._ai_status.setStyleSheet(f"color:{current_palette().success};")
        self.badge_changed.emit(" ✓")

    def show_confirm_row(self, visible: bool) -> None:
        """Hiện/ẩn hàng nút Áp dụng · Huỷ cho bản đề xuất đang chờ."""
        self._ai_confirm_row.setVisible(visible)

    def set_review_status(self, text: str, color) -> None:
        """Đặt dòng trạng thái kèm màu (xanh khi xong, đỏ khi lỗi)."""
        self._ai_status.setText(text)
        if color:
            self._ai_status.setStyleSheet(f"color:{color};")

    def _confirm_routing_switch(self, decision, timeout: float) -> bool:
        """Manual mode: ask before moving this AI-Edit run to another model."""
        from cowork_local.ui.routing_toggle import confirm_switch

        return bool(confirm_switch(self, decision, timeout))


__all__ = ["AiFileEditorDialog"]
