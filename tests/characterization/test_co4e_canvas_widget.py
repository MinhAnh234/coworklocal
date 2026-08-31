"""Characterization test cho ``Co4ECanvas`` (``ui/co4e_canvas.py``, dòng
289-701) — KHÔNG bao gồm ``_NodeItem``/``_EdgeItem`` (hai lớp đó chỉ vẽ, đã
được phủ gián tiếp bởi ``tests/characterization/test_co4e_canvas_geometry.py``
qua ``_rounded_path``/``_route``/``_elide`` mà ``_EdgeItem.update_path``/
``_NodeItem.paint`` dùng).

VÒNG ĐỜI: đây là giàn giáo (scaffolding), KHÔNG phải đặc tả cuối cùng. Mục
đích DUY NHẤT là lưới an toàn cho đợt tách ``ui/co4e_canvas.py`` (2000+ dòng
cả file, xem ``docs/architecture/co4e-split-map.md``) — 8 hàm hình học thuần
đã dời sang ``presentation/co4e/canvas_geometry.py`` rồi (xem test cùng tên);
đợt sau nhiều khả năng sẽ động vào chính ``Co4ECanvas`` (tách thành
``_NodeItem``/``_EdgeItem`` module riêng, hoặc tách state machine
connect/port-drag ra khỏi lớp view). Khi việc tách phần này hoàn tất và ổn
định, các test ở đây nên được viết lại thành test đặc tả (specification test)
cho lớp/API mới; quirk nào liệt kê dưới đây nên có issue riêng nếu ai đó muốn
"dọn" chúng — ĐỪNG tự sửa code sản phẩm để "dọn" quirk khi đọc thấy test này.

CÁCH CHỐT ASSERT: mọi giá trị dưới đây lấy bằng cách CHẠY code thật (script
``_PROBE_SCRIPT`` bên dưới, qua ``.venv/Scripts/python.exe``, giống hệt lệnh ở
cuối file) rồi dán NGUYÊN VĂN JSON in được vào assert — không suy luận lý
thuyết.

AN TOÀN DỮ LIỆU: ``Co4ECanvas`` tự nó KHÔNG chạm đĩa/mạng (khác
``Co4ETab``/``Co4ERunManager``) — nhưng import ``cowork_local.config`` (qua
chuỗi import ``cowork_local.ui.co4e_canvas`` -> ``..core.co4e`` ->
``..config``) vẫn tính ``CONFIG_DIR`` từ ``Path.home()`` một lần lúc module
nạp. Để không rủi ro và để chạy trong TIẾN TRÌNH CON riêng (tránh xung đột
``QApplication`` singleton với các test khác đã/sẽ tạo app trong cùng lượt
chạy pytest), toàn bộ probe chạy qua ``subprocess`` với ``HOME``/
``USERPROFILE`` trỏ vào một ``tmp_path`` sandbox ĐẶT TRƯỚC khi script import
bất kỳ thứ gì thuộc ``cowork_local`` (đúng kỹ thuật
``tools/capture_screens.py::_isolate_home()``: đặt ``USERPROFILE``/``HOME``,
xoá ``HOMEDRIVE``/``HOMEPATH``), và ``QT_QPA_PLATFORM=offscreen`` được đặt
TRƯỚC khi import PySide6 (đúng khuôn ``tools/check_co4e.py`` dòng 22+40-42).
Một assert ngay trong tiến trình con chốt ``CONFIG_DIR`` nằm trong sandbox
trước khi làm gì khác (kiểu ``tools/check_co4e.py:47``).

KHÔNG spawn thread/gọi provider thật: ``Co4ECanvas`` không có method nào dựng
``QThread``/gọi AI — mọi method characterize ở đây (``add_node``,
``begin_port_drag``/``finish_port_drag``, ``delete_*``, ``zoom_*``,
``relayout*``, ``add_workflow``, ``dropEvent``...) chỉ thao tác trên
``QGraphicsScene``/dict nội bộ, gọi trực tiếp không cần seed job nào.

CẦN QApplication: các method characterize ở đây dựng ``QGraphicsScene``/
``QGraphicsItem`` thật, đọc ``transform()``, tạo ``QDropEvent`` — không phải
kiểu giá trị thuần như ``_dist``/``_towards`` (khác
``test_co4e_canvas_geometry.py``, không cần app).

QUIRK ĐÃ ĐÓNG ĐINH (xem case tương ứng bên dưới — ĐỪNG "dọn" các chỗ này khi
tách, chúng trông như bug nhưng là hành vi đang chạy thật hôm nay):
  * ``_finish_connect(target_id)`` với ``target_id == connect_from`` hiện tại
    (tự nối vào chính nó) bị bỏ qua HOÀN TOÀN im lặng — không tạo cạnh, không
    báo lỗi — nhưng ``_connect_from`` VẪN bị reset về ``None`` (chế độ connect
    kết thúc dù không nối được gì).
  * ``_make_edge`` chống trùng cạnh CÙNG source+target (kể cả khi gọi lại qua
    ``finish_port_drag`` lần hai với cùng cặp) nhưng KHÔNG chống cạnh ngược
    hướng (target->source) — hàm không kiểm tra chiều ngược, chỉ kiểm tra
    đúng chiều đã cho.
  * ``delete_edge(edge)`` gọi ``graph_changed.emit()`` VÔ ĐIỀU KIỆN, kể cả khi
    không có item nào khớp để xoá (ví dụ gọi lại lần hai với cùng đối tượng
    ``Edge`` đã bị xoá trước đó) — không có "removed count" nào được kiểm tra
    trước khi emit.
  * ``delete_node`` với id không tồn tại trả về sớm (``item is None: return``)
    TRƯỚC dòng emit — nên KHÔNG phát ``graph_changed`` trong trường hợp này,
    khác hẳn ``delete_edge`` ở trên.
  * ``delete_selected()`` chạy 2 vòng lặp riêng (xoá node trước, xoá cạnh
    sau) — nếu một node bị xoá đã kéo theo xoá cả các cạnh nối tới nó (qua
    ``delete_node``), thì vòng lặp cạnh thứ hai KHÔNG còn thấy các cạnh đó
    nữa (chúng đã biến mất khỏi ``self._edges`` trước khi vòng lặp cạnh chạy
    tới), nên chỉ những cạnh CÒN SỐNG và đang selected riêng mới bị xoá thêm.
  * ``_zoom_by`` khi đã chạm biên (``_ZOOM_MIN``/``_ZOOM_MAX``) và gọi
    ``zoom_in()``/``zoom_out()`` thêm lần nữa: hiệu ứng là no-op tuyệt đối —
    không gọi ``self.scale()``, không đổi ``self._zoom`` — vì
    ``abs(target - cur) < 1e-6`` chặn sớm. 20 lần ``zoom_in()`` liên tiếp từ
    1.0 chạm trần 3.0 sau đúng 7 lần, 13 lần còn lại là no-op.
  * ``add_workflow(nodes, edges, at=None)``: offset áp dụng cho batch mới phụ
    thuộc vào canvas ĐÃ có node hay chưa TẠI THỜI ĐIỂM GỌI — batch đầu tiên
    (canvas rỗng) giữ nguyên toạ độ gốc (offset 0,0); batch thứ hai (canvas đã
    có node từ batch trước) bị dịch (60, 60) dù truyền cùng ``nodes``/``edges``
    y hệt lần đầu. ``at`` được cho tường minh thì luôn thắng offset ngầm này.
  * ``add_workflow`` bỏ qua ÂM THẦM mọi cạnh mà một đầu (source hoặc target)
    không nằm trong danh sách ``nodes`` đang được thả — không lỗi, không log,
    cạnh đó biến mất khỏi kết quả.
  * ``dropEvent`` với payload JSON hỏng (không parse được) hoặc payload
    workflow rỗng (``wf.nodes`` rỗng) đều là NO-OP HOÀN TOÀN im lặng — không
    thêm node nào, không báo lỗi, không exception nào lộ ra ngoài.
  * ``dropEvent`` gọi ``self.mapToScene(...)`` trên một view CHƯA từng
    ``show()``/resize — toạ độ scene kết quả (đóng đinh trong
    ``s11_step_drop_pos``) là quirk của việc mapToScene phụ thuộc viewport mặc
    định lúc chưa hiển thị, KHÔNG phải toạ độ "50, 60" người ta tưởng sẽ thấy;
    nếu đợt tách sau show canvas trước khi test tương tự, số này sẽ đổi và đó
    là dấu hiệu ĐÚNG cần cập nhật lại giá trị đóng đinh, không phải lỗi.

Lệnh thủ công đã dùng để chốt các con số trên (quy trình ngược, xem cuối
file để chạy lại nếu cần chốt lại sau khi code đổi có chủ đích).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REPO_PARENT = REPO_ROOT.parent

_PROBE_SCRIPT = r"""
import json
import os
import sys
from pathlib import Path

