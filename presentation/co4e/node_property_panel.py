"""Panel bên phải chỉnh sửa persona của một step đang chọn trên canvas Co4E —
tách khỏi ``ui/co4e_config_panel.py`` (nguyên bản dòng 1-27, 133-378).

Vấn đề đang có: cả ``StepConfigPanel`` (dựng UI + 8 hành động phụ trợ) và
khung section gấp/mở dùng chung của nó nằm trong một file 528 dòng — vượt
trần 400 dòng của CASAN Check 2 nếu tách nguyên khối. Chia thành 3 file theo
trách nhiệm: ``step_config_section.py`` (khung ▶/▼ dùng chung, không có hành
vi nghiệp vụ riêng), ``node_property_actions_mixin.py`` (8 hành động: thêm/
sửa/xoá sub-agent, thêm/xoá attachment, soạn AI, tải model — chỉ đọc/ghi state
đã có sẵn trên ``self``), và file này (``StepConfigPanel`` — 4 Signal,
``__init__`` dựng toàn bộ form, ``load_step``/``clear_step`` nạp/xoá dữ liệu,
``_on_edit`` ghi field vào ``Step``).

Cách làm: dời NGUYÊN VĂN phần class (Signal + ``__init__`` + ``load_step`` +
``clear_step`` + ``_on_edit``, nguyên bản dòng 133-378) sang đây, không đổi
tên thuộc tính/tham số, không đổi thứ tự dựng widget, không đổi giá trị mặc
định nào. ``StepConfigPanel`` giờ kế thừa thêm ``_StepConfigActionsMixin``
(``class StepConfigPanel(_StepConfigActionsMixin, QScrollArea)``) để có lại
các method đã dời sang ``node_property_actions_mixin.py`` — không có method
nào của mixin trùng tên với ``QScrollArea`` nên thứ tự kế thừa mixin-trước
không phải là bắt buộc như ở ``co4e_canvas_widget.py``, chỉ giữ để nhất quán
quy ước đặt mixin trước base Qt.

Import ``PROVIDER_LABELS`` (nguyên bản dòng 21) hiện KHÔNG được dùng ở đâu
trong phần class đã dời (đã xác minh bằng grep trên toàn bộ
``ui/co4e_config_panel.py`` gốc) — vẫn giữ nguyên import này y hệt bản gốc,
KHÔNG xoá dù có vẻ thừa, để đúng phạm vi "chỉ dời chỗ" của lượt tách này.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPlainTextEdit, QPushButton, QScrollArea, QSpinBox,
    QVBoxLayout, QWidget,
)

from ...config import PROVIDER_LABELS
from ...core.co4e import PERMISSION_PRESETS, Step
from ...i18n import tr
from ...ui.icons import icon, icon_picker_combo
from .node_property_actions_mixin import _StepConfigActionsMixin
from .step_config_section import _add_section


class StepConfigPanel(_StepConfigActionsMixin, QScrollArea):
    """Bảng thuộc tính bên phải khung vẽ Co4E: sửa nhãn, vai trò, model, chỉ dẫn,
    skill, sub-agent và tệp đính kèm của một bước.
    """
    changed = Signal()            # any field edited → repaint node + autosave
    run_node = Signal(str)        # "Run this step" (node id)
    run_from = Signal(str)        # "Run from here"
    delete_node = Signal(str)     # "Delete step"

    def __init__(self, ctx=None):
        """Panel cấu hình cho bước đang chọn.

        ``_loading`` chặn tín hiệu trong lúc đổ dữ liệu vào form: không có nó thì
        chính việc đổ dữ liệu sẽ bị hiểu là người dùng vừa sửa.
        """
        super().__init__()
        self.ctx = ctx
        self._step: Optional[Step] = None
        self._node_id = ""
        self._loading = False
        self.setWidgetResizable(True)
        host = QWidget()
        self.setWidget(host)
        outer = QVBoxLayout(host)
        outer.setSpacing(1)

        # Grouped sections stacked on one scrolling page — same fields as
        # before, grouped by what they're for: identity, execution
        # (model/permission), and the extra resources fed to the step
        # (skills/files/sub-agents). No tabs/accordion: every group's border
        # and heading are what separate it from its neighbours, and all three
        # are on screen (or one scroll away) at once.
        form, _basic_card = _add_section(outer, tr("co4e.tab_basic"))

        self.label_edit = QLineEdit()
        self.label_edit.textChanged.connect(self._on_edit)
        form.addRow(tr("co4e.f_label"), self.label_edit)

        self.role_edit = QLineEdit()
        self.role_edit.textChanged.connect(self._on_edit)
        form.addRow(tr("co4e.f_role"), self.role_edit)

        # Dropdown of every icon in the registry (Monitoring's Icon Management
        # set + built-ins), each row previewing its actual glyph — still
        # editable so a not-yet-added custom name can be typed directly.
        self.icon_edit = icon_picker_combo()
        self.icon_edit.lineEdit().setPlaceholderText(tr("co4e.f_icon_placeholder"))
        self.icon_edit.currentTextChanged.connect(self._on_edit)
        form.addRow(tr("co4e.f_icon"), self.icon_edit)

        self.instructions_edit = QPlainTextEdit()
        self.instructions_edit.setMaximumHeight(120)
        self.instructions_edit.textChanged.connect(self._on_edit)
        self.gen_btn = QPushButton(tr("co4e.ai_draft"))
        self.gen_btn.setIcon(icon("sparkle"))
        self.gen_btn.setToolTip(tr("co4e.ai_draft_tooltip"))
        self.gen_btn.setEnabled(ctx is not None)
        self.gen_btn.clicked.connect(self._ai_draft)
        instr_box = QWidget()
        ib = QVBoxLayout(instr_box)
        ib.setContentsMargins(0, 0, 0, 0)
        ib.addWidget(self.instructions_edit)
        ib.addWidget(self.gen_btn, alignment=Qt.AlignRight)
        form.addRow(tr("co4e.f_instructions"), instr_box)

        # Extra context — free-text background/info fed to the step at run time
        # (in addition to instructions, attachments and upstream outputs).
        self.context_edit = QPlainTextEdit()
        self.context_edit.setMaximumHeight(90)
        self.context_edit.setPlaceholderText(tr("co4e.f_context_placeholder"))
        self.context_edit.textChanged.connect(self._on_edit)
        form.addRow(tr("co4e.f_context"), self.context_edit)

        form2, _model_card = _add_section(outer, tr("co4e.tab_model_perm"))

        model_row = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.editTextChanged.connect(self._on_edit)
        self.load_models_btn = QPushButton()
        self.load_models_btn.setIcon(icon("download"))
        self.load_models_btn.setToolTip(tr("co4e.load_models_tooltip"))
        self.load_models_btn.clicked.connect(self._load_models)
        self.load_models_btn.setEnabled(ctx is not None)
        model_row.addWidget(self.model_combo, 1)
        model_row.addWidget(self.load_models_btn)
        mrow = QWidget(); mrow.setLayout(model_row)
        form2.addRow(tr("co4e.f_model"), mrow)

        self.perm_combo = QComboBox()
        for preset in PERMISSION_PRESETS:
            self.perm_combo.addItem(tr(f"co4e.perm.{preset}"), preset)
        self.perm_combo.currentIndexChanged.connect(self._on_edit)
        form2.addRow(tr("co4e.f_permission"), self.perm_combo)

        verify_row = QHBoxLayout()
        self.verify_chk = QCheckBox(tr("co4e.f_self_verify"))
        self.verify_chk.toggled.connect(self._on_edit)
        self.rounds_spin = QSpinBox()
        self.rounds_spin.setRange(1, 5)
        self.rounds_spin.valueChanged.connect(self._on_edit)
        verify_row.addWidget(self.verify_chk)
        verify_row.addWidget(QLabel(tr("co4e.f_verify_rounds")))
        verify_row.addWidget(self.rounds_spin)
        verify_row.addStretch(1)
        vrow = QWidget(); vrow.setLayout(verify_row)
        form2.addRow("", vrow)

        form3, _skills_card = _add_section(outer, tr("co4e.tab_skills_files"))

        # Skills checklist (registry skills)
        self.skills_list = QListWidget()
        self.skills_list.setMaximumHeight(110)
        self.skills_list.itemChanged.connect(self._on_edit)
        form3.addRow(tr("co4e.f_skills"), self.skills_list)

        # Attachments — files whose extracted text is fed to this step at run time.
        self.attach_list = QListWidget()
        self.attach_list.setMaximumHeight(80)
        self.attach_add_btn = QPushButton(tr("co4e.attach_add"))
        self.attach_add_btn.setIcon(icon("plus"))
        self.attach_add_btn.clicked.connect(self._add_attachment)
        self.attach_del_btn = QPushButton(tr("co4e.attach_remove"))
        self.attach_del_btn.setIcon(icon("trash"))
        self.attach_del_btn.clicked.connect(self._del_attachment)
        att_btns = QHBoxLayout()
        att_btns.addWidget(self.attach_add_btn)
        att_btns.addWidget(self.attach_del_btn)
        att_btns.addStretch(1)
        abtn = QWidget(); abtn.setLayout(att_btns)
        form3.addRow(tr("co4e.f_attachments"), self.attach_list)
        form3.addRow("", abtn)

        # Parallel sub-agents get their OWN section — same header style as
        # Cơ bản/Model & Quyền/Skills & Tệp — rather than a row buried inside
        # Skills & Tệp, since it's really a distinct group, just one that
        # only applies to parallel-variant steps. load_step() hides the whole
        # card for a non-parallel step (see is_par below).
        form4, self._parallel_card = _add_section(outer, tr("co4e.f_subagents"))
        self.sub_list = QListWidget()
        self.sub_list.setMaximumHeight(90)
        self.sub_list.itemDoubleClicked.connect(self._edit_subagent)   # re-pick agent
        self.sub_add_btn = QPushButton(tr("co4e.add_subagent"))
        self.sub_add_btn.setIcon(icon("plus"))
        self.sub_add_btn.clicked.connect(self._add_subagent)
        self.sub_del_btn = QPushButton(tr("co4e.del_subagent"))
        self.sub_del_btn.setIcon(icon("trash"))
        self.sub_del_btn.clicked.connect(self._del_subagent)
        sub_btns = QHBoxLayout()
        sub_btns.addWidget(self.sub_add_btn)
        sub_btns.addWidget(self.sub_del_btn)
        sub_btns.addStretch(1)
        sbtn = QWidget(); sbtn.setLayout(sub_btns)
        form4.addRow(self.sub_list)
        form4.addRow("", sbtn)

        # Footer actions — one compact row (Run · Run from here · Delete),
        # kept below every section, not inside one of the cards.
        self.run_btn = QPushButton(tr("co4e.run"))
        self.run_btn.setIcon(icon("play"))
        self.run_btn.setToolTip(tr("co4e.run_this_step"))
        self.run_btn.clicked.connect(lambda: self.run_node.emit(self._node_id))
        self.run_from_btn = QPushButton(tr("co4e.run_from_here"))
        self.run_from_btn.setToolTip(tr("co4e.run_from_here"))
        self.run_from_btn.clicked.connect(lambda: self.run_from.emit(self._node_id))
        self.del_btn = QPushButton()
        self.del_btn.setIcon(icon("trash"))
        self.del_btn.setObjectName("danger")
        self.del_btn.setToolTip(tr("co4e.delete_step"))
        self.del_btn.setFixedWidth(38)
        self.del_btn.clicked.connect(lambda: self.delete_node.emit(self._node_id))
        foot = QHBoxLayout()
        foot.addWidget(self.run_btn, 1)
        foot.addWidget(self.run_from_btn, 1)
        foot.addWidget(self.del_btn)
        foot_w = QWidget(); foot_w.setLayout(foot)
        outer.addWidget(foot_w)
        # Without this, QVBoxLayout hands every child widget an EQUAL share of
        # whatever extra height the scroll area's viewport has beyond the
        # content's own sizeHint (setWidgetResizable(True) stretches `host` to
        # fill it) — each collapsed header's card was measuring a true
        # sizeHint of ~17px but rendering over 100px taller, and no amount of
        # margin/padding/spacing on the header itself could touch that: the
        # surplus was being spent on the cards, not around them. One trailing
        # stretch absorbs all of it instead, so every section (and the
        # footer) renders at exactly its own natural height.
        outer.addStretch(1)

        self.setEnabled(False)

    # ---- load a step ------------------------------------------------------
    def load_step(self, node_id: str, step: Step, skill_names: List[str]) -> None:
        """Nạp một bước lên bảng.

        Bật cờ ``_loading`` trong lúc điền để việc đặt giá trị không bị hiểu nhầm là
        người dùng vừa sửa và kích hoạt tự lưu.
        """
        self._loading = True
        self._node_id = node_id
        self._step = step
        self.setEnabled(True)
        self.label_edit.setText(step.label)
        self.role_edit.setText(step.role)
        self.icon_edit.setCurrentText(step.icon)
        self.instructions_edit.setPlainText(step.instructions)
        self.context_edit.setPlainText(getattr(step, "context", ""))
        self.model_combo.setEditText(step.model)
        idx = self.perm_combo.findData(step.permission_preset)
        self.perm_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.verify_chk.setChecked(step.self_verify)
        self.rounds_spin.setValue(max(1, step.max_verify_rounds))
        # skills checklist
        self.skills_list.clear()
        for name in skill_names:
            it = QListWidgetItem(name)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if name in step.skills else Qt.Unchecked)
            self.skills_list.addItem(it)
        # attachments
        self.attach_list.clear()
        from pathlib import Path as _P
        for path in step.attachments:
            item = QListWidgetItem(_P(path).name)
            item.setToolTip(path)
            self.attach_list.addItem(item)
        # parallel sub-agents — the whole "Agent song song" section only
        # applies to parallel-variant steps, so the entire card (header
        # included) is hidden for any other step, not just its rows.
        is_par = step.is_parallel
        self._parallel_card.setVisible(is_par)
        self.sub_list.clear()
        if is_par:
            for sub in step.sub_agents:
                self.sub_list.addItem(sub.agent)
        self._loading = False

    def clear_step(self) -> None:
        """Xoá bảng khi không có bước nào được chọn."""
        self._step = None
        self._node_id = ""
        self.setEnabled(False)

    # ---- edits write back to the Step -------------------------------------
    def _on_edit(self, *_a) -> None:
        """Người dùng sửa một trường: ghi vào bước rồi báo ra ngoài để vẽ lại node và tự lưu."""
        if self._loading or self._step is None:
            return
        s = self._step
        s.label = self.label_edit.text()
        s.role = self.role_edit.text().upper() or "AGENT"
        s.icon = self.icon_edit.currentText().strip()
        s.instructions = self.instructions_edit.toPlainText()
        s.context = self.context_edit.toPlainText()
        s.model = self.model_combo.currentText().strip()
        s.permission_preset = self.perm_combo.currentData() or "inherit"
        s.self_verify = self.verify_chk.isChecked()
        s.max_verify_rounds = self.rounds_spin.value()
        s.skills = [self.skills_list.item(i).text()
                    for i in range(self.skills_list.count())
                    if self.skills_list.item(i).checkState() == Qt.Checked]
        self.changed.emit()
