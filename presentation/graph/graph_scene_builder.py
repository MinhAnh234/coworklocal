"""Dựng các item Qt cho khung đồ thị 2D — tách khỏi ``graph_renderer.py``.

Đây là phần "biến dữ liệu thành hình" của GraphRAG: nhận một đồ thị đã quét
cùng bảng toạ độ, đổ ``_Node``/``_Edge`` vào ``QGraphicsScene`` rồi trả lại
danh sách item và trọng tâm cho bên gọi.

Tách ra vì nó không cần biết gì về widget: không đọc thuộc tính nào của
``GraphRenderer``, không phát tín hiệu, không chạm cấu hình. Nhờ thế mà thử
được bằng một ``QGraphicsScene`` trần, và ``graph_renderer.py`` bớt đi phần
duy nhất trong nó có tính toán hình học thật sự.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsScene

from cowork_local.presentation.graph.graph_scene_items import _Edge, _Node


def node_degrees(graph) -> Dict[str, int]:
    """Số cạnh chạm vào từng node.

    Dùng để định cỡ node: node càng nhiều liên kết thì vẽ càng to, nên mắt
    người nhìn vào là thấy ngay đâu là đầu mối của cả đồ thị.
    """
    degree = {n.id: 0 for n in graph.nodes}
    for edge in graph.edges:
        if edge.source in degree:
            degree[edge.source] += 1
        if edge.target in degree:
            degree[edge.target] += 1
    return degree


def node_radius(degree: int) -> int:
    """Bán kính vẽ của một node theo bậc của nó.

    Lấy căn bậc hai chứ không lấy tuyến tính: bậc tăng gấp bốn thì bán kính
    mới gấp đôi, nhờ vậy DIỆN TÍCH mới tỉ lệ với bậc — đó mới là thứ mắt
    người thật sự so sánh. Chặn trên ở 28 để một node trung tâm không nuốt
    mất phần còn lại của đồ thị.
    """
    return int(8 + min(20, 2.2 * math.sqrt(degree)))


def build_scene(
    scene: QGraphicsScene, graph, pos: Dict[str, Tuple[float, float]], bg: str
) -> Tuple[List[_Node], List[_Edge], QPointF]:
    """Xoá sạch ``scene`` rồi dựng lại toàn bộ node và cạnh của ``graph``.

    ``pos`` là toạ độ đã tính sẵn ở luồng nền (``{node_id: (x, y)}``); node
    không có trong đó rơi về gốc toạ độ thay vì bị bỏ, để không im lặng đánh
    mất dữ liệu.

    Cạnh chỉ được vẽ khi CẢ HAI đầu đều có item — đồ thị bị cắt bớt
    (``truncated``) hay dữ liệu lệch có thể trỏ tới node không tồn tại, và
    một ``_Edge`` treo lơ lửng sẽ làm hỏng cả phép tính khung nhìn.

    Trả về ``(danh sách node, danh sách cạnh, trọng tâm)``. Trọng tâm là
    trung bình cộng toạ độ các node, dùng làm tâm khi thu phóng.
    """
    scene.clear()
    scene.setBackgroundBrush(QColor(bg))

    degree = node_degrees(graph)
    items: Dict[str, _Node] = {}
    node_items: List[_Node] = []
    sx = sy = 0.0
    for node in graph.nodes:
        item = _Node(node, node_radius(degree.get(node.id, 0)))
        x, y = pos.get(node.id, (0, 0))
        item.setPos(x, y)
        scene.addItem(item)
        items[node.id] = item
        node_items.append(item)
        sx += x
        sy += y

    edge_items: List[_Edge] = []
    for edge in graph.edges:
        a, b = items.get(edge.source), items.get(edge.target)
        if a and b:
            e = _Edge(a, b, getattr(edge, "type", ""))
            scene.addItem(e)
            edge_items.append(e)

    n = max(1, len(node_items))
    return node_items, edge_items, QPointF(sx / n, sy / n)


__all__ = ["build_scene", "node_degrees", "node_radius"]