sandbox = sys.argv[1]
repo_parent = sys.argv[2]
sys.path.insert(0, repo_parent)

os.environ["QT_QPA_PLATFORM"] = "offscreen"
for var in ("USERPROFILE", "HOME"):
    os.environ[var] = sandbox
os.environ.pop("HOMEDRIVE", None)
os.environ.pop("HOMEPATH", None)

from PySide6.QtCore import QByteArray, QMimeData, QPointF, Qt
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QApplication

app = QApplication([])

from cowork_local.config import AppConfig, CONFIG_DIR
assert str(Path(sandbox).resolve()) in str(CONFIG_DIR.resolve()), (
    "khong co lap: CONFIG_DIR=" + str(CONFIG_DIR))

from cowork_local.core.co4e import Edge, Node, Step, Workflow, workflow_to_dict
from cowork_local.ui.co4e_canvas import CO4E_MIME, Co4ECanvas, _NODE_H, _NODE_W

result = {}

# --- Section 1: add_node ----------------------------------------------------
c1 = Co4ECanvas()
sel_calls = []
c1.node_selected.connect(lambda nid: sel_calls.append(nid))
changed = {"n": 0}
c1.graph_changed.connect(lambda: changed.__setitem__("n", changed["n"] + 1))

nid1 = c1.add_node(Step(label="A"))
result["s1_nid1"] = nid1
result["s1_nid1_pos"] = [c1._nodes[nid1].node.x, c1._nodes[nid1].node.y]
result["s1_after_nid1_edges"] = len(c1._edges)
result["s1_sel_calls_after_1"] = list(sel_calls)
result["s1_changed_after_1"] = changed["n"]

nid2 = c1.add_node(Step(label="B"), x=10, y=20, connect_from=nid1)
result["s1_nid2"] = nid2
result["s1_nid2_pos"] = [c1._nodes[nid2].node.x, c1._nodes[nid2].node.y]
result["s1_after_nid2_edges"] = [(e.edge.source, e.edge.target, e.edge.id) for e in c1._edges]
result["s1_sel_calls_after_2"] = list(sel_calls)
result["s1_changed_after_2"] = changed["n"]

