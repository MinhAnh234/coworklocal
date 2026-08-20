# 📋 COWORK-LOCAL BamBOO — Danh Sách Chức Năng Chi Tiết Theo Navigation Bar

---

## 🔹 1. 📊 DASHBOARD (Bảng Điều Khiển)

### 1.1 Token Usage & Cost — Thống Kê Token & Chi Phí

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 1.1.1 | `_refresh_cards()` | Làm mới các thẻ thống kê (Total, Input, Output, Cache tokens + Cost) |
| 1.1.2 | `_refresh_chart()` | Vẽ biểu đồ spline theo chu kỳ (week/month/year) và metric (cost/tokens) |
| 1.1.3 | `_chart_prev()` / `_chart_next()` | Chuyển đến chu kỳ trước/sau trên biểu đồ |
| 1.1.4 | `_on_gran_changed()` | Thay đổi đơn vị thời gian (week/month/year) |
| 1.1.5 | `_refresh_budget()` | Cập nhật ngân sách (budget card — còn lại / đã dùng / cảnh báo >85%) |
| 1.1.6 | `_apply_budget()` | Lưu giá trị budget mới |
| 1.1.7 | `_refresh_habits()` | Hiển thị thói quen sử dụng (task tốn nhiều token nhất, trung bình/prompt, ngày/giờ bận nhất) |
| 1.1.8 | `_ai_analyze()` | ✨ AI phân tích thói quen dùng token và gợi ý tiết kiệm |
| 1.1.9 | `_apply_saving_strategy()` | Áp dụng chiến lược tiết kiệm AI (tự nén context, nén sớm hơn) |
| 1.1.10 | Currency Picker | Chọn đơn vị tiền tệ hiển thị (USD, VND, JPY, …) |

---

## 🔹 2. 📅 SCHEDULE TASK (Lên Lịch Nhiệm Vụ)

### 2.1 Kanban Board

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 2.1.1 | `_build_kanban()` | Xây dựng board Kanban với 7 cột: Backlog, Scheduled, Running, Waiting Input, Done, Failed, Paused |
| 2.1.2 | `_render_kanban()` | Render các thẻ task vào từng cột |
| 2.1.3 | `_on_task_dropped(task_id, new_status)` | Kéo thả task giữa các cột (thay đổi status) |
| 2.1.4 | `_on_card_double_click()` | Mở Task Editor khi double-click |
| 2.1.5 | `_on_card_right_click()` | Menu ngữ cảnh: Run now, Edit, Duplicate, Pause, Delete, View logs, Create-next-from-output |
| 2.1.6 | `_bulk_delete_menu()` | Xóa hàng loạt (chọn nhiều thẻ → right-click → Delete N selected) |
| 2.1.7 | `_run_now(task_id)` | Chạy task ngay lập tức |
| 2.1.8 | `_duplicate_task(task_id)` | Sao chép task |
| 2.1.9 | `_pause_task(task_id)` | Tạm dừng task |
| 2.1.10 | `_delete_task(task_id)` | Xóa task |
| 2.1.11 | `_view_logs(task_id)` | Xem log của task |
| 2.1.12 | `_search_tasks()` | Tìm kiếm task theo tên |
| 2.1.13 | `_filter_by_type()` | Lọc task theo loại (cowork/co4e/code/…) |

### 2.2 Calendar View

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 2.2.1 | `_build_calendar()` | Xây dựng chế độ xem lịch |
| 2.2.2 | `_shift(direction)` | Chuyển tháng/tuần trước/sau |
| 2.2.3 | `add_task_on_date(date)` | Thêm task vào ngày cụ thể |
| 2.2.4 | `edit_task(task_id)` | Sửa task từ lịch |

### 2.3 Add / AI Create Task

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 2.3.1 | `_open_add_dialog()` | Mở dialog thêm task thủ công |
| 2.3.2 | `_ai_create_task()` | Mở dialog AI tạo task tự động |
| 2.3.3 | `_ai_pick_files()` | Chọn file đính kèm cho AI planner |
| 2.3.4 | `_generate()` | AI tạo kế hoạch tasks từ mô tả |
| 2.3.5 | `_on_planned(result)` | Hiển thị preview các task AI đề xuất |
| 2.3.6 | `_confirm()` | Xác nhận và tạo các task từ AI plan |

