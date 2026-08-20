"""Co4E right-hand config panels — edit a selected step node's persona.

StepConfigPanel edits the fields of a ``core.co4e.Step`` in place and emits
``changed`` (so the canvas repaints + the workflow autosaves) and ``run_node`` /
``delete_node`` for the footer actions. Kept intentionally close to nova's
config-panel.tsx field set: label, role, icon, instructions, model, permission
preset, self-verify (+rounds), attached skills, and — for parallel nodes — the
sub-agent list.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, QEasingCurve, QPropertyAnimation, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit,
    QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from ..config import PROVIDER_LABELS
from ..core.co4e import PERMISSION_PRESETS, Step, SubAgent
from ..i18n import tr
from ..theme import current_palette
from .icons import icon, icon_picker_combo

_SECTION_ANIM_MS = 180


class _SectionHeader(QLabel):
    """A clickable label — a QPushButton's own style chrome (border, native
    button margin, focus rect) always leaves a taller minimum height than a
    plain label, even once its QSS padding is zeroed out, so the header that
    needs to sit tight against its neighbours is a label, not a button."""

    clicked = Signal()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def showEvent(self, event) -> None:  # noqa: N802
        # fontMetrics() at construction time (before this label is ever part
        # of a shown top-level window) reflects the QSS font-size only if the
        # style has fully polished by then — on the very FIRST paint of the
        # Co4E screen it sometimes hasn't, so the fixed height computed in
        # _add_section is briefly wrong (too tall) until something else
        # triggers a relayout. Recomputing here, every time the label
        # actually becomes visible, means the first paint is never stale.
        self.setFixedHeight(self.fontMetrics().height())
        super().showEvent(event)


def _add_section(outer: QVBoxLayout, title: str) -> tuple[QFormLayout, QWidget]:
    """One group of fields, collapsed to just its heading by default and
    independently expandable, so a long step config reads as a short list of
    group names until you open the one you need. Deliberately bare — no card
    border/background/box — the ▶/▼ marker and the heading text are the only
    things separating one group from the next; opening one never closes
    another (not an accordion, not a tab bar). Returns ``(form, card)``: add
    the group's rows to ``form``; ``card`` is the whole section (header +
    body) — hide it to remove the group entirely (e.g. for a section that
    only applies to some steps), rather than hiding individual rows inside
    an always-visible header."""
    p = current_palette()
    card = QWidget()
    card_lay = QVBoxLayout(card)
    card_lay.setContentsMargins(0, 0, 0, 0)
    card_lay.setSpacing(0)

    header = _SectionHeader()
    header.setCursor(Qt.PointingHandCursor)
    header.setStyleSheet(f"font-weight:400; font-size:13px; color:{p.text}; padding:0; margin:0;")
    header.setContentsMargins(0, 0, 0, 0)
    # QSS font-size only lands on the widget's actual QFont (and therefore
    # its fontMetrics()) once the style sheet is polished — ensurePolished()
    # forces that now, so the fixed height below is computed from the 12px
    # font just set above, not the default one this label was constructed
    # with. A label's natural sizeHint still reserves font leading above/
    # below the glyphs on top of the (now zeroed) QSS padding — pinning the
    # height to the text's actual cap-to-baseline span is what closes that
    # last gap without clipping the ▶ glyph, the title, or Vietnamese
    # diacritics.
    header.ensurePolished()
    header.setFixedHeight(header.fontMetrics().height())
    header.setText(f"▶ {title}")
    card_lay.addWidget(header)

    body = QWidget()
    body.setVisible(False)
    body.setMaximumHeight(0)
    form = QFormLayout(body)
    form.setContentsMargins(0, 6, 0, 0)
    card_lay.addWidget(body)

    anim = QPropertyAnimation(body, b"maximumHeight", body)
    anim.setDuration(_SECTION_ANIM_MS)
    anim.setEasingCurve(QEasingCurve.InOutCubic)

    is_open = False

    def _on_finished() -> None:
        if is_open:
            # Uncapped once open, so switching to a step whose fields make
            # this section taller/shorter (e.g. a parallel node's sub-agent
            # list appearing) is never clipped by the height this animation
            # last landed on.
            body.setMaximumHeight(16_777_215)
        else:
            body.setVisible(False)
    anim.finished.connect(_on_finished)

    def _toggle() -> None:
        nonlocal is_open
        is_open = not is_open
        header.setText(f"{'▼' if is_open else '▶'} {title}")
        anim.stop()
        if is_open:
            body.setVisible(True)
            anim.setStartValue(body.height())
            anim.setEndValue(body.sizeHint().height())
        else:
            anim.setStartValue(body.height())
            anim.setEndValue(0)
        anim.start()
    header.clicked.connect(_toggle)

    outer.addWidget(card)
    return form, card


class StepConfigPanel(QScrollArea):
    changed = Signal()            # any field edited → repaint node + autosave
    run_node = Signal(str)        # "Run this step" (node id)
    run_from = Signal(str)        # "Run from here"
    delete_node = Signal(str)     # "Delete step"

    def __init__(self, ctx=None):
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
        self._step = None
        self._node_id = ""
        self.setEnabled(False)

    # ---- edits write back to the Step -------------------------------------
    def _on_edit(self, *_a) -> None:
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

    @staticmethod
    def _available_agent_names() -> List[str]:
        """Agents the user can pick as a parallel sub-agent: their own custom
        agents first, then the built-in personas (kept for resolution even
        though they're no longer in the palette)."""
        from ..core import co4e
        from ..core.co4e_builtins import BUILTIN_AGENTS

        names = [a.name for a in co4e.list_custom_agents()]
        names += [a.name for a in BUILTIN_AGENTS if a.name not in names]
        return names

    def _add_subagent(self) -> None:
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
        if self._step is None:
            return
        row = self.sub_list.currentRow()
        if 0 <= row < len(self._step.sub_agents):
            self._step.sub_agents.pop(row)
            self.sub_list.takeItem(row)
            self.changed.emit()

    def _add_attachment(self) -> None:
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
        from ..core.worker import AgentWorker

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
            from ..core.ai_task_planner import generate_agent_prompt
            return {"text": generate_agent_prompt(ctx.build_active_provider(), name, role, hint,
                                                  cancel=worker.is_cancelled)}

        def done(result: dict):
            self.gen_btn.setEnabled(True)
            if result.get("text"):
                self.instructions_edit.setPlainText(result["text"])   # _on_edit persists it

        w = AgentWorker(job)
        w.finished_ok.connect(done)
        w.failed.connect(lambda _e: self.gen_btn.setEnabled(True))
        self._draft_worker = w
        w.start()

    def _load_models(self) -> None:
        if self.ctx is None:
            return
        from ..core import preview_ai
        from ..core.worker import AgentWorker

        self.load_models_btn.setEnabled(False)
        ctx = self.ctx

        def job(_w):
            return preview_ai.fetch_live_models(ctx)

        def done(result: dict):
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
