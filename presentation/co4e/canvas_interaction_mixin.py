"""Mixin xử lý tương tác (zoom/pan/relayout/drop) của canvas Co4E — dời khỏi
``ui/co4e_canvas.py``.

Vấn đề đang có: gộp toàn bộ ``Co4ECanvas`` (dòng 289-701 của file cũ) vào một
file duy nhất vẫn dư 413 dòng — vượt trần 400 dòng/file production của CASAN
Check 2 dù đã tách ``_NodeItem``/``_EdgeItem`` ra ``canvas_items.py`` rồi. Khối
còn lại chia làm hai nhóm trách nhiệm tự nhiên: (1) mutation đồ thị (add/delete
node/edge, port-drag) và (2) tương tác view thuần tuý (overlay góc, zoom,
pan-chuột-giữa, fit/relayout, phím tắt, kéo-thả từ sidebar). Nhóm (2) được cắt
ra đây thành MIXIN THUẦN — không có ``__init__`` riêng, không tự gọi
``super().__init__()`` — vì toàn bộ state nó dùng (``self._overlay``,
``self._zoom``, ``self._panning``, ``self._pan_start``, ``self._nodes``,
``self._edges``, ``self._scene``, ``self._connect_from``, ``self._temp_edge``,
hằng số lớp ``self._ZOOM_MIN``/``self._ZOOM_MAX``) do ``Co4ECanvas.__init__``
định nghĩa; mixin chỉ mượn ``self`` khi đã được trộn vào lớp đó.

Cách làm: cắt dán NGUYÊN VĂN các khối dòng 318-345, 484-519, 522-548, 550-610,
652-701 của ``ui/co4e_canvas.py`` — không đổi tên/tham số/thứ tự/logic, kể cả
inline import ``from collections import defaultdict`` bên trong ``relayout``
hay hai inline import ``from ..core.co4e import ...`` bên trong ``dropEvent``
(chỉ đổi SỐ DẤU CHẤM cho đúng cấp thư mục mới — xem chú thích tại chỗ).

Thứ tự kế thừa bắt buộc ở nơi dùng (``co4e_canvas_widget.py``):
``class Co4ECanvas(_CanvasInteractionMixin, QGraphicsView)`` — mixin đứng
TRƯỚC ``QGraphicsView`` trong danh sách base để MRO ưu tiên các override ở
đây (``mousePressEvent``/``mouseMoveEvent``/``mouseReleaseEvent``/
``wheelEvent``/``resizeEvent``/``keyPressEvent``/``dragEnterEvent``/
``dragMoveEvent``/``dropEvent``) thay vì rơi vào bản gốc của
``QGraphicsView``. Mỗi ``super().xxxEvent(e)`` gọi trong file này dựa vào đúng
thứ tự MRO đó để rơi xuống ``QGraphicsView.xxxEvent`` khi mixin không tự xử lý
— không phải gọi đệ quy lại chính nó.
"""
from __future__ import annotations

import copy
import json
from typing import Dict, Optional

from PySide6.QtCore import QPointF, Qt

from ...core.co4e import Edge, Node, compute_waves, new_edge_id, new_node_id
from .canvas_items import CO4E_MIME, _NODE_H, _NODE_W, _NodeItem


