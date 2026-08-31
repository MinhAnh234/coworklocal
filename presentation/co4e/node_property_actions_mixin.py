"""Các hành động (sub-agent/attachment/AI-draft/load-models) của
``StepConfigPanel`` — tách khỏi ``ui/co4e_config_panel.py`` (nguyên bản dòng
380-528) để ``presentation/co4e/node_property_panel.py`` không vượt trần 400
dòng của CASAN Check 2.

Vấn đề đang có: ``StepConfigPanel`` gộp cả việc dựng UI (``__init__``) lẫn 8
hành động phụ trợ (thêm/sửa/xoá sub-agent, thêm/xoá attachment, soạn hướng dẫn
bằng AI, tải danh sách model) trong cùng một class 396 dòng — vượt trần nếu
để nguyên một file. Support cắt riêng phần hành động ra một ``mixin`` là hợp
lý vì các method này CHỈ đọc/ghi trạng thái đã có sẵn trên ``self`` do
``StepConfigPanel.__init__`` định nghĩa (``self._step``, ``self._node_id``,
``self.ctx``, ``self.sub_list``, ``self.attach_list``,
``self.instructions_edit``, ``self.gen_btn``, ``self.model_combo``,
``self.load_models_btn``) — không có state/``__init__`` riêng của mixin.

Cách làm: dời NGUYÊN VĂN 8 method (``_available_agent_names``,
``_add_subagent``, ``_edit_subagent``, ``_del_subagent``, ``_add_attachment``,
``_del_attachment``, ``_ai_draft``, ``_load_models``) vào class MỚI
``_StepConfigActionsMixin``. Không đổi tên, không đổi thứ tự tham số, không
gộp/tách hàm nào bên trong. ``node_property_panel.py`` ghép mixin này với
``QScrollArea`` qua đa kế thừa (``class StepConfigPanel(_StepConfigActionsMixin,
QScrollArea)``) — không có method nào ở đây trùng tên với ``QScrollArea`` nên
thứ tự kế thừa không ảnh hưởng hành vi (khác trường hợp
``co4e_canvas_widget.py``, nơi thứ tự mixin-trước-Qt-base là bắt buộc vì có
override trùng tên).

Import trong từng method giữ nguyên y hệt bản gốc (kể cả các import cục bộ có
vẻ thừa như ``from PySide6.QtWidgets import QInputDialog`` lặp lại bên trong
``_add_subagent``/``_edit_subagent`` dù đã có ở top-level) — chỉ số cấp `..`
được nâng lên `...` cho khớp việc file dời từ ``ui/`` (cách gốc 2 cấp) sang
``presentation/co4e/`` (cách gốc 3 cấp).
"""
from __future__ import annotations

from typing import List

from PySide6.QtWidgets import QInputDialog, QListWidgetItem

from ...core.co4e import SubAgent
from ...i18n import tr


