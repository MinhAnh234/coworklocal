"""Đổi ngôn ngữ phải có lớp phủ "đang xử lý" — và chỉ khi nó đáng có.

``set_language()`` chạy ĐỒNG BỘ trên GUI thread: nó gọi lần lượt mọi callback
đã đăng ký qua ``on_language_changed``. Trong lúc đó không có vòng lặp sự kiện,
nên không ``QTimer`` nào bắn được và không thanh tiến trình nào quay được — lớp
phủ phải được ``repaint()`` NGAY, không phải ``update()``.

Cùng lý do đó, lớp phủ không thể "đợi xem có chậm không rồi mới hiện": khi việc
chặn đã bắt đầu thì không còn ai chạy để bật nó lên. Thứ duy nhất đo được là
LẦN ĐỔI TRƯỚC. Vì vậy chính sách là: lần đầu trong phiên thì luôn hiện (thận
trọng), các lần sau chỉ hiện khi lần trước đã đủ chậm để người ta kịp nhận ra.
Máy nhanh vì thế nháy đúng một lần rồi thôi, thay vì nháy mãi mãi.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="cần PySide6 để dựng widget thật")

from cowork_local.presentation.shell import top_bar as top_bar_mod


class _Ctx:
    """Ngữ cảnh tối thiểu mà ``_switch_language``/``_open_settings`` cần."""

    def __init__(self, language: str = "vi") -> None:
        self.config = type("C", (), {})()
        self.config.language = language
        self.config.active_provider = "p"
        self.config.theme = "dark"
        self.config.data = {}
        self.so_lan_luu = 0

    def save(self) -> None:
        self.so_lan_luu += 1


class _Any:
    """Nuốt mọi lời gọi.

    ``_open_settings`` còn làm mới sidebar/cowork/workspace sau khi đổi ngôn
    ngữ; không thứ nào trong số đó là thứ đang được kiểm ở đây.
    """

    def __getattr__(self, name):
        return _Any()

    def __call__(self, *a, **k):
        return _Any()


def _dung(qapp):
    """Một ``QMainWindow`` thật có mang ``TopBarMixin`` — đúng ``self`` mà mixin
    nhận trong sản phẩm, nên lớp phủ làm con của cửa sổ chính y như ``Toast``."""
    from PySide6.QtWidgets import QComboBox, QMainWindow

    class W(top_bar_mod.TopBarMixin, QMainWindow):
        _THEME_ICONS = {"system": "monitor", "dark": "moon", "light": "sun"}

    w = W()
    w.resize(900, 700)
    w.ctx = _Ctx()
    combo = QComboBox()
    for code in ("en", "ja", "vi"):
        combo.addItem(code.upper(), code)
    combo.setCurrentIndex(combo.findData("vi"))
    w.language_combo = combo
    pcombo = QComboBox()
    pcombo.addItem("P", "p")
    w.provider_combo = pcombo
    return w


def _dong_ho(*moc):
    """Đồng hồ giả trả lần lượt các mốc thời gian (giây) cho trước."""
    it = iter(moc)
    return lambda: next(it)


@pytest.fixture
def dat_ngon_ngu():
    """Đặt ngôn ngữ hiện tại mà KHÔNG phát tán cho listener.

    ``set_language()`` gọi mọi callback đã đăng ký — trong một phiên pytest đầy
    đủ, danh sách đó chứa widget của các test khác. Ở đây chỉ cần biết ``tr()``
    đang trả về ngôn ngữ nào.
    """
    from cowork_local import i18n as i18n_mod

    cu = i18n_mod._current

    def dat(code: str) -> None:
        i18n_mod._current = code

    yield dat
    i18n_mod._current = cu


# ---- lớp phủ bật TRƯỚC khi việc chặn bắt đầu -----------------------------

def test_overlay_hien_truoc_khi_set_language_chan(qapp, monkeypatch, dat_ngon_ngu):
    """Đi qua đúng đường người dùng bấm: combo ngôn ngữ ở chân nav rail.

    ``isHidden()`` chứ không ``isVisible()``: cửa sổ cha chưa ``show()`` thì
    ``isVisible()`` của widget con luôn False, đúng idiom mà
    ``test_graphrag_busy_panel.py:41`` đã dùng.
    """
    dat_ngon_ngu("vi")
    w = _dung(qapp)
    ghi = {}

    def probe(lang):
        ghi["hien"] = not w._lang_busy.isHidden()

    monkeypatch.setattr(top_bar_mod, "set_language", probe)
    try:
        w.language_combo.setCurrentIndex(w.language_combo.findData("en"))
        w._on_language_changed(0)

        assert ghi["hien"] is True, (
            "lớp phủ bật sau khi GUI thread đã bị chặn thì người dùng không thấy gì")
    finally:
        w.deleteLater()


def test_nguoi_dung_that_su_nhin_thay_lop_phu(qapp, monkeypatch, dat_ngon_ngu):
    """Cửa sổ đã hiện thì ``isVisible()`` mới có nghĩa — chốt luôn mức đó."""
    dat_ngon_ngu("vi")
    w = _dung(qapp)
    ghi = {}

    def probe(lang):
        ghi["hien"] = w._lang_busy.isVisible()

    monkeypatch.setattr(top_bar_mod, "set_language", probe)
    w.show()
    try:
        w._switch_language("en")

        assert ghi["hien"] is True
    finally:
        w.hide()
        w.deleteLater()


def test_overlay_tat_sau_khi_doi_xong(qapp, monkeypatch, dat_ngon_ngu):
    dat_ngon_ngu("vi")
    w = _dung(qapp)
    monkeypatch.setattr(top_bar_mod, "set_language", lambda lang: None)
    try:
        w._switch_language("en")

        assert w._lang_busy.isHidden() is True
    finally:
        w.deleteLater()


def test_callback_nem_loi_van_tat_overlay(qapp, monkeypatch, dat_ngon_ngu):
    """``i18n/__init__.py:68`` chỉ nuốt ``RuntimeError``. Một listener ném loại
    khác sẽ xuyên qua ``set_language()`` — không có ``try/finally`` thì lớp phủ
    treo lại trên màn hình vĩnh viễn."""
    dat_ngon_ngu("vi")
    w = _dung(qapp)

    def probe(lang):
        raise ValueError("một listener nào đó hỏng")

    monkeypatch.setattr(top_bar_mod, "set_language", probe)
    try:
        with pytest.raises(ValueError):
            w._switch_language("en")

        assert w._lang_busy.isHidden() is True, "lớp phủ treo lại mãi mãi"
        assert w.language_combo.isEnabled() is True, "combo khoá lại mãi mãi"
    finally:
        w.deleteLater()


# ---- chữ hiện bằng NGÔN NGỮ CŨ -------------------------------------------

def _chu_luc_chan(qapp, monkeypatch, dat_ngon_ngu, tu: str, sang: str) -> str:
    """Chữ trên lớp phủ tại thời điểm việc chặn bắt đầu.

    Probe đổi ``_current`` thật, y như ``set_language()`` làm, nên nếu ``tr()``
    bị gọi SAU lượt đổi thì chữ sẽ ra ngôn ngữ mới và test đỏ.
    """
    from cowork_local import i18n as i18n_mod

    dat_ngon_ngu(tu)
    w = _dung(qapp)
    ghi = {}

    def probe(lang):
        i18n_mod._current = lang
        ghi["chu"] = w._lang_busy.text()

    monkeypatch.setattr(top_bar_mod, "set_language", probe)
    try:
        w._switch_language(sang)
        return ghi["chu"]
    finally:
        w.deleteLater()


def test_chu_hien_bang_ngon_ngu_cu(qapp, monkeypatch, dat_ngon_ngu):
    from cowork_local.i18n import STRINGS

    chu = _chu_luc_chan(qapp, monkeypatch, dat_ngon_ngu, tu="vi", sang="en")

    assert chu == STRINGS["app.lang.switching"]["vi"]


def test_chu_hien_bang_ngon_ngu_cu_chieu_nguoc(qapp, monkeypatch, dat_ngon_ngu):
    from cowork_local.i18n import STRINGS

    chu = _chu_luc_chan(qapp, monkeypatch, dat_ngon_ngu, tu="en", sang="vi")

    assert chu == STRINGS["app.lang.switching"]["en"]


def test_i18n_du_ba_ngon_ngu():
    from cowork_local.i18n import STRINGS

    assert set(STRINGS["app.lang.switching"]) >= {"en", "ja", "vi"}


# ---- hình dạng: phủ kín cửa sổ, khoá combo -------------------------------

def test_overlay_phu_kin_cua_so(qapp, monkeypatch, dat_ngon_ngu):
    """Phủ nửa vời thì người dùng vẫn bấm được vào phần còn lại."""
    dat_ngon_ngu("vi")
    w = _dung(qapp)
    monkeypatch.setattr(top_bar_mod, "set_language", lambda lang: None)
    try:
        w._switch_language("en")

        assert w._lang_busy.geometry() == w.rect()
    finally:
        w.deleteLater()


def test_combo_bi_khoa_trong_luc_chan(qapp, monkeypatch, dat_ngon_ngu):
    dat_ngon_ngu("vi")
    w = _dung(qapp)
    ghi = {}

    def probe(lang):
        ghi["khoa"] = w.language_combo.isEnabled()

    monkeypatch.setattr(top_bar_mod, "set_language", probe)
    try:
        w._switch_language("en")

        assert ghi["khoa"] is False
        assert w.language_combo.isEnabled() is True, "phải mở khoá lại sau khi xong"
    finally:
        w.deleteLater()


# ---- chính sách: chỉ nháy một lần trên máy nhanh -------------------------

def test_lan_dau_trong_phien_luon_hien(qapp, monkeypatch, dat_ngon_ngu):
    """Chưa đo được gì thì nghiêng về phía hiện: một cái nháy còn hơn một lần
    đơ vài giây không lời giải thích."""
    from cowork_local.presentation.shell import busy_overlay as busy_mod

    dat_ngon_ngu("vi")
    w = _dung(qapp)
    ghi = {}
    monkeypatch.setattr(top_bar_mod, "set_language",
                        lambda lang: ghi.setdefault("hien", not w._lang_busy.isHidden()))
    try:
        assert w._lang_busy_overlay()._last_ms is None
        w._switch_language("en")

        assert ghi["hien"] is True
        assert busy_mod._NOTICEABLE_MS > 0
    finally:
        w.deleteLater()


def test_lan_truoc_nhanh_thi_khong_hien_nua(qapp, monkeypatch, dat_ngon_ngu):
    """20 ms thì không ai kịp thấy mình đang đợi — hiện lớp phủ ở đó là tự tạo
    ra một cái nháy toàn màn hình."""
    from cowork_local.presentation.shell import busy_overlay as busy_mod

    dat_ngon_ngu("vi")
    w = _dung(qapp)
    monkeypatch.setattr(busy_mod, "perf_counter", _dong_ho(0.0, 0.02, 5.0, 5.02))
    ghi = []
    monkeypatch.setattr(top_bar_mod, "set_language",
                        lambda lang: ghi.append(not w._lang_busy.isHidden()))
    try:
        w._switch_language("en")
        w._switch_language("ja")

        assert ghi == [True, False]
    finally:
        w.deleteLater()


def test_lan_truoc_cham_thi_van_hien(qapp, monkeypatch, dat_ngon_ngu):
    """Máy chậm / thư viện skill lớn: lần trước mất 1 giây thì lần này phải có
    lớp phủ, không đợi thêm lần nào nữa."""
    from cowork_local.presentation.shell import busy_overlay as busy_mod

    dat_ngon_ngu("vi")
    w = _dung(qapp)
    monkeypatch.setattr(busy_mod, "perf_counter", _dong_ho(0.0, 1.0, 5.0, 6.0))
    ghi = []
    monkeypatch.setattr(top_bar_mod, "set_language",
                        lambda lang: ghi.append(not w._lang_busy.isHidden()))
    try:
        w._switch_language("en")
        w._switch_language("ja")

        assert ghi == [True, True]
    finally:
        w.deleteLater()


# ---- đường Cài đặt ▸ Chung -----------------------------------------------

def _mo_cai_dat(qapp, monkeypatch, ngon_ngu_sau_khi_luu: str):
    """Chạy ``_open_settings`` với hộp thoại bị thay, trả về (window, ghi)."""
    w = _dung(qapp)
    w._apply_theme = lambda: None
    w.theme_btn = _Any()
    w.cowork = _Any()
    w.workspace = _Any()
    w.sidebar = _Any()
    ghi = {"goi": 0}

    class _Dlg:
        def __init__(self, ctx, parent):
            self._ctx = ctx

        def exec(self):
            self._ctx.config.language = ngon_ngu_sau_khi_luu
            return True

    def probe(lang):
        ghi["goi"] += 1
        ghi["hien"] = not w._lang_busy.isHidden()

    monkeypatch.setattr(top_bar_mod, "SettingsDialog", _Dlg)
    monkeypatch.setattr(top_bar_mod, "set_language", probe)
    return w, ghi


def test_duong_cai_dat_cung_co_overlay(qapp, monkeypatch, dat_ngon_ngu):
    """Cài đặt ▸ Chung đổi ngôn ngữ thì cũng chặn GUI thread y hệt combo."""
    dat_ngon_ngu("vi")
    w, ghi = _mo_cai_dat(qapp, monkeypatch, ngon_ngu_sau_khi_luu="en")
    try:
        w._open_settings()

        assert ghi["goi"] == 1
        assert ghi["hien"] is True
    finally:
        w.deleteLater()


def test_duong_cai_dat_khong_nhay_khi_khong_doi_ngon_ngu(qapp, monkeypatch, dat_ngon_ngu):
    """Bấm Lưu mà không đụng tới ngôn ngữ: ``set_language()`` là no-op
    (``i18n/__init__.py:62``), nên bật lớp phủ ở đây chỉ là một cái nháy."""
    dat_ngon_ngu("vi")
    w, ghi = _mo_cai_dat(qapp, monkeypatch, ngon_ngu_sau_khi_luu="vi")
    try:
        w._open_settings()

        assert ghi["goi"] == 0, "gọi set_language() cho một lượt đổi không tồn tại"
        assert getattr(w, "_lang_busy", None) is None
    finally:
        w.deleteLater()


# ---- màu lấy từ theme, không hardcode ------------------------------------

def test_mau_lay_tu_theme():
    """Guardrail G4: ngoài ``theme/`` không file nào được đặt tên một màu."""
    from cowork_local.theme.qss import _TEMPLATE

    assert "QWidget#busyOverlayPanel" in _TEMPLATE.template
    src = (Path(__file__).resolve().parents[2]
           / "presentation" / "shell" / "busy_overlay.py").read_text(encoding="utf-8")
    assert "setStyleSheet" not in src
