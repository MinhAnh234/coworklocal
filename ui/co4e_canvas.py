"""Co4E node canvas — a QGraphicsView node-graph editor.

Renders workflow nodes as draggable cards and edges as rounded orthogonal
("elbow with rounded corners") arrows. Supports: drag to move (positions
persist), click to select (→ right config panel), drag-to-connect from a node's
output port (bottom) to another node, a context-menu "connect" mode, "add step
below" (auto-connected child), delete, zoom (Ctrl+wheel / buttons), auto-fit,
and drops from the sidebar palette (agent/skill/parallel/whole-flow) via the
``application/x-co4e-step`` mime type.

Kept UI-only; the graph model lives in ``core/co4e.py``.
"""
from __future__ import annotations

# _NodeItem/_EdgeItem (hằng số vẽ + hai lớp QGraphicsItem) đã dời sang
# presentation/co4e/canvas_items.py; Co4ECanvas (mutation đồ thị) đã dời sang
# presentation/co4e/co4e_canvas_widget.py, phần tương tác view (zoom/pan/
# relayout/phím tắt/kéo-thả) nằm trong _CanvasInteractionMixin cùng thư mục.
# Không đổi hành vi — xem characterization test cùng tên và docstring ở từng
# file đích. Import ĐÍCH DANH tên gốc, không alias — nếu đổi thành
# `import co4e_canvas_widget as _w` thì các chỗ gọi bên dưới (và cả test cũ)
# vẫn chạy được vì Python cho phép, nhưng lại sai mục đích của việc giữ nguyên
# tên: test characterization import trực tiếp các tên này TỪ module này,
# alias sẽ làm test đó ngưng chứng minh được điều nó cần chứng minh.
from ..presentation.co4e.canvas_items import (
    _NODE_H, _NODE_W, _PORT_HIT, _PORT_R, _EdgeItem, _NodeItem, _status_color,
)
# 8 hàm hình học thuần đã dời sang canvas_geometry.py (không đổi hành vi, xem
# characterization test cùng tên). Import ĐÍCH DANH tên gốc, không alias — nếu
# đổi thành `import canvas_geometry as _g` thì các chỗ gọi bên dưới (và cả
# test cũ) vẫn chạy được vì Python cho phép, nhưng lại sai mục đích của việc
# giữ nguyên tên: test characterization import trực tiếp các tên này TỪ module
# này, alias sẽ làm test đó ngưng chứng minh được điều nó cần chứng minh.
from ..presentation.co4e.canvas_geometry import (
    _dist, _elide, _hits, _ortho_path, _route, _rounded_path, _seg_hits_rect,
    _towards,
)
from ..presentation.co4e.co4e_canvas_widget import Co4ECanvas, CO4E_MIME
