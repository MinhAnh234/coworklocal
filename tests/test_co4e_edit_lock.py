"""DF-002 (phần b) — node đang chạy HOẶC đã chạy xong không cho edit thông
tin trong Node. Trước khi sửa, ``_LOCKED_NODE_STATUSES`` khoá cả STEP_RUNNING
lẫn STEP_DONE, nên một bước đã chạy xong không bao giờ sửa lại được nữa.

Fix: chỉ khoá khi bước ĐANG chạy (STEP_RUNNING) — chạy xong rồi thì mở khoá
trở lại. Test này chốt cả nguồn sự thật (tuple
``co4e_workflow_crud._LOCKED_NODE_STATUSES``) lẫn hành vi ở widget
(``StepConfigPanel.set_locked``), để không bị hồi quy về hành vi cũ.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from cowork_local.core.co4e import (
    STEP_DONE, STEP_ERROR, STEP_IDLE, STEP_PLANNED, STEP_RUNNING,
)
from cowork_local.presentation.co4e.co4e_workflow_crud import _LOCKED_NODE_STATUSES
from cowork_local.presentation.co4e.node_property_panel import StepConfigPanel


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_only_running_status_is_locked() -> None:
    """Một bước đã chạy xong (STEP_DONE) phải sửa lại được — chỉ bước đang
    thực sự chạy (STEP_RUNNING) mới bị khoá."""
    assert _LOCKED_NODE_STATUSES == (STEP_RUNNING,)
    assert STEP_DONE not in _LOCKED_NODE_STATUSES
    assert STEP_IDLE not in _LOCKED_NODE_STATUSES
    assert STEP_ERROR not in _LOCKED_NODE_STATUSES
    assert STEP_PLANNED not in _LOCKED_NODE_STATUSES


def test_set_locked_disables_then_reenables_edit_fields(qapp) -> None:
    panel = StepConfigPanel()
    panel.setEnabled(True)   # panel starts disabled until a step is loaded

    panel.set_locked(True)
    assert not panel.label_edit.isEnabled()
    assert not panel.instructions_edit.isEnabled()
    assert not panel.model_combo.isEnabled()

    panel.set_locked(False)
    assert panel.label_edit.isEnabled()
    assert panel.instructions_edit.isEnabled()
    assert panel.model_combo.isEnabled()
