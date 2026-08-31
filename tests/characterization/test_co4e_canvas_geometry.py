"""Characterization tests cho 8 ham hinh hoc thuan cua Co4E canvas.

Vong doi: day la gian giao (scaffolding), khong phai test dac ta cuoi cung.
Muc dich la ghi lai HANH VI DANG CO cua ``_dist``, ``_towards``,
``_rounded_path``, ``_seg_hits_rect``, ``_hits``, ``_route``, ``_ortho_path``,
``_elide`` — hien dang duoc re-export tu ``ui/co4e_canvas.py`` (thuc chat da
duoc doi sang song o ``presentation/co4e/canvas_geometry.py``, xem docstring
cua file do) — de lam luoi an toan cho dot tach file 2000+ dong. Test nay
KHONG phan xet dung/sai thiet ke, chi dong dinh lai output thuc te da chay va
in ra. Sau khi dot tach hoan tat va on dinh, cac test o day nen duoc viet lai
thanh test dac ta (specification test) that su — luc do co the xoa cac assert
kieu "quirk" ben duoi va thay bang assert dua tren hop dong ro rang, hoac mo
issue rieng de sua cac quirk neu chung thuc su la bug.

Khong can QApplication: cac ham nay chi dung QPointF/QRectF/QPainterPath nhu
kieu gia tri thuan, khong ve, khong doc kich thuoc widget.

Cac quirk dang chu y da duoc dong dinh o day (dung sua o code san pham):

  * ``_elide(text, n)`` dung slicing ``text[: n - 1] + "..."``. Voi ``n=0``,
    ``n - 1 == -1`` nen KHONG cat rong ma cat mat ky tu cuoi cung cua chuoi
    con lai roi noi dau "..." vao — vi du ``_elide("abc", 0) == "ab..."`` chu
    khong phai chuoi rong. Voi ``n=1``, ket qua la chinh dau "..." (do
    ``text[:0] == ""``).
  * ``_seg_hits_rect`` kiem tra nhanh "horizontal" (``abs(y1-y2) < 0.5``)
    TRUOC nhanh "vertical" — mot doan suy bien (diem trung diem, ``p1==p2``)
    luon roi vao nhanh horizontal du no cung thoa dieu kien vertical.
  * ``_route`` co the "bo cuoc": khi vat can qua lon bao kin moi phuong an
    tranh, no tra ve elbow co ban (``base``) DU NO VAN VA CHAM vat can — ham
    khong nem loi, khong bao dam duong tra ve khong va cham.
  * ``_towards(a, b, d)`` khi ``a == b`` (khoang cach ~0) tra ve ban sao cua
    ``a`` bat ke ``d`` la bao nhieu, thay vi loi hoac diem khong xac dinh.

Cac assert duoi day duoc chot bang cach CHAY code that qua
``.venv/Scripts/python.exe -c "..."`` roi dan nguyen ket qua in duoc vao
assert, khong suy luan ly thuyet.
"""
from __future__ import annotations

import pytest

from cowork_local.ui.co4e_canvas import (
    _dist,
    _elide,
    _hits,
    _ortho_path,
    _route,
    _rounded_path,
    _seg_hits_rect,
    _towards,
)
from PySide6.QtCore import QPointF, QRectF


# ---------------------------------------------------------------------------
# _dist
# ---------------------------------------------------------------------------

def test_dist_pythagorean_3_4_5():
    assert _dist(QPointF(0, 0), QPointF(3, 4)) == pytest.approx(5.0)


def test_dist_same_point_is_zero():
    assert _dist(QPointF(5, 5), QPointF(5, 5)) == pytest.approx(0.0)


def test_dist_negative_coordinates():
    assert _dist(QPointF(-1, -1), QPointF(2, 3)) == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# _towards
# ---------------------------------------------------------------------------

def test_towards_moves_along_axis_by_distance():
    p = _towards(QPointF(0, 0), QPointF(10, 0), 5)
    assert p.x() == pytest.approx(5.0)
    assert p.y() == pytest.approx(0.0)


