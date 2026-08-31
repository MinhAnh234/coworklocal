"""Dải tab các flow đang mở — R08-T09.

Mỗi flow người dùng mở là một tab. Đóng tab không đóng flow: nó chỉ rời khỏi
dải, flow vẫn còn trong thư viện bên trái.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QPushButton, QTabBar
from ...core import co4e
from ...i18n import tr
from ...ui.icons import icon


class Co4EFlowTabsMixin:
    """Dải tab kiểu trình duyệt của Co4E Studio: mỗi luồng đang mở là một tab.

    Tab chỉ số 0 luôn là trang Flow Status được ghim, nên luồng thứ ``i`` nằm ở
    tab ``i + 1`` — mọi phép đổi chỉ số trong file này đều theo quy ước đó.
    """
    def _open_flow(self, wf: co4e.Workflow) -> None:
        """Open ``wf`` in a tab — reuse its tab if already open (like a browser),
        else add a new one and switch to it. Bar index 0 is the pinned Runs tab,
        so flow ``i`` lives at bar index ``i + 1``. If the flow has an active run,
        its live status is reflected on the canvas."""
        for i, f in enumerate(self._flows):
            if f.id == wf.id:
                self._flows[i] = wf
                bar_idx = i + 1
                self.flow_bar.setTabText(bar_idx, wf.name or tr("co4e.untitled"))
                if self.flow_bar.currentIndex() == bar_idx:
                    self._active_flow_idx = -1        # force reload of same tab
                    self._on_flow_tab_changed(bar_idx)
                else:
                    self.flow_bar.setCurrentIndex(bar_idx)
                self._reflect_active_run(wf.id)
                return
        # Without the strip there is nowhere to switch between open flows, so
        # opening one REPLACES the one on the canvas (saved first, as the tab
        # switch used to do). Runs already in progress are unaffected — they are
        # tracked per flow id and keep going in the background.
        self._close_other_flows()
        self._flows.append(wf)
        self.flow_bar.blockSignals(True)
        bar_idx = self.flow_bar.addTab(icon("flow"), wf.name or tr("co4e.untitled"))
        self._add_tab_close_button(bar_idx)
        self.flow_bar.blockSignals(False)
        if self.flow_bar.currentIndex() == bar_idx:
            self._on_flow_tab_changed(bar_idx)        # already current → load manually
        else:
            self.flow_bar.setCurrentIndex(bar_idx)
        self._reflect_active_run(wf.id)
    def _close_other_flows(self) -> None:
        """Leave the canvas empty of flows, saving whatever was on it.

        Called before opening a flow, because the tab strip that used to hold
        several at once is gone. Tab 0 (Runs) is never touched.
        """
        if not self._flows:
            return
        if 0 <= self._active_flow_idx < len(self._flows):
            self._sync_wf_from_canvas()
        self.flow_bar.blockSignals(True)
        for idx in range(self.flow_bar.count() - 1, 0, -1):
            self.flow_bar.removeTab(idx)
        self.flow_bar.blockSignals(False)
        self._flows.clear()
        self._active_flow_idx = -1
    def _show_runs(self, on: bool) -> None:
        """Swap the centre between the flow editor and the Runs table.

        This is where the pinned "Runs" tab went when the strip was removed —
        same page, same table, reached from a toggle in the flow toolbar.
        """
        target = 0 if on else min(1, self.flow_bar.count() - 1)
        if self.flow_bar.currentIndex() == target:
            self._on_flow_tab_changed(target)          # already there → re-apply
        else:
            self.flow_bar.setCurrentIndex(target)
    def _on_flow_tab_changed(self, idx: int) -> None:
        # save the outgoing flow (active_flow_idx is a FLOWS-list index) first
        """Đổi tab: lưu luồng vừa rời đi rồi nạp luồng mới lên khung vẽ.

        Phải lưu TRƯỚC khi chuyển, nếu không thay đổi chưa lưu của luồng cũ sẽ bị
        khung vẽ ghi đè khi nạp luồng mới.
        """
        if 0 <= self._active_flow_idx < len(self._flows) and (self._active_flow_idx + 1) != idx:
            self._sync_wf_from_canvas()
        if idx <= 0:                                   # the Runs page
            self._active_flow_idx = -1
            self.center_stack.setCurrentIndex(0)
            self._sync_runs_toggle(True)
            self._refresh_runs()
            return
        flow_idx = idx - 1
        if not (0 <= flow_idx < len(self._flows)):
            return
        self._active_flow_idx = flow_idx
        self.center_stack.setCurrentIndex(1)
        self._sync_runs_toggle(False)
        self._apply_workflow(self._flows[flow_idx])
    def _sync_runs_toggle(self, on: bool) -> None:
        """Keep the Runs toggle showing which page is up, however it got there
        (a double-click in the runs table also switches pages)."""
        btn = getattr(self, "runs_btn", None)
        if btn is not None and btn.isChecked() != on:
            blocked = btn.blockSignals(True)
            btn.setChecked(on)
            btn.blockSignals(blocked)
    def _add_tab_close_button(self, idx: int) -> None:
        """Give a flow tab its own close button — a small ✕ placed by QTabBar on
        the tab's right side, vertically centered and INSIDE the tab (reliable
        across themes, unlike the CSS-positioned default which looked detached)."""
        btn = QPushButton("×")                    # ×
        btn.setObjectName("flowTabClose")
        btn.setFlat(True)
        btn.setFixedSize(16, 16)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self._close_flow_tab_button(btn))
        self.flow_bar.setTabButton(idx, QTabBar.RightSide, btn)
    def _close_flow_tab_button(self, btn) -> None:
        """Tìm tab ứng với nút ✕ vừa bấm rồi đóng tab đó."""
        for i in range(self.flow_bar.count()):
            if self.flow_bar.tabButton(i, QTabBar.RightSide) is btn:
                self._close_flow_tab(i)
                return
    def _close_flow_tab(self, idx: int) -> None:
        """Đóng một tab luồng. Tab Flow Status (chỉ số 0) được ghim, không đóng được."""
        if idx <= 0:                                   # Runs tab is pinned
            return
        flow_idx = idx - 1
        if not (0 <= flow_idx < len(self._flows)):
            return
        closing = self._flows[flow_idx]
        # Stop mirroring the closed flow's run onto the canvas — the run itself
        # keeps going in the background and stays in Flow Status. (Per-flow run
        # tracking: only this flow's entry is dropped; other flows keep running.)
        rid = self._flow_runs.pop(closing.id, None)
        if rid is not None:
            self._run_logs.pop(rid, None)
            if getattr(self, "_wf", None) is not None and self._wf.id == closing.id:
                self._manual_active = False
                self.run_btn.setText(tr("co4e.run"))
        self._flows.pop(flow_idx)
        self.flow_bar.blockSignals(True)
        self.flow_bar.removeTab(idx)
        self.flow_bar.blockSignals(False)
        self._active_flow_idx = -1
        if not self._flows:
            self._open_flow(co4e.new_workflow(tr("co4e.untitled")))
        else:
            new_bar = min(idx, len(self._flows))       # clamp to the last flow tab
            self.flow_bar.blockSignals(True)
            self.flow_bar.setCurrentIndex(new_bar)
            self.flow_bar.blockSignals(False)
            self._on_flow_tab_changed(new_bar)
    def _sync_active_flow_tab_text(self) -> None:
        """Cập nhật nhãn tab đang mở theo tên luồng; không bao giờ đổi tên tab Flow Status."""
        i = self.flow_bar.currentIndex()
        if i >= 1:                                     # never rename the Runs tab
            self.flow_bar.setTabText(i, self._wf.name or tr("co4e.untitled"))
    def _reflect_active_run(self, wf_id: str) -> None:
        """If a run for this flow is active, mirror its live node statuses onto the
        canvas and keep tracking it so updates continue to show."""
        for h in self.manager.all_runs():
            if h.wf_id == wf_id and h.running:
                self._flow_runs[wf_id] = h.id
                for nid, st in h.node_status.items():
                    self.canvas.update_node_status(nid, st)
                return
    def _cur_run_id(self) -> Optional[str]:
        """The active canvas run of the CURRENTLY-shown flow, or None. Clears a
        stale entry if that run already finished."""
        wf = getattr(self, "_wf", None)
        if wf is None:
            return None
        rid = self._flow_runs.get(wf.id)
        if rid is None:
            return None
        h = self.manager.get(rid)
        if h is None or not h.running:
            self._flow_runs.pop(wf.id, None)
            return None
        return rid
    def _outputs_for(self, wf_id: str) -> Dict[str, str]:
        """This flow's accumulated step outputs (kept separate per flow so parallel
        runs never seed each other's context)."""
        return self._flow_outputs.setdefault(wf_id, {})
    def _update_run_btn(self) -> None:
        """Nhãn nút Chạy đổi theo trạng thái luồng đang mở: đang chạy thì thành "Dừng"."""
        self.run_btn.setText(tr("co4e.interrupt") if self._cur_run_id() is not None
                             else tr("co4e.run"))
