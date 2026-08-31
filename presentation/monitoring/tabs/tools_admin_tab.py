"""Tools — Monitoring tab (Admin) to govern every agent capability.

Two sub-tabs:
  * "Tool"      — built-in agent tools (read/write/edit files, run commands,
                  install packages, fetch URLs) as a left-aligned card grid;
                  toggling one OFF removes it from the agent's toolset
                  (persisted in ``config.tools_disabled``).
  * "Connector" — the full Connectors (MCP / REST API) setup, moved here from
                  Settings: add/edit/delete CAD/CAE/MS365/Other connectors and
                  enable/disable each (``ConnectorsPanel``).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QTabWidget,
    QVBoxLayout, QWidget,
)

from ....core.tools import TOOL_SPECS
from ....core.worker import AgentWorker
from ....i18n import on_language_changed, tr
from ....state import AppContext
from ....ui.connectors_panel import ConnectorsPanel
from ....ui.icons import icon
from ....ui.widgets import FlowLayout, ToggleSwitch, enable_height_for_width, style_card

# Identity colour + icon per built-in tool — same "fixed colour regardless of
# theme" convention as monitoring_tab.py's agent avatars / agents_admin_tab.py's
# kind avatars, grouped by what the tool actually touches (file i/o, shell,
# packages, network, Jira).
_TOOL_COLOUR = {
    "read_file": "#0078D4", "list_dir": "#0078D4", "write_file": "#0078D4",
    "edit_file": "#0078D4", "run_command": "#107C10", "install_package": "#8764B8",
    "fetch_url": "#FFB900", "jira_search": "#8764B8", "jira_get_issue": "#8764B8",
}
_TOOL_ICON_NAME = {
    "read_file": "document", "list_dir": "folder", "write_file": "new",
    "edit_file": "edit", "run_command": "terminal", "install_package": "download",
    "fetch_url": "globe", "jira_search": "search", "jira_get_issue": "link",
}


def _tool_icon_pixmap(name: str, size: int = 28) -> QPixmap:
    """Vẽ icon tròn cho một thẻ công cụ."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(_TOOL_COLOUR.get(name, "#0078D4")))
    r = size * 0.28
    p.drawRoundedRect(0, 0, size, size, r, r)
    inner = int(size * 0.58)
    glyph = icon(_TOOL_ICON_NAME.get(name, "puzzle"), size=inner, color="#FFFFFF").pixmap(inner, inner)
    p.drawPixmap((size - inner) // 2, (size - inner) // 2, glyph)
    p.end()
    return pm


def _clear_flow(flow: FlowLayout) -> None:
    """Xoá sạch mọi widget trong một ``FlowLayout`` trước khi dựng lại."""
    while flow.count():
        item = flow.takeAt(0)
        w = item.widget()
        if w is not None:
            w.deleteLater()


class ToolsAdminTab(QWidget):
    """Tab "Công cụ" trong màn Giám sát: bật/tắt từng tool dựng sẵn và tool MCP.

    Tắt một tool ở đây là agent không còn được gọi nó nữa — danh sách tắt lưu
    trong cấu hình dưới dạng ``tools_disabled``.
    """
    def __init__(self, ctx: AppContext):
        """Tab quản trị tool, chia thành các tab con theo nhóm tool."""
        super().__init__()
        self.ctx = ctx
        root = QVBoxLayout(self)

        self.subtabs = QTabWidget()
        root.addWidget(self.subtabs, 1)

        # ---- "Tool" sub-tab: built-in agent tools ------------------------
        tool_page = QWidget()
        tl = QVBoxLayout(tool_page)
        self._net_worker = None
        self._hint = QLabel()
        self._hint.setObjectName("hint")
        self._hint.setWordWrap(True)
        tl.addWidget(self._hint)

        # A left-aligned, wrapping card grid — one card per built-in tool
        # (colour-coded icon + name + toggle switch + description), replacing
        # the old flat Name/Description/Enabled table.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        cards_host = QWidget()
        self._tool_flow = FlowLayout(cards_host, margin=0, h_spacing=10, v_spacing=10)
        scroll.setWidget(cards_host)
        tl.addWidget(scroll, 1)

        # "Test Internet" self-test lives INSIDE the fetch_url tool's card now
        # (see refresh) instead of a separate boxed section — persistent
        # widgets so they survive card rebuilds.
        self.test_internet_btn = QPushButton(tr("settings.test_internet"))
        self.test_internet_btn.setIcon(icon("globe"))
        self.test_internet_btn.setToolTip(tr("settings.test_internet_tooltip"))
        self.test_internet_btn.clicked.connect(self._test_internet)
        self.test_internet_status = QLabel("")
        self.test_internet_status.setWordWrap(True)

        btn_row = QHBoxLayout()
        self.refresh_btn = QPushButton()
        self.refresh_btn.clicked.connect(self.refresh)
        btn_row.addStretch(1)
        btn_row.addWidget(self.refresh_btn)
        tl.addLayout(btn_row)
        # Jira CONNECTION setup lives in the Connector sub-tab now; here the Tool
        # list just lets the admin turn the jira_* tools on/off. A pointer note:
        self.jira_note = QLabel()
        self.jira_note.setObjectName("hint")
        self.jira_note.setWordWrap(True)
        tl.addWidget(self.jira_note)
        self.subtabs.addTab(tool_page, "")

        # ---- "Connector" sub-tab: MCP / REST API setup (moved from Settings) --
        self.connectors_panel = ConnectorsPanel(ctx)
        self.subtabs.addTab(self.connectors_panel, "")

        # on_language_changed() already invokes _retranslate() once immediately
        # (see i18n.py) — a second explicit call here double-populates the
        # card grid back-to-back with no event-loop turn in between, so the
        # first pass's cards are only queued for deleteLater() (not yet gone)
        # when the second pass adds new ones on top (see connectors_panel.py's
        # ConnectorsPanel, which hit the exact same bug this same way).
        on_language_changed(self._retranslate)

    # ---- built-in tools card grid ---------------------------------------------
    def refresh(self) -> None:
        """Vẽ lại toàn bộ lưới thẻ công cụ theo cấu hình mới nhất."""
        disabled = set(self.ctx.config.tools_disabled)
        _clear_flow(self._tool_flow)
        for spec in TOOL_SPECS:
            self._tool_flow.addWidget(self._tool_card(spec, spec.name not in disabled))

    def _tool_card(self, spec, enabled: bool) -> QWidget:
        """Dựng một thẻ công cụ: icon, tên, mô tả và công tắc bật/tắt."""
        card = QFrame()
        card.setFrameShape(QFrame.NoFrame)
        style_card(card)
        card.setFixedWidth(220)
        # The description below wraps to a variable number of lines at this
        # fixed width, so the card's own height depends on its width — without
        # this, the outer FlowLayout's QWidgetItem queries card.sizePolicy()
        # (not the description label's), gets a too-short sizeHint, and
        # squeezes the card into less height than its QVBoxLayout needs,
        # which is what overlapped the header onto the description text.
        enable_height_for_width(card)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(4)

        hdr = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(_tool_icon_pixmap(spec.name))
        icon_lbl.setStyleSheet("border: none;")
        hdr.addWidget(icon_lbl)
        name_lbl = QLabel(spec.name)
        name_lbl.setStyleSheet("font-weight:700; border: none;")
        hdr.addWidget(name_lbl)
        hdr.addStretch(1)
        sw = ToggleSwitch()
        sw.setChecked(enabled)
        sw.toggled.connect(lambda on, n=spec.name: self._toggle_builtin(n, on))
        hdr.addWidget(sw)
        lay.addLayout(hdr)

        desc = QLabel(spec.description)
        desc.setWordWrap(True)
        desc.setToolTip(spec.description)
        desc.setObjectName("hint")
        desc.setStyleSheet("border: none;")
        lay.addWidget(desc)

        if spec.name == "fetch_url":
            # The live "Test Internet" self-test lives inside fetch_url's own
            # card — it tests THIS capability, not the tab as a whole.
            net = QWidget()
            net.setStyleSheet("border: none;")
            nl = QHBoxLayout(net)
            nl.setContentsMargins(0, 2, 0, 0)
            nl.addWidget(self.test_internet_btn)
            nl.addWidget(self.test_internet_status, 1)
            lay.addWidget(net)

        return card

    def _toggle_builtin(self, name: str, enabled: bool) -> None:
        """Bật/tắt một tool dựng sẵn và ghi ngay vào cấu hình."""
        self.ctx.config.set_tool_enabled(name, enabled)
        # For fetch_url, the Enabled toggle also governs the runtime web-access
        # gate (agent_security.allow_url_fetch) — one control for the capability.
        if name == "fetch_url":
            self.ctx.config.agent_security["allow_url_fetch"] = bool(enabled)
            self.ctx.config.save()

    def _test_internet(self) -> None:
        """Live-check the app's own outbound HTTPS path and report the concrete
        result. Respects the fetch_url toggle: when web access is OFF the agent
        cannot reach the internet, so the test reports that instead of probing."""
        disabled = ("fetch_url" in self.ctx.config.tools_disabled
                    or not bool(self.ctx.config.agent_security.get("allow_url_fetch", True)))
        if disabled:
            self.test_internet_status.setText(tr("tools_admin.internet_disabled"))
            self.test_internet_status.setStyleSheet("color: #c00;")
            return

        def job(worker):
            """Chạy nền: chẩn đoán kết nối Internet và tình trạng chứng chỉ TLS."""
            from ....core import tls_trust
            ok, message = tls_trust.diagnose_internet()
            return {"ok": ok, "message": message}

        def done(result):
            """Hiện kết quả chẩn đoán, tô xanh/đỏ theo kết quả."""
            ok = result.get("ok")
            self.test_internet_status.setText(result.get("message", ""))
            self.test_internet_status.setStyleSheet("color: #090;" if ok else "color: #c00;")
            self.test_internet_btn.setEnabled(True)

        def failed(e):
            """Chẩn đoán ném lỗi: hiện lỗi bằng màu đỏ."""
            self.test_internet_status.setText(str(e))
            self.test_internet_status.setStyleSheet("color: #c00;")
            self.test_internet_btn.setEnabled(True)

        w = AgentWorker(job)
        w.finished_ok.connect(done)
        w.failed.connect(failed)
        self._net_worker = w   # keep a ref so the thread isn't GC'd mid-run
        self.test_internet_btn.setEnabled(False)
        self.test_internet_status.setStyleSheet("")
        self.test_internet_status.setText(tr("settings.testing_internet"))
        w.start()

    # ---- i18n -----------------------------------------------------------------
    def _retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn rồi vẽ lại lưới thẻ."""
        self.subtabs.setTabText(0, tr("tools_admin.subtab_tool"))
        self.subtabs.setTabText(1, tr("tools_admin.subtab_connector"))
        self._hint.setText(tr("tools_admin.hint"))
        self.test_internet_btn.setText(tr("settings.test_internet"))
        self.test_internet_btn.setToolTip(tr("settings.test_internet_tooltip"))
        self.refresh_btn.setText(tr("tools_admin.refresh"))
        self.jira_note.setText(tr("tools_admin.jira_note"))
        self.refresh()