def test_towards_same_point_returns_copy_of_a_regardless_of_d():
    # quirk: khi a == b (khoang cach ~0), tra ve ban sao cua a, khong loi.
    p = _towards(QPointF(0, 0), QPointF(0, 0), 5)
    assert p.x() == pytest.approx(0.0)
    assert p.y() == pytest.approx(0.0)


def test_towards_zero_distance_stays_at_a():
    p = _towards(QPointF(0, 0), QPointF(10, 0), 0)
    assert p.x() == pytest.approx(0.0)
    assert p.y() == pytest.approx(0.0)


def test_towards_overshoot_past_b_is_allowed():
    # quirk: d lon hon khoang cach a->b van duoc ngoai suy, khong bi kep lai.
    p = _towards(QPointF(0, 0), QPointF(10, 0), 20)
    assert p.x() == pytest.approx(20.0)
    assert p.y() == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _rounded_path
# ---------------------------------------------------------------------------

def test_rounded_path_empty_points_returns_empty_path():
    path = _rounded_path([])
    assert path.elementCount() == 0


def test_rounded_path_single_point():
    path = _rounded_path([QPointF(1, 2)])
    assert path.elementCount() == 1
    e = path.elementAt(0)
    assert (e.x, e.y) == pytest.approx((1.0, 2.0))


def test_rounded_path_two_points_is_a_straight_line_no_bend():
    path = _rounded_path([QPointF(0, 0), QPointF(10, 0)])
    assert path.elementCount() == 2
    e0, e1 = path.elementAt(0), path.elementAt(1)
    assert (e0.x, e0.y) == pytest.approx((0.0, 0.0))
    assert (e1.x, e1.y) == pytest.approx((10.0, 0.0))


def test_rounded_path_three_points_default_radius():
    # dist(prev,cur)=10, dist(cur,nxt)=10 -> rr = min(12, 5, 5) = 5.
    path = _rounded_path([QPointF(0, 0), QPointF(10, 0), QPointF(10, 10)])
    assert path.elementCount() == 6
    pts = [(path.elementAt(i).x, path.elementAt(i).y) for i in range(6)]
    expected = [
        (0.0, 0.0),
        (5.0, 0.0),
        (8.333333333333334, 0.0),
        (10.0, 1.6666666666666667),
        (10.0, 5.0),
        (10.0, 10.0),
    ]
    for got, exp in zip(pts, expected):
        assert got[0] == pytest.approx(exp[0])
        assert got[1] == pytest.approx(exp[1])
    rect = path.boundingRect()
    assert (rect.x(), rect.y(), rect.width(), rect.height()) == pytest.approx(
        (0.0, 0.0, 10.0, 10.0)
    )


def test_rounded_path_default_radius_matches_explicit_r_12():
    a = _rounded_path([QPointF(0, 0), QPointF(10, 0), QPointF(10, 10)])
    b = _rounded_path([QPointF(0, 0), QPointF(10, 0), QPointF(10, 10)], 12)
    assert a.elementCount() == b.elementCount()
    for i in range(a.elementCount()):
        ea, eb = a.elementAt(i), b.elementAt(i)
        assert (ea.x, ea.y) == pytest.approx((eb.x, eb.y))


def test_rounded_path_custom_smaller_radius_changes_bend_points():
    path = _rounded_path([QPointF(0, 0), QPointF(10, 0), QPointF(10, 10)], r=2)
    assert path.elementCount() == 6
    pts = [(path.elementAt(i).x, path.elementAt(i).y) for i in range(6)]
    expected = [
        (0.0, 0.0),
        (8.0, 0.0),
        (9.333333333333334, 0.0),
        (10.0, 0.6666666666666666),
        (10.0, 2.0),
        (10.0, 10.0),
    ]
    for got, exp in zip(pts, expected):
        assert got[0] == pytest.approx(exp[0])
        assert got[1] == pytest.approx(exp[1])


# ---------------------------------------------------------------------------
# _seg_hits_rect
# ---------------------------------------------------------------------------

