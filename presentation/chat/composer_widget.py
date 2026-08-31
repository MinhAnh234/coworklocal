"""Message composer: multiline input, attachments, Send/Stop, message queue.

Several turns can run at once (up to the configured parallel limit). Once that
limit is reached the composer switches to "Queue" mode: extra messages (with
their attachments) are held in the queue and dispatched automatically as running
turns finish and free up a slot. Files/images can be attached to a message.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QListView, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout, QWidget,
)

from ...i18n import on_language_changed, tr
from ...theme import current_palette
from ...ui.icons import icon, IconLabel
from .chat_input_box import _Input
from .composer_mime import is_local_agent_command, is_local_skill_command


class Composer(QWidget):
    """Vùng soạn tin: ô nhập, tệp đính kèm, hàng đợi tin nhắn và dải trạng thái.

    Hàng đợi cho phép gõ tiếp trong lúc lượt trước còn chạy — chỗ gọi rút dần
    qua :meth:`pop_next` sau mỗi lượt xong.
    """
    submitted = Signal(str, list)        # (text, attachment paths)
    stop_requested = Signal()
    queue_changed = Signal(int)
    attachments_added = Signal(list)     # current attachment paths (pushed to the Input box)
    attachment_removed = Signal(str)     # a wrongly-added attachment was removed
    attach_limit_note = Signal(str)      # shown when the attachment-count limit is hit
    manage_skills = Signal()             # relayed from the /skill popup "Manage skills…"

    def __init__(self, placeholder_key: str = "composer.placeholder_default"):
        """Dựng ô soạn kèm hàng đính kèm và hàng đợi tin nhắn.

        Người dùng gõ tiếp trong lúc lượt trước đang chạy thì tin mới vào hàng đợi
        chứ không bị bỏ.
        """
        super().__init__()
        self._placeholder_key = placeholder_key   # i18n key, re-looked-up on language change
        self._queue: List[Dict] = []          # each: {"text": str, "attachments": [str]}
        self._attachments: List[str] = []
        self._max_attachments = 0             # 0 = unlimited; set from Settings
        self._busy = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # --- queue strip (hidden when empty) ---
        self.queue_box = QWidget()
        qlay = QVBoxLayout(self.queue_box)
        qlay.setContentsMargins(0, 0, 0, 0)
        self.queue_label = QLabel()
        self.queue_label.setObjectName("hint")
        self.queue_list = QListWidget()
        self.queue_list.setMaximumHeight(78)
        self.queue_list.itemDoubleClicked.connect(self._remove_queue_item)
        qlay.addWidget(self.queue_label)
        qlay.addWidget(self.queue_list)
        self.queue_box.setVisible(False)
        root.addWidget(self.queue_box)

        # --- attachments strip (hidden when empty) ---
        self.attach_box = QWidget()
        alay = QVBoxLayout(self.attach_box)
        alay.setContentsMargins(0, 0, 0, 0)
        self.attach_label = QLabel()
        self.attach_label.setObjectName("hint")
        self.attach_list = QListWidget()
        # Single horizontal row of chips; scroll sideways when there are many.
        self.attach_list.setFlow(QListView.LeftToRight)
        self.attach_list.setWrapping(False)
        self.attach_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.attach_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.attach_list.setFixedHeight(40)
        self.attach_list.itemDoubleClicked.connect(self._remove_attachment)
        alay.addWidget(self.attach_label)
        alay.addWidget(self.attach_list)
        self.attach_box.setVisible(False)
        root.addWidget(self.attach_box)

        # --- input row ---
        row = QHBoxLayout()
        self.input = _Input()
        self.input.setPlaceholderText(tr(self._placeholder_key))
        self.input.submit.connect(self._on_submit)
        self.input.media_added.connect(self._add_paths)
        self.input.manage_skills.connect(self.manage_skills.emit)
        row.addWidget(self.input, 1)

        btns = QVBoxLayout()
        self.attach_btn = QPushButton("")
        self.attach_btn.setIcon(icon("attach"))
        self.attach_btn.clicked.connect(self._pick_attachments)
        self.send_btn = QPushButton()
        self.send_btn.setIcon(icon("upload"))
        self.send_btn.setObjectName("primary")
        self.send_btn.clicked.connect(self._on_submit)
        self.stop_btn = QPushButton()
        self.stop_btn.setIcon(icon("stop"))
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setVisible(False)
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        # Attach pinned to the input's top edge, Send (and Stop, once a turn
        # is running) pinned to its bottom edge — the gap between them is
        # absorbed by this stretch instead of splitting evenly above/below
        # the whole button column, which is what centering it did before.
        btns.addWidget(self.attach_btn)
        btns.addStretch(1)
        btns.addWidget(self.send_btn)
        btns.addWidget(self.stop_btn)
        row.addLayout(btns)
        root.addLayout(row)

        # bottom row: left slot (e.g. Cowork's output-folder picker) — stretch —
        # right slot (e.g. Plan/Act toggle, the per-tab Agent combo on Code/Cowork)
        # Its own strip UNDER the typing box, styled as a status line rather
        # than a second toolbar: the design asks for the typing area to be just
        # input · attach · send, with agent / routing / usage / folder reading
        # as status underneath. They stay interactive — only quieter.
        self._bottom_left_count = 0
        self.extra_bar = QWidget()
        self.extra_bar.setObjectName("composerStatus")
        self.extra_row = QHBoxLayout(self.extra_bar)
        self.extra_row.setContentsMargins(2, 2, 2, 0)
        self.extra_row.setSpacing(6)
        self.extra_row.addStretch(1)
        root.addWidget(self.extra_bar)

        on_language_changed(self._retranslate)

    def _retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn cho placeholder và các tooltip."""
        self.queue_list.setToolTip(tr("composer.queue_tooltip"))
        self.attach_list.setToolTip(tr("composer.attachments_tooltip"))
        self.attach_btn.setToolTip(tr("composer.attach_btn_tooltip"))
        self.send_btn.setText(tr("composer.queue_btn") if self._busy else tr("composer.send"))
        self.stop_btn.setText(tr("composer.stop"))
        if self.input.toPlainText().strip() == "" and not self._attachments:
            self.input.setPlaceholderText(tr(self._placeholder_key))
        self._refresh_queue()
        self._refresh_attachments()

    def add_bottom_right(self, widget) -> None:
        """Gắn thêm một widget vào dải trạng thái dưới ô nhập (bộ chọn agent, định
        tuyến, usage…).
        """
        self.extra_row.addWidget(widget)

    def add_bottom_left(self, widget) -> None:
        """Insert before the stretch, after any previously-added left widget —
        so repeated calls read left-to-right in call order, same row as
        whatever add_bottom_right widgets (e.g. the Agent combo) sit on the
        right of the stretch."""
        self.extra_row.insertWidget(self._bottom_left_count, widget)
        self._bottom_left_count += 1

    # ---- public API --------------------------------------------------
    def set_text(self, text: str) -> None:
        """Đặt nội dung ô nhập và đưa con trỏ vào đó."""
        self.input.setPlainText(text)
        self.input.setFocus()

    def reset_input(self) -> None:
        """Clear the input + pending attachments and restore the default placeholder
        (used on New chat so no stale text or 'Attached: …' hint carries over)."""
        self.input.clear()
        self._attachments = []
        self._refresh_attachments()
        self.input.setPlaceholderText(tr(self._placeholder_key))

    def set_busy(self, busy: bool) -> None:
        """Capacity gate: when True, new sends are queued (the Send button reads
        'Queue'). Independent of whether any turn is running — see set_running."""
        self._busy = busy
        self.send_btn.setText(tr("composer.queue_btn") if busy else tr("composer.send"))

    def set_running(self, running: bool) -> None:
        """Show the Stop button whenever at least one turn is running (may be True
        even when not at capacity, so a single in-flight message can be stopped)."""
        self.stop_btn.setVisible(running)

    def has_queue(self) -> bool:
        """Còn tin nhắn nào đang xếp hàng chờ gửi không."""
        return bool(self._queue)

    def pop_next(self) -> Dict | None:
        """Lấy tin nhắn kế tiếp trong hàng đợi ra; ``None`` nếu hàng đợi rỗng."""
        if not self._queue:
            return None
        item = self._queue.pop(0)
        self._refresh_queue()
        return item

    def clear_queue(self) -> None:
        """Xoá sạch hàng đợi (dùng khi người dùng bấm Dừng)."""
        self._queue.clear()
        self._refresh_queue()

    def enqueue(self, text: str, attachments: List[str] | None = None) -> None:
        """Xếp một tin nhắn vào cuối hàng đợi."""
        self._queue.append({"text": text, "attachments": list(attachments or [])})
        self._refresh_queue()

    # ---- attachments -------------------------------------------------
    def set_max_attachments(self, n: int) -> None:
        """Đặt trần số tệp đính kèm cho một tin nhắn."""
        self._max_attachments = max(0, int(n or 0))

    def _add_one(self, path: str) -> bool:
        """Add a file unless it's a duplicate or the count limit is reached.
        Returns False (and notifies) when the limit blocked it."""
        if not path or path in self._attachments:
            return True
        if self._max_attachments and len(self._attachments) >= self._max_attachments:
            self.attach_limit_note.emit(tr("chatpanel.attach_limit", n=self._max_attachments))
            return False
        self._attachments.append(path)
        return True

    def _pick_attachments(self) -> None:
        """Mở hộp thoại chọn tệp đính kèm."""
        files, _ = QFileDialog.getOpenFileNames(
            self, tr("composer.attach_dialog_title"), "",
            tr("composer.attach_dialog_filter"),
        )
        for f in files:
            if not self._add_one(f):
                break
        self._refresh_attachments()

    def _add_paths(self, paths: List[str]) -> None:
        """Add attachments from paste / drag-drop."""
        for p in paths:
            if not self._add_one(p):
                break
        self._refresh_attachments()
        if paths:
            names = ", ".join(Path(p).name for p in paths)
            self.input.setPlaceholderText(tr("chatpanel.attached_hint", names=names))

    def _remove_attachment(self, item: QListWidgetItem) -> None:
        """Gỡ một tệp đính kèm khỏi danh sách."""
        idx = self.attach_list.row(item)
        if 0 <= idx < len(self._attachments):
            self._remove_attachment_path(self._attachments[idx])

    def _remove_attachment_path(self, path: str) -> None:
        """Remove one wrongly-added file (✕ button or double-click)."""
        if path in self._attachments:
            self._attachments.remove(path)
            self._refresh_attachments()
            self.attachment_removed.emit(path)   # also drop it from the Input panel

    def _refresh_attachments(self) -> None:
        """Vẽ lại danh sách tệp đính kèm."""
        self.attach_list.clear()
        for p in self._attachments:
            item = QListWidgetItem()
            row = QWidget()
            _cp = current_palette()
            row.setStyleSheet(
                f"background: {_cp.surface_raised}; border: 1px solid {_cp.border};"
                f" border-radius: {_cp.radius_sm}px;")
            h = QHBoxLayout(row)
            h.setContentsMargins(8, 2, 4, 2)
            h.setSpacing(4)
            short = Path(p).name
            if len(short) > 22:
                short = short[:19] + "…"
            name = IconLabel("attach", short, size=13)
            name.setToolTip(p)
            remove = QPushButton()
            remove.setIcon(icon("close", size=12))
            remove.setObjectName("danger")
            remove.setFixedSize(18, 18)
            remove.setToolTip(tr("composer.remove_tooltip"))
            remove.setCursor(Qt.PointingHandCursor)
            remove.clicked.connect(lambda _=False, path=p: self._remove_attachment_path(path))
            h.addWidget(name)       # compact chip (no stretch → many fit in one row)
            h.addWidget(remove)
            item.setSizeHint(row.sizeHint())
            self.attach_list.addItem(item)
            self.attach_list.setItemWidget(item, row)
        self.attach_label.setText(tr("composer.attachments_label", n=len(self._attachments)))
        self.attach_box.setVisible(bool(self._attachments))
        if self._attachments:
            self.attachments_added.emit(list(self._attachments))

    # ---- submit / queue ----------------------------------------------
    def _on_submit(self) -> None:
        """Gửi tin: bận thì xếp hàng, rảnh thì phát ``submitted``.

        Không gửi khi vừa trống chữ vừa không có tệp đính kèm.
        """
        text = self.input.toPlainText().strip()
        attachments = list(self._attachments)
        if not text and not attachments:
            return
        self.input.clear()
        self._attachments = []
        self._refresh_attachments()
        self.input.setPlaceholderText(tr(self._placeholder_key))   # clear any "Attached: …" hint
        # A local /skill or /agent list/select command is answered inline instantly
        # — run it now even while a turn is busy (don't bury it in the queue).
        if self._busy and not (is_local_skill_command(text) or is_local_agent_command(text)):
            self._queue.append({"text": text, "attachments": attachments})
            self._refresh_queue()
        else:
            self.submitted.emit(text, attachments)

    def _remove_queue_item(self, item: QListWidgetItem) -> None:
        """Gỡ một tin khỏi hàng đợi trước khi nó được gửi."""
        idx = self.queue_list.row(item)
        if 0 <= idx < len(self._queue):
            self._queue.pop(idx)
            self._refresh_queue()

    def _refresh_queue(self) -> None:
        """Vẽ lại danh sách hàng đợi và báo số lượng ra ngoài."""
        self.queue_list.clear()
        for i, entry in enumerate(self._queue, 1):
            text = entry.get("text", "")
            n = len(entry.get("attachments", []))
            preview = text if len(text) <= 70 else text[:70] + "…"
            if n:
                preview += f"  (+{n})"
            self.queue_list.addItem(f"{i}. {preview}")
        self.queue_label.setText(tr("composer.queue_label", n=len(self._queue)))
        self.queue_box.setVisible(bool(self._queue))
        self.queue_changed.emit(len(self._queue))


ComposerWidget = Composer

__all__ = ["Composer", "ComposerWidget"]

