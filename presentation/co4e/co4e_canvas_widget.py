"""Widget canvas Co4E — dời khỏi ``ui/co4e_canvas.py``.

Vấn đề đang có: ``Co4ECanvas`` (dòng 289-701 của file cũ) một mình đã 413
dòng — vượt trần 400 dòng/file production của CASAN Check 2 kể cả sau khi tách
riêng ``_NodeItem``/``_EdgeItem`` (nay ở ``canvas_items.py``, xem docstring ở
đó) và 8 hàm hình học thuần (``canvas_geometry.py``). Phần còn lại của lớp lại
chia tiếp làm hai nhóm: mutation đồ thị (ở lại đây) và tương tác view thuần
tuý — zoom/pan/overlay/relayout/phím tắt/kéo-thả (dời sang
``_CanvasInteractionMixin`` ở ``canvas_interaction_mixin.py``, xem docstring
đó về lý do và ràng buộc MRO).

Cách làm: cắt dán NGUYÊN VĂN dòng 289-317 (khai báo lớp + signal + hằng số zoom
+ ``__init__``), 348-481 (load/nodes/edges + toàn bộ mutation node/edge/port-
drag), 612-649 (status + reposition) từ ``ui/co4e_canvas.py`` — không đổi
tên/tham số/thứ tự/logic.

``class Co4ECanvas(_CanvasInteractionMixin, QGraphicsView)``: mixin đứng
TRƯỚC ``QGraphicsView`` trong danh sách base để MRO ưu tiên các override của
mixin (``mousePressEvent``/``mouseMoveEvent``/``mouseReleaseEvent``/
``wheelEvent``/``resizeEvent``/``keyPressEvent``/``dragEnterEvent``/
``dragMoveEvent``/``dropEvent``) — nếu đảo thứ tự, các override đó sẽ bị
``QGraphicsView`` che mất và toàn bộ hành vi pan-chuột-giữa/zoom/kéo-thả sẽ
biến mất im lặng (không lỗi, chỉ rơi lại hành vi mặc định của Qt).

``ui/co4e_canvas.py`` import lại ``Co4ECanvas``/``CO4E_MIME`` từ đây (không
alias) để giữ nguyên đường import public mà các test/characterization khác
đang dùng.
"""
from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsScene, QGraphicsView

from ...core.co4e import Edge, Node, Step, new_edge_id, new_node_id
from ...theme import current_palette
from .canvas_geometry import _ortho_path, _route
from .canvas_interaction_mixin import _CanvasInteractionMixin
from .canvas_items import CO4E_MIME, _NODE_H, _NODE_W, _EdgeItem, _NodeItem

__all__ = ["Co4ECanvas", "CO4E_MIME"]


