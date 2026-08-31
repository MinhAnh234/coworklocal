"""Agent và skill dùng trong flow — R08-T09.
"""
from __future__ import annotations

import re
from typing import Dict, List
from PySide6.QtCore import QSize, Qt
from ...core import co4e, skills as skills_mod
from ...i18n import tr
from ...presentation.co4e.co4e_chat_view import _skill_names


class Co4EAgentsMixin:
    """Quản lý agent tự tạo và thư viện skill dùng trong luồng Co4E."""
    def _new_agent(self) -> None:
        """Mở hộp thoại tạo agent tự tạo mới."""
        self._edit_agent_dialog(co4e.new_custom_agent(""))
    def _edit_agent(self) -> None:
        """Sửa agent đang chọn; chưa chọn gì thì nhắc người dùng chọn."""
        item = self.agent_list.currentItem()
        cid = item.data(Qt.UserRole + 1) if item else None
        if not cid:
            self.status_message.emit(tr("co4e.select_custom_agent"))
            return
        agent = next((a for a in co4e.list_custom_agents() if a.id == cid), None)
        if agent is not None:
            self._edit_agent_dialog(agent)
    def _edit_agent_dialog(self, agent: co4e.CustomAgent) -> None:
        """Mở hộp thoại sửa agent; bấm OK thì lưu và nạp lại cột bên trái."""
        from ...ui.co4e_agent_dialog import Co4EAgentDialog

        dlg = Co4EAgentDialog(self.ctx, agent, _skill_names(), self)
        if dlg.exec():
            co4e.save_custom_agent(dlg.result_agent())
            self._reload_sidebar()
    def _delete_agent(self) -> None:
        """Xoá agent đang chọn; chưa chọn gì thì nhắc người dùng chọn."""
        item = self.agent_list.currentItem()
        cid = item.data(Qt.UserRole + 1) if item else None
        if not cid:
            self.status_message.emit(tr("co4e.select_custom_agent"))
            return
        co4e.delete_custom_agent(cid)
        self._reload_sidebar()
    def _manage_skills(self) -> None:
        """Mở trình quản lý Skill, đóng xong thì nạp lại cột bên trái."""
        from ...ui.skills_dialog import SkillsDialog

        SkillsDialog(self, self.ctx).exec()
        self._reload_sidebar()
    def _skill_map(self) -> Dict[str, str]:
        """Bảng ``{tên skill: nội dung chỉ dẫn}`` để truyền cho một lượt chạy luồng.

        Cắt bỏ dòng tiêu đề của khối chỉ dẫn, chỉ giữ phần nội dung.
        """
        out = {}
        for name in _skill_names():
            block = skills_mod.skill_prefix_for(name)
            if block:
                out[name] = block.split("\n", 1)[1] if "\n" in block else block
        return out
