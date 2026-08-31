"""Hình học thuần cho canvas Co4E — tách khỏi ``ui/co4e_canvas.py``.

Vấn đề đang có: ``ui/co4e_canvas.py`` dài hơn 2000 dòng, gộp chung widget Qt
(``QGraphicsItem``, vẽ, sự kiện chuột) với các hàm hình học thuần (khoảng cách,
nội suy điểm, dựng đường bo góc, né vật cản, cắt chuỗi). Các hàm hình học này
không cần ``QApplication``, không vẽ, không đọc kích thước widget — chúng chỉ
dùng ``QPointF``/``QRectF``/``QPainterPath`` như kiểu giá trị thuần. Gộp chung
vào một file khiến file đó khó đọc và khó kiểm tra theo giới hạn CASAN (≤400
dòng mỗi file production).

Cách làm: dời nguyên 8 hàm này sang đây, không đổi tên/tham số/giá trị mặc
định/hành vi — kể cả các "quirk" đã bị characterization test đóng đinh (xem
``tests/characterization/test_co4e_canvas_geometry.py``), ví dụ ``_route`` có
thể "bỏ cuộc" và trả về elbow va chạm nếu bị vật cản bao kín hoàn toàn, hoặc
``_elide(text, 0)`` trả về ``"…"`` chứ không phải chuỗi rỗng do cách slicing
``text[: n - 1]``. Đừng "sửa" các quirk này ở đây — chúng đã có test khoá lại,
sửa sai chỗ này sẽ làm vỡ hợp đồng mà nơi khác đang phụ thuộc.

``ui/co4e_canvas.py`` import lại các tên này (không alias) để giữ nguyên đường
import public mà các test/character khác đang dùng.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainterPath

_CORNER_R = 12             # edge elbow corner radius


def _dist(a: QPointF, b: QPointF) -> float:
    """Khoảng cách Euclid giữa hai điểm."""
    return ((a.x() - b.x()) ** 2 + (a.y() - b.y()) ** 2) ** 0.5


def _towards(a: QPointF, b: QPointF, d: float) -> QPointF:
    """Điểm cách ``a`` một đoạn ``d`` theo hướng đi về ``b``.

    Hai điểm trùng nhau thì trả về chính ``a``, tránh chia cho 0.
    """
    dist = _dist(a, b)
    if dist < 1e-6:
        return QPointF(a)
    t = d / dist
    return QPointF(a.x() + (b.x() - a.x()) * t, a.y() + (b.y() - a.y()) * t)


def _rounded_path(points, r: float = _CORNER_R) -> QPainterPath:
    """Build a path through axis-aligned ``points`` with rounded corners at each
    bend ("vuông bo cong ở góc")."""
    if not points:
        return QPainterPath()
    path = QPainterPath(points[0])
    if len(points) == 1:
        return path
    for i in range(1, len(points) - 1):
        prev, cur, nxt = points[i - 1], points[i], points[i + 1]
        rr = min(r, _dist(prev, cur) / 2.0, _dist(cur, nxt) / 2.0)
        path.lineTo(_towards(cur, prev, rr))
        path.quadTo(cur, _towards(cur, nxt, rr))
    path.lineTo(points[-1])
    return path


def _seg_hits_rect(p1: QPointF, p2: QPointF, rect: QRectF) -> bool:
    """Axis-aligned segment vs rectangle overlap (all routed segments are H or V)."""
    x1, y1, x2, y2 = p1.x(), p1.y(), p2.x(), p2.y()
    if abs(y1 - y2) < 0.5:                       # horizontal
        if rect.top() <= y1 <= rect.bottom():
            lo, hi = sorted((x1, x2))
            return not (hi < rect.left() or lo > rect.right())
        return False
    if abs(x1 - x2) < 0.5:                       # vertical
        if rect.left() <= x1 <= rect.right():
            lo, hi = sorted((y1, y2))
            return not (hi < rect.top() or lo > rect.bottom())
        return False
    box = QRectF(QPointF(min(x1, x2), min(y1, y2)), QPointF(max(x1, x2), max(y1, y2)))
    return rect.intersects(box)


def _hits(points, obstacles) -> bool:
    """Đường gấp khúc này có cắt qua hình chữ nhật vật cản nào không.

    Dùng để định tuyến đường nối lách qua các node khác.
    """
    for i in range(len(points) - 1):
        for r in obstacles:
            if _seg_hits_rect(points[i], points[i + 1], r):
                return True
    return False


def _route(src: QPointF, dst: QPointF, obstacles=None):
    """Waypoints for a LEFT→RIGHT orthogonal edge from ``src`` (a node's right
    output) to ``dst`` (the next node's left input) that AVOIDS the other node
    rectangles: try the straight elbow, then a clear vertical band, then a
    top/bottom detour — so a connector never overlaps or hides behind a step."""
    obstacles = list(obstacles or [])
    if abs(src.y() - dst.y()) < 1.5:
        cand = [src, dst]
        if not _hits(cand, obstacles):
            return cand
    mid_x = (src.x() + dst.x()) / 2.0
    base = [src, QPointF(mid_x, src.y()), QPointF(mid_x, dst.y()), dst]
    if not _hits(base, obstacles):
        return base
    # 1) slide the vertical run to a clear band between the two columns
    lo, hi = min(src.x(), dst.x()) + 6, max(src.x(), dst.x()) - 6
    if hi > lo:
        for frac in (0.5, 0.35, 0.65, 0.2, 0.8):
            x = lo + (hi - lo) * frac
            cand = [src, QPointF(x, src.y()), QPointF(x, dst.y()), dst]
            if not _hits(cand, obstacles):
                return cand
    # 2) detour above/below every obstacle, then back in
    margin = 44.0
    ys = [src.y(), dst.y()] + [r.top() for r in obstacles] + [r.bottom() for r in obstacles]
    out_x, in_x = src.x() + 34, dst.x() - 34   # short stubs out of the side ports
    for side_y in (min(ys) - margin, max(ys) + margin):
        cand = [src, QPointF(out_x, src.y()), QPointF(out_x, side_y),
                QPointF(in_x, side_y), QPointF(in_x, dst.y()), dst]
        if not _hits(cand, obstacles):
            return cand
    return base


def _ortho_path(src: QPointF, dst: QPointF, r: float = _CORNER_R) -> QPainterPath:
    """Rounded orthogonal elbow (no obstacle avoidance) — used for the transient
    drag-to-connect line and by callers that pass no obstacles."""
    return _rounded_path(_route(src, dst), r)


def _elide(text: str, n: int) -> str:
    """Cắt chuỗi cho vừa ``n`` ký tự và thay xuống dòng bằng dấu cách — nhãn trên
    khung vẽ chỉ có một dòng.
    """
    text = (text or "").replace("\n", " ")
    return text if len(text) <= n else text[: n - 1] + "…"
