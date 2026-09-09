"""Regression: Định tuyến / Tự chạy phải đổi chữ theo ngôn ngữ runtime (UI-20260907-01).

Người dùng dựng app ở một ngôn ngữ rồi đổi sang ngôn ngữ khác: chữ trên công tắc
"Định tuyến" và ô "Tự chạy" ở tab Cowork vẫn đóng băng ở ngôn ngữ lúc dựng widget.
Vì vậy MỌI test ở đây phải theo khuôn **dựng ở X → đổi sang Y → kiểm**: kiểm ngay
lúc vừa dựng là vô nghĩa (widget luôn đúng lúc dựng, kể cả khi bản vá sai).
"""
from __future__ import annotations

import pytest

from cowork_local import i18n
from cowork_local.ui.routing_toggle import AutoRunToggle, RoutingToggle


class FakeCtx:
    """AppContext tối thiểu; ghi lại MỌI lần ghi để test chứng minh dịch lại không ghi đĩa."""

    def __init__(self) -> None:
        """Khởi tạo với sổ ghi rỗng."""
        self.writes: list = []

    def project_routing_mode(self, surface: str) -> str:
        """Chế độ định tuyến của bề mặt đang mở — cố định "manual" cho test."""
        return "manual"

    def set_project_routing_mode(self, surface: str, mode: str) -> None:
        """Ghi lại lần ghi chế độ định tuyến thay vì chạm đĩa."""
        self.writes.append((surface, mode))

    def project_auto_run(self) -> bool:
        """Trạng thái tự chạy của project — cố định True cho test."""
        return True

    def set_project_auto_run(self, value: bool) -> None:
        """Ghi lại lần ghi cờ tự chạy thay vì chạm đĩa."""
        self.writes.append(("auto_run", value))


@pytest.fixture
def i18n_sach():
    """Trả ngôn ngữ VÀ danh sách listener về nguyên trạng.

    ``i18n._listeners`` chỉ có đường vào (i18n/__init__.py:100); widget do test
    dựng sẽ nằm lại đó và bị gọi ở mọi test sau. Khôi phục để test hermetic.
    """
    lang, listeners = i18n.get_language(), list(i18n._listeners)
    yield
    i18n._listeners[:] = listeners
    i18n.set_language(lang)


def _chu_dinh_tuyen_phai_la(toggle: RoutingToggle, lang: str) -> None:
    """Mọi chữ trên công tắc định tuyến phải khớp bản dịch của ``lang``.

    So với ``i18n.STRINGS`` chứ không hard-code chuỗi: đổi từ ngữ sau này không
    được làm test đỏ oan.
    """
    assert toggle._label.text() == i18n.STRINGS["routing.toggle_label"][lang]
    assert toggle._combo.toolTip() == i18n.STRINGS["routing.toggle_tooltip"][lang]
    for i, (_value, key) in enumerate(toggle._modes):
        assert toggle._combo.itemText(i) == i18n.STRINGS[key][lang], (
            f"item {i} sai ngôn ngữ"
        )


def _on_dinh_layout(app, lap: int = 3) -> None:
    """Ép Qt xử lý hết layout request đang xếp hàng để bề rộng widget ổn định."""
    from PySide6.QtCore import QEvent

    for _ in range(lap):
        app.sendPostedEvents(None, QEvent.LayoutRequest)
        app.processEvents()


def _be_rong_o_chu(combo) -> int:
    """Bề rộng vùng hiển thị chữ của combo (đã trừ khung và mũi tên)."""
    from PySide6.QtWidgets import QStyle, QStyleOptionComboBox

    opt = QStyleOptionComboBox()
    opt.initFrom(combo)
    opt.currentText = combo.currentText()
    opt.editable = combo.isEditable()
    opt.frame = combo.hasFrame()
    opt.subControls = QStyle.SC_All
    return combo.style().subControlRect(
        QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxEditField, combo
    ).width()


def test_dinh_tuyen_dung_ngon_ngu_khi_dung_o_ja_roi_doi_sang_vi(qapp, i18n_sach):
    """Dựng ở tiếng Nhật, đổi sang tiếng Việt → nhãn/tooltip/4 chế độ phải là tiếng Việt."""
    i18n.set_language("ja")
    toggle = RoutingToggle(FakeCtx(), "cowork")

    i18n.set_language("vi")

    _chu_dinh_tuyen_phai_la(toggle, "vi")


def test_dinh_tuyen_dung_ngon_ngu_khi_dung_o_ja_roi_doi_sang_en(qapp, i18n_sach):
    """Dựng ở tiếng Nhật, đổi sang tiếng Anh → toàn bộ chữ phải là tiếng Anh."""
    i18n.set_language("ja")
    toggle = RoutingToggle(FakeCtx(), "cowork")

    i18n.set_language("en")

    _chu_dinh_tuyen_phai_la(toggle, "en")


