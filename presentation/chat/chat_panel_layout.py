"""Bố cục khung chat — R08-T06.

Hai cột: mạch hội thoại bên trái, khung tệp đầu ra bên phải. Ô nhập nằm dưới
CẢ HAI cột — đó là lý do khung tệp đứng cạnh mạch hội thoại mà không làm hẹp
chỗ gõ. Đặt trong cột chat thì ô nhập co lại mỗi lần có tệp xuất hiện.

Vài widget cố ý được gắn vào một cha ẩn vĩnh viễn thay vì bỏ hẳn: khung tệp
đầu vào và bảng kế hoạch cũ vẫn còn được gọi ``set_steps``/``add`` ở nơi
khác. Không có cha thì lần gọi đầu tiên sẽ bật lên thành một cửa sổ nổi lạc
lõng giữa màn hình.

Cùng kiểu mixin, xem ghi chú ở đầu ``presentation/shell/nav_rail.py``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtCore import QFileSystemWatcher
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QSplitter,
    QVBoxLayout, QWidget,
)
from ...core.worker import AgentWorker
from ...i18n import on_language_changed, tr
from ...state import AppContext
from ...theme import current_palette
from .chat_bubble_style import ThinkingIndicator
from .chat_history_widget import ChatView
from .chat_welcome import ChatWelcome
from .composer_widget import Composer
from ...ui.icons import collapse_right_icon, icon as app_icon
from ...ui.osutil import is_image, open_path
from ...ui.widgets import CollapsibleSection, CollapseStrip, PlanSection


class ChatPanelLayoutMixin:
    """Dựng bố cục. Trộn vào ChatPanel."""

    def _build_layout(self, root) -> None:
        """``root`` là QVBoxLayout gốc do ``__init__`` dựng."""
        # Chat column: transcript expands, the chat box is pinned at the bottom.
        chat_col = QWidget()
        cc = QVBoxLayout(chat_col)
        cc.setContentsMargins(0, 0, 0, 0)
        cc.setSpacing(0)
        # Man gioi thieu chiem dung cho cua khung chat va thay the no khi hoi
        # thoai con rong — hai thu khong bao gio cung hien.
        self.welcome = ChatWelcome()
        self.welcome.suggestion_picked.connect(self._use_suggestion)
        cc.addWidget(self.welcome, 1)
        cc.addWidget(self.chat_view, 1)
        self.chat_view.hide()      # phien moi thi rong -> man gioi thieu di truoc
        self.thinking = ThinkingIndicator()   # animated "working…" line while we wait
        cc.addWidget(self.thinking)
        self.center_split = QSplitter(Qt.Horizontal)
        self.center_split.addWidget(chat_col)
        root.addWidget(self.center_split, 1)

        # The composer spans the whole screen, under BOTH columns — that is how
        # the drawing lays it out, and it is the reason the files panel can sit
        # beside the transcript without narrowing what you type into. Inside the
        # chat column it stopped at the panel's edge and the input shrank
        # whenever files appeared.
        composer_wrap = QWidget()
        cwl = QVBoxLayout(composer_wrap)
        cwl.setContentsMargins(8, 4, 8, 8)
        cwl.addWidget(self.composer)
        root.addWidget(composer_wrap)

        # Right sidebar: Output files only (see below — Input is tracked but
        # not shown).
        self.input_section = CollapsibleSection(tr("widgets.input_files"))
        # No cap: this section owns the whole right panel (its header is
        # hoisted into io_hdr below), so the list should fill the space down
        # to the composer instead of stopping at a fixed height with empty
        # panel below it.
        self.output_section = CollapsibleSection(tr("widgets.output_files").upper(), max_height=None)
        # Input files are NOT shown in Cowork's UI anymore — but they're still
        # fully tracked (add/remove/paths()) exactly as before, since that list
        # is what gets written into the conversation's own "inputs" field on
        # save (kept alongside the conversation; nothing here deletes the
        # user's actual files — the conversation JSON itself only disappears
        # when the conversation is deleted, same as always). Give input_section
        # a real, permanently-hidden PARENT (not just "never added to a layout")
        # so its own internal auto-show-on-add() call can never pop it up as a
        # stray floating window.
        self._input_hidden_host = QWidget(self)
        self._input_hidden_host.setVisible(False)
        _hh_lay = QVBoxLayout(self._input_hidden_host)
        _hh_lay.setContentsMargins(0, 0, 0, 0)
        _hh_lay.addWidget(self.input_section)
        self.plan_section = PlanSection(tr("widgets.plan_title"))   # live step checklist, above the Files panel
        # The plan is shown INLINE in the conversation now (see add_plan), so this
        # legacy right-panel checklist is parked inside the permanently-hidden
        # host. Without a parent it would pop as a stray top-level "Plan (N)"
        # window the moment set_steps() made it visible — parenting it here keeps
        # its set_steps/clear calls truly inert (a hidden ancestor never renders).
        _hh_lay.addWidget(self.plan_section)
        self.input_section.activated.connect(self._open_io_item)
        self.output_section.activated.connect(self._open_io_item)
        # Right-click a file → Open / "View & AI Edit" (in-app viewer+editor).
        for section in (self.input_section, self.output_section):
            section.list.setContextMenuPolicy(Qt.CustomContextMenu)
            section.list.customContextMenuRequested.connect(
                lambda pos, s=section: self._io_context_menu(s, pos))
        self._io_widget = QWidget()
        iol = QVBoxLayout(self._io_widget)
        iol.setContentsMargins(6, 6, 6, 6)
        iol.setSpacing(4)
        io_hdr = QHBoxLayout()
        self._io_collapse_btn = QPushButton()
        self._io_collapse_btn.setIcon(collapse_right_icon())
        self._io_collapse_btn.setFixedWidth(28)
        self._io_collapse_btn.clicked.connect(lambda: self._set_io_collapsed(True))
        self._files_header = QLabel()
        self._files_header.setStyleSheet("font-weight:600;")
        # The drawing gives this panel ONE heading — "TỆP ĐẦU RA (3) ›" — and
        # the section already draws exactly that, count included. A separate
        # "Files" label above it was the same thing said twice, so the section's
        # own header moves onto this row and the collapse chevron sits at its
        # right, where the drawing puts it. _files_header stays for the tabs
        # that still label their panel, just not in this layout.
        self._files_header.setVisible(False)
        io_hdr.addWidget(self.output_section.header, 1)
        io_hdr.addWidget(self._io_collapse_btn)
        # The plan now shows INLINE in the conversation (an expandable block whose
        # steps tick off as they complete), not in this right panel — so it's kept
        # out of the layout here. The object stays (its set_steps/clear calls are
        # harmless no-ops on a hidden widget).
        self.plan_section.setVisible(False)
        iol.addLayout(io_hdr)
        bl_host = QWidget()
        bl = QVBoxLayout(bl_host)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(4)
        bl.addWidget(self.output_section, 1)   # Output only — Input is tracked but hidden; fills down to the composer
        iol.addWidget(bl_host, 1)

        # Collapsing shrinks the panel to a thin clickable line (not hidden).
        # The collapse button lives in the panel header; the strip re-expands.
        self._io_strip = CollapseStrip(tr("chatpanel.expand_files_tooltip"), expand_dir="left")
        self._io_strip.clicked.connect(lambda: self._set_io_collapsed(False))
        self._io_strip.setVisible(False)
        self._io_pane = QWidget()
        pl = QHBoxLayout(self._io_pane)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(0)
        pl.addWidget(self._io_strip)
        pl.addWidget(self._io_widget, 1)

        self.center_split.addWidget(self._io_pane)
        self.center_split.setStretchFactor(0, 1)
        self.center_split.setStretchFactor(1, 0)
        self.center_split.setChildrenCollapsible(False)
        self.center_split.setSizes([820, 220])
        on_language_changed(self._retranslate_base)

    # ---- man gioi thieu ----------------------------------------------------
    def _use_suggestion(self, text: str) -> None:
        """Thẻ gợi ý được bấm: ĐIỀN vào ô nhập, không gửi luôn.

        Câu gợi ý là điểm bắt đầu — người dùng gần như luôn cần thêm chi tiết
        của riêng họ, và gửi ngay sẽ tiêu một lượt gọi model cho một câu hỏi
        chung chung.
        """
        self.composer.input.setPlainText(text)
        self.composer.input.setFocus()

    def show_welcome(self, show: bool) -> None:
        """Bật màn giới thiệu (hội thoại rỗng) hoặc khung chat (đã có tin)."""
        welcome = getattr(self, "welcome", None)
        if welcome is None:
            return
        welcome.setVisible(show)
        self.chat_view.setVisible(not show)
        if show:
            welcome.refresh(**self._welcome_context())

    def _welcome_context(self) -> dict:
        """Dữ liệu cho dòng bối cảnh. Không biết thì trả -1, KHÔNG trả 0.

        Hiện "0 tệp" khi người dùng vừa nhìn thấy tệp trong thư mục còn tệ hơn
        là bỏ mảnh đó khỏi dòng meta.
        """
        from pathlib import Path as _P

        ten = ""
        try:
            from ...core.projects import load_project
            project = load_project(self.project_id) if getattr(self, "project_id", "") else None
            ten = project.name if project is not None else ""
        except Exception:                                    # noqa: BLE001
            ten = ""

        so_tep = -1
        try:
            folder = self.workspace_dir()
            if folder is not None and _P(folder).is_dir():
                so_tep = sum(1 for f in _P(folder).rglob("*")
                             if f.is_file() and f.suffix.lower() in self._INPUT_EXTS)
        except Exception:                                    # noqa: BLE001
            so_tep = -1

        # Ten nguoi dung do cua so chinh giu (app.py truyen xuong MainWindow).
        window = self.window()
        return {"user_name": getattr(window, "_user_name", "") or "",
                "project": ten, "files": so_tep}
