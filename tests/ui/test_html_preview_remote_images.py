"""Xem trước HTML trong tab Folder phải hiện được ảnh lấy từ web khi mạng mở.

Tệp được nạp với base URL ``file://``; Qt mặc định cấm trang cục bộ tải bất kỳ
tài nguyên web nào nếu ``LocalContentCanAccessRemoteUrls`` tắt, nên ảnh
``<img src="https://...">`` không bao giờ hiện, kể cả khi đã mở Internet.
Việc chặn khi bật "Chặn mạng" là của bộ chặn request, không phải của cờ này.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWebEngineWidgets", reason="cần Qt WebEngine")

from cowork_local.presentation.shared import HAS_WEB_ENGINE  # noqa: E402

pytestmark = pytest.mark.skipif(not HAS_WEB_ENGINE, reason="WebEngine không dùng được ở đây")


def test_trang_xem_truoc_cho_phep_tai_anh_tu_web(qapp):
    from PySide6.QtWebEngineCore import QWebEngineSettings
    from PySide6.QtWebEngineWidgets import QWebEngineView

    from cowork_local.presentation.folder import offline_web_page as owp

    view = QWebEngineView()
    try:
        owp.install_offline_page(view)
        profile = view.page().profile()
        assert profile is owp.preview_profile()
        assert profile.settings().testAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls)
        assert isinstance(owp._blocker, owp.RemoteRequestBlocker)
    finally:
        view.deleteLater()


def test_profile_song_lau_hon_moi_trang(qapp):
    """Profile do view sở hữu bị huỷ TRƯỚC trang: Qt cảnh báo "Release of
    profile requested but WebEnginePage still not deleted" rồi app có thể văng
    (0xc0000409 trong Qt6Core.dll) khi chuyển tab. Profile phải thuộc về app."""
    from PySide6.QtWebEngineWidgets import QWebEngineView

    from cowork_local.presentation.folder import offline_web_page as owp

    view = QWebEngineView()
    try:
        owp.install_offline_page(view)
        assert view.page().parent() is view
        assert owp.preview_profile().parent() is qapp
    finally:
        view.deleteLater()