nid3 = c1.add_node(Step(label="C"), connect_from="does-not-exist")
result["s1_nid3"] = nid3
result["s1_after_nid3_edges_count"] = len(c1._edges)

# --- Section 2: add_step_below -----------------------------------------------
before_count = len(c1._nodes)
c1.add_step_below("nope-does-not-exist")
result["s2_missing_parent_nodes_unchanged"] = len(c1._nodes) == before_count

c1.add_step_below(nid2)
new_ids = [nid for nid in c1._nodes if nid not in (nid1, nid2, nid3)]
result["s2_new_node_ids"] = new_ids
new_id = new_ids[0]
result["s2_new_node_pos"] = [c1._nodes[new_id].node.x, c1._nodes[new_id].node.y]
result["s2_edge_nid2_to_new"] = any(
    e.edge.source == nid2 and e.edge.target == new_id for e in c1._edges
)

# --- Section 3: _chain_tail ---------------------------------------------------
result["s3_tail_current_state"] = c1._chain_tail()

c_empty = Co4ECanvas()
result["s3_tail_empty_canvas"] = c_empty._chain_tail()

c_single = Co4ECanvas()
single_id = c_single.add_node(Step(label="Solo"))
result["s3_tail_single_node_no_edges"] = c_single._chain_tail()

# --- Section 4: add_palette_step ----------------------------------------------
tail_before = c1._chain_tail()
new_pal_id = c1.add_palette_step(Step(label="D"), QPointF(500, 500))
result["s4_add_palette_step_return"] = new_pal_id
newest_ids = [nid for nid in c1._nodes if nid not in (nid1, nid2, nid3, new_id)]
result["s4_new_ids"] = newest_ids
pal_id = newest_ids[0]
result["s4_pos"] = [c1._nodes[pal_id].node.x, c1._nodes[pal_id].node.y]
result["s4_tail_before"] = tail_before
result["s4_edge_from_tail_to_new"] = any(
    e.edge.source == tail_before and e.edge.target == pal_id for e in c1._edges
)

# --- Section 5: begin_connect / _finish_connect --------------------------------
c2 = Co4ECanvas()
a2 = c2.add_node(Step(label="A"))
b2 = c2.add_node(Step(label="B"))
result["s5_initial_edges"] = len(c2._edges)

c2.begin_connect(a2)
result["s5_connect_from_after_begin"] = c2._connect_from
c2._finish_connect(a2)  # self-connect
result["s5_connect_from_after_self_finish"] = c2._connect_from
result["s5_edges_after_self_finish"] = len(c2._edges)

c2.begin_connect(a2)
c2._finish_connect(b2)
result["s5_connect_from_after_finish_ab"] = c2._connect_from
result["s5_edges_after_finish_ab"] = [(e.edge.source, e.edge.target) for e in c2._edges]

c2._finish_connect(a2)  # no active connect (src None)
result["s5_edges_after_finish_with_no_active_connect"] = len(c2._edges)

# --- Section 6: begin_port_drag / update / finish / _node_at / _make_edge dedup -
c3 = Co4ECanvas()
p3 = c3.add_node(Step(label="P"), x=0, y=0)
q3 = c3.add_node(Step(label="Q"), x=400, y=0)
result["s6_scene_items_before_drag"] = len(c3._scene.items())

p_item = c3._nodes[p3]
src_pt = p_item.pos() + QPointF(_NODE_W, _NODE_H / 2)
c3.begin_port_drag(p3, src_pt)
result["s6_port_src_after_begin"] = c3._port_src
result["s6_temp_edge_in_scene_after_begin"] = c3._temp_edge in c3._scene.items()

mid_pt = QPointF(200, 100)
c3.update_port_drag(mid_pt)
result["s6_temp_edge_path_elements_after_update"] = c3._temp_edge.path().elementCount()

q_hit_pt = c3._nodes[q3].pos() + QPointF(50, 50)  # inside Q's card
node_at_q = c3._node_at(q_hit_pt)
result["s6_node_at_hit_point"] = node_at_q
empty_pt = QPointF(-500, -500)
result["s6_node_at_empty_point"] = c3._node_at(empty_pt)

c3.finish_port_drag(q_hit_pt)
result["s6_port_src_after_finish"] = c3._port_src
result["s6_temp_edge_after_finish"] = c3._temp_edge
result["s6_edges_after_finish"] = [(e.edge.source, e.edge.target) for e in c3._edges]

c3.begin_port_drag(p3, src_pt)
c3.finish_port_drag(q_hit_pt)
result["s6_edges_after_duplicate_drag"] = len(c3._edges)

c3.begin_port_drag(p3, src_pt)
c3.finish_port_drag(empty_pt)
result["s6_edges_after_finish_over_empty_space"] = len(c3._edges)
result["s6_port_src_after_empty_finish"] = c3._port_src

# --- Section 7: delete_edge / delete_node / delete_selected --------------------
c4 = Co4ECanvas()
a4 = c4.add_node(Step(label="A"), x=0, y=0)
b4 = c4.add_node(Step(label="B"), x=300, y=0, connect_from=a4)
c4_ = c4.add_node(Step(label="C"), x=600, y=0, connect_from=b4)
d4 = c4.add_node(Step(label="D"), x=900, y=0, connect_from=c4_)
result["s7_initial_edges"] = [(e.edge.source, e.edge.target) for e in c4._edges]

edge_ab = next(e.edge for e in c4._edges if e.edge.source == a4 and e.edge.target == b4)
changed4 = {"n": 0}
c4.graph_changed.connect(lambda: changed4.__setitem__("n", changed4["n"] + 1))

