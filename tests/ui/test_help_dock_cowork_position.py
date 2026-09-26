"""Ở tab Cowork, nút trợ lý AI luôn nằm ngay trên ô chat, ở góc phải — kể cả trên
màn hình lớn (27 inch trở lên).

Trước đây nút chỉ được nâng lên khi ô chat nằm ngay dưới nó, và phép thử đó trừ
nhầm toạ độ của cửa sổ trên màn hình: cửa sổ đặt giữa một màn hình lớn (x lớn)
thì phép thử trượt, nút rơi xuống góc dưới cùng, đè lên hàng nút của ô chat.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6", reason="cần PySide6 để dựng cửa sổ thật")


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    from cowork_local.core import projects as projects_mod
    from cowork_local.core.projects import new_project
    from cowork_local.presentation.shell.bootstrap import build_config, build_context
    from cowork_local.presentation.shell.main_window import MainWindow

    monkeypatch.setattr(projects_mod, "PROJECTS_DIR", tmp_path / "projects")
    config_path = tmp_path / "config.json"
    build_config(config_path)
    project = new_project("Alpha", directory=projects_mod.PROJECTS_DIR)
    win = MainWindow(build_context(config_path))
    win.show()
    win.workspace.choose_project(project.project_id)
    win._goto(win._ROW_WORKSPACE, win.workspace._cowork_tab_idx)
    qapp.processEvents()
    yield win
    win.close()


@pytest.mark.parametrize("pos, size", [
    ((0, 0), (1366, 768)),          # laptop, cửa sổ đầy màn hình
    ((640, 280), (2560, 1440)),     # màn 27"+, cửa sổ đặt giữa màn hình
    ((1200, 500), (3440, 1440)),    # màn siêu rộng
])
def test_dock_sits_above_the_composer_on_cowork(window, qapp, pos, size):
    win = window
    assert win.workspace.current_subtab() == win.workspace._cowork_tab_idx
    win.move(*pos)
    win.resize(*size)
    qapp.processEvents()
    win._update_dock_guard()
    win.help_agent.reposition()

    dock = win.help_agent
    comp = win.cowork.composer
    comp_top = comp.mapTo(win, comp.rect().topLeft()).y()
    assert dock.geometry().bottom() < comp_top            # nằm TRÊN ô chat
    assert win.width() - dock.geometry().right() - 1 == 18  # vẫn sát mép phải


def test_first_show_on_a_big_centred_window_still_lifts_the_dock(window, qapp):
    """Lúc mở app, showEvent tính khoảng chừa khi nút còn ở chỗ tạm (tính theo cỡ
    cửa sổ lúc dựng), còn cửa sổ thì đã được đặt giữa một màn hình lớn (x lớn).
    Phép thử cũ trừ toạ độ màn hình của cửa sổ ra khỏi toạ độ của nút, kết luận
    "ô chat không nằm dưới nút" và để nút rơi xuống góc dưới cùng."""
    win = window
    win.resize(2560, 1440)
    qapp.processEvents()
    win.help_agent.move(570, 0)          # chỗ tạm lúc mới dựng
    win.move(900, 300)                   # cửa sổ đặt giữa màn hình lớn
    qapp.processEvents()
    win._update_dock_guard()
    assert win.help_agent._bottom_guard > 0
    win.help_agent.reposition()
    comp = win.cowork.composer
    assert win.help_agent.geometry().bottom() < comp.mapTo(win, comp.rect().topLeft()).y()
