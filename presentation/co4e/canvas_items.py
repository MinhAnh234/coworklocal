"""Các item vẽ trực tiếp trên canvas Co4E — dời khỏi ``ui/co4e_canvas.py``.

Vấn đề đang có: gộp riêng ``Co4ECanvas`` (dòng 289-701 của file cũ) vào một
file mới đã đủ 413 dòng, vượt trần 400 dòng/file production của CASAN Check 2
— dù không đổi gì bên trong. ``_NodeItem``/``_EdgeItem`` (và hằng số/hàm phụ
trợ chúng dùng để vẽ) là phần độc lập nhất về mặt trách nhiệm: chỉ vẽ và xử lý
sự kiện chuột NGAY TRÊN item đó, gọi ngược vào canvas cha qua tham số
``canvas`` được truyền ở constructor — nên tách được sang module riêng mà
không cần đổi bất kỳ hành vi nào.

Cách làm: cắt dán NGUYÊN VĂN các khối dòng 43-56 (hằng số + ``_status_color``)
và 59-286 (``_NodeItem``, ``_EdgeItem``) từ ``ui/co4e_canvas.py`` sang đây,
không đổi tên/tham số/thứ tự/giá trị mặc định — kể cả các quirk đã bị
characterization test (``tests/characterization/test_co4e_canvas_widget.py``,
``test_co4e_canvas_geometry.py``) đóng đinh gián tiếp qua ``_rounded_path``/
``_route``/``_elide`` mà ``_EdgeItem.update_path``/``_NodeItem.paint`` gọi.

Tham số ``canvas: "Co4ECanvas"`` trong ``__init__`` của cả hai lớp dùng string
forward-reference vì ``Co4ECanvas`` giờ nằm ở module
``co4e_canvas_widget.py`` khác — import trực tiếp sẽ tạo vòng lặp (canvas
widget import ngược lại các item này). Đây thuần là type hint, không cần
import runtime.

``ui/co4e_canvas.py`` import lại các tên public (``CO4E_MIME`` qua
``co4e_canvas_widget.py``) để giữ nguyên đường import mà test/characterization
khác đang dùng.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject, QGraphicsPathItem, QMenu

from ...core.co4e import STEP_DONE, STEP_ERROR, STEP_PLANNED, STEP_RUNNING, Edge, Node
from ...theme import current_palette
from .canvas_geometry import _elide, _rounded_path


def _status_color(status: str) -> str:
    """Accent colour for a step's run status. Resolved per paint so the canvas
    follows a live theme switch."""
    p = current_palette()
    return {
        "idle": p.text_muted, STEP_RUNNING: p.accent, STEP_DONE: p.success,
        STEP_ERROR: p.danger, STEP_PLANNED: p.purple, "pending": p.text_faint,
    }.get(status, p.text_muted)

CO4E_MIME = "application/x-co4e-step"

_NODE_W, _NODE_H = 210, 96
_PORT_R = 6                 # output port radius (the drag-to-connect handle)
_PORT_HIT = 15             # click tolerance around a port


class _NodeItem(QGraphicsObject):
    """One draggable step card. Emits signals via the parent canvas."""

    def __init__(self, node: Node, canvas: "Co4ECanvas"):
        """Thẻ một bước trên khung vẽ: kéo được, chọn được, và báo cho khung vẽ mỗi khi
        nó đổi vị trí để đường nối vẽ lại theo.
        """
        super().__init__()
        self.node = node
        self.canvas = canvas
        self.status = "idle"
        self._porting = False
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable
                      | QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setPos(node.x, node.y)
        self.setZValue(2)

    def boundingRect(self) -> QRectF:
        """Khung bao của node, nới rộng hai bên cho hai cổng vào/ra vẽ trọn vẹn."""
        # slack left/right so the input/output ports (now on the sides) paint cleanly
        return QRectF(-_PORT_R - 2, -3, _NODE_W + 2 * _PORT_R + 4, _NODE_H + 6)

    def _card_rect(self) -> QRectF:
        """Khung thẻ (đã trừ 1px viền) — phần thân thật sự được vẽ."""
        return QRectF(1, 1, _NODE_W - 2, _NODE_H - 2)

    def paint(self, p, _opt, _widget=None):
        """Vẽ thẻ bước: viền, dải tiêu đề, nhãn, vai trò, xem trước nội dung, chân thẻ và hai cổng.

        Dải tiêu đề dùng màu trạng thái đã pha loãng (alpha 48) chứ không dùng
        nguyên màu — để chữ trên thẻ vẫn là thứ nổi nhất. Cổng vào (trái) rỗng
        ruột, cổng ra (phải) đặc ruột: cổng đặc chính là tay nắm để kéo nối sang
        bước sau, nên nó phải trông "cầm được".
        """
        tok = current_palette()
        step = self.node.data
        accent = QColor(_status_color(self.status))
        body = QColor(tok.surface_raised)
        border = QColor(tok.accent) if self.isSelected() else QColor(tok.border)
        p.setRenderHint(p.RenderHint.Antialiasing)
        rect = self._card_rect()
        path = QPainterPath()
        radius = float(tok.radius_lg)
        path.addRoundedRect(rect, radius, radius)
        p.fillPath(path, QBrush(body))
        p.setPen(QPen(border, 2 if self.isSelected() else 1))
        p.drawPath(path)
        # header stripe — a tint of the status colour, not the status colour
        # itself, so the card's own text stays the brightest thing on it.
        hdr = QRectF(rect.left(), rect.top(), rect.width(), 26)
        hpath = QPainterPath()
        hpath.addRoundedRect(hdr, radius, radius)
        stripe = QColor(accent)
        stripe.setAlpha(48)
        p.fillPath(hpath, QBrush(stripe))
        # label
        p.setPen(QColor(tok.text))
        f = p.font(); f.setBold(True); f.setPointSize(9); p.setFont(f)
        p.drawText(QRectF(10, 4, _NODE_W - 20, 20), Qt.AlignVCenter | Qt.AlignLeft,
                   _elide(step.label, 26))
        # role badge + status
        f.setBold(False); f.setPointSize(8); p.setFont(f)
        p.setPen(accent)
        p.drawText(QRectF(10, 30, _NODE_W - 20, 16), Qt.AlignLeft, step.role)
        # body: instructions preview OR sub-agent chips
        p.setPen(QColor(tok.text_muted))
        if step.is_parallel:
            preview = "⇉ " + ", ".join(s.agent for s in step.sub_agents) if step.sub_agents else "⇉ (no sub-agents)"
        else:
            preview = step.instructions or "(no instructions)"
        p.drawText(QRectF(10, 46, _NODE_W - 20, 30), Qt.TextWordWrap | Qt.AlignTop,
                   _elide(preview, 66))
        # footer: model + skills + status dot
        p.setPen(QColor(tok.text_faint))
        foot = []
        if step.model:
            foot.append(step.model)
        if step.skills:
            foot.append(f"skills:{len(step.skills)}")
        foot.append(self.status)
        p.drawText(QRectF(10, _NODE_H - 18, _NODE_W - 20, 14), Qt.AlignLeft,
                   _elide(" · ".join(foot), 34))
        # ---- ports ---------------------------------------------------------
        # input port (top-center): hollow. output port (bottom-center): filled —
        # the drag handle you pull to wire an edge to another step.
        port_col = QColor(tok.accent)
        # input port (left-center): hollow. output port (right-center): filled —
        # the drag handle you pull to wire an edge to the next step (left→right).
        p.setBrush(QBrush(body)); p.setPen(QPen(port_col, 1.4))
        p.drawEllipse(QPointF(1, _NODE_H / 2), _PORT_R - 1, _PORT_R - 1)
        p.setBrush(QBrush(port_col)); p.setPen(QPen(port_col, 1.4))
        p.drawEllipse(QPointF(_NODE_W - 1, _NODE_H / 2), _PORT_R, _PORT_R)

    def _in_out_port(self, pos: QPointF) -> bool:
        """Điểm ``pos`` có nằm trong vùng bắt của cổng ra không.

        Vùng bắt (``_PORT_HIT``) rộng hơn hình vẽ để chuột không cần trúng đúng
        chấm tròn nhỏ mới kéo được.
        """
        d = pos - QPointF(_NODE_W, _NODE_H / 2)
        return (d.x() * d.x() + d.y() * d.y()) ** 0.5 <= _PORT_HIT

    def itemChange(self, change, value):
        """Đồng bộ vị trí node về dữ liệu, và đưa node đang chọn lên trên.

        Kéo node xong phải ghi lại toạ độ vào ``self.node`` rồi vẽ lại đường nối,
        nếu không lần lưu kế tiếp sẽ ghi toạ độ cũ. Node được chọn nhảy lên
        z=4 (trên cả cạnh ở z=3) để không bị đường nối che lúc đang sửa.
        """
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.node.x = float(self.pos().x())
            self.node.y = float(self.pos().y())
            self.canvas._reposition_edges()
            self.canvas.graph_changed.emit()
        elif change == QGraphicsItem.ItemSelectedHasChanged:
            # a selected/edited node comes to the front (above the edges at z=3)
            self.setZValue(4 if value else 2)
            if value:
                self.canvas.node_selected.emit(self.node.id)
        return super().itemChange(change, value)

    def hoverMoveEvent(self, e):
        """Đổi con trỏ thành bàn tay khi rê qua cổng ra — gợi ý là kéo nối được."""
        # a hand cursor over the output port hints it's draggable-to-connect
        self.setCursor(Qt.PointingHandCursor if self._in_out_port(e.pos()) else Qt.ArrowCursor)
        super().hoverMoveEvent(e)

    def mousePressEvent(self, e):
        """Bấm chuột: chốt lượt nối đang chờ, hoặc bắt đầu kéo nối từ cổng ra.

        Thứ tự quan trọng: đang có lượt nối chờ (mở từ menu chuột phải) thì cú
        bấm này là chọn đích, không phải chọn node.
        """
        if self.canvas._connect_from is not None:
            self.canvas._finish_connect(self.node.id)
            e.accept()
            return
        if e.button() == Qt.LeftButton and self._in_out_port(e.pos()):
            # start a manual drag-to-connect from this node's output port
            self._porting = True
            self.canvas.begin_port_drag(self.node.id, self.mapToScene(QPointF(_NODE_W, _NODE_H / 2)))
            e.accept()
            return
        super().mousePressEvent(e)
        if self.isSelected():
            # itemChange() only emits node_selected when the SELECTION STATE
            # actually flips (ItemSelectedHasChanged) — clicking a node that
            # was already selected (e.g. left selected when a run started)
            # never re-fires it, so the property panel silently kept showing
            # stale data and looked "locked" while the node ran. Emit
            # explicitly on every click so the panel always reloads.
            self.canvas.node_selected.emit(self.node.id)

    def mouseMoveEvent(self, e):
        """Rê chuột trong lúc kéo nối: vẽ lại đường nét đứt theo con trỏ."""
        if self._porting:
            self.canvas.update_port_drag(self.mapToScene(e.pos()))
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        """Thả chuột: kết thúc lượt kéo nối (nối cạnh nếu rơi trúng node khác)."""
        if self._porting:
            self._porting = False
            self.canvas.finish_port_drag(self.mapToScene(e.pos()))
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        """Bấm đúp một bước: báo lên để mở bảng thuộc tính của bước đó."""
        self.canvas.node_activated.emit(self.node.id)
        e.accept()

    def contextMenuEvent(self, e):
        """Menu chuột phải trên node: thêm bước kế, nối từ đây, xoá bước."""
        menu = QMenu()
        a_add = menu.addAction("＋ Add next step")
        a_conn = menu.addAction("→ Connect from here")
        a_del = menu.addAction("🗑 Delete step")
        chosen = menu.exec(e.screenPos())
        if chosen is a_add:
            self.canvas.add_step_below(self.node.id)
        elif chosen is a_conn:
            self.canvas.begin_connect(self.node.id)
        elif chosen is a_del:
            self.canvas.delete_node(self.node.id)
        e.accept()

    def center(self) -> QPointF:
        """Toạ độ tâm node trên khung — dùng để định tuyến đường nối."""
        return self.pos() + QPointF(_NODE_W / 2, _NODE_H / 2)


class _EdgeItem(QGraphicsPathItem):
    """Một đường nối giữa hai bước, kèm mũi tên ở đầu đích.

    Nằm ở z=3, tức trên thẻ bước (z=2), để đường nối không bao giờ bị thẻ
    che khuất — node đang được chọn thì tự nhảy lên z=4.
    """
    def __init__(self, edge: Edge, canvas: "Co4ECanvas"):
        """Đường nối giữa hai bước.

        Đặt ``z=3``, trên thẻ bước (``z=2``): đường nối bị thẻ che thì không nhìn ra
        luồng chạy nữa.
        """
        super().__init__()
        self.edge = edge
        self.canvas = canvas
        self._dst: Optional[QPointF] = None
        # Above node cards (z=2) so a connecting line is never hidden behind a
        # step; a selected node bumps itself to the front while being edited.
        self.setZValue(3)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self._hover = False
        self._apply_pen()

    def _apply_pen(self):
        """Chọn màu và độ dày nét theo trạng thái: đang chọn > đang rê chuột > bình thường."""
        tok = current_palette()
        if self.isSelected():
            color, w = QColor(tok.accent), 3
        elif self._hover:
            color, w = QColor(tok.text_muted), 3
        else:
            color, w = QColor(tok.border_strong), 2
        self.setPen(QPen(color, w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

    def update_path(self, points):
        """Vẽ lại đường theo danh sách điểm đã định tuyến, nhớ lại điểm cuối để đặt mũi tên."""
        self._dst = points[-1] if points else None
        self.setPath(_rounded_path(points))

    def boundingRect(self):
        """Khung bao của đường, nới thêm 10px mỗi phía cho mũi tên."""
        return super().boundingRect().adjusted(-10, -10, 10, 10)   # room for the arrowhead

    def shape(self):
        """Nới vùng bấm/chọn lên 14px.

        Đường nối chỉ dày 2px — không nới thì gần như không thể trỏ trúng để
        chọn hay mở menu xoá.
        """
        # Widen the clickable/selectable area so a thin line is easy to grab.
        from PySide6.QtGui import QPainterPathStroker
        stroker = QPainterPathStroker()
        stroker.setWidth(14)
        return stroker.createStroke(self.path())

    def hoverEnterEvent(self, e):
        """Rê chuột vào: làm nét đậm lên để thấy rõ đang trỏ vào đường nào."""
        self._hover = True
        self._apply_pen()
        self.update()
        super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e):
        """Rời chuột: trả nét về trạng thái bình thường."""
        self._hover = False
        self._apply_pen()
        self.update()
        super().hoverLeaveEvent(e)

    def paint(self, p, opt, widget=None):
        """Vẽ đường nối và mũi tên tam giác chĩa vào cổng vào của node đích."""
        self._apply_pen()
        super().paint(p, opt, widget)
        # arrowhead at the target, pointing right into its (left) input port
        if self._dst is not None:
            p.setRenderHint(p.RenderHint.Antialiasing)
            tip = self._dst
            s = 7.0
            tri = QPolygonF([
                QPointF(tip.x() + 1, tip.y()),
                QPointF(tip.x() - s, tip.y() - s * 0.7),
                QPointF(tip.x() - s, tip.y() + s * 0.7),
            ])
            col = self.pen().color()
            p.setBrush(QBrush(col))
            p.setPen(QPen(col, 1))
            p.drawPolygon(tri)

    def contextMenuEvent(self, e):
        """Menu chuột phải trên đường nối: xoá liên kết."""
        menu = QMenu()
        act_del = menu.addAction("🗑 Delete connection")
        if menu.exec(e.screenPos()) is act_del:
            self.canvas.delete_edge(self.edge)
        e.accept()