class _StepConfigActionsMixin:
    """Mixin THUẦN (không ``__init__`` riêng) chứa các hành động phụ trợ của
    ``StepConfigPanel``. Vai trò: giữ ``node_property_panel.py`` gọn dưới 400
    dòng bằng cách tách phần "hành động" (nghiệp vụ khi bấm nút) ra khỏi phần
    "dựng UI" (``__init__``/``load_step``), trong khi vẫn nằm cùng tầng
    ``presentation`` — các method này thao tác trực tiếp widget Qt
    (``QInputDialog``, ``QFileDialog``, danh sách Qt) nên không hạ được xuống
    ``application``/``domain`` (nơi cấm import PySide6) mà không viết lại
    logic, việc đó ngoài phạm vi của lượt tách này.
    """

    @staticmethod
    def _available_agent_names() -> List[str]:
        """Agents the user can pick as a parallel sub-agent: their own custom
        agents first, then the built-in personas (kept for resolution even
        though they're no longer in the palette)."""
        from ...core import co4e
        from ...core.co4e_builtins import BUILTIN_AGENTS

        names = [a.name for a in co4e.list_custom_agents()]
        names += [a.name for a in BUILTIN_AGENTS if a.name not in names]
        return names

    def _add_subagent(self) -> None:
        """Thêm một sub-agent vào bước đang chọn (chạy song song trong bước đó)."""
        if self._step is None:
            return
        from PySide6.QtWidgets import QInputDialog

        names = self._available_agent_names()
        if names:
            name, ok = QInputDialog.getItem(self, tr("co4e.pick_agent"), tr("co4e.pick_agent"),
                                            names, 0, True)   # editable: can type a new one
        else:
            name, ok = QInputDialog.getText(self, tr("co4e.pick_agent"), tr("co4e.pick_agent"))
        name = (name or "").strip()
        if not ok or not name:
            return
        self._step.sub_agents.append(SubAgent(agent=name))
        self.sub_list.addItem(name)
        self.changed.emit()

    def _edit_subagent(self, item) -> None:
        """Double-click a sub-agent row → re-pick from the list."""
        if self._step is None:
            return
        row = self.sub_list.row(item)
        if not (0 <= row < len(self._step.sub_agents)):
            return
        from PySide6.QtWidgets import QInputDialog

        names = self._available_agent_names()
        cur = self._step.sub_agents[row].agent
        start = names.index(cur) if cur in names else 0
        name, ok = QInputDialog.getItem(self, tr("co4e.pick_agent"), tr("co4e.pick_agent"),
                                        names or [cur], start, True)
        name = (name or "").strip()
        if ok and name:
            self._step.sub_agents[row].agent = name
            item.setText(name)
            self.changed.emit()

    def _del_subagent(self) -> None:
        """Xoá sub-agent đang chọn khỏi bước."""
        if self._step is None:
            return
        row = self.sub_list.currentRow()
        if 0 <= row < len(self._step.sub_agents):
            self._step.sub_agents.pop(row)
            self.sub_list.takeItem(row)
            self.changed.emit()

    def _add_attachment(self) -> None:
        """Đính kèm tệp vào bước đang chọn."""
        if self._step is None:
            return
        from pathlib import Path as _P

        from PySide6.QtWidgets import QFileDialog
        files, _ = QFileDialog.getOpenFileNames(self, tr("co4e.attach_add"))
        for f in files:
            if f and f not in self._step.attachments:
                self._step.attachments.append(f)
                item = QListWidgetItem(_P(f).name)
                item.setToolTip(f)
                self.attach_list.addItem(item)
        if files:
            self.changed.emit()

    def _del_attachment(self) -> None:
        """Gỡ tệp đính kèm đang chọn khỏi bước."""
        if self._step is None:
            return
        row = self.attach_list.currentRow()
        if 0 <= row < len(self._step.attachments):
            self._step.attachments.pop(row)
            self.attach_list.takeItem(row)
            self.changed.emit()

    def _ai_draft(self) -> None:
        """Draft this step's instructions from its label (name) + role — first
        asking for an optional description so the generated instructions can be
        more specific/detailed than name+role alone would produce."""
        if self.ctx is None or self._step is None:
            return
        from ...core.worker import AgentWorker

        name = self.label_edit.text().strip()
        role = self.role_edit.text().strip()
        if not name and not role:
            return
        hint, ok = QInputDialog.getMultiLineText(
            self, tr("co4e.ai_draft_hint_title"), tr("co4e.ai_draft_hint_label"))
        if not ok:
            return
        hint = hint.strip()
        self.gen_btn.setEnabled(False)
        ctx = self.ctx

        def job(worker: AgentWorker):
            """Chạy nền: nhờ model soạn thử prompt cho agent theo tên, vai trò và gợi ý."""
            from ...core.ai_task_planner import generate_agent_prompt
            return {"text": generate_agent_prompt(ctx.build_active_provider(), name, role, hint,
                                                  cancel=worker.is_cancelled)}

        def done(result: dict):
            """Đổ prompt vừa soạn vào ô chỉ dẫn (``_on_edit`` sẽ tự lưu lại)."""
            self.gen_btn.setEnabled(True)
            if result.get("text"):
                self.instructions_edit.setPlainText(result["text"])   # _on_edit persists it

        w = AgentWorker(job)
        w.finished_ok.connect(done)
        w.failed.connect(lambda _e: self.gen_btn.setEnabled(True))
        self._draft_worker = w
        w.start()

    def _load_models(self) -> None:
        """Nạp danh sách model đang chạy được vào ô chọn của bước, ở luồng nền."""
        if self.ctx is None:
            return
        from ...core import preview_ai
        from ...core.worker import AgentWorker

        self.load_models_btn.setEnabled(False)
        ctx = self.ctx

        def job(_w):
            """Chạy nền: hỏi mọi provider danh sách model đang sống."""
            return preview_ai.fetch_live_models(ctx)

        def done(result: dict):
            """Gộp model của mọi provider vào ô chọn, giữ nguyên thứ đang chọn."""
            self.load_models_btn.setEnabled(True)
            models = []
            for lst in (result or {}).values():
                models.extend(lst)
            cur = self.model_combo.currentText()
            self.model_combo.blockSignals(True)
            self.model_combo.clear()
            self.model_combo.addItems(sorted(set(models)))
            self.model_combo.setEditText(cur)
            self.model_combo.blockSignals(False)

        w = AgentWorker(job)
        w.finished_ok.connect(done)
        w.failed.connect(lambda _e: self.load_models_btn.setEnabled(True))
        self._model_worker = w
        w.start()
