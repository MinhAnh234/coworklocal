"""Thanh trên cùng và hàng tài khoản — R08-T10.

Bóc từ ``MainWindow``: logo, chọn provider, chọn ngôn ngữ, nút đổi giao diện,
và lối mở hộp thoại Cài đặt.

Cùng lý do mixin như ``nav_rail.py``: các phương thức này đọc/ghi state của cửa
sổ. Xem ghi chú ở đầu file đó.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox, QHBoxLayout, QLabel, QMenu, QPushButton, QToolButton, QVBoxLayout, QWidget
from ...config import PROVIDER_LABELS
from ...i18n import LANGUAGE_SHORT, LANGUAGES, get_language, on_language_changed, set_language, tr
from .branding import ASSETS
from .rail_metrics import _NAV_ROW_GAP, _NAV_ROW_INSET
from ...ui.widgets import tidy_popup
from ...theme import set_active_theme, stylesheet
from ...ui.settings_dialog import SettingsDialog




class TopBarMixin:
    """Thanh trên cùng. Trộn vào MainWindow."""

    def _build_rail_bottom(self, nvl) -> None:
        """Đáy thanh rail: nhóm ghim dưới, nút Cài đặt, hàng tài khoản.

        Nằm ở file thanh trên cùng chứ không phải file rail, vì ba thứ này
        đều là "tài khoản và thiết lập" — cùng mối quan tâm với
        ``_build_account_row`` ngay bên dưới, chỉ khác chỗ đặt trên màn hình.
        """
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton
        from ...i18n import tr
        from ...ui.icons import icon as _icon
        from .rail_metrics import _NAV_ROW_GAP, _NAV_ROW_INSET, _NAV_SETTINGS_GAP

        # Bottom-pinned group: the places you visit occasionally, kept out of the
        # way of the ones you live in. A hairline (styled via #navrailBottom in
        # theme.py) separates the two lists.
        nvl.addWidget(self.nav_bottom, 0)
        # Settings reads as one more row under Dashboard / Giám sát, so its icon
        # and label must start exactly where theirs do. Letting QPushButton place
        # them does not achieve that: the gap it leaves between icon and text is
        # the platform style's, and on macOS it is visibly tighter than the tree
        # rows above — a Windows-tuned nudge only moved the mismatch. So the row
        # is laid out here, in the same two numbers the tree uses: 4px in, 6px
        # between.
        self._nav_settings_btn = QPushButton()
        self._nav_settings_btn.setObjectName("navSettingsBtn")
        self._nav_settings_btn.setFlat(True)
        self._nav_settings_btn.setCursor(Qt.PointingHandCursor)
        self._nav_settings_btn.clicked.connect(self._open_settings)
        srow = QHBoxLayout(self._nav_settings_btn)
        # No vertical padding of its own: ``_rebuild_nav`` pins this button to the
        # nav rows' OWN height, so the 6px a row pads with is already inside
        # that number. Adding it again here made the row taller than the button
        # (28 wanted, 20 given), which both clipped the icon and pushed the text
        # 8px below an even pitch with Dashboard / Giám sát.
        srow.setContentsMargins(_NAV_ROW_INSET, 0, 8, 0)
        srow.setSpacing(_NAV_ROW_GAP)
        self._nav_settings_icon = QLabel()
        self._nav_settings_icon.setPixmap(_icon("settings").pixmap(16, 16))
        self._nav_settings_icon.setFixedSize(16, 16)
        self._nav_settings_text = QLabel(tr("app.settings"))
        srow.addWidget(self._nav_settings_icon)
        srow.addWidget(self._nav_settings_text)
        srow.addStretch(1)
        # The first _rebuild_nav() ran before this button existed (it is what
        # fills the list this row belongs under), so take the height here too.
        self._nav_settings_btn.setFixedHeight(self.nav_bottom.sizeHintForRow(0))
        # Khe TRÊN hàng Cài đặt, xin thẳng từ layout — thanh rail đặt
        # ``setSpacing(0)`` nên không có khoảng nào sẵn, và margin trong QSS thì
        # không mua được pixel nào (xem ``_NAV_SETTINGS_GAP``). Cài đặt là việc
        # khác với nhóm Dashboard/Giám sát ngay trên nó; dán sát vào thì hai thứ
        # đọc thành một khối.
        nvl.addSpacing(_NAV_SETTINGS_GAP)
        nvl.addWidget(self._nav_settings_btn)
        self._account_row = self._build_account_row()

    def _build_topbar(self) -> QWidget:
        """Dựng thanh trên: thương hiệu, bộ chọn provider/ngôn ngữ/theme và hàng tài khoản."""
        bar = QWidget()
        bar.setObjectName("topbar")
        # Styled centrally (see theme._TEMPLATE): flat, with a single hairline
        # separating it from the content below — no card box behind it.
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 10, 12, 10)
        h.setSpacing(10)
        # FPT logo slot in front of the brand text: shown only when a logo
        # image has been dropped into assets/ (see _brand_logo_pixmap) — the
        # brand works text-only until the real artwork is supplied.
        self.logo_img = QLabel()
        logo_pm = self._brand_logo_pixmap()
        if logo_pm is not None:
            self.logo_img.setPixmap(logo_pm)
        else:
            self.logo_img.setVisible(False)
        h.addWidget(self.logo_img)
        self.logo_lbl = QLabel(tr("app.logo"))
        self.logo_lbl.setObjectName("brand")   # styled centrally — see theme._TEMPLATE
        h.addWidget(self.logo_lbl)
        h.addStretch(1)
        # Provider / language / theme / Settings used to live here, five controls
        # wide across the top of every screen. They are per-account settings, not
        # per-screen ones, so they moved to the account row at the foot of the
        # rail (_build_account_row) — same widgets, same handlers, new home.
        return bar
    def _build_account_row(self) -> QWidget:
        """The rail's foot: who you are, and the settings that follow you.

        Nothing new is introduced here — these are the exact widgets the top bar
        used to hold, moved as-is so every existing signal still lands.
        """
        box = QWidget()
        box.setObjectName("navAccount")
        v = QVBoxLayout(box)
        v.setContentsMargins(6, 4, 6, 4)
        v.setSpacing(4)

        who = QHBoxLayout()
        who.setSpacing(4)
        self.account_lbl = QLabel(f"👤 {self._user_name}" if self._user_name else "👤")
        self.account_lbl.setObjectName("hint")
        who.addWidget(self.account_lbl, 1)
        self.language_combo = QComboBox()
        for key in LANGUAGES:
            self.language_combo.addItem(LANGUAGE_SHORT.get(key, key.upper()), key)
            self.language_combo.setItemData(
                self.language_combo.count() - 1, LANGUAGES[key], Qt.ToolTipRole)
        idx = self.language_combo.findData(get_language())
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        tidy_popup(self.language_combo)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        who.addWidget(self.language_combo)
        self.theme_btn = self._build_theme_button()
        who.addWidget(self.theme_btn)
        v.addLayout(who)

        self.provider_lbl = QLabel(tr("app.provider"))
        self.provider_lbl.setObjectName("hint")
        self.provider_lbl.setVisible(False)   # the combo names itself in the rail
        self.provider_combo = QComboBox()
        self.provider_combo.setToolTip(tr("app.provider"))
        for key, label in PROVIDER_LABELS.items():
            self.provider_combo.addItem(label, key)
        tidy_popup(self.provider_combo)
        idx = self.provider_combo.findData(self.ctx.config.active_provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        v.addWidget(self.provider_lbl)
        v.addWidget(self.provider_combo)
        return box
    def _brand_logo_pixmap(self):
        """The FPT logo scaled to top-bar height, or None while no logo file
        exists yet — drop the artwork into src/cowork_local/assets/ under one
        of the _BRAND_LOGO_NAMES and it appears on next launch."""
        from PySide6.QtGui import QPixmap

        for name in self._BRAND_LOGO_NAMES:
            path = ASSETS / name
            if not path.exists():
                continue
            pm = QPixmap(str(path))
            if pm.isNull():
                continue
            return pm.scaledToHeight(self._BRAND_LOGO_HEIGHT, Qt.SmoothTransformation)
        return None
    def _build_theme_button(self) -> QToolButton:
        """A single icon button (System/Dark/Light) replacing the old
        Settings-only theme dropdown — one click applies the choice
        immediately via the existing _apply_theme(), no dialog round-trip."""
        from ...ui.icons import icon as _icon

        btn = QToolButton()
        btn.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(btn)
        self._theme_actions = {}
        for value, icon_name in self._THEME_ICONS.items():
            act = menu.addAction(_icon(icon_name), tr(f"settings.theme_{value}"))
            act.triggered.connect(lambda _checked=False, v=value: self._set_theme(v))
            self._theme_actions[value] = act
        btn.setMenu(menu)
        btn.setIcon(_icon(self._THEME_ICONS.get(self.ctx.config.theme, "monitor")))
        return btn
    def _set_theme(self, value: str) -> None:
        """Đổi theme, ghi cấu hình và áp stylesheet mới lên toàn ứng dụng."""
        from ...ui.icons import icon as _icon

        self.ctx.config.theme = value
        self.ctx.save()
        self._apply_theme()
        self.theme_btn.setIcon(_icon(self._THEME_ICONS.get(value, "monitor")))
    def _on_provider_changed(self, _idx: int) -> None:
        """Đổi provider đang dùng: lưu cấu hình rồi làm mới mọi bề mặt phụ thuộc nó
        (tiêu đề Cowork, bộ chọn model của AI-Edit).
        """
        self.ctx.config.active_provider = self.provider_combo.currentData()
        self.ctx.save()
        self.cowork.refresh_header()
        # Reload the Cowork tab's Agent (Model) list for the newly selected provider.
        self.cowork.refresh_agents()
        self.workspace.refresh_ai_models()   # + the Folder AI-edit model picker
        # Khong bao "dang dung <provider>" o thanh trang thai: chinh bo chon
        # provider nam ngay tren man hinh va da hien thu vua chon, nen dong thong
        # bao chi nhac lai mot thu nguoi dung vua tu tay lam.
    def _lang_busy_overlay(self):
        """The window's busy cover, built on first use.

        Built lazily so a window that never changes language never gets one —
        and so ``_open_settings`` can be checked for "no switch, no flash".
        """
        overlay = getattr(self, "_lang_busy", None)
        if overlay is None:
            from .busy_overlay import BusyOverlay
            overlay = BusyOverlay(self)
            self._lang_busy = overlay
        return overlay

    def _switch_language(self, lang: str) -> None:
        """Apply a new UI language behind a busy cover.

        ``set_language`` runs every registered widget's re-translation on the
        GUI thread, which on a large skill library takes long enough to look
        like a hang. Nothing can raise a cover once that has started (no event
        loop is left running), so it goes up FIRST — see ``busy_overlay.py``.

        The message is read before the switch on purpose: mid-switch the only
        language the user can still read is the one being left behind.
        """
        message = tr("app.lang.switching")
        self.language_combo.setEnabled(False)
        try:
            self._lang_busy_overlay().run_blocking(message, lambda: set_language(lang))
        finally:
            # In a ``finally`` so a listener that raises cannot leave the
            # switcher locked for the rest of the session.
            self.language_combo.setEnabled(True)

    def _on_language_changed(self, _idx: int) -> None:
        """Đổi ngôn ngữ giao diện; trùng ngôn ngữ hiện tại thì bỏ qua để không dựng lại
        toàn bộ chữ vô ích.
        """
        lang = self.language_combo.currentData()
        if not lang or lang == get_language():
            return
        self.ctx.config.language = lang
        self.ctx.save()
        self._switch_language(lang)   # notifies every registered persistent widget
    def _open_settings(self) -> None:
        """Mở hộp thoại Cài đặt; bấm Lưu thì áp lại theme và làm mới thanh trên."""
        dlg = SettingsDialog(self.ctx, self)
        if dlg.exec():
            self._apply_theme()
            # Settings can change the theme too — keep the rail's toggle icon
            # showing the value that is actually in effect.
            from ...ui.icons import icon as _theme_icon
            self.theme_btn.setIcon(
                _theme_icon(self._THEME_ICONS.get(self.ctx.config.theme, "monitor")))
            # Guarded, not left to set_language's own no-op check: the cover
            # around the switch would otherwise flash on every Save.
            if self.ctx.config.language != get_language():
                self._switch_language(self.ctx.config.language)
            # reflect provider/theme/language changes
            i = self.provider_combo.findData(self.ctx.config.active_provider)
            if i >= 0:
                self.provider_combo.setCurrentIndex(i)
            li = self.language_combo.findData(get_language())
            if li >= 0:
                self.language_combo.blockSignals(True)
                self.language_combo.setCurrentIndex(li)
                self.language_combo.blockSignals(False)
            self.cowork.refresh_header()
            self.cowork.refresh_agents()
            self.workspace.refresh_ai_models()   # + the Folder AI-edit model picker
            max_files = int(self.ctx.config.data.get("attachments", {}).get("max_files", 10) or 0)
            self.cowork.composer.set_max_attachments(max_files)
            self.sidebar.refresh()
            self.statusBar().showMessage(tr("app.status.settings_saved"))
    def _apply_theme(self) -> None:
        """Áp theme đang cấu hình lên toàn bộ ứng dụng."""
        app = QApplication.instance()
        if app:
            set_active_theme(self.ctx.config.theme)
            app.setStyleSheet(stylesheet(self.ctx.config.theme))
        # Re-apply theme styles to chat bubbles so they adapt to the new theme.
        self.cowork.apply_theme()
        if getattr(self, "help_agent", None) is not None:
            self.help_agent.apply_theme()   # chat body follows theme (header stays fixed)
