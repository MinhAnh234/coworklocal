"""Connectors (MCP / REST API) management — the setup UI.

Lives in Monitoring → Tools → "Connector" sub-tab (moved out of Settings).
Grouped by the four real categories (CAD / CAE / MS365 / Other): each is a
header (icon + name + the software it covers) above a left-aligned row of
cards, one per real connector, each with its own on/off switch — user-added
connectors (MCP-stdio or REST-API, via ExtConnectorEditDialog) also get
✎ Sửa/🗑 Xóa; the built-in ones (MS365 OneDrive/SharePoint, Jira under
"Other") only get what they actually support (Jira: ✎ Sửa only, opens its own
setup dialog; OneDrive/SharePoint: neither, they only toggle).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from ..core.ext_connectors import CATEGORIES as EXT_CATEGORIES
from ..core.worker import AgentWorker
from ..i18n import on_language_changed, tr
from ..state import AppContext
from .ext_connector_dialog import ExtConnectorEditDialog
from .icons import icon
from .widgets import FlowLayout, ToggleSwitch, enable_height_for_width, style_card


class JiraConnectDialog(QDialog):
    """Minimal Jira connect — paste any Jira link (it fills the base URL) + email
    + API token. Once connected, pasting a Jira link into Cowork / Co4E chat is
    read and processed automatically (no per-request setup)."""

    def __init__(self, ctx: AppContext, parent=None):
        """Form khai báo kết nối Jira: địa chỉ, tài khoản và token."""
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle(tr("connectors.jira_group"))
        self.setMinimumWidth(460)
        jira = ctx.config.data.get("jira", {})
        form = QFormLayout(self)

        hint = QLabel(tr("connectors.jira_hint"))
        hint.setObjectName("hint"); hint.setWordWrap(True); hint.setOpenExternalLinks(True)
        form.addRow(hint)
        self.paste = QLineEdit()
        self.paste.setPlaceholderText(tr("connectors.jira_paste_placeholder"))
        self.paste.textChanged.connect(self._on_paste)
        form.addRow(tr("connectors.jira_paste"), self.paste)
        self.url = QLineEdit(jira.get("base_url", ""))
        self.url.setPlaceholderText("https://your-domain.atlassian.net")
        self.email = QLineEdit(jira.get("email", ""))
        self.token = QLineEdit(jira.get("api_token", ""))
        self.token.setEchoMode(QLineEdit.Password)
        form.addRow(tr("connectors.jira_url"), self.url)
        form.addRow(tr("connectors.jira_email"), self.email)
        form.addRow(tr("connectors.jira_token"), self.token)
        self.status = QLabel(); self.status.setObjectName("hint"); self.status.setWordWrap(True)
        form.addRow(self.status)

        row = QHBoxLayout()
        self.test_btn = QPushButton(tr("connectors.jira_test"))
        self.test_btn.clicked.connect(self._test)
        self.save_btn = QPushButton(tr("connectors.jira_save"))
        self.save_btn.setObjectName("primary"); self.save_btn.setIcon(icon("save"))
        self.save_btn.clicked.connect(self._save_close)
        row.addWidget(self.test_btn); row.addStretch(1); row.addWidget(self.save_btn)
        rw = QWidget(); rw.setLayout(row)
        form.addRow(rw)

    def _on_paste(self, text: str) -> None:
        """Dán một link Jira bất kỳ thì tự rút ra base URL — người dùng không phải
        biết đâu là phần gốc của địa chỉ.
        """
        from ..core import jira_tool
        base = jira_tool.base_url_from_link(text)
        if base:
            self.url.setText(base)

    def _save(self) -> None:
        """Ghi thông tin Jira vào cấu hình (chưa đóng hộp thoại)."""
        j = self.ctx.config.data.setdefault("jira", {})
        j.update({"base_url": self.url.text().strip(), "email": self.email.text().strip(),
                  "api_token": self.token.text().strip()})
        j.setdefault("enabled", True)
        self.ctx.save()

    def _save_close(self) -> None:
        """Lưu rồi đóng hộp thoại."""
        self._save()
        self.accept()

    def _test(self) -> None:
        """Thử kết nối bằng một truy vấn tối thiểu, chạy ở luồng nền."""
        from ..core import jira_tool
        self._save()
        cfg = self.ctx.config.data.get("jira", {})
        if not jira_tool.configured(cfg):
            self.status.setText(tr("connectors.jira_need_fields"))
            return
        self.status.setText(tr("connectors.jira_testing"))
        self.test_btn.setEnabled(False)

        def job(_w):
            """Chạy nền: tìm đúng 1 issue mới nhất để xác nhận kết nối sống."""
            return {"out": jira_tool.search(cfg, "order by created DESC", 1)}

        def done(r):
            """Hiện kết quả thử: coi là lỗi khi thông điệp bắt đầu bằng câu báo chưa cấu
            hình hoặc tìm kiếm thất bại.
            """
            self.test_btn.setEnabled(True)
            out = r.get("out", "")
            ok = not out.lower().startswith(("jira is not configured", "jira search failed"))
            self.status.setText(tr("connectors.jira_ok") if ok
                                else tr("connectors.jira_fail", err=out[:200]))

        w = AgentWorker(job)
        w.finished_ok.connect(done)
        w.failed.connect(lambda e: (self.test_btn.setEnabled(True),
                                    self.status.setText(tr("connectors.jira_fail", err=str(e)[:200]))))
        self._jira_worker = w
        w.start()


class ConnectorsPanel(QWidget):
    """Bảng Connectors trong Cài đặt: MS365 dựng sẵn, Jira, và connector MCP tự thêm,
    gom theo bốn nhóm CAD / CAE / MS365 / Khác.

    Có một công tắc tổng: tắt là agent không nối ra connector ngoài nào cả.
    """
    _EXT_CATEGORY_LABELS = {
        "cad": "CAD (NX / CATIA / SolidWorks / AutoCAD)",
        "cae": "CAE (ANSA / ABAQUS / HyperWorks / ANSYS)",
        "ms365": "MS365 (Microsoft 365 / OneDrive / SharePoint)",
        "other": "Other (any generic MCP server)",
    }
    _EXT_CATEGORY_ICONS = {"cad": "wrench", "cae": "ruler", "ms365": "cloud", "other": "plug"}
    # TEMPORARY: only OneDrive + SharePoint (auto-connect via locally-synced
    # OneDrive folders, no sign-in). Restore Outlook/Teams/Meeting when cloud
    # OAuth is re-enabled.
    _MS365_BUILTIN_LABELS = {"onedrive": "OneDrive", "sharepoint": "SharePoint"}

    def __init__(self, ctx: AppContext):
        """Panel quản lý connector ngoài.

        Công tắc tổng ở trên cùng: tắt là agent KHÔNG nối tới connector nào, bất kể
        từng connector bên dưới có bật hay không.
        """
        super().__init__()
        self.ctx = ctx
        lay = QVBoxLayout(self)

        # Master switch: connect to external connectors at all (default ON).
        # Off = the agent connects to NO external connector/MCP (see
        # AppContext.build_mcp_tools), regardless of the per-connector checks below.
        self.connect_external_sw = ToggleSwitch(tr("connectors.connect_external"))
        self.connect_external_sw.setChecked(self.ctx.config.connect_external)
        self.connect_external_sw.setToolTip(tr("connectors.connect_external_tooltip"))
        self.connect_external_sw.toggled.connect(self._on_connect_external_toggled)
        lay.addWidget(self.connect_external_sw)

        hint = QLabel(tr("settings.ext_hint"))
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        # Each category (CAD/CAE/MS365/Other) is a header + a left-aligned,
        # wrapping row of cards — one per real connector — instead of a tree
        # the admin had to expand to see what was inside.
        self._cat_scroll = QScrollArea()
        self._cat_scroll.setWidgetResizable(True)
        self._cat_scroll.setFrameShape(QScrollArea.NoFrame)
        cat_host = QWidget()
        enable_height_for_width(cat_host)  # holds several height-for-width sections — see FlowLayout
        self._cat_lay = QVBoxLayout(cat_host)
        self._cat_lay.setContentsMargins(0, 4, 0, 4)
        self._cat_lay.setSpacing(10)
        self._cat_scroll.setWidget(cat_host)
        lay.addWidget(self._cat_scroll, 1)

        self.add_btn = QPushButton(tr("settings.ext_add_btn"))
        self.add_btn.setIcon(icon("plus"))
        self.add_btn.setObjectName("primary")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._ext_add)
        add_row = QHBoxLayout()
        add_row.addWidget(self.add_btn)
        add_row.addStretch(1)
        lay.addLayout(add_row)

        self.ms365_local_status = QLabel()
        self.ms365_local_status.setObjectName("hint")
        self.ms365_local_status.setWordWrap(True)
        lay.addWidget(self.ms365_local_status)

        # on_language_changed() below already invokes _retranslate() once
        # immediately (see i18n.py), which itself calls _reload_connectors() —
        # calling it again here would rebuild the category cards twice
        # back-to-back with no event-loop turn in between, so the first pass's
        # widgets are only QUEUED for deleteLater() (not yet gone) when the
        # second pass adds new ones on top: the two rows visually overlap
        # (the exact bug agents_admin_tab.py hit the same way).
        self._refresh_ms365_local_status()
        on_language_changed(self._retranslate)

    # ---- rendering ------------------------------------------------------------
    def _clear_categories(self) -> None:
        """Xoá sạch các mục nhóm trước khi dựng lại."""
        while self._cat_lay.count():
            item = self._cat_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _reload_connectors(self) -> None:
        """Dựng lại toàn bộ bảng từ cấu hình mới nhất."""
        self._clear_categories()
        for cat in EXT_CATEGORIES:
            self._cat_lay.addWidget(self._category_section(cat))

    def _category_section(self, cat: str) -> QWidget:
        """Dựng một mục nhóm kèm lưới thẻ connector bên trong."""
        section = QWidget()
        enable_height_for_width(section)  # this section wraps a FlowLayout row — see FlowLayout
        sl = QVBoxLayout(section)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(6)

        hdr = QHBoxLayout()
        hdr.setSpacing(6)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(icon(self._EXT_CATEGORY_ICONS.get(cat, "plug"), size=18).pixmap(18, 18))
        hdr.addWidget(icon_lbl)
        name, _, subtitle = self._EXT_CATEGORY_LABELS.get(cat, cat).partition(" (")
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-weight:700;")
        hdr.addWidget(name_lbl)
        if subtitle:
            sub_lbl = QLabel("(" + subtitle)
            sub_lbl.setObjectName("hint")
            hdr.addWidget(sub_lbl)
        hdr.addStretch(1)
        sl.addLayout(hdr)

        flow_host = QWidget()
        flow = FlowLayout(flow_host, margin=0, h_spacing=10, v_spacing=10)

        if cat == "ms365":
            conns = self.ctx.config.ms365.get("connectors", {})
            for key, label in self._MS365_BUILTIN_LABELS.items():
                flow.addWidget(self._connector_card(
                    label, tr("connectors.builtin_auto"), bool(conns.get(key)),
                    lambda on, k=key: self._toggle_ms365_builtin(k, on)))

        for entry in self.ctx.config.ext_connectors.get(cat, []):
            mode_label = tr("ext.mode_mcp") if entry.get("mode") == "mcp_stdio" else tr("ext.mode_rest")
            flow.addWidget(self._connector_card(
                entry.get("name", ""), mode_label, bool(entry.get("enabled")),
                lambda on, e=entry: self._toggle_ext_entry(e, on),
                # QPushButton.clicked emits a `checked` bool — a lambda whose
                # ONLY parameter is a defaulted capture (`e=entry`) looks like
                # it accepts that bool, so Qt hands it the click state instead
                # of using the default, silently replacing the captured dict
                # with False. An explicit leading `checked=False` soaks up the
                # signal's argument so `e` keeps the entry it was defined with.
                edit_cb=lambda checked=False, e=entry: self._edit_ext_entry(cat, e),
                delete_cb=lambda checked=False, e=entry: self._delete_ext_entry(cat, e)))

        if cat == "other":
            # Jira is a built-in "Other" connector (like OneDrive under MS365):
            # switch = enabled; ✎ Sửa opens its own minimal setup dialog — no
            # 🗑 Xóa, same as OneDrive/SharePoint have neither (nothing to delete).
            jira = self.ctx.config.data.get("jira", {})
            configured = bool(jira.get("base_url") and jira.get("email") and jira.get("api_token"))
            jstate = tr("connectors.jira_connected") if configured else tr("connectors.jira_not_set")
            flow.addWidget(self._connector_card(
                "Jira", f"{tr('ext.mode_builtin').capitalize()} · {jstate}",
                configured and jira.get("enabled", True), self._toggle_jira,
                edit_cb=self._open_jira_dialog))

        sl.addWidget(flow_host)
        return section

    def _connector_card(self, title: str, subtitle: str, checked: bool, on_toggle,
                        edit_cb=None, delete_cb=None) -> QWidget:
        """Dựng một thẻ connector: tiêu đề, dòng phụ, công tắc bật/tắt và nút sửa/xoá
        (nếu có).
        """
        card = QFrame()
        card.setFrameShape(QFrame.NoFrame)
        style_card(card)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(4)

        hdr = QHBoxLayout()
        name_lbl = QLabel(title)
        name_lbl.setStyleSheet("font-weight:700; border: none;")
        hdr.addWidget(name_lbl)
        hdr.addStretch(1)
        sw = ToggleSwitch()
        sw.setChecked(checked)
        sw.toggled.connect(on_toggle)
        hdr.addWidget(sw)
        lay.addLayout(hdr)

        sub_lbl = QLabel(subtitle)
        sub_lbl.setObjectName("hint")
        sub_lbl.setStyleSheet("border: none;")
        lay.addWidget(sub_lbl)

        if edit_cb is not None or delete_cb is not None:
            actions = QHBoxLayout()
            actions.setContentsMargins(0, 2, 0, 0)
            actions.setSpacing(2)
            if edit_cb is not None:
                b = QPushButton(tr("settings.ext_edit_btn"))
                b.setIcon(icon("edit"))
                b.setFlat(True)
                b.setCursor(Qt.PointingHandCursor)
                b.clicked.connect(edit_cb)
                actions.addWidget(b)
            if delete_cb is not None:
                b = QPushButton(tr("settings.ext_delete_btn"))
                b.setIcon(icon("trash"))
                b.setFlat(True)
                b.setCursor(Qt.PointingHandCursor)
                b.clicked.connect(delete_cb)
                actions.addWidget(b)
            actions.addStretch(1)
            lay.addLayout(actions)

        return card

    def _toggle_ms365_builtin(self, key: str, checked: bool) -> None:
        """Bật/tắt một connector MS365 dựng sẵn và lưu ngay."""
        self.ctx.config.ms365.setdefault("connectors", {})[key] = checked
        self.ctx.save()

    def _toggle_jira(self, checked: bool) -> None:
        """Bật/tắt connector Jira và lưu ngay."""
        self.ctx.config.data.setdefault("jira", {})["enabled"] = checked
        self.ctx.save()

    def _toggle_ext_entry(self, entry: dict, checked: bool) -> None:
        """Bật/tắt một connector MCP tự thêm và lưu ngay."""
        entry["enabled"] = checked
        self.ctx.save()

    # ---- CRUD -----------------------------------------------------------------
    def _ext_add(self) -> None:
        """Thêm một connector MCP mới qua hộp thoại."""
        dlg = ExtConnectorEditDialog(self, category=EXT_CATEGORIES[0])
        if dlg.exec():
            entry = dlg.result_connector()
            self.ctx.config.ext_connectors.setdefault(entry["category"], []).append(entry)
            self.ctx.save()
            self._reload_connectors()

    def _edit_ext_entry(self, cat: str, entry: dict) -> None:
        """Sửa một connector MCP đã có."""
        dlg = ExtConnectorEditDialog(self, category=cat, connector=entry)
        if dlg.exec():
            entry.update(dlg.result_connector())
            self.ctx.save()
            self._reload_connectors()

    def _open_jira_dialog(self) -> None:
        """Mở hộp thoại cấu hình Jira rồi dựng lại bảng."""
        JiraConnectDialog(self.ctx, self).exec()
        self._reload_connectors()

    def _delete_ext_entry(self, cat: str, entry: dict) -> None:
        """Xoá một connector MCP sau khi hỏi xác nhận."""
        if QMessageBox.question(
                self, tr("settings.ext_delete_btn"),
                tr("settings.ext_delete_confirm", name=entry.get("name", ""))) != QMessageBox.Yes:
            return
        self.ctx.config.ext_connectors[cat].remove(entry)
        self.ctx.save()
        self._reload_connectors()

    def _refresh_ms365_local_status(self) -> None:
        """Cập nhật dòng trạng thái MS365 cục bộ theo việc có tìm thấy thư mục OneDrive hay không."""
        from .. import paths
        root = paths.primary_onedrive_root()
        if root is not None:
            self.ms365_local_status.setText(tr("settings.ms365_local_connected", path=str(root)))
        else:
            self.ms365_local_status.setText(tr("settings.ms365_local_none"))

    def _on_connect_external_toggled(self, on: bool) -> None:
        """Bật/tắt công tắc tổng cho connector ngoài, và khoá/mở cả bảng theo đó."""
        self.ctx.config.set_connect_external(on)
        self._apply_connect_external_enabled(on)

    def _apply_connect_external_enabled(self, on: bool) -> None:
        """Grey out the per-connector setup when the master switch is off — the
        agent won't connect to any of them anyway."""
        for w in (self._cat_scroll, self.add_btn):
            w.setEnabled(on)

    def _retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn."""
        self.connect_external_sw.setText(tr("connectors.connect_external"))
        self.connect_external_sw.setToolTip(tr("connectors.connect_external_tooltip"))
        self.add_btn.setText(tr("settings.ext_add_btn"))
        self._refresh_ms365_local_status()
        self._reload_connectors()
        self._apply_connect_external_enabled(self.ctx.config.connect_external)
