# BÁO CÁO KẾT QUẢ — TEAM HOA: EPIC R05, R06, R07, R08 (phần Team Hoa)

* **Dự án**: Cowork Local (Cowork-Local BamBOO)
* **Team**: 🟢 Team Hoa — Workspace, Filesystem, Scheduling & Tool Registry
* **Nhánh**: `feature/teamhoa/r05-r08` (tạo từ `origin/feature/deltateam/refactor-plan`, có sẵn nền R01/R03/R04 của Team Duy; đổi tên từ `feature/teamhoa/r05-r06` sau khi gộp thêm R07/R08)
* **Thời gian thực hiện**: 21/08/2026 21:40 → 27/08/2026 20:52
* **Ngày báo cáo**: 27/08/2026 (bản gộp, thay thế `BaoCao_TeamHoa_R05_R06.md` và `BaoCao_TeamHoa_R07_R08.md`)
* **Tài liệu gốc**: `Feature_Architecture_Proposal.md`, `Refactoring_Checklist.md`, `plan.md`

---

## 1. Tóm tắt điều hành

Hoàn tất **toàn bộ 19/19 task thuộc phạm vi Team Hoa** trên 4 EPIC: **R05** (Tool, MCP & Connector Policy), **R06** (Workspace, Filesystem & History Isolation), **R07** (Scheduling & Workflow Runtime), **R08** (UI/Application Separation — phần Team Hoa, T11→T14).

| Chỉ số | Kết quả |
| :--- | :--- |
| Task hoàn thành | **19/19** (R05: 5, R06: 5, R07: 5, R08: 4 — không tính R07-T06/R08-T01→T10 thuộc Team Duy/Team Nam) |
| File thay đổi | 92+ (phần lớn file mới) |
| Test cuối cùng | **377 pass / 4 fail** (xem tiến trình chi tiết ở mục 4) |
| CASAN Check 3 (`scripts/check_imports.py`) | **PASS** — 0 Qt import trong `domain/`, `application/` |
| File production > 400 dòng (file mới) | **0** — lớn nhất `presentation/graph/graph_renderer.py` 391 dòng |
| `python -c "import cowork_local.app"` | **OK** sau mọi task |

**3 lỗi thật phát hiện và sửa**, **1 quyết định kiến trúc đổi so với plan gốc (xác nhận bằng thực nghiệm)** — chi tiết mục 5.

---

## 2. Kết quả theo từng EPIC

### 🔹 EPIC R05 — Tool, MCP & Connector Policy (5/5)

| Task | Sản phẩm | Ghi chú |
| :--- | :--- | :--- |
| R05-T01/T02 | `domain/tools/{tool_descriptor,tool_registry}.py`, `infrastructure/filesystem/{file_tools,command_tools,fetch_tools}.py` | Tách if/elif dispatcher của `core/tools.py`; `core/tools.py` còn lại là shim strangler-fig (re-export `ToolContext`/`ToolError`, dispatch qua dict), 566 ➔ 291 dòng. |
| R05-T03 | `application/conversations/tool_policy_gateway.py::ToolPolicyGateway` | Thay 2 chỗ check hardcode riêng biệt (`chat_agent.py`, `code_agent.py`) bằng 1 lookup capability chung. |
| R05-T04 | Sửa `core/chat_agent.py`, `core/mcp_client.py` | **Thay đổi hành vi có chủ đích** — xem mục 5, Lỗi 1. |
| R05-T05 | `infrastructure/mcp/mcp_source_manager.py::McpToolSourceManager` | Tách lifecycle connection MCP khỏi `state.py::AppContext`. |

### 🔹 EPIC R06 — Workspace, Filesystem & History Isolation (5/5)