RECT = QRectF(10, 10, 20, 20)  # x in [10, 30], y in [10, 30]


def test_seg_hits_rect_horizontal_through_rect():
    assert _seg_hits_rect(QPointF(0, 20), QPointF(40, 20), RECT) is True


def test_seg_hits_rect_horizontal_outside_y_range():
    assert _seg_hits_rect(QPointF(0, 5), QPointF(40, 5), RECT) is False


def test_seg_hits_rect_horizontal_not_reaching_rect_x_range():
    assert _seg_hits_rect(QPointF(0, 20), QPointF(5, 20), RECT) is False


def test_seg_hits_rect_vertical_through_rect():
    assert _seg_hits_rect(QPointF(20, 0), QPointF(20, 40), RECT) is True


def test_seg_hits_rect_vertical_outside_x_range():
    assert _seg_hits_rect(QPointF(5, 0), QPointF(5, 40), RECT) is False


def test_seg_hits_rect_diagonal_intersecting():
    assert _seg_hits_rect(QPointF(0, 0), QPointF(40, 40), RECT) is True


def test_seg_hits_rect_diagonal_not_intersecting():
    assert _seg_hits_rect(QPointF(0, 0), QPointF(5, 5), RECT) is False


def test_seg_hits_rect_degenerate_point_inside_counts_as_hit():
    # quirk: p1 == p2 roi vao nhanh "horizontal" (abs(y1-y2) < 0.5 duoc kiem
    # truoc), du no cung thoa nhanh vertical.
    assert _seg_hits_rect(QPointF(20, 20), QPointF(20, 20), RECT) is True


def test_seg_hits_rect_degenerate_point_outside():
    assert _seg_hits_rect(QPointF(0, 0), QPointF(0, 0), RECT) is False


# ---------------------------------------------------------------------------
# _hits
# ---------------------------------------------------------------------------

def test_hits_empty_points_list_is_false():
    assert _hits([], [RECT]) is False


def test_hits_single_point_has_no_segments_so_false():
    assert _hits([QPointF(20, 20)], [RECT]) is False


def test_hits_no_obstacles_default_behaviour_false():
    assert _hits([QPointF(0, 20), QPointF(40, 20)], []) is False


def test_hits_true_when_segment_crosses_obstacle():
    assert _hits([QPointF(0, 20), QPointF(40, 20)], [RECT]) is True


def test_hits_false_when_segment_misses_obstacle():
    assert _hits([QPointF(0, 5), QPointF(40, 5)], [RECT]) is False


# ---------------------------------------------------------------------------
# _route
# ---------------------------------------------------------------------------

def test_route_same_y_no_obstacles_is_straight_line():
    r = _route(QPointF(0, 0), QPointF(100, 0))
    pts = [(p.x(), p.y()) for p in r]
    assert pts == pytest.approx([(0.0, 0.0), (100.0, 0.0)])


def test_route_default_obstacles_none_matches_explicit_none():
    # tham so mac dinh: goi khong truyen obstacles == truyen None tuong minh.
    r_default = _route(QPointF(0, 0), QPointF(100, 0))
    r_explicit = _route(QPointF(0, 0), QPointF(100, 0), None)
    pts_default = [(p.x(), p.y()) for p in r_default]
    pts_explicit = [(p.x(), p.y()) for p in r_explicit]
    assert pts_default == pytest.approx(pts_explicit)


def test_route_different_y_no_obstacles_is_mid_x_elbow():
    r = _route(QPointF(0, 0), QPointF(100, 50))
    pts = [(p.x(), p.y()) for p in r]
    assert pts == pytest.approx(
        [(0.0, 0.0), (50.0, 0.0), (50.0, 50.0), (100.0, 50.0)]
    )