### 2.4 AI Import Tasks

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 2.4.1 | `_ai_import()` | AI nhập task từ file/link |
| 2.4.2 | `_ai_pick_import_files()` | Chọn file để import |
| 2.4.3 | `_generate_import()` | AI phân tích file và tạo tasks |
| 2.4.4 | `_on_import_planned()` | Hiển thị preview import |

---

## 🔹 3. 🏠 WORKSPACE (Không Gian Làm Việc)

### 3.1 Projects — Quản Lý Dự Án (Tab 0)

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 3.1.1 | `_create()` | Tạo dự án mới |
| 3.1.2 | `_delete()` | Xóa dự án (có xác nhận) |
| 3.1.3 | `_save()` | Lưu thông tin dự án (name, description, instructions, folder) |
| 3.1.4 | `_pick_folder()` | Chọn workspace folder cho dự án |
| 3.1.5 | `_open_workspace()` | Mở folder workspace trong file explorer |
| 3.1.6 | `_select_project_row(project_id)` | Chọn dự án trong danh sách |
| 3.1.7 | `_refresh_sandbox_toggle()` | Bật/tắt sandbox cho dự án |
| 3.1.8 | `refresh()` | Làm mới danh sách dự án |

### 3.2 Workspace Pane — Mỗi Dự Án Mở (Tab 1..N)

#### 3.2.1 🤖 COWORK — Chat Với AI Agent

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 3.2.1.1 | `new_session()` | Tạo phiên chat mới |
| 3.2.1.2 | `send_message()` | Gửi tin nhắn đến AI agent |
| 3.2.1.3 | `_build_job()` | Xây dựng job cho AgentWorker (gọi `run_cowork`) |
| 3.2.1.4 | `_cleanup_turn(ctx, ok)` | Dọn dẹp sau khi turn kết thúc (promote files, xóa sandbox) |
| 3.2.1.5 | `_promote_turn_outputs()` | Di chuyển file đầu ra từ sandbox lên session output |
| 3.2.1.6 | `_refresh_outputs_from_disk()` | Làm mới danh sách output files |
| 3.2.1.7 | `_pick_output_folder()` | Chọn thư mục output |
| 3.2.1.8 | `_open_skills_manager()` | Mở Skill Manager |
| 3.2.1.9 | `refresh_header()` | Làm mới header (project name, model info) |
| 3.2.1.10 | `refresh_agents()` | Làm mới danh sách agents trong combo |
| 3.2.1.11 | `admin_agent_prompt()` | Lấy prompt từ agent preset đã chọn |
| 3.2.1.12 | `build_provider()` | Xây dựng provider từ cấu hình agent/model |
| 3.2.1.13 | `workspace_dir()` | Trả về workspace directory hiện tại |
| 3.2.1.14 | `_start_watching(dir)` | Giám sát folder output (file watcher) |
| 3.2.1.15 | `_on_file_changed()` | Xử lý khi file output thay đổi |

**ChatPanel (Class cha của CoworkTab):**

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 3.2.1.16 | `_submit_message()` | Gửi tin nhắn (kiểm tra queue, parallel limit) |
| 3.2.1.17 | `_on_turn_started()` | Khi turn bắt đầu (show thinking indicator) |
| 3.2.1.18 | `_on_turn_finished()` | Khi turn kết thúc (update UI, queue next) |
| 3.2.1.19 | `_on_event(ev)` | Xử lý streaming events (text delta, tool calls, plan) |
| 3.2.1.20 | `_compress_messages()` | Nén tin nhắn cũ để giảm token |
| 3.2.1.21 | `_on_agent_changed()` | Khi thay đổi agent trong combo |
| 3.2.1.22 | `_apply_routing()` | Áp dụng model routing (Auto/Manual/Off) |
| 3.2.1.23 | `_note_agent_switch()` | Ghi chú khi agent thay đổi giữa các turn |
| 3.2.1.24 | `_ensure_conversation()` | Đảm bảo conversation tab tồn tại |
| 3.2.1.25 | `load_conversation()` | Load hội thoại từ disk |
| 3.2.1.26 | `running_session_ids()` | Trả về danh sách session đang chạy |
| 3.2.1.27 | `active_workers()` | Trả về danh sách worker đang hoạt động |
| 3.2.1.28 | `_save_conversation()` | Tự động lưu hội thoại |