| Task | Sản phẩm | Ghi chú |
| :--- | :--- | :--- |
| R06-T01 | `domain/workspaces/workspace_session.py::WorkspaceSession` | Snapshot bất biến (project_id/workspace_root/sandbox_dir/allowed_paths) + `is_allowed(path)`. |
| R06-T02 | `infrastructure/persistence/json/{atomic_write,workspace_repository_impl,conversation_repository_impl}.py` | **Sửa bug thật** — xem mục 5, Lỗi 2. |
| R06-T03 | `infrastructure/filesystem/execution_workspace.py::ExecutionWorkspace` | Đặt tên cho quy ước `.scratch` đã có sẵn. |
| R06-T04 | Sửa `ui/chat_panel.py` | **Sửa race condition thật** — xem mục 5, Lỗi 3. |
| R06-T05 | `application/workspaces/file_workspace_service.py::FileWorkspaceService` | Seam cho File Explorer/AI Editor gọi `execute_tool` giống agent — **chưa có call site thật lúc R06 xong; đã nối dây ở R08-T12** (xem mục 5). |

### 🔹 EPIC R07 — Scheduling & Workflow Runtime (5/5, phạm vi Team Hoa)

| Task | Sản phẩm | Ghi chú |
| :--- | :--- | :--- |
| R07-T01 | `infrastructure/persistence/json/task_repository_impl.py::TaskRepository` | Bọc CRUD của `core/tasks.py`. **Sửa bug thật**: `save_task` trước đây ghi không atomic — cùng lớp bug đã sửa ở R06-T02. |
| R07-T02 | `domain/tasks/schedule_calculator.py::ScheduleCalculator` | Tách "schedule math" (cron/interval/daily/weekly/monthly + holiday exclusion) thành pure Python, trước đây **0 test**, giờ có 14 test. |
| R07-T03 | `infrastructure/qt/qt_scheduler_clock.py::QtSchedulerClock` | Bọc `QTimer` sau 1 interface nhỏ, inject qua `clock=`. **Đổi vị trí so với plan gốc** — xem mục 5. |
| R07-T04 | `application/scheduling/task_application_service.py::TaskApplicationService` | Gom CRUD + luật kéo-thả Kanban (`move_to_status`). |
| R07-T05 | `application/scheduling/ai_task_planner_service.py::AiTaskPlannerService` | Seam cho `plan_tasks`/`import_tasks`. |

*(R07-T06 `Co4EWorkflowService` là việc Team Nam — không đụng.)*

### 🔹 EPIC R08 — UI/Application Separation (4/4, phạm vi Team Hoa: T11→T14)

`presentation/` **chưa tồn tại** trước task này — Team Hoa tạo cấu trúc lần đầu.

| Task | God file gốc | Tách thành |
| :--- | :--- | :--- |
| R08-T11 | `ui/schedule_task_tab.py` (795 dòng) | `presentation/scheduling/{kanban_board_widget,calendar_view_widget,ai_task_creator_dialog,ai_task_import_dialog,run_history_dialog}.py` + shell |
| R08-T12 | `ui/folder_tab.py` (1587 dòng — lớn nhất) | `presentation/folder/{workspace_file_tree,document_preview_manager,code_editor,office_document_renderer,ai_file_editor_dialog,ai_edit_model_resolver,ai_edit_pipeline}.py` + shell |
| R08-T13 | `ui/dashboard_tab.py` (437 dòng) | `presentation/dashboard/{token_usage_card_widget,usage_chart_widget,habits_widget}.py` + shell, `application/monitoring/dashboard_query_service.py` |
| R08-T14 | `ui/structure_graph_view.py` (1035 dòng) | `presentation/graph/{graph_scene_items,graph_renderer,graph_messages_view,graph_qa_widget}.py` + shell |

*(R08-T01→T10 thuộc Team Duy/Team Nam — không đụng.)* Mỗi god-file cũ chỉ có 1-2 nơi khởi tạo thật (`app.py`, `ui/workspace_tab.py`) nên đã **sửa thẳng import site** và **xoá hẳn file `ui/*.py` cũ** thay vì giữ shim (khác `core/tools.py` ở R05, có hàng chục call site).

---

## 3. Kiến trúc sau refactor

