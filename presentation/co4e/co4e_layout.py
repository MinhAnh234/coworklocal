"""Bố cục ba khung và bảng cấu hình node — R08-T09.

Co4E có bốn lớp điều hướng chồng nhau (dải flow, tab icon bên phải, bảng cấu
hình, canvas). Phần quyết định cái nào hiện lúc nào nằm ở đây, tách khỏi phần
hành vi để sửa bố cục không phải đọc logic chạy flow.

``_apply_narrow_layout`` là chỗ đáng chú ý: màn hẹp thì bảng cấu hình chuyển
từ khung cố định sang lớp phủ, vì ba khung cạnh nhau không vừa 1280px.
"""
from __future__ import annotations

import re
from typing import List
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QSizePolicy, QSpacerItem, QSplitter, QTabBar, QTabWidget, QVBoxLayout, QWidget
from ...core import co4e
from ...i18n import bind_text, tr
from ...theme import current_palette
from ...ui.co4e_canvas import Co4ECanvas
from ...ui.icons import icon
from ...presentation.co4e.co4e_run_control_widget import RunsPagePanel


class Co4ELayoutMixin:
    """Bố cục ba cột của Co4E Studio: cột trái, khung vẽ ở giữa, bảng thuộc tính
    bên phải — cùng dải tab luồng phía trên.
    """
    def _build_center(self) -> QWidget:
        """Dựng vùng giữa: dải tab luồng, khung vẽ và trang Flow Status xếp chồng."""
        from PySide6.QtWidgets import QStackedWidget, QTabBar
        page = QWidget()
        lay = QVBoxLayout(page)

        # Flow tab bar: a pinned "Runs" tab first (manage every flow run), then a
        # browser-style tab per open flow — each keeps its own graph (no mixing).
        self.flow_bar = QTabBar()
        self.flow_bar.setObjectName("flowTabs")
        self.flow_bar.setTabsClosable(True)
        self.flow_bar.setMovable(True)
        self.flow_bar.setExpanding(False)
        self.flow_bar.setDrawBase(False)
        # No arrow scroll buttons — when the tabs overflow they scroll inside a
        # frameless horizontal scroller you drag left/right (see flow_row below).
        self.flow_bar.setUsesScrollButtons(False)
        # Tab colours + layout live in theme.py (QTabBar#flowTabs — theme-aware,
        # flush, centred). Here we only style the per-tab close (✕) button, which
        # QTabBar places centred on the tab's right (see _add_tab_close_button).
        _fp = current_palette()
        self.flow_bar.setStyleSheet(
            "QPushButton#flowTabClose {"
            f" border: none; background: transparent; color: {_fp.text_muted};"
            " font-size: 13px; font-weight: bold; padding: 0; margin: 0;"
            f" border-radius: {_fp.radius_sm}px; }}"
            "QPushButton#flowTabClose:hover {"
            f" background: {_fp.danger_soft}; color: {_fp.danger}; }}")
        runs_idx = self.flow_bar.addTab(icon("monitoring"), tr("co4e.runs_tab"))  # 0 = Runs
        self.flow_bar.setTabButton(runs_idx, QTabBar.RightSide, None)             # pinned
        self.flow_bar.currentChanged.connect(self._on_flow_tab_changed)
        self.flow_bar.tabCloseRequested.connect(self._close_flow_tab)
        # "+" new-flow button styled as the last tab in the strip (browser-style)
        # — the ＋ glyph sits inside a tab-shaped button flush with the tabs.
        self.flow_add_btn = QPushButton("＋")
        self.flow_add_btn.setObjectName("flowAddBtn")
        self.flow_add_btn.setFixedWidth(34)
        self.flow_add_btn.setToolTip(tr("co4e.tt_new_wf"))
        self.flow_add_btn.clicked.connect(self._new_workflow)
        # Frameless horizontal scroller around the tab strip: overflowing tabs
        # scroll (drag) left/right instead of being boxed with arrow buttons.
        # The tab bar AND the "+" button are pinned to the SAME fixed height —
        # giving the scroll area extra height for its scrollbar (as a previous
        # version did) left the tabs top-anchored inside a taller box while the
        # "+" button centered across that whole (taller) box, so the two drifted
        # out of alignment. Same height on both = always aligned, no centering
        # math needed; the scrollbar only appears on overflow (rare) and briefly
        # overlaps the tab strip's bottom edge in that case.
        _tab_h = self.flow_bar.sizeHint().height()
        self.flow_bar.setFixedHeight(_tab_h)
        self.flow_add_btn.setFixedHeight(_tab_h)
        self.flow_scroll = QScrollArea()
        self.flow_scroll.setObjectName("flowTabScroll")
        self.flow_scroll.setWidget(self.flow_bar)
        self.flow_scroll.setWidgetResizable(True)
        self.flow_scroll.setFrameShape(QScrollArea.NoFrame)     # no outer frame
        self.flow_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.flow_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.flow_scroll.setFixedHeight(_tab_h)
        self.flow_scroll.setStyleSheet(
            "QScrollArea#flowTabScroll { background: transparent; border: none; }"
            "QScrollArea#flowTabScroll QScrollBar:horizontal { height: 8px; background: transparent; margin: 0; }"
            "QScrollArea#flowTabScroll QScrollBar::handle:horizontal {"
            f" background: {current_palette().scroll_handle}; border-radius: 4px; min-width: 30px; }}"
            "QScrollArea#flowTabScroll QScrollBar::add-line:horizontal,"
            "QScrollArea#flowTabScroll QScrollBar::sub-line:horizontal { width: 0; height: 0; }")
        # The strip itself is NOT shown any more (see class docstring): flows are
        # picked from the WORKFLOWS list on the left, one open at a time. The
        # QTabBar stays alive off-screen as the index that maps flow ↔ canvas —
        # every open/close/rename path already goes through it — but the user
        # never sees or drives it.
        self.flow_scroll.setVisible(False)
        self.flow_add_btn.setVisible(False)

        # Content switches between the Runs table (tab 0) and the flow editor.
        self.center_stack = QStackedWidget()
        lay.addWidget(self.center_stack, 1)
        self.center_stack.addWidget(self._build_runs_page())          # stack 0 = Runs

        flow_page = QWidget()
        lay = QVBoxLayout(flow_page)
        lay.setContentsMargins(0, 0, 0, 0)

        bar = QHBoxLayout(); bar.setSpacing(5)
        self.name_edit = QLineEdit(self._wf.name)
        self.name_edit.setToolTip(tr("co4e.tt_flow_name"))
        self.name_edit.textChanged.connect(self._on_name_changed)
        # "Add" is a labelled button (not a "+" icon) so it isn't mistaken for
        # the zoom-in control, which now lives in the canvas's bottom-left overlay.
        self.add_step_btn = QPushButton(tr("co4e.add")); self.add_step_btn.setIcon(icon("plus"))
        self.add_step_btn.setToolTip(tr("co4e.tt_add_step"))
        self.add_step_btn.clicked.connect(self._add_blank_step)
        self.save_btn = QPushButton(tr("co4e.save")); self.save_btn.setIcon(icon("save"))
        self.save_btn.setObjectName("primary")
        self.save_btn.setToolTip(tr("co4e.tt_save"))
        self.save_btn.clicked.connect(lambda: self._save(as_template=False))
        self.save_tpl_btn = self._icon_btn("star", "co4e.tt_save_template",
                                           lambda: self._save(as_template=True))
        self.mode_combo = QComboBox()
        self.mode_combo.setToolTip(tr("co4e.tt_mode"))
        for m in co4e.RUN_MODES:
            self.mode_combo.addItem(tr(f"co4e.mode.{m}"), m)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self.run_btn = QPushButton(tr("co4e.run")); self.run_btn.setIcon(icon("play"))
        self.run_btn.setObjectName("primary")
        self.run_btn.setToolTip(tr("co4e.tt_run"))
        self.run_btn.clicked.connect(self._on_run_clicked)

        # The pinned "Runs" tab lost its strip, so it becomes a toggle here —
        # one click to the run table and one click back, from either page.
        self.runs_btn = QPushButton(tr("co4e.runs_tab"))
        self.runs_btn.setIcon(icon("monitoring"))
        self.runs_btn.setCheckable(True)
        self.runs_btn.setToolTip(tr("co4e.tt_runs_tab"))
        self.runs_btn.toggled.connect(self._show_runs)

        # Bound: nothing else holds this label, so a one-shot tr() here would
        # leave "Flow" stuck in the language the toolbar was built in.
        bar.addWidget(bind_text(QLabel(), "co4e.flow_name"))
        bar.addWidget(self.name_edit, 1)
        bar.addWidget(self.add_step_btn)
        bar.addWidget(self.save_btn)
        bar.addWidget(self.save_tpl_btn)
        bar.addWidget(self.mode_combo)
        bar.addWidget(self.run_btn)
        bar.addWidget(self.runs_btn)
        lay.addLayout(bar)

        self.canvas = Co4ECanvas()
        self._build_canvas_overlay()
        vsplit = QSplitter(Qt.Vertical)
        vsplit.addWidget(self.canvas)
        chat_widget = self._build_chat()          # default-collapsed (see _build_chat)
        vsplit.addWidget(chat_widget)
        vsplit.setStretchFactor(0, 1)
        self._vsplit = vsplit           # so the message panel can collapse/expand
        # Messages start collapsed — give the canvas the room from the start,
        # not the [540, 220] split that assumed an expanded chat box.
        collapsed_h = chat_widget.maximumHeight()
        vsplit.setSizes([max(0, 760 - collapsed_h), collapsed_h])
        lay.addWidget(vsplit, 1)
        self.center_stack.addWidget(flow_page)                       # stack 1 = flow editor
        self.center_stack.setCurrentIndex(1)
        return page
    def _build_runs_page(self) -> QWidget:
        """The pinned 'Runs' tab: a table of every flow run (name · status · steps
        done/total · creator · created) for tracking. Double-click a run to open
        that flow's tab with its live status.

        Widget construction lives in ``RunsPagePanel`` (presentation/co4e/
        co4e_run_control_widget.py); this method just wires the panel's public
        attributes to the handler methods that know about ``self`` (``_show_runs``,
        ``_stop_selected_run``, ...) — the panel itself stays ignorant of ``Co4ETab``.
        """
        panel = RunsPagePanel()
        self.runs_back_btn = panel.back_btn
        self.runs_back_btn.clicked.connect(lambda: self._show_runs(False))
        self.runs_title = panel.title_label
        self.ws_folder_btn = panel.ws_folder_btn
        self.ws_folder_btn.clicked.connect(self._open_workspace_folder)
        self._refresh_ws_folder_btn()
        self.run_stop_btn = panel.stop_btn
        self.run_stop_btn.clicked.connect(self._stop_selected_run)
        self.run_rename_btn = panel.rename_btn
        self.run_rename_btn.clicked.connect(self._rename_selected_run)
        self.run_del_btn = panel.del_btn
        self.run_del_btn.clicked.connect(self._delete_selected_run)
        self.run_clear_btn = panel.clear_btn
        self.run_clear_btn.clicked.connect(lambda: self.manager.clear_finished())
        self.runs_table = panel.table
        self.runs_table.itemDoubleClicked.connect(self._open_run_from_table)
        self.runs_table.customContextMenuRequested.connect(self._runs_context_menu)
        return panel
    def _wrap_config(self) -> QWidget:
        """Wrap the step-config panel with a header that has an expand/collapse
        toggle, so it can be folded away to give the canvas more room."""
        container = QWidget()
        container.setObjectName("configContainer")
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        header = QWidget()
        hb = QHBoxLayout(header)
        hb.setContentsMargins(4, 3, 4, 3)
        hb.setSpacing(4)
        self.config_toggle_btn = QPushButton()
        self.config_toggle_btn.setIcon(icon("chevron-right"))
        self.config_toggle_btn.setToolTip(tr("co4e.tt_collapse_config"))
        self.config_toggle_btn.setFixedSize(26, 24)
        self.config_toggle_btn.clicked.connect(self._toggle_config)
        self.config_title = QLabel(tr("co4e.config_title"))
        self.config_title.setObjectName("hint")
        hb.addWidget(self.config_toggle_btn)
        hb.addWidget(self.config_title, 1)
        v.addWidget(header)
        v.addWidget(self.config, 1)
        self._cfg_vlayout = v
        # Spacers used ONLY while collapsed, to keep the lone toggle icon
        # vertically CENTERED in the thin strip (its position no longer jumps to
        # the top after collapsing).
        self._cfg_top_spacer = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self._cfg_bot_spacer = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.config_container = container
        return container
    def _apply_narrow_layout(self, narrow: bool) -> None:  # noqa: D401
        """Fold the step-config panel on a narrow window, restore it when there
        is room again.

        Attached from __init__ rather than only on show: this page sits inside a
        QTabWidget, whose minimum width is the MAXIMUM over all its pages —
        including hidden ones. While Co4E sat unfolded in the background it was
        forcing Project and Cowork to be ~1180px wide too.
        """
        if narrow != self._config_collapsed:
            self._toggle_config()
    def _toggle_config(self) -> None:
        """Gập/mở bảng thuộc tính bên phải."""
        self._config_collapsed = not self._config_collapsed
        v = self._cfg_vlayout
        if self._config_collapsed:
            w = self.config_container.width()
            if w > 60:
                self._config_expanded_w = w
            self.config.hide()
            self.config_title.hide()
            self.config_container.setMaximumWidth(34)
            self.config_toggle_btn.setIcon(icon("chevron-left"))
            self.config_toggle_btn.setToolTip(tr("co4e.tt_expand_config"))
            # center the toggle vertically in the collapsed strip
            v.insertItem(0, self._cfg_top_spacer)
            v.addItem(self._cfg_bot_spacer)
            # A maximumWidth alone doesn't make the splitter hand the freed width
            # to the canvas — set sizes explicitly so the panel folds to the right.
            sizes = self._split.sizes()
            if len(sizes) == 3:
                freed = sizes[2] - 34
                sizes[2] = 34
                sizes[1] = max(200, sizes[1] + freed)
                self._split.setSizes(sizes)
            # Without this the splitter keeps reporting the OLD minimum width,
            # and since a QTabWidget's minimum is the maximum over all its pages
            # — hidden ones included — Co4E would go on forcing Project and
            # Cowork to be 1180px wide even while folded here.
            self._refresh_min_width()
        else:
            v.removeItem(self._cfg_top_spacer)
            v.removeItem(self._cfg_bot_spacer)
            self.config_container.setMaximumWidth(16777215)
            self.config.show()
            self.config_title.show()
            self.config_toggle_btn.setIcon(icon("chevron-right"))
            self.config_toggle_btn.setToolTip(tr("co4e.tt_collapse_config"))
            sizes = self._split.sizes()
            if len(sizes) == 3:
                want = self._config_expanded_w
                delta = want - sizes[2]
                sizes[2] = want
                sizes[1] = max(200, sizes[1] - delta)
                self._split.setSizes(sizes)
            self._refresh_min_width()
    def _refresh_min_width(self) -> None:
        """Make the splitter (and everything above it) re-read its minimum."""
        self.config_container.updateGeometry()
        self._split.refresh()
        self._split.updateGeometry()
        self.updateGeometry()
    def _build_canvas_overlay(self) -> None:
        """Zoom +/− and Fit as a small floating control at the canvas's
        bottom-left, stacked vertically. The frame is transparent (so it follows
        the dark/light theme — only the buttons carry a themed background) and the
        buttons are half-size."""
        from PySide6.QtCore import QSize

        bar = QFrame()
        bar.setObjectName("canvasOverlay")
        bar.setStyleSheet("QFrame#canvasOverlay { background: transparent; border: none; }")
        v = QVBoxLayout(bar)
        v.setContentsMargins(2, 2, 2, 2)
        v.setSpacing(3)
        self.zoom_in_btn = self._icon_btn("plus", "co4e.tt_zoom_in", lambda: self.canvas.zoom_in())
        self.zoom_out_btn = self._icon_btn("minus", "co4e.tt_zoom_out", lambda: self.canvas.zoom_out())
        self.fit_btn = self._icon_btn("search", "co4e.fit_tooltip", lambda: self.canvas.fit_view())
        for b in (self.zoom_in_btn, self.zoom_out_btn, self.fit_btn):
            b.setFixedSize(16, 16)          # ~half the previous size
            b.setIconSize(QSize(11, 11))
            b.setStyleSheet("QPushButton { padding: 0px; }")   # keep themed bg, drop padding
            v.addWidget(b)
        self.canvas.add_overlay(bar)
