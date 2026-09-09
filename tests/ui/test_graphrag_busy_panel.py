"""Vào màn GraphRAG phải có báo "đang tải".

``prewarm()`` chỉ chạy 3 giây sau khi cửa sổ hiện (``main_window.py``), nên bấm
GraphRAG trong 3 giây đầu sẽ gặp ``_ensure_web()`` dựng ``QWebEngineView`` ĐỒNG BỘ
trên GUI thread — đóng băng 1-2 giây mà trước đây không có gì báo.

Vì GUI thread bị chặn, panel phải được ``repaint()`` NGAY, không phải ``update()``:
``update()`` chỉ xếp hàng một lượt vẽ cho vòng lặp sự kiện, mà vòng lặp đó sắp bị
chặn — panel sẽ chỉ hiện ra sau khi hết đóng băng, đúng lúc không còn cần nữa.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="cần PySide6 để dựng widget thật")


class _Renderer:
    """Thay GraphRenderer. Ghi lại panel có đang hiện lúc nó bị gọi hay không."""

    def __init__(self, qapp, web=None, path=""):
        from PySide6.QtCore import QObject, Signal

        class _Sig(QObject):
            graph_rendered = Signal()
            project_changed = Signal()
        self._sig = _Sig()
        self.graph_rendered = self._sig.graph_rendered
        self.project_changed = self._sig.project_changed
        self._hien = False
        self.web = web
        self.path_edit = type("E", (), {"text": lambda _s: path})()
        self.busy_luc_duoc_goi = None
        self._view = None

    def isVisible(self):  # noqa: N802 — khớp API của QWidget
        return self._hien

    def auto_scan_and_fit(self):
        # Chốt điều quan trọng nhất: panel phải hiện TRƯỚC khi việc chặn bắt đầu.
        self.busy_luc_duoc_goi = not self._view._busy.isHidden()


@pytest.fixture
def view(qapp):
    from cowork_local.presentation.graph.structure_graph_view import StructureGraphView
    return StructureGraphView


def _dung(qapp, ViewCls, web=None, path="C:/tmp"):
    """StructureGraphView với renderer bị thay — renderer thật kéo theo QtWebEngine."""
    v = ViewCls.__new__(ViewCls)
    from PySide6.QtWidgets import QWidget
    QWidget.__init__(v)
    v.renderer = _Renderer(qapp, web=web, path=path)
    v.renderer._view = v
    v._workspace_project = None
    v.ctx = type("C", (), {"active_project_id": "default"})()
    v.resize(800, 600)
    v._build_busy_panel()
    return v


# ---- panel bật trước khi việc chặn bắt đầu -------------------------------

def test_panel_hien_TRUOC_khi_dung_khung_xem(qapp, view):
    v = _dung(qapp, view)
    try:
        v.auto_scan_and_fit()

        assert v.renderer.busy_luc_duoc_goi is True, (
            "panel bật sau khi GUI thread đã bị chặn thì người dùng không thấy gì")
    finally:
        v.deleteLater()


def test_chua_dung_khung_xem_thi_bao_dang_tai_khung(qapp, view):
    """Hai giai đoạn, hai thông báo khác nhau."""
    from cowork_local.i18n import tr

    v = _dung(qapp, view, web=None)
    try:
        v.auto_scan_and_fit()
        assert v._busy_label.text() == tr("structure.loading_view")
    finally:
        v.deleteLater()


def test_da_co_khung_xem_thi_bao_dang_quet(qapp, view):
    from cowork_local.i18n import tr

    v = _dung(qapp, view, web=object())
    try:
        v.auto_scan_and_fit()
        assert v._busy_label.text() == tr("structure.scanning")
    finally:
        v.deleteLater()


# ---- panel tắt đúng lúc --------------------------------------------------

def test_panel_tat_khi_do_thi_ve_xong(qapp, view):
    """Tắt theo ``graph_rendered``, không tắt ngay khi hàm trả về — lượt quét
    còn chạy ở luồng nền phía sau."""
    v = _dung(qapp, view)
    try:
        v.auto_scan_and_fit()
        assert v._busy.isHidden() is False

        v.renderer._sig.graph_rendered.emit()

        assert v._busy.isHidden() is True
    finally:
        v.deleteLater()


def test_chua_chon_thu_muc_thi_panel_khong_treo_lai(qapp, view):
    """Không có gì để vẽ thì ``graph_rendered`` không phát — panel phải tự dọn."""
    v = _dung(qapp, view, path="")
    try:
        v.auto_scan_and_fit()

        assert v._busy.isHidden() is True, "panel treo lại mãi mãi"
    finally:
        v.deleteLater()


# ---- panel nằm giữa và theo kích thước ----------------------------------

def test_panel_nam_giua_khung(qapp, view):
    v = _dung(qapp, view)
    try:
        v.auto_scan_and_fit()
        g = v._busy.geometry()

        assert abs(g.center().x() - v.rect().center().x()) <= 1
        assert abs(g.center().y() - v.rect().center().y()) <= 1
    finally:
        v.deleteLater()


def test_doi_kich_thuoc_thi_panel_theo(qapp, view):
    """Gửi ``QResizeEvent`` thật thay vì chỉ gọi ``resize()``.

    Widget chưa ``show()`` thì Qt hoãn việc phát ``resizeEvent`` — mà việc Qt
    phát event là phần của Qt, không phải phần cần kiểm. Cái cần kiểm là hàm
    xử lý event có căn lại panel hay không.
    """
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QResizeEvent

    v = _dung(qapp, view)
    try:
        v.auto_scan_and_fit()
        cu = v.size()
        v.resize(1200, 900)
        v.resizeEvent(QResizeEvent(QSize(1200, 900), cu))

        g = v._busy.geometry()
        assert abs(g.center().x() - v.rect().center().x()) <= 1
        assert abs(g.center().y() - v.rect().center().y()) <= 1
    finally:
        v.deleteLater()


# ---- màu lấy từ theme, không hardcode ------------------------------------

def test_panel_duoc_style_bang_token_trong_theme():
    """Guardrail G4: ngoài theme/ không file nào được đặt tên một màu."""
    from pathlib import Path
    from cowork_local.theme.qss import _TEMPLATE

    assert "QWidget#graphBusy" in _TEMPLATE.template
    src = (Path(__file__).resolve().parents[2]
           / "presentation" / "graph" / "structure_graph_view.py").read_text(encoding="utf-8")
    assert "setStyleSheet" not in src


# ---- đổi project ngay trên màn này thì quét luôn, có panel ---------------

def test_doi_project_khi_man_dang_mo_thi_panel_bat(qapp, view):
    """Renderer quét ngay (không chờ lần ghé sau) nên panel phải bật theo."""
    v = _dung(qapp, view)
    try:
        v.renderer._hien = True
        v.renderer.project_changed.emit()

        assert v._busy.isHidden() is False
    finally:
        v.deleteLater()


def test_doi_project_khi_man_dang_an_thi_khong_bat_panel(qapp, view):
    """Renderer hoãn lượt quét sang lần ghé sau — bật panel lúc này là treo lại."""
    v = _dung(qapp, view)
    try:
        v.renderer._hien = False
        v.renderer.project_changed.emit()

        assert v._busy.isHidden() is True
    finally:
        v.deleteLater()


# ---- đường dẫn quét rỗng thì lấy từ project đang hoạt động ---------------

def test_o_duong_dan_rong_thi_dien_tu_project_dang_chon(qapp, view, monkeypatch, tmp_path):
    """GraphRenderer.auto_scan_and_fit thoát sớm khi ô đường dẫn rỗng, trong khi
    nút Scan lại có đường lùi — vào màn không làm gì, bấm Scan thì chạy."""
    import cowork_local.core.projects as projects

    ws = tmp_path / "ws"
    ws.mkdir()

    class _P:
        project_id = "p1"
        def workspace_dir(self, base=None):
            return ws

    monkeypatch.setattr(projects, "load_project", lambda pid: _P() if pid == "p1" else None)

    v = _dung(qapp, view, path="")
    v.ctx = type("C", (), {"active_project_id": "p1"})()
    v.renderer.path_edit = type("E", (), {
        "_t": "",
        "text": lambda s: s._t,
        "setText": lambda s, t: setattr(s, "_t", t)})()
    try:
        v._ensure_scan_path()

        assert v.renderer.path_edit.text() == str(ws)
    finally:
        v.deleteLater()


def test_da_co_duong_dan_thi_khong_ghi_de(qapp, view):
    v = _dung(qapp, view, path="C:/da-chon")
    v.ctx = type("C", (), {"active_project_id": "p1"})()
    try:
        v._ensure_scan_path()

        assert v.renderer.path_edit.text() == "C:/da-chon"
    finally:
        v.deleteLater()


def test_chua_chon_project_thi_khong_bia_duong_dan(qapp, view):
    """Không lấy cwd() làm đường lùi: quét thư mục làm việc của tiến trình là
    quét một cây không liên quan gì tới project."""
    v = _dung(qapp, view, path="")
    v.ctx = type("C", (), {"active_project_id": "default"})()
    v.renderer.path_edit = type("E", (), {
        "_t": "",
        "text": lambda s: s._t,
        "setText": lambda s, t: setattr(s, "_t", t)})()
    try:
        v._ensure_scan_path()

        assert v.renderer.path_edit.text() == ""
    finally:
        v.deleteLater()