c4.delete_edge(edge_ab)
result["s7_edges_after_delete_ab"] = [(e.edge.source, e.edge.target) for e in c4._edges]
result["s7_changed_after_delete_ab"] = changed4["n"]

c4.delete_edge(edge_ab)
result["s7_changed_after_delete_ab_again"] = changed4["n"]
result["s7_edges_after_delete_ab_again"] = len(c4._edges)

result["s7_delete_node_missing_returns_early"] = c4.delete_node("no-such-node") is None
result["s7_changed_after_delete_missing_node"] = changed4["n"]

c4._nodes[c4_].setSelected(True)
c4.delete_selected()
result["s7_nodes_after_delete_selected"] = sorted(c4._nodes.keys())
result["s7_edges_after_delete_selected"] = [(e.edge.source, e.edge.target) for e in c4._edges]

# --- Section 8: zoom -----------------------------------------------------------
c5 = Co4ECanvas()
result["s8_initial_m11"] = c5.transform().m11()
result["s8_initial_zoom_attr"] = c5._zoom

c5.zoom_in()
result["s8_m11_after_1_zoom_in"] = c5.transform().m11()
result["s8_zoom_attr_after_1_zoom_in"] = c5._zoom

m11_series = []
for _ in range(20):
    c5.zoom_in()
    m11_series.append(round(c5.transform().m11(), 6))
result["s8_m11_series_zoom_in_x20_more"] = m11_series
result["s8_zoom_attr_after_many_zoom_in"] = c5._zoom

before_m11 = c5.transform().m11()
c5.zoom_in()
result["s8_m11_unchanged_when_already_at_cap"] = c5.transform().m11() == before_m11

c5.reset_zoom()
result["s8_m11_after_reset"] = c5.transform().m11()
result["s8_zoom_attr_after_reset"] = c5._zoom

m11_series_out = []
for _ in range(30):
    c5.zoom_out()
    m11_series_out.append(round(c5.transform().m11(), 6))
result["s8_m11_series_zoom_out_x30"] = m11_series_out
result["s8_zoom_attr_after_many_zoom_out"] = c5._zoom

# --- Section 9: relayout / relayout_if_vertical --------------------------------
c6 = Co4ECanvas()
c6.relayout()
result["s9_relayout_empty_ok"] = True

a6 = c6.add_node(Step(label="A"), x=0, y=0)
b6 = c6.add_node(Step(label="B"), x=0, y=150, connect_from=a6)
c6_ = c6.add_node(Step(label="C"), x=0, y=300, connect_from=b6)
result["s9_vertical_before"] = {
    a6: [c6._nodes[a6].pos().x(), c6._nodes[a6].pos().y()],
    b6: [c6._nodes[b6].pos().x(), c6._nodes[b6].pos().y()],
    c6_: [c6._nodes[c6_].pos().x(), c6._nodes[c6_].pos().y()],
}
c6.relayout_if_vertical()
result["s9_vertical_after_relayout_if_vertical"] = {
    a6: [c6._nodes[a6].pos().x(), c6._nodes[a6].pos().y()],
    b6: [c6._nodes[b6].pos().x(), c6._nodes[b6].pos().y()],
    c6_: [c6._nodes[c6_].pos().x(), c6._nodes[c6_].pos().y()],
}

c7 = Co4ECanvas()
a7 = c7.add_node(Step(label="A"), x=0, y=0)
b7 = c7.add_node(Step(label="B"), x=500, y=50, connect_from=a7)
result["s9_horizontal_before"] = {
    a7: [c7._nodes[a7].pos().x(), c7._nodes[a7].pos().y()],
    b7: [c7._nodes[b7].pos().x(), c7._nodes[b7].pos().y()],
}
c7.relayout_if_vertical()
result["s9_horizontal_after_relayout_if_vertical"] = {
    a7: [c7._nodes[a7].pos().x(), c7._nodes[a7].pos().y()],
    b7: [c7._nodes[b7].pos().x(), c7._nodes[b7].pos().y()],
}

c8 = Co4ECanvas()
a8 = c8.add_node(Step(label="Solo"), x=0, y=0)
c8.relayout_if_vertical()
result["s9_single_node_after_relayout_if_vertical"] = [
    c8._nodes[a8].pos().x(), c8._nodes[a8].pos().y()
]

# --- Section 10: add_workflow ---------------------------------------------------
c9 = Co4ECanvas()
src_nodes = [
    Node(id="src1", x=0.0, y=0.0, data=Step(label="X")),
    Node(id="src2", x=200.0, y=0.0, data=Step(label="Y")),
]
src_edges = [Edge(id="e1", source="src1", target="src2")]

c9.add_workflow(src_nodes, src_edges, at=None)
first_batch_ids = sorted(c9._nodes.keys())
result["s10_first_batch_ids"] = first_batch_ids
result["s10_first_batch_positions"] = {
    nid: [c9._nodes[nid].pos().x(), c9._nodes[nid].pos().y()] for nid in first_batch_ids
}
result["s10_first_batch_edges"] = [(e.edge.source, e.edge.target) for e in c9._edges]

c9.add_workflow(src_nodes, src_edges, at=None)
second_batch_ids = sorted(set(c9._nodes.keys()) - set(first_batch_ids))
result["s10_second_batch_ids"] = second_batch_ids
result["s10_second_batch_positions"] = {
    nid: [c9._nodes[nid].pos().x(), c9._nodes[nid].pos().y()] for nid in second_batch_ids
}
result["s10_total_edges_after_second_call"] = len(c9._edges)