```text
presentation/            (MỚI ở R08 — Team Hoa tạo cấu trúc lần đầu)
      scheduling/  {kanban_board_widget, calendar_view_widget,
                    ai_task_creator_dialog, ai_task_import_dialog,
                    run_history_dialog, schedule_task_tab}.py
      folder/      {workspace_file_tree, document_preview_manager, code_editor,
                    office_document_renderer, ai_file_editor_dialog,
                    ai_edit_model_resolver, ai_edit_pipeline, folder_tab}.py
      dashboard/   {token_usage_card_widget, usage_chart_widget,
                    habits_widget, dashboard_tab}.py
      graph/       {graph_scene_items, graph_renderer, graph_messages_view,
                    graph_qa_widget, structure_graph_view}.py
      shared/      web_engine_support.py (HAS_WEB_ENGINE dùng chung)
      │
      ▼
application/   conversations/tool_policy_gateway.py        ← ALLOW/CONFIRM cho mọi tool call (R05)
               workspaces/{file_workspace_service, file_preview_helpers,
                           ai_edit_output, graph_index_service}.py         (R06, R08)
               scheduling/{task_application_service, ai_task_planner_service}.py   (R07)
               monitoring/dashboard_query_service.py                       (R08)
      │        (100% pure Python — check_imports.py chặn import Qt)
      ▼
domain/        tools/{tool_descriptor,tool_registry}.py     ← capability + catalogue (R05)
               workspaces/workspace_session.py              ← snapshot workspace bất biến (R06)
               tasks/schedule_calculator.py                 ← due-time/cron math thuần Python (R07)
      ▲
infrastructure/ filesystem/{file_tools,command_tools,fetch_tools,tool_context,execution_workspace}.py  (R05/R06)
                mcp/mcp_source_manager.py                   ← lifecycle connection MCP (R05)
                persistence/json/{atomic_write,workspace_repository_impl,
                                   conversation_repository_impl,task_repository_impl}.py  (R06/R07)
                qt/qt_scheduler_clock.py                    ← QTimer đằng sau 1 interface nhỏ (R07)
```

**Nguyên tắc di trú xuyên suốt cả 4 EPIC (ADR-001 mục 4, tiếp nối cách Team Duy làm ở R04)**: **không viết lại engine**. `core/tools.py::execute_tool`, `core/chat_agent.py::run_cowork`, `core/tasks.py`, `core/task_scheduler.py`, `core/task_executors.py` vẫn là engine bên dưới — tầng mới chỉ sở hữu phần từng nằm rải rác/hardcode trong widget hoặc dispatcher. `pytest` xanh liên tục giữa các bước, chạy full suite sau MỖI task.

**Riêng ở R08**: khi 1 file bị tách vượt 400 dòng dù đã theo đúng mapping gốc, đã tách thêm file phụ theo kiểu **composition** (class phụ nhận `owner` là widget chính) thay vì service riêng — ví dụ `run_history_dialog.py`, `office_document_renderer.py`, `ai_edit_pipeline.py`, `ai_edit_model_resolver.py`, `graph_messages_view.py`. Đây là split kỹ thuật để đạt giới hạn LOC, không phải ranh giới tầng kiến trúc.

---

## 4. Bằng chứng kiểm thử

### Tiến trình test qua từng EPIC

| Mốc | Tổng pass | Ghi chú |
| :--- | ---: | :--- |
| Sau R05+R06 | 283 (/287, 4 fail) | +41 unit test + 2 integration test (Qt offscreen thật) |
| Sau R07 | 328 | +45 test mới (task repo, schedule calculator, Qt clock, task/AI-planner services) |
| Sau R08 | **377** | +49 test mới (4 widget split, mỗi cái có unit + integration Qt offscreen) |

**4 fail cuối cùng — cùng 1 baseline có sẵn từ trước, xuyên suốt cả 4 EPIC, không phải do Team Hoa**:
* `tests/test_config_security.py` × 2 (EPIC R02/Team Nam — `config.py` hardcode `sandbox_pw`)
* `tests/unit/test_routing_wiring.py` × 2 (môi trường máy này có Ollama/llama3.1 thật, khác giả định "fresh install" của test)

