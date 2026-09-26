"""Nút trợ lý AI kéo đi đâu cũng được, bấm vẫn mở chat, và nhớ vị trí."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def dock(qt_app, tmp_path):
    from PySide6.QtWidgets import QWidget

    from cowork_local.config import AppConfig
    from cowork_local.state import AppContext
    from cowork_local.ui.help_agent_widget import HelpAgentWidget

    win = QWidget()
    win.resize(1000, 700)
    ctx = AppContext(AppConfig.load(tmp_path / "config.json"))
    d = HelpAgentWidget(ctx, win, user_name="t")
    win.show()
    qt_app.processEvents()
    yield d, win, ctx
    win.close()
    win.deleteLater()


def _move_events_follow_widget(launcher, dx, dy):
    """QTest.mouseMove dùng toạ độ của widget — widget đã bị dời theo, nên gửi
    sự kiện toàn cục thẳng tới filter để mô phỏng đúng một cú kéo."""
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication

    g0 = QPointF(launcher.mapToGlobal(launcher.rect().center()))

    def send(kind, g, buttons):
        local = QPointF(launcher.mapFromGlobal(g.toPoint()))
        ev = QMouseEvent(kind, local, g, Qt.LeftButton, buttons, Qt.NoModifier)
        QApplication.sendEvent(launcher, ev)

    send(QEvent.MouseButtonPress, g0, Qt.LeftButton)
    for i in range(1, 6):
        send(QEvent.MouseMove, g0 + QPointF(dx * i / 5, dy * i / 5), Qt.LeftButton)
    send(QEvent.MouseButtonRelease, g0 + QPointF(dx, dy), Qt.NoButton)


def test_default_position_is_bottom_right(dock):
    d, win, _ = dock
    assert d.geometry().right() == win.width() - 18 - 1
    assert d.geometry().bottom() == win.height() - 18 - 1


def test_drag_moves_dock_without_opening_chat(dock):
    d, win, ctx = dock
    before = d.pos()
    _move_events_follow_widget(d.launcher, -400, -300)
    assert d.pos() == before + type(before)(-400, -300)
    assert d._state == "launcher"                   # kéo không phải bấm
    assert ctx.config.data["help_agent"]["anchor"] == [18 + 400, 18 + 300]


def test_position_is_kept_on_resize_and_when_panel_opens(dock):
    d, win, _ = dock
    _move_events_follow_widget(d.launcher, -400, -300)
    win.resize(1200, 800)
    d.reposition()
    assert win.width() - d.geometry().right() - 1 == 418
    assert win.height() - d.geometry().bottom() - 1 == 318
    d.launcher.click()                              # bấm thường vẫn mở chat
    assert d._state == "panel"
    assert d.geometry().left() >= 0 and d.geometry().top() >= 0


def test_drag_is_clamped_inside_window(dock):
    d, win, _ = dock
    _move_events_follow_widget(d.launcher, -5000, -5000)
    assert d.pos().x() == 0 and d.pos().y() == 0


def test_saved_position_is_restored(qt_app, tmp_path):
    from PySide6.QtWidgets import QWidget

    from cowork_local.config import AppConfig
    from cowork_local.state import AppContext
    from cowork_local.ui.help_agent_widget import HelpAgentWidget

    ctx = AppContext(AppConfig.load(tmp_path / "config.json"))
    ctx.config.data["help_agent"] = {"anchor": [300, 200]}
    win = QWidget()
    win.resize(1000, 700)
    d = HelpAgentWidget(ctx, win, user_name="t")
    d.reposition()
    assert win.width() - d.geometry().right() - 1 == 300
    assert win.height() - d.geometry().bottom() - 1 == 200
    win.deleteLater()


def test_dock_is_masked_to_its_round_shape(dock):
    """Trên nền QtWebEngine (tab GraphRAG), phần trong suốt quanh nút tròn bị tô
    đen thành ô vuông. Mask cắt bỏ hẳn phần đó."""
    from PySide6.QtCore import QPoint

    d, win, _ = dock
    mask = d.mask()
    assert d._state == "launcher"
    assert mask.contains(QPoint(d.width() // 2, d.height() // 2))   # tâm hình tròn
    for corner in (QPoint(0, 0), QPoint(d.width() - 1, 0),
                   QPoint(0, d.height() - 1), QPoint(d.width() - 1, d.height() - 1)):
        assert not mask.contains(corner)                              # 4 góc vuông bị cắt

    d.launcher.click()                                                # mở panel
    assert d._state == "panel"
    assert d.mask().boundingRect().size() == d.size()                 # panel không bị cắt mất