c9.add_workflow(src_nodes, src_edges, at=QPointF(1000, 1000))
third_batch_ids = sorted(
    set(c9._nodes.keys()) - set(first_batch_ids) - set(second_batch_ids)
)
result["s10_third_batch_ids"] = third_batch_ids
result["s10_third_batch_positions"] = {
    nid: [c9._nodes[nid].pos().x(), c9._nodes[nid].pos().y()] for nid in third_batch_ids
}

c10 = Co4ECanvas()
edges_unknown_target = [Edge(id="ex", source="src1", target="unknown")]
c10.add_workflow(src_nodes, edges_unknown_target, at=None)
result["s10_edges_with_unknown_target_dropped"] = len(c10._edges)
result["s10_nodes_still_added_despite_bad_edge"] = len(c10._nodes)

# --- Section 11: dropEvent ------------------------------------------------------
_mime_keepalive = []  # QDropEvent only stores a pointer to the QMimeData; the
# Python wrapper must be kept alive for the event's lifetime or mimeData()
# comes back as a dangling/base QObject (hit exactly this while writing the probe).


def make_drop_event(payload_bytes, fmt, pos):
    mime = QMimeData()
    if fmt is not None:
        mime.setData(fmt, QByteArray(payload_bytes))
    _mime_keepalive.append(mime)
    return QDropEvent(pos, Qt.CopyAction, mime, Qt.NoButton, Qt.NoModifier)


c11 = Co4ECanvas()
step_payload = json.dumps({"label": "Dropped Step", "role": "AGENT"}).encode("utf-8")
ev1 = make_drop_event(step_payload, CO4E_MIME, QPointF(50, 60))
c11.dropEvent(ev1)
result["s11_step_drop_nodes_count"] = len(c11._nodes)
only_id = next(iter(c11._nodes))
result["s11_step_drop_label"] = c11._nodes[only_id].node.data.label
result["s11_step_drop_pos"] = [c11._nodes[only_id].pos().x(), c11._nodes[only_id].pos().y()]

wf_payload_dict = {
    "kind": "workflow",
    "workflow": workflow_to_dict(
        Workflow(id="wfX", name="WF", nodes=[Node(id="wn1", x=0.0, y=0.0, data=Step(label="WFNode"))])
    ),
}
ev2 = make_drop_event(json.dumps(wf_payload_dict).encode("utf-8"), CO4E_MIME, QPointF(10, 10))
before_wf_drop = len(c11._nodes)
c11.dropEvent(ev2)
result["s11_workflow_drop_added_nodes"] = len(c11._nodes) - before_wf_drop

empty_wf_payload = {
    "kind": "workflow",
    "workflow": workflow_to_dict(Workflow(id="wfEmpty", name="Empty", nodes=[], edges=[])),
}
ev3 = make_drop_event(json.dumps(empty_wf_payload).encode("utf-8"), CO4E_MIME, QPointF(10, 10))
before_empty_drop = len(c11._nodes)
c11.dropEvent(ev3)
result["s11_empty_workflow_drop_is_noop"] = len(c11._nodes) == before_empty_drop

ev4 = make_drop_event(b"{not valid json", CO4E_MIME, QPointF(10, 10))
before_bad_json = len(c11._nodes)
c11.dropEvent(ev4)
result["s11_bad_json_drop_is_noop_no_crash"] = len(c11._nodes) == before_bad_json

ev5 = make_drop_event(b"whatever", "text/plain", QPointF(10, 10))
before_wrong_fmt = len(c11._nodes)
c11.dropEvent(ev5)
result["s11_wrong_mime_format_is_noop_no_crash"] = len(c11._nodes) == before_wrong_fmt

