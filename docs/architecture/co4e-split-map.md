# Bản đồ tách file Co4E (gộp từ 6 agent quét song song)

- Tổng số symbol quét được (thô, tính cả trùng): **367**
- Tổng số dòng trong bản đồ cuối cùng (sau gộp trùng): **363**
- Số nhóm ký hiệu bị quét trùng bởi 2 agent (đã gộp làm 1 dòng): 4 (Co4ECanvas.dropEvent, Co4ETab._co4e_routed_provider, Co4ETab._config_expanded_w, Co4ETab._reload_sidebar)
- Số ký hiệu có 2 định nghĩa thật ở 2 dòng khác nhau, giữ riêng và gắn cờ: 1 (Co4ETab.showEvent)
- EXPECTED (tools/check_co4e.py) có **27** phần tử; kết quả đối chiếu: OK — cả 27 xuất hiện đúng 1 lần, có target cụ thể
- Số note bắt đầu bằng `khac tai lieu:`: **0** (không có -> không có mục 'Chỗ thấy khác tài liệu' nào phát sinh từ tiêu chí này)

## Ghi chú về gộp trùng (5 ký hiệu bị 2 agent cùng quét thấy)

### `Co4ETab._config_expanded_w`
- dòng 275-275, target agent gốc đề xuất = `presentation/co4e/co4e_tab.py` — cùng lý do với _config_collapsed
- dòng 995-995, target agent gốc đề xuất = `presentation/co4e/co4e_tab.py` — gán trong nhánh collapse của _toggle_config; có thể đã khởi tạo trong __init__ (ngoài phạm vi đọc).
- **Quyết định gộp**: 1 dòng, target cuối = `presentation/co4e/co4e_tab.py`, dòng 275; 995

### `Co4ETab._reload_sidebar`
- dòng 689-700, target agent gốc đề xuất = `presentation/co4e/co4e_tab.py` — cắt ngang lát — cần agent gộp đối chiếu (method tiếp tục sau dòng 700); gọi co4e.list_workflows() (đọc đĩa) rồi dựng QListWidgetItem trực tiếp trong cùng hàm — trộn data-fetch và UI, nên tách phần đọc dữ liệu sang co4e_workflow_service.py
- dòng 689-722, target agent gốc đề xuất = `unsure` — cắt ngang lát — cần agent gộp đối chiếu (bắt đầu trước dòng 701). Gộp refresh cả agent_list và skill_list trong cùng 1 hàm — nên tách thành _refresh_agents_list (agent_list_panel.py) và _refresh_skills_list (skills_list_panel.py) như plan.md yêu cầu; gọi co4e.list_custom_agents() (đĩa) và skills_mod.skill_prefix_for (đĩa).
- **Quyết định gộp**: 1 dòng, target cuối = `presentation/co4e/co4e_tab.py`, dòng 689-722

### `Co4ETab.showEvent`
- dòng 973-975, target agent gốc đề xuất = `presentation/co4e/co4e_tab.py` — Qt override, gọi self._narrow_guard.attach() (đối tượng khởi tạo ngoài phạm vi đọc, <701).
- dòng 1806-1809, target agent gốc đề xuất = `presentation/co4e/co4e_tab.py` — override Qt lifecycle method của chính QWidget container nên phải ở lại co4e_tab.py; gọi self._refresh_runs() (thuộc co4e_run_control_widget.py) — điểm nối giữa container và run-control widget.
- **Quyết định**: đây là 2 định nghĩa method trùng tên thật sự tồn tại ở 2 vị trí khác nhau trong cùng class `Co4ETab` (khả năng cao là lỗi nguồn — định nghĩa sau đè định nghĩa trước, làm dòng logic ở định nghĩa trước thành dead code). Giữ nguyên 2 dòng riêng biệt trong bản đồ, KHÔNG gộp, và cần người quyết định giữ định nghĩa nào.

### `Co4ETab._co4e_routed_provider`
- dòng 1114-1114, target agent gốc đề xuất = `presentation/co4e/co4e_chat_view.py` — override provider cho lượt chat kế tiếp — dùng bởi _apply_co4e_routing (ngoài phạm vi đọc, >1400).
- dòng 1853-1853, target agent gốc đề xuất = `presentation/co4e/co4e_chat_view.py` — gán None lần đầu tại đây (trong _apply_co4e_routing); đọc bằng getattr(self, '_co4e_routed_provider', None) ở _run_chat_turn dòng ~1922 — gợi ý có thể không được init trong __init__. Trạng thái routing theo từng lượt chat, dùng chung giữa chat-view và _start_canvas_run/manager.start.
- **Quyết định gộp**: 1 dòng, target cuối = `presentation/co4e/co4e_chat_view.py`, dòng 1114; 1853

### `Co4ECanvas.dropEvent`
- dòng 683-700, target agent gốc đề xuất = `presentation/co4e/co4e_canvas_widget.py` — cắt ngang lát — cần agent gộp đối chiếu (thân try chưa đóng ở dòng 700, còn tiếp; xử lý JSON từ mimeData trong bộ nhớ, không phải file đĩa nên touches_disk_or_network=false)
- dòng 683-701, target agent gốc đề xuất = `presentation/co4e/co4e_canvas_widget.py` — cắt ngang lát — cần agent gộp đối chiếu. Method dropEvent bắt đầu ở dòng 683 (ngoài khoảng được giao 701-791), chỉ dòng 701 (e.acceptProposedAction()) nằm trong lát này; dòng 702 là dòng trống cuối file. File ui/co4e_canvas.py chỉ có 702 dòng — không có nội dung nào khác trong khoảng 702-791 vì đã hết file. Xử lý drop từ sidebar (kind=='workflow' → add_workflow, ngược lại → add_palette_step) — logic thao tác node/canvas nên khớp nhóm _add_node/_connect_nodes trong bảng plan.md dòng 623 dù plan.md không liệt kê rõ dropEvent.
- **Quyết định gộp**: 1 dòng, target cuối = `presentation/co4e/co4e_canvas_widget.py`, dòng 683-701

## Bảng đầy đủ

