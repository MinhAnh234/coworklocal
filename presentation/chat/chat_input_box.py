"""Ô nhập của khung chat — R08-T02.

Tự giãn cao theo nội dung, Ctrl+Enter để gửi, dán ảnh từ clipboard thành tệp
đính kèm, và popup gợi ý khi gõ ``/skill`` hoặc ``/agent``.

Tách khỏi ``composer_widget.py`` vì đây là phần bắt phím và chuột; phần kia
là thanh công cụ quanh nó.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QPlainTextEdit
from ...i18n import tr
from .composer_mime import paths_from_mime


class _SkillPopup(QListWidget):
    """The ``/skill`` picker.

    Shown as a NON-activating overlay (``WA_ShowWithoutActivating``) — crucially it
    does NOT grab the keyboard, so the input keeps focus and the user can keep
    typing their request after ``/skill``. Navigation / accept / Esc are handled by
    the parent ``_Input``'s key handler (which still receives every key); clicking
    an item selects it; the popup auto-hides when the input loses focus."""

    def __init__(self, parent=None):
        """Danh sách gợi ý skill nổi lên khi gõ ``/``.

        Đặt cờ không nhận tiêu điểm: bật lên mà cướp tiêu điểm thì con trỏ rời ô
        nhập và người dùng gõ tiếp không được.
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint
                            | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.NoFocus)