class Co4ECanvas(_CanvasInteractionMixin, QGraphicsView):
    """Khung vẽ luồng Co4E: node là bước, cạnh là thứ tự chạy.

    Lớp này giữ *dữ liệu đồ thị* (thêm/xoá node, nối cạnh, định tuyến đường
    nối). Phần thao tác chuột/bàn phím — phóng to, kéo màn, kéo-thả từ bảng
    nguyên liệu — nằm ở ``_CanvasInteractionMixin`` để file này không vượt
    hạn mức 400 dòng.

    Mọi thay đổi làm đồ thị khác đi đều phát ``graph_changed`` để lớp trên
    tự lưu.
    """
    node_selected = Signal(str)     # a node was clicked (→ config panel)
    node_activated = Signal(str)    # double-clicked
    graph_changed = Signal()        # nodes/edges/positions changed (autosave)

    _ZOOM_MIN, _ZOOM_MAX = 0.3, 3.0

    def __init__(self):
        """Khung vẽ workflow: kéo chọn theo vùng, thu phóng lấy con trỏ làm tâm."""
        super().__init__()
        self.setObjectName("co4eCanvas")   # themed frame (see theme.py)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(self.renderHints().Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setAcceptDrops(True)
        self._nodes: Dict[str, _NodeItem] = {}
        self._edges: list[_EdgeItem] = []
        self._connect_from: Optional[str] = None
        self._zoom = 1.0
        self._panning = False         # middle-mouse drag-to-pan
        self._pan_start = None
        self._overlay = None          # bottom-left zoom/fit controls (parented to viewport)
        # manual drag-to-connect state
        self._port_src: Optional[str] = None
        self._port_src_pt: Optional[QPointF] = None
        self._temp_edge: Optional[QGraphicsPathItem] = None

    # ---- load / serialize -------------------------------------------------
    def load(self, nodes, edges) -> None:
        """Nạp lại toàn bộ đồ thị, xoá sạch khung cũ.

        Cạnh trỏ tới node không tồn tại thì bỏ lặng lẽ — file luồng sửa tay
        hoặc luồng cũ có thể còn cạnh mồ côi, và treo cả màn vì một cạnh hỏng
        thì tệ hơn là bỏ nó đi.
        """
        self._scene.clear()
        self._nodes.clear()
        self._edges.clear()
        self._connect_from = None
        self._port_src = None
        self._temp_edge = None
        for n in nodes:
            item = _NodeItem(n, self)
            self._nodes[n.id] = item
            self._scene.addItem(item)
        for e in edges:
            if e.source in self._nodes and e.target in self._nodes:
                self._add_edge_item(e)
        self._reposition_edges()

    def nodes(self):
        """Danh sách node (dạng dữ liệu, không phải item đồ hoạ) để đem đi lưu."""
        return [it.node for it in self._nodes.values()]

    def edges(self):
        """Danh sách cạnh (dạng dữ liệu) để đem đi lưu."""
        return [it.edge for it in self._edges]

    # ---- mutation ---------------------------------------------------------
    def add_node(self, step: Step, x: float = 60.0, y: float = 60.0,
                 connect_from: str = "") -> str:
        """Thêm một bước vào khung và trả về id node vừa tạo.

        ``connect_from`` trỏ tới node nào thì nối luôn một cạnh từ đó sang; id
        không tồn tại thì bỏ qua phần nối. Node mới luôn được chọn ngay để bảng
        thuộc tính bên phải mở đúng bước vừa thêm.
        """
        node = Node(id=new_node_id(), x=x, y=y, data=step)
        item = _NodeItem(node, self)
        self._nodes[node.id] = item
        self._scene.addItem(item)
        if connect_from and connect_from in self._nodes:
            self._make_edge(connect_from, node.id)
        self._reposition_edges()
        self.graph_changed.emit()
        self.node_selected.emit(node.id)
        return node.id

    def add_step_below(self, node_id: str) -> None:
        """Add the next step to the RIGHT of ``node_id`` (horizontal flow)."""
        parent = self._nodes.get(node_id)
        if parent is None:
            return
        step = Step(label="New Step")
        self.add_node(step, x=parent.node.x + _NODE_W + 150, y=parent.node.y, connect_from=node_id)

    def _chain_tail(self) -> str:
        """A node with no outgoing edge (so a freshly added node chains on)."""
        sources = {e.edge.source for e in self._edges}
        tails = [nid for nid in self._nodes if nid not in sources]
        return tails[-1] if tails else (next(reversed(self._nodes), "") if self._nodes else "")

    def add_palette_step(self, step: Step, pos: QPointF) -> None:
        """Thả một bước từ bảng nguyên liệu xuống đúng vị trí con trỏ.

        Tự nối vào đuôi chuỗi hiện có, để kéo liên tiếp vài bước là thành một
        luồng chạy được mà không phải nối tay từng cạnh.
        """
        tail = self._chain_tail()
        self.add_node(step, x=pos.x(), y=pos.y(), connect_from=tail)

    def begin_connect(self, source_id: str) -> None:
        """Bắt đầu nối cạnh bằng menu chuột phải: ghi nhớ node nguồn."""
        self._connect_from = source_id

    def _finish_connect(self, target_id: str) -> None:
        """Kết thúc lượt nối bằng menu: tạo cạnh và xoá trạng thái đang nối.

        Tự nối vào chính mình thì không tạo cạnh, nhưng vẫn xoá trạng thái —
        nếu không, lần bấm kế tiếp sẽ nối nhầm từ node cũ.
        """
        src = self._connect_from
        self._connect_from = None
        if src and src != target_id:
            self._make_edge(src, target_id)

    # ---- manual drag-to-connect (from a node's output port) ---------------
    def begin_port_drag(self, source_id: str, scene_pt: QPointF) -> None:
        """Bắt đầu kéo cạnh từ cổng ra của một node: dựng đường nét đứt tạm."""
        self._port_src = source_id
        self._port_src_pt = scene_pt
        self._temp_edge = QGraphicsPathItem()
        self._temp_edge.setZValue(3.5)      # above nodes + edges while connecting
        self._temp_edge.setPen(
            QPen(QColor(current_palette().accent), 2, Qt.DashLine, Qt.RoundCap))
        self._scene.addItem(self._temp_edge)

    def update_port_drag(self, scene_pt: QPointF) -> None:
        """Vẽ lại đường nét đứt theo con trỏ trong lúc kéo."""
        if self._temp_edge is None or self._port_src_pt is None:
            return
        self._temp_edge.setPath(_ortho_path(self._port_src_pt, scene_pt))

    def finish_port_drag(self, scene_pt: QPointF) -> None:
        """Thả chuột: nối cạnh nếu rơi trúng một node khác, và luôn dọn đường tạm.

        Thả vào chỗ trống hay vào chính node nguồn đều không tạo cạnh — nhưng
        trạng thái kéo vẫn phải được xoá, nếu không đường nét đứt sẽ dính lại.
        """
        src = self._port_src
        if self._temp_edge is not None:
            self._scene.removeItem(self._temp_edge)
        self._temp_edge = None
        self._port_src = None
        self._port_src_pt = None
        tgt = self._node_at(scene_pt)
        if src and tgt and tgt != src:
            self._make_edge(src, tgt)

    def _node_at(self, scene_pt: QPointF) -> Optional[str]:
        """Id node nằm dưới một điểm trên khung; ``None`` nếu là chỗ trống."""
        for it in self._scene.items(scene_pt):
            if isinstance(it, _NodeItem):
                return it.node.id
        return None

    def _make_edge(self, source: str, target: str) -> None:
        """Tạo cạnh nguồn → đích.

        Bỏ qua cạnh tự nối và cạnh trùng cặp đã có — kéo hai lần cùng một
        hướng không được sinh ra hai đường chồng lên nhau.
        """
        if source == target:
            return
        if any(e.edge.source == source and e.edge.target == target for e in self._edges):
            return
        edge = Edge(id=new_edge_id(source, target), source=source, target=target)
        self._add_edge_item(edge)
        self._reposition_edges()
        self.graph_changed.emit()

    def _add_edge_item(self, edge: Edge) -> None:
        """Đưa một cạnh vào khung vẽ và vào danh sách quản lý."""
        item = _EdgeItem(edge, self)
        self._edges.append(item)
        self._scene.addItem(item)

    def delete_edge(self, edge: Edge) -> None:
        """Xoá cạnh, so khớp theo cặp nguồn/đích chứ không chỉ theo danh tính đối
        tượng — cạnh có thể đã được dựng lại sau một lần nạp.
        """
        for e in list(self._edges):
            if e.edge is edge or (e.edge.source == edge.source and e.edge.target == edge.target):
                self._scene.removeItem(e)
                self._edges.remove(e)
        self.graph_changed.emit()

    def delete_node(self, node_id: str) -> None:
        """Xoá một node và mọi cạnh dính vào nó. Id không tồn tại thì bỏ qua."""
        item = self._nodes.pop(node_id, None)
        if item is None:
            return
        self._scene.removeItem(item)
        for e in list(self._edges):
            if e.edge.source == node_id or e.edge.target == node_id:
                self._scene.removeItem(e)
                self._edges.remove(e)
        self._reposition_edges()
        self.graph_changed.emit()

    def delete_selected(self) -> None:
        """Xoá mọi node và cạnh đang được chọn.

        Xoá node trước: node kéo theo cạnh của nó, nên vòng lặp cạnh phía sau
        chỉ còn phải xử lý các cạnh được chọn riêng lẻ.
        """
        for nid in [it.node.id for it in self._nodes.values() if it.isSelected()]:
            self.delete_node(nid)
        for e in [it.edge for it in self._edges if it.isSelected()]:
            self.delete_edge(e)

    def update_node_status(self, node_id: str, status: str) -> None:
        """Đổi màu trạng thái của một node lúc luồng đang chạy (đang chạy/xong/lỗi)."""
        item = self._nodes.get(node_id)
        if item is not None:
            item.status = status
            item.update()

    def reset_statuses(self) -> None:
        """Đưa mọi node về trạng thái chờ — gọi trước mỗi lần chạy lại luồng."""
        for it in self._nodes.values():
            it.status = "idle"
            it.update()

    def refresh_node(self, node_id: str) -> None:
        """Vẽ lại một node sau khi nội dung bước của nó bị sửa."""
        item = self._nodes.get(node_id)
        if item is not None:
            item.update()

    def _node_rects(self, exclude):
        """Rectangles of every node except ``exclude`` (inflated a little), used
        as obstacles the edge router steers around."""
        m = 12.0
        out = []
        for nid, item in self._nodes.items():
            if nid in exclude:
                continue
            p = item.pos()
            out.append(QRectF(p.x(), p.y(), _NODE_W, _NODE_H).adjusted(-m, -m, m, m))
        return out

    def _reposition_edges(self) -> None:
        """Định tuyến lại mọi đường nối.

        Cạnh luôn đi từ cổng ra (giữa cạnh phải) sang cổng vào (giữa cạnh trái)
        và lách qua các node khác, nên luồng đọc được từ trái sang phải.
        """
        for e in self._edges:
            s = self._nodes.get(e.edge.source)
            t = self._nodes.get(e.edge.target)
            if s is None or t is None:
                continue
            src = s.pos() + QPointF(_NODE_W, _NODE_H / 2)   # right-center (output)
            dst = t.pos() + QPointF(0, _NODE_H / 2)          # left-center (input)
            obstacles = self._node_rects({e.edge.source, e.edge.target})
            e.update_path(_route(src, dst, obstacles))
