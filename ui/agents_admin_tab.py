"""Agents Admin — Monitoring tab visible to the Admin role ONLY.

CRUD over the shared admin-agent catalog (``core/admin_agents.py``): each
agent has a name, an app function from a fixed droplist (search / monitor /
cowork / graphrag / schedule / security), optional extra instructions and a
model (blank = the machine's Settings model). Saved straight into the shared
accounts folder, so every machine pointed at the same share picks changes up
automatically (OneDrive/network sync) — non-admin machines only ever READ the
catalog (their pickers in Cowork / Schedule Task list the enabled agents).

The header's "Kiểm tra tất cả" icon probes each agent's effective provider
(``check_agent``) and shows the result as the Trạng thái pill (OK / error /
checking…) — separate from the per-row Kích hoạt switch, which only toggles
the config flag.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..config import PROVIDER_LABELS
from ..core import admin_agents, preview_ai
from ..core.worker import AgentWorker
from ..i18n import on_language_changed, tr
from ..state import AppContext
from .icons import icon
from .widgets import ToggleSwitch, badge_pill_widget

_PROVIDER_DEFAULT = ""   # "" = each machine's own active provider (unchanged default)

# Identity colour (avatar circle) + badge tone per task_kind — same "fixed
# colour regardless of theme" convention as monitoring_tab.py's per-agent
# avatars, plus a badge object name (theme.py) for the Vai trò pill. Seven
# kinds, seven distinct tones — no two kinds share a badge colour.
_KIND_COLOUR = {
    "search": "#8A8886", "monitor": "#FFB900", "cowork": "#0078D4",
    "graphrag": "#8764B8", "schedule": "#107C10", "security": "#D13438",
    "help": "#E3008C",
}
_KIND_BADGE = {
    "search": "badgeNeutral", "monitor": "badgeWarn", "cowork": "badge",
    "graphrag": "badgePurple", "schedule": "badgeSuccess", "security": "badgeDanger",
    "help": "badgePink",
}
_STATUS_BADGE = {
    "unchecked": "badgeNeutral", "checking": "badgeWarn",
    "ok": "badgeSuccess", "bad": "badgeDanger",
}


def _initials(name: str) -> str:
    return "".join(w[0] for w in name.split() if w)[:2].upper()


def _fmt_updated(ts: str) -> str:
    """"dd/MM hh:mm" — same Cập nhật/Thời gian format as Monitoring's
    Bảo mật/MCP/Hành động tables (``_fmt_event_time`` in monitoring_tab.py)."""
    try:
        dt = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return ts
    return dt.strftime("%d/%m %H:%M")


def _kind_avatar_icon(kind: str, name: str, size: int = 20) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(_KIND_COLOUR.get(kind, "#0078D4")))
    p.drawEllipse(0, 0, size, size)
    font = QFont()
    font.setPixelSize(max(7, size // 2))
    font.setBold(True)
    p.setFont(font)
    p.setPen(QColor("#FFFFFF"))
    p.drawText(pm.rect(), Qt.AlignCenter, _initials(name))
    p.end()
    return QIcon(pm)


class AgentEditDialog(QDialog):
    """Add/Edit one admin agent. The provider/model pickers are drop-lists,
    not free text — ``provider_combo`` offers the app's built-in providers
    (plus "machine default"), ``model_combo`` offers that provider's REAL
    model list once fetched via "Load models" (same on-demand fetch the
    Preview tab and Settings' own "Load" button use) — editable so an admin
    can still pin an exact model string that isn't in the fetched list yet."""

    def __init__(self, parent=None, ctx: Optional[AppContext] = None,
                 agent: Optional[admin_agents.AdminAgent] = None,
                 default_model_hint: str = ""):
        super().__init__(parent)
        self.ctx = ctx
        self._existing = agent
        self._live_models: Dict[str, List[str]] = {}
        self._workers: List[AgentWorker] = []
        self.setWindowTitle(tr("agents_admin.edit_title") if agent
                            else tr("agents_admin.add_title"))
        self.resize(420, 400)
        form = QFormLayout(self)
        self.name_edit = QLineEdit(agent.name if agent else "")
        form.addRow(tr("agents_admin.f_name"), self.name_edit)
        self.kind_combo = QComboBox()
        for kind in admin_agents.TASK_KINDS:
            self.kind_combo.addItem(tr(f"agents_admin.kind.{kind}"), kind)
        if agent:
            idx = self.kind_combo.findData(agent.task_kind)
            if idx >= 0:
                self.kind_combo.setCurrentIndex(idx)
        form.addRow(tr("agents_admin.f_kind"), self.kind_combo)
        self.prompt_edit = QPlainTextEdit(agent.prompt if agent else "")
        self.prompt_edit.setPlaceholderText(tr("agents_admin.f_prompt_placeholder"))
        self.prompt_edit.setMaximumHeight(110)
        form.addRow(tr("agents_admin.f_prompt"), self.prompt_edit)

        self.provider_combo = QComboBox()
        self.provider_combo.addItem(tr("agents_admin.provider_default"), _PROVIDER_DEFAULT)
        for key, label in PROVIDER_LABELS.items():
            self.provider_combo.addItem(label, key)
        if agent and agent.provider:
            idx = self.provider_combo.findData(agent.provider)
            if idx >= 0:
                self.provider_combo.setCurrentIndex(idx)
        self.provider_combo.currentIndexChanged.connect(self._refresh_model_combo)
        form.addRow(tr("agents_admin.f_provider"), self.provider_combo)

        model_row = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        if agent and agent.model:
            self.model_combo.addItem(agent.model)
        self.model_combo.setEditText(agent.model if agent else "")
        self.model_combo.lineEdit().setPlaceholderText(
            tr("agents_admin.f_model_placeholder", model=default_model_hint or "—"))
        self.load_models_btn = QPushButton()
        self.load_models_btn.setIcon(icon("download"))
        self.load_models_btn.setToolTip(tr("agents_admin.load_models_tooltip"))
        self.load_models_btn.clicked.connect(self._load_live_models)
        self.load_models_btn.setEnabled(self.ctx is not None)
        model_row.addWidget(self.model_combo, 1)
        model_row.addWidget(self.load_models_btn)
        form.addRow(tr("agents_admin.f_model"), model_row)

        self.enabled_chk = QCheckBox(tr("agents_admin.f_enabled"))
        self.enabled_chk.setChecked(agent.enabled if agent else True)
        form.addRow("", self.enabled_chk)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _load_live_models(self) -> None:
        if self.ctx is None:
            return
        self.load_models_btn.setEnabled(False)
        ctx = self.ctx

        def job(_worker: AgentWorker):
            return preview_ai.fetch_live_models(ctx)

        def done(result: dict) -> None:
            self.load_models_btn.setEnabled(True)
            self._live_models = result or {}
            self._refresh_model_combo()
            if not self._live_models:
                QMessageBox.information(self, tr("agents_admin.add_title"),
                                        tr("agents_admin.load_models_empty"))

        def failed(err: str) -> None:
            self.load_models_btn.setEnabled(True)
            QMessageBox.warning(self, tr("agents_admin.add_title"), err)

        w = AgentWorker(job)
        w.finished_ok.connect(done)
        w.failed.connect(failed)
        self._workers.append(w)
        w.start()

    def _refresh_model_combo(self) -> None:
        provider_key = self.provider_combo.currentData()
        current_text = self.model_combo.currentText().strip()
        models = self._live_models.get(provider_key, []) if provider_key else []
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(models)
        self.model_combo.setEditText(current_text)
        self.model_combo.blockSignals(False)

    def result_fields(self) -> Dict[str, str]:
        return {
            "name": self.name_edit.text().strip(),
            "task_kind": self.kind_combo.currentData(),
            "prompt": self.prompt_edit.toPlainText().strip(),
            "provider": self.provider_combo.currentData() or "",
            "model": self.model_combo.currentText().strip(),
            "enabled": self.enabled_chk.isChecked(),
        }


class AgentsAdminTab(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        # Last operational-health result per agent_id → (ok, message). Populated
        # on demand by the "Check" button (see _check_all); survives refresh().
        self._status: Dict[str, tuple] = {}
        self._check_workers: List[AgentWorker] = []

        root = QVBoxLayout(self)

        hdr = QHBoxLayout()
        self._title_lbl = QLabel()
        self._title_lbl.setStyleSheet("font-weight:700; font-size:14px;")
        hdr.addWidget(self._title_lbl)
        hdr.addStretch(1)
        # "Kiểm tra tất cả" keeps the real _check_all action reachable without
        # competing with the 2 primary header buttons (Làm mới / + Thêm) — a
        # flat, secondary-styled button rather than a 3rd primary one, but
        # still labelled: an icon-only button here was a mystery button.
        self.check_btn = QPushButton()
        self.check_btn.setIcon(icon("check"))
        self.check_btn.setFlat(True)
        self.check_btn.setCursor(Qt.PointingHandCursor)
        self.check_btn.clicked.connect(self._check_all)
        hdr.addWidget(self.check_btn)
        self.refresh_btn = QPushButton()
        self.refresh_btn.setIcon(icon("refresh"))
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh)
        hdr.addWidget(self.refresh_btn)
        self.add_btn = QPushButton()
        self.add_btn.setIcon(icon("plus"))
        self.add_btn.setObjectName("primary")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._add)
        hdr.addWidget(self.add_btn)
        root.addLayout(hdr)

        self._hint = QLabel("")
        self._hint.setObjectName("hint")
        self._hint.setWordWrap(True)
        root.addWidget(self._hint)

        self.table = QTableWidget(0, 7)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        # Sửa/Xoá/Kích hoạt are now per-row widgets (button/switch), and Vai
        # trò/Trạng thái are pill cell widgets — none of those track a row
        # across a re-sort (a cell widget stays pinned to its screen position,
        # not to the item that moves — see monitoring_tab.py's _EventTable for
        # the same lesson learned the hard way), so this table doesn't sort.
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.verticalHeader().setVisible(False)
        # Fixed row height — letting Qt auto-size rows from content fights
        # with the toggle switch / badge cell widgets: their layout settles on
        # a stale, oversized geometry from an intermediate sizing pass, which
        # then overlaps neighbouring rows (same bug _EventTable hit for its
        # Hành động pill, fixed there the same way).
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.setIconSize(QSize(20, 20))
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        for col in (0, 6):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        # Vai trò/Trạng thái (1, 4) are pill cell widgets — ResizeToContents
        # only measures QTableWidgetItem content, so it kept fighting refresh()'s
        # manual sizeHint()-based setColumnWidth() and clipping the pill text.
        # Interactive leaves whatever width refresh() sets alone.
        for col in (1, 4):
            header.setSectionResizeMode(col, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)   # Model
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        root.addWidget(self.table, 1)

        # on_language_changed() already invokes _retranslate() once immediately
        # (see i18n.py) — calling it again here was a harmless no-op back when
        # every column was a plain QTableWidgetItem, but now refresh() also
        # populates cell WIDGETS (toggle switch, pills, row actions): running
        # it twice back-to-back with no event-loop turn in between left the
        # first pass's widgets replaced but not yet deleted, so they briefly
        # painted overlapping the second pass's row 0.
        on_language_changed(self._retranslate)

    # ---- storage ---------------------------------------------------------
    def _dir(self):
        return admin_agents.agents_admin_dir(self.ctx.config.shared_dir)

    def _default_model_hint(self) -> str:
        conf = self.ctx.config.provider_conf(self.ctx.config.active_provider)
        return conf.get("model", "")

    # ---- CRUD -------------------------------------------------------------
    def _add(self) -> None:
        dlg = AgentEditDialog(self, ctx=self.ctx, default_model_hint=self._default_model_hint())
        if not dlg.exec():
            return
        fields = dlg.result_fields()
        if not fields["name"]:
            return
        agent = admin_agents.new_agent(
            fields["name"], fields["task_kind"], fields["prompt"],
            provider=fields.get("provider", ""), model=fields["model"],
            updated_by=(getattr(self.ctx, "account", None).username if getattr(self.ctx, "account", None) else ""))
        agent.enabled = bool(fields["enabled"])
        admin_agents.save_agent(agent, self._dir())
        self.refresh()

    def _edit_agent(self, agent_id: str) -> None:
        agent = admin_agents.load_agent(agent_id, self._dir())
        if agent is None:
            return
        dlg = AgentEditDialog(self, ctx=self.ctx, agent=agent,
                              default_model_hint=self._default_model_hint())
        if not dlg.exec():
            return
        fields = dlg.result_fields()
        if not fields["name"]:
            return

        agent.name = fields["name"]
        agent.task_kind = fields["task_kind"]
        agent.prompt = fields["prompt"]
        agent.provider = fields.get("provider", "")
        agent.model = fields["model"]
        agent.enabled = bool(fields["enabled"])
        agent.updated = datetime.now().isoformat(timespec="seconds")
        agent.updated_by = (getattr(self.ctx, "account", None).username if getattr(self.ctx, "account", None) else "")
        admin_agents.save_agent(agent, self._dir())
        self.refresh()

    def _delete_agent(self, agent_id: str) -> None:
        agent = admin_agents.load_agent(agent_id, self._dir())
        if agent is None:
            return
        if QMessageBox.question(
                self, tr("agents_admin.delete_title"),
                tr("agents_admin.delete_confirm", name=agent.name)) != QMessageBox.Yes:
            return
        admin_agents.delete_agent(agent.agent_id, self._dir())
        self.refresh()

    def _set_enabled(self, agent_id: str, enabled: bool) -> None:
        agent = admin_agents.load_agent(agent_id, self._dir())
        if agent is None or agent.enabled == enabled:
            return

        agent.enabled = enabled
        agent.updated = datetime.now().isoformat(timespec="seconds")
        agent.updated_by = (getattr(self.ctx, "account", None).username if getattr(self.ctx, "account", None) else "")
        admin_agents.save_agent(agent, self._dir())
        self.refresh()

    # ---- view --------------------------------------------------------------
    def _status_cell(self, agent_id: str) -> tuple:
        """(state_key, display_text, tooltip) for the Trạng thái pill —
        state_key indexes _STATUS_BADGE for the badge's colour tone."""
        res = self._status.get(agent_id)
        if res is None:
            return ("unchecked", tr("agents_admin.status_unchecked").lstrip("— ").strip(),
                    tr("agents_admin.status_unchecked_tip"))
        ok, msg = res
        if msg == "checking":
            return "checking", tr("agents_admin.status_checking"), ""
        return ("ok" if ok else "bad"), (tr("agents_admin.status_ok") if ok else tr("agents_admin.status_bad")), msg

    def _toggle_widget(self, agent_id: str, enabled: bool) -> QWidget:
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(container)
        lay.setContentsMargins(6, 0, 0, 0)
        sw = ToggleSwitch()
        sw.setChecked(enabled)
        sw.toggled.connect(lambda checked, aid=agent_id: self._set_enabled(aid, checked))
        lay.addWidget(sw, 0, Qt.AlignVCenter)
        lay.addStretch(1)
        return container

    def _row_actions_widget(self, agent_id: str) -> QWidget:
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(container)
        lay.setContentsMargins(2, 0, 2, 0)
        lay.setSpacing(2)
        edit_btn = QPushButton()
        edit_btn.setIcon(icon("edit"))
        edit_btn.setFlat(True)
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setToolTip(tr("agents_admin.edit_row_tooltip"))
        edit_btn.clicked.connect(lambda: self._edit_agent(agent_id))
        del_btn = QPushButton()
        del_btn.setIcon(icon("trash"))
        del_btn.setFlat(True)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setToolTip(tr("agents_admin.delete_row_tooltip"))
        del_btn.clicked.connect(lambda: self._delete_agent(agent_id))
        lay.addWidget(edit_btn)
        lay.addWidget(del_btn)
        return container

    def refresh(self) -> None:
        # Make sure the built-in in-app Help assistant exists, so the Admin can
        # manage its provider/model here (the floating Help widget uses it).
        admin_agents.ensure_help_agent(self._dir())
        agents = admin_agents.list_agents(self._dir())
        self.table.setRowCount(len(agents))
        default_model = self._default_model_hint()
        for row, agent in enumerate(agents):
            if agent.model:
                provider_lbl = PROVIDER_LABELS.get(agent.provider, "") if agent.provider else ""
                model = f"{provider_lbl} — {agent.model}" if provider_lbl else agent.model
            else:
                model = tr("agents_admin.default_model", model=default_model or "—")

            name_item = QTableWidgetItem(agent.name)
            name_item.setIcon(_kind_avatar_icon(agent.task_kind, agent.name))
            self.table.setItem(row, 0, name_item)

            kind_tone = _KIND_BADGE.get(agent.task_kind, "badge")
            self.table.setCellWidget(
                row, 1, badge_pill_widget(tr(f"agents_admin.kind.{agent.task_kind}"), kind_tone))

            self.table.setItem(row, 2, QTableWidgetItem(model))
            self.table.setCellWidget(row, 3, self._toggle_widget(agent.agent_id, agent.enabled))

            state_key, status_text, status_tip = self._status_cell(agent.agent_id)
            status_widget = badge_pill_widget(status_text, _STATUS_BADGE[state_key])
            if status_tip:
                status_widget.setToolTip(status_tip)
            self.table.setCellWidget(row, 4, status_widget)

            self.table.setItem(row, 5, QTableWidgetItem(_fmt_updated(agent.updated)))
            self.table.setCellWidget(row, 6, self._row_actions_widget(agent.agent_id))

        # ResizeToContents doesn't measure a cell WIDGET's real width (only
        # QTableWidgetItem content) — size the Vai trò/Trạng thái pill columns
        # by hand, or their text clips against whatever width it guessed.
        if self.table.rowCount():
            for col in (1, 4):
                needed = max(self.table.cellWidget(r, col).sizeHint().width()
                             for r in range(self.table.rowCount()))
                if needed + 24 > self.table.columnWidth(col):
                    self.table.setColumnWidth(col, needed + 24)

    def _check_all(self) -> None:
        """Health-check every agent's effective provider off the UI thread and
        update the Status column with the result (🟢 reachable / 🔴 error)."""
        agents = admin_agents.list_agents(self._dir())
        if not agents:
            return
        for a in agents:
            self._status[a.agent_id] = (False, "checking")
        self.check_btn.setEnabled(False)
        self.refresh()
        ctx = self.ctx

        def job(_worker: AgentWorker) -> dict:
            return {a.agent_id: admin_agents.check_agent(ctx, a) for a in agents}

        def done(result: dict) -> None:
            self.check_btn.setEnabled(True)
            self._status.update(result or {})
            self.refresh()

        def failed(err: str) -> None:
            self.check_btn.setEnabled(True)
            for a in agents:
                self._status[a.agent_id] = (False, err[:200])
            self.refresh()

        w = AgentWorker(job)
        w.finished_ok.connect(done)
        w.failed.connect(failed)
        self._check_workers.append(w)
        w.start()

    def _retranslate(self) -> None:
        self._title_lbl.setText(tr("agents_admin.page_title"))
        self._hint.setText(tr("agents_admin.hint"))
        self.table.setHorizontalHeaderLabels([
            tr("agents_admin.col_name"), tr("agents_admin.col_kind"),
            tr("agents_admin.col_model"), tr("agents_admin.col_enabled"),
            tr("agents_admin.col_status"), tr("agents_admin.col_updated"), "",
        ])
        self.add_btn.setText(tr("agents_admin.add_btn"))
        self.refresh_btn.setText(tr("monitoring.refresh"))
        self.check_btn.setText(tr("agents_admin.check_btn"))
        self.check_btn.setToolTip(tr("agents_admin.check_tooltip"))
        self.refresh()
