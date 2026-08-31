"""Cột trái: thư viện workflow, agent, skill — R08-T09.

Bốn mục gập được (WORKFLOWS / AGENTS / SKILLS / FLOW STATUS). Trạng thái gập
của từng mục là thứ người dùng đặt rồi mong nó giữ nguyên, nên nó nằm trong
cấu hình chứ không phải trong widget.
"""
from __future__ import annotations

import re
from typing import List
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QSplitter, QVBoxLayout, QWidget
from ...core import co4e, skills as skills_mod
from ...i18n import tr
from ...ui.icons import icon
from ...presentation.co4e.agent_list_panel import AgentListPanel
from ...presentation.co4e.co4e_chat_view import _skill_names
from ...presentation.co4e.palette_list import _PaletteList
from ...presentation.co4e.skills_list_panel import SkillsListPanel


class Co4ESidebarMixin:
    """Cột trái của Co4E Studio: Workflows, Agents, Skills và Flow Status."""
    def _build_sidebar(self) -> QWidget:
        # ONE COLUMN, four named sections — no icon tabs. Every list is on screen
        # at once, so "what can I drag onto the canvas" is answered by looking
        # rather than by clicking through three unlabeled tabs.
        # A vertical splitter, not a fixed stack: on a short window four stacked
        # lists otherwise squeeze down to one visible row each. The splitter
        # hands out the available height by weight and lets the user re-balance
        # it by dragging; each list keeps a small minimum so none disappears.
        """Dựng cột trái: MỘT cột, bốn mục có tên, không dùng tab icon.

        Mọi danh sách hiện cùng lúc nên câu hỏi "kéo được gì lên khung vẽ" trả lời
        bằng cách NHÌN, không phải bấm qua ba tab không nhãn. Dùng splitter dọc chứ
        không xếp cứng: cửa sổ thấp thì bốn danh sách chồng nhau sẽ bị bóp còn đúng
        một dòng mỗi cái; splitter chia chiều cao theo trọng số và cho người dùng
        tự cân lại.
        """
        self._sections: dict = {}
        self.sidebar = QWidget()
        outer_col = QVBoxLayout(self.sidebar)
        outer_col.setContentsMargins(6, 6, 6, 6)
        outer_col.setSpacing(0)
        self.side_split = QSplitter(Qt.Vertical)
        self.side_split.setChildrenCollapsible(False)
        self.side_split.setHandleWidth(8)
        outer_col.addWidget(self.side_split, 1)

        class _Col:
            """Adapter so the section builders below read the same as before."""

            def __init__(self, split):
                """Bọc một ``QSplitter`` để phần còn lại thao tác với nó như một cột."""
                self._split = split

            def addWidget(self, w, stretch=1):
                """Thêm một mục vào splitter dọc kèm trọng số chia chiều cao.

                Lớp bọc nhỏ này cho phép dùng splitter ở chỗ mã cũ đang gọi theo API của
                layout, nên phần dựng mục không phải sửa.
                """
                self._split.addWidget(w)
                self._split.setStretchFactor(self._split.count() - 1, stretch)

        col = _Col(self.side_split)

        # --- WORKFLOWS ---------------------------------------------------
        self.wf_new_btn = QPushButton(tr("co4e.new"))
        self.wf_new_btn.setIcon(icon("plus"))
        self.wf_new_btn.setToolTip(tr("co4e.tt_new_wf"))
        self.wf_new_btn.setObjectName("co4eSectionAction")
        self.wf_new_btn.setFlat(True)
        self.wf_new_btn.setCursor(Qt.PointingHandCursor)
        self.wf_new_btn.clicked.connect(self._new_workflow)
        wf_body = QWidget(); wl = QVBoxLayout(wf_body)
        wl.setContentsMargins(0, 0, 0, 0); wl.setSpacing(4)
        # Draggable: drag a flow onto the canvas to merge it in (Nova-style);
        # double-click loads it onto the canvas.
        self.wf_list = _PaletteList(payload_role=Qt.UserRole + 2)
        self.wf_list.setToolTip(tr("co4e.drag_hint"))
        self.wf_list.itemDoubleClicked.connect(self._load_selected_workflow)
        self.wf_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.wf_list.customContextMenuRequested.connect(self._wf_context_menu)
        wl.addWidget(self.wf_list, 1)
        wf_btns = QHBoxLayout(); wf_btns.setSpacing(4)
        self.wf_edit_btn = self._icon_btn("edit", "co4e.tt_edit_wf", self._edit_selected_workflow)
        self.wf_dup_btn = self._icon_btn("branch", "co4e.tt_dup_wf", self._duplicate_selected_workflow)
        self.wf_del_btn = self._icon_btn("trash", "co4e.tt_del_wf", self._delete_selected_workflow)
        for b in (self.wf_edit_btn, self.wf_dup_btn, self.wf_del_btn):
            wf_btns.addWidget(b)
        wf_btns.addStretch(1)
        wl.addLayout(wf_btns)
        # Its own row: sharing one line with the three icon buttons cut "Chạy
        # nền" down to "Chạ" as soon as the sidebar hit its narrow width.
        self.wf_runbg_btn = QPushButton(tr("co4e.run_bg")); self.wf_runbg_btn.setIcon(icon("play"))
        self.wf_runbg_btn.setToolTip(tr("co4e.tt_run_bg"))
        self.wf_runbg_btn.clicked.connect(self._run_selected_in_background)
        wl.addWidget(self.wf_runbg_btn)
        col.addWidget(self._section("co4e.tab_workflows", wf_body, self.wf_new_btn), 3)

        # --- AGENTS ------------------------------------------------------
        # Widget cua khu vuc nay da doi sang AgentListPanel (xem
        # presentation/co4e/agent_list_panel.py); o day chi con giu
        # ag_new_btn/agent_list/ag_edit_btn/ag_del_btn nhu 4 ten thuoc tinh cu
        # va tu noi signal - dung nguyen tac panel khong tu wire, Co4ETab moi
        # biet _new_agent/_edit_agent/_delete_agent.
        self._agent_panel = AgentListPanel()
        self.ag_new_btn = self._agent_panel.new_btn
        self.ag_new_btn.clicked.connect(self._new_agent)
        self.agent_list = self._agent_panel.list_widget
        self.ag_edit_btn = self._agent_panel.edit_btn
        self.ag_edit_btn.clicked.connect(self._edit_agent)
        self.ag_del_btn = self._agent_panel.del_btn
        self.ag_del_btn.clicked.connect(self._delete_agent)
        col.addWidget(self._section("co4e.tab_agents", self._agent_panel, self.ag_new_btn), 3)

        # --- SKILLS ------------------------------------------------------
        # Widget cua khu vuc nay da doi sang SkillsListPanel (xem
        # presentation/co4e/skills_list_panel.py); o day chi con giu
        # sk_manage_btn/skill_list nhu 2 ten thuoc tinh cu va tu noi signal -
        # dung nguyen tac panel khong tu wire, Co4ETab moi biet _manage_skills.
        self._skills_panel = SkillsListPanel()
        self.sk_manage_btn = self._skills_panel.manage_btn
        self.sk_manage_btn.clicked.connect(self._manage_skills)
        self.skill_list = self._skills_panel.list_widget
        col.addWidget(self._section("co4e.tab_skills", self._skills_panel, self.sk_manage_btn), 2)

        # --- RUNS --------------------------------------------------------
        # A short, always-visible view of the same runs the Flow Status page
        # tables in full. Clicking one opens that page with the run selected.
        # Icon only: the heading beside it already reads FLOW STATUS, and the
        # label was long enough to be cut in half in a narrow sidebar.
        self.runs_more_btn = QPushButton()
        self.runs_more_btn.setIcon(icon("chevron-right"))
        self.runs_more_btn.setFixedWidth(30)
        self.runs_more_btn.setFlat(True)
        self.runs_more_btn.setToolTip(tr("co4e.tt_runs_tab"))
        self.runs_more_btn.clicked.connect(lambda: self._show_runs(True))
        runs_body = QWidget(); rl = QVBoxLayout(runs_body)
        rl.setContentsMargins(0, 0, 0, 0); rl.setSpacing(4)
        self.runs_side_list = QListWidget()
        self.runs_side_list.setToolTip(tr("co4e.tt_runs_tab"))
        self.runs_side_list.itemClicked.connect(self._on_side_run_clicked)
        rl.addWidget(self.runs_side_list, 1)
        col.addWidget(self._section("co4e.runs_tab", runs_body, self.runs_more_btn), 2)
        # Small enough that all four still fit on a laptop screen, large enough
        # that each shows more than a single row.
        for lst in (self.wf_list, self.agent_list, self.skill_list, self.runs_side_list):
            lst.setMinimumHeight(56)
        return self.sidebar
    def _refresh_side_runs(self) -> None:
        """Mirror the newest runs into the sidebar's short list."""
        lst = getattr(self, "runs_side_list", None)
        if lst is None:
            return
        dots = {"running": "▶", "done": "✓", "error": "✕", "stopped": "■"}
        lst.clear()
        for h in list(reversed(self.manager.runs()))[:self._SIDE_RUNS]:
            it = QListWidgetItem(f"{dots.get(h.status, '•')} {h.name}"
                                 f"   {h.progress_text()}")
            it.setData(Qt.UserRole, h.id)
            it.setToolTip(f"{h.name} · {tr('co4e.status.' + h.status)} · {h.created_at or '-'}")
            lst.addItem(it)
    def _on_side_run_clicked(self, item) -> None:
        """Open the full Flow Status page with this run selected."""
        run_id = item.data(Qt.UserRole)
        self._show_runs(True)
        for r in range(self.runs_table.rowCount()):
            cell = self.runs_table.item(r, 0)
            if cell is not None and cell.data(Qt.UserRole) == run_id:
                self.runs_table.setCurrentCell(r, 0)
                break
    def _section(self, key: str, body: QWidget, action: QPushButton | None = None,
                 stretch: int = 1) -> QWidget:
        """One named, foldable section of the sidebar column.

        Replaces the three icon-only tabs: all the lists are visible at once
        (WORKFLOWS · AGENTS · SKILLS · runs), each under its own heading with the
        action that belongs to it. Clicking the heading folds the section, so a
        narrow window can still get to everything.
        """
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        head = QPushButton()
        head.setObjectName("co4eSectionHdr")
        head.setCheckable(True)
        head.setChecked(True)
        head.setCursor(Qt.PointingHandCursor)
        head.setFlat(True)
        head.toggled.connect(lambda on, w=body, b=box: self._fold_section(key, w, b, on))
        row.addWidget(head, 1)
        if action is not None:
            row.addWidget(action, 0)
        v.addLayout(row)
        v.addWidget(body, 1)

        self._sections[key] = (head, body, stretch)
        self._sync_section_arrow(key)
        return box
    def _fold_section(self, key: str, body: QWidget, box: QWidget, on: bool) -> None:
        """Fold/unfold a section AND give its height back to the others.

        Inside a splitter, hiding the body is not enough — the pane keeps its
        share of the height, so folding would free nothing. Clamping the whole
        section to its header height makes the splitter re-deal the space.
        """
        body.setVisible(on)
        if on:
            box.setMaximumHeight(16777215)
        else:
            box.setMaximumHeight(box.layout().itemAt(0).sizeHint().height() + 4)
        self._sync_section_arrow(key)
    def _sync_section_arrow(self, key: str) -> None:
        """Cập nhật mũi tên gập/mở và nhãn viết hoa của một mục ở cột trái."""
        head, _body, _s = self._sections[key]
        head.setText(("▾ " if head.isChecked() else "▸ ") + tr(key).upper())
    def _icon_btn(self, icon_name: str, tip_key: str, slot) -> QPushButton:
        """Dựng một nút icon nhỏ (rộng 34px) kèm tooltip cho hàng công cụ của mục."""
        b = QPushButton(); b.setIcon(icon(icon_name)); b.setToolTip(tr(tip_key))
        b.setFixedWidth(34)
        b.clicked.connect(slot)
        return b
    def _reload_sidebar(self) -> None:
        """Nạp lại cả bốn danh sách ở cột trái: luồng, agent, skill và Flow Status."""
        self.wf_list.clear()
        for wf in co4e.list_workflows():
            tag = tr("co4e.template") if wf.is_template else tr("co4e.saved")
            it = QListWidgetItem(icon("workspaces"), f"{wf.name}  ·  {tag}")
            it.setData(Qt.UserRole, ("saved", wf.id))
            it.setData(Qt.UserRole + 2, {"kind": "workflow", "workflow": co4e.workflow_to_dict(wf)})
            self.wf_list.addItem(it)
        # Agents: only the Parallel fan-out node + the user's own custom agents
        # (create your own with "+ New agent"; drag onto the canvas). The blank
        # "New Step" palette entry was removed — use the toolbar "+ Add" instead.
        self.agent_list.clear()
        self.agent_list.addItem(self._palette_item(
            tr("co4e.parallel_node"), "server",
            {"variant": "parallel", "label": "Parallel", "role": "PARALLEL", "icon": "server",
             "sub_agents": []}))
        for ca in co4e.list_custom_agents():
            step = co4e.Step(label=ca.name, agent_slug=co4e.slugify(ca.name), role=ca.role or "AGENT",
                             icon=ca.icon, instructions=ca.instructions,
                             context=getattr(ca, "context", ""), model=ca.model,
                             permission_preset=ca.permission_preset, skills=list(ca.skills),
                             attachments=list(getattr(ca, "attachments", []) or []))
            it = self._palette_item(f"{ca.name}  ·  {ca.role} ·  {tr('co4e.custom')}", ca.icon or "robot",
                                    co4e._step_dict(step))
            it.setData(Qt.UserRole + 1, ca.id)
            self.agent_list.addItem(it)
        # Skills
        self.skill_list.clear()
        for name in _skill_names():
            content = skills_mod.skill_prefix_for(name)
            payload = co4e._step_dict(co4e.Step(
                label=name, agent_slug=co4e.slugify(name), role="SKILL", icon="sparkle",
                instructions=content, skills=[name]))
            self.skill_list.addItem(self._palette_item(name, "sparkle", payload))
    @staticmethod
    def _palette_item(text: str, icon_name: str, payload: dict) -> QListWidgetItem:
        """Dựng một mục trong bảng nguyên liệu, mang sẵn payload để kéo-thả lên khung vẽ."""
        it = QListWidgetItem(icon(icon_name), text)
        it.setData(Qt.UserRole, payload)
        return it
