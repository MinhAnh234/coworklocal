"""Dựng Qt ở chế độ offscreen cho test giao diện.

Offscreen là bắt buộc, không phải cho nhanh: máy dev là máy làm việc thật của
người dùng. Test bật cửa sổ lên là nó nhảy ra trước mặt, che thứ đang mở.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app