| symbol | dòng | file đích | lý do | có trong bảng cũ chưa | chỗ nào thấy bảng cũ sai |
|---|---|---|---|---|---|
| Co4ETab._flow_outputs | 245 | application/workflows/co4e_workflow_service.py | state per-flow outputs — ứng viên chuyển vào state machine thuần Python | chua/khong ro | - |
| Co4ETab._outputs_for | 475-478 | application/workflows/co4e_workflow_service.py | truy cập dict state per-flow outputs, thuần Python | chua/khong ro | - |
| Co4ETab._duplicate_selected_workflow | 1239-1246 | application/workflows/co4e_workflow_service.py | tương ứng _duplicate_flow() trong bảng plan.md dòng 616, nhưng tên hàm thực tế khác (_duplicate_selected_workflow). Gộp gọi service (co4e.duplicate_workflow, đĩa) với cập nhật UI (self._reload_sidebar(), self.status_message.emit) — cần tách; phần UI nên ở lại co4e_tab.py. | co | ate_flow() trong bảng plan.md dòng 616, nhưng tên hàm thực tế khác (_duplicate_selected_workflow). Gộp gọi service (co4e.duplicate_workflow, đĩa) |
| Co4ETab._rename_workflow | 1273-1289 | application/workflows/co4e_workflow_service.py | mở QInputDialog (cần Qt) rồi gọi co4e.save_workflow (đĩa), đồng bộ self._wf.name/self.name_edit nếu flow đang mở là flow bị đổi tên — gộp UI dialog + service + trạng thái chia sẻ self._wf trong 1 hàm, nên tách. | chua/khong ro | - |
| Co4ETab._delete_selected_workflow | 1291-1297 | application/workflows/co4e_workflow_service.py | tương ứng _delete_flow() trong bảng plan.md dòng 616; gọi co4e.delete_workflow (đĩa). | co | - |
| Co4ETab._save | 1304-1309 | application/workflows/co4e_workflow_service.py | gộp _sync_wf_from_canvas (đọc canvas UI), lưu đĩa (co4e.save_workflow), và cập nhật UI (_reload_sidebar, status_message) — cần tách phần service khỏi phần UI khi chuyển sang co4e_workflow_service.py. | chua/khong ro | - |
| Co4ETab._autosave | 1311-1314 | application/workflows/co4e_workflow_service.py | gọi self._sync_wf_from_canvas() (cần canvas) rồi co4e.get_workflow/save_workflow (đĩa). | chua/khong ro | - |
| Co4ETab._skill_map | 1376-1382 | application/workflows/co4e_workflow_service.py | chuẩn bị nội dung skill (skills_mod.skill_prefix_for, đọc đĩa) để đưa vào lúc chạy flow/chat — không có trong bảng plan.md, tự xếp theo chức năng (dùng lúc run/build system prompt, không phải UI danh sách skill). | co | ọc đĩa) để đưa vào lúc chạy flow/chat — không có trong bảng plan.md, tự xếp theo chức năng (dùng lúc run/build system prompt, không phải UI danh sá |
| Co4ETab.ag_new_btn | 550 | presentation/co4e/agent_list_panel.py | hiện định nghĩa trực tiếp trong Co4ETab._build_sidebar — ứng viên chuyển sang agent_list_panel.py tương tự cách skills đã tách | chua/khong ro | - |
| Co4ETab.agent_list | 558 | presentation/co4e/agent_list_panel.py | cùng lý do với ag_new_btn | chua/khong ro | - |
| Co4ETab.ag_edit_btn | 562 | presentation/co4e/agent_list_panel.py | cùng lý do với ag_new_btn | chua/khong ro | - |
| Co4ETab.ag_del_btn | 563 | presentation/co4e/agent_list_panel.py | cùng lý do với ag_new_btn | chua/khong ro | - |
| Co4ETab._new_agent | 1339-1340 | presentation/co4e/agent_list_panel.py | tương ứng _create_agent() trong bảng plan.md dòng 620 (tên hàm thực tế là _new_agent). | co | - |
| Co4ETab._edit_agent | 1342-1350 | presentation/co4e/agent_list_panel.py | khớp _edit_agent() dòng 620 plan.md; gọi co4e.list_custom_agents() (đĩa). | co | - |
| Co4ETab._edit_agent_dialog | 1352-1358 | presentation/co4e/agent_list_panel.py | mở Co4EAgentDialog rồi co4e.save_custom_agent (đĩa) và self._reload_sidebar() — trạng thái chia sẻ, liên quan tới cắt ngang lát ở _reload_sidebar. | chua/khong ro | - |
| Co4ETab._delete_agent | 1360-1367 | presentation/co4e/agent_list_panel.py | khớp _delete_agent() dòng 620 plan.md; gọi co4e.delete_custom_agent (đĩa). | co | - |
| _status_color | 43-50 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| _NodeItem | 59-210 | presentation/co4e/co4e_canvas_widget.py | class nội bộ gắn chặt với Co4ECanvas qua self.canvas backreference — nên đi cùng file với Co4ECanvas | chua/khong ro | - |
| _NodeItem.__init__ | 62-72 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| _NodeItem.node | 64 | presentation/co4e/co4e_canvas_widget.py | giữ tham chiếu domain Node — dữ liệu chia sẻ với core/co4e.py | chua/khong ro | - |
| _NodeItem.canvas | 65 | presentation/co4e/co4e_canvas_widget.py | backreference tới Co4ECanvas cha — mọi event của _NodeItem đều gọi ngược lên canvas (add_step_below, begin_connect, delete_node, các signal) — điểm khớp nối chặt nhất trong file | chua/khong ro | - |
| _NodeItem.status | 66 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| _NodeItem._porting | 67 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| _NodeItem.boundingRect | 74-76 | presentation/co4e/co4e_canvas_widget.py | trả QRectF như kiểu giá trị, logic thuần | chua/khong ro | - |
| _NodeItem._card_rect | 78-79 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| _NodeItem.paint | 81-139 | presentation/co4e/co4e_canvas_widget.py | vẽ toàn bộ card: nền, header stripe, label, badge role, preview instructions/sub-agents, footer model/skills, 2 port — gộp nhiều việc nhưng vẫn dưới 80 dòng nên chưa bắt buộc tách thêm | chua/khong ro | - |
| _NodeItem._in_out_port | 141-143 | presentation/co4e/co4e_canvas_widget.py | hình học thuần dùng QPointF như kiểu giá trị | chua/khong ro | - |
| _NodeItem.itemChange | 145-156 | presentation/co4e/co4e_canvas_widget.py | ghi self.node.x/y rồi gọi self.canvas._reposition_edges() và emit self.canvas.graph_changed/node_selected — chạm trạng thái chia sẻ của canvas cha | chua/khong ro | - |
| _NodeItem.hoverMoveEvent | 158-161 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| _NodeItem.mousePressEvent | 163-174 | presentation/co4e/co4e_canvas_widget.py | đọc/ghi self.canvas._connect_from, gọi canvas._finish_connect/begin_port_drag — trạng thái connect-mode chia sẻ với Co4ECanvas | chua/khong ro | - |
| _NodeItem.mouseMoveEvent | 176-181 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| _NodeItem.mouseReleaseEvent | 183-189 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| _NodeItem.mouseDoubleClickEvent | 191-193 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| _NodeItem.contextMenuEvent | 195-207 | presentation/co4e/co4e_canvas_widget.py | gọi canvas.add_step_below/begin_connect/delete_node — trạng thái/hành vi thuộc canvas cha | chua/khong ro | - |
| _NodeItem.center | 209-210 | presentation/co4e/co4e_canvas_widget.py | trả QPointF như kiểu giá trị | chua/khong ro | - |
| _EdgeItem | 213-286 | presentation/co4e/co4e_canvas_widget.py | class nội bộ gắn chặt với Co4ECanvas qua self.canvas backreference | chua/khong ro | - |
| _EdgeItem.__init__ | 214-225 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| _EdgeItem.edge | 216 | presentation/co4e/co4e_canvas_widget.py | tham chiếu domain Edge — chia sẻ với core/co4e.py | chua/khong ro | - |
| _EdgeItem.canvas | 217 | presentation/co4e/co4e_canvas_widget.py | backreference tới Co4ECanvas — contextMenuEvent gọi canvas.delete_edge | chua/khong ro | - |
| _EdgeItem._dst | 218 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| _EdgeItem._hover | 224 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| _EdgeItem._apply_pen | 227-235 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| _EdgeItem.update_path | 237-239 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| _EdgeItem.boundingRect | 241-242 | presentation/co4e/co4e_canvas_widget.py | gọi super().boundingRect() phụ thuộc trạng thái path sống của item | chua/khong ro | - |
| _EdgeItem.shape | 244-249 | presentation/co4e/co4e_canvas_widget.py | dùng QPainterPathStroker trên self.path() sống của item | chua/khong ro | - |
| _EdgeItem.hoverEnterEvent | 251-255 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| _EdgeItem.hoverLeaveEvent | 257-261 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| _EdgeItem.paint | 263-279 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| _EdgeItem.contextMenuEvent | 281-286 | presentation/co4e/co4e_canvas_widget.py | gọi self.canvas.delete_edge(self.edge) | chua/khong ro | - |
| Co4ECanvas | 289-700 | presentation/co4e/co4e_canvas_widget.py | cắt ngang lát — class tiếp tục sau dòng 700 (dropEvent chưa kết thúc, có thể còn method khác chưa đọc) — cần agent gộp đối chiếu với phần đọc dòng 701+ | chua/khong ro | - |
| Co4ECanvas.node_selected | 290 | presentation/co4e/co4e_canvas_widget.py | Signal được node_property_panel.py (và co4e_tab.py) nối vào để nạp node được chọn — điểm chia sẻ giữa canvas và property panel | chua/khong ro | - |
| Co4ECanvas.node_activated | 291 | presentation/co4e/co4e_canvas_widget.py | Signal double-click, có thể được co4e_tab.py nối để mở panel chỉnh sửa — cần kiểm nơi consume | chua/khong ro | - |
| Co4ECanvas.graph_changed | 292 | presentation/co4e/co4e_canvas_widget.py | Signal báo graph đổi (autosave) — nhiều khả năng được co4e_tab.py/co4e_workflow_service.py nối để lưu flow, trạng thái chia sẻ xuyên lớp application | chua/khong ro | - |
| Co4ECanvas.__init__ | 296-315 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas._scene | 299 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas._nodes | 305 | presentation/co4e/co4e_canvas_widget.py | dict id->_NodeItem — trạng thái trung tâm được đọc/ghi bởi gần như mọi method của Co4ECanvas (add/delete/relayout/zoom/status/route edges) | chua/khong ro | - |
| Co4ECanvas._edges | 306 | presentation/co4e/co4e_canvas_widget.py | list _EdgeItem — trạng thái trung tâm tương tự self._nodes | chua/khong ro | - |
| Co4ECanvas._connect_from | 307 | presentation/co4e/co4e_canvas_widget.py | trạng thái connect-mode, cũng được _NodeItem.mousePressEvent đọc/ghi qua self.canvas | chua/khong ro | - |
| Co4ECanvas._zoom | 308 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas._panning | 309 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas._pan_start | 310 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas._overlay | 311 | presentation/co4e/co4e_canvas_widget.py | widget zoom/fit overlay được co4e_tab.py hoặc co4e_canvas_widget.py truyền vào qua add_overlay() | chua/khong ro | - |
| Co4ECanvas._port_src | 313 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas._port_src_pt | 314 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas._temp_edge | 315 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.add_overlay | 318-323 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas._place_overlay | 325-330 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.resizeEvent | 332-334 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.scrollContentsBy | 336-341 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.showEvent | 343-345 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.load | 348-362 | presentation/co4e/co4e_canvas_widget.py | reset toàn bộ self._nodes/self._edges/self._connect_from/self._port_src/self._temp_edge — điểm nạp lại state từ flow, được co4e_tab.py hoặc co4e_workflow_service.py gọi khi mở flow | chua/khong ro | - |
| Co4ECanvas.nodes | 364-365 | presentation/co4e/co4e_canvas_widget.py | chỉ đọc .node từ self._nodes, không gọi API Qt trực tiếp | chua/khong ro | - |
| Co4ECanvas.edges | 367-368 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.add_node | 371-382 | presentation/co4e/co4e_canvas_widget.py | ghi self._nodes, scene.addItem, emit graph_changed/node_selected — trạng thái chia sẻ với property panel qua node_selected | chua/khong ro | - |
| Co4ECanvas.add_step_below | 384-390 | presentation/co4e/co4e_canvas_widget.py | orchestration thuần, ủy quyền cho add_node (bản thân không gọi trực tiếp API Qt) | chua/khong ro | - |
| Co4ECanvas._chain_tail | 392-396 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.add_palette_step | 398-400 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.begin_connect | 402-403 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas._finish_connect | 405-409 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.begin_port_drag | 412-419 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.update_port_drag | 421-424 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.finish_port_drag | 426-435 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas._node_at | 437-441 | presentation/co4e/co4e_canvas_widget.py | dùng self._scene.items(scene_pt) — cần scene đang sống | chua/khong ro | - |
| Co4ECanvas._make_edge | 443-451 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas._add_edge_item | 453-456 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.delete_edge | 458-463 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.delete_node | 465-475 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.delete_selected | 477-481 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas._zoom_by | 484-495 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.zoom_in | 497-498 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.zoom_out | 500-501 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.reset_zoom | 503-505 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.wheelEvent | 507-519 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.mousePressEvent | 522-529 | presentation/co4e/co4e_canvas_widget.py | trùng tên với _NodeItem.mousePressEvent nhưng là override của Co4ECanvas (pan chuột giữa) — đừng nhầm khi gộp map | chua/khong ro | - |
| Co4ECanvas.mouseMoveEvent | 531-540 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.mouseReleaseEvent | 542-548 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.fit_view | 550-558 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.relayout | 560-578 | presentation/co4e/co4e_canvas_widget.py | phần tính waves/cols (compute_waves, defaultdict) là logic thuần, phần item.setPos() cần scene sống — có thể tách hàm tính toạ độ ra khỏi phần apply nếu muốn test thuần Python | chua/khong ro | - |
| Co4ECanvas.relayout_if_vertical | 580-589 | presentation/co4e/co4e_canvas_widget.py | bản thân chỉ ra quyết định thuần dựa trên node.x, việc chạm Qt nằm trong relayout() được gọi | chua/khong ro | - |
| Co4ECanvas.add_workflow | 591-610 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.update_node_status | 612-616 | presentation/co4e/co4e_canvas_widget.py | được co4e_run_control_widget.py gọi khi step chạy/xong/lỗi — điểm nối giữa canvas và run control | chua/khong ro | - |
| Co4ECanvas.reset_statuses | 618-621 | presentation/co4e/co4e_canvas_widget.py | được co4e_run_control_widget.py gọi khi bắt đầu run mới | chua/khong ro | - |
| Co4ECanvas.refresh_node | 623-626 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas._node_rects | 628-638 | presentation/co4e/co4e_canvas_widget.py | dựng QRectF như kiểu giá trị từ item.pos() — logic hình học thuần | chua/khong ro | - |
| Co4ECanvas._reposition_edges | 640-649 | presentation/co4e/co4e_canvas_widget.py | gọi e.update_path (setPath) trên item sống, dùng hàm định tuyến _route từ canvas_geometry.py | chua/khong ro | - |
| Co4ECanvas.keyPressEvent | 652-669 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.dragEnterEvent | 671-675 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.dragMoveEvent | 677-681 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ECanvas.dropEvent | 683-701 | presentation/co4e/co4e_canvas_widget.py | [GỘP 2 lượt quét trùng ký hiệu] (dòng 683-700, target gốc=presentation/co4e/co4e_canvas_widget.py) cắt ngang lát — cần agent gộp đối chiếu (thân try chưa đóng ở dòng 700, còn tiếp; xử lý JSON từ mimeData trong bộ nhớ, không phải file đĩa nên touches_disk_or_network=false) \|\| (dòng 683-701, target gốc=presentation/co4e/co4e_canvas_widget.py) cắt ngang lát — cần agent gộp đối chiếu. Method dropEvent bắt đầu ở dòng 683 (ngoài khoảng được giao 701-791), chỉ dòng 701 (e.acceptProposedAction()) nằm trong lát này; dòng 702 là dòng trống cuối file. File ui/co4e_canvas.py chỉ có 702 dòng — không có nội dung nào khác trong khoảng 702-791 vì đã hết file. Xử lý drop từ sidebar (kind=='workflow' → add_workflow, ngược lại → add_palette_step) — logic thao tác node/canvas nên khớp nhóm _add_node/_connect_nodes trong bảng plan.md dòng 623 dù plan.md không liệt kê rõ dropEvent. | co | nnect_nodes trong bảng plan.md dòng 623 dù plan.md không liệt kê rõ dropEvent. |
| Co4ETab.canvas | 856 | presentation/co4e/co4e_canvas_widget.py | TRẠNG THÁI CHIA SẺ lớn nhất trong file — self.canvas được đọc/ghi ở gần như mọi nhóm chức năng khác (sync_wf_from_canvas, apply_workflow, node selection, run, add_blank_step...). | chua/khong ro | - |
| Co4ETab._build_canvas_overlay | 1041-1062 | presentation/co4e/co4e_canvas_widget.py | dựng nút zoom/fit gắn vào self.canvas.add_overlay(bar); các slot gọi thẳng self.canvas.zoom_in/zoom_out/fit_view (thuộc nhóm 3.2.2.21-22 trong plan.md → co4e_canvas_widget.py). Có thể tranh cãi nên giữ ở co4e_tab.py (được gọi từ _build_center) — ghi lại để người soát quyết. | co | - |
| Co4ETab.zoom_in_btn | 1054 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.zoom_out_btn | 1055 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.fit_btn | 1056 | presentation/co4e/co4e_canvas_widget.py | (không có ghi chú) | chua/khong ro | - |
| _skill_names | 61-65 | presentation/co4e/co4e_chat_view.py | gọi skills_mod.list_skills()/builtin_skills() (đọc đĩa); dùng cho autocomplete /skill: trong _ChatInput — cũng liên quan skills_list_panel.py vì cùng nguồn dữ liệu | chua/khong ro | - |
| _agent_names | 68-71 | presentation/co4e/co4e_chat_view.py | gọi co4e.list_custom_agents() (đọc đĩa); dùng cho autocomplete /agent: trong _ChatInput — cũng liên quan agent_list_panel.py vì cùng nguồn dữ liệu | chua/khong ro | - |
| _directive_token | 122-134 | presentation/co4e/co4e_chat_view.py | logic regex thuần Python, test được không cần Qt | chua/khong ro | - |
| _ChatInput | 137-226 | presentation/co4e/co4e_chat_view.py | khai báo 'submit = Signal()' ở dòng 141 là thuộc tính lớp (không phải self.) | chua/khong ro | - |
| _ChatInput.__init__ | 143-151 | presentation/co4e/co4e_chat_view.py | (không có ghi chú) | chua/khong ro | - |
| _ChatInput._popup | 145 | presentation/co4e/co4e_chat_view.py | QListWidget popup autocomplete | chua/khong ro | - |
| _ChatInput._maybe_popup | 153-178 | presentation/co4e/co4e_chat_view.py | (không có ghi chú) | chua/khong ro | - |
| _ChatInput._add_row | 180-184 | presentation/co4e/co4e_chat_view.py | (không có ghi chú) | chua/khong ro | - |
| _ChatInput._accept | 186-199 | presentation/co4e/co4e_chat_view.py | (không có ghi chú) | chua/khong ro | - |
| _ChatInput.focusOutEvent | 201-204 | presentation/co4e/co4e_chat_view.py | (không có ghi chú) | chua/khong ro | - |
| _ChatInput.keyPressEvent | 206-226 | presentation/co4e/co4e_chat_view.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._chat_worker | 236 | presentation/co4e/co4e_chat_view.py | AgentWorker của chat, hiện giữ trên Co4ETab | chua/khong ro | - |
| Co4ETab._build_chat | 1064-1127 | presentation/co4e/co4e_chat_view.py | dài ~63 dòng, gộp: header 'Messages' + toggle, chat_stack (QStackedWidget chứa 1 ChatView/flow), input row + usage label + composer + routing toggle. Tạo self._flow_logs (Dict[str, ChatView]) — TRẠNG THÁI CHIA SẺ dùng bởi _ensure_flow_log/_active_log/chat_log/_apply_workflow (self._wf) — điểm dễ vỡ nhất khi tách file chat ra khỏi co4e_tab.py. | chua/khong ro | - |
| Co4ETab._chat_widget | 1066 | presentation/co4e/co4e_chat_view.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._mhdr | 1072 | presentation/co4e/co4e_chat_view.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.msgs_icon | 1074 | presentation/co4e/co4e_chat_view.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.msgs_title | 1075 | presentation/co4e/co4e_chat_view.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.chat_toggle_btn | 1076 | presentation/co4e/co4e_chat_view.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.chat_stack | 1091 | presentation/co4e/co4e_chat_view.py | chuyển self.center_stack tương tự — dùng chung với self.center_stack (co4e_tab.py). | chua/khong ro | - |
| Co4ETab._flow_logs | 1092 | presentation/co4e/co4e_chat_view.py | Dict[str, ChatView] keyed theo workflow id — TRẠNG THÁI CHIA SẺ chính của toàn bộ logic chat theo-flow; đọc/ghi bởi _ensure_flow_log, _active_log, chat_log, _apply_workflow, và các hàm chat khác ngoài phạm vi đọc (>1400). | chua/khong ro | - |
| Co4ETab.chat_input_row | 1094 | presentation/co4e/co4e_chat_view.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._usage_total_lbl | 1099 | presentation/co4e/co4e_chat_view.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.chat_input | 1105 | presentation/co4e/co4e_chat_view.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.chat_send_btn | 1108 | presentation/co4e/co4e_chat_view.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.co4e_routing_toggle | 1113 | presentation/co4e/co4e_chat_view.py | RoutingToggle(self.ctx, 'co4e') — self.ctx là trạng thái chia sẻ của cả Co4ETab (khởi tạo ngoài phạm vi đọc). | chua/khong ro | - |
| Co4ETab._co4e_routed_provider | 1114; 1853 | presentation/co4e/co4e_chat_view.py | [GỘP 2 lượt quét trùng ký hiệu] (dòng 1114-1114, target gốc=presentation/co4e/co4e_chat_view.py) override provider cho lượt chat kế tiếp — dùng bởi _apply_co4e_routing (ngoài phạm vi đọc, >1400). \|\| (dòng 1853-1853, target gốc=presentation/co4e/co4e_chat_view.py) gán None lần đầu tại đây (trong _apply_co4e_routing); đọc bằng getattr(self, '_co4e_routed_provider', None) ở _run_chat_turn dòng ~1922 — gợi ý có thể không được init trong __init__. Trạng thái routing theo từng lượt chat, dùng chung giữa chat-view và _start_canvas_run/manager.start. | chua/khong ro | [GỘP 2 lượt quét trùng ký hiệu] (dòng 1114-1114, target gốc=presentation/co4e/co4e_chat_view.py) overr |
| Co4ETab._vsplit_sizes | 1121 | presentation/co4e/co4e_chat_view.py | dùng bởi _toggle_messages để restore kích thước splitter — chia sẻ với self._vsplit (co4e_tab.py). | chua/khong ro | - |
| Co4ETab._msgs_collapsed | 1122 | presentation/co4e/co4e_chat_view.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._toggle_messages | 1129-1161 | presentation/co4e/co4e_chat_view.py | thao tác self._vsplit (tạo ở co4e_tab.py/_build_center) — trạng thái chia sẻ giữa co4e_chat_view.py và co4e_tab.py. | chua/khong ro | - |
| Co4ETab._ensure_flow_log | 1164-1173 | presentation/co4e/co4e_chat_view.py | đọc/ghi self._flow_logs — trạng thái chia sẻ chính của chat theo-flow. | chua/khong ro | - |
| Co4ETab._active_log | 1175-1177 | presentation/co4e/co4e_chat_view.py | đọc self._wf — trạng thái chia sẻ với toàn bộ Co4ETab (canvas, sidebar, save/autosave, run control). | chua/khong ro | - |
| Co4ETab.chat_log | 1180-1183 | presentation/co4e/co4e_chat_view.py | @property, chỉ đọc, uỷ nhiệm cho _active_log(). | chua/khong ro | - |
| Co4ETab._plan_bubble | 1186-1187 | presentation/co4e/co4e_chat_view.py | @property getter, đọc self._active_log()._co4e_plan_bubble (thuộc tính gắn thêm vào từng instance ChatView). | chua/khong ro | - |
| Co4ETab._plan_bubble (setter) | 1189-1191 | presentation/co4e/co4e_chat_view.py | @_plan_bubble.setter, ghi self._active_log()._co4e_plan_bubble. | chua/khong ro | - |
| Co4ETab._chat_send | 1820-1846 | presentation/co4e/co4e_chat_view.py | self.chat_input.clear(), self._append_chat — thao tác widget; điều phối /agent /skill directive rồi gọi self._run_chat_turn (network qua provider, không trực tiếp trong hàm này) | chua/khong ro | - |
| Co4ETab._apply_co4e_routing | 1848-1883 | presentation/co4e/co4e_chat_view.py | gọi confirm_switch (dialog Qt) khi mode=='manual' và self._append_chat khi có switch — cần widget sống. Gán self._co4e_routed_provider (xem attribute riêng). | chua/khong ro | - |
| Co4ETab._extract_agent_directive | 1885-1891 | presentation/co4e/co4e_chat_view.py | regex thuần Python | chua/khong ro | - |
| Co4ETab._resolve_agent | 1893-1901 | presentation/co4e/co4e_chat_view.py | tra cứu BUILTIN_AGENTS và co4e.list_custom_agents() (bộ nhớ/đĩa tùy triển khai list_custom_agents, không rõ trong khoảng đọc) — cross-reference với agent_list_panel.py (nguồn danh sách custom agent) | chua/khong ro | - |
| Co4ETab._run_chat_turn | 1903-1974 | presentation/co4e/co4e_chat_view.py | 72 dòng, gộp: chuẩn bị prompt, tạo bubble stream, định nghĩa 4 closures nội bộ (job/on_event/done/failed) và khởi worker nền — nên tách các closures ra thành hàm riêng nếu dễ đọc hơn. Closure job() gọi run_cowork(provider,...) — network/AI call thật sự. Đọc/ghi self._chat_worker, self._co4e_routed_provider, self.chat_send_btn, self._wf; set log._co4e_plan_bubble=None (thuộc log là ChatView, không phải self). | chua/khong ro | - |
| Co4ETab._run_chat_turn.job | 1917-1946 | presentation/co4e/co4e_chat_view.py | closure nội bộ của _run_chat_turn, chạy trong AgentWorker (thread nền); gọi run_cowork(provider,...) — network/AI call thật; dùng usage_tracker (đọc/ghi trạng thái tích lũy usage) | chua/khong ro | - |
| Co4ETab._run_chat_turn.on_event | 1948-1954 | presentation/co4e/co4e_chat_view.py | closure nội bộ, cập nhật assistant.set_markdown và log.scroll_to_bottom (widget) | chua/khong ro | - |
| Co4ETab._run_chat_turn.done | 1956-1962 | presentation/co4e/co4e_chat_view.py | closure nội bộ, gán self._chat_worker = None, thao tác widget assistant/log | chua/khong ro | - |
| Co4ETab._run_chat_turn.failed | 1964-1967 | presentation/co4e/co4e_chat_view.py | closure nội bộ, gán self._chat_worker = None, gọi self._append_chat lỗi | chua/khong ro | - |
| Co4ETab._append_chat | 1976-1991 | presentation/co4e/co4e_chat_view.py | nhận tham số log tùy chọn, mặc định self.chat_log — dùng bởi rất nhiều method ở cả run-control (qua tham số log truyền vào) và chat-view; điểm nối giữa hai nhóm. | chua/khong ro | - |
| Co4ETab._fmt_usage | 1994-2001 | presentation/co4e/co4e_chat_view.py | format chuỗi thuần, đọc self.ctx.config.data — không chạm widget | chua/khong ro | - |
| Co4ETab._apply_usage | 2003-2020 | presentation/co4e/co4e_chat_view.py | bub.add_usage(...) thao tác widget bubble; ghi self._flow_usage[wf_id] — trạng thái tổng usage theo flow, dùng chung với _refresh_usage_total | chua/khong ro | - |
| Co4ETab._refresh_usage_total | 2022-2037 | presentation/co4e/co4e_chat_view.py | self._usage_total_lbl.setText — đọc self._wf, self._flow_usage | chua/khong ro | - |
| Co4ETab._append_diff | 2039-2043 | presentation/co4e/co4e_chat_view.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._append_plan | 2045-2056 | presentation/co4e/co4e_chat_view.py | đọc/ghi log._co4e_plan_bubble (thuộc tính động trên đối tượng log/ChatView, không phải self) | chua/khong ro | - |
| _html_escape | 2082-2083 | presentation/co4e/co4e_chat_view.py | hàm module-level (ngoài class Co4ETab), escape HTML thuần, dùng cho hiển thị chat | chua/khong ro | - |
| _PLAN_GLYPH | 45-46 | presentation/co4e/co4e_run_control_widget.py | module-level dict glyph trạng thái dùng bởi _fmt_plan | chua/khong ro | - |
| _fmt_plan | 49-58 | presentation/co4e/co4e_run_control_widget.py | helper thuần Python dùng bởi _render_plan() | chua/khong ro | - |
| Co4ETab.manager | 238 | presentation/co4e/co4e_run_control_widget.py | Co4ERunManager — lõi run control, trạng thái chia sẻ với canvas (node status) và chat view (run_logs) | chua/khong ro | - |
| Co4ETab._flow_runs | 243 | presentation/co4e/co4e_run_control_widget.py | map wf_id->run id, chia sẻ với _open_flow/_close_flow_tab (co4e_tab.py) và canvas | chua/khong ro | - |
| Co4ETab._run_logs | 244 | presentation/co4e/co4e_run_control_widget.py | map run_id->ChatView, chia sẻ với co4e_chat_view.py | chua/khong ro | - |
| Co4ETab._flow_usage | 248 | presentation/co4e/co4e_run_control_widget.py | usage token/cost theo flow, hiển thị ở Messages header | chua/khong ro | - |
| Co4ETab._manual_active | 252 | presentation/co4e/co4e_run_control_widget.py | chia sẻ với _close_flow_tab (co4e_tab.py) — set lại self.run_btn khi đóng tab | chua/khong ro | - |
| Co4ETab._manual_order | 253 | presentation/co4e/co4e_run_control_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._manual_idx | 254 | presentation/co4e/co4e_run_control_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._cur_run_id | 460-473 | presentation/co4e/co4e_run_control_widget.py | logic thuần Python, không gọi Qt trực tiếp | chua/khong ro | - |
| Co4ETab._update_run_btn | 480-482 | presentation/co4e/co4e_run_control_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.runs_more_btn | 586 | presentation/co4e/co4e_run_control_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.runs_side_list | 594 | presentation/co4e/co4e_run_control_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._SIDE_RUNS | 605 | presentation/co4e/co4e_run_control_widget.py | class-level constant, không phải self. | chua/khong ro | - |
| Co4ETab._refresh_side_runs | 607-619 | presentation/co4e/co4e_run_control_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._on_side_run_clicked | 621-629 | presentation/co4e/co4e_run_control_widget.py | chạm self.runs_table (định nghĩa ngoài khoảng đọc — thuộc trang Flow Status) | chua/khong ro | - |
| Co4ETab.mode_combo | 828 | presentation/co4e/co4e_run_control_widget.py | combo chọn run mode auto/plan/manual — thuộc nhóm _set_run_mode() trong plan.md dù được dựng bên trong _build_center (co4e_tab.py); ranh giới tách file ở đây dễ vỡ. | co | - |
| Co4ETab.run_btn | 833 | presentation/co4e/co4e_run_control_widget.py | nút Run — tương tự mode_combo, dựng trong _build_center nhưng thuộc nhóm run control; cũng bị _update_run_btn (<701), _on_run_clicked, _on_mode_changed đọc/ghi text. | chua/khong ro | - |
| Co4ETab.runs_btn | 840 | presentation/co4e/co4e_run_control_widget.py | toggle chuyển sang trang Runs (self.center_stack) — chia sẻ state center_stack với co4e_tab.py. | chua/khong ro | - |
| Co4ETab._build_runs_page | 873-932 | presentation/co4e/co4e_run_control_widget.py | dựng trang bảng Runs (theo dõi mọi run của mọi flow) — dùng self.manager (Co4ERunManager, sẽ thay bằng co4e_workflow_service) — trạng thái chia sẻ. | chua/khong ro | - |
| Co4ETab.runs_back_btn | 882 | presentation/co4e/co4e_run_control_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.runs_title | 887 | presentation/co4e/co4e_run_control_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.ws_folder_btn | 892 | presentation/co4e/co4e_run_control_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.run_stop_btn | 900 | presentation/co4e/co4e_run_control_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.run_rename_btn | 905 | presentation/co4e/co4e_run_control_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.run_del_btn | 909 | presentation/co4e/co4e_run_control_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.run_clear_btn | 913 | presentation/co4e/co4e_run_control_widget.py | clicked gọi self.manager.clear_finished() — trạng thái chia sẻ self.manager. | chua/khong ro | - |
| Co4ETab.runs_table | 921 | presentation/co4e/co4e_run_control_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._current_mode | 1384-1385 | presentation/co4e/co4e_run_control_widget.py | đọc self.mode_combo — khớp nhóm _set_run_mode() dòng 624 plan.md. | co | - |
| Co4ETab._on_mode_changed | 1387-1393 | presentation/co4e/co4e_run_control_widget.py | reset self._manual_active/_manual_order/_manual_idx (trạng thái chia sẻ với luồng manual step _manual_step/_manual_run_or_advance, ngoài phạm vi đọc >1400) và gọi self._cur_run_id() (chia sẻ với self.manager). | chua/khong ro | - |
| Co4ETab._on_run_clicked | 1395-1400 | presentation/co4e/co4e_run_control_widget.py | cắt ngang lát — cần agent gộp đối chiếu (tiếp tục sau dòng 1400). Dùng self.manager.stop() và self._cur_run_id() — trạng thái chia sẻ với co4e_workflow_service tương lai. Khớp nhóm _run_flow()/_stop_flow() dòng 618 plan.md (dù đó là bản service, đây là UI handler nút Run). | co | - |
| Co4ETab.<method truoc dong 1401, ten chua xac dinh - co the la _on_run_clicked> | 1401-1405 | presentation/co4e/co4e_run_control_widget.py | cắt ngang lát — cần agent gộp đối chiếu. Định nghĩa (def ...) nằm ở lát trước dòng 1401 nên tên chính xác không xác định được; đoạn thấy được chỉ dispatch theo self._current_mode() sang _manual_run_or_advance() hoặc _start_canvas_run() — thuộc nhóm Run/mode. | chua/khong ro | (def ...) nằm ở lát trước dòng 1401 nên tên chính xác không xác định được; đoạn thấy được chỉ dispatch theo self._current_mode() sang _manual_run_or |
| Co4ETab._start_canvas_run | 1407-1424 | presentation/co4e/co4e_run_control_widget.py | gọi self.manager.start(...) — spawn chạy flow (dẫn tới gọi provider AI ở tầng khác); đọc/ghi self._wf, self._flow_runs, self._flow_runs[wf_id], self._run_logs, self.chat_log — trạng thái chia sẻ giữa run-control và chat-view. self.manager (Co4ERunManager) nên đổi sang application/workflows/co4e_workflow_service.py theo mapping. | chua/khong ro | - |
| Co4ETab._run_single | 1426-1431 | presentation/co4e/co4e_run_control_widget.py | wrapper mỏng gọi _start_canvas_run; đọc self._wf.id | chua/khong ro | - |
| Co4ETab._run_from | 1433-1437 | presentation/co4e/co4e_run_control_widget.py | wrapper mỏng gọi _start_canvas_run với self._downstream(node_id) | chua/khong ro | - |
| Co4ETab._downstream | 1439-1450 | presentation/co4e/co4e_run_control_widget.py | thuật toán BFS thuần Python, chỉ đọc self.canvas.edges() làm input — test được với danh sách edge giả lập, không cần canvas thật | chua/khong ro | - |
| Co4ETab._manual_run_or_advance | 1453-1466 | presentation/co4e/co4e_run_control_widget.py | gọi self.canvas.reset_statuses() và self._append_chat (self._append_chat thuộc nhóm chat-view) — cắt ngang giữa run-control và chat-view. Đọc/ghi self._manual_active, self._manual_order, self._manual_idx, self._wf, self._outputs_for(...), self._plan_bubble — trạng thái run thuần túy chia sẻ với _manual_step. | chua/khong ro | - |
| Co4ETab._manual_step | 1468-1484 | presentation/co4e/co4e_run_control_widget.py | gọi self.manager.start(...) (network/AI qua provider) và self.run_btn.setText, self._append_chat (chat-view); đọc/ghi self._manual_idx, self._manual_order, self._wf, self._flow_runs, self._run_logs, self.chat_log — trạng thái chia sẻ rộng giữa run-control và chat-view. | chua/khong ro | - |
| Co4ETab._topo_order | 1486-1491 | presentation/co4e/co4e_run_control_widget.py | đọc self.canvas.nodes()/edges() làm dữ liệu đầu vào, logic tính toán thuần túy (co4e.compute_waves) — test được với dữ liệu giả | chua/khong ro | - |
| Co4ETab._on_manager_event | 1494-1550 | presentation/co4e/co4e_run_control_widget.py | method dài (57 dòng), gộp nhiều việc không liên quan: định tuyến sự kiện chạy theo từng flow (routing run_id -> log), cập nhật trạng thái node trên canvas, hiển thị bubble chat (assistant/diff/plan/tool-failed — thuộc co4e_chat_view.py), xử lý hoàn tất run (run_done/run_error), hiển thị popup thông báo, cập nhật status bar. Nên tách phần hiển thị chat (self._append_chat/_append_diff/_append_plan) sang co4e_chat_view.py, giữ phần routing/flow-completion ở co4e_run_control_widget.py. Đọc/ghi self._flow_runs, self._run_logs, self.chat_log, self.canvas, self._wf, self._outputs_for(...), self._manual_active, self._manual_idx — trạng thái chia sẻ rất rộng, điểm dễ vỡ nhất khi tách file. | chua/khong ro | - |
| Co4ETab._notify_run_finished | 1552-1573 | presentation/co4e/co4e_run_control_widget.py | tạo QMessageBox không chặn; khởi tạo lazy self._run_popups (xem attribute riêng) | chua/khong ro | - |
| Co4ETab._run_popups | 1560-1561 | presentation/co4e/co4e_run_control_widget.py | khởi tạo lazy (list rỗng) trong _notify_run_finished qua hasattr guard — không init trong __init__; giữ ref các QMessageBox non-blocking khỏi bị GC | chua/khong ro | - |
| Co4ETab._refresh_runs | 1575-1616 | presentation/co4e/co4e_run_control_widget.py | render bảng runs_table + gọi self._refresh_side_runs() (sidebar) + cập nhật self.flow_bar.setTabText và self._sections['co4e.runs_tab'] — self._sections và self.flow_bar là trạng thái chia sẻ với co4e_tab.py (container/sidebar). | chua/khong ro | - |
| Co4ETab._stop_selected_run | 1618-1624 | presentation/co4e/co4e_run_control_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._delete_selected_run | 1626-1639 | presentation/co4e/co4e_run_control_widget.py | đọc/ghi self._flow_runs, self._run_logs — trạng thái chia sẻ với _on_manager_event/_start_canvas_run | chua/khong ro | - |
| Co4ETab._runs_context_menu | 1641-1655 | presentation/co4e/co4e_run_control_widget.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._open_run_output_folder | 1704-1715 | presentation/co4e/co4e_run_control_widget.py | path.mkdir + open_location (spawn process); dùng bởi _runs_context_menu 'Open output' | chua/khong ro | - |
| Co4ETab._rename_selected_run | 1717-1748 | presentation/co4e/co4e_run_control_widget.py | gọi co4e.save_workflow(wf) (ghi đĩa); đọc/ghi self._flows (list flow của sidebar/tab-bar), self.flow_bar, self.name_edit, self._wf — chạm nhiều trạng thái chia sẻ với co4e_tab.py container (tab bar + name edit thuộc header, không rõ nằm ở panel nào) — rủi ro vỡ cao khi tách. | chua/khong ro | - |
| Co4ETab._run_selected_in_background | 1750-1760 | presentation/co4e/co4e_run_control_widget.py | gọi self.manager.start(...) (network/AI) và self._refresh_side_runs() (widget) | chua/khong ro | - |
| Co4ETab._wf_by_id | 1762-1770 | presentation/co4e/co4e_run_control_widget.py | gọi co4e.get_workflow(wf_id) (đọc đĩa) và self._sync_wf_from_canvas() (không nằm trong khoảng đọc) — đọc self._wf; dùng chung bởi _rerun_run_item/_open_run_from_table (Runs tab) và có thể cả co4e_tab.py container | chua/khong ro | - |
| Co4ETab._rerun_run_item | 1772-1783 | presentation/co4e/co4e_run_control_widget.py | gọi self.manager.start(...) (network/AI) | chua/khong ro | - |
| Co4ETab._open_run_from_table | 1785-1804 | presentation/co4e/co4e_run_control_widget.py | gọi self._open_flow(wf) (không nằm trong khoảng đọc, theo plan.md thuộc co4e_tab.py) và self.canvas.update_node_status — nối Runs tab với việc mở flow trên canvas, điểm khớp nối giữa run-control và container/canvas. | co | - |
| _qcolor | 2086-2088 | presentation/co4e/co4e_run_control_widget.py | hàm module-level (ngoài class Co4ETab), tạo QColor từ hex string — dùng kiểu giá trị QColor, không cần QApplication sống; dùng trong _refresh_runs để tô màu status | chua/khong ro | - |
| _EqualTabBar | 74-94 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| _EqualTabBar._GAP | 80 | presentation/co4e/co4e_tab.py | class-level constant, không phải self. | chua/khong ro | - |
| _EqualTabBar.tabSizeHint | 82-90 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| _EqualTabBar.resizeEvent | 92-94 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab | 229-700 | presentation/co4e/co4e_tab.py | Lớp kéo dài quá dòng 700 (cắt ngang lát) — chỉ ghi nhận phần 229-700; 'status_message = Signal(str)' dòng 230 là thuộc tính lớp, không phải self. | chua/khong ro | - |
| Co4ETab.__init__ | 232-304 | presentation/co4e/co4e_tab.py | method 73 dòng, gộp: khởi state run/flow, dựng splitter 3 cột (sidebar/center/config), wiring canvas & config panel, gọi _reload_sidebar (đọc đĩa qua co4e.list_workflows) và _open_flow; chạm rất nhiều thuộc tính chia sẻ: self._wf, self._flows, self.manager, self._flow_runs, self._run_logs, self._flow_outputs, self._flow_usage, self.config, self.canvas (gán ở _build_center ngoài khoảng đọc này) | chua/khong ro | - |
| Co4ETab.ctx | 234 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._wf | 235 | presentation/co4e/co4e_tab.py | trạng thái chia sẻ — đọc/ghi bởi canvas, run control, chat view | chua/khong ro | - |
| Co4ETab._flows | 257 | presentation/co4e/co4e_tab.py | danh sách flow đang mở dạng tab — trạng thái chia sẻ nhạy cảm (nêu rõ trong hướng dẫn đề bài) | chua/khong ro | - |
| Co4ETab._active_flow_idx | 258 | presentation/co4e/co4e_tab.py | chỉ số tab đang active — chia sẻ giữa _open_flow, _on_flow_tab_changed, _reflect_active_run | chua/khong ro | - |
| Co4ETab._split | 261 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._config_collapsed | 274 | presentation/co4e/co4e_tab.py | trạng thái cho _toggle_config (định nghĩa dòng 989, ngoài khoảng đọc); plan.md xếp _toggle_config ở co4e_tab.py container | co | - |
| Co4ETab._config_expanded_w | 275; 995 | presentation/co4e/co4e_tab.py | [GỘP 2 lượt quét trùng ký hiệu] (dòng 275-275, target gốc=presentation/co4e/co4e_tab.py) cùng lý do với _config_collapsed \|\| (dòng 995-995, target gốc=presentation/co4e/co4e_tab.py) gán trong nhánh collapse của _toggle_config; có thể đã khởi tạo trong __init__ (ngoài phạm vi đọc). | chua/khong ro | [GỘP 2 lượt quét trùng ký hiệu] (dòng 275-275, target gốc=presentation/co4e/co4e_tab.py) cùng lý do vớ |
| Co4ETab._narrow_guard | 280 | presentation/co4e/co4e_tab.py | gắn với _apply_narrow_layout (dòng 977, ngoài khoảng đọc) | chua/khong ro | - |
| Co4ETab._open_flow | 307-338 | presentation/co4e/co4e_tab.py | khớp plan.md: _open_flow() -> co4e_tab.py, gọi canvas; chạm self._flows, self.flow_bar (định nghĩa ngoài khoảng đọc), self.canvas | co | - |
| Co4ETab._close_other_flows | 340-355 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._show_runs | 357-367 | presentation/co4e/co4e_tab.py | chuyển đổi center_stack giữa flow editor và Runs table — liên quan Flow Status (run control) | chua/khong ro | - |
| Co4ETab._on_flow_tab_changed | 369-385 | presentation/co4e/co4e_tab.py | chạm self.center_stack (định nghĩa ngoài khoảng đọc, ở _build_center) | chua/khong ro | - |
| Co4ETab._sync_runs_toggle | 387-394 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._add_tab_close_button | 396-406 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._close_flow_tab_button | 408-412 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._close_flow_tab | 414-442 | presentation/co4e/co4e_tab.py | chạm self._flow_runs/_run_logs/_manual_active/self.run_btn (chia sẻ với run control widget) | chua/khong ro | - |
| Co4ETab._sync_active_flow_tab_text | 444-447 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._build_sidebar | 485-603 | presentation/co4e/co4e_tab.py | >80 dòng (119 dòng) — gộp dựng 4 section (Workflows/Agents/Skills/Runs) + wiring nhiều nút bấm; nên tách theo section: Workflows giữ ở container, Agents nên chuyển agent_list_panel.py, Skills đã tách (chỉ còn wiring), Runs nên chuyển co4e_run_control_widget.py | chua/khong ro | - |
| Co4ETab._sections | 493 | presentation/co4e/co4e_tab.py | trạng thái chia sẻ (nêu rõ trong hướng dẫn đề bài) — dùng bởi _fold_section, _sync_section_arrow | chua/khong ro | - |
| Co4ETab.sidebar | 494 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.side_split | 498 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| _Col | 503-511 | presentation/co4e/co4e_tab.py | adapter nội bộ định nghĩa bên trong _build_sidebar, chỉ dùng tại chỗ | chua/khong ro | - |
| _Col.__init__ | 506-507 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| _Col.addWidget | 509-511 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.wf_new_btn | 516 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.wf_list | 527 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.wf_edit_btn | 534 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.wf_dup_btn | 535 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.wf_del_btn | 536 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.wf_runbg_btn | 543 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._skills_panel | 575 | presentation/co4e/co4e_tab.py | instantiate SkillsListPanel đã tách; Co4ETab giữ wiring theo comment trong code (dòng 571-574) | chua/khong ro | - |
| Co4ETab.sk_manage_btn | 576 | presentation/co4e/co4e_tab.py | cùng lý do với _skills_panel | chua/khong ro | - |
| Co4ETab.skill_list | 578 | presentation/co4e/co4e_tab.py | cùng lý do với _skills_panel | chua/khong ro | - |
| Co4ETab._section | 631-663 | presentation/co4e/co4e_tab.py | chạm self._sections (chia sẻ) — helper dựng section sidebar dùng chung | chua/khong ro | - |
| Co4ETab._fold_section | 665-677 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._sync_section_arrow | 679-681 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._icon_btn | 683-687 | presentation/co4e/co4e_tab.py | helper dùng chung tạo nút icon, dùng bởi cả section Workflows và Agents | chua/khong ro | - |
| Co4ETab._reload_sidebar | 689-722 | presentation/co4e/co4e_tab.py | [GỘP 2 lượt quét trùng ký hiệu] (dòng 689-700, target gốc=presentation/co4e/co4e_tab.py) cắt ngang lát — cần agent gộp đối chiếu (method tiếp tục sau dòng 700); gọi co4e.list_workflows() (đọc đĩa) rồi dựng QListWidgetItem trực tiếp trong cùng hàm — trộn data-fetch và UI, nên tách phần đọc dữ liệu sang co4e_workflow_service.py \|\| (dòng 689-722, target gốc=unsure) cắt ngang lát — cần agent gộp đối chiếu (bắt đầu trước dòng 701). Gộp refresh cả agent_list và skill_list trong cùng 1 hàm — nên tách thành _refresh_agents_list (agent_list_panel.py) và _refresh_skills_list (skills_list_panel.py) như plan.md yêu cầu; gọi co4e.list_custom_agents() (đĩa) và skills_mod.skill_prefix_for (đĩa). | co | [GỘP 2 lượt quét trùng ký hiệu] (dòng 689-700, target gốc=presentation/co4e/co4e_tab.py) cắt ngang lát |
| Co4ETab._build_center | 731-871 | presentation/co4e/co4e_tab.py | dài ~140 dòng, làm nhiều việc không liên quan: dựng flow tab bar (ẩn, không hiển thị cho user), dựng runs-page stack, toolbar flow (name_edit/save/save_tpl/mode_combo/run_btn/runs_btn), tạo canvas, gọi _build_canvas_overlay, tạo chat widget, splitter dọc self._vsplit. Nên tách nhỏ. Đọc self._wf.name (dòng 814) và tạo self.center_stack — TRẠNG THÁI CHIA SẺ dùng bởi _show_runs/_apply_workflow (ngoài phạm vi đọc). Khớp phần '_build_canvas()' trong bảng plan.md dòng 615. | co | - |
| Co4ETab.flow_bar | 738 | presentation/co4e/co4e_tab.py | QTabBar bị ẩn (setVisible False dòng 802), chỉ dùng làm index nội bộ ánh xạ flow↔canvas — trạng thái chia sẻ với _on_flow_tab_changed/_close_flow_tab (định nghĩa <701, ngoài phạm vi đọc). | chua/khong ro | - |
| Co4ETab.flow_add_btn | 764 | presentation/co4e/co4e_tab.py | ẩn (setVisible False), không hiển thị cho user hiện tại. | chua/khong ro | - |
| Co4ETab.flow_scroll | 781 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.center_stack | 805 | presentation/co4e/co4e_tab.py | TRẠNG THÁI CHIA SẺ — chuyển đổi giữa trang Runs (co4e_run_control_widget) và trang flow editor; dùng bởi _show_runs (ngoài phạm vi đọc) và _apply_workflow. | chua/khong ro | - |
| Co4ETab.name_edit | 814 | presentation/co4e/co4e_tab.py | khởi tạo từ self._wf.name — trạng thái chia sẻ; cũng bị _on_name_changed/_new_workflow đọc/ghi. | chua/khong ro | - |
| Co4ETab.add_step_btn | 819 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.save_btn | 822 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.save_tpl_btn | 826 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._vsplit | 863 | presentation/co4e/co4e_tab.py | splitter dọc canvas/chat — dùng chung với _toggle_messages (co4e_chat_view.py thao tác self._vsplit.setSizes) — trạng thái chia sẻ giữa co4e_tab.py và co4e_chat_view.py. | chua/khong ro | - |
| Co4ETab._NARROW | 971 | presentation/co4e/co4e_tab.py | hằng class-level (không phải self.), ngưỡng chiều rộng dùng bởi _apply_narrow_layout. | chua/khong ro | - |
| Co4ETab.showEvent | 973-975 | presentation/co4e/co4e_tab.py | Qt override, gọi self._narrow_guard.attach() (đối tượng khởi tạo ngoài phạm vi đọc, <701). [ANOMALY: cùng tên method định nghĩa 2 lần ở 2 dòng khác nhau trong cùng class -- có khả năng là lỗi nguồn (định nghĩa sau đè định nghĩa trước), không phải do quét trùng; giữ 2 dòng riêng, cần người quyết định định nghĩa nào còn hiệu lực] | chua/khong ro | ợng khởi tạo ngoài phạm vi đọc, <701). [ANOMALY: cùng tên method định nghĩa 2 lần ở 2 dòng khác nhau trong cùng class -- có khả |
| Co4ETab._apply_narrow_layout | 977-987 | presentation/co4e/co4e_tab.py | so self._config_collapsed rồi gọi self._toggle_config() — trạng thái chia sẻ với node_property_panel wrap logic. | chua/khong ro | - |
| Co4ETab._toggle_config | 989-1032 | presentation/co4e/co4e_tab.py | dài 44 dòng, gộp: ẩn/hiện self.config (widget thuộc node_property_panel.py), đổi icon, tính lại self._split.setSizes, gọi _refresh_min_width — thao tác trực tiếp self.config/self.config_container (node_property_panel.py) và self._split (co4e_tab.py) cùng lúc — ranh giới tách file dễ vỡ nhất ở đoạn này. Ghi self._config_expanded_w. | chua/khong ro | - |
| Co4ETab._refresh_min_width | 1034-1039 | presentation/co4e/co4e_tab.py | thao tác trực tiếp self._split (QSplitter) và self.config_container — chia sẻ với _build_center/_wrap_config. | chua/khong ro | - |
| Co4ETab._apply_workflow | 1194-1207 | presentation/co4e/co4e_tab.py | hàm điều phối trung tâm khi mở 1 flow: gán self._wf (TRẠNG THÁI CHIA SẺ dùng khắp mọi nhóm chức năng — canvas, chat_stack/_flow_logs, config panel, run button, usage total). Đây là điểm nối chính giữa các file sau khi tách — không nên tách nhỏ hơn nếu không rất cẩn thận. | chua/khong ro | - |
| Co4ETab._new_workflow | 1209-1217 | presentation/co4e/co4e_tab.py | gọi self._open_flow(...) — khớp dòng plan.md '_open_flow() -> co4e_tab.py → gọi canvas'. | co | - |
| Co4ETab._selected_wf | 1219-1225 | presentation/co4e/co4e_tab.py | đọc self.wf_list (sidebar, dựng ở _build_sidebar <701) rồi gọi co4e.get_workflow (đĩa). | chua/khong ro | - |
| Co4ETab._load_selected_workflow | 1227-1230 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._edit_selected_workflow | 1232-1237 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._wf_context_menu | 1248-1271 | presentation/co4e/co4e_tab.py | dựng QMenu cho sidebar flows, điều phối gọi _edit_selected_workflow/_rename_workflow/_duplicate_selected_workflow/_run_selected_in_background/_delete_selected_workflow (một số nằm ngoài phạm vi đọc, dòng >1400). | chua/khong ro | - |
| Co4ETab._sync_wf_from_canvas | 1299-1302 | presentation/co4e/co4e_tab.py | đọc self.canvas.nodes()/edges() và ghi self._wf.nodes/edges/name — cầu nối giữa co4e_canvas_widget.py và trạng thái self._wf chia sẻ; cân nhắc đặt cùng canvas nếu muốn canvas tự chịu trách nhiệm export dữ liệu. | chua/khong ro | - |
| Co4ETab._on_name_changed | 1316-1318 | presentation/co4e/co4e_tab.py | ghi self._wf.name (trạng thái chia sẻ) rồi gọi self._sync_active_flow_tab_text() (định nghĩa dòng 444, ngoài phạm vi đọc). | chua/khong ro | - |
| Co4ETab._add_blank_step | 1320-1322 | presentation/co4e/co4e_tab.py | nút 'Add' trên toolbar uỷ nhiệm sang self.canvas.add_palette_step — liên quan nhóm _add_node() trong plan.md (co4e_canvas_widget.py) nhưng bản thân handler chỉ là cầu nối từ toolbar. | co | - |
| Co4ETab.set_project | 1658-1674 | presentation/co4e/co4e_tab.py | gọi load_project(project_id) (đọc đĩa) và self.manager.set_output_root/set_current_project (self.manager nên là co4e_workflow_service). Gán self._project_id, self._project_dir — không chắc là lần gán đầu tiên (có thể đã init ở __init__ ngoài khoảng đọc). Không khớp rõ nhóm nào trong danh sách đích cho trước — xếp tạm vào co4e_tab.py vì đây là API binding cấp container gọi từ ngoài. | chua/khong ro | ể đã init ở __init__ ngoài khoảng đọc). Không khớp rõ nhóm nào trong danh sách đích cho trước — xếp tạm vào co4e_tab.py vì đây là |
| Co4ETab._flow_output_root | 1676-1686 | presentation/co4e/co4e_tab.py | helper dùng chung bởi cả chat (_out_dir) và run-control (_open_workspace_folder, _open_run_output_folder) — trạng thái/logic cắt ngang nhiều nhóm; đọc self._project_dir, self.ctx.config | chua/khong ro | - |
| Co4ETab._refresh_ws_folder_btn | 1688-1693 | presentation/co4e/co4e_tab.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._open_workspace_folder | 1695-1702 | presentation/co4e/co4e_tab.py | root.mkdir + open_location (mở file explorer hệ điều hành — spawn process) | chua/khong ro | - |
| Co4ETab.showEvent | 1806-1809 | presentation/co4e/co4e_tab.py | override Qt lifecycle method của chính QWidget container nên phải ở lại co4e_tab.py; gọi self._refresh_runs() (thuộc co4e_run_control_widget.py) — điểm nối giữa container và run-control widget. [ANOMALY: cùng tên method định nghĩa 2 lần ở 2 dòng khác nhau trong cùng class -- có khả năng là lỗi nguồn (định nghĩa sau đè định nghĩa trước), không phải do quét trùng; giữ 2 dòng riêng, cần người quyết định định nghĩa nào còn hiệu lực] | chua/khong ro | giữa container và run-control widget. [ANOMALY: cùng tên method định nghĩa 2 lần ở 2 dòng khác nhau trong cùng class -- có khả |
| Co4ETab._out_dir | 1811-1817 | presentation/co4e/co4e_tab.py | d.mkdir(parents=True, exist_ok=True) — ghi đĩa; dùng chung bởi _run_chat_turn (chat) và tiềm năng bởi run-control; đọc self._wf.name, self._flow_output_root() | chua/khong ro | - |
| Co4ETab._retranslate | 2059-2079 | presentation/co4e/co4e_tab.py | cập nhật text i18n cho rất nhiều widget thuộc nhiều nhóm khác nhau (sidebar buttons, runs_table, run control buttons) và gọi self._reload_sidebar()/self._refresh_runs() — thuộc container vì bao trùm toàn tab, dù có thể tách nhỏ theo từng panel sau này. | chua/khong ro | - |
| _SectionHeader | 30-52 | presentation/co4e/node_property_panel.py | Widget nội bộ (header có thể click, thu/mở section) chỉ dùng bởi StepConfigPanel; không có trong bảng plan.md/function_list.md, xếp cùng chỗ với StepConfigPanel vì mô tả node_property_panel.py là 'Bọc StepConfigPanel' | co | section) chỉ dùng bởi StepConfigPanel; không có trong bảng plan.md/function_list.md, xếp cùng chỗ với StepConfigPanel vì mô tả node_property_panel |
| _SectionHeader.clicked | 36 | presentation/co4e/node_property_panel.py | Signal Qt khai báo ở cấp class, không phải self.<tên> gán trong __init__ | chua/khong ro | - |
| _SectionHeader.mousePressEvent | 38-41 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| _SectionHeader.showEvent | 43-52 | presentation/co4e/node_property_panel.py | recompute fontMetrics khi label thực sự hiển thị — cần widget đang sống, không test được nếu không có QApplication | chua/khong ro | - |
| _add_section | 55-130 | presentation/co4e/node_property_panel.py | Hàm dựng UI khối section thu gọn/mở rộng (header + body animate) dùng riêng cho StepConfigPanel; chứa 2 closure nội bộ _on_finished và _toggle. Không có trong bảng cũ. | co | closure nội bộ _on_finished và _toggle. Không có trong bảng cũ. |
| _add_section._on_finished | 103-112 | presentation/co4e/node_property_panel.py | closure lồng bên trong _add_section, không phải hàm top-level — chỉ tồn tại khi _add_section chạy | chua/khong ro | - |
| _add_section._toggle | 114-127 | presentation/co4e/node_property_panel.py | closure lồng bên trong _add_section, gắn vào header.clicked | chua/khong ro | - |
| StepConfigPanel | 133-528 | presentation/co4e/node_property_panel.py | cắt ngang lát — cần agent gộp đối chiếu (lớp còn tiếp tục sau dòng 528, chỉ đọc được 1-528). Bảng plan.md/function_list.md không liệt kê StepConfigPanel trực tiếp (chỉ có _build_config_panel() -> co4e_tab.py container); xếp theo mô tả node_property_panel.py 'Bọc StepConfigPanel, nối chọn node sang panel thuộc tính' trong danh sách đích được giao cho task này — người quyết cuối nên xác nhận lại. | co | - |
| StepConfigPanel.changed | 134 | presentation/co4e/node_property_panel.py | Signal Qt: bất kỳ field nào đổi -> canvas repaint node + autosave; đây là điểm nối trạng thái chia sẻ với canvas/co4e_workflow_service, cần giữ tên/signature khi tách file | chua/khong ro | - |
| StepConfigPanel.run_node | 135 | presentation/co4e/node_property_panel.py | Signal Qt 'chạy step này' — nối sang co4e_run_control_widget.py hoặc co4e_workflow_service.py | chua/khong ro | - |
| StepConfigPanel.run_from | 136 | presentation/co4e/node_property_panel.py | Signal Qt 'chạy từ bước này' — nối sang co4e_run_control_widget.py | chua/khong ro | - |
| StepConfigPanel.delete_node | 137 | presentation/co4e/node_property_panel.py | Signal Qt xoá step — nối sang co4e_canvas_widget.py để xoá node trên canvas | chua/khong ro | - |
| StepConfigPanel.__init__ | 139-313 | presentation/co4e/node_property_panel.py | >80 dòng (174 dòng) — gộp nhiều việc không liên quan: dựng section Cơ bản, section Model&Quyền, section Skills&Tệp, section Sub-agents (ẩn/hiện theo is_parallel), và dựng hàng nút footer Run/Run-from/Delete, cộng thêm cơ chế 'outer.addStretch(1)' vá lỗi layout. Nên tách thành các hàm _build_basic_section(), _build_model_section(), _build_skills_section(), _build_subagent_section(), _build_footer() riêng khi tách file. | chua/khong ro | - |
| StepConfigPanel.ctx | 141 | presentation/co4e/node_property_panel.py | context được truyền từ ngoài vào, dùng cho _ai_draft/_load_models (gọi AI provider) — trạng thái chia sẻ với co4e_tab.py | chua/khong ro | - |
| StepConfigPanel._step | 142 | presentation/co4e/node_property_panel.py | Step đang chỉnh sửa — trạng thái chia sẻ giữa load_step()/_on_edit()/mọi hành động subagent+attachment; do canvas gán vào qua load_step() | chua/khong ro | - |
| StepConfigPanel._node_id | 143 | presentation/co4e/node_property_panel.py | id node đang chọn — dùng để emit run_node/run_from/delete_node; là cầu nối canvas <-> property panel | chua/khong ro | - |
| StepConfigPanel._loading | 144 | presentation/co4e/node_property_panel.py | cờ chặn _on_edit() chạy lại trong lúc load_step() đang set giá trị field | chua/khong ro | - |
| StepConfigPanel.label_edit | 159 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| StepConfigPanel.role_edit | 163 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| StepConfigPanel.icon_edit | 170 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| StepConfigPanel.instructions_edit | 175 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| StepConfigPanel.gen_btn | 178 | presentation/co4e/node_property_panel.py | nút 'AI draft' — enable chỉ khi có ctx | chua/khong ro | - |
| StepConfigPanel.context_edit | 192 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| StepConfigPanel.model_combo | 201 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| StepConfigPanel.load_models_btn | 204 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| StepConfigPanel.perm_combo | 214 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| StepConfigPanel.verify_chk | 221 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| StepConfigPanel.rounds_spin | 223 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| StepConfigPanel.skills_list | 236 | presentation/co4e/node_property_panel.py | checklist skill của registry, gán checked theo step.skills | chua/khong ro | - |
| StepConfigPanel.attach_list | 242 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| StepConfigPanel.attach_add_btn | 244 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| StepConfigPanel.attach_del_btn | 247 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| StepConfigPanel._parallel_card | 263 | presentation/co4e/node_property_panel.py | card cả section Sub-agents; load_step() ẩn/hiện toàn bộ card này theo step.is_parallel | chua/khong ro | - |
| StepConfigPanel.sub_list | 264 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| StepConfigPanel.sub_add_btn | 267 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.config | 268 | presentation/co4e/node_property_panel.py | StepConfigPanel + wiring changed/run_node/run_from/delete_node (dòng 268-273) — khớp vai trò mô tả cho node_property_panel.py | chua/khong ro | - |
| StepConfigPanel.sub_del_btn | 270 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| StepConfigPanel.run_btn | 283 | presentation/co4e/node_property_panel.py | click emit run_node(self._node_id) | chua/khong ro | - |
| StepConfigPanel.run_from_btn | 287 | presentation/co4e/node_property_panel.py | click emit run_from(self._node_id) | chua/khong ro | - |
| StepConfigPanel.del_btn | 290 | presentation/co4e/node_property_panel.py | click emit delete_node(self._node_id) | chua/khong ro | - |
| StepConfigPanel.load_step | 316-354 | presentation/co4e/node_property_panel.py | Điểm nối chính giữa canvas (khi chọn node) và panel thuộc tính — nhận (node_id, step, skill_names) từ ngoài rồi ghi self._step/self._node_id; đây là API mà co4e_canvas_widget.py hoặc co4e_tab.py sẽ gọi khi chọn node | chua/khong ro | - |
| StepConfigPanel.clear_step | 356-359 | presentation/co4e/node_property_panel.py | gọi khi bỏ chọn node — reset self._step/self._node_id | chua/khong ro | - |
| StepConfigPanel._on_edit | 362-378 | presentation/co4e/node_property_panel.py | ghi ngược giá trị field UI vào self._step rồi emit changed() — canvas repaint + autosave phụ thuộc signal này, đổi tên/behavior ở đây ảnh hưởng cả canvas lẫn service lưu flow | chua/khong ro | - |
| StepConfigPanel._available_agent_names | 380-390 | presentation/co4e/node_property_panel.py | staticmethod; gọi core.co4e.list_custom_agents() đọc file JSON trong AGENTS_DIR trên đĩa — logic thuần Python nhưng có I/O, có thể tách ra application layer nếu cần test không đụng đĩa | chua/khong ro | - |
| StepConfigPanel._add_subagent | 392-408 | presentation/co4e/node_property_panel.py | dùng QInputDialog để chọn/nhập tên agent song song | chua/khong ro | - |
| StepConfigPanel._edit_subagent | 410-428 | presentation/co4e/node_property_panel.py | double-click 1 dòng sub-agent để chọn lại agent khác | chua/khong ro | - |
| StepConfigPanel._del_subagent | 430-437 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| StepConfigPanel._add_attachment | 439-453 | presentation/co4e/node_property_panel.py | QFileDialog chỉ chọn đường dẫn hiển thị tên file, không tự đọc nội dung ở đây (nội dung được đọc lúc chạy step, ở nơi khác) | chua/khong ro | - |
| StepConfigPanel._del_attachment | 455-462 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| StepConfigPanel._ai_draft | 464-498 | presentation/co4e/node_property_panel.py | gọi generate_agent_prompt(ctx.build_active_provider(), ...) qua AgentWorker — gọi network tới AI provider, chạy nền rồi cập nhật UI ở callback done(); nếu tách sang service, phần gọi AI nên chuyển xuống application layer, phần còn lại (QInputDialog + set text) ở lại đây | chua/khong ro | - |
| StepConfigPanel._draft_worker | 497 | presentation/co4e/node_property_panel.py | giữ tham chiếu AgentWorker (QThread-like) để không bị GC giữa lúc job async đang chạy | chua/khong ro | - |
| StepConfigPanel._load_models | 500-528 | presentation/co4e/node_property_panel.py | gọi preview_ai.fetch_live_models(ctx) qua AgentWorker — network call tới provider để lấy danh sách model; cắt ngang lát — cần agent gộp đối chiếu vì dòng cuối trùng đúng biên đọc được giao (528), chưa chắc thân method đã hết ở đây | chua/khong ro | - |
| StepConfigPanel._model_worker | 525 | presentation/co4e/node_property_panel.py | giữ tham chiếu AgentWorker của _load_models để không bị GC | chua/khong ro | - |
| Co4ETab._wrap_config | 934-964 | presentation/co4e/node_property_panel.py | bọc self.config (StepConfigPanel) với header expand/collapse — khớp mô tả node_property_panel.py trong prompt. | chua/khong ro | - |
| Co4ETab.config_toggle_btn | 946 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.config_title | 951 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab._cfg_vlayout | 957 | presentation/co4e/node_property_panel.py | dùng lại trong _toggle_config (co4e_tab.py) — trạng thái chia sẻ. | chua/khong ro | - |
| Co4ETab._cfg_top_spacer | 961 | presentation/co4e/node_property_panel.py | QSpacerItem — kiểu giá trị layout, không cần QApplication đang sống. | chua/khong ro | - |
| Co4ETab._cfg_bot_spacer | 962 | presentation/co4e/node_property_panel.py | (không có ghi chú) | chua/khong ro | - |
| Co4ETab.config_container | 963 | presentation/co4e/node_property_panel.py | dùng lại bởi _toggle_config (co4e_tab.py) — trạng thái chia sẻ giữa node_property_panel.py và co4e_tab.py. | chua/khong ro | - |
| Co4ETab._on_node_selected | 1325-1331 | presentation/co4e/node_property_panel.py | khớp mô tả 'nối chọn node sang panel thuộc tính' trong prompt. Đọc self.canvas.nodes() và self.config, toggle self._config_collapsed (trạng thái chia sẻ với _toggle_config ở co4e_tab.py). | chua/khong ro | - |
| Co4ETab._on_config_changed | 1333-1336 | presentation/co4e/node_property_panel.py | gọi self.canvas.refresh_node cho từng node rồi self._autosave() — cầu nối property panel ↔ canvas ↔ service lưu đĩa. | chua/khong ro | - |
| Co4ETab._manage_skills | 1369-1373 | presentation/co4e/skills_list_panel.py | mở SkillsDialog rồi self._reload_sidebar() — không có tên tương ứng trực tiếp trong bảng plan.md, tự xếp theo mô tả skills_list_panel.py. | co | - |
| _PaletteList | 97-119 | unsure | list kéo-thả dùng chung cho wf_list và agent_list, phát payload CO4E_MIME hiểu bởi canvas — không rõ nên đặt ở co4e_tab.py (nơi dùng) hay co4e_canvas_widget.py (định nghĩa giao thức CO4E_MIME) | chua/khong ro | - |
| _PaletteList.__init__ | 102-106 | unsure | cùng lý do với class _PaletteList | chua/khong ro | - |
| _PaletteList._payload_role | 104 | unsure | cùng lý do với class _PaletteList | chua/khong ro | - |
| _PaletteList.startDrag | 108-119 | unsure | cùng lý do với class _PaletteList; dùng CO4E_MIME từ co4e_canvas | chua/khong ro | - |
| Co4ETab._project_id | 249 | unsure | project Workspace đang chọn, ảnh hưởng đường dẫn output flow — không chắc thuộc container hay run control | chua/khong ro | - |
| Co4ETab._project_dir | 250 | unsure | cùng lý do với _project_id | chua/khong ro | - |
| Co4ETab._reflect_active_run | 449-457 | unsure | cầu nối giữa self.manager (run control) và self.canvas (canvas widget) — không chắc nên đặt file nào | chua/khong ro | - |
| Co4ETab._palette_item | 724-728 | unsure | staticmethod helper dùng chung để tạo QListWidgetItem cho cả agent_list, skill_list, và cả node palette sequential/parallel (thấy dùng ở dòng 701-704) — không rõ nên đặt ở agent_list_panel.py, skills_list_panel.py hay co4e_canvas_widget.py. | chua/khong ro | - |

## Chỗ thấy khác tài liệu — cần người quyết

Không có symbol nào có note bắt đầu bằng `khac tai lieu:` trong dữ liệu 367 symbol đầu vào. Mục này để trống theo đúng dữ liệu quét được — không tự bịa thêm mục.