def test_route_same_y_with_obstacle_falls_back_to_detour():
    # obstacle nam giua duong thang mid_x va cung chan luon dai vertical band
    # (obstacle qua rong so voi khoang cach 2 diem) -> _route roi xuong nhanh
    # detour tren/duoi (margin 44) thay vi elbow don gian.
    obstacle_mid = QRectF(40, -10, 20, 20)  # phu y=0 tai x trong [40, 60]
    r = _route(QPointF(0, 0), QPointF(100, 0), [obstacle_mid])
    pts = [(p.x(), p.y()) for p in r]
    assert pts == pytest.approx(
        [
            (0.0, 0.0),
            (34.0, 0.0),
            (34.0, -54.0),
            (66.0, -54.0),
            (66.0, 0.0),
            (100.0, 0.0),
        ]
    )
    # duong tra ve nay khong con va cham obstacle da cho.
    assert _hits(r, [obstacle_mid]) is False


def test_route_gives_up_and_returns_colliding_base_when_fully_boxed_in():
    # quirk: neu vat can qua lon, bao kin moi phuong an tranh (vertical band
    # va detour tren/duoi deu khong thoat), _route "bo cuoc" va tra ve elbow
    # co ban (base) DU NO VAN VA CHAM vat can — khong nem loi, khong dam bao
    # duong tra ve la an toan.
    huge = QRectF(-1000, -1000, 3000, 3000)
    r = _route(QPointF(0, 0), QPointF(100, 50), [huge])
    pts = [(p.x(), p.y()) for p in r]
    assert pts == pytest.approx(
        [(0.0, 0.0), (50.0, 0.0), (50.0, 50.0), (100.0, 50.0)]
    )
    assert _hits(r, [huge]) is True


# ---------------------------------------------------------------------------
# _ortho_path
# ---------------------------------------------------------------------------

def test_ortho_path_straight_case_element_count():
    op = _ortho_path(QPointF(0, 0), QPointF(100, 0))
    assert op.elementCount() == 2


def test_ortho_path_elbow_case_element_count_and_bounds():
    op = _ortho_path(QPointF(0, 0), QPointF(100, 50))
    assert op.elementCount() == 10
    rect = op.boundingRect()
    assert (rect.x(), rect.y(), rect.width(), rect.height()) == pytest.approx(
        (0.0, 0.0, 100.0, 50.0)
    )


def test_ortho_path_default_radius_is_corner_r_12():
    a = _ortho_path(QPointF(0, 0), QPointF(100, 50))
    b = _ortho_path(QPointF(0, 0), QPointF(100, 50), 12)
    assert a.elementCount() == b.elementCount()
    for i in range(a.elementCount()):
        ea, eb = a.elementAt(i), b.elementAt(i)
        assert (ea.x, ea.y) == pytest.approx((eb.x, eb.y))


# ---------------------------------------------------------------------------
# _elide
# ---------------------------------------------------------------------------

def test_elide_short_text_under_limit_is_unchanged():
    assert _elide("hello", 10) == "hello"


def test_elide_text_exactly_at_limit_is_unchanged():
    assert _elide("abc", 3) == "abc"


def test_elide_long_text_is_cut_with_ellipsis_and_total_len_equals_n():
    result = _elide("hello world this is long", 10)
    assert result == "hello wor…"
    assert len(result) == 10


def test_elide_newlines_are_replaced_with_spaces():
    assert _elide("line1\nline2", 20) == "line1 line2"


def test_elide_empty_string_stays_empty():
    assert _elide("", 10) == ""


def test_elide_none_is_treated_as_empty_string():
    assert _elide(None, 10) == ""


def test_elide_n_zero_quirk_slices_off_last_char_not_empty():
    # quirk: text[: n - 1] voi n=0 la text[:-1], KHONG phai cat rong. Voi
    # chuoi "abc" (len 3 > 0) ket qua la "ab" + dau "..." = "ab...".
    assert _elide("abc", 0) == "ab…"


def test_elide_n_one_quirk_result_is_just_ellipsis():
    # quirk: voi n=1, text[:0] == "" nen ket qua chi con dau "...".
    assert _elide("abc", 1) == "…"


def test_elide_n_larger_than_text_length_boundary():
    # len("abcd") = 4 > 3 nen van bi cat, dung == thi khong cat.
    assert _elide("abcd", 3) == "ab…"