class _CanvasInteractionMixin:
    """Phần tương tác view của ``Co4ECanvas``: overlay góc, zoom/pan, fit/
    relayout, phím tắt, kéo-thả từ sidebar. Xem docstring đầu module về lý do
    tách và ràng buộc thứ tự kế thừa MRO khi trộn vào ``Co4ECanvas``."""

    # ---- bottom-left overlay (zoom / fit) --------------------------------
    def add_overlay(self, widget) -> None:
        """Gắn thanh điều khiển zoom/fit vào góc dưới-trái khung nhìn.

        Widget được đặt làm con của ``viewport()`` chứ không của khung vẽ, nên nó
        đứng yên khi người dùng kéo hay phóng to đồ thị.
        """
        self._overlay = widget
        widget.setParent(self.viewport())
        widget.show()
        widget.raise_()
        self._place_overlay()

    def _place_overlay(self) -> None:
        """Ghim lại thanh điều khiển vào góc dưới-trái, cách lề 12px."""
        if self._overlay is not None:
            self._overlay.adjustSize()
            vp = self.viewport()
            self._overlay.move(12, vp.height() - self._overlay.height() - 12)
            self._overlay.raise_()

    def resizeEvent(self, e):  # noqa: N802
        """Đổi kích thước khung thì ghim lại thanh điều khiển."""
        super().resizeEvent(e)
        self._place_overlay()

    def scrollContentsBy(self, dx, dy):  # noqa: N802
        """Cuộn khung thì ghim lại thanh điều khiển.

        ``QGraphicsView`` cuộn cả widget con của viewport theo cảnh, nên không
        ghim lại thì nút +/−/fit sẽ trôi khỏi góc.
        """
        # QGraphicsView scrolls the viewport's child widgets along with the
        # scene, so panning/scrolling would drag the zoom overlay off-corner.
        # Re-pin it after every scroll so +/−/fit stay fixed in place.
        super().scrollContentsBy(dx, dy)
        self._place_overlay()

    def showEvent(self, e):  # noqa: N802
        """Lần hiện đầu tiên mới biết kích thước thật của viewport — ghim lại lúc đó."""
        super().showEvent(e)
        self._place_overlay()   # viewport size is final once shown

    # ---- zoom / fit -------------------------------------------------------
    def _zoom_by(self, factor: float) -> None:
        """Phóng to/thu nhỏ theo hệ số, chặn trong khoảng ``_ZOOM_MIN``..``_ZOOM_MAX``.

        Mức phóng hiện tại đọc thẳng từ ma trận biến đổi, KHÔNG dùng biến đếm
        riêng: biến đếm lệch khỏi thực tế sau mỗi lần ``fit_view``/``relayout``/
        ``reset_zoom`` là đúng thứ từng làm nút +/− và Ctrl+lăn ngẫu nhiên chết.
        Chặn ở đích rồi mới tính hệ số cần áp, nên vẫn phóng được sát mép giới hạn.
        """
        # Derive the CURRENT scale from the live transform (never a separate
        # accumulator that can drift out of sync with fit_view/relayout/reset —
        # that drift is what made the +/− buttons and Ctrl+wheel randomly stop
        # working). Clamp the TARGET to the range and apply the exact factor to
        # reach it, so zooming still works right up to the limits.
        cur = self.transform().m11() or 1.0
        target = max(self._ZOOM_MIN, min(self._ZOOM_MAX, cur * factor))
        if abs(target - cur) < 1e-6:
            return
        self.scale(target / cur, target / cur)
        self._zoom = target

    def zoom_in(self) -> None:
        """Phóng to một nấc (×1,15)."""
        self._zoom_by(1.15)

    def zoom_out(self) -> None:
        """Thu nhỏ một nấc (÷1,15)."""
        self._zoom_by(1 / 1.15)

    def reset_zoom(self) -> None:
        """Về đúng tỉ lệ 1:1 và bỏ mọi dịch chuyển."""
        self.resetTransform()
        self._zoom = 1.0

    def wheelEvent(self, e):
        """Lăn chuột: Ctrl = phóng to/thu nhỏ quanh con trỏ, Shift = cuộn ngang,
        không phím = cuộn dọc như mặc định.
        """
        # Ctrl+wheel = zoom (anchored under the cursor); Shift+wheel = pan
        # horizontally; plain wheel scrolls vertically.
        if e.modifiers() & Qt.ControlModifier:
            self._zoom_by(1.15 if e.angleDelta().y() > 0 else 1 / 1.15)
            e.accept()
            return
        if e.modifiers() & Qt.ShiftModifier:
            bar = self.horizontalScrollBar()
            bar.setValue(bar.value() - e.angleDelta().y())
            e.accept()
            return
        super().wheelEvent(e)

    # ---- middle-mouse drag-to-pan ----------------------------------------
    def mousePressEvent(self, e):
        """Nhấn chuột giữa: bắt đầu kéo cả khung (pan), đổi con trỏ thành bàn tay nắm."""
        if e.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start = e.position().toPoint()
            self.setCursor(Qt.ClosedHandCursor)
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        """Đang kéo khung: dời hai thanh cuộn ngược chiều con trỏ."""
        if self._panning and self._pan_start is not None:
            pos = e.position().toPoint()
            delta = pos - self._pan_start
            self._pan_start = pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        """Thả chuột giữa: kết thúc kéo khung, trả con trỏ về bình thường."""
        if e.button() == Qt.MiddleButton and self._panning:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def fit_view(self) -> None:
        """Auto-fit: zoom/pan so every node is visible with a small margin."""
        rect = self._scene.itemsBoundingRect()
        if rect.isNull():
            return
        self.setSceneRect(rect.adjusted(-60, -60, 60, 60))
        self.fitInView(rect.adjusted(-40, -40, 40, 40), Qt.KeepAspectRatio)
        # keep the zoom accumulator in sync with the transform fitInView applied
        self._zoom = self.transform().m11() or 1.0

    def relayout(self, hgap: float = 110.0, vgap: float = 40.0) -> None:
        """Arrange nodes LEFT→RIGHT by dependency depth: each topological wave is
        a column (x = wave), siblings stacked vertically within it. Used to turn
        an old top-down graph into the horizontal flow layout."""
        nodes = [it.node for it in self._nodes.values()]
        edges = [it.edge for it in self._edges]
        if not nodes:
            return
        waves = compute_waves(nodes, edges)
        from collections import defaultdict
        cols: Dict[int, list] = defaultdict(list)
        for n in nodes:
            cols[waves.get(n.id, 0)].append(n)
        for w in sorted(cols):
            for row, n in enumerate(sorted(cols[w], key=lambda nn: (nn.y, nn.x))):
                item = self._nodes.get(n.id)
                if item is not None:
                    item.setPos(w * (_NODE_W + hgap), row * (_NODE_H + vgap))
        self._reposition_edges()

    def relayout_if_vertical(self) -> None:
        """Convert a graph that's stacked vertically (the old top-down layout, or
        overlapping nodes) into the horizontal left→right layout — but leave a
        graph the user already arranged horizontally untouched."""
        nodes = [it.node for it in self._nodes.values()]
        if len(nodes) < 2:
            return
        xs = [n.x for n in nodes]
        if max(xs) - min(xs) < _NODE_W:      # all in one column → it's vertical
            self.relayout()

    def add_workflow(self, nodes, edges, at: Optional[QPointF] = None) -> None:
        """Drop/merge a whole flow's nodes+edges onto the canvas with fresh ids
        (so the same template can be dropped several times). Offsets it near
        ``at`` when given, else tiles it beside whatever is already there."""
        remap: Dict[str, str] = {}
        # offset so a dropped template doesn't land exactly on existing nodes
        ox = (at.x() - nodes[0].x) if (at and nodes) else (60 if self._nodes else 0)
        oy = (at.y() - nodes[0].y) if (at and nodes) else (60 if self._nodes else 0)
        for n in nodes:
            new = Node(id=new_node_id(), x=n.x + ox, y=n.y + oy, data=copy.deepcopy(n.data))
            remap[n.id] = new.id
            item = _NodeItem(new, self)
            self._nodes[new.id] = item
            self._scene.addItem(item)
        for e in edges:
            s, t = remap.get(e.source), remap.get(e.target)
            if s and t:
                self._add_edge_item(Edge(id=new_edge_id(s, t), source=s, target=t))
        self._reposition_edges()
        self.graph_changed.emit()

    # ---- key / drop -------------------------------------------------------
    def keyPressEvent(self, e):
        """Phím tắt: Delete/Backspace xoá phần đang chọn, Esc huỷ lượt nối đang dở,
        Ctrl +/−/0 phóng to/thu nhỏ/về 1:1.
        """
        if e.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_selected()
            return
        if e.key() == Qt.Key_Escape:
            self._connect_from = None
            if self._temp_edge is not None:
                self._scene.removeItem(self._temp_edge)
                self._temp_edge = None
                self._port_src = None
            return
        if e.key() in (Qt.Key_Plus, Qt.Key_Equal) and (e.modifiers() & Qt.ControlModifier):
            self.zoom_in(); return
        if e.key() == Qt.Key_Minus and (e.modifiers() & Qt.ControlModifier):
            self.zoom_out(); return
        if e.key() == Qt.Key_0 and (e.modifiers() & Qt.ControlModifier):
            self.reset_zoom(); return
        super().keyPressEvent(e)

    def dragEnterEvent(self, e):
        """Chỉ nhận thứ kéo vào mang đúng định dạng của bảng nguyên liệu Co4E."""
        if e.mimeData().hasFormat(CO4E_MIME):
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        """Giữ trạng thái nhận thả trong suốt lúc rê qua khung."""
        if e.mimeData().hasFormat(CO4E_MIME):
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e):
        """Thả một bước hoặc cả một luồng từ bảng nguyên liệu xuống đúng vị trí con trỏ.

        Payload hỏng thì bỏ qua lặng lẽ — thả nhầm thứ gì đó vào khung không
        được phép làm vỡ màn hình.
        """
        if not e.mimeData().hasFormat(CO4E_MIME):
            super().dropEvent(e)
            return
        try:
            payload = json.loads(bytes(e.mimeData().data(CO4E_MIME)).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return
        pos = self.mapToScene(e.position().toPoint())
        if isinstance(payload, dict) and payload.get("kind") == "workflow":
            # A whole flow dragged from the sidebar → merge its graph in.
            # 3 dấu chấm vì file này giờ nằm ở presentation/co4e/ (sâu hơn
            # ui/ gốc 1 cấp) — cùng module core.co4e như bản gốc, chỉ đổi số
            # cấp cho đúng vị trí mới, không đổi cái được import.
            from ...core.co4e import workflow_from_dict
            wf = workflow_from_dict(payload.get("workflow", {}))
            if wf.nodes:
                self.add_workflow(wf.nodes, wf.edges, at=pos)
        else:
            from ...core.co4e import step_from_dict
            self.add_palette_step(step_from_dict(payload), pos)
        e.acceptProposedAction()
