"""Chạy flow và bảng lịch sử lượt chạy — R08-T09.

Ba chế độ chạy: cả flow, một node, hoặc từng bước thủ công. ``_topo_order`` và
``_downstream`` là phần đồ thị — chạy node nào trước, node nào phụ thuộc node
nào.

``_on_manager_event`` là nơi mọi tín hiệu từ bộ chạy nền đổ về; nó dài vì phải
phân nhánh theo loại sự kiện, không tách nhỏ được mà không làm khó đọc hơn.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QInputDialog, QMenu, QMessageBox, QTableWidget, QTableWidgetItem
from ...core import co4e
from ...i18n import tr
from ...theme import current_palette
from .co4e_workflow_crud import _LOCKED_NODE_STATUSES


class Co4ERunsMixin:
    """Phần chạy luồng của Co4E Studio: nút Chạy, ba chế độ, và bảng Flow Status.

    Nhiều luồng chạy song song được, nên mọi thứ ở đây đều đánh khoá theo
    luồng: ``_flow_runs[wf_id]`` là run của từng luồng, ``_run_logs[run_id]``
    là nhật ký nhận sự kiện của run đó. Khung vẽ chỉ phản chiếu run của luồng
    ĐANG hiện, còn các run khác vẫn chạy nền bình thường.
    """
    def _current_mode(self) -> str:
        """Chế độ chạy đang chọn: 'auto' (mặc định), 'plan' hay 'manual'."""
        return self.mode_combo.currentData() or "auto"
    def _on_mode_changed(self, *_a) -> None:
        # switching mode resets any in-progress manual sequence
        """Đổi chế độ thì huỷ chuỗi chạy thủ công đang dở và trả nhãn nút về 'Chạy'."""
        self._manual_active = False
        self._manual_order = []
        self._manual_idx = 0
        if self._cur_run_id() is None:
            self.run_btn.setText(tr("co4e.run"))
    def _on_run_clicked(self) -> None:
        # THIS flow's run is active → interrupt it (other flows keep running).
        """Bấm nút Chạy: luồng NÀY đang chạy thì dừng nó, chưa chạy thì bắt đầu theo
        chế độ đang chọn.

        Chỉ dừng run của luồng đang mở — các luồng khác không bị đụng tới.
        """
        cur = self._cur_run_id()
        if cur is not None:
            self.manager.stop(cur)
            return
        mode = self._current_mode()
        if mode == "manual":
            self._manual_run_or_advance()
        else:
            self._start_canvas_run(plan_mode=(mode == "plan"))
    def _start_canvas_run(self, *, plan_mode: bool, only: Optional[set] = None,
                          seed: Optional[Dict[str, str]] = None) -> None:
        """Bắt đầu chạy luồng trên khung vẽ.

        ``only`` giới hạn ở một nhóm bước (chạy lại một nhánh); để trống thì chạy
        cả luồng và xoá sạch trạng thái/đầu ra cũ trước. ``seed`` là đầu ra sẵn có
        đưa vào làm ngữ cảnh, để chạy tiếp một nhánh không mất kết quả phía trên.
        """
        self._sync_wf_from_canvas()
        if not self._wf.nodes:
            self.status_message.emit(tr("co4e.no_steps"))
            return
        wf_id = self._wf.id
        if only is None:
            self.canvas.reset_statuses()
            self._outputs_for(wf_id).clear()
            self._plan_bubble = None
        self._append_chat("system", tr("co4e.run_started", name=self._wf.name))
        run_id = self.manager.start(
            self._wf, skill_map=self._skill_map(), plan_mode=plan_mode,
            only_nodes=only, seed_outputs=seed or dict(self._outputs_for(wf_id)))
        self._flow_runs[wf_id] = run_id          # track THIS flow's run (parallel-safe)
        self._run_logs[run_id] = self.chat_log   # route its events to THIS flow's log
        self.run_btn.setText(tr("co4e.interrupt"))
    def _run_single(self, node_id: str) -> None:
        """Run one step (config panel "Run this step") with upstream context."""
        if self._cur_run_id() is not None:
            return
        self._start_canvas_run(plan_mode=(self._current_mode() == "plan"),
                               only={node_id}, seed=dict(self._outputs_for(self._wf.id)))
    def _run_from(self, node_id: str) -> None:
        """Chạy lại từ một bước trở đi — tức bước đó và mọi bước phía sau nó."""
        if self._cur_run_id() is not None:
            return
        self._start_canvas_run(plan_mode=(self._current_mode() == "plan"),
                               only=self._downstream(node_id), seed=dict(self._outputs_for(self._wf.id)))
    def _downstream(self, node_id: str) -> set:
        """Tập id các bước nằm sau ``node_id`` trên đồ thị (kể cả chính nó)."""
        adj: Dict[str, List[str]] = {}
        for e in self.canvas.edges():
            adj.setdefault(e.source, []).append(e.target)
        seen, stack = set(), [node_id]
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(adj.get(cur, []))
        return seen
    def _manual_run_or_advance(self) -> None:
        """Chế độ thủ công: lần bấm đầu khởi tạo chuỗi bước, các lần sau đi tiếp một bước."""
        if not self._manual_active:
            self._sync_wf_from_canvas()
            if not self._wf.nodes:
                self.status_message.emit(tr("co4e.no_steps"))
                return
            self.canvas.reset_statuses()
            self._outputs_for(self._wf.id).clear()
            self._plan_bubble = None
            self._manual_order = self._topo_order()
            self._manual_idx = 0
            self._manual_active = True
            self._append_chat("system", tr("co4e.manual_started", name=self._wf.name))
        self._manual_step()
    def _manual_step(self) -> None:
        """Chạy đúng một bước trong chuỗi thủ công, hoặc kết thúc nếu đã hết bước."""
        if self._manual_idx >= len(self._manual_order):
            self._manual_active = False
            self.run_btn.setText(tr("co4e.run"))
            self._append_chat("system", tr("co4e.run_done"))
            return
        nid = self._manual_order[self._manual_idx]
        label = next((n.data.label for n in self.canvas.nodes() if n.id == nid), nid)
        self._append_chat("system", tr("co4e.manual_step",
                                        i=self._manual_idx + 1, n=len(self._manual_order), label=label))
        run_id = self.manager.start(
            self._wf, skill_map=self._skill_map(),
            plan_mode=False, only_nodes={nid}, seed_outputs=dict(self._outputs_for(self._wf.id)),
            manual=True)
        self._flow_runs[self._wf.id] = run_id
        self._run_logs[run_id] = self.chat_log
        self.run_btn.setText(tr("co4e.interrupt"))
    def _topo_order(self) -> List[str]:
        """Thứ tự chạy các bước: theo lớp phụ thuộc trước, trong cùng lớp thì theo"""
        nodes = self.canvas.nodes()
        edges = self.canvas.edges()
        waves = co4e.compute_waves(nodes, edges)
        y = {n.id: n.y for n in nodes}
        return sorted((n.id for n in nodes), key=lambda nid: (waves.get(nid, 0), y.get(nid, 0)))
    def _on_manager_event(self, run_id: str, ev: dict) -> None:
        # Per-flow routing: every run's events go to ITS OWN flow log (so parallel
        # runs never mix), and the canvas mirrors ONLY the run whose flow is the
        # one currently shown. Flow Status refreshes on its own via `changed`.
        """Nhận sự kiện của một run và chuyển về đúng nơi."""
        h = self.manager.get(run_id)
        run_wf = h.wf_id if h is not None else None
        log = self._run_logs.get(run_id) or self.chat_log
        shown = getattr(self, "_wf", None) is not None and run_wf == self._wf.id
        t = ev.get("type")
        if t == "node_status":
            if shown:
                nid = ev.get("node_id")
                self.canvas.update_node_status(nid, ev.get("status"))
                # If the panel is showing THIS node right now (e.g. it was
                # idle and the user had it open when the run started), keep
                # the lock in sync instead of waiting for the next click.
                if nid == getattr(self.config, "_node_id", None):
                    self.config.set_locked(
                        self.canvas.node_status(nid) in _LOCKED_NODE_STATUSES)
        elif t == "node_output":
            if run_wf is not None:
                self._outputs_for(run_wf)[ev["node_id"]] = ev.get("output", "")
            label = ev["node_id"]
            if shown:
                label = next((n.data.label for n in self.canvas.nodes() if n.id == ev["node_id"]),
                             ev["node_id"])
            elif h is not None and h.wf is not None:
                label = next((n.data.label for n in h.wf.nodes if n.id == ev["node_id"]), ev["node_id"])
            if ev.get("output"):
                bub = self._append_chat("assistant", f"**{label}**\n\n{ev['output']}", log=log)
                # Per-message token/cost footer (↓in ↑out ▤ctx $cost), like Cowork.
                self._apply_usage(bub, run_wf, ev.get("usage"))
        elif t == "node_diff":
            self._append_diff(ev.get("title", ""), ev.get("diff", ""), log=log)
        elif t == "node_plan":
            self._append_plan(ev.get("steps") or [], log=log)
        elif t == "node_tool":
            if not ev.get("ok", True):
                # A single failed tool call isn't a step failure — the agent is told
                # to recover and continue, so show it as a neutral notice (not a red
                # "Error" that reads like the whole flow crashed).
                self._append_chat("system", "⚠ " + tr("co4e.tool_failed", name=ev.get("name", "")), log=log)
        elif t in ("run_done", "run_error"):
            # Drop THIS flow's run tracking (other flows keep running in parallel).
            if run_wf is not None and self._flow_runs.get(run_wf) == run_id:
                self._flow_runs.pop(run_wf, None)
            self._run_logs.pop(run_id, None)
            if self._manual_active and shown:
                self._manual_idx += 1
                self._manual_step()
            else:
                if shown:
                    self.run_btn.setText(tr("co4e.run"))
                self._append_chat("system", tr("co4e.run_done"), log=log)
                # Clickable link to the output folder so files are one click away.
                out = (h.out_dir if h is not None and h.out_dir else "") or str(self._flow_output_root())
                try:
                    log.add_folder_link(out, tr("co4e.open_output_link"))
                    log.scroll_to_bottom()
                except Exception:  # noqa: BLE001 - link is a nicety, never fatal
                    pass
                self._notify_run_finished(run_id)      # popup: the flow finished
                if not shown and h is not None:
                    self.status_message.emit(tr("co4e.bg_done", name=h.name, status=h.status))
    def _notify_run_finished(self, run_id: str) -> None:
        """Show a non-blocking popup when a flow finishes (done / error / stopped),
        so the user is notified even if they're on another screen."""
        h = self.manager.get(run_id)
        if h is None:
            return
        from PySide6.QtWidgets import QMessageBox

        if not hasattr(self, "_run_popups"):
            self._run_popups = []
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning if h.status == "error" else QMessageBox.Information)
        box.setWindowTitle(tr("co4e.run_done_title"))
        box.setText(tr("co4e.run_done_popup", name=h.name,
                       status=tr("co4e.status." + h.status)))
        box.setStandardButtons(QMessageBox.Ok)
        box.setModal(False)                       # non-blocking notification
        box.setAttribute(Qt.WA_DeleteOnClose, True)
        box.finished.connect(
            lambda _r=0, b=box: self._run_popups.remove(b) if b in self._run_popups else None)
        self._run_popups.append(box)              # keep a ref so it isn't GC'd
        box.show()
    def _refresh_runs(self) -> None:
        # Rebuild the always-fresh Runs table from the manager (single source of truth).
        """Dựng lại bảng Flow Status từ dữ liệu của manager."""
        if not hasattr(self, "runs_table"):
            return
        p = current_palette()
        color = {"running": p.accent, "done": p.success, "error": p.danger,
                 "stopped": p.text_muted}
        dots = {"running": "▶", "done": "✓", "error": "✕", "stopped": "■"}
        # Most-recent run at the TOP, oldest at the bottom (manager keeps runs in
        # chronological insertion order, so reverse it for display).
        runs = list(reversed(self.manager.runs()))
        t = self.runs_table
        # Preserve the selected run across the rebuild by its id (row indices shift
        # as runs are added/deleted, so a row-index restore would jump).
        sel_item = t.item(t.currentRow(), 0) if t.currentRow() >= 0 else None
        sel_id = sel_item.data(Qt.UserRole) if sel_item is not None else None
        t.setRowCount(len(runs))
        sel_row = -1
        for r, h in enumerate(runs):
            vals = [f"{dots.get(h.status, '•')} {h.name}", tr("co4e.status." + h.status),
                    h.progress_text(), h.created_by or "-", h.created_at or "-"]
            for c, val in enumerate(vals):
                it = QTableWidgetItem(str(val))
                if c == 0:
                    it.setData(Qt.UserRole, h.id)
                if c == 1:
                    from ...ui.co4e_tab import _qcolor
                    it.setForeground(_qcolor(color.get(h.status, p.text)))
                t.setItem(r, c, it)
            if h.id == sel_id:
                sel_row = r
        if sel_row >= 0:
            t.setCurrentCell(sel_row, 0)
        # The sidebar's short run list is the same data — refresh it together.
        self._refresh_side_runs()
        # Active-run count, on the sidebar heading now that the tab strip is gone.
        n = self.manager.active_count()
        label = tr("co4e.runs_tab_n", n=n) if n else tr("co4e.runs_tab")
        if hasattr(self, "flow_bar"):
            self.flow_bar.setTabText(0, label)
        head = (self._sections.get("co4e.runs_tab") or (None,))[0]
        if head is not None:
            head.setText(("▾ " if head.isChecked() else "▸ ") + label.upper())
    def _stop_selected_run(self) -> None:
        """Dừng run đang chọn; không chọn gì thì dừng toàn bộ run của workspace này."""
        row = self.runs_table.currentRow()
        it = self.runs_table.item(row, 0) if row >= 0 else None
        if it is None:
            self.manager.stop_all()
            return
        self.manager.stop(it.data(Qt.UserRole))
    def _delete_selected_run(self) -> None:
        """Delete the selected run from the Flow Status history (a running one is
        stopped first). Removes just that single entry."""
        row = self.runs_table.currentRow()
        it = self.runs_table.item(row, 0) if row >= 0 else None
        if it is None:
            self.status_message.emit(tr("co4e.select_run"))
            return
        run_id = it.data(Qt.UserRole)
        h = self.manager.get(run_id)             # stop tracking it per-flow if we were
        if h is not None and self._flow_runs.get(h.wf_id) == run_id:
            self._flow_runs.pop(h.wf_id, None)
        self._run_logs.pop(run_id, None)
        self.manager.remove(run_id)             # emits `changed` → _refresh_runs
    def _runs_context_menu(self, pos) -> None:
        """Menu chuột phải trên bảng Flow Status: mở, đổi tên, chạy lại, dừng, xoá."""
        from PySide6.QtWidgets import QMenu
        item = self.runs_table.itemAt(pos)
        if item is None:
            return
        self.runs_table.selectRow(item.row())
        menu = QMenu(self)
        menu.addAction(tr("co4e.open_run"),
                       lambda: self._open_run_from_table(self.runs_table.item(item.row(), 0)))
        it0 = self.runs_table.item(item.row(), 0)
        rid = it0.data(Qt.UserRole) if it0 is not None else None
        menu.addAction(tr("co4e.open_output"), lambda: self._open_run_output_folder(rid))
        menu.addAction(tr("co4e.rename_run"), self._rename_selected_run)
        menu.addAction(tr("co4e.delete_run"), self._delete_selected_run)
        menu.exec(self.runs_table.viewport().mapToGlobal(pos))
    def _open_run_output_folder(self, run_id) -> None:
        """Open the workspace folder a specific run wrote its files into."""
        from ...ui.osutil import open_location
        h = self.manager.get(run_id) if run_id else None
        path = Path(h.out_dir) if (h is not None and h.out_dir) else self._flow_output_root()
        if not path.exists():
            path = self._flow_output_root()
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
        open_location(str(path))
    def _rename_selected_run(self) -> None:
        """Rename the selected run in Flow Status — updates the run entry AND its
        underlying saved flow / open tab so the name stays consistent everywhere."""
        row = self.runs_table.currentRow()
        it = self.runs_table.item(row, 0) if row >= 0 else None
        if it is None:
            self.status_message.emit(tr("co4e.select_run"))
            return
        run_id = it.data(Qt.UserRole)
        h = self.manager.get(run_id)
        if h is None:
            return
        from PySide6.QtWidgets import QInputDialog
        new, ok = QInputDialog.getText(self, tr("co4e.rename_run"),
                                       tr("co4e.rename_run_label"), text=h.name)
        new = (new or "").strip()
        if not ok or not new or new == h.name:
            return
        self.manager.rename(run_id, new)          # run entry + snapshot (→ refresh)
        # Keep the underlying saved flow + any open tab in sync.
        wf = co4e.get_workflow(h.wf_id)
        if wf is not None:
            wf.name = new
            co4e.save_workflow(wf)
            self._reload_sidebar()
        for i, f in enumerate(self._flows):
            if f.id == h.wf_id:
                f.name = new
                self.flow_bar.setTabText(i + 1, new)
                break
        if self._wf.id == h.wf_id and self.name_edit.text() != new:
            self.name_edit.setText(new)           # updates _wf.name + active tab text
    def _run_selected_in_background(self) -> None:
        """Chạy luồng đang chọn trong danh sách ở chế độ nền, không mở nó lên khung vẽ."""
        wf = self._selected_wf()
        if wf is None:
            self.status_message.emit(tr("co4e.select_flow"))
            return
        self.manager.start(wf, skill_map=self._skill_map(),
                           plan_mode=(self._current_mode() == "plan"))
        # Used to jump the sidebar back to the Workflows tab; with one column
        # there is nothing to jump to — show the run that just started instead.
        self._refresh_side_runs()
        self.status_message.emit(tr("co4e.bg_started", name=wf.name))
    def _rerun_run_item(self, item) -> None:
        """Double-click a run in the history → run that flow again (in background)."""
        h = self.manager.get(item.data(Qt.UserRole))
        if h is None:
            return
        wf = self._wf_by_id(h.wf_id)
        if wf is None:
            self.status_message.emit(tr("co4e.flow_gone"))
            return
        self.manager.start(wf, skill_map=self._skill_map(),
                           plan_mode=(self._current_mode() == "plan"))
        self.status_message.emit(tr("co4e.bg_started", name=wf.name))
    def _open_run_from_table(self, item) -> None:
        """Double-click a run row in the Runs tab → open that flow's tab and show
        its live status (opens/focuses the tab; _open_flow reflects the run)."""
        id_item = self.runs_table.item(item.row(), 0)
        if id_item is None:
            return
        h = self.manager.get(id_item.data(Qt.UserRole))
        if h is None:
            return
        # Prefer the flow the run kept a reference to (works even after its tab was
        # closed or if it was never saved); fall back to resolving by id.
        wf = getattr(h, "wf", None) or self._wf_by_id(h.wf_id)
        if wf is None:
            self.status_message.emit(tr("co4e.flow_gone"))
            return
        self._open_flow(wf)
        # reflect this run's step statuses (done/error/running) on the canvas
        for nid, st in h.node_status.items():
            self.canvas.update_node_status(nid, st)
        self.status_message.emit(tr("co4e.viewing_flow", name=wf.name))