### Đối chiếu Definition of Done

| # | Tiêu chí | Kết quả |
| :--- | :--- | :--- |
| 1 | Mọi file mới < 400 dòng | ✅ Lớn nhất: `presentation/graph/graph_renderer.py` 391 dòng |
| 2 | 0 import Qt trong `domain/`, `application/` | ✅ `check_imports.py` PASS |
| 3 | Comment tiếng Anh giải thích lý do ở mọi khối sửa/mới | ✅ |
| 4 | Có unit/contract/integration test, verify bằng chạy thật | ✅ +90 test mới sau R05/R06 lên tới 377; mọi widget Qt test bằng offscreen thật, không double |
| 5 | Không hồi quy | ✅ 377/381 pass — 4 fail cùng 1 baseline có sẵn, không đổi qua 4 EPIC |
| 6 | Ghi Start/End vào Checklist | ✅ 19 task đã tick kèm mốc thời gian thật |
| 7 | Cổng CASAN (`run_quality_gate.py`, R10-T02) | ⚠️ Chưa viết (thuộc R10, chưa tới lượt) — Check 3 đã PASS |

---

## 5. Lỗi thật phát hiện & quyết định kiến trúc

### 🔴 Lỗi 1 (R05-T04) — Tool MCP/Connector chạy hoàn toàn không qua permission gate

`core/chat_agent.py::run_cowork` có 2 nhánh dispatch tool call: built-in đi qua gate xác nhận khi Settings bật "confirm before running commands"; nhánh `extra_tools` (mọi tool từ MCP server hoặc Connector) gọi thẳng `extra_executor(name, args)` **không qua bước xác nhận nào**. Đây không phải khác biệt thiết kế — không có ghi chú, không có toggle riêng.

*Sửa*: mọi `extra_tools` gắn `ToolCapability` mặc định bảo toàn (`WRITE|EXECUTE|NETWORK`), đi qua CÙNG `ToolPolicyGateway` với built-in tools. **Thay đổi hành vi người dùng sẽ thấy**: tool MCP/connector giờ hỏi xác nhận khi "confirm before running commands" bật. Test: `tests/unit/test_cowork_extra_tool_policy.py`.

### 🟠 Lỗi 2 (R06-T02, R07-T01) — Ghi file không atomic ở 3 nơi

`core/projects.py::save_project`, `core/history.py::save_conversation/rename_conversation/set_pinned` (R06), và `core/tasks.py::save_task` (R07) đều từng dùng `path.write_text(json.dumps(...))` trần — crash giữa lúc ghi để lại file JSON hỏng, và hàm `load_*` tương ứng coi file hỏng như "không tồn tại" → **mất project/hội thoại/task âm thầm, không báo lỗi**. Cả 4 điểm ghi giờ qua `infrastructure/persistence/json/atomic_write.py::write_json` (temp file + `os.replace`). Có test giả lập crash giữa lúc ghi xác nhận file cũ không bị hỏng, cho cả 2 đợt sửa.

### 🟡 Lỗi 3 (R06-T04) — Turn chạy ngầm lưu nhầm lịch sử vào project khác

`ui/chat_panel.py::_persist_session` gọi `save_conversation(self.ctx.config.history_dir(), ...)`, đọc `config._project_history_dir` — field dùng chung bị `ui/workspace_tab.py::_load_current` ghi đè mỗi lần đổi project. Một turn chạy ngầm ở project A hoàn tất SAU khi user đã chuyển sang project B thì bị lưu nhầm vào lịch sử của B.

*Sửa*: thêm `"home_history_dir"` vào dict `ctx` mỗi turn, chụp giá trị tại lúc submit thay vì đọc sống lúc lưu. Test Qt offscreen thật: `tests/integration/test_history_dir_race.py`.