**Composer (Composer input box):**

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 3.2.1.29 | `send()` | Gửi tin nhắn |
| 3.2.1.30 | `attach_files()` | Đính kèm file |
| 3.2.1.31 | `attach_links()` | Đính kèm link URL |
| 3.2.1.32 | `has_any_queue()` | Kiểm tra queue có tin nhắn chờ |
| 3.2.1.33 | `_parse_directives()` | Phân tích directives inline (`/agent:name`, `/skill:name`) |
| 3.2.1.34 | `_show_autocomplete()` | Hiển thị gợi ý tự động |

#### 3.2.2 ⚡ CO4E — Node-Graph Workflow Studio

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 3.2.2.1 | `_build_sidebar()` | Xây dựng sidebar (Workflows / Agents / Skills tabs) |
| 3.2.2.2 | `_build_canvas()` | Xây dựng canvas node-graph |
| 3.2.2.3 | `_build_config_panel()` | Xây dựng config panel bên phải |
| 3.2.2.4 | `_toggle_config()` | Thu/mở config panel |
| 3.2.2.5 | `_build_canvas_overlay()` | Zoom +/− và Fit buttons trên canvas |

**Workflows (Sidebar):**

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 3.2.2.6 | `_refresh_flows_list()` | Làm mới danh sách flows |
| 3.2.2.7 | `_create_flow()` | Tạo flow mới |
| 3.2.2.8 | `_delete_flow()` | Xóa flow |
| 3.2.2.9 | `_duplicate_flow()` | Sao chép flow |
| 3.2.2.10 | `_import_flow()` | Import flow từ file |
| 3.2.2.11 | `_export_flow()` | Export flow ra file |
| 3.2.2.12 | `_run_flow()` | Chạy flow (foreground/background) |
| 3.2.2.13 | `_stop_flow()` | Dừng flow đang chạy |
| 3.2.2.14 | `_open_flow()` | Mở flow trên canvas |

**Agents (Sidebar):**

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 3.2.2.15 | `_refresh_agents_list()` | Làm mới danh sách agents |
| 3.2.2.16 | `_create_agent()` | Tạo agent mới (dialog) |
| 3.2.2.17 | `_edit_agent()` | Sửa agent |
| 3.2.2.18 | `_delete_agent()` | Xóa agent |
| 3.2.2.19 | `_toggle_agent_enabled()` | Bật/tắt agent |

**Skills (Sidebar):**

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 3.2.2.20 | `_refresh_skills_list()` | Làm mới danh sách skills |

**Canvas (Node-Graph):**

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 3.2.2.21 | `zoom_in()` / `zoom_out()` | Zoom canvas |
| 3.2.2.22 | `fit_view()` | Auto-fit canvas |
| 3.2.2.23 | `_add_node()` | Thêm node lên canvas |
| 3.2.2.24 | `_delete_node()` | Xóa node |
| 3.2.2.25 | `_connect_nodes()` | Kết nối 2 nodes |
| 3.2.2.26 | `_drag_node()` | Kéo thả node |
| 3.2.2.27 | `_select_node()` | Chọn node (→ config panel) |
| 3.2.2.28 | `_activate_node()` | Double-click node |

**Run Modes:**

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 3.2.2.29 | `_set_run_mode("auto")` | Auto mode: agent tự plan rồi execute |
| 3.2.2.30 | `_set_run_mode("plan")` | Plan mode: chỉ tạo kế hoạch |
| 3.2.2.31 | `_set_run_mode("manual")` | Manual mode: từng bước, bấm "Next step" |
| 3.2.2.32 | `_run_step()` | Chạy bước tiếp theo (manual mode) |
| 3.2.2.33 | `_on_step_finished()` | Xử lý khi bước hoàn thành |
| 3.2.2.34 | `_render_plan()` | Render plan checklist |

**Chat/Output (Bottom):**

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 3.2.2.35 | `_get_flow_chat(flow_id)` | Lấy ChatView cho flow (tạo mới nếu chưa có) |
| 3.2.2.36 | `_on_chat_event()` | Xử lý event từ chat |

#### 3.2.3 📁 FOLDER — File Explorer

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 3.2.3.1 | `set_root(path)` | Đặt thư mục gốc |
| 3.2.3.2 | `_build_tree_view()` | Xây dựng cây thư mục (QFileSystemModel) |
| 3.2.3.3 | `_open_file(path)` | Mở file được chọn |
| 3.2.3.4 | `_view_source()` | Xem source code (syntax highlighting) |
| 3.2.3.5 | `_view_html_preview()` | Preview HTML (WebEngine/rich text) |
| 3.2.3.6 | `_view_office_doc()` | Xem Office doc (docx/pdf/xlsx/…) |
| 3.2.3.7 | `_view_image()` | Hiển thị ảnh inline |
| 3.2.3.8 | `_edit_file()` | Chỉnh sửa file (code editor) |
| 3.2.3.9 | `_save_file()` | Lưu file |
| 3.2.3.10 | `_preview_toggle()` | Chuyển đổi Preview ⇄ Edit |
| 3.2.3.11 | `_create_new_file()` | Tạo file mới |
| 3.2.3.12 | `_create_new_folder()` | Tạo folder mới |
| 3.2.3.13 | `_rename_item()` | Đổi tên file/folder |
| 3.2.3.14 | `_delete_item()` | Xóa file/folder |
| 3.2.3.15 | `_copy_item()` | Sao chép file/folder |
| 3.2.3.16 | `_paste_item()` | Dán file/folder |
| 3.2.3.17 | `refresh_ai_models()` | Làm mới danh sách AI models cho AI Edit |

**AI Edit (Chỉnh Sửa File Bằng AI):**

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 3.2.3.18 | `_ai_send()` | Gửi yêu cầu AI edit |
| 3.2.3.19 | `_ai_apply()` | Áp dụng thay đổi AI |
| 3.2.3.20 | `_ai_discard()` | Hủy thay đổi AI |
| 3.2.3.21 | `_reset_ai_conversation()` | Xóa hội thoại AI edit |
| 3.2.3.22 | `_ai_apply_routing()` | Áp dụng routing cho AI edit |

#### 3.2.4 🧠 GRAPH RAG — Knowledge Graph

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 3.2.4.1 | `_build_graph()` | Xây dựng knowledge graph từ code/documents |
| 3.2.4.2 | `_render_d3_graph()` | Render graph bằng D3.js (WebEngine) |
| 3.2.4.3 | `_render_native_graph()` | Render graph bằng QGraphicsView (fallback) |
| 3.2.4.4 | `_auto_rotate()` | Tự xoay graph khi idle |
| 3.2.4.5 | `_on_node_click()` | Xử lý click node (mở folder) |
| 3.2.4.6 | `_open_node_path()` | Mở folder chứa node |
| 3.2.4.7 | `_refresh_graph()` | Tự cập nhật graph khi có output mới |
| 3.2.4.8 | `_search_graph()` | Tìm kiếm trong graph |
| 3.2.4.9 | `_filter_by_kind()` | Lọc node theo loại |
| 3.2.4.10 | `_zoom_graph()` | Zoom graph |

**Graph-RAG Q&A:**

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 3.2.4.11 | `_ask_question()` | Hỏi AI về graph |
| 3.2.4.12 | `_on_ask_event()` | Xử lý streaming answer |
| 3.2.4.13 | `_on_ask_done()` | Khi AI trả lời xong |
| 3.2.4.14 | `_candidate_file_paths()` | Lấy danh sách file để extract |
| 3.2.4.15 | `_extract_tmp_dir()` | Tạo thư mục tạm cho extraction |
| 3.2.4.16 | `_clear_extracts()` | Xóa dữ liệu extract tạm |

---

## 🔹 4. 📊 MONITORING (Giám Sát)

### 4.1 Overview — Tổng Quan

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 4.1.1 | `_refresh_overview()` | Làm mới tất cả cards overview |
| 4.1.2 | `_refresh_usage_cards()` | Token Usage & Cost cards (Total, Input, Output, Cache) |
| 4.1.3 | `_refresh_resource_usage()` | Resource usage (CPU, RAM, Disk) |
| 4.1.4 | `_refresh_recent_activity()` | Hoạt động gần đây |
| 4.1.5 | `_refresh_sandbox_details()` | Chi tiết sandbox (PID, uptime, limits) |
| 4.1.6 | `_refresh_permissions()` | Hiển thị permissions hiện tại |
| 4.1.7 | `_refresh_audit_log()` | Audit log gần đây |
| 4.1.8 | `_refresh_budget()` | Budget card (còn lại / đã dùng) |
| 4.1.9 | `_apply_budget()` | Lưu budget mới |

### 4.2 Security Events — Sự Kiện Bảo Mật

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 4.2.1 | `_refresh_security_events()` | Làm mới bảng security events (audit log `kind="security_block"`) |
| 4.2.2 | `_filter_security_events()` | Lọc sự kiện bảo mật |
| 4.2.3 | `_sort_events()` | Sắp xếp bảng events |

