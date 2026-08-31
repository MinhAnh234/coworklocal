"""Cách vẽ một bong bóng chat: màu, đường thời gian, diff, trạng thái — R08-T01.

Tách khỏi ``chat_history_widget.py``: đây là phần quyết định TRÔNG THẾ NÀO,
còn file kia quyết định HIỆN CÁI GÌ.

``diff_to_html`` tô màu phần thêm/bớt khi agent sửa file; ``_TimelineGutter``
vẽ đường dọc nối các lượt, ``ThinkingIndicator`` là ba chấm lúc chờ.
"""
from __future__ import annotations

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


def _app_theme() -> str:
    """Resolve the current app theme (light or dark) from config."""
    try:
        import json
        with open(CONFIG_DIR / "config.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return resolve_theme(data.get("theme", "dark"))
    except Exception:  # noqa: BLE001
        return "dark"


def _p():
    """Design tokens for the theme in effect right now."""
    return palette(_app_theme())


def _dot_color(role: str) -> str:
    """Timeline dot colour for a message role."""
    p = _p()
    return {
        "user": p.role_user, "assistant": p.role_assistant, "tool": p.role_tool,
        "error": p.role_error, "success": p.role_result,
    }.get(role, p.text_faint)


class _TimelineGutter(QWidget):
    """The left rail of the point-conversation: a vertical connector line with a
    role-colored dot near the top, so stacked messages read as a timeline
    (Claude-Code style) instead of separate boxes."""

    def __init__(self, role: str):
        """Dải dọc bên trái mỗi bong bóng, màu theo vai người nói."""
        super().__init__()
        self._role = role
        self.setFixedWidth(22)

    def set_role(self, role: str) -> None:
        """Đổi vai trò (người dùng/trợ lý/tool/lỗi) và vẽ lại chấm mốc."""
        self._role = role
        self.update()

    def paintEvent(self, _e):  # noqa: N802
        """Vẽ dải mốc thời gian bên trái bong bóng: một đường mờ chạy suốt chiều cao
        cộng một chấm màu theo vai trò — nối lại thành một trục liền mạch cho cả
        dòng thời gian.
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        tok = _p()
        x = 11.0
        cy = 15.0
        # connector line (faint) running the full height → continuous rail
        p.setPen(QPen(QColor(tok.border), 2))
        p.drawLine(int(x), 0, int(x), self.height())
        # a background ring lifts the dot off the line
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(tok.bg))
        p.drawEllipse(QPointF(x, cy), 7.5, 7.5)
        p.setBrush(QColor(_dot_color(self._role)))
        p.drawEllipse(QPointF(x, cy), 4.5, 4.5)


def _diff_legend(diff_text: str) -> str:
    """A small badge pair labeling what the colors mean: 'Before → After' for
    an edit, or a single 'Added'/'Removed' badge for a pure create/delete —
    so the before/after distinction is explicit, not just implied by color."""
    has_add = any(ln.startswith("+") and not ln.startswith("+++") for ln in diff_text.splitlines())
    has_del = any(ln.startswith("-") and not ln.startswith("---") for ln in diff_text.splitlines())
    p = _p()

    def pill(bg: str, fg: str, key: str) -> str:
        """Một nhãn viên thuốc (nền + chữ) trong chú giải diff."""
        return (f'<span style="background:{bg}; color:{fg}; padding:1px 8px; '
                f'border-radius:4px; font-weight:600;">{html.escape(tr(key))}</span>')

    if has_add and has_del:
        badge = (pill(p.diff_del_bg, p.diff_del_fg, "chat.diff_before")
                 + f'<span style="color:{p.text_muted};"> → </span>'
                 + pill(p.diff_add_bg, p.diff_add_fg, "chat.diff_after"))
    elif has_add:
        badge = pill(p.diff_add_bg, p.diff_add_fg, "chat.diff_added")
    elif has_del:
        badge = pill(p.diff_del_bg, p.diff_del_fg, "chat.diff_removed")
    else:
        return ""
    return f'<div style="margin-bottom:6px;">{badge}</div>'


def diff_to_html(diff_text: str) -> str:
    """Render a unified diff with GitHub/Claude-Code-style line coloring —
    additions green, deletions red, hunk headers highlighted — plus an
    explicit Before/After (or Added/Removed) legend, instead of a flat text
    block, so a before/after edit reads at a glance. A brand-new file (an
    empty 'before') naturally renders as all-green, which is exactly what
    ``difflib.unified_diff`` already produces for it."""
    legend = _diff_legend(diff_text)
    p = _p()
    rows = []
    for ln in diff_text.splitlines():
        esc = html.escape(ln) if ln else "&nbsp;"
        if ln.startswith(("+++", "---")):
            rows.append(f'<div style="color:{p.text_muted};">{esc}</div>')
        elif ln.startswith("@@"):
            rows.append(f'<div style="color:{p.accent};">{esc}</div>')
        elif ln.startswith("+"):
            rows.append(f'<div style="background:{p.diff_add_bg}; color:{p.diff_add_fg};">{esc}</div>')
        elif ln.startswith("-"):
            rows.append(f'<div style="background:{p.diff_del_bg}; color:{p.diff_del_fg};">{esc}</div>')
        else:
            rows.append(f"<div>{esc}</div>")
    body = "".join(rows) or "(no textual change)"
    return (f'{legend}<div style="font-family:{p.font_mono}; font-size:12.5px; '
            f'white-space:pre-wrap;">{body}</div>')


def format_status_line(base: str, ticks: int) -> str:
    """Animated status line for the working indicator, e.g. ``🤖 Running..`` and,
    once the wait is a few seconds long, ``🤖 Running.   ·   5s`` — so a slow
    synthesis clearly reads as still running. ``ticks`` advances every 500 ms."""
    dots = "." * (ticks % 4)
    secs = ticks // 2
    suffix = f"   ·   {secs}s" if secs >= 3 else ""
    return f"{base}{dots}{suffix}"


class ThinkingIndicator(QWidget):
    """A small animated 'the agent is working' line shown while waiting for a
    result, so a long wait never looks like a frozen / empty screen.

    Renders a bot icon + status (e.g. ``🤖 Running…``) and, once the wait passes
    a few seconds, the elapsed time — so a long synthesis clearly reads as still
    running rather than stuck."""

    def __init__(self):
        """Dòng "đang nghĩ…" hiện trong lúc chờ model trả lời."""
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 2, 14, 4)
        lay.setSpacing(0)
        self._label = QLabel("")
        self._label.setObjectName("hint")
        lay.addWidget(self._label)
        lay.addStretch(1)
        self._base_key = "chat.running"
        self._override: str | None = None
        self._ticks = 0
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._tick)
        self.setVisible(False)
        on_language_changed(self._render)

    def start(self, label_key: str = "chat.running") -> None:
        """Bật chỉ báo "đang nghĩ" kèm nhãn và bộ đếm chấm động."""
        self._base_key = label_key
        self._override = None
        self._ticks = 0
        self._render()
        self.setVisible(True)
        if not self._timer.isActive():
            self._timer.start()

    def set_label(self, label_key: str) -> None:
        """Đổi nhãn đang hiện (ví dụ từ "đang chạy" sang "đang gọi tool")."""
        if label_key != self._base_key:
            self._base_key = label_key
            self._override = None
            self._render()

    def set_progress_text(self, text: str) -> None:
        """Show an already-formatted, literal status line (e.g. a live "reading
        page 12/40" or streamed command-output detail) instead of a translated
        key — used for fine-grained progress within a single step."""
        self._override = text
        self._render()

    def stop(self) -> None:
        """Tắt chỉ báo và dừng bộ đếm."""
        self._timer.stop()
        self._override = None
        self.setVisible(False)

    def _tick(self) -> None:
        """Một nhịp của hiệu ứng chấm động: tăng bộ đếm rồi vẽ lại nhãn."""
        self._ticks += 1
        self._render()

    def _render(self) -> None:
        """Vẽ lại dòng trạng thái: nhãn hiện tại cộng chấm động theo bộ đếm."""
        base = self._override if self._override is not None else tr(self._base_key)
        self._label.setText(format_status_line(base, self._ticks))