### 🔵 Quyết định kiến trúc (R07-T03) — `platform/qt/` đè lên module chuẩn `platform` của Python

Plan gốc đặt tên `platform/qt/qt_scheduler_clock.py`. Thực nghiệm trước khi viết:

```bash
cd <repo_root> && python -c "import cowork_local; import platform; print(platform.system())"
```

Sau khi tạo `platform/__init__.py`, lệnh trên báo lỗi `AttributeError: module 'platform' has no attribute 'system'` — bất cứ khi nào repo root nằm trực tiếp trên `sys.path` (không qua `__main__.py`'s parent-dir fixup), `import platform` phân giải nhầm vào package cục bộ. `core/windows_sandbox_vm.py`/`core/appcontainer_sandbox.py` đều `import platform`.

*Sửa*: chuyển sang `infrastructure/qt/qt_scheduler_clock.py` (không tạo package `platform/` mới) — đúng layer, cùng cấp `infrastructure/{filesystem,mcp,persistence,providers,telemetry}/`. Verify lại: PASS.

### Nối dây `FileWorkspaceService` (R06-T05 → R08-T12)

Báo cáo R06 để lại nợ: `FileWorkspaceService` (R06-T05) chưa có call site thật. Xác nhận lại bằng grep trước R08-T12: đúng 0 occurrence trong `ui/folder_tab.py`. Khi tách `document_preview_manager.py` (R08-T12), mọi điểm ghi text thuần (`save`, `create_new_file`, `write_content`) chuyển sang gọi `FileWorkspaceService.write_file` — dùng `WorkspaceSession.unscoped(...)` vì Folder Explorer duyệt bất kỳ thư mục nào, không giới hạn 1 project sandbox. Nhánh ghi `.pptx` (binary) vẫn giữ nguyên đường cũ.

**Tác dụng phụ có lợi**: `infrastructure/filesystem/file_tools.py::write_file` đã có sẵn cảnh báo cú pháp Python và tự build `.xlsx` thật từ text — 2 hành vi này **trước đây không tồn tại** trên đường ghi cũ của `folder_tab.py`, giờ được hưởng miễn phí.

---

## 6. Cải thiện phụ (không nằm trong yêu cầu task)

| Cải thiện | Ảnh hưởng |
| :--- | :--- |
| `McpServerConnection.is_alive()` (R05, `core/mcp_client.py`) | Cho `McpToolSourceManager` biết một connection cached đã chết để khởi động lại. |
| `domain/tasks/schedule_calculator.py` có bộ test riêng (R07) | `core/tasks.py` tự nhận "Qt-free, unit-testable" nhưng **0 test tồn tại** cho cron/interval/holiday-exclusion trước R07-T02. Giờ 14 test. |
| `AiEditModelResolver.routed_provider`/`.routed_model` (R08-T12, property public mới) | Cần thêm để giữ `tests/integration/test_routing_surfaces.py`'s 2 test AI-Edit routing sau khi lớp routing chuyển từ `FolderTab` sang `AiEditModelResolver` — tránh hồi quy 1 test có từ EPIC R03. |

---

## 7. Còn nợ & cần quyết định

| # | Nội dung | Người quyết |
| :--- | :--- | :--- |
| 1 | **Xung đột quy hoạch thư mục `infrastructure/persistence/json/atomic_write.py`** (R06) với `atomic_json_file.py` do Team Nam quy hoạch ở R02-T01 — chưa có xung đột file thật, cần xác nhận hợp nhất hay giữ 2 module song song. | Team Nam |
| 2 | **Xung đột quy hoạch thư mục `application/monitoring/`** (R08-T13, `dashboard_query_service.py`) — quy hoạch cho Team Nam ở R08-T07→T10, nhưng plan gốc lại đặt file Dashboard vào đúng thư mục này. Chưa có xung đột file thật (thư mục trống trước đó). | Team Nam |
| 3 | **`WorkspaceRepository`/`ConversationRepository` (R06) vẫn chưa có call site sản xuất thật** — R08-T12 chỉ nối `FileWorkspaceService`, chưa đụng 2 repository kia. | Chưa có EPIC nào nhận |
| 4 | **AI-Edit pipeline (`ai_edit_pipeline.py`) và Graph Q&A ask-flow (`graph_qa_widget.py::_ask`) chưa có test end-to-end thật** — cả 2 chạy trên `AgentWorker` (QThread) thật, và **vốn dĩ đã không có test nào trước khi refactor** (xác nhận bằng grep). | Có thể thuộc phạm vi R10 Testing Pyramid |
| 5 | **Dev tooling chưa cập nhật đường dẫn cũ**: `tools/check_controls_alive.py`, `tools/capture_screens.py`, `tools/build_audit_page.py`, `docs/screens/*.json`, `docs/ui-audit*.html` vẫn tham chiếu `ui/schedule_task_tab.py`/`ui/folder_tab.py`/`ui/dashboard_tab.py`/`ui/structure_graph_view.py` (không còn tồn tại). Không nằm trong `tests/`, không ảnh hưởng CI. | Chưa quyết định người phụ trách |

---

## 8. Phạm vi chưa kiểm thử

* **R05-T04 (gate cho MCP/connector) chưa test với MCP server thật** — dùng `ToolSpec` giả, chưa thử `core/mcp_client.py::McpServerConnection` chạy subprocess thật.
* **`McpToolSourceManager` (R05-T05) chưa test với subprocess MCP thật** — dùng `_FakeConnection`.
* **`presentation/folder/ai_edit_pipeline.py`** (toàn bộ luồng plan → edit → apply/discard qua `AgentWorker` streaming) — chỉ verify bằng import/construction, chưa gửi instruction qua worker thật.
* **`presentation/graph/graph_qa_widget.py::_ask`** — tương tự, chỉ test phần không cần AgentWorker thật.
* **`office_document_renderer.py`'s PDF/LibreOffice conversion path** — chưa xác nhận kịch bản fallback trên máy không có QtPdf/LibreOffice bằng test thật.
* **Đã mở app thật bằng `python -c "import cowork_local.app"` sau mỗi task** để xác nhận không lỗi import — **chưa** mở app GUI thật, thao tác tay qua toàn bộ 4 màn hình đã tách để xác nhận trải nghiệm người dùng cuối.

---

## 9. Việc kế tiếp của Team Hoa

Toàn bộ 4 EPIC thuộc phạm vi Team Hoa (R05, R06, R07, R08 phần T11→T14) đã **hoàn tất**. Các bước còn lại không thuộc EPIC riêng của Team Hoa nữa:

| Việc | Điều kiện |
| :--- | :--- |
| Checkpoint 2 (Services & Sub-widgets, 28/08) | Cần Team Duy (R08-T01→T06) và Team Nam (R08-T07→T10) xong phần UI split của họ |
| CASAN Check 2 (Modularity/LOC, Team Hoa chủ trì, 30/08) | `scripts/check_loc.py` chưa tồn tại (thuộc R10-T02, Team Duy) |
| Giải quyết mục 7 #1, #2 | Khi Team Nam bắt đầu R02-T01 và R08-T07→T10 |
| R10 (Testing, Packaging & Contributor Experience) | Team Duy chủ trì, chờ 3 team hoàn tất |

---

## 10. Lịch sử commit

| Commit | Nội dung |
| :--- | :--- |
| `ae4fe72` | feat(R05): tool capability registry, unified policy gateway, MCP lifecycle manager |
| `cf542b7` | feat(R06): workspace session snapshot, atomic persistence, history-dir race fix |
| `69ab8e1` | feat(R07): task repository, schedule calculator, Qt clock adapter, task/AI-planner services |
| `0e51356` | feat(R08): split ScheduleTaskTab, FolderTab, DashboardTab, StructureGraphView |
| *(gộp báo cáo)* | docs(refactor): merge Team Hoa reports R05→R08 into one; rename branch to `feature/teamhoa/r05-r08` |