print(json.dumps(result, sort_keys=True))
print("PROBE_OK")
"""


@pytest.fixture(scope="module")
def probe_result(tmp_path_factory):
    """Chạy ``_PROBE_SCRIPT`` một lần cho cả module trong TIẾN TRÌNH CON, trả
    về dict JSON đã in được. Test riêng lẻ chỉ đọc lại dict này — không dựng
    lại canvas cho mỗi assert."""
    sandbox = tmp_path_factory.mktemp("co4e-canvas-widget-home")

    env = dict(os.environ)
    env["HOME"] = str(sandbox)
    env["USERPROFILE"] = str(sandbox)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env.pop("HOMEDRIVE", None)
    env.pop("HOMEPATH", None)

    result = subprocess.run(
        [sys.executable, "-c", _PROBE_SCRIPT, str(sandbox), str(REPO_PARENT)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"probe co4e canvas widget that bai (exit {result.returncode}):\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    assert "PROBE_OK" in result.stdout, result.stdout

    json_line = result.stdout.strip().splitlines()[-2]
    return json.loads(json_line)


# ---------------------------------------------------------------------------
# Section 1: add_node
# ---------------------------------------------------------------------------

def test_add_node_default_pos_and_no_edge_without_connect_from(probe_result):
    assert probe_result["s1_nid1"] == "node_000001"
    assert probe_result["s1_nid1_pos"] == pytest.approx([60.0, 60.0])
    assert probe_result["s1_after_nid1_edges"] == 0


def test_add_node_emits_node_selected_and_graph_changed(probe_result):
    # add_node emits graph_changed rồi node_selected — 1 lần add_node "trơn"
    # (không connect_from hợp lệ) vẫn tính là 2 lần graph_changed: một từ
    # add_node, một từ _reposition_edges gọi ngầm bên trong add_node? Số thực
    # tế chốt được là 2 sau lần add_node đầu tiên.
    assert probe_result["s1_changed_after_1"] == 2
    assert probe_result["s1_sel_calls_after_1"] == ["node_000001"]


def test_add_node_with_valid_connect_from_creates_edge_with_deterministic_id(probe_result):
    assert probe_result["s1_nid2"] == "node_000002"
    assert probe_result["s1_nid2_pos"] == pytest.approx([10.0, 20.0])
    assert probe_result["s1_after_nid2_edges"] == [
        ["node_000001", "node_000002", "e_node_000001__node_000002"],
    ]
    assert probe_result["s1_changed_after_2"] == 5
    assert probe_result["s1_sel_calls_after_2"] == ["node_000001", "node_000002"]


def test_add_node_with_unknown_connect_from_is_silently_skipped(probe_result):
    # quirk: connect_from khong ton tai trong _nodes -> khong tao canh, khong
    # loi, node van duoc them binh thuong.
    assert probe_result["s1_nid3"] == "node_000003"
    assert probe_result["s1_after_nid3_edges_count"] == 1


# ---------------------------------------------------------------------------
# Section 2: add_step_below
# ---------------------------------------------------------------------------

def test_add_step_below_missing_parent_is_noop(probe_result):
    assert probe_result["s2_missing_parent_nodes_unchanged"] is True


def test_add_step_below_places_new_node_to_the_right_and_connects(probe_result):
    # parent (nid2) o (10, 20); node moi o (10 + _NODE_W(210) + 150, 20) = (370, 20).
    assert probe_result["s2_new_node_ids"] == ["node_000004"]
    assert probe_result["s2_new_node_pos"] == pytest.approx([370.0, 20.0])
    assert probe_result["s2_edge_nid2_to_new"] is True


# ---------------------------------------------------------------------------
# Section 3: _chain_tail
# ---------------------------------------------------------------------------

def test_chain_tail_picks_last_inserted_node_without_outgoing_edge(probe_result):
    # trang thai luc nay: nid1->nid2->new(node_000004); nid3 dung mot minh.
    # tails (theo thu tu chen) = [nid3, new] -> tails[-1] = new.
    assert probe_result["s3_tail_current_state"] == "node_000004"


def test_chain_tail_empty_canvas_returns_empty_string(probe_result):
    assert probe_result["s3_tail_empty_canvas"] == ""


def test_chain_tail_single_node_with_no_edges_is_itself(probe_result):
    assert probe_result["s3_tail_single_node_no_edges"] == "node_000005"


# ---------------------------------------------------------------------------
# Section 4: add_palette_step
# ---------------------------------------------------------------------------

def test_add_palette_step_returns_none_unlike_add_node(probe_result):
    # quirk: add_palette_step KHONG tra ve id node moi (khac add_node) - no
    # goi self.add_node(...) nhung khong return ket qua cua no.
    assert probe_result["s4_add_palette_step_return"] is None


def test_add_palette_step_uses_pos_directly_and_chains_from_tail(probe_result):
    assert probe_result["s4_tail_before"] == "node_000004"
    assert probe_result["s4_new_ids"] == ["node_000006"]
    assert probe_result["s4_pos"] == pytest.approx([500.0, 500.0])
    assert probe_result["s4_edge_from_tail_to_new"] is True


# ---------------------------------------------------------------------------
# Section 5: begin_connect / _finish_connect
# ---------------------------------------------------------------------------

def test_begin_connect_sets_pending_source(probe_result):
    assert probe_result["s5_connect_from_after_begin"] == "node_000007"


def test_finish_connect_self_target_quirk_resets_state_but_makes_no_edge(probe_result):
    # quirk: target_id == connect_from (tu noi minh vao minh) bi bo qua im
    # lang, KHONG tao canh, nhung _connect_from van duoc reset ve None.
    assert probe_result["s5_connect_from_after_self_finish"] is None
    assert probe_result["s5_edges_after_self_finish"] == 0


def test_finish_connect_valid_pair_creates_edge_and_resets_state(probe_result):
    assert probe_result["s5_connect_from_after_finish_ab"] is None
    assert probe_result["s5_edges_after_finish_ab"] == [["node_000007", "node_000008"]]


def test_finish_connect_with_no_active_connect_is_noop(probe_result):
    assert probe_result["s5_edges_after_finish_with_no_active_connect"] == 1


# ---------------------------------------------------------------------------
# Section 6: begin_port_drag / update_port_drag / finish_port_drag / _node_at
# ---------------------------------------------------------------------------

def test_begin_port_drag_adds_temp_edge_item_to_scene(probe_result):
    assert probe_result["s6_scene_items_before_drag"] == 2
    assert probe_result["s6_port_src_after_begin"] == "node_000009"
    assert probe_result["s6_temp_edge_in_scene_after_begin"] is True


def test_update_port_drag_sets_elbow_path_on_temp_edge(probe_result):
    # P o (0,0)->cong o (210,48); dich toi (200,100) khac y -> nhanh elbow
    # cua _ortho_path (10 element, khop voi test_co4e_canvas_geometry.py).
    assert probe_result["s6_temp_edge_path_elements_after_update"] == 10


def test_node_at_hits_node_under_point_and_none_when_empty(probe_result):
    assert probe_result["s6_node_at_hit_point"] == "node_000010"
    assert probe_result["s6_node_at_empty_point"] is None


def test_finish_port_drag_creates_edge_and_clears_temp_state(probe_result):
    assert probe_result["s6_port_src_after_finish"] is None
    assert probe_result["s6_temp_edge_after_finish"] is None
    assert probe_result["s6_edges_after_finish"] == [["node_000009", "node_000010"]]


def test_make_edge_dedups_same_source_target_pair(probe_result):
    # quirk: keo lai dung cap p->q lan hai khong tao canh trung.
    assert probe_result["s6_edges_after_duplicate_drag"] == 1


def test_finish_port_drag_over_empty_space_adds_no_edge_and_clears_state(probe_result):
    assert probe_result["s6_edges_after_finish_over_empty_space"] == 1
    assert probe_result["s6_port_src_after_empty_finish"] is None


# ---------------------------------------------------------------------------
# Section 7: delete_edge / delete_node / delete_selected
# ---------------------------------------------------------------------------

def test_delete_edge_removes_matching_item_and_emits_graph_changed(probe_result):
    assert probe_result["s7_initial_edges"] == [
        ["node_000011", "node_000012"],
        ["node_000012", "node_000013"],
        ["node_000013", "node_000014"],
    ]
    assert probe_result["s7_edges_after_delete_ab"] == [
        ["node_000012", "node_000013"],
        ["node_000013", "node_000014"],
    ]
    assert probe_result["s7_changed_after_delete_ab"] == 1


def test_delete_edge_called_again_on_already_removed_edge_still_emits(probe_result):
    # quirk: khong co "removed count" guard - goi lai voi Edge da bi xoa van
    # phat graph_changed, du khong con item nao khop de xoa.
    assert probe_result["s7_changed_after_delete_ab_again"] == 2
    assert probe_result["s7_edges_after_delete_ab_again"] == 2


def test_delete_node_missing_id_returns_early_without_emitting(probe_result):
    # quirk: khac delete_edge o tren - delete_node voi id khong ton tai return
    # SOM (truoc dong emit), nen KHONG phat graph_changed trong truong hop nay.
    assert probe_result["s7_delete_node_missing_returns_early"] is True
    assert probe_result["s7_changed_after_delete_missing_node"] == 2


def test_delete_selected_node_cascades_its_edges_before_edge_loop_runs(probe_result):
    # quirk: xoa node c4_ (id thu 3, "node_000013") keo theo xoa ca 2 canh noi
    # toi no (b->c va c->d) NGAY trong vong lap xoa node; vong lap xoa canh
    # (rieng, cho canh dang selected) sau do khong con thay 2 canh nay nua.
    assert probe_result["s7_nodes_after_delete_selected"] == [
        "node_000011", "node_000012", "node_000014",
    ]
    assert probe_result["s7_edges_after_delete_selected"] == []


# ---------------------------------------------------------------------------
# Section 8: _zoom_by / zoom_in / zoom_out / reset_zoom
# ---------------------------------------------------------------------------

def test_zoom_in_once_scales_by_1_15(probe_result):
    assert probe_result["s8_initial_m11"] == pytest.approx(1.0)
    assert probe_result["s8_initial_zoom_attr"] == pytest.approx(1.0)
    assert probe_result["s8_m11_after_1_zoom_in"] == pytest.approx(1.15)
    assert probe_result["s8_zoom_attr_after_1_zoom_in"] == pytest.approx(1.15)


def test_zoom_in_clamps_at_max_after_7_steps_from_1_0(probe_result):
    # quirk: tran _ZOOM_MAX=3.0 dat duoc sau dung 7 lan zoom_in() lien tiep tu
    # 1.0 (1 lan da tinh o test truoc + 6 lan trong series nay); 13 lan con
    # lai trong series 20 lan la no-op tuyet doi (gia tri dung yen o 3.0).
    expected = [
        1.3225, 1.520875, 1.749006, 2.011357, 2.313061, 2.66002, 3.0,
        3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0,
    ]
    assert probe_result["s8_m11_series_zoom_in_x20_more"] == pytest.approx(expected)
    assert probe_result["s8_zoom_attr_after_many_zoom_in"] == pytest.approx(3.0)


def test_zoom_in_at_cap_is_exact_noop(probe_result):
    assert probe_result["s8_m11_unchanged_when_already_at_cap"] is True


def test_reset_zoom_returns_to_1_0_regardless_of_prior_zoom(probe_result):
    assert probe_result["s8_m11_after_reset"] == pytest.approx(1.0)
    assert probe_result["s8_zoom_attr_after_reset"] == pytest.approx(1.0)


def test_zoom_out_clamps_at_min_after_8_steps_from_1_0(probe_result):
    # quirk: san _ZOOM_MIN=0.3 dat duoc sau dung 8 lan zoom_out() lien tiep tu
    # 1.0; 22 lan con lai trong series 30 lan la no-op (dung yen o 0.3).
    expected = [
        0.869565, 0.756144, 0.657516, 0.571753, 0.497177, 0.432328, 0.375937,
        0.326902, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3,
        0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3,
    ]
    assert probe_result["s8_m11_series_zoom_out_x30"] == pytest.approx(expected, abs=1e-5)
    assert probe_result["s8_zoom_attr_after_many_zoom_out"] == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# Section 9: relayout / relayout_if_vertical
# ---------------------------------------------------------------------------

def test_relayout_on_empty_canvas_is_a_safe_noop(probe_result):
    assert probe_result["s9_relayout_empty_ok"] is True


def test_relayout_if_vertical_reflows_a_stacked_chain_left_to_right(probe_result):
    # 3 node xep doc cung x=0 (chenh lech < _NODE_W=210) -> duoc coi la
    # "vertical" -> relayout() sap lai theo wave: cot 0/1/2 x = w*(210+110).
    assert probe_result["s9_vertical_before"] == {
        "node_000015": pytest.approx([0.0, 0.0]),
        "node_000016": pytest.approx([0.0, 150.0]),
        "node_000017": pytest.approx([0.0, 300.0]),
    }
    assert probe_result["s9_vertical_after_relayout_if_vertical"] == {
        "node_000015": pytest.approx([0.0, 0.0]),
        "node_000016": pytest.approx([320.0, 0.0]),
        "node_000017": pytest.approx([640.0, 0.0]),
    }


def test_relayout_if_vertical_leaves_already_horizontal_graph_untouched(probe_result):
    # chenh lech x (500) >= _NODE_W(210) -> khong duoc coi la "vertical" ->
    # relayout_if_vertical() khong dong gi toi vi tri da xep, du no khong
    # thang hang theo luoi wave.
    before = probe_result["s9_horizontal_before"]
    after = probe_result["s9_horizontal_after_relayout_if_vertical"]
    assert after == before
    assert after == {
        "node_000018": pytest.approx([0.0, 0.0]),
        "node_000019": pytest.approx([500.0, 50.0]),
    }


def test_relayout_if_vertical_with_fewer_than_2_nodes_is_noop(probe_result):
    assert probe_result["s9_single_node_after_relayout_if_vertical"] == pytest.approx(
        [0.0, 0.0]
    )


# ---------------------------------------------------------------------------
# Section 10: add_workflow
# ---------------------------------------------------------------------------

def test_add_workflow_first_batch_on_empty_canvas_keeps_original_positions(probe_result):
    # quirk: offset ngam ("60 neu self._nodes khac rong") kiem tra TRANG THAI
    # canvas LUC GOI, khong phai lien quan gi den tham so `at`. Canvas rong
    # luc goi -> offset (0,0) -> toa do y het nodes goc.
    ids = probe_result["s10_first_batch_ids"]
    assert len(ids) == 2
    positions = probe_result["s10_first_batch_positions"]
    assert positions[ids[0]] == pytest.approx([0.0, 0.0])
    assert positions[ids[1]] == pytest.approx([200.0, 0.0])
    assert probe_result["s10_first_batch_edges"] == [[ids[0], ids[1]]]


def test_add_workflow_second_batch_same_args_gets_implicit_60_60_offset(probe_result):
    # quirk: goi lai add_workflow VOI CUNG nodes/edges (khong at) nhung canvas
    # gio da co node tu lan truoc -> offset ngam (60, 60) duoc ap dung, id moi
    # hoan toan khac (fresh new_node_id moi lan).
    ids = probe_result["s10_second_batch_ids"]
    positions = probe_result["s10_second_batch_positions"]
    assert positions[ids[0]] == pytest.approx([60.0, 60.0])
    assert positions[ids[1]] == pytest.approx([260.0, 60.0])
    assert probe_result["s10_total_edges_after_second_call"] == 2


def test_add_workflow_with_explicit_at_overrides_implicit_offset(probe_result):
    ids = probe_result["s10_third_batch_ids"]
    positions = probe_result["s10_third_batch_positions"]
    assert positions[ids[0]] == pytest.approx([1000.0, 1000.0])
    assert positions[ids[1]] == pytest.approx([1200.0, 1000.0])


def test_add_workflow_silently_drops_edges_with_unknown_endpoint(probe_result):
    assert probe_result["s10_edges_with_unknown_target_dropped"] == 0
    assert probe_result["s10_nodes_still_added_despite_bad_edge"] == 2


# ---------------------------------------------------------------------------
# Section 11: dropEvent
# ---------------------------------------------------------------------------

def test_drop_event_step_payload_adds_node_with_dropped_label(probe_result):
    assert probe_result["s11_step_drop_nodes_count"] == 1
    assert probe_result["s11_step_drop_label"] == "Dropped Step"
    # quirk: view chua tung show()/resize khi dropEvent chay -> mapToScene tra
    # ve toa do phu thuoc kich thuoc viewport MAC DINH cua QGraphicsView chua
    # hien, KHONG phai (50, 60) nhu vi tri tha ban dau - dong dinh dung so da
    # chay ra duoc, khong suy doan.
    assert probe_result["s11_step_drop_pos"] == pytest.approx([-269.0, -179.0])


def test_drop_event_workflow_payload_merges_its_nodes(probe_result):
    assert probe_result["s11_workflow_drop_added_nodes"] == 1


def test_drop_event_empty_workflow_payload_is_a_silent_noop(probe_result):
    # quirk: workflow rong (wf.nodes == []) khong lam gi ca - `if wf.nodes:`
    # false nen add_workflow khong duoc goi, khong loi, khong node moi.
    assert probe_result["s11_empty_workflow_drop_is_noop"] is True


def test_drop_event_invalid_json_payload_is_a_silent_noop(probe_result):
    # quirk: except (ValueError, UnicodeDecodeError): return - khong nem loi
    # ra ngoai, khong e.acceptProposedAction() nao duoc goi trong nhanh nay.
    assert probe_result["s11_bad_json_drop_is_noop_no_crash"] is True


def test_drop_event_wrong_mime_format_falls_back_to_base_class_noop(probe_result):
    assert probe_result["s11_wrong_mime_format_is_noop_no_crash"] is True


# ---------------------------------------------------------------------------
# Lenh thu cong da dung de chot cac gia tri JSON o tren (quy trinh nguoc):
#
#   .venv/Scripts/python.exe -c "<noi dung _PROBE_SCRIPT>" <sandbox> <repo_parent>
#
# voi <sandbox> la mot thu muc rong duoc gan vao HOME/USERPROFILE TRUOC khi
# script import bat ky thu gi thuoc cowork_local, va <repo_parent> la thu muc
# cha cua repo (de "import cowork_local" hoat dong dung nhu conftest.py lam).
# ---------------------------------------------------------------------------