class _Input(QPlainTextEdit):
    """Plain text edit: submits on Enter, accepts pasted/dropped images & files."""

    submit = Signal()
    media_added = Signal(list)
    manage_skills = Signal()   # user picked "Manage skills…" in the /skill popup

    MIN_HEIGHT = 64     # ~2 lines
    MAX_HEIGHT = 220    # ~8 lines, then it scrolls

    def __init__(self):
        """Ô soạn tin, nhận kéo–thả tệp.

        Đặt phông riêng vì quy tắc ``*`` chung rơi về phông tiếng Nhật, làm một số
        chữ tiếng Việt hiện sai dấu.
        """
        super().__init__()
        self.setAcceptDrops(True)
        # Use a clean Latin/Vietnamese-friendly UI font for the input (the global
        # '*' rule falls back to Japanese faces, which mis-render some glyphs).
        self.setStyleSheet(
            "font-family: 'Segoe UI', 'Helvetica Neue', 'Arial', sans-serif; font-size: 14px;"
        )
        # Grow with the text (up to MAX_HEIGHT), then scroll instead.
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.textChanged.connect(self._adjust_height)
        # "/skill" + "/agent" command popup — lists skills / agents inline.
        self._skill_popup = _SkillPopup(self)
        self._popup_kind = "skill"            # which command the popup is showing
        self._skill_popup.itemClicked.connect(self._accept_item)
        self.textChanged.connect(self._maybe_show_skills)
        self._adjust_height()

    # ---- /skill autocomplete ----------------------------------------
    def _skill_token(self):
        """Locate a ``/skill[:partial]`` command the cursor is currently typing —
        ANYWHERE in the message, not just at the start (so "dùng /skill:foo …"
        with text typed before it still triggers the picker). Mirrors
        ``core.skills.parse_skill_command``'s whitespace-boundary rule.

        Returns ``(start_offset, partial_filter)`` — ``start_offset`` is where the
        ``/skill`` token begins in the document, ``partial_filter`` is the text
        typed after ``:`` (``''`` while still typing the command word itself) — or
        ``None`` when the cursor isn't inside a ``/skill`` token."""
        import re
        pos = self.textCursor().position()
        before = self.toPlainText()[:pos]
        # The token is the whitespace-delimited word ending at the cursor; its
        # start must be the document start or follow whitespace (same boundary
        # parse_skill_command enforces with its (?<!\S) lookbehind).
        start = re.search(r"\S*$", before).start()
        token = before[start:]
        if len(token) >= 2 and "/skill".startswith(token):
            return start, ""   # typing "/s", "/sk", … "/skill" → show the whole list
        m = re.match(r"^/skill:?([\w\-.]*)$", token)
        return (start, m.group(1)) if m else None

    def _skill_filter(self):
        """Return the partial filter while a '/skill' command is being typed
        (anywhere in the message), or None."""
        tok = self._skill_token()
        return tok[1] if tok else None

    def _agent_token(self):
        """Locate a ``/agent[:partial]`` command the cursor is typing (mirror of
        ``_skill_token``). Returns ``(start_offset, partial)`` or None."""
        import re
        pos = self.textCursor().position()
        before = self.toPlainText()[:pos]
        start = re.search(r"\S*$", before).start()
        token = before[start:]
        if len(token) >= 2 and "/agent".startswith(token):
            return start, ""
        m = re.match(r"^/agent:?([\w\-.]*)$", token)
        return (start, m.group(1)) if m else None

    def _maybe_show_skills(self) -> None:
        # One popup serves both commands: show skills while typing /skill, agents
        # while typing /agent (Cowork parity with the Co4E chat).
        """Mở bảng gợi ý khi con trỏ đang đứng trên lệnh ``/skill`` hoặc ``/agent``.

        Một bảng dùng chung cho cả hai lệnh, ``_popup_kind`` nhớ đang gợi ý loại
        nào — giống hệt cách khung chat Co4E làm.
        """
        stok = self._skill_token()
        if stok is not None:
            self._popup_kind = "skill"
            self._populate_skill_popup(stok[1])
            self._show_cmd_popup()
            return
        atok = self._agent_token()
        if atok is not None:
            self._popup_kind = "agent"
            self._populate_agent_popup(atok[1])
            self._show_cmd_popup()
            return
        self._skill_popup.hide()

    def _populate_skill_popup(self, filt: str) -> None:
        """Nạp danh sách skill khớp bộ lọc vào bảng gợi ý.

        Gồm cả skill dựng sẵn để bảng vẫn dùng được khi người dùng chưa tạo skill
        nào. Dấu ✓ đánh dấu skill đang bật. Dòng cuối luôn là lối mở trình quản lý.
        """
        try:
            from ..core.skills import builtin_skills, list_skills
            # Include always-on built-ins so the picker is usable before the user
            # has created any custom skill.
            skills = list_skills() + builtin_skills()
        except Exception:
            skills = []
        f = (filt or "").lower()
        matches = [s for s in skills
                   if f in s.name.lower() or f in s.slug.lower() or f in (s.description or "").lower()]
        self._skill_popup.clear()
        for s in matches:
            text = ("✓ " if s.enabled else "   ") + s.name
            if s.description:
                text += f"  —  {s.description}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, s.slug)
            self._skill_popup.addItem(item)
        if not matches:
            empty = QListWidgetItem(tr("composer.no_skills"))
            empty.setFlags(Qt.NoItemFlags)
            self._skill_popup.addItem(empty)
        manage = QListWidgetItem(tr("composer.manage_skills"))
        manage.setData(Qt.UserRole, "__manage__")
        self._skill_popup.addItem(manage)
        self._skill_popup.setCurrentRow(0 if matches else self._skill_popup.count() - 1)

    def _populate_agent_popup(self, filt: str) -> None:
        """Nạp danh sách agent khớp bộ lọc (dựng sẵn + admin + tự tạo) vào bảng gợi ý."""
        try:
            from ..core.agent_command import collect_agents
            agents = collect_agents("")   # built-ins + local admin + custom agents
        except Exception:
            agents = []
        f = (filt or "").lower()
        matches = [a for a in agents
                   if f in a["slug"].lower() or f in a["name"].lower() or f in (a.get("desc") or "").lower()]
        self._skill_popup.clear()
        for a in matches:
            text = a["name"] + (f"  —  {a['desc']}" if a.get("desc") else "")
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, a["slug"])
            self._skill_popup.addItem(item)
        if not matches:
            empty = QListWidgetItem(tr("composer.no_agents"))
            empty.setFlags(Qt.NoItemFlags)
            self._skill_popup.addItem(empty)
        self._skill_popup.setCurrentRow(0 if matches else self._skill_popup.count() - 1)

    def _show_cmd_popup(self) -> None:
        """Hiện bảng gợi ý ngay PHÍA TRÊN ô nhập, cao tối đa 7 dòng.

        Đặt trên chứ không dưới vì ô nhập nằm sát đáy cửa sổ — thả xuống dưới là
        rơi ra ngoài màn hình.
        """
        rows = min(7, self._skill_popup.count())
        h = 10 + rows * 22
        self._skill_popup.resize(max(300, self.width()), h)
        top_left = self.mapToGlobal(self.rect().topLeft())
        self._skill_popup.move(top_left.x(), top_left.y() - h - 2)
        self._skill_popup.show()

    def _dismiss_skill_popup(self) -> None:
        """Hide the /skill picker (Esc)."""
        self._skill_popup.hide()

    def focusOutEvent(self, e) -> None:  # noqa: N802
        # The popup never grabs focus, so a click away lands here → dismiss it
        # (unless the click is on the popup itself, e.g. picking an item).
        """Bấm ra chỗ khác thì ẩn bảng gợi ý.

        Bảng không bao giờ giành focus, nên mọi cú bấm ra ngoài đều rơi vào đây —
        trừ khi chuột đang ở trên chính bảng, tức người dùng đang chọn một mục.
        """
        if not self._skill_popup.underMouse():
            self._skill_popup.hide()
        super().focusOutEvent(e)

    def _accept_item(self, item=None) -> None:
        """Dispatch popup selection to the right handler based on which command
        (``/skill`` or ``/agent``) the popup is currently showing."""
        if self._popup_kind == "agent":
            self._accept_agent(item)
        else:
            self._accept_skill(item)

    def _replace_token(self, tok, replacement: str) -> None:
        """Thay đúng đoạn lệnh con trỏ đang đứng, giữ nguyên chữ trước và sau nó.

        Nhờ vậy ``/skill:`` viết được ở giữa câu. Chặn tín hiệu lúc đặt lại nội
        dung để không kích hoạt lại chính bảng gợi ý.
        """
        pos = self.textCursor().position()
        start = tok[0] if tok else pos
        full = self.toPlainText()
        new_text = full[:start] + replacement + full[pos:]
        new_pos = start + len(replacement)
        self.blockSignals(True)
        self.setPlainText(new_text)
        self.blockSignals(False)
        cur = self.textCursor()
        cur.setPosition(min(new_pos, len(new_text)))
        self.setTextCursor(cur)
        self._adjust_height()
        self.setFocus()

    def _accept_skill(self, item=None) -> None:
        """Chọn một skill: thay đoạn ``/skill…`` bằng ``/skill:<slug>``.

        Mục cuối cùng (``__manage__``) không phải skill mà là lối mở trình quản lý.
        """
        item = item or self._skill_popup.currentItem()
        self._skill_popup.hide()
        if item is None:
            return
        slug = item.data(Qt.UserRole)
        if slug == "__manage__":
            self.manage_skills.emit()   # open the Skills manager
            return
        if not slug:
            return
        # Replace ONLY the /skill token the cursor is on — text typed before it
        # ("dùng …") and after it is preserved, so the command can sit mid-sentence.
        self._replace_token(self._skill_token(), f"/skill:{slug} ")

    def _accept_agent(self, item=None) -> None:
        """Chọn một agent: thay đoạn ``/agent…`` bằng ``/agent:<slug>``."""
        item = item or self._skill_popup.currentItem()
        self._skill_popup.hide()
        if item is None:
            return
        slug = item.data(Qt.UserRole)
        if not slug:
            return
        self._replace_token(self._agent_token(), f"/agent:{slug} ")

    def _adjust_height(self, *_a) -> None:
        # QPlainTextEdit reports the document height in LINES (not pixels), so
        # convert via line spacing to get the real pixel height.
        """Co giãn ô nhập theo số dòng đang gõ, chặn trong ``MIN_HEIGHT``..``MAX_HEIGHT``.

        ``QPlainTextEdit`` trả chiều cao tài liệu theo SỐ DÒNG chứ không phải
        pixel, nên phải nhân với khoảng cách dòng mới ra chiều cao thật.
        """
        lines = self.document().size().height() or 1
        line_px = self.fontMetrics().lineSpacing()
        h = int(lines * line_px + 2 * self.frameWidth() + 12)
        h = max(self.MIN_HEIGHT, min(self.MAX_HEIGHT, h))
        if h != self.height():
            self.setFixedHeight(h)

    def keyPressEvent(self, e: QKeyEvent) -> None:  # noqa: N802
        """Điều hướng bảng gợi ý khi nó đang mở (lên/xuống/Enter/Esc); ngoài ra
        Enter gửi tin nhắn còn Shift+Enter xuống dòng.
        """
        if self._skill_popup.isVisible():
            k = e.key()
            if k in (Qt.Key_Down, Qt.Key_Up):
                n = self._skill_popup.count()
                if n:
                    step = 1 if k == Qt.Key_Down else -1
                    self._skill_popup.setCurrentRow((self._skill_popup.currentRow() + step) % n)
                return
            if k == Qt.Key_Tab:
                self._accept_item()   # Tab = autocomplete the highlighted item
                return
            if k == Qt.Key_Escape:
                self._dismiss_skill_popup()
                return
            if k in (Qt.Key_Return, Qt.Key_Enter):
                item = self._skill_popup.currentItem()
                slug = item.data(Qt.UserRole) if item else None
                is_agent = self._popup_kind == "agent"
                tok = self._agent_token() if is_agent else self._skill_token()
                prefix = "/agent:" if is_agent else "/skill:"
                token = self.toPlainText()[tok[0]:self.textCursor().position()] if tok else ""
                exact = bool(slug) and slug != "__manage__" and token == f"{prefix}{slug}"
                if slug and slug != "__manage__" and not exact:
                    # A suggestion is highlighted but not yet fully typed —
                    # Enter completes it into the box first (same as Tab),
                    # instead of submitting a partial/mistyped slug that
                    # the parser would just reject as "not found".
                    self._accept_item(item)
                    return
                # Slug already fully typed (or nothing usable is highlighted,
                # e.g. the "no skills found" placeholder) — Enter RUNS the
                # /skill command as typed: hide the popup and fall through to
                # the normal submit below.
                self._skill_popup.hide()
        if e.key() in (Qt.Key_Return, Qt.Key_Enter) and not (e.modifiers() & Qt.ShiftModifier):
            self.submit.emit()
            return
        super().keyPressEvent(e)

    def insertFromMimeData(self, source) -> None:  # noqa: N802 - paste
        """Dán ảnh hoặc đường dẫn tệp thì gắn thành tệp đính kèm thay vì dán chữ."""
        paths = paths_from_mime(source)
        if paths:
            self.media_added.emit(paths)
            return
        super().insertFromMimeData(source)

    def canInsertFromMimeData(self, source) -> bool:  # noqa: N802
        """Cho phép dán cả ảnh và danh sách tệp, không chỉ văn bản."""
        if source.hasImage() or source.hasUrls():
            return True
        return super().canInsertFromMimeData(source)

    def dragEnterEvent(self, e) -> None:  # noqa: N802
        """Nhận kéo-thả ảnh và tệp vào ô nhập."""
        if e.mimeData().hasUrls() or e.mimeData().hasImage():
            e.acceptProposedAction()
            return
        super().dragEnterEvent(e)

    def dragMoveEvent(self, e) -> None:  # noqa: N802
        """Giữ trạng thái nhận thả trong suốt lúc rê qua ô nhập."""
        if e.mimeData().hasUrls() or e.mimeData().hasImage():
            e.acceptProposedAction()
            return
        super().dragMoveEvent(e)

    def dropEvent(self, e) -> None:  # noqa: N802
        """Thả tệp/ảnh vào ô nhập: gắn thành tệp đính kèm của lượt chat."""
        paths = paths_from_mime(e.mimeData())
        if paths:
            self.media_added.emit(paths)
            e.acceptProposedAction()
            return
        super().dropEvent(e)