### 4.3 MCP Call History — Lịch Sử Gọi MCP

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 4.3.1 | `_refresh_mcp_calls()` | Làm mới bảng MCP calls (audit log `kind="mcp_call"`) |
| 4.3.2 | `_filter_mcp_calls()` | Lọc MCP calls |

### 4.4 Action Logs — Nhật Ký Hành Động

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 4.4.1 | `_refresh_action_logs()` | Làm mới bảng action logs (toàn bộ audit log) |
| 4.4.2 | `_filter_action_logs()` | Lọc action logs |
| 4.4.3 | `_sort_action_logs()` | Sắp xếp action logs |

### 4.5 Agent Status — Trạng Thái Agent

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 4.5.1 | `_refresh_agent_status()` | Làm mới trạng thái các agent (Cowork, Co4E, Schedule, GraphRAG) |

### 4.6 Security Settings — Cài Đặt Bảo Mật

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 4.6.1 | `_toggle_sandbox()` | Bật/tắt sandbox |
| 4.6.2 | `_toggle_network_block()` | Chặn kết nối mạng |
| 4.6.3 | `_set_resource_limits()` | Đặt giới hạn tài nguyên (CPU/RAM/Disk) |
| 4.6.4 | `_toggle_command_confirm()` | Xác nhận trước khi chạy lệnh |
| 4.6.5 | `_manage_permissions()` | Quản lý quyền truy cập |

---

## 🔹 5. ⚙️ SETTINGS (Cài Đặt)

### 5.1 AI Provider — Nhà Cung Cấp AI

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 5.1.1 | `_on_provider_changed()` | Khi thay đổi provider |
| 5.1.2 | `_load_models(provider)` | Load danh sách models của provider |
| 5.1.3 | `_test_connection(provider)` | Kiểm tra kết nối provider |
| 5.1.4 | `_stash_provider_fields()` | Lưu tạm các trường cấu hình provider |
| 5.1.5 | `_apply_provider_fields()` | Áp dụng các trường cấu hình provider |
| 5.1.6 | Model List Widget | Hiển thị danh sách models (enable/disable, chọn default) |

### 5.2 Connectors (MCP) — Kết Nối

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 5.2.1 | `_add_mcp_server()` | Thêm MCP server mới |
| 5.2.2 | `_edit_mcp_server()` | Sửa MCP server |
| 5.2.3 | `_delete_mcp_server()` | Xóa MCP server |
| 5.2.4 | `_test_mcp_connection()` | Kiểm tra kết nối MCP |
| 5.2.5 | MS365 Connector | Kết nối Microsoft 365 (tự động khi đăng nhập) |
| 5.2.6 | CAD/CAE Connectors | Kết nối CAD/CAE tools |

### 5.3 Parameters — Tham Số

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 5.3.1 | `attach_tokens` | Giới hạn token cho attachments |
| 5.3.2 | `attach_files` | Giới hạn số file attachments |
| 5.3.3 | `struct_nodes` | Giới hạn nodes cho GraphRAG |
| 5.3.4 | `struct_edges` | Giới hạn edges cho GraphRAG |

### 5.4 Model Routing — Định Tuyến Model

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 5.4.1 | `routing_mode` | Chế độ routing (Off/Auto/Manual) |
| 5.4.2 | `routing_policy` | Chính sách routing |
| 5.4.3 | `routing_min_gain` | Threshold tối thiểu để chuyển model |
| 5.4.4 | `routing_timeout` | Timeout xác nhận routing |
| 5.4.5 | `routing_interval` | Khoảng thời gian đánh giá lại |
| 5.4.6 | `routing_concurrency` | Số lượng request đồng thời per provider |
| 5.4.7 | `routing_judge` | Model dùng để đánh giá routing |

### 5.5 General — Chung

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 5.5.1 | Language Picker | Chọn ngôn ngữ (EN/VI/JP) |
| 5.5.2 | `tray_chk` | Minimize to tray thay vì đóng |
| 5.5.3 | `notify_chk` | Thông báo khi task hoàn thành |
| 5.5.4 | `_save()` | Lưu tất cả cài đặt |

---

