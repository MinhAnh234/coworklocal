"""Tạo, sửa, đổi tên, xoá, nhân bản workflow — R08-T09.

Chỉ thao tác trên danh sách. Phần chạy một workflow nằm ở ``co4e_runs.py``,
phần vẽ node nằm ở canvas.
"""
from __future__ import annotations

import re
from typing import List, Optional
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QMenu
from ...core import co4e
from ...core.co4e import STEP_DONE, STEP_RUNNING
from ...i18n import tr
from ...ui.dialog_buttons import ask_text
from ...ui.icons import icon
from ...presentation.co4e.co4e_chat_view import _skill_names

_LOCKED_NODE_STATUSES = (STEP_RUNNING, STEP_DONE)


class Co4EWorkflowCrudMixin:
    """Phần tạo/mở/lưu/xoá luồng của Co4E Studio.

    Tách khỏi ``Co4ETab`` vì đây là nhóm việc trên *danh sách luồng đã lưu*,
    không phải trên khung vẽ đang mở — dù hai bên nói chuyện với nhau liên tục.
    """
    def _apply_workflow(self, wf: co4e.Workflow) -> None:
        """Đưa một luồng lên khung vẽ và chuyển hội thoại sang nhật ký của chính nó.

        KHÔNG xoá ``_flow_outputs``: mỗi luồng giữ ngữ cảnh tích luỹ riêng, đổi
        tab mà xoá là mất kết quả của luồng khác. Luồng cũ xếp dọc thì tự bẻ lại
        thành trái→phải cho khớp bố cục hiện tại.
        """
        self._wf = wf
        # Per-flow outputs are kept in self._flow_outputs[wf.id] — do NOT clear
        # here (switching tabs must not wipe another flow's accumulated context).
        # Switch the visible conversation to THIS flow's own log.
        self.chat_stack.setCurrentWidget(self._ensure_flow_log(wf.id))
        self.name_edit.setText(wf.name)
        self.canvas.load(wf.nodes, wf.edges)
        self.config.clear_step()
        if wf.nodes:
            self.canvas.relayout_if_vertical()   # convert old top-down flows to left→right
            self.canvas.fit_view()
        self._update_run_btn()                   # reflect THIS flow's run state
        self._refresh_usage_total()              # show THIS flow's token/cost total
    def _new_workflow(self) -> None:
        """Tạo luồng trống mới, đưa con trỏ vào ô tên và báo trạng thái.

        Trước đây bấm nút này khi khung vẽ đã có sẵn một luồng trống chưa đặt tên
        sẽ tạo ra một luồng trống y hệt — đúng logic nhưng nhìn không thấy gì đổi,
        nên nút bị hiểu là hỏng. Giờ nói rõ vừa xảy ra chuyện gì và đặt con trỏ
        vào đúng việc tiếp theo: đặt tên.
        """
        self._open_flow(co4e.new_workflow(tr("co4e.untitled")))
        # Pressing this while the canvas already holds an empty untitled flow
        # produced an identical empty untitled flow — correct, and completely
        # invisible, so the button read as broken. Say what happened and put the
        # cursor where the next thing to do is: naming it.
        self.name_edit.setFocus()
        self.name_edit.selectAll()
        self.status_message.emit(tr("co4e.new_flow_ready"))
    def _selected_wf(self) -> Optional[co4e.Workflow]:
        """Materialise the selected saved-flow row into a Workflow."""
        item = self.wf_list.currentItem()
        if item is None:
            return None
        _kind, ident = item.data(Qt.UserRole)
        return co4e.get_workflow(ident)
    def _load_selected_workflow(self, *_a) -> None:
        """Mở luồng đang chọn trong danh sách (hoặc chuyển sang tab của nó nếu đã mở)."""
        wf = self._selected_wf()
        if wf is not None:
            self._open_flow(wf)          # open (or focus) its browser-style tab
    def _edit_selected_workflow(self) -> None:
        """Mở luồng đang chọn để sửa; chưa chọn gì thì nhắc người dùng chọn."""
        wf = self._selected_wf()
        if wf is None:
            self.status_message.emit(tr("co4e.select_flow"))
            return
        self._open_flow(wf)
    def _duplicate_selected_workflow(self) -> None:
        """Nhân bản luồng đang chọn thành một luồng mới rồi nạp lại danh sách."""
        wf = self._selected_wf()
        if wf is None:
            self.status_message.emit(tr("co4e.select_flow"))
            return
        dup = co4e.duplicate_workflow(wf)
        self._reload_sidebar()
        self.status_message.emit(tr("co4e.duplicated_msg", name=dup.name))
    def _wf_context_menu(self, pos) -> None:
        """Menu chuột phải trên danh sách luồng: sửa, đổi tên, nhân bản, chạy nền, xoá."""
        lw = self.wf_list
        item = lw.itemAt(pos)
        if item is None:
            return
        lw.setCurrentItem(item)
        _kind, ident = item.data(Qt.UserRole)
        menu = QMenu(lw)
        act_edit = menu.addAction(icon("edit"), tr("co4e.edit"))
        act_rename = menu.addAction(icon("edit"), tr("co4e.rename"))
        act_dup = menu.addAction(icon("branch"), tr("co4e.duplicate"))
        act_run = menu.addAction(icon("play"), tr("co4e.run_bg"))
        act_del = menu.addAction(icon("trash"), tr("co4e.delete"))
        chosen = menu.exec(lw.viewport().mapToGlobal(pos))
        if chosen is act_edit:
            self._edit_selected_workflow()
        elif chosen is act_rename:
            self._rename_workflow(ident)
        elif chosen is act_dup:
            self._duplicate_selected_workflow()
        elif chosen is act_run:
            self._run_selected_in_background()
        elif chosen is act_del:
            self._delete_selected_workflow()
    def _rename_workflow(self, ident: str) -> None:
        """Rename a saved flow in place (e.g. to match its function/task)."""
        wf = co4e.get_workflow(ident)
        if wf is None:
            return
        name, ok = ask_text(self, tr("co4e.rename"), tr("co4e.rename_prompt"),
                            text=wf.name)
        name = (name or "").strip()
        if not ok or not name:
            return
        wf.name = name
        co4e.save_workflow(wf)
        if self._wf.id == ident:
            self.name_edit.setText(name)
            self._wf.name = name
        self._reload_sidebar()
        self.status_message.emit(tr("co4e.renamed_msg", name=name))
    def _delete_selected_workflow(self) -> None:
        """Xoá luồng đang chọn khỏi đĩa rồi nạp lại danh sách."""
        item = self.wf_list.currentItem()
        if item is None:
            return
        _kind, ident = item.data(Qt.UserRole)
        co4e.delete_workflow(ident)
        self._reload_sidebar()
    def _sync_wf_from_canvas(self) -> None:
        """Chép node, cạnh và tên từ khung vẽ về đối tượng luồng trước khi lưu."""
        self._wf.nodes = self.canvas.nodes()
        self._wf.edges = self.canvas.edges()
        self._wf.name = self.name_edit.text().strip() or tr("co4e.untitled")
    def _save(self, as_template: bool) -> None:
        """Lưu luồng đang mở; ``as_template`` đánh dấu nó là mẫu dùng lại được."""
        self._sync_wf_from_canvas()
        self._wf.is_template = as_template
        co4e.save_workflow(self._wf)
        self._reload_sidebar()
        self.status_message.emit(tr("co4e.saved_msg", name=self._wf.name))
    def _autosave(self) -> None:
        """Tự lưu sau mỗi thay đổi trên khung vẽ — nhưng chỉ với luồng ĐÃ tồn tại
        trên đĩa, để luồng nháp chưa đặt tên không tự nhảy vào danh sách.
        """
        if co4e.get_workflow(self._wf.id) is not None:
            self._sync_wf_from_canvas()
            co4e.save_workflow(self._wf)
    def _on_name_changed(self, text: str) -> None:
        """Gõ tên mới thì cập nhật luôn nhãn tab của luồng đang mở."""
        self._wf.name = text.strip() or tr("co4e.untitled")
        self._sync_active_flow_tab_text()
    def _add_blank_step(self) -> None:
        """Thêm một bước trống vào giữa khung nhìn hiện tại."""
        self.canvas.add_palette_step(co4e.Step(label="New Step"),
                                     self.canvas.mapToScene(self.canvas.rect().center()))
    def _on_node_selected(self, node_id: str) -> None:
        """Chọn một node thì nạp bước đó vào bảng thuộc tính, tự mở bảng nếu đang gập.

        Bước đang chạy hoặc đã chạy xong thì khoá ô nhập liệu ngay khi nạp —
        tránh sửa nhầm cấu hình của lần chạy đang xem kết quả.
        """
        for n in self.canvas.nodes():
            if n.id == node_id:
                self.config.load_step(node_id, n.data, _skill_names())
                self.config.set_locked(self.canvas.node_status(node_id) in _LOCKED_NODE_STATUSES)
                if self._config_collapsed:
                    self._toggle_config()
                return
    def _on_config_changed(self) -> None:
        """Sửa thuộc tính bước thì vẽ lại mọi node (nhãn/model có thể đổi) rồi tự lưu."""
        for n in self.canvas.nodes():
            self.canvas.refresh_node(n.id)
        self._autosave()
    def _wf_by_id(self, wf_id: str) -> Optional[co4e.Workflow]:
        """Resolve a flow id to a Workflow — saved, or the open canvas."""
        wf = co4e.get_workflow(wf_id)
        if wf is not None:
            return wf
        if self._wf.id == wf_id:
            self._sync_wf_from_canvas()
            return self._wf
        return None
