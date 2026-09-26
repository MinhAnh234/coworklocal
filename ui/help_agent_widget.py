"""Floating in-app Help assistant — the app icon pinned to the bottom-right of
the main window, on every screen. Click it to expand a compact chat panel that
greets the user (in the display language) and answers how-to-use-the-app
questions only. A chevron on its left collapses it to a thin tab at the screen
edge when the user doesn't want it visible.

It is deliberately minimal: no tools, no file access, no agent loop — just a
single ``provider.chat`` per message (same pattern as the AI-draft helpers),
scoped by the built-in "help" admin agent's system prompt (see
``core.admin_agents``: task_kind "help"). The agent is managed in Monitoring →
Agents Admin, so the Admin can pick which provider/model answers.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton, QTextBrowser,
    QVBoxLayout, QWidget,
)

from ..core import admin_agents, help_knowledge
from ..core.worker import AgentWorker
from ..i18n import tr
from .icons import icon

_ASSETS = Path(__file__).resolve().parent.parent / "assets"

_MARGIN = 18                       # gap from the window's bottom-right corner
# Closed, the assistant is a single 26px dot. It used to be an 84×64 block (a
# 64px badge plus an 18px "hide" chevron beside it) sitting permanently over the
# bottom-right of every screen — on Cowork, right on top of the Send button —
# for something opened a few times a day. The name now appears on hover only,
# and "hide to the edge" moved into the panel's ⋯ menu.
# The audit page draws this at 26px ("26×26 · không chữ, không chevron").
# Doubled at the user's request: 26 read as too small to notice on a 1920
# screen. Still half the area of the 84×64 button it replaced.
_DOT = 52                          # closed launcher (a round chip)
_DOT_ICON = 28                     # the sparkle inside it
_PILL_PAD = 12                     # extra width for the label when hovered
_TAB_W, _TAB_H = 28, 48            # the "show" tab when hidden at the edge (was 16 wide)
_PANEL_W, _PANEL_H = 340, 460      # expanded chat panel size

# Straight from docs/ui-audit.html (.wf .fab / .fabpill / .spark): the
# assistant is teal, not the app accent, and the same in both themes —
# it is one recognisable object floating over every screen.
_TEAL_BG, _TEAL_LINE = "#E6F6F4", "#7FD0C4"
_TEAL_TEXT = "#0F6E62"
# The page's CSS says .spark{color:#0F9B8A}, but the glyph is the ✨ EMOJI and a
# colour emoji ignores CSS colour — so what the page actually renders is the
# gold star. Sampled from the page's own render of section 27 (1055 pixels of
# the star, averaged): #FDBE59.
_SPARK_GOLD = "#FDBE59"

# The three states the floating assistant cycles through.
_HIDDEN, _LAUNCHER_ST, _PANEL = "hidden", "launcher", "panel"


def _current_user() -> str:
    """Tên đăng nhập hệ điều hành, dùng để chào người dùng; '' nếu không đọc được."""
    return (os.environ.get("USERNAME") or os.environ.get("USER") or "").strip()


def _app_icon() -> QIcon:
    """The app's own icon.png (falls back to the generic robot glyph if the
    asset is somehow missing)."""
    p = _ASSETS / "icon.png"
    return QIcon(str(p)) if p.exists() else icon("robot")


# _app_pixmap()/_IconTap were the 52px icon and its click-through QLabel for the
# old 64px badge. The launcher is a real button now, so both are gone.


class _HoverPill(QPushButton):
    """The closed launcher: a dot at rest, a labelled pill under the pointer.

    Keyboard focus counts as hover, so the name is reachable without a mouse.
    Resizing is delegated to the owner because this widget is inside an overlay
    that has to re-pin itself to the window corner whenever its size changes.
    """

    def __init__(self, owner):
        """Nút tròn nổi ở góc màn hình, mở ra panel Trợ giúp khi bấm."""
        super().__init__(owner)
        self._owner = owner
        self.open = False

    def _set_open(self, value: bool) -> None:
        """Đổi trạng thái bung/co và vẽ lại; đã đúng trạng thái thì bỏ qua."""
        if value == self.open:
            return
        self.open = value
        self.setText(f"  {tr('help_agent.badge')}" if value else "")
        self._owner._layout_launcher()

    def enterEvent(self, e):  # noqa: N802 - Qt override
        """Rê chuột vào: bung ra."""
        self._set_open(True)
        super().enterEvent(e)

    def leaveEvent(self, e):  # noqa: N802 - Qt override
        """Rời chuột: co lại — trừ khi đang giữ focus bàn phím."""
        if not self.hasFocus():
            self._set_open(False)
        super().leaveEvent(e)

    def focusInEvent(self, e):  # noqa: N802 - Qt override
        """Nhận focus bàn phím: bung ra, để người dùng dùng Tab cũng thấy được nhãn."""
        self._set_open(True)
        super().focusInEvent(e)

    def focusOutEvent(self, e):  # noqa: N802 - Qt override
        """Mất focus: co lại."""
        self._set_open(False)
        super().focusOutEvent(e)


class HelpAgentWidget(QWidget):
    """Overlay child of the main window; anchors itself bottom-right and cycles
    hidden-tab → launcher icon → expanded chat panel."""

    status_message = Signal(str)

    def __init__(self, ctx, parent=None, user_name: str = ""):
        """Trợ lý Trợ giúp trong ứng dụng.

        Giữ lịch sử hội thoại riêng (không kèm prompt hệ thống — cái đó ghép vào ở
        mỗi lượt gọi) để người dùng hỏi tiếp mà không phải nhắc lại bối cảnh.
        """
        super().__init__(parent)
        self.ctx = ctx
        self._user_name = user_name or _current_user()
        self._state = _LAUNCHER_ST
        self._busy = False
        self._worker: Optional[AgentWorker] = None
        # Conversation history (excludes the system prompt, prepended per call).
        # Seeded with the greeting so the panel always opens on a friendly hello.
        # Kept by identity so retranslate() can rewrite it without having to
        # guess which language the visible text is in — and without touching a
        # real reply that happens to look like a greeting.
        self._greet_msg: Dict[str, str] = {
            "role": "assistant", "content": self._greeting()}
        self._history: List[Dict[str, str]] = [self._greet_msg]
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._pal = self._compute_palette()
        self._build_edge_tab()
        self._build_launcher()
        self._build_panel()
        self._apply_style()
        self._apply_state()

    # ---- theming ----------------------------------------------------------
    def _compute_palette(self):
        """The app's design tokens for the theme in effect. The whole dock —
        header included — follows the app theme; a header locked to a light
        strip stranded a bright bar in the middle of the dark UI."""
        from ..theme import palette
        return palette(getattr(self.ctx.config, "theme", "system"))

    def apply_theme(self) -> None:
        """Re-style + re-render when the app theme switches (called from
        MainWindow._apply_theme). The whole dock re-colours, icons included —
        icons are painted bitmaps, so they must be rebuilt, not restyled."""
        self._pal = self._compute_palette()
        self._apply_style()
        muted = self._pal.text_muted
        self.edge_tab.setIcon(icon("chevron-left", color=_TEAL_TEXT))
        self.launcher.setIcon(icon("sparkle", size=_DOT_ICON, color=_SPARK_GOLD))
        self.min_btn.setIcon(icon("minus", color=muted))
        self._render()

    def _apply_style(self) -> None:
        """The dock owns its own style sheet (it floats above the window, so the
        app-wide sheet does not reach it cleanly) but draws every value from the
        shared tokens — see theme.py."""
        p = self._pal
        r, rl = p.radius, p.radius_lg
        self.setStyleSheet(f"""
            /* Closed launcher: a {_DOT}px dot. `pill` flips to true on hover, when
               the label comes out and the shape stretches to a rounded bar. */
            #helpLauncher {{ background: {_TEAL_BG}; border: 1px solid {_TEAL_LINE};
                border-radius: {_DOT // 2}px; color: {_TEAL_TEXT}; font-weight: 700;
                font-size: 12px; padding: 0; text-align: center; }}
            #helpLauncher[pill="true"] {{ text-align: left; padding-left: 6px; }}
            #helpLauncher:hover {{ background: #D5EFEA; border-color: {_TEAL_LINE}; }}
            #helpLauncher:focus {{ border: 1px solid {_TEAL_TEXT}; }}
            #helpEdgeTab {{ background: {_TEAL_BG}; border: 1px solid {_TEAL_LINE};
                border-right: none; border-top-left-radius: {r}px;
                border-bottom-left-radius: {r}px; }}
            #helpEdgeTab:hover {{ background: #D5EFEA; }}
            #helpPanel {{ background: {p.surface}; border: 1px solid {p.border};
                border-radius: {rl}px; color: {p.text}; }}
            #helpHeader {{ background: {p.surface}; border-bottom: 1px solid {p.border};
                border-top-left-radius: {rl}px; border-top-right-radius: {rl}px; }}
            #helpHeader QLabel {{ background: transparent; color: {p.text}; }}
            #helpTitle {{ color: {p.text}; font-weight: 600; font-size: 13px;
                background: transparent; }}
            #helpMinBtn {{ background: transparent; border: none; border-radius: {r}px; }}
            #helpMinBtn:hover {{ background: {p.hover}; }}
            #helpLog {{ background: {p.sunken}; border: none; color: {p.text};
                padding: 4px 6px; }}
            #helpInputRow {{ background: {p.surface};
                border-bottom-left-radius: {rl}px; border-bottom-right-radius: {rl}px; }}
            #helpInput {{ border: 1px solid {p.border}; border-radius: {r}px; padding: 5px 8px;
                background: {p.surface_raised}; color: {p.text}; }}
            #helpInput:focus {{ border: 1px solid {p.focus_ring}; }}
            #helpSendBtn {{ background: {p.accent_solid}; border: none; border-radius: {r}px; }}
            #helpSendBtn:hover {{ background: {p.accent_solid_hover}; }}
            #helpSendBtn:disabled {{ background: {p.border_strong}; }}
        """)

    # ---- greeting / labels ------------------------------------------------
    def _greeting(self) -> str:
        """Câu chào mở đầu, có tên người dùng nếu biết."""
        return help_knowledge.greeting(self._user_name)

    # ---- construction -----------------------------------------------------
    def _build_edge_tab(self) -> None:
        # Shown only while hidden: a thin tab at the right edge to bring the
        # assistant back (chevron points left = "slide out").
        """Dựng thẻ mỏng ở mép phải — chỉ hiện khi trợ lý đang ẩn hẳn, bấm vào để gọi lại."""
        self.edge_tab = QPushButton(self)
        self.edge_tab.setObjectName("helpEdgeTab")
        self.edge_tab.setIcon(icon("chevron-left", color=_TEAL_TEXT))
        self.edge_tab.setCursor(Qt.PointingHandCursor)
        self.edge_tab.setToolTip(tr("help_agent.show_tooltip"))
        self.edge_tab.clicked.connect(self._show_launcher)

    def _build_launcher(self) -> None:
        # One control, one job: this opens the chat. The chevron that used to sit
        # beside it (a second 18px hit target for a second meaning of "closed")
        # is gone — hiding to the edge is now a line in the panel's ⋯ menu.
        """Dựng nút mở chat.

        Một nút, một việc: mở khung chat. Cái chevron từng đứng cạnh nó (thêm một
        vùng bấm 18px cho một nghĩa "đóng" thứ hai) đã bỏ — muốn ẩn hẳn thì vào
        menu ⋯ của panel.
        """
        self.launcher = _HoverPill(self)
        self.launcher.setObjectName("helpLauncher")
        self.launcher.setIcon(icon("sparkle", size=_DOT_ICON, color=_SPARK_GOLD))
        self.launcher.setCursor(Qt.PointingHandCursor)
        self.launcher.setToolTip(
            f'{tr("help_agent.open_tooltip")} · {tr("help_agent.dot_hint")}')
        self.launcher.clicked.connect(self._expand)
        # Kéo nút đi đâu cũng được; bấm (không kéo) vẫn mở chat như cũ.
        from ..presentation.shell.help_dock_drag import DockDragger
        self._drag = DockDragger(self, self.launcher, margin=_MARGIN)

    def _build_panel(self) -> None:
        """Dựng panel chat: dòng thời gian, ô nhập, nút gửi và menu ⋯."""
        self.panel = QFrame(self)
        self.panel.setObjectName("helpPanel")

        v = QVBoxLayout(self.panel)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # Header: app icon + title + minimize (plain white bar, no colour fill)
        header = QFrame(self.panel)
        header.setObjectName("helpHeader")
        hb = QHBoxLayout(header)
        hb.setContentsMargins(12, 8, 8, 8)
        self.title_icon = QLabel(header)
        self.title_icon.setPixmap(
            icon("sparkle", size=16, color=_SPARK_GOLD).pixmap(16, 16))
        hb.addWidget(self.title_icon)
        self.title = QLabel(tr("help_agent.title"), header)
        self.title.setObjectName("helpTitle")
        hb.addWidget(self.title, 1)
        self.min_btn = QPushButton(header)
        self.min_btn.setObjectName("helpMinBtn")
        self.min_btn.setIcon(icon("minus", color=self._pal.text_muted))
        self.min_btn.setFixedSize(24, 24)
        self.min_btn.setCursor(Qt.PointingHandCursor)
        self.min_btn.setToolTip(tr("help_agent.collapse_tooltip"))
        self.min_btn.clicked.connect(self._collapse)
        hb.addWidget(self.min_btn)
        # No ⋯ menu. The audit page put "Ẩn trợ lý" in one, but its two entries
        # were "thu nhỏ" — which the − button beside it already does — and
        # "ẩn vào cạnh phải". A drop-list to reach one action that duplicates
        # its neighbour is chrome; removed at the user's request.
        #
        # Hiding stays reachable by right-click, on the header while the panel
        # is open and on the dot while it is shut, so no route is lost.
        for target in (header, self.launcher):
            target.setContextMenuPolicy(Qt.CustomContextMenu)
            target.customContextMenuRequested.connect(
                lambda pos, w=target: self._hide_menu(w, pos))
        v.addWidget(header)

        # Conversation log
        self.log = QTextBrowser(self.panel)
        self.log.setObjectName("helpLog")
        self.log.setOpenExternalLinks(False)
        v.addWidget(self.log, 1)

        # Input row
        row = QFrame(self.panel)
        row.setObjectName("helpInputRow")
        rb = QHBoxLayout(row)
        rb.setContentsMargins(8, 8, 8, 8)
        rb.setSpacing(6)
        self.input = QLineEdit(row)
        self.input.setObjectName("helpInput")
        self.input.setPlaceholderText(tr("help_agent.placeholder"))
        self.input.returnPressed.connect(self._send)
        rb.addWidget(self.input, 1)
        self.send_btn = QPushButton(row)
        self.send_btn.setObjectName("helpSendBtn")
        self.send_btn.setIcon(icon("send"))
        self.send_btn.setFixedSize(32, 30)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self._send)
        rb.addWidget(self.send_btn)
        v.addWidget(row)

        self._render()

    # ---- state transitions ------------------------------------------------
    def _expand(self) -> None:
        """Mở panel chat đầy đủ và đưa con trỏ vào ô nhập."""
        self._state = _PANEL
        self._apply_state()
        self.input.setFocus()

    def _collapse(self) -> None:
        """Thu panel về nút tròn."""
        self._state = _LAUNCHER_ST
        self._apply_state()

    def _hide_menu(self, widget, pos) -> None:
        """Right-click, on the dot or the open panel's header: hide to the edge.

        The only action worth offering here — collapsing is what the − button
        and the dot itself already are.
        """
        from PySide6.QtWidgets import QMenu

        menu = QMenu(widget)
        act = menu.addAction(tr("help_agent.hide_tooltip"))
        act.triggered.connect(self._hide_to_edge)
        menu.exec(widget.mapToGlobal(pos))

    def _hide_to_edge(self) -> None:
        """Ẩn hẳn trợ lý, chỉ chừa thẻ mỏng ở mép phải."""
        self._state = _HIDDEN
        self._apply_state()

    def _show_launcher(self) -> None:
        """Gọi trợ lý trở lại từ trạng thái ẩn."""
        self._state = _LAUNCHER_ST
        self._apply_state()

    def _layout_launcher(self) -> None:
        """Size the overlay to the dot, or to the pill while it is hovered."""
        w = _DOT
        if self.launcher.open:
            w = max(_DOT, self.launcher.fontMetrics()
                    .horizontalAdvance(self.launcher.text()) + _DOT + _PILL_PAD)
        self.resize(w, _DOT)
        self.launcher.setGeometry(0, 0, w, _DOT)
        # Round while it is a dot, pill-shaped once the label is out.
        self.launcher.setProperty("pill", bool(self.launcher.open))
        self.launcher.style().unpolish(self.launcher)
        self.launcher.style().polish(self.launcher)
        self.reposition()
        self.raise_()

    def _apply_state(self) -> None:
        """Áp trạng thái hiện tại lên ba thành phần: thẻ mép, nút tròn và panel."""
        st = self._state
        self.edge_tab.setVisible(st == _HIDDEN)
        self.launcher.setVisible(st == _LAUNCHER_ST)
        self.panel.setVisible(st == _PANEL)
        if st == _PANEL:
            self.resize(_PANEL_W, _PANEL_H)
            self.panel.setGeometry(0, 0, _PANEL_W, _PANEL_H)
        elif st == _LAUNCHER_ST:
            self._layout_launcher()
            return                      # _layout_launcher repositions and raises
        else:  # hidden
            self.resize(_TAB_W, _TAB_H)
            self.edge_tab.setGeometry(0, 0, _TAB_W, _TAB_H)
        self.reposition()
        self.raise_()

    # A screen whose bottom edge is an input row (Cowork's composer) must not
    # have the dock sitting on top of it — set by MainWindow when the page
    # changes, in window coordinates.
    _bottom_guard = 0

    def set_bottom_guard(self, height: int) -> None:
        """Reserve `height` px at the foot of the window for the page's own
        controls; the dock floats above it instead of over the Send button."""
        if height != self._bottom_guard:
            self._bottom_guard = max(0, height)
            self.reposition()

    def reposition(self) -> None:
        """Đặt lại chỗ khi cửa sổ đổi cỡ: chỗ người dùng đã kéo tới, mặc định là
        góc dưới-phải (xem presentation/shell/help_dock_drag.py)."""
        self._drag.place()

    # ---- rendering --------------------------------------------------------
    def _bubble_html(self, who: str, content: str) -> str:
        """One message as a clearly-separated, labelled bubble: the user's turns
        sit right-aligned with an accent tint, the assistant's left-aligned on a
        neutral fill, each headed by its speaker name — so who said what is never
        ambiguous. (QTextDocument has no border-radius, so filled table cells do
        the bubble work.)"""
        p = self._pal
        text = (content or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        text = text.replace("\n", "<br>")
        # bgcolor= is a solid-only HTML attribute, hence accent_wash (pre-blended)
        # rather than the translucent accent_soft used in style sheets.
        if who == "user":
            align, bg, label_color = "right", p.accent_wash, p.accent
            label = tr("chat.you")
        else:
            align, bg, label_color = "left", p.surface_raised, p.success
            label = tr("help_agent.title")
        return (
            f'<table width="100%" cellspacing="0" cellpadding="0"><tr>'
            f'<td align="{align}">'
            f'<table width="80%" cellspacing="0" cellpadding="7" bgcolor="{bg}"><tr>'
            f'<td style="color:{p.text};">'
            f'<b style="color:{label_color};">{label}</b><br>{text}'
            f'</td></tr></table></td></tr></table>'
            '<div style="line-height:6px;">&nbsp;</div>'   # gap between turns
        )

    def _render(self, pending: bool = False) -> None:
        """Dựng lại toàn bộ dòng thời gian dưới dạng HTML.

        ``pending=True`` thêm một bong bóng "…" để báo đang chờ trả lời.
        """
        parts = [self._bubble_html(m["role"], m["content"]) for m in self._history]
        if pending:
            parts.append(self._bubble_html("assistant", "…"))
        self.log.setHtml("".join(parts))
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    # ---- send a message ---------------------------------------------------
    def _send(self) -> None:
        """Gửi câu hỏi tới Help Agent ở luồng nền."""
        if self._busy:
            return
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self._history.append({"role": "user", "content": text})
        self._set_busy(True)
        self._render(pending=True)

        agent = admin_agents.ensure_help_agent(
            admin_agents.agents_admin_dir(self.ctx.config.shared_dir))
        history = list(self._history)
        sys_prompt = help_knowledge.build_prompt(agent.effective_prompt(), getattr(self.parent(), "help_context", lambda: "")())

        def job(worker):
            """Chạy nền: gọi provider của Help Agent kèm prompt hệ thống của nó."""
            provider = admin_agents.build_agent_provider(self.ctx, agent)
            messages = [{"role": "system", "content": sys_prompt}] + history
            result = provider.chat(messages, tools=None, cancel=worker.is_cancelled)
            content = result.get("content", "") if isinstance(result, dict) else str(result)
            return {"content": provider.strip_think(content) or ""}

        worker = AgentWorker(job)
        worker.finished_ok.connect(self._on_reply)
        worker.failed.connect(self._on_failed)
        self._worker = worker
        worker.start()

    def _on_reply(self, result: Dict[str, Any]) -> None:
        """Nhận trả lời và vẽ vào dòng thời gian; rỗng thì hiện câu thay thế."""
        content = (result or {}).get("content", "").strip() or tr("help_agent.empty_reply")
        self._history.append({"role": "assistant", "content": content})
        self._set_busy(False)
        self._render()

    def _on_failed(self, err: str) -> None:
        """Gọi lỗi: hiện thông báo lỗi ngay trong khung chat thay vì im lặng."""
        self._history.append({"role": "assistant",
                              "content": tr("help_agent.error", error=err)})
        self._set_busy(False)
        self._render()

    def _set_busy(self, busy: bool) -> None:
        """Khoá/mở ô nhập và nút gửi trong lúc chờ trả lời."""
        self._busy = busy
        self.input.setEnabled(not busy)
        self.send_btn.setEnabled(not busy)

    def retranslate(self) -> None:
        # The transcript is rendered HTML, so switching language left the
        # greeting — and every "AI Assistant" speaker label — in the language
        # the panel was built in.
        """Áp lại chữ theo ngôn ngữ đang chọn.

        Dòng thời gian là HTML đã dựng sẵn, nên đổi ngôn ngữ mà không dựng lại sẽ
        để câu chào — và mọi nhãn người nói "AI Assistant" — nằm nguyên ở ngôn ngữ
        lúc panel được tạo.
        """
        if self._history and self._history[0] is self._greet_msg:
            self._greet_msg["content"] = self._greeting()
        self._render()
        self.title.setText(tr("help_agent.title"))
        self.input.setPlaceholderText(tr("help_agent.placeholder"))
        self.launcher.setToolTip(
            f'{tr("help_agent.open_tooltip")} · {tr("help_agent.dot_hint")}')
        if self.launcher.open:
            self.launcher.setText(f"  {tr('help_agent.badge')}")
            self._layout_launcher()
        self.min_btn.setToolTip(tr("help_agent.collapse_tooltip"))
        self.edge_tab.setToolTip(tr("help_agent.show_tooltip"))
