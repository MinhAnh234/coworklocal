"""Hộp thoại Cài đặt — khung lắp ráp.

Năm mục, mỗi mục một trang: Chung, AI Provider, Bảo mật sandbox, Tham số,
Auto Model Routing. Bốn mục đầu... đúng hơn: bốn trong năm mục đã bóc sang
``presentation/settings/`` (R08-T07); file này còn giữ mục Bảo mật sandbox,
phần lắp ráp danh sách mục bên trái, và ``_save`` gọi ``apply_to`` của từng
widget con.

Không còn phần Connector nào ở đây: nó đã dời sang Monitoring → Tools →
Connector từ trước. Ngày 25/08 dọn nốt 108 dòng MS365 chết còn sót lại của
lần dời đó — năm hàm gọi lẫn nhau, không đường vào, và đọc ba thuộc tính
chưa từng được gán nên gọi vào là AttributeError.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QListWidget, QListWidgetItem,
    QScrollArea, QSpinBox,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ..i18n import tr
from .dialog_buttons import dialog_buttons
from .widgets import ToggleSwitch


from ..presentation.settings.general_settings_widget import GeneralSettingsWidget
from ..presentation.settings.provider_settings_widget import ProviderSettingsWidget
from ..presentation.settings.parameter_settings_widget import ParameterSettingsWidget
from ..presentation.settings.routing_settings_widget import RoutingSettingsWidget
from ..presentation.settings.about_widget import AboutSettingsWidget


class SettingsDialog(QDialog):
    """Hộp thoại Cài đặt: cột mục lục bên trái, các trang bên phải
    (Nhà cung cấp · Connectors · Định tuyến · Tham số · Chung).
    """
    def __init__(self, ctx, parent=None):
        """Hộp thoại Cài đặt, ghép các nhóm thiết lập.

        Có nút thu nhỏ (không phải mặc định của hộp thoại Qt) vì màn này hay được để
        mở trong lúc người dùng làm việc ở cửa sổ chính.
        """
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle(tr("settings.title"))
        self.setMinimumWidth(560)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
        )
        self.setSizeGripEnabled(True)
        # Group boxes are styled app-wide (see theme._TEMPLATE); this dialog
        # used to re-declare them and drifted out of sync with the rest.
        data = ctx.config.data

        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        # Never sideways: the content must fit the width it is given and scroll
        # only downwards. Anything too wide has to shrink (see _model_combo and
        # _with_load), not push a second scrollbar onto the user.
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._content = QWidget()
        root = QVBoxLayout(self._content)

        # --- Chung: ngôn ngữ, giao diện, khay ---
        # Đã bóc sang presentation/settings/general_settings_widget.py (R08-T07).
        self._general_box = GeneralSettingsWidget(self.ctx)
        root.addWidget(self._general_box)

        self._load_workers = []

        # --- AI Provider ---
        # Đã bóc sang presentation/settings/provider_settings_widget.py (R08-T07).
        prov_group = ProviderSettingsWidget(self.ctx)
        self._provider_page = prov_group
        root.addWidget(prov_group)

        # --- Sandbox Security Layer ---
        sec = ctx.config.agent_security
        self.sandbox_group = QGroupBox(tr("settings.group.sandbox"))
        sbl = QVBoxLayout(self.sandbox_group)

        # Nhóm này KHÔNG còn khoá bằng mật khẩu: bốn công tắc dưới đây bật/tắt
        # tự do. Khoá cũ chỉ là rào chống bấm nhầm ở phía giao diện, không phải
        # cơ chế bảo mật thật (rào thật nằm ở sandbox lúc chạy lệnh), nên bỏ đi
        # theo yêu cầu thay vì giữ một bước nhập mật khẩu không bảo vệ được gì.
        self.sandbox_confirm = ToggleSwitch(tr("settings.sandbox_confirm_commands"))
        self.sandbox_confirm.setChecked(bool(sec.get("cowork_confirm_commands", False)))
        self.sandbox_confirm.setToolTip(tr("settings.sandbox_confirm_commands_tooltip"))
        sbl.addWidget(self.sandbox_confirm)

        self.sandbox_block_network = ToggleSwitch(tr("settings.sandbox_block_network"))
        self.sandbox_block_network.setChecked(bool(sec.get("block_network", True)))
        self.sandbox_block_network.setToolTip(tr("settings.sandbox_block_network_tooltip"))
        sbl.addWidget(self.sandbox_block_network)

        # "Allow the agent to fetch URLs" + the live "Test Internet" self-test
        # moved to Monitoring → Tools → Tool (they govern a tool capability, so
        # they belong with the other tool toggles — see ToolsAdminTab).

        # --- Enable/Disable Agent Security ---
        self.sec_enabled = ToggleSwitch(tr("settings.sec_enabled"))
        self.sec_enabled.setChecked(bool(sec.get("enabled", True)))
        self.sec_enabled.setToolTip(tr("settings.sec_enabled_tooltip"))
        sbl.addWidget(self.sec_enabled)

        # --- AI Command Check toggle ---
        self.ai_check = ToggleSwitch(tr("settings.ai_check"))
        self.ai_check.setChecked(bool(sec.get("command_ai_check", False)))
        self.ai_check.setToolTip(tr("settings.ai_check_tooltip"))
        sbl.addWidget(self.ai_check)

        # Resource limits (CPU/Memory/Disk I/O) moved to the Parameter group
        # below — see _param_section("settings.group.sandbox_limits").

        root.addWidget(self.sandbox_group)

        # Connectors (MCP / REST API) are managed entirely in Monitoring → Tools
        # for the dead-but-retained MS365 OAuth sign-in handlers below.)

        # --- Parameter ---
        # Đã bóc sang presentation/settings/parameter_settings_widget.py (R08-T07).
        param_group = ParameterSettingsWidget(self.ctx)
        self._param_page = param_group
        root.addWidget(param_group)

        # ---- Auto Model Routing ------------------------------------------
        # Đã bóc sang presentation/settings/routing_settings_widget.py (R08-T07).
        routing_group = RoutingSettingsWidget(self.ctx)
        self._routing_page = routing_group
        root.addWidget(routing_group)


        # Left list + right panel: one group on screen at a time, the way the
        # audit page's mock-up shows it. The five rows are the five real group
        # boxes, so "which group am I in, how many left" is answerable at a
        # glance instead of by scrolling to find out.
        from .widgets import section_panels


        # Giới thiệu đứng CUỐI: nó không có thiết lập nào để đổi, nên đặt trước
        # các mục thao tác được sẽ đẩy chúng xuống mà không được gì.
        self._about_page = AboutSettingsWidget(self.ctx)
        root.addWidget(self._about_page)

        pages = []
        for label, widget in ((tr("settings.group.general"), self._general_box),
                              (tr("settings.group.provider"), prov_group),
                              (tr("settings.group.sandbox"), self.sandbox_group),
                              (tr("settings.group.parameter"), param_group),
                              (tr("routing.settings_group"), routing_group),
                              (tr("settings.group.about"), self._about_page)):
            root.removeWidget(widget)
            page = QWidget()
            pv = QVBoxLayout(page)
            pv.setContentsMargins(4, 4, 4, 4)
            pv.addWidget(widget)
            pv.addStretch(1)
            wrap = QScrollArea()
            wrap.setWidgetResizable(True)
            wrap.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            wrap.setWidget(page)
            pages.append((label, wrap))
        self.section_list, self.section_stack = section_panels(pages)
        scroll.setParent(None)
        body = QHBoxLayout()
        body.setSpacing(10)
        body.addWidget(self.section_list)
        body.addWidget(self.section_stack, 1)
        outer.addLayout(body, 1)
        self._content = self._general_box       # kept for other callers
        # Floor the dialog at the width its WIDEST page needs, at the current
        # font. On a 125%/150% display everything is wider, and without this the
        # form was simply cut off instead of the window refusing to get smaller.
        widest = max(w.widget().sizeHint().width() for _lab, w in pages)
        self.setMinimumWidth(self.section_list.width() + widest + 60)

        buttons = dialog_buttons(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        from .widgets import guard_wheel
        guard_wheel(self)

        screen = QGuiApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            self.resize(640, min(740, avail.height() - 80))
            self.setMaximumHeight(avail.height())

    # ---- cầu tương thích sau khi bóc Routing -----------------------------
    # Năm checker trong tools/ và bài đặc tả đọc thẳng self.routing_*. Giữ tên
    # cũ trỏ vào widget mới để việc bóc không kéo theo sửa chỗ khác — đây là
    # đổi chỗ ở, không đổi hành vi. Bỏ được khi tools/ chuyển sang đọc
    # self._routing_page.
    provider_combo = property(lambda self: self._provider_page.provider_combo)
    prov_base = property(lambda self: self._provider_page.prov_base)
    prov_key = property(lambda self: self._provider_page.prov_key)
    prov_model = property(lambda self: self._provider_page.prov_model)
    prov_status = property(lambda self: self._provider_page.prov_status)
    language_combo = property(lambda self: self._general_box.language_combo)
    theme_combo = property(lambda self: self._general_box.theme_combo)
    tray_chk = property(lambda self: self._general_box.tray_chk)
    notify_chk = property(lambda self: self._general_box.notify_chk)
    attach_files = property(lambda self: self._param_page.attach_files)
    attach_tokens = property(lambda self: self._param_page.attach_tokens)
    struct_nodes = property(lambda self: self._param_page.struct_nodes)
    struct_edges = property(lambda self: self._param_page.struct_edges)
    sandbox_cpu = property(lambda self: self._param_page.sandbox_cpu)
    sandbox_memory = property(lambda self: self._param_page.sandbox_memory)
    sandbox_disk = property(lambda self: self._param_page.sandbox_disk)
    routing_mode = property(lambda self: self._routing_page.mode)
    routing_policy = property(lambda self: self._routing_page.policy)
    routing_min_gain = property(lambda self: self._routing_page.min_gain)
    routing_timeout = property(lambda self: self._routing_page.timeout)
    routing_interval = property(lambda self: self._routing_page.interval)
    routing_concurrency = property(lambda self: self._routing_page.concurrency)
    routing_judge = property(lambda self: self._routing_page.judge)
    routing_reassess_btn = property(lambda self: self._routing_page.reassess_btn)

    # ---- helpers -----------------------------------------------------


    @staticmethod
    def _group(title: str, rows) -> QGroupBox:
        """Dựng một nhóm có tiêu đề chứa các hàng nhãn–điều khiển."""
        box = QGroupBox(title)
        form = QFormLayout(box)
        for label, widget in rows:
            form.addRow(label, widget)
        return box






    # ---- MS365 zero-config sign-in ("connect like Claude") ---------------







    def _save(self) -> None:
        """Gom cấu hình từ mọi trang con rồi ghi xuống đĩa."""
        data = self.ctx.config.data
        self._provider_page.apply_to(data)
        self._general_box.apply_to(data)


        # NOTE: allow_url_fetch is managed in Monitoring → Tools → Tool now
        # (persisted there directly), so it is intentionally not written here.
        data.setdefault("agent_security", {}).update({
            "enabled": self.sec_enabled.isChecked(),
            "cowork_confirm_commands": self.sandbox_confirm.isChecked(),
            "block_network": self.sandbox_block_network.isChecked(),
            "command_ai_check": self.ai_check.isChecked(),
            "command_whitelist": [],
        })
        self._param_page.apply_limits_to(data["agent_security"])
        self._param_page.apply_to(data)

        self._routing_page.apply_to(data)

        self.ctx.save()

        # Force-reload config so all parts of the app pick up the new settings immediately
        self.ctx.config._data = None  # invalidate cache
        self.ctx.config._agent_security = None

        self.accept()