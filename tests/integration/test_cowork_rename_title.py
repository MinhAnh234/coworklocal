"""Đổi tên hội thoại ở cột lịch sử thì thanh tiêu đề Cowork đổi theo ngay.

Trước đây nhãn tiêu đề giữ tên cũ cho tới khi người dùng mở lại hội thoại, và
``self.title`` cũ còn ghi đè tên mới ở lượt chat kế tiếp.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cowork_local.config import AppConfig               # noqa: E402
from cowork_local.presentation.chat.chat_helpers import clip_chars  # noqa: E402
from cowork_local.state import AppContext               # noqa: E402

pytest.importorskip("PySide6", reason="Qt is required for the integration suite")


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def cowork(qt_app, tmp_path: Path):
    from cowork_local.ui.cowork_tab import CoworkTab

    tab = CoworkTab(AppContext(AppConfig.load(tmp_path / "config.json")))
    yield tab
    tab.deleteLater()


def test_clip_chars_keeps_ten_characters():
    assert clip_chars("Tên ngắn") == "Tên ngắn"
    assert clip_chars("0123456789") == "0123456789"
    assert clip_chars("0123456789AB") == "0123456789…"
    assert clip_chars("Dự án mới toanh") == "Dự án mới…"   # không để khoảng trắng trước "…"


def test_rename_of_open_conversation_updates_header(cowork):
    cowork.load_conversation({"session_id": "s1", "title": "Tên cũ", "messages": []})
    assert cowork._title_lbl.text() == "Tên cũ"

    cowork.apply_renamed_title("s1", "Tên mới")

    assert cowork.title == "Tên mới"          # lượt chat sau lưu bằng tên mới
    assert cowork._title_lbl.text() == "Tên mới"


def test_rename_of_other_conversation_is_ignored(cowork):
    cowork.load_conversation({"session_id": "s1", "title": "Đang mở", "messages": []})
    cowork.apply_renamed_title("s2", "Khác")
    assert cowork._title_lbl.text() == "Đang mở"


def test_long_title_is_clipped_with_full_tooltip(cowork):
    long_title = "Báo cáo doanh thu quý 3"
    cowork.load_conversation({"session_id": "s1", "title": "x", "messages": []})
    cowork.apply_renamed_title("s1", long_title)
    assert cowork._title_lbl.text() == "Báo cáo do…"
    assert cowork._title_lbl.toolTip() == long_title


def test_history_list_clips_title_to_ten_chars(qt_app, tmp_path):
    from PySide6.QtCore import Qt

    from cowork_local.core.history import save_conversation
    from cowork_local.ui.sidebar import HistorySidebar

    ctx = AppContext(AppConfig.load(tmp_path / "config.json"))
    ctx.config.data.setdefault("history", {})["custom_dir"] = str(tmp_path / "history")
    assert ctx.config.history_dir() == tmp_path / "history"   # không đọc lịch sử thật
    title = "Báo cáo doanh thu quý 3"
    save_conversation(tmp_path / "history", "cowork", "s1",
                      [{"role": "user", "content": "hi"}], title, project_id="p-test")
    sb = HistorySidebar(ctx)
    sb._project_filter = "p-test"   # chỉ đọc history_dir() tạm, không gộp các project thật
    sb.refresh()
    items = []
    stack = [sb.tree.topLevelItem(i) for i in range(sb.tree.topLevelItemCount())]
    while stack:
        it = stack.pop()
        if it.data(0, Qt.UserRole):
            items.append(it)
        stack.extend(it.child(i) for i in range(it.childCount()))
    assert len(items) == 1
    assert items[0].text(0).splitlines()[0] == "Báo cáo do…"
    assert items[0].toolTip(0) == title
    assert items[0].data(0, Qt.UserRole + 3) == title   # đổi tên vẫn điền tên đầy đủ
    sb.deleteLater()
