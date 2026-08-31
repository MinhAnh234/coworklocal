"""Native QGraphicsScene primitives for the fallback (non-WebEngine) graph
view (R08-T14, split out of ``graph_renderer.py`` to keep it under the
400-line cap; originally ``ui/structure_graph_view.py``, lines 65-186 of the
original 1035-line file: ``_Bridge``, ``_Edge``, ``_Node``, ``_GraphView``).
"""
from __future__ import annotations

import math

from PySide6.QtCore import QObject, QPointF, Qt, Slot
from PySide6.QtGui import QBrush, QColor, QFont, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsSimpleTextItem, QGraphicsView

from cowork_local.core.structure_graph import EDGE_KIND_COLORS, NODE_KIND_COLORS
from cowork_local.theme import current_palette
from cowork_local.ui.osutil import open_folder, open_location


class _Bridge(QObject):
    """Exposed to the D3 page so a Shift+click on a node can open its
    storage folder/link (local path or URL — see osutil.open_location)."""

    @Slot(str)
    def openPath(self, path: str) -> None:  # noqa: N802 - JS-facing name
        """Cầu nối JavaScript → Python: Shift+click một node trên khung D3 thì mở thư
        mục hoặc link lưu trữ của nó.
        """
        if path:
            open_location(path)


class _Edge(QGraphicsLineItem):
    """Một cạnh trên khung Qt 2D, kèm nhãn tên quan hệ ở điểm giữa.

    Màu cạnh lấy theo LOẠI quan hệ (contains/defines/method…) để nhìn đồ thị
    là biết mỗi liên kết nghĩa là gì; cạnh không có loại thì mượn màu nhạt của
    node nguồn. Nằm ở z=-1, tức dưới mọi node.
    """
    def __init__(self, a: "_Node", b: "_Node", type_: str = ""):
        """Một cạnh trên khung đồ thị, tô màu theo LOẠI quan hệ (chứa/định nghĩa/phương
        thức…) để nhìn là biết liên kết ấy nghĩa gì; cạnh không có loại thì lấy màu
        của node nguồn.
        """
        super().__init__()
        self.a, self.b = a, b
        self.type = type_
        # Colour the edge by its RELATIONSHIP type (contains/defines/method/…),
        # so the graph shows what each connection MEANS — falling back to the
        # source node's tint for any untyped edge.
        color = QColor(EDGE_KIND_COLORS.get(type_, "")) if type_ else QColor()
        if not color.isValid():
            color = a.brush().color().lighter(130)
        self._color = color
        self.setPen(QPen(color, 1.4))
        self.setZValue(-1)
        # A small label naming the relationship, shown at the edge midpoint.
        self._label = None
        if type_:
            self._label = QGraphicsSimpleTextItem(type_, self)
            self._label.setBrush(QBrush(color.lighter(140)))
            f = QFont()
            f.setPointSize(7)
            self._label.setFont(f)
            self._label.setZValue(0)
        a.edges.append(self)
        b.edges.append(self)
        self.adjust()

    def adjust(self) -> None:
        """Vẽ lại đường thẳng theo vị trí hai node và đặt nhãn vào đúng điểm giữa."""
        pa, pb = self.a.scenePos(), self.b.scenePos()
        self.setLine(pa.x(), pa.y(), pb.x(), pb.y())
        if self._label is not None:
            br = self._label.boundingRect()
            self._label.setPos((pa.x() + pb.x()) / 2 - br.width() / 2,
                                (pa.y() + pb.y()) / 2 - br.height() / 2)


class _Node(QGraphicsEllipseItem):
    """Một node hình tròn; bán kính do chỗ gọi tính theo bậc của node.

    ``NODE_KIND_COLORS`` là mã màu theo LOẠI dữ liệu (mỗi loại một sắc), cố ý
    giữ nguyên ở cả theme sáng lẫn tối để một loại luôn là một màu. Chỉ phần
    khung viền/chữ mới đi theo theme.
    """
    def __init__(self, data, radius: int):
        """Một node hình tròn, bán kính theo số liên kết.

        Màu theo loại node là mã hoá dữ liệu chứ không phải trang trí, nên cố định
        qua mọi giao diện — cùng một loại luôn cùng một màu.
        """
        super().__init__(-radius, -radius, 2 * radius, 2 * radius)
        self.data = data
        self.edges = []
        tok = current_palette()
        # NODE_KIND_COLORS is a categorical data encoding (one hue per node
        # kind), not UI chrome — it stays fixed across themes on purpose so a
        # given kind is always the same colour. Only the chrome follows tokens.
        color = QColor(NODE_KIND_COLORS.get(data.kind, tok.text_muted))
        self.setBrush(QBrush(color))
        self.setPen(QPen(color.darker(160), 1.5))
        self.setFlags(
            QGraphicsEllipseItem.ItemIsMovable
            | QGraphicsEllipseItem.ItemIsSelectable
            | QGraphicsEllipseItem.ItemSendsGeometryChanges
        )
        self.setZValue(1)
        label = QGraphicsSimpleTextItem(data.label, self)
        label.setBrush(QBrush(QColor(tok.text)))
        label.setPos(radius + 3, -8)

    def itemChange(self, change, value):  # noqa: N802
        """Kéo node thì kéo theo mọi cạnh dính vào nó."""
        if change == QGraphicsEllipseItem.ItemPositionHasChanged:
            for edge in self.edges:
                edge.adjust()
        return super().itemChange(change, value)


class _GraphView(QGraphicsView):
    """Khung xem đồ thị Qt 2D: lăn chuột để phóng, kéo nền để dời khung."""
    def __init__(self, scene):
        """Khung xem đồ thị: kéo bằng chuột giữa để di chuyển, không kéo chọn vùng."""
        super().__init__(scene)
        self.setDragMode(QGraphicsView.NoDrag)
        self._panning = False
        self._pan_start = QPointF()

    def wheelEvent(self, e):  # noqa: N802
        """Lăn chuột phóng to/thu nhỏ một nấc 1,15 lần."""
        self.scale(1.15 if e.angleDelta().y() > 0 else 1 / 1.15,
                   1.15 if e.angleDelta().y() > 0 else 1 / 1.15)

    def mousePressEvent(self, e):  # noqa: N802
        """Nhấn trái vào chỗ TRỐNG thì bắt đầu kéo khung; nhấn trúng node thì để Qt
        xử lý như chọn/kéo node bình thường.
        """
        if e.button() == Qt.LeftButton and self.itemAt(e.pos()) is None:
            self._panning = True
            self._pan_start = e.position()
            self.setCursor(Qt.ClosedHandCursor)
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):  # noqa: N802
        """Đang kéo khung: dời hai thanh cuộn ngược chiều con trỏ."""
        if self._panning:
            delta = e.position() - self._pan_start
            self._pan_start = e.position()
            self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().value() - delta.x()))
            self.verticalScrollBar().setValue(int(self.verticalScrollBar().value() - delta.y()))
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):  # noqa: N802
        """Thả chuột: kết thúc kéo khung, trả con trỏ về bình thường."""
        if self._panning:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):  # noqa: N802
        """Double-click or Ctrl+click on a node opens its storage folder."""
        item = self.itemAt(e.pos())
        if isinstance(item, _Node) and getattr(item.data, "path", ""):
            open_folder(item.data.path)
            e.accept()
            return
        super().mouseDoubleClickEvent(e)


__all__ = ["_Bridge", "_Edge", "_Node", "_GraphView"]
