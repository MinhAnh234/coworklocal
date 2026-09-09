"""DF-007 — browse OneDrive/SharePoint via Microsoft Graph and pick a folder
to use as (a local mirror of) a project's working directory. See
``core/cloud_workspace_sync.py`` for the mirror/sync side and
``ui/ms365_signin_dialog.py`` for the sign-in gate this calls first.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QRadioButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
)

from ..core import ms365_auth
from ..core import ms365_graph as graph
from ..i18n import tr
from .icons import icon
from .ms365_signin_dialog import ensure_signed_in

_ITEM_KIND = Qt.UserRole
_ITEM_NAME = Qt.UserRole + 1


class CloudFolderPickerDialog(QDialog):
    """Chọn "OneDrive của tôi" hoặc tìm 1 site SharePoint, rồi duyệt thư mục
    con của nó; "Chọn thư mục này" trả về thư mục ĐANG HIỂN THỊ (không phải
    dòng đang bôi đen — giống hành vi ``QFileDialog`` khi đang ở trong 1
    thư mục)."""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        ms365 = (config.ms365 if config is not None else {}) or {}
        self._token = ms365_auth.get_access_token(
            ms365.get("tenant_id", ""), ms365.get("client_id", ""))
        self._site_id = ""
        self._site_name = ""
        self._path_parts: list[str] = []  # relative path segments from the drive root

        self.setWindowTitle(tr("cloud_picker.title"))
        self.setModal(True)
        self.resize(520, 480)
        layout = QVBoxLayout(self)

        source_row = QHBoxLayout()
        self._onedrive_radio = QRadioButton(tr("cloud_picker.source_onedrive"))
        self._onedrive_radio.setChecked(True)
        self._onedrive_radio.toggled.connect(self._on_source_toggled)
        self._sharepoint_radio = QRadioButton(tr("cloud_picker.source_sharepoint"))
        source_row.addWidget(self._onedrive_radio)
        source_row.addWidget(self._sharepoint_radio)
        source_row.addStretch(1)
        layout.addLayout(source_row)

        search_row = QHBoxLayout()
        self._site_search = QLineEdit()
        self._site_search.setPlaceholderText(tr("cloud_picker.search_sites_placeholder"))
        self._site_search.setEnabled(False)
        self._site_search.returnPressed.connect(self._search_sites)
        self._search_btn = QPushButton(tr("cloud_picker.search_btn"))
        self._search_btn.setEnabled(False)
        self._search_btn.clicked.connect(self._search_sites)
        search_row.addWidget(self._site_search, 1)
        search_row.addWidget(self._search_btn)
        layout.addLayout(search_row)

        self._path_lbl = QLabel()
        self._path_lbl.setWordWrap(True)
        layout.addWidget(self._path_lbl)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.itemDoubleClicked.connect(self._on_item_activated)
        layout.addWidget(self._tree, 1)

        btn_row = QHBoxLayout()
        self._choose_btn = QPushButton(tr("cloud_picker.choose_here"))
        self._choose_btn.setObjectName("primary")
        self._choose_btn.setIcon(icon("cloud"))
        self._choose_btn.clicked.connect(self.accept)
        self._cancel_btn = QPushButton(tr("cloud_picker.cancel"))
        self._cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch(1)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._choose_btn)
        layout.addLayout(btn_row)

        self._refresh_path_label()
        self._reload()

    # ---- source switching -------------------------------------------------
    def _on_source_toggled(self, _checked: bool) -> None:
        is_sharepoint = self._sharepoint_radio.isChecked()
        self._site_search.setEnabled(is_sharepoint)
        self._search_btn.setEnabled(is_sharepoint)
        self._choose_btn.setEnabled(not is_sharepoint or bool(self._site_id))
        if not is_sharepoint:
            self._site_id = ""
            self._site_name = ""
            self._path_parts = []
            self._refresh_path_label()
            self._reload()

    def _search_sites(self) -> None:
        query = self._site_search.text().strip()
        if not query:
            return
        self._tree.clear()
        try:
            sites = graph.list_sharepoint_sites(self._token, query)
        except graph.Ms365GraphError as exc:
            QMessageBox.warning(self, tr("cloud_picker.title"),
                                 tr("cloud_picker.load_failed", err=str(exc)))
            return
        if not sites:
            item = QTreeWidgetItem([tr("cloud_picker.no_sites")])
            item.setData(0, _ITEM_KIND, "empty")
            self._tree.addTopLevelItem(item)
            return
        for site in sites:
            item = QTreeWidgetItem([site.get("displayName") or site.get("name") or site.get("id", "")])
            item.setIcon(0, icon("globe"))
            item.setData(0, _ITEM_KIND, "site")
            item.setData(0, _ITEM_NAME, site.get("id", ""))
            item.setData(0, Qt.UserRole + 2, site.get("displayName") or site.get("name") or "")
            self._tree.addTopLevelItem(item)
        self._choose_btn.setEnabled(False)  # must pick a site before choosing a folder

    def _on_item_activated(self, item: QTreeWidgetItem, _col: int) -> None:
        kind = item.data(0, _ITEM_KIND)
        if kind == "site":
            self._site_id = item.data(0, _ITEM_NAME)
            self._site_name = item.data(0, Qt.UserRole + 2)
            self._path_parts = []
            self._choose_btn.setEnabled(True)
            self._refresh_path_label()
            self._reload()
        elif kind == "up":
            self._path_parts.pop()
            self._refresh_path_label()
            self._reload()
        elif kind == "folder":
            self._path_parts.append(item.data(0, _ITEM_NAME))
            self._refresh_path_label()
            self._reload()
        # kind == "file": not navigable, double-click does nothing

    # ---- listing ------------------------------------------------------------
    def _current_remote_path(self) -> str:
        return "/".join(self._path_parts)

    def _refresh_path_label(self) -> None:
        if self._sharepoint_radio.isChecked():
            root = self._site_name or tr("cloud_picker.source_sharepoint")
        else:
            root = tr("cloud_picker.source_onedrive")
        parts = "/".join([root] + self._path_parts)
        self._path_lbl.setText(parts)

    def _reload(self) -> None:
        self._tree.clear()
        if self._sharepoint_radio.isChecked() and not self._site_id:
            return  # waiting on a site search/selection
        if self._path_parts:
            up = QTreeWidgetItem([tr("cloud_picker.up")])
            up.setData(0, _ITEM_KIND, "up")
            self._tree.addTopLevelItem(up)
        try:
            if self._sharepoint_radio.isChecked():
                children = graph.list_sharepoint_files(
                    self._token, self._site_id, self._current_remote_path())
            else:
                children = graph.list_onedrive_files(self._token, self._current_remote_path())
        except graph.Ms365GraphError as exc:
            QMessageBox.warning(self, tr("cloud_picker.title"),
                                 tr("cloud_picker.load_failed", err=str(exc)))
            return
        for entry in children:
            name = entry.get("name", "")
            if not name:
                continue
            is_folder = "folder" in entry
            item = QTreeWidgetItem([name])
            item.setIcon(0, icon("folder" if is_folder else "file"))
            item.setData(0, _ITEM_KIND, "folder" if is_folder else "file")
            item.setData(0, _ITEM_NAME, name)
            self._tree.addTopLevelItem(item)

    # ---- result ---------------------------------------------------------
    def cloud_source(self) -> dict:
        """Chỉ gọi sau khi ``exec()`` trả về ``QDialog.Accepted``."""
        if self._sharepoint_radio.isChecked():
            return {
                "provider": "sharepoint", "site_id": self._site_id,
                "site_name": self._site_name, "remote_path": self._current_remote_path(),
            }
        return {"provider": "onedrive", "site_id": "", "site_name": "",
                "remote_path": self._current_remote_path()}


def pick_cloud_folder(parent, config) -> Optional[dict]:
    """Đảm bảo đã đăng nhập MS365 rồi mở dialog duyệt; trả về ``cloud_source``
    dict nếu người dùng xác nhận một thư mục, ``None`` nếu hủy hoặc chưa đăng
    nhập."""
    if not ensure_signed_in(parent, config):
        return None
    dialog = CloudFolderPickerDialog(config, parent)
    if dialog.exec() == QDialog.Accepted:
        return dialog.cloud_source()
    return None
