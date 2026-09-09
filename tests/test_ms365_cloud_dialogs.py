"""DF-007 — construction smoke tests for the two new MS365 cloud dialogs.
Not a full characterization suite (see tests/test_monitoring_tab_container.py
for the convention this follows) — just proves each dialog builds against a
real AppConfig/AppContext without touching the network (Graph calls faked via
monkeypatch)."""
from __future__ import annotations

import copy
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication
QDialog = pytest.importorskip("PySide6.QtWidgets").QDialog

from cowork_local.config import AppConfig, DEFAULT_CONFIG
from cowork_local.core import ms365_auth
from cowork_local.core import ms365_graph as graph
from cowork_local.ui.cloud_folder_picker_dialog import CloudFolderPickerDialog
from cowork_local.ui.ms365_signin_dialog import Ms365SignInDialog, ensure_signed_in


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def config(tmp_path):
    return AppConfig(data=copy.deepcopy(DEFAULT_CONFIG), path=tmp_path / "config.json")


def test_signin_dialog_constructs(qapp, config) -> None:
    dialog = Ms365SignInDialog(config)
    assert dialog.windowTitle()


def test_ensure_signed_in_short_circuits_when_already_signed_in(qapp, config, monkeypatch) -> None:
    monkeypatch.setattr(ms365_auth, "is_signed_in", lambda cfg: True)
    assert ensure_signed_in(None, config) is True


def test_cloud_folder_picker_constructs_and_lists_onedrive_root(qapp, config, monkeypatch) -> None:
    monkeypatch.setattr(ms365_auth, "get_access_token", lambda tenant_id, client_id: "fake-token")
    monkeypatch.setattr(graph, "list_onedrive_files", lambda token, path="": [
        {"name": "Documents", "folder": {}},
        {"name": "readme.txt"},
    ])

    dialog = CloudFolderPickerDialog(config)

    assert dialog._tree.topLevelItemCount() == 2
    source = dialog.cloud_source()
    assert source == {"provider": "onedrive", "site_id": "", "site_name": "", "remote_path": ""}


def test_cloud_folder_picker_navigates_into_a_folder(qapp, config, monkeypatch) -> None:
    monkeypatch.setattr(ms365_auth, "get_access_token", lambda tenant_id, client_id: "fake-token")

    def fake_list(token, path=""):
        if path == "":
            return [{"name": "Documents", "folder": {}}]
        if path == "Documents":
            return [{"name": "report.docx"}]
        return []

    monkeypatch.setattr(graph, "list_onedrive_files", fake_list)

    dialog = CloudFolderPickerDialog(config)
    folder_item = dialog._tree.topLevelItem(0)
    dialog._on_item_activated(folder_item, 0)

    assert dialog._current_remote_path() == "Documents"
    assert dialog.cloud_source()["remote_path"] == "Documents"
