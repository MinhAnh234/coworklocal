"""Scrollable chat transcript built from message bubbles."""
from __future__ import annotations

from .chat_bubble_style import (  # noqa: F401 — giữ đường vào cũ
    ThinkingIndicator, _TimelineGutter, _app_theme, _diff_legend, _dot_color, _p,
    diff_to_html, format_status_line,
)

import html
from pathlib import Path

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QTextBrowser,
    QVBoxLayout, QWidget,
)

from ...i18n import on_language_changed, tr
from ...theme import palette, resolve_theme
from ...config import CONFIG_DIR
from ...ui.osutil import is_image, open_folder, open_path


















class MessageBubble(QFrame):
    """One message; assistant/tool bubbles render markdown via QTextBrowser."""

    def __init__(self, role: str, title: str = "", collapsible: bool = False,
                 collapsed: bool = True):
        """Một bong bóng tin nhắn.

        ``collapsible`` dành cho khối dài (kết quả tool, suy nghĩ của model): chúng
        mở sẵn thì đẩy phần trả lời thật ra khỏi màn hình.
        """
        super().__init__()
        self.role = role
        self._text = ""
        self._collapsible = collapsible
        self._title = title
        self._head = None
        # Point-conversation layout: [dot rail][content column].
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)
        self._gutter = _TimelineGutter(role)
        outer.addWidget(self._gutter)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(2, 4, 8, 8)
        lay.setSpacing(4)
        self._content_layout = lay
        outer.addWidget(content, 1)

        if title:
            if collapsible:
                # Clickable header that folds long tool output away to keep the
                # transcript short. Collapsed by default; click to expand.
                self._head = QPushButton(title)
                self._head.setCursor(Qt.PointingHandCursor)
                self._head.setStyleSheet(
                    "QPushButton { text-align:left; border:none; background:transparent;"
                    f" font-weight:600; color:{_p().text_muted}; padding:0; }}")
                self._head.clicked.connect(self._toggle_body)
                lay.addWidget(self._head)
            else:
                head = QLabel(title)
                head.setStyleSheet(f"font-weight:600; color:{_p().text_muted};")
                lay.addWidget(head)

        self.body = QTextBrowser()
        self.body.setOpenExternalLinks(True)
        self.body.setFrameShape(QFrame.NoFrame)
        # Text color adapts to theme.
        self._apply_theme_styles(role)
        lay.addWidget(self.body)

        self._apply_style(role)
        if collapsible and collapsed:
            self.body.setVisible(False)
        if collapsible:
            self._update_head()

    def _toggle_body(self) -> None:
        """Gập/mở phần thân bong bóng khi bấm vào dòng tiêu đề."""
        self.body.setVisible(not self.body.isVisible())
        if self.body.isVisible():
            self._autosize()
        self._update_head()

    def _update_head(self) -> None:
        """Vẽ lại dòng tiêu đề: mũi tên gập/mở, và khi đang gập thì kèm 70 ký tự
        đầu làm xem trước — để nhìn dòng tiêu đề là đoán được bên trong có gì.
        """
        if not self._head:
            return
        expanded = self.body.isVisible()
        arrow = "▾" if expanded else "▸"
        preview = ""
        if not expanded and self._text.strip():
            first = self._text.strip().splitlines()[0]
            if len(first) > 70:
                first = first[:70] + "…"
            preview = f"   {first}"
        self._head.setText(f"{arrow} {self._title}{preview}")

    def _current_theme(self) -> str:
        """Resolve the current app theme (light or dark)."""
        return _app_theme()

    def _apply_theme_styles(self, role: str) -> None:
        """Apply text color to the body QTextBrowser based on current theme + role."""
        p = _p()
        text_color = {
            "success": p.success,
            "error": p.danger,
            "tool": p.text_muted,       # secondary, like Claude's steps
        }.get(role, p.text)
        self.body.setStyleSheet(f"background: transparent; border: none; color: {text_color};")

    def _apply_style(self, role: str) -> None:
        """Flat timeline row — no bubble box; the left dot/rail conveys role and
        structure (Claude-Code style). The user's own message gets a faint tint
        so questions are easy to pick out when scanning."""
        p = _p()
        if role == "user":
            self.setStyleSheet(
                f"QFrame {{ background: {p.surface}; border: none; "
                f"border-radius: {p.radius}px; }}")
        else:
            self.setStyleSheet("QFrame { background: transparent; border: none; }")

    def apply_theme(self) -> None:
        """Re-apply theme-dependent styles so existing rows adapt when the app
        theme switches (light ↔ dark)."""
        self._apply_theme_styles(self.role)
        self._apply_style(self.role)
        self._gutter.set_role(self.role)

    def chat_view(self):
        """Walk up the parent chain to find the enclosing ChatView, if any."""
        p = self.parent()
        while p is not None:
            if isinstance(p, ChatView):
                return p
            p = p.parent()
        return None

    def append_delta(self, delta: str) -> None:
        """Nối thêm một mẩu văn bản đang phát dần từ model rồi vẽ lại dạng markdown."""
        self._text += delta
        self.set_markdown(self._text)

    def set_markdown(self, text: str) -> None:
        """Đặt toàn bộ nội dung, hiển thị dạng markdown, rồi co giãn lại chiều cao."""
        self._text = text
        self.body.setMarkdown(text)
        self._autosize()
        if self._collapsible:
            self._update_head()

    def set_plain(self, text: str) -> None:
        """Đặt toàn bộ nội dung dạng văn bản thuần (không diễn giải markdown)."""
        self._text = text
        self.body.setPlainText(text)
        self._autosize()
        if self._collapsible:
            self._update_head()

    def append_plain(self, delta: str) -> None:
        """Nối thêm một mẩu văn bản thuần đang phát dần (dùng cho log tool)."""
        self._text += delta
        self.set_plain(self._text)

    def set_diff(self, diff_text: str) -> None:
        """Render a unified diff (see :func:`diff_to_html`) with colored
        before/after lines instead of a flat text block."""
        self._text = diff_text
        self.body.setHtml(diff_to_html(diff_text))
        self._autosize()
        if self._collapsible:
            self._update_head()

    def add_usage(self, text: str) -> None:
        """A small muted token/cost footer under the message (↓in ↑out ▤ctx $cost),
        like Claude Code. Replaces any previous usage line on this bubble."""
        existing = getattr(self, "_usage_lbl", None)
        if existing is not None:
            existing.setText(text)
            return
        lbl = QLabel(text)
        lbl.setObjectName("faint")
        lbl.setStyleSheet(f"color: {_p().text_faint}; font-size: 11px;")
        self._usage_lbl = lbl
        self._content_layout.addWidget(lbl)

    def add_delete_link(self, callback) -> None:
        """Gắn liên kết "xoá" màu cảnh báo dưới bong bóng, bấm vào thì gọi ``callback``."""
        link = QLabel(f'<a href="#del" style="color:{_p().danger};">{tr("chat.delete_link")}</a>')
        link.setToolTip(tr("chat.delete_tooltip"))
        link.linkActivated.connect(lambda *_: callback())
        self._content_layout.addWidget(link)

    def add_folder_link(self, folder: str, label: str | None = None) -> None:
        """Gắn liên kết mở thư mục kết quả trong trình quản lý tệp của hệ điều hành."""
        label = label or tr("chat.open_workspace")
        link = QLabel(f'<a href="#open" style="color:{_p().accent};">{label}</a>')
        link.setToolTip(str(folder))
        link.linkActivated.connect(lambda *_: open_folder(folder))
        self._content_layout.addWidget(link)

    def add_attachments(self, paths) -> None:
        """Show attached files: images as thumbnails, others as clickable links."""
        for p in paths:
            path = str(p)
            name = Path(path).name
            if is_image(path):
                pix = QPixmap(path)
                if not pix.isNull():
                    thumb = QLabel()
                    thumb.setPixmap(pix.scaledToWidth(min(320, pix.width()), Qt.SmoothTransformation))
                    thumb.setToolTip(name)
                    thumb.setCursor(Qt.PointingHandCursor)
                    self._content_layout.addWidget(thumb)
                    continue
            file_link = QLabel(f'<a href="#open" style="color:{_p().accent};">{name}</a>')
            file_link.setToolTip(path)
            file_link.linkActivated.connect(lambda *_a, fp=path: open_path(fp))
            self._content_layout.addWidget(file_link)

    def _autosize(self) -> None:
        """Đặt chiều cao bong bóng vừa đúng nội dung.

        QTextBrowser không tự co giãn theo nội dung, nên phải tính tay. Chặn
        trong khoảng 28..1200px: quá thấp thì mất chữ, quá cao thì một câu trả
        lời dài chiếm trọn màn hình và không cuộn tới cái sau được.
        """
        width = self.body.viewport().width()
        if width <= 0:
            width = 560  # sensible default before the widget is laid out
        self.body.document().setTextWidth(width)
        height = int(self.body.document().size().height()) + 12
        self.body.setFixedHeight(max(28, min(height, 1200)))

    def resizeEvent(self, event):  # noqa: N802 - re-flow on width change
        """Đổi bề rộng thì phải tính lại chiều cao — chữ xuống dòng khác đi."""
        super().resizeEvent(event)
        self._autosize()