## 🔹 6. 📜 HISTORY SIDEBAR (Thanh Lịch Sử Bên Trái)

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 6.0.1 | `refresh()` | Làm mới danh sách hội thoại |
| 6.0.2 | `set_view_state(session_id, running_ids)` | Đánh dấu hội thoại hiện tại + đang chạy |
| 6.0.3 | `set_project_filter(project_id)` | Lọc theo dự án |
| 6.0.4 | `_open_chat()` | Mở hội thoại khi click |
| 6.0.5 | `_context_menu()` | Menu chuột phải (Pin/Unpin, Rename, Delete) |
| 6.0.6 | `_bulk_delete_menu()` | Menu xóa hàng loạt |
| 6.0.7 | `_confirm_and_delete_selected()` | Xác nhận và xóa các hội thoại đã chọn |
| 6.0.8 | `new_chat(kind)` | Tạo hội thoại mới |
| 6.0.9 | `collapse_requested()` | Thu nhỏ sidebar |
| 6.0.10 | `expand_requested()` | Mở rộng sidebar |

---

## 🔹 7. 🧩 CÁC CHỨC NĂNG TOÀN CẦU (Global)

### 7.1 MainWindow (app.py)

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 7.1.1 | `_build_topbar()` | Xây dựng thanh trên cùng (User name, Settings, Language) |
| 7.1.2 | `_build_nav_rail()` | Xây dựng thanh điều hướng bên trái |
| 7.1.3 | `_toggle_nav()` | Thu/mở nav rail (icon-only ↔ full) |
| 7.1.4 | `_apply_nav_labels()` | Áp dụng labels cho nav items |
| 7.1.5 | `_ensure_page(row)` | Xây dựng page lười (lazy loading) |
| 7.1.6 | `_refresh_history()` | Làm mới history của tất cả panes |
| 7.1.7 | `_on_scheduled_task_done()` | Thông báo khi scheduled task hoàn thành |
| 7.1.8 | `_notify_task()` | Thông báo khi task hoàn thành |
| 7.1.9 | `_on_projects_changed()` | Khi danh sách dự án thay đổi |
| 7.1.10 | `_on_pane_turn_finished()` | Khi turn trong pane hoàn thành |
| 7.1.11 | `_open_settings()` | Mở dialog cài đặt |
| 7.1.12 | `_fit_to_screen()` | Tự động fit cửa sổ theo màn hình |
| 7.1.13 | Toast notifications | Hiển thị thông báo toast |
| 7.1.14 | System Tray | Minimize to tray, tray notifications |

### 7.2 Skills Manager

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 7.2.1 | `_open_skills_manager()` | Mở Skill Manager |
| 7.2.2 | `seed_library_skills()` | Gieo skills mặc định |
| 7.2.3 | `prune_seeded_builtins()` | Dọn dẹp skills built-in |

### 7.3 Welcome Dialog

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 7.3.1 | `maybe_show_welcome()` | Hiển thị dialog chào mừng lần đầu |

### 7.4 i18n (Đa Ngôn Ngữ)

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 7.4.1 | `tr(key)` | Dịch chuỗi theo ngôn ngữ hiện tại |
| 7.4.2 | `set_language(lang)` | Đặt ngôn ngữ |
| 7.4.3 | `get_language()` | Lấy ngôn ngữ hiện tại |
| 7.4.4 | `on_language_changed(callback)` | Đăng ký callback khi ngôn ngữ thay đổi |

### 7.5 Task Scheduler (Nền)

| # | Tên Hàm / Chức Năng | Mô Tả |
|---|---------------------|--------|
| 7.5.1 | `task_finished` signal | Khi scheduled task hoàn thành |
| 7.5.2 | `history_ready` signal | Khi session của task sẵn sàng |
| 7.5.3 | `running_session_ids()` | Lấy danh sách session đang chạy |

---

## 📌 TỔNG KẾT

| Navigation Item | Số Hàm/Chức Năng |
|----------------|:-:|
| 📊 Dashboard | ~10 |
| 📅 Schedule Task | ~25 |
| 🏠 Workspace → Projects | ~8 |
| 🏠 Workspace → Cowork | ~34 |
| 🏠 Workspace → Co4E | ~36 |
| 🏠 Workspace → Folder | ~22 |
| 🏠 Workspace → Graph RAG | ~16 |
| 📊 Monitoring | ~20 |
| ⚙️ Settings | ~25 |
| 📜 History Sidebar | ~10 |
| 🌐 Global Functions | ~15 |
| **TỔNG CỘNG** | **~221** |

> **Lưu ý:** Đây là danh sách các hàm/chức năng ở cấp UI và business logic chính. Các hàm core (providers, MCP, worker, security…) nằm ở tầng dưới và được gọi bởi các hàm UI ở trên.