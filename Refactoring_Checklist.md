# COWORK LOCAL - BẢNG CHECKLIST TIẾN ĐỘ TÁI CẤU TRÚC (2026)
## (REFACTORING & MIGRATION PROGRESS TRACKER)

* **Dự án**: Cowork Local (Cowork-Local BamBOO)
* **Thời gian thực hiện**: 21/08/2026 ➔ 31/08/2026
* **Đội ngũ phụ trách**: 
  - 🔵 **Team Duy** (Core AI, Routing, Turn Runtime & Testing Pyramid - Tech Lead)
  - 🟣 **Team Nam** (Automation Workflows, Co4E, Monitoring & Shell Governance)
  - 🟢 **Team Hoa** (Workspace, Filesystem, Scheduling & Tool Registry)
* **Tài liệu thiết kế kiến trúc gốc**: `Feature_Architecture_Proposal.md`

> [!IMPORTANT]
> ### 📝 QUY ĐỊNH BẮT BUỘC KHI CODE & GHI NHẬN TIẾN ĐỘ (MANDATORY RULES):
> 1. **In-Code Comments in English (Bắt buộc comment tiếng Anh ở mọi dòng/khối code sửa đổi)**:
>    - Mỗi khi sửa đổi hoặc viết mới bất kỳ dòng code nào, lập trình viên **bắt buộc phải thêm comment bằng tiếng Anh** giải thích rõ mục đích xử lý, lý do kiến trúc và mối quan hệ giữa các tầng.
>    - Tuyệt đối không để code không có chú thích, đặc biệt tại các điểm chuyển đổi DTO, seams và xử lý ngoại lệ.
> 2. **Task Start / End Timestamps (Ghi nhận chính xác ngày giờ bắt đầu và hoàn tất)**:
>    - Khi bắt đầu làm một task ➔ Điền mốc thời gian: `Start: YYYY-MM-DD HH:mm`.
>    - Khi task hoàn tất (unit test pass 100%) ➔ Điền mốc thời gian: `End: YYYY-MM-DD HH:mm` và tích chọn `[x]`.

---

## 📌 PHẦN 1: CHECKLIST CHI TIẾT THEO 10 EPIC (R01 ➔ R10)

### 🔹 EPIC R01: Architecture Foundation & Characterization (Nền Tảng Kiến Trúc & Test Bảo Vệ)
* **Team chịu trách nhiệm**: 🔵 **Team Duy** (Chủ trì ADR & Test Doubles) + Phối hợp cả 3 team
* **Mục tiêu**: Khóa DTO, dựng fakes/test doubles chạy offline không phụ thuộc Qt/mạng, thiết lập script chặn vi phạm kiến trúc.

- [ ] **R01-T01 (Team Duy)**: Viết Architecture ADR định rõ ranh giới các tầng ➔ `docs/architecture/ADR-001-layered-architecture.md`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R01-T02 (Team Duy)**: Xây dựng `FakeProvider` và `FakeToolExecutor` chạy offline từ `providers/base.py` ➔ `tests/fakes/fake_provider.py` & `tests/fakes/fake_tool_executor.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R01-T03 (Team Duy)**: Viết script quét tĩnh chặn code mới trong `domain/` và `application/` import `PySide6` ➔ `scripts/check_imports.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R01-T04 (Team Duy)**: Viết Characterization Tests cho `core/chat_agent.py::run_cowork` ➔ `tests/characterization/test_run_cowork.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R01-T05 (Team Duy)**: Lập danh mục và phân loại mã nguồn dormant/dead code ➔ `docs/architecture/dormant-code.md`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*

---

### 🔹 EPIC R02: Configuration, Secrets & Persistence (Cấu Hình Atomic & Bảo Mật Keyring)
* **Team chịu trách nhiệm**: 🟣 **Team Nam** (Chủ trì)
* **Mục tiêu**: Xóa bỏ untyped global `config.py`, cài đặt `AtomicJsonFile` chống hỏng file và lưu trữ API Key/Token vào OS Keyring.

- [ ] **R02-T01 (Team Nam)**: Xây dựng module `AtomicJsonFile` ghi tệp an toàn (tmp file + fsync + atomic replace) ➔ `infrastructure/persistence/json/atomic_json_file.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R02-T02 (Team Nam)**: Refactor `config.py::AppConfig` sử dụng `AtomicJsonFile` ➔ `infrastructure/config/config_repository.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R02-T03 (Team Nam)**: Xây dựng Typed Settings Facade (`ProviderSettings`, `RoutingSettings`) ➔ `infrastructure/config/settings_facade.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R02-T04 (Team Nam)**: Định nghĩa interface `SecretStore` và cài đặt `KeyringAdapter` ➔ `infrastructure/secrets/keyring_adapter.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R02-T05 (Team Nam)**: Di chuyển cấu hình API Key của OpenAI/Anthropic/FPT Gateway sang lưu trữ qua `SecretStore`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R02-T06 (Team Nam)**: Chuẩn hóa JSON schema versioning và recovery policy cho các file data  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*

---

### 🔹 EPIC R03: Model Providers & Routing (Hợp Nhất Nhà Cung Cấp & Bộ Định Tuyến Mô Hình)
* **Team chịu trách nhiệm**: 🔵 **Team Duy** (Chủ trì)
* **Mục tiêu**: Hợp nhất logic routing bị phân tán thành `RoutingApplicationService` độc lập Qt; chuẩn hóa catalog nhà cung cấp.

- [ ] **R03-T01 (Team Duy)**: Xây dựng bộ Contract Tests chuẩn hóa cho các Provider từ `providers/base.py` ➔ `tests/contracts/test_providers.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R03-T02 (Team Duy)**: Xây dựng `ProviderDescriptor` và `ProviderRegistry` tập trung từ `providers/factory.py` ➔ `domain/models/provider_descriptor.py` & `infrastructure/providers/provider_registry.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R03-T03 (Team Duy)**: Xây dựng `RoutingApplicationService` độc lập với Qt từ `core/routing/` ➔ `application/model_routing/routing_application_service.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R03-T04 (Team Duy)**: Di chuyển luồng gọi routing từ `ui/chat_panel.py#L638` sang `RoutingApplicationService`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R03-T05 (Team Duy)**: Di chuyển luồng gọi routing từ `ui/co4e_tab.py` và `ui/folder_tab.py` sang `RoutingApplicationService`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R03-T06 (Team Duy)**: Tách logic ghi nhận token usage ra khỏi Provider, chuyển thành `UsageEventSink` ➔ `infrastructure/telemetry/usage_sink.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*

---

### 🔹 EPIC R04: Agent Runtime & Conversation Application Service (Vòng Đời Turn Chat & Agent Engine)
* **Team chịu trách nhiệm**: 🔵 **Team Duy** (Chủ trì)
* **Mục tiêu**: Đóng gói input turn chat thành `ConversationExecutionRequest` bất biến, điều phối vòng đời qua `ConversationApplicationService` và phát sinh sự kiện `AgentEvent` có định kiểu.

- [ ] **R04-T01 (Team Duy)**: Định nghĩa immutable dataclass `ConversationExecutionRequest` ➔ `domain/agents/conversation_execution_request.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R04-T02 (Team Duy)**: Chuẩn hóa các sự kiện `AgentEvent` (TextChunk, ToolCallStarted, ToolCallResult, Error) ➔ `domain/agents/agent_event.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R04-T03 (Team Duy)**: Xây dựng `ConversationApplicationService` điều phối thực thi từ `core/chat_agent.py` ➔ `application/conversations/conversation_application_service.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R04-T04 (Team Duy)**: Di chuyển `ui/cowork_tab.py::build_job` sang sử dụng `ConversationExecutionRequest`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R04-T05 (Team Duy)**: Di chuyển `core/task_executors.py` sang dùng chung `ConversationApplicationService`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*

---

### 🔹 EPIC R05: Tool, MCP & Connector Policy (Quản Lý Công Cụ, MCP & Cổng Kiểm Soát Quyền)
* **Team chịu trách nhiệm**: 🟢 **Team Hoa** (Chủ trì) + Phối hợp Team Duy
* **Mục tiêu**: Bóc tách monolithic `core/tools.py`, đưa toàn bộ Built-in tools, MCP tools và Connectors qua `ToolPolicyGateway` kiểm tra quyền phân tầng.

- [ ] **R05-T01 (Team Hoa)**: Định nghĩa `ToolDescriptor`, `ToolCapability` (read/write/execute/network) ➔ `domain/tools/tool_descriptor.py` & `domain/tools/tool_registry.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R05-T02 (Team Hoa)**: Tách nhỏ các built-in handlers từ `core/tools.py` ➔ `infrastructure/filesystem/file_tools.py`, `command_tools.py`, `fetch_tools.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R05-T03 (Team Hoa)**: Xây dựng `ToolPolicyGateway` (kiểm tra phân quyền allow/confirm/deny) ➔ `application/conversations/tool_policy_gateway.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R05-T04 (Team Hoa)**: Chuẩn hóa MCP tools từ `core/mcp_client.py` đi qua `ToolPolicyGateway`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R05-T05 (Team Hoa)**: Xây dựng `McpToolSourceManager` quản lý vòng đời tiến trình MCP ➔ `infrastructure/mcp/mcp_source_manager.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*

---

### 🔹 EPIC R06: Workspace, Filesystem & History Isolation (Cô Lập Không Gian Làm Việc & Quản Lý Tệp)
* **Team chịu trách nhiệm**: 🟢 **Team Hoa** (Chủ trì)
* **Mục tiêu**: Xóa bỏ biến toàn cục `state.py::active_project_id`, đóng gói workspace per-turn thành `WorkspaceSession` bất biến, bảo vệ an toàn đường dẫn sandbox.

- [ ] **R06-T01 (Team Hoa)**: Định nghĩa `WorkspaceSession` chứa snapshot project id, workspace root ➔ `domain/workspaces/workspace_session.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R06-T02 (Team Hoa)**: Xây dựng `WorkspaceRepository` từ `core/projects.py` & `ConversationRepository` từ `core/history.py` ➔ `infrastructure/persistence/json/workspace_repository_impl.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R06-T03 (Team Hoa)**: Xây dựng `ExecutionWorkspace` quản lý output/scratch files ➔ `infrastructure/filesystem/execution_workspace.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R06-T04 (Team Hoa)**: Khắc phục race condition trong `ui/workspace_tab.py::_load_current`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R06-T05 (Team Hoa)**: Xây dựng `FileWorkspaceService` xử lý thao tác file cho File Explorer và AI File Editor ➔ `application/workspaces/file_workspace_service.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*

---

### 🔹 EPIC R07: Scheduling & Workflow Runtime (Bộ Lập Lịch & Động Cơ Quy Trình)
* **Team chịu trách nhiệm**: 🟢 **Team Hoa** (Task Scheduling) + 🟣 **Team Nam** (Co4E Workflows)
* **Mục tiêu**: Tách `TaskRepository` và `ScheduleCalculator` khỏi `QTimer` trong `core/task_scheduler.py#L20`; xây dựng `TaskApplicationService` và `Co4EWorkflowService`.

- [ ] **R07-T01 (Team Hoa)**: Tách `TaskRepository` lưu trữ JSON độc lập khỏi `core/tasks.py` ➔ `infrastructure/persistence/json/task_repository_impl.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R07-T02 (Team Hoa)**: Xây dựng `ScheduleCalculator` tính due-time / cron độc lập ➔ `domain/tasks/schedule_calculator.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R07-T03 (Team Hoa)**: Xây dựng `QtSchedulerClock` adapter (tách `TaskScheduler` khỏi `QTimer`) ➔ `platform/qt/qt_scheduler_clock.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R07-T04 (Team Hoa)**: Xây dựng `TaskApplicationService` (Pure Python) điều phối chạy, sao chép, dừng, xóa task ➔ `application/scheduling/task_application_service.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R07-T05 (Team Hoa)**: Xây dựng `AiTaskPlannerService` hỗ trợ tạo / import task bằng AI ➔ `application/scheduling/ai_task_planner_service.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R07-T06 (Team Nam)**: Xây dựng `Co4EWorkflowService` (Pure Python) quản lý định nghĩa và thực thi Co4E từ `core/co4e_run_manager.py` ➔ `application/workflows/co4e_workflow_service.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*

---

### 🔹 EPIC R08: UI/Application Separation (Phân Rã Toàn Diện Các God Widgets)
* **Team chịu trách nhiệm**: **Cả 3 Team** (Mỗi team phụ trách phân hệ của mình)
* **Mục tiêu**: Phân rã các file giao diện khổng lồ (>1.500 dòng) thành các widget chuyên biệt, mỗi file < 400 dòng code.

#### 🔵 Team Duy (Chat UI Hub):
- [ ] **R08-T01**: Tách `ui/chat_panel.py` thành `presentation/chat/chat_history_widget.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R08-T02**: Tách Composer & input box ➔ `presentation/chat/composer_widget.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R08-T03**: Tách Picker file đính kèm ➔ `presentation/chat/attachment_picker.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R08-T04**: Tách Voice/Audio recording ➔ `presentation/chat/audio_recorder_widget.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R08-T05**: Tách Output panel & file watcher ➔ `presentation/chat/chat_output_panel.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R08-T06**: Lắp ráp container `presentation/chat/chat_panel.py` và tối ưu `Floating HelpAgent`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*

#### 🟣 Team Nam (Settings, Monitoring, Co4E & Shell):
- [ ] **R08-T07**: Tách `ui/settings_dialog.py` thành 4 section widgets ➔ `provider_settings_widget.py`, `connector_settings_widget.py`, `routing_settings_widget.py`, `general_settings_widget.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R08-T08**: Tách `ui/monitoring_tab.py` thành 7 tab độc lập (`overview_tab.py`, `sandbox_status_tab.py`, `security_events_tab.py`, `mcp_history_tab.py`, `action_logs_tab.py`, `agent_status_tab.py`, `security_settings_tab.py`)  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R08-T09**: Tách `ui/co4e_tab.py` thành các sub-components ➔ `co4e_canvas_widget.py`, `node_property_panel.py`, `co4e_run_control_widget.py`, `co4e_chat_view.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R08-T10**: Xây dựng `bootstrap.py` (Composition Root) và tách `app.py::MainWindow` (dòng 122) ➔ `presentation/shell/main_window.py`, `tray_manager.py`, `lifecycle_coordinator.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*

#### 🟢 Team Hoa (Workspace, Folder, Scheduling, Dashboard & Graph):
- [ ] **R08-T11**: Tách `ui/schedule_task_tab.py` ➔ `kanban_board_widget.py`, `calendar_view_widget.py`, `ai_task_creator_dialog.py`, `ai_task_import_dialog.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R08-T12**: Tách `ui/folder_tab.py#L350` ➔ `workspace_file_tree.py`, `document_preview_manager.py`, `ai_file_editor_dialog.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R08-T13**: Tách `ui/dashboard_tab.py` ➔ `token_usage_card_widget.py`, `usage_chart_widget.py`, `habits_widget.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R08-T14**: Tách `ui/structure_graph_view.py` ➔ `presentation/graph/structure_graph_view.py` & `graph_qa_widget.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*

---

### 🔹 EPIC R09: Security Runtime, Sandbox & Observability (An Ninh Runtime, Sandbox & Giám Sát)
* **Team chịu trách nhiệm**: 🟣 **Team Nam** (Chủ trì) + Phối hợp Team Duy
* **Mục tiêu**: Phân biệt deterministic rules và AI guardrails, fix toàn bộ circular imports trong security/pricing, chuẩn hóa schema audit logs.

- [ ] **R09-T01 (Team Nam)**: Viết tài liệu chuẩn hóa Security Policy Model ➔ `docs/architecture/security-policy.md`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R09-T02 (Team Nam)**: Xử lý triệt để Circular Import giữa `core/model_pricing.py` và `core/usage_tracker.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R09-T03 (Team Nam)**: Xử lý triệt để Circular Import giữa `core/agent_security.py` và `core/agent_security_alert.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R09-T04 (Team Nam)**: Xây dựng `CanonicalAuditLogger` thống nhất định dạng log từ `core/audit_log.py` ➔ `infrastructure/telemetry/audit_logger.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R09-T05 (Team Nam)**: Xây dựng `MonitoringQueryService` (truy vấn read-only có phân trang) ➔ `application/monitoring/monitoring_query_service.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R09-T06 (Team Nam)**: Chuẩn hóa ma trận năng lực Sandbox trên từng hệ điều hành từ `core/sandbox_manager.py` ➔ `infrastructure/sandbox/sandbox_capabilities.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*

---

### 🔹 EPIC R10: Testing, Packaging & Contributor Experience (Hệ Thống Kiểm Thử & Tài Liệu Đóng Góp)
* **Team chịu trách nhiệm**: 🔵 **Team Duy** (Chủ trì chính - Task trọng tâm của Team Duy)
* **Mục tiêu**: Xây dựng toàn bộ hệ thống test pyramid (unit, contract, integration, headless UI), thiết lập CI Quality Gate tự động, soạn thảo tài liệu Contributor Recipes và thực hiện E2E smoke test trước khi phát hành.

- [ ] **R10-T01 (Team Duy)**: Thiết lập Tháp kiểm thử phân tầng (Unit tests không I/O <0.05s, Contract tests cho Providers/Tools, Integration tests, Fakes library) ➔ `tests/`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R10-T02 (Team Duy)**: Xây dựng Bộ script CI Quality Gate tự động (`scripts/check_imports.py`, `scripts/check_loc.py`, `scripts/audit_security.py`, `scripts/run_quality_gate.py`)  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R10-T03 (Team Duy)**: Cập nhật tài liệu kiến trúc 4 tầng, hướng dẫn setup môi trường & pre-commit hook ➔ `README.md` & `START_CONTRIBUTING.md`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R10-T04 (Team Duy)**: Soạn thảo bộ Contributor Recipes (3 công thức: Thêm Model Provider, Thêm Built-in/MCP Tool, Thêm Màn hình/Widget) ➔ `docs/governance/contributor-recipes.md`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*
- [ ] **R10-T05 (Team Duy)**: Xây dựng bộ kiểm thử khói phát hành (E2E Release Smoke Test qua headless Qt với 5 kịch bản chính) ➔ `tests/e2e/test_smoke.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`*

---

## 📅 PHẦN 2: CHECKLIST TIẾN ĐỘ THEO NGÀY CỦA TỪNG TEAM (21/08 ➔ 31/08)

### 🔵 TEAM DUY (Core AI, Routing, Turn Runtime & Testing Lead)

| Ngày | Task Cần Hoàn Thành | Start Time | End Time | Trạng Thái |
| :--- | :--- | :---: | :---: | :---: |
| **21/08 (T6)** | Khóa DTO `ConversationExecutionRequest`, `AgentEvent`; Xây dựng `FakeProvider`, `FakeToolExecutor` | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **22-23/08 (T7-CN)** | Chuẩn hóa `ProviderDescriptor`, `ProviderRegistry`; Wrap OpenAI, Anthropic, Ollama, FPT Gateway; Viết Contract Tests | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **24/08 (T2)** | Xây dựng `RoutingApplicationService` độc lập Qt; Tách `ComposerWidget` & `AttachmentPicker` | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **25/08 (T3)** | Xây dựng `ConversationApplicationService`; Tách `ChatHistoryWidget` và bubble renderer | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **26/08 (T4)** | Nối stream `AgentEvent` sang Chat History; Tách `AudioRecorderWidget` | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **27/08 (T5)** | Tách `ChatOutputPanel` & File Watcher; Lắp ráp container `ChatPanel` và `Floating HelpAgent` | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **28/08 (T6)** | Xóa copy routing cũ trong `ui/chat_panel.py`; Fix circular import `model_pricing` ↔ `usage_tracker` | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **29/08 (T7)** | Viết suite integration test cho toàn bộ luồng Chat (`tests/integration/test_chat_flow.py`) | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **30/08 (CN)** | 🔍 **Chủ trì CASAN Check 3**: Chạy `python scripts/check_imports.py` đảm bảo 0 import `PySide6` trong domain & application | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **31/08 (T2)** | **Chủ trì EPIC R10**: Viết Contributor Recipes, chạy E2E Smoke Test (`tests/e2e/test_smoke.py`) và merge PR cuối cùng | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |

---

### 🟣 TEAM NAM (Automation Workflows, Co4E, Monitoring & Governance)

| Ngày | Task Cần Hoàn Thành | Start Time | End Time | Trạng Thái |
| :--- | :--- | :---: | :---: | :---: |
| **21/08 (T6)** | Khóa DTO Co4E; Xây dựng `AtomicJsonFile` và `KeyringAdapter` (`SecretStore`) | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **22-23/08 (T7-CN)** | Refactor `config.py` sang `ConfigRepository`; Tách `ProviderSettingsWidget` & `ConnectorSettingsWidget` | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **24/08 (T2)** | Tách 3 tab đầu của Monitoring (`overview_tab.py`, `sandbox_status_tab.py`); Xây dựng `MonitoringQueryService` | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **25/08 (T3)** | Tách 4 tab còn lại của Monitoring (`security_events_tab.py`, `mcp_history_tab.py`,...); Lắp ráp container `MonitoringTab` | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **26/08 (T4)** | Bóc tách `Co4EWorkflowService`; Tách `NodePropertyPanel` & `AgentListPanel` | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **27/08 (T5)** | Tách `Co4ECanvasWidget`, `Co4ERunControlWidget` & `Co4EChatView` | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **28/08 (T6)** | Lắp ráp container `Co4ETab`; Xây dựng `bootstrap.py` (Composition Root) và tách `MainWindow` shell | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **29/08 (T7)** | Fix circular import `agent_security` ↔ `agent_security_alert`; Integration test luồng Co4E & Settings | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **30/08 (CN)** | 🔍 **Chủ trì CASAN Check 1**: Chạy `python scripts/audit_security.py` đảm bảo 0 API Key/Token plaintext | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **31/08 (T2)** | Fix tồn đọng Check 1, cập nhật tài liệu kiến trúc, merge PR cuối | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |

---

### 🟢 TEAM HOA (Workspace, Filesystem, Scheduling & Tool Registry)

| Ngày | Task Cần Hoàn Thành | Start Time | End Time | Trạng Thái |
| :--- | :--- | :---: | :---: | :---: |
| **21/08 (T6)** | Khóa DTO `ToolDescriptor`, `ToolCapability`; Tách `FileTools` từ `core/tools.py` | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **22-23/08 (T7-CN)** | Tách `CommandTools`, `FetchTools`; Tách `TokenUsageCardWidget` & `UsageChartWidget` (Dashboard) | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **24/08 (T2)** | Tách `TaskRepository` & `ScheduleCalculator`; Tách `KanbanBoardWidget` (7 cột trạng thái) | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **25/08 (T3)** | Xây dựng `QtSchedulerClock` adapter (tách khỏi `QTimer`); Tách `CalendarViewWidget` | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **26/08 (T4)** | Xây dựng `TaskApplicationService`; Tách `AiTaskCreatorDialog` & `AiTaskImportDialog` | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **27/08 (T5)** | Tách `WorkspaceFileTree`, `DocumentPreviewManager` & `AiFileEditorDialog` từ `FolderTab` | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **28/08 (T6)** | Tách `StructureGraphView` (GraphRAG); Lắp ráp shell `FolderTab` & `ScheduleTaskTab` | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **29/08 (T7)** | Nối `ToolPolicyGateway` qua MCP Client & Built-in Tools; Integration test Task Scheduler & File Explorer | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **30/08 (CN)** | 🔍 **Chủ trì CASAN Check 2**: Chạy `python scripts/check_loc.py --max-lines 400` đảm bảo 0 file >400 dòng | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **31/08 (T2)** | Fix tồn đọng Check 2, cập nhật README, merge PR cuối | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |

---

## 🚦 PHẦN 3: CHECKLIST CHECKPOINT REVIEW & CƠ CHẾ KIỂM DUYỆT CASAN

### 🛡️ Định nghĩa 5 Chữ Cái CASAN:
- **C - Clean Architecture**: 0 import `PySide6` trong `domain/` và `application/`.
- **A - Atomic Persistence**: 0 plaintext secrets trong JSON/config; dùng `AtomicJsonFile` ghi tệp an toàn.
- **S - Single Responsibility**: 0 file production nào > 400 dòng code (LOC).
- **A - Automated Test Pyramid**: Bộ test phân tầng chạy offline 100% không phụ thuộc network/UI.
- **N - No Regression & Smoke**: Toàn bộ suite test (>81 tests) và E2E Smoke test pass 100%.

### 🔍 Bảng Theo Dõi Các Checkpoints & Cổng Kiểm Duyệt CASAN:

| Thời Điểm | Checkpoint / Cổng Duyệt | Lệnh Kiểm Tra Thực Tế | Tiêu Chí Bắt Buộc | Phụ Trách | Start Time | End Time | Trạng Thái |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| **23/08 (CN - 17:00)** | **Checkpoint 1: Contracts & Fakes** | `pytest tests/contracts tests/fakes` | 100% DTO và Fake Services tạo xong; test pass | Cả 3 Team | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **28/08 (T6 - 17:00)** | **Checkpoint 2: Services & Sub-widgets** | `pytest tests/` | Tách xong 100% God Files; 0 circular import | Cả 3 Team | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **30/08 (CN - 17:00)** | **CASAN Check 1: Security Audit** | `python scripts/audit_security.py` | 0 plaintext secret trong file cấu hình | Team Nam | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **30/08 (CN - 17:00)** | **CASAN Check 2: Modularity (LOC)** | `python scripts/check_loc.py --max-lines 400` | 0 file production nào > 400 dòng code | Team Hoa | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **30/08 (CN - 17:00)** | **CASAN Check 3: Clean Architecture** | `python scripts/check_imports.py` | 0 import `PySide6` trong domain & application | Team Duy | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |
| **31/08 (T2 - 15:00)** | **Final Release E2E Smoke Test** | `pytest tests/e2e/test_smoke.py` | 5 kịch bản end-to-end pass 100% trên `main` | Team Duy & 3 Team | `____-__-__ __:__` | `____-__-__ __:__` | [ ] |

---

## 📋 PHẦN 4: DEFINITION OF DONE (DOD) CHO MỖI PULL REQUEST

Mọi Pull Request của cả 3 team trước khi merge vào nhánh chính cần được đối chiếu checklist sau:

- [ ] **1. Kích thước file (LOC)**: File mới hoặc file sau khi refactor không vượt quá **400 dòng code**.
- [ ] **2. Phụ thuộc kiến trúc (Clean Architecture)**: Không import `PySide6` / Qt trong các module thuộc `domain/` và `application/`.
- [ ] **3. An toàn thông tin (Security)**: API Key / Credential được lưu trữ qua `SecretStore` (Keyring), không lưu cứng hoặc lưu plaintext trong file JSON.
- [ ] **4. Bắt buộc Comment Code bằng Tiếng Anh (English In-Code Comments)**: 100% các dòng hoặc khối code sửa đổi/bóc tách đều có comment tiếng Anh giải thích rõ logic xử lý và lý do kỹ thuật.
- [ ] **5. Ghi nhận thời gian thực hiện (Timestamps)**: Đã điền đầy đủ mốc thời gian `Start: YYYY-MM-DD HH:mm` và `End: YYYY-MM-DD HH:mm` vào `Refactoring_Checklist.md` và PR description.
- [ ] **6. Kiểm thử tự động (Automated Tests)**: Có unit test hoặc contract test đi kèm với tỷ lệ pass 100%. Chạy `pytest` hoàn tất < 3 giây.
- [ ] **7. Không gây lỗi chéo (No Regression)**: Chạy kiểm thử toàn bộ hệ thống không làm hỏng các tính năng hiện hữu.