class ChatView(QScrollArea):
    """Scrollable chat transcript.

    Emits ``theme_changed`` (via the apply_theme method) so every child
    ``MessageBubble`` can re-apply its theme-aware inline styles when the
    app switches between light and dark modes."""

    def __init__(self):
        """Vùng cuộn chứa dòng thời gian tin nhắn.

        Có một ``addStretch`` ở cuối để khi ít tin, chúng dồn lên trên thay vì trôi
        giữa khung.
        """
        super().__init__()
        self.setWidgetResizable(True)
        self._container = QWidget()
        self._lay = QVBoxLayout(self._container)
        self._lay.setContentsMargins(12, 12, 12, 12)
        self._lay.setSpacing(10)
        self._lay.addStretch(1)
        self.setWidget(self._container)

    def apply_theme(self) -> None:
        """Ask every MessageBubble inside this view to re-apply theme styles.

        Called from ``ChatPanel.apply_theme`` whenever the app theme changes."""
        for i in range(self._lay.count()):
            item = self._lay.itemAt(i)
            w = item.widget() if item else None
            if isinstance(w, MessageBubble):
                w.apply_theme()

    def _add(self, bubble: MessageBubble) -> MessageBubble:
        """Chèn bong bóng vào cuối danh sách (trước phần đệm co giãn) rồi cuộn xuống."""
        # insert before the trailing stretch
        self._lay.insertWidget(self._lay.count() - 1, bubble)
        self._scroll_to_bottom()
        return bubble

    def add_user(self, text: str) -> MessageBubble:
        """Thêm một tin nhắn của người dùng."""
        b = MessageBubble("user", tr("chat.you"))
        b.set_plain(text)
        return self._add(b)

    def add_assistant(self, title: str | None = None) -> MessageBubble:
        """Thêm một bong bóng trả lời rỗng để model phát nội dung dần vào."""
        b = MessageBubble("assistant", title or tr("chat.assistant"))
        return self._add(b)

    def add_tool(self, title: str, body: str, ok: bool = True) -> MessageBubble:
        """Thêm một bước tool (chạy lệnh, sinh mã, kết quả).

        Chạy xuôi thì gập lại cho dòng thời gian ngắn gọn; lỗi thì mở sẵn vì đó
        là thứ người dùng cần đọc ngay.
        """
        # Tool steps (run command, generated code/diff, output) are collapsible to
        # keep the transcript short — collapsed when OK, expanded on error.
        b = MessageBubble("tool" if ok else "error", title, collapsible=True, collapsed=ok)
        b.set_plain(body)
        return self._add(b)

    def add_diff(self, title: str, diff_text: str, ok: bool = True) -> MessageBubble:
        """Like :meth:`add_tool`, but renders ``diff_text`` as a colored
        before/after diff (see :func:`diff_to_html`) instead of flat text."""
        b = MessageBubble("tool" if ok else "error", title, collapsible=True, collapsed=ok)
        b.set_diff(diff_text)
        return self._add(b)

    def add_plan(self, body: str) -> MessageBubble:
        """The task plan shown INLINE in the timeline (never a pop-up or side
        panel) — a permanent, always-expanded row whose steps tick off as they
        complete. The agent re-sends the full list on each update; the caller
        updates this same row in place via ``set_plain``."""
        b = MessageBubble("tool", tr("widgets.plan_title"), collapsible=False)
        b.set_plain(body)
        return self._add(b)

    def add_reasoning(self, title: str | None = None) -> MessageBubble:
        """Thêm hộp suy luận nội bộ của model — gập sẵn, mở ra đọc được.

        Để người dùng thấy nó đang nghĩ mà không bị lấp kín khung chat.
        """
        # The model's private reasoning — a collapsed, collapsible box so the user
        # can see it's thinking (and expand to read) without it flooding the chat.
        b = MessageBubble("tool", title or tr("chat.thinking"), collapsible=True, collapsed=True)
        return self._add(b)

    def add_error(self, text: str) -> MessageBubble:
        """Thêm một bong bóng báo lỗi."""
        b = MessageBubble("error", tr("chat.error"))
        b.set_plain(text)
        return self._add(b)

    def add_status(self, text: str) -> MessageBubble:
        """A small one-line status marker in the transcript (e.g. '✅ Đã hoàn thành')."""
        b = MessageBubble("tool", "")
        b.set_plain(text)
        return self._add(b)

    def add_success(self, text: str) -> MessageBubble:
        """Like :meth:`add_status`, but styled green — used for the "turn done"
        marker so completion reads as an unmistakable success signal."""
        b = MessageBubble("success", "")
        b.set_plain(text)
        return self._add(b)

    def clear(self) -> None:
        """Xoá sạch dòng thời gian, giữ lại phần đệm co giãn ở cuối."""
        while self._lay.count() > 1:
            item = self._lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def scroll_to_bottom(self) -> None:
        """Scroll to the newest message, deferred so freshly-added bubbles have
        finished sizing (their height is computed after layout)."""
        QTimer.singleShot(0, self._scroll_to_bottom)
        QTimer.singleShot(80, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        """Kéo thanh cuộn xuống đáy ngay lập tức."""
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())


ChatHistoryWidget = ChatView

__all__ = ["ChatView", "ChatHistoryWidget", "MessageBubble"]