def test_dinh_tuyen_dung_ngon_ngu_khi_dung_o_vi_roi_doi_sang_ja(qapp, i18n_sach):
    """Chiều ngược lại: dựng ở tiếng Việt, đổi sang tiếng Nhật."""
    i18n.set_language("vi")
    toggle = RoutingToggle(FakeCtx(), "cowork")

    i18n.set_language("ja")

    _chu_dinh_tuyen_phai_la(toggle, "ja")


def test_doi_ngon_ngu_khong_lam_doi_che_do_dinh_tuyen(qapp, i18n_sach):
    """Test KHOÁ: dịch lại chỉ được đổi CHỮ, không đổi chế độ và không ghi đĩa.

    Cột ``data`` ("off"/"auto"/"manual"/"fallback") được persist xuống đĩa; nếu
    ai đó dịch luôn cột đó, hoặc đổi ``retranslate()`` sang ``clear()+addItem()``,
    thì mode routing của mọi workspace bị âm thầm reset về "off".
    """
    i18n.set_language("ja")
    ctx = FakeCtx()
    toggle = RoutingToggle(ctx, "cowork")

    for lang in ("vi", "en", "ja"):
        i18n.set_language(lang)

    assert toggle.current_mode() == "manual"
    assert toggle._combo.currentData() == "manual"
    assert ctx.writes == [], "đổi ngôn ngữ không được ghi lại chế độ định tuyến"


def test_tu_chay_dung_ngon_ngu_sau_khi_doi_ngon_ngu(qapp, i18n_sach):
    """Ô "Tự chạy" cũng phải đổi chữ, và không được tự đổi trạng thái tick."""
    i18n.set_language("ja")
    ctx = FakeCtx()
    toggle = AutoRunToggle(ctx)

    i18n.set_language("vi")

    assert toggle._chk.text() == i18n.STRINGS["routing.autorun_label"]["vi"]
    assert toggle._chk.toolTip() == i18n.STRINGS["routing.autorun_tooltip"]["vi"]

    i18n.set_language("en")

    assert toggle._chk.text() == i18n.STRINGS["routing.autorun_label"]["en"]
    assert toggle._chk.toolTip() == i18n.STRINGS["routing.autorun_tooltip"]["en"]
    assert toggle._chk.isChecked() is True
    assert ctx.writes == [], "đổi ngôn ngữ không được ghi lại cờ tự chạy"


def test_bon_che_do_khong_bi_cat_chu_sau_khi_doi_ngon_ngu(qapp, i18n_sach):
    """Dịch lại xong thì combo phải rộng ra theo chữ mới, không nuốt đuôi.

    Combo dựng ở tiếng Nhật rồi đổi sang tiếng Việt: tên chế độ tiếng Việt dài
    hơn tên tiếng Nhật, nên nếu bề rộng còn bị khoá theo lần hiện đầu tiên thì
    "Thủ công"/"Dự phòng" (96px) không lọt ô chữ 89px và bị cắt đuôi.

    Hai lớp assert, mỗi lớp bắt một nửa bản vá:

    * chữ phải là tiếng Việt — bắt việc quên đăng ký ``on_language_changed``;
    * chữ phải lọt ô — bắt việc quên ``setSizeAdjustPolicy``, vì combo chỉ đo
      lại bề rộng khi chính sách là ``AdjustToContents``.

    ``host`` được nới rộng có chủ ý: ``addStretch`` phải còn chỗ trống để nhả ra
    cho combo, nếu không thì cả combo đúng lẫn combo sai đều kẹt ở bề rộng cũ và
    test không phân biệt được hai trạng thái.
    """
    from PySide6.QtGui import QFontMetrics
    from PySide6.QtWidgets import QHBoxLayout, QWidget

    i18n.set_language("ja")
    host = QWidget()
    lay = QHBoxLayout(host)
    toggle = RoutingToggle(FakeCtx(), "cowork")
    lay.addWidget(toggle)
    lay.addStretch(1)
    host.resize(600, 60)
    host.show()
    _on_dinh_layout(qapp)

    i18n.set_language("vi")
    _on_dinh_layout(qapp)

    combo = toggle._combo
    fm = QFontMetrics(combo.font())
    o_chu = _be_rong_o_chu(combo)
    chu_hien = [combo.itemText(i) for i in range(combo.count())]
    bi_cat = [t for t in chu_hien if fm.horizontalAdvance(t) > o_chu]
    host.close()

    assert chu_hien == [i18n.STRINGS[key]["vi"] for _value, key in toggle._modes]
    assert not bi_cat, f"bị cắt chữ: {bi_cat} (ô chữ rộng {o_chu}px)"


@pytest.mark.parametrize("key", [
    "routing.toggle_label", "routing.toggle_tooltip",
    "routing.autorun_label", "routing.autorun_tooltip",
    "routing.mode_off", "routing.mode_auto",
    "routing.mode_manual", "routing.mode_fallback",
])
def test_key_routing_co_du_ba_ngon_ngu(key):
    """Test KHOÁ: thiếu một bản dịch thì ``tr()`` rơi về tiếng Anh, lỗi lại tái diễn."""
    for lang in ("en", "ja", "vi"):
        assert i18n.STRINGS[key].get(lang), f"{key} thiếu {lang}"
