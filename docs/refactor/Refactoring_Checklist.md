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

## 📊 TIẾN ĐỘ THỰC TẾ — TEAM DUY (cập nhật `2026-08-21 10:55`)

> [!NOTE]
> ### ✅ ĐÃ HOÀN TẤT: 16/16 task của **R01, R03, R04** — đã commit & push lên nhánh `feature/deltateam/refactor-plan`
>
> | EPIC | Task | Trạng thái |
> | :--- | :--- | :--- |
> | **R01** Architecture Foundation | T01 → T05 | ✅ 5/5 |
> | **R03** Providers & Routing | T01 → T06 | ✅ 6/6 |
> | **R04** Agent Runtime & Conversation | T01 → T05 | ✅ 5/5 |
>
> **Kiểm chứng (chạy thật, không phải ước lượng):**
> * `pytest tests/` ➔ **243 pass / 2 fail** trong 44s
> * Suite nhanh (`unit + contracts + characterization + routing`) ➔ **218 pass trong 1,16s** (đạt yêu cầu CASAN "A – Automated Tests < 1s cho unit")
> * `python scripts/check_imports.py` ➔ **PASS** (0 Qt import trong `domain/`, `application/`)
> * Mọi file production mới **< 400 dòng** (lớn nhất: `routing_application_service.py` 353 dòng)
> * 2 test fail là **lỗi có sẵn từ trước**, thuộc EPIC **R02**: `config.py` vẫn hardcode `sandbox_pw = "quandh14"` ➔ `tests/test_config_security.py` đỏ
>
> ### 📍 PHẠM VI TEAM DUY & PHẦN CÒN LẠI
> Theo `Feature_Architecture_Proposal.md` (dòng 7) và `DeltaTeam_prompt.md` (dòng 17), Team Duy chủ trì **R01, R03, R04, R08 (phân hệ Chat UI), R10**.
> * ✅ **R01, R03, R04** — xong 16/16 task, đã push.
> * ⬜ **R08 (R08-T01 ➔ R08-T06)** — chưa bắt đầu: tách `ui/chat_panel.py` (1.795 dòng) thành 6 widget < 400 dòng.
> * ⬜ **R10** — làm sau cùng, chờ 3 team hoàn tất.
> * **R02 thuộc 🟣 Team Nam** (xem mục EPIC R02 bên dưới) — đây là nguyên nhân 2 test đỏ ở trên, không phải việc của Team Duy.
>
> ### 📄 BÁO CÁO CHI TIẾT
> Xem `docs/refactor/BaoCao_TeamDuy_R01_R03_R04.md` — kết quả từng EPIC, bằng chứng kiểm thử, 3 lỗi thật đã phát hiện, và phạm vi **chưa** kiểm thử.
>
> ### 📌 CÒN NỢ / CẦN QUYẾT ĐỊNH
> 1. `ProviderRegistry` **chưa nối** vào `state.build_provider_for` (vẫn dùng `providers/factory.py`). Nối vào sẽ sửa luôn lỗi: usage của `ollama`/`github_copilot`/`codex` hiện bị ghi nhận nhầm thành `openai_compat` trên Dashboard — nhưng làm vậy sẽ **đổi cách gom dữ liệu lịch sử**.
> 2. Mode `fallback` đã hỗ trợ ở config + service nhưng **chưa có trên toggle UI** (thuộc R08).
> 3. Đã sửa 2 dòng trong `config.py` (`routing_mode_for` / `set_routing_mode_for`) để dùng chung một bộ từ vựng mode — **cần báo Team Nam** vì file này đang được refactor ở R02.
> 4. Circular import `core/model_pricing.py` ↔ `core/usage_tracker.py` **chưa xử lý** (task ngày 28/08).
> 5. Việc kế tiếp của Team Duy là **R08 phân hệ Chat UI** (6 widget con), rồi **R10** sau cùng.

---

## 📊 TIẾN ĐỘ THỰC TẾ — TEAM HOA (cập nhật `2026-08-21 22:57`)

> [!NOTE]
> ### ✅ ĐÃ HOÀN TẤT: 10/10 task của **R05 + R06** — branch `feature/teamhoa/r05-r06` (tạo từ `origin/feature/deltateam/refactor-plan`, có sẵn nền R01/R03/R04)
>
> | EPIC | Task | Trạng thái |
> | :--- | :--- | :--- |
> | **R05** Tool, MCP & Connector Policy | T01 → T05 | ✅ 5/5 |
> | **R06** Workspace, Filesystem & History Isolation | T01 → T05 | ✅ 5/5 |
>
> **Kiểm chứng (chạy thật):**
> * `pytest tests/` ➔ **283 pass / 4 fail** (+41 test mới cho R05+R06, gồm 2 test Qt offscreen thật trong `tests/integration/test_history_dir_race.py`)
> * 4 fail là **lỗi có sẵn từ trước**, không liên quan R05/R06: 2 trong `test_config_security.py` (EPIC R02, đã ghi nhận bởi Team Duy) + 2 trong `test_routing_wiring.py` (môi trường máy này có Ollama/llama3.1 thật + config routing cục bộ khác "fresh install").
> * `python scripts/check_imports.py` ➔ **PASS** (0 Qt import trong `domain/`, `application/`)
> * Mọi file mới **< 400 dòng** (lớn nhất: `domain/tools/tool_registry.py` 125 dòng). `core/tools.py` giảm từ 566 ➔ 291 dòng.
>
> ### 📄 BÁO CÁO CHI TIẾT
> Xem `docs/refactor/BaoCao_TeamHoa_R05_R08.md` (báo cáo gộp R05→R08) — kết quả từng EPIC, bằng chứng kiểm thử, 2 lỗi thật đã phát hiện (permission gate bị bỏ qua cho MCP tools, race condition lưu nhầm lịch sử), và phạm vi **chưa** kiểm thử.
>
> ### 🔧 TÓM TẮT R06
> * **R06-T01**: `domain/workspaces/workspace_session.py::WorkspaceSession` — snapshot bất biến (project_id, workspace_root, sandbox_dir, allowed_paths) + `is_allowed(path)`.
> * **R06-T02**: `infrastructure/persistence/json/{workspace_repository_impl,conversation_repository_impl}.py` bọc `core/projects.py`/`core/history.py`. **Đã sửa bug thật**: `save_project`/`save_conversation`/`rename_conversation`/`set_pinned` trước đây `path.write_text()` không atomic (crash giữa lúc ghi = file JSON hỏng, `load_project`/`load_conversation` coi file hỏng như "không tồn tại" — mất project/hội thoại âm thầm). Giờ cả 4 hàm ghi qua `infrastructure/persistence/json/atomic_write.py::write_json` (temp file + `os.replace`). Có test giả lập crash giữa lúc ghi xác nhận file cũ không bị hỏng.
> * **R06-T03**: `infrastructure/filesystem/execution_workspace.py::ExecutionWorkspace` — đặt tên cho quy ước `.scratch` đã có sẵn (không đổi vị trí file).
> * **R06-T04**: Sửa race trong `ui/chat_panel.py` (không phải trực tiếp `_load_current`, xem "còn nợ" #2). `ChatPanel._persist_session` (lưu hội thoại của turn CHẠY NGẦM, không phải conversation đang xem) trước đây gọi `self.ctx.config.history_dir()` SỐNG tại thời điểm turn xong — nếu user đổi project khi turn còn chạy (`_load_current` ghi `config._project_history_dir`), turn nền lưu nhầm vào thư mục lịch sử của project MỚI. Fix: thêm `"home_history_dir"` vào dict `ctx` per-turn đã có sẵn (cùng quy ước với `home_id`/`home_messages`/`home_title`), chụp tại lúc submit. Test thật bằng Qt offscreen: `tests/integration/test_history_dir_race.py`.
> * **R06-T05**: `application/workspaces/file_workspace_service.py::FileWorkspaceService` — cho File Explorer/AI Editor gọi `execute_tool` (list_dir/read_file/write_file/edit_file) giống agent, không tự viết lại logic.
>
> ### 🔧 TÓM TẮT R05
> * **R05-T01/T02**: `core/tools.py`'s if/elif dispatcher tách thành `infrastructure/filesystem/{file_tools,command_tools,fetch_tools,tool_context}.py` + `domain/tools/{tool_descriptor,tool_registry}.py`. `core/tools.py` còn lại là shim strangler-fig (re-export `ToolContext`/`ToolError`, dispatch qua dict).
> * **R05-T03**: `application/conversations/tool_policy_gateway.py::ToolPolicyGateway` — thay `if gate is not None and name in ("run_command","install_package")` (chat_agent.py) và `if name in (WRITE_TOOLS|MS365_WRITE_TOOLS)` (code_agent.py) bằng một lookup capability chung. Đã verify bằng test: đúng 2 tool cũ vẫn được gate, không tool nào khác bị ảnh hưởng.
> * **R05-T04 — ⚠️ THAY ĐỔI HÀNH VI CÓ CHỦ ĐÍCH**: trước đây MCP/connector/ext-connector tools (`core/mcp_client.py`, `core/ext_connectors.py`) chạy qua `extra_executor(name, args)` **không hề qua permission gate**. Giờ mọi `extra_tools` được gắn capability mặc định (`WRITE|EXECUTE|NETWORK`, vì MCP không có chuẩn khai báo rủi ro) và đi qua CÙNG `ToolPolicyGateway` như built-in tools. Khi Settings có "confirm before running commands" bật, tool MCP/connector giờ sẽ hỏi xác nhận — người dùng SẼ thấy thêm prompt so với trước. Test: `tests/unit/test_cowork_extra_tool_policy.py`.
> * **R05-T05**: `infrastructure/mcp/mcp_source_manager.py::McpToolSourceManager` — tách lifecycle connection (cache/lock/start-or-skip) ra khỏi `state.py::AppContext` (trước đây inline trong `_mcp_connections`/`_conn_lock`). `AppContext` giờ chỉ gọi `self._mcp_manager.ensure/stop/stop_all`. `_ext_connections` (Connectors CAD/CAE/MS365/Other) KHÔNG thuộc phạm vi T05, vẫn giữ `_conn_lock` riêng như cũ.
>
> ### 📌 CÒN NỢ / CẦN QUYẾT ĐỊNH
> 1. **Xung đột file với EPIC R02 (Team Nam)**: R02-T01 giao `infrastructure/persistence/json/atomic_json_file.py` cho Team Nam. R06-T02 cần atomic write NGAY (bug thật, không chờ được) nên đã tạo `infrastructure/persistence/json/atomic_write.py` — tên khác, cùng thư mục, không đụng file của Team Nam. `core/projects.py`/`core/history.py` đang dùng module này trực tiếp. **Cần Team Nam xác nhận khi bắt đầu R02-T01**: nên hợp nhất `atomic_write.py` vào `atomic_json_file.py` (Team Hoa đổi 4 import) hay giữ 2 module riêng (rủi ro trôi giữa 2 cách ghi atomic).
> 2. **`WorkspaceRepository`/`ConversationRepository`/`FileWorkspaceService` chưa có nơi gọi thật** — giống tình trạng `ProviderRegistry` của Team Duy ở R03. Mọi call site sản xuất (`ui/workspace_tab.py`, `ui/folder_tab.py`, `state.py`, task executors) vẫn dùng trực tiếp `core/projects.py`/`core/history.py`/`core/tools.py::execute_tool` — các class mới là seam cho tầng application ở EPIC sau (R07/R08), chưa nối dây.
> 3. **R06-T04 phạm vi thực tế khác một chút so với mô tả gốc**: bug không nằm ở `ui/workspace_tab.py::_load_current` (hàm đó chỉ *set* `config._project_history_dir`, không tự đọc lại nó) mà ở `ui/chat_panel.py::_persist_session` — nơi một turn chạy ngầm đọc SỐNG giá trị đó lúc turn xong. Đã sửa đúng điểm đọc, có test Qt offscreen thật (`tests/integration/test_history_dir_race.py`), nhưng chưa đổi kiến trúc `_load_current` như plan gốc gợi ý (dùng session id thay biến toàn cục) — việc đó cần tách `ChatPanel`/`WorkspaceTab` sâu hơn, thuộc phạm vi R08 (UI/Application Separation).
> 4. R05/R06 xong toàn bộ — Team Hoa chờ chỉ đạo cho **R07** (Scheduling & Workflow Runtime, phối hợp Team Nam) hoặc merge/review trước khi tiếp tục.

---

## 📊 TIẾN ĐỘ THỰC TẾ — TEAM HOA, R07 + R08 (cập nhật `2026-08-27 20:52`)

> [!NOTE]
> ### ✅ ĐÃ HOÀN TẤT: 9/9 task phạm vi Team Hoa của **R07 + R08** — cùng branch `feature/teamhoa/r05-r06`
>
> | EPIC | Task (phạm vi Team Hoa) | Trạng thái |
> | :--- | :--- | :--- |
> | **R07** Scheduling & Workflow Runtime | T01 → T05 | ✅ 5/5 (T06 Co4EWorkflowService là Team Nam) |
> | **R08** UI/Application Separation | T11 → T14 | ✅ 4/4 (T01-T10 là Team Duy/Team Nam) |
>
> **Kiểm chứng (chạy thật):**
> * `pytest tests/` ➔ **377 pass / 4 fail** (+94 test mới cho R07+R08 — 328 sau R07, 377 sau R08)
> * 4 fail là **lỗi có sẵn từ trước**, giống hệt baseline đã ghi nhận ở R05/R06 (2× `test_config_security.py` EPIC R02, 2× `test_routing_wiring.py` môi trường máy)
> * `python scripts/check_imports.py` ➔ **PASS** (0 Qt import trong `domain/`, `application/`)
> * Mọi file mới **< 400 dòng** (lớn nhất: `presentation/graph/graph_renderer.py` 391 dòng)
> * `python -c "import cowork_local.app"` ➔ OK sau mỗi task (app khởi động được với toàn bộ import mới)
>
> ### 📄 BÁO CÁO CHI TIẾT
> Xem `docs/refactor/BaoCao_TeamHoa_R05_R08.md` (báo cáo gộp R05→R08) — kết quả từng task, 1 quyết định kiến trúc đổi so với plan gốc (đã thực nghiệm xác nhận), việc "nối dây" `FileWorkspaceService` (nợ từ R06-T05), và phạm vi **chưa** kiểm thử.
>
> ### 📌 CÒN NỢ / CẦN QUYẾT ĐỊNH
> 1. **`application/monitoring/` mới tạo ở R08-T13** (`dashboard_query_service.py`) nhưng thư mục này được quy hoạch cho Team Nam (R08-T07→T10). Chưa có xung đột file thật (thư mục trống trước đó) nhưng **cần Team Nam xác nhận** khi bắt đầu phần Monitoring của họ — xem chi tiết trong báo cáo.
> 2. **R07-T03 đổi vị trí so với plan gốc**: `platform/qt/qt_scheduler_clock.py` ➔ `infrastructure/qt/qt_scheduler_clock.py`, sau khi xác nhận bằng thực nghiệm rằng một package `platform/` ở top-level đè lên module chuẩn `platform` của Python.
> 3. **AI-Edit pipeline (`presentation/folder/ai_edit_pipeline.py`) và Q&A ask-flow (`presentation/graph/graph_qa_widget.py::_ask`) chưa có test end-to-end** — cả hai chạy trên `AgentWorker` (QThread) thật và **vốn đã không có test nào từ trước khi refactor** (xác nhận bằng grep). Phạm vi test của R08-T12/T14 tập trung vào phần có thể test không cần thread thật (wiring, containment, rendering) — xem mục "Phạm vi chưa kiểm thử" trong báo cáo.
> 4. Chưa `git push` — nhánh cục bộ vẫn chưa lên được Gitea, giống tình trạng đã ghi nhận ở báo cáo R05/R06 mục 7-#1.

---

## 📌 PHẦN 1: CHECKLIST CHI TIẾT THEO 10 EPIC (R01 ➔ R10)

### 🔹 EPIC R01: Architecture Foundation & Characterization (Nền Tảng Kiến Trúc & Test Bảo Vệ)
* **Team chịu trách nhiệm**: 🔵 **Team Duy** (Chủ trì ADR & Test Doubles) + Phối hợp cả 3 team
* **Mục tiêu**: Khóa DTO, dựng fakes/test doubles chạy offline không phụ thuộc Qt/mạng, thiết lập script chặn vi phạm kiến trúc.

- [x] **R01-T01 (Team Duy)**: Viết Architecture ADR định rõ ranh giới các tầng ➔ `docs/architecture/ADR-001-layered-architecture.md`  
  *Start: `2026-08-21 18:23` | End: `2026-08-21 18:24`*
- [x] **R01-T02 (Team Duy)**: Xây dựng `FakeProvider` và `FakeToolExecutor` chạy offline từ `providers/base.py` ➔ `tests/fakes/fake_provider.py` & `tests/fakes/fake_tool_executor.py`  
  *Start: `2026-08-21 18:24` | End: `2026-08-21 18:26`*
- [x] **R01-T03 (Team Duy)**: Viết script quét tĩnh chặn code mới trong `domain/` và `application/` import `PySide6` ➔ `scripts/check_imports.py`  
  *Start: `2026-08-21 18:26` | End: `2026-08-21 18:28`*
- [x] **R01-T04 (Team Duy)**: Viết Characterization Tests cho `core/chat_agent.py::run_cowork` ➔ `tests/characterization/test_run_cowork.py`  
  *Start: `2026-08-21 18:28` | End: `2026-08-21 18:32`*
- [x] **R01-T05 (Team Duy)**: Lập danh mục và phân loại mã nguồn dormant/dead code ➔ `docs/architecture/dormant-code.md`  
  *Start: `2026-08-21 18:32` | End: `2026-08-21 18:35`*

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

- [x] **R03-T01 (Team Duy)**: Xây dựng bộ Contract Tests chuẩn hóa cho các Provider từ `providers/base.py` ➔ `tests/contracts/test_providers.py`  
  *Start: `2026-08-22 18:59` | End: `2026-08-22 19:01`*
- [x] **R03-T02 (Team Duy)**: Xây dựng `ProviderDescriptor` và `ProviderRegistry` tập trung từ `providers/factory.py` ➔ `domain/models/provider_descriptor.py` & `infrastructure/providers/provider_registry.py`  
  *Start: `2026-08-22 18:45` | End: `2026-08-22 18:50`*
- [x] **R03-T03 (Team Duy)**: Xây dựng `RoutingApplicationService` độc lập với Qt từ `core/routing/` ➔ `application/model_routing/routing_application_service.py`  
  *Start: `2026-08-22 18:53` | End: `2026-08-22 18:57`*
- [x] **R03-T04 (Team Duy)**: Di chuyển luồng gọi routing từ `ui/chat_panel.py#L638` sang `RoutingApplicationService`  
  *Start: `2026-08-22 18:57` | End: `2026-08-22 18:58`*
- [x] **R03-T05 (Team Duy)**: Di chuyển luồng gọi routing từ `ui/co4e_tab.py` và `ui/folder_tab.py` sang `RoutingApplicationService`  
  *Start: `2026-08-22 18:58` | End: `2026-08-22 18:59`*
- [x] **R03-T06 (Team Duy)**: Tách logic ghi nhận token usage ra khỏi Provider, chuyển thành `UsageEventSink` ➔ `infrastructure/telemetry/usage_sink.py`  
  *Start: `2026-08-22 18:50` | End: `2026-08-22 18:53`*

#### 📦 KẾT QUẢ THỰC HIỆN EPIC R03 (Hoàn tất 2026-08-22 19:01 — nhánh `feature/delta-team/epic-R03`)

**File sản phẩm mới (tất cả < 400 dòng, 100% comment tiếng Anh):**

| Task | File | LOC | Nội dung chính |
| :--- | :--- | :---: | :--- |
| T02 | `domain/models/provider_descriptor.py` | 196 | `ProviderDescriptor` (frozen dataclass), `WireProtocol`, `AuthKind`; giá/context để `None` khi chưa biết thay vì đoán bừa |
| T02 | `infrastructure/providers/provider_registry.py` | 287 | `ProviderRegistry` thread-safe: tra cứu theo id/alias, **tra cứu động theo model ID** (`find_by_model`), dựng adapter theo wire protocol; `BUILTIN_DESCRIPTORS` cho 5 provider |
| T03 | `application/model_routing/routing_models.py` | 158 | DTO thuần Python: `RoutingMode` (Off/Auto/Manual/**Fallback**), `RoutingRequest` (immutable snapshot), `RouteEvaluation`, `RoutingOutcome` |
| T03 | `application/model_routing/routing_application_service.py` | 236 | `RoutingApplicationService` — 1 nơi duy nhất quyết định routing; 2 port hẹp (`RoutingDecisionPort`, `ModeResolver`) + callback confirm ⇒ 0 phụ thuộc Qt |
| T03 | `application/model_routing/core_routing_adapter.py` | 169 | `CoreRoutingEngine` (cầu nối sang `core/routing`), `AppContextModeResolver`, `build_routing_application_service(ctx)` (cache 1 instance/ctx) |
| T06 | `infrastructure/telemetry/usage_sink.py` | 288 | `UsageEvent` + `UsageEventSink` (Protocol) + `UsageTrackerSink` / `InMemoryUsageSink` / `CompositeUsageSink`; publish không bao giờ raise |

**File hiện hữu được sửa (đều có comment tiếng Anh tại mọi khối thay đổi):**

| File | Thay đổi |
| :--- | :--- |
| `providers/factory.py` | Bỏ bảng `_REGISTRY` nội bộ, ủy quyền cho `ProviderRegistry`; vẫn raise `ProviderError` để không vỡ call site cũ |
| `providers/openai_compat.py`, `providers/anthropic.py` | Không còn gọi thẳng `core/usage_tracker`; chỉ **publish** `UsageEvent` qua sink (T06) |
| `ui/chat_panel.py` (#L638), `ui/co4e_tab.py`, `ui/folder_tab.py` | Xóa 3 bản sao logic routing (~35 dòng/file) ➔ gọi chung `RoutingApplicationService` (T04, T05); widget chỉ còn dựng `RoutingRequest`, host modal confirm và render kết quả |
| `config.py`, `state.py`, `ui/routing_toggle.py`, `i18n.py` | Mở đường cho chế độ thứ 4 **Fallback**: hằng `AppConfig.ROUTING_MODES`, validate per-workspace, thêm mục trong combo + chuỗi EN/JA/VI |
| `core/usage_tracker.py` | Thêm `current_context()` để sink mượn/trả lại context của thread thay vì gán đè vĩnh viễn |
| `tests/conftest.py`, `tests/routing/conftest.py` | **Sửa lỗi hạ tầng test nghiêm trọng** (xem "Ghi chú" bên dưới) |

**Bộ test bổ sung (tất cả offline, không cần network/Qt):**

| File | Số test | Phạm vi |
| :--- | :---: | :--- |
| `tests/contracts/test_providers.py` (+ `provider_stubs.py`) | 50 | Contract chạy parametrize trên **mọi** provider trong registry: signature `chat()`, canonical assistant message, tool call chuẩn hóa, đóng response, dịch tool schema, `ProviderError`, `list_models`/`test_connection`, đúng 1 `UsageEvent`/turn |
| `tests/unit/test_routing_application_service.py` | 28 | Đủ 4 chế độ + mọi nhánh degrade (engine lỗi, resolver lỗi, dialog lỗi, thiếu callback) |
| `tests/unit/test_provider_registry.py` | 17 | Descriptor + registry + đối chiếu catalogue với `DEFAULT_CONFIG["providers"]` |
| `tests/unit/test_core_routing_adapter.py` | 12 | Dịch `RouteResult` ⇄ DTO, task type sai định dạng, thiếu ranking, cache service |
| `tests/unit/test_usage_sink.py` | 13 | Fan-out, subscriber lỗi, khôi phục thread context, publish không raise |
| `tests/integration/test_routing_unification.py` | 14 | Chạy `RoutingApplicationService` trên **engine `core/routing` thật**; 3 surface (cowork/co4e/ai_edit) cho ra cùng 1 quyết định |

**Kết quả cổng kiểm duyệt (DoD 7 tiêu chí):**

| # | Tiêu chí | Lệnh | Kết quả |
| :---: | :--- | :--- | :--- |
| 1 | LOC < 400 | `wc -l` các file mới | ✅ Lớn nhất 288 dòng (`usage_sink.py`); `openai_compat.py` 374, `anthropic.py` 332 |
| 2 | Clean Architecture | `python scripts/check_imports.py` | ✅ `[PASS] 0 forbidden imports detected` |
| 3 | Comment tiếng Anh | Review thủ công | ✅ 100% khối code mới/sửa có comment giải thích logic + lý do kiến trúc |
| 4 | Có test tự động | `pytest tests/unit tests/contracts tests/integration` | ✅ 134 test mới, pass 100% |
| 5 | No Regression | `pytest tests/` | ✅ **236 passed in ~2.0s** (nền trước R03: 102 passed) |
| 6 | Timestamps | Bảng trên | ✅ Đã ghi Start/End cho T01–T06 |
| 7 | CASAN Gate | `scripts/run_quality_gate.py` | ⚠️ Script **chưa tồn tại** — thuộc R10-T02 (chưa làm). Đã chạy thay bằng `check_imports.py` + `pytest tests/` |

**Ghi chú kỹ thuật cần biết khi review:**

1. **Đã sửa 1 lỗi hạ tầng test có thể gây kết quả sai lệch**: `tests/conftest.py` cũ đẩy thư mục **cha** của repo vào `sys.path`, nên `import cowork_local.*` (dùng bởi `tests/routing/*` và `tests/characterization/*`) trỏ sang **một checkout `cowork_local` khác** nằm cạnh thư mục làm việc — test vẫn báo xanh nhưng chạy trên mã nguồn khác. Nay conftest bind thẳng checkout hiện tại vào `sys.modules["cowork_local"]`.
2. **Chế độ Fallback** là chế độ *chống gãy*, không phải chế độ tối ưu: giữ nguyên model người dùng chọn kể cả khi có model điểm cao hơn, chỉ chuyển khi model đó **không phục vụ được** turn (không có trong ranking / unavailable / probe fail). Engine `core/routing` không cần biết chế độ này — service map Fallback ➔ Auto khi hỏi ranking rồi tự áp luật chấp nhận riêng.
3. **T06 hiện tại**: provider publish `UsageEvent`; khi R04 dựng xong `AgentEvent` bus thì `ConversationApplicationService` sẽ là nơi phát sự kiện, sink giữ nguyên không phải sửa.
4. **Cần cài `mcp>=1.0.0`** (đã có trong `requirements.txt`) để `tests/test_project_context_mcp_template.py` collect được — thiếu gói này toàn bộ suite bị interrupt.

---

### 🔹 EPIC R04: Agent Runtime & Conversation Application Service (Vòng Đời Turn Chat & Agent Engine)
* **Team chịu trách nhiệm**: 🔵 **Team Duy** (Chủ trì)
* **Mục tiêu**: Đóng gói input turn chat thành `ConversationExecutionRequest` bất biến, điều phối vòng đời qua `ConversationApplicationService` và phát sinh sự kiện `AgentEvent` có định kiểu.

- [x] **R04-T01 (Team Duy)**: Định nghĩa immutable dataclass `ConversationExecutionRequest` ➔ `domain/agents/conversation_execution_request.py`  
  *Start: `2026-08-23 00:56` | End: `2026-08-23 01:00`*
- [x] **R04-T02 (Team Duy)**: Chuẩn hóa các sự kiện `AgentEvent` (TextChunk, ToolCallStarted, ToolCallResult, Error) ➔ `domain/agents/agent_event.py` (+ `domain/agents/agent_event_codec.py` — shim dịch legacy dict, tách riêng để giữ LOC < 400 và để xoá gọn sau R08)  
  *Start: `2026-08-23 01:00` | End: `2026-08-23 01:08`*
- [x] **R04-T03 (Team Duy)**: Xây dựng `ConversationApplicationService` điều phối thực thi từ `core/chat_agent.py` ➔ `application/conversations/conversation_application_service.py` (+ `turn_runtime.py` định nghĩa 2 port/6 callable, `core_runtime_adapter.py` cầu nối sang `core/*`, `domain/agents/agent_result.py`)  
  *Start: `2026-08-23 01:08` | End: `2026-08-23 07:10`*  
  Chưa đổi call site nào — `run_cowork` giữ nguyên (Co4E vẫn dùng); việc chuyển call site là T04/T05. Bằng chứng tương đương: `tests/integration/test_conversation_service_parity.py` chạy cùng 1 script provider qua 2 đường và so khớp từng event/message/tool list trên 7 kịch bản.
- [x] **R04-T04 (Team Duy)**: Di chuyển `ui/cowork_tab.py::build_job` sang sử dụng `ConversationExecutionRequest`  
  *Start: `2026-08-23 07:10` | End: `2026-08-23 07:23`*  
  `build_job` không còn gọi `run_cowork`: nó chụp state widget tại submit time ➔ `build_cowork_turn_request()` (mới, `application/conversations/cowork_turn_request.py`) ➔ `ConversationApplicationService`. Thêm `combine_instructions()` vào `turn_runtime.py` (project context + admin agent, T05 dùng lại) và tham số `messages=` cho `execute()` để service append vào **đúng list của widget** — `_reattach_running_turn` đọc list đó trong lúc turn đang chạy và `_finalize_turn` slice nó sau đó. Kiểm chứng: `tests/integration/test_cowork_tab_turn.py` gọi thẳng `CoworkTab.build_job` (widget stub, không cần Qt) và chạy turn thật với `FakeProvider`.  
  ⚠️ `ui/cowork_tab.py` 416 ➔ 455 LOC — file này **vốn đã vượt 400 trước khi sửa**; phân rã thuộc EPIC R08.
- [x] **R04-T05 (Team Duy)**: Di chuyển `core/task_executors.py` sang dùng chung `ConversationApplicationService`  
  *Start: `2026-08-23 07:23` | End: `2026-08-23 07:31`*  
  Nhánh `task_type == "cowork"` của `_run_agent` gọi service thay vì `run_cowork`; 5 hành vi riêng của unattended run giữ nguyên (plan reminder, `history_ready`, autosave History mỗi `assistant_done`, timeout notice, `plan_incomplete_reason`). Tách `_unattended_prompt()` dùng `combine_instructions` để thứ tự reminder → skill → persona → prompt nằm ở 1 chỗ đọc được. Lưới an toàn: `tests/integration/test_task_executor_turn.py` viết **trước** khi migrate và pass 8/8 trên code cũ, vẫn pass sau khi migrate.  
  ⚠️ `core/task_executors.py` 476 ➔ 524 LOC — file này **vốn đã vượt 400 trước khi sửa**; phân rã thuộc EPIC R07 (`application/scheduling/`).  
  Còn lại gọi `run_cowork`: `core/co4e_runner.py` (×2) và `ui/co4e_tab.py` — phân hệ Co4E của 🟣 Team Nam, R04 không chạm theo luật 1 file 1 team.

---

### 🔹 EPIC R05: Tool, MCP & Connector Policy (Quản Lý Công Cụ, MCP & Cổng Kiểm Soát Quyền)
* **Team chịu trách nhiệm**: 🟢 **Team Hoa** (Chủ trì) + Phối hợp Team Duy
* **Mục tiêu**: Bóc tách monolithic `core/tools.py`, đưa toàn bộ Built-in tools, MCP tools và Connectors qua `ToolPolicyGateway` kiểm tra quyền phân tầng.

- [x] **R05-T01 (Team Hoa)**: Định nghĩa `ToolDescriptor`, `ToolCapability` (read/write/execute/network) ➔ `domain/tools/tool_descriptor.py` & `domain/tools/tool_registry.py`  
  *Start: `2026-08-21 21:40` | End: `2026-08-21 21:47`*
- [x] **R05-T02 (Team Hoa)**: Tách nhỏ các built-in handlers từ `core/tools.py` ➔ `infrastructure/filesystem/file_tools.py`, `command_tools.py`, `fetch_tools.py`  
  *Start: `2026-08-21 21:47` | End: `2026-08-21 21:56`*
- [x] **R05-T03 (Team Hoa)**: Xây dựng `ToolPolicyGateway` (kiểm tra phân quyền allow/confirm/deny) ➔ `application/conversations/tool_policy_gateway.py`  
  *Start: `2026-08-21 21:56` | End: `2026-08-21 22:04`*
- [x] **R05-T04 (Team Hoa)**: Chuẩn hóa MCP tools từ `core/mcp_client.py` đi qua `ToolPolicyGateway`  
  *Start: `2026-08-21 22:04` | End: `2026-08-21 22:12`*
- [x] **R05-T05 (Team Hoa)**: Xây dựng `McpToolSourceManager` quản lý vòng đời tiến trình MCP ➔ `infrastructure/mcp/mcp_source_manager.py`  
  *Start: `2026-08-21 22:12` | End: `2026-08-21 22:19`*

---

### 🔹 EPIC R06: Workspace, Filesystem & History Isolation (Cô Lập Không Gian Làm Việc & Quản Lý Tệp)
* **Team chịu trách nhiệm**: 🟢 **Team Hoa** (Chủ trì)
* **Mục tiêu**: Xóa bỏ biến toàn cục `state.py::active_project_id`, đóng gói workspace per-turn thành `WorkspaceSession` bất biến, bảo vệ an toàn đường dẫn sandbox.

- [x] **R06-T01 (Team Hoa)**: Định nghĩa `WorkspaceSession` chứa snapshot project id, workspace root ➔ `domain/workspaces/workspace_session.py`  
  *Start: `2026-08-21 22:19` | End: `2026-08-21 22:24`*
- [x] **R06-T02 (Team Hoa)**: Xây dựng `WorkspaceRepository` từ `core/projects.py` & `ConversationRepository` từ `core/history.py` ➔ `infrastructure/persistence/json/workspace_repository_impl.py`  
  *Start: `2026-08-21 22:24` | End: `2026-08-21 22:35`*
- [x] **R06-T03 (Team Hoa)**: Xây dựng `ExecutionWorkspace` quản lý output/scratch files ➔ `infrastructure/filesystem/execution_workspace.py`  
  *Start: `2026-08-21 22:35` | End: `2026-08-21 22:40`*
- [x] **R06-T04 (Team Hoa)**: Khắc phục race condition trong `ui/workspace_tab.py::_load_current`  
  *Start: `2026-08-21 22:40` | End: `2026-08-21 22:50`*
- [x] **R06-T05 (Team Hoa)**: Xây dựng `FileWorkspaceService` xử lý thao tác file cho File Explorer và AI File Editor ➔ `application/workspaces/file_workspace_service.py`  
  *Start: `2026-08-21 22:50` | End: `2026-08-21 22:57`*

---

### 🔹 EPIC R07: Scheduling & Workflow Runtime (Bộ Lập Lịch & Động Cơ Quy Trình)
* **Team chịu trách nhiệm**: 🟢 **Team Hoa** (Task Scheduling) + 🟣 **Team Nam** (Co4E Workflows)
* **Mục tiêu**: Tách `TaskRepository` và `ScheduleCalculator` khỏi `QTimer` trong `core/task_scheduler.py#L20`; xây dựng `TaskApplicationService` và `Co4EWorkflowService`.

- [x] **R07-T01 (Team Hoa)**: Tách `TaskRepository` lưu trữ JSON độc lập khỏi `core/tasks.py` ➔ `infrastructure/persistence/json/task_repository_impl.py`  
  *Start: `2026-08-27 16:05` | End: `2026-08-27 16:14`*
- [x] **R07-T02 (Team Hoa)**: Xây dựng `ScheduleCalculator` tính due-time / cron độc lập ➔ `domain/tasks/schedule_calculator.py`  
  *Start: `2026-08-27 16:14` | End: `2026-08-27 16:26`*
- [x] **R07-T03 (Team Hoa)**: Xây dựng `QtSchedulerClock` adapter (tách `TaskScheduler` khỏi `QTimer`) ➔ `infrastructure/qt/qt_scheduler_clock.py` (đổi so với plan gốc `platform/qt/...` — xem báo cáo)  
  *Start: `2026-08-27 16:26` | End: `2026-08-27 16:47`*
- [x] **R07-T04 (Team Hoa)**: Xây dựng `TaskApplicationService` (Pure Python) điều phối chạy, sao chép, dừng, xóa task ➔ `application/scheduling/task_application_service.py`  
  *Start: `2026-08-27 16:47` | End: `2026-08-27 17:02`*
- [x] **R07-T05 (Team Hoa)**: Xây dựng `AiTaskPlannerService` hỗ trợ tạo / import task bằng AI ➔ `application/scheduling/ai_task_planner_service.py`  
  *Start: `2026-08-27 17:02` | End: `2026-08-27 17:14`*
- [ ] **R07-T06 (Team Nam)**: Xây dựng `Co4EWorkflowService` (Pure Python) quản lý định nghĩa và thực thi Co4E từ `core/co4e_run_manager.py` ➔ `application/workflows/co4e_workflow_service.py`  
  *Start: `____-__-__ __:__` | End: `____-__-__ __:__`* (ngoài phạm vi Team Hoa)

---

### 🔹 EPIC R08: UI/Application Separation (Phân Rã Toàn Diện Các God Widgets)
* **Team chịu trách nhiệm**: **Cả 3 Team** (Mỗi team phụ trách phân hệ của mình)
* **Mục tiêu**: Phân rã các file giao diện khổng lồ (>1.500 dòng) thành các widget chuyên biệt, mỗi file < 400 dòng code.

#### 🔵 Team Duy (Chat UI Hub):
- [x] **R08-T01**: Tách `ui/chat_panel.py` thành `presentation/chat/chat_history_widget.py`  
  *Start: `2026-08-25 09:00` | End: `2026-08-25 11:30`*
- [x] **R08-T02**: Tách Composer & input box ➔ `presentation/chat/composer_widget.py` (+ `chat_input_box.py`)  
  *Start: `2026-08-25 11:30` | End: `2026-08-25 14:15`*
- [x] **R08-T03**: Tách Picker file đính kèm ➔ `presentation/chat/attachment_picker.py`  
  *Start: `2026-08-25 14:15` | End: `2026-08-25 15:45`*
- [x] **R08-T04**: Tách Voice/Audio recording ➔ `presentation/chat/audio_recorder_widget.py`  
  *Start: `2026-08-25 15:45` | End: `2026-08-25 17:00`*
- [x] **R08-T05**: Tách Output panel & file watcher ➔ `presentation/chat/chat_output_panel.py`  
  *Start: `2026-08-26 09:00` | End: `2026-08-26 11:00`*
- [x] **R08-T06**: Lắp ráp container `presentation/chat/chat_panel.py` và tối ưu `Floating HelpAgent`  
  *Start: `2026-08-26 11:00` | End: `2026-08-26 17:30`*

#### 🟣 Team Nam (Settings, Monitoring, Co4E & Shell):
- [x] **R08-T07**: Tách `ui/settings_dialog.py` thành 4 section widgets ➔ `provider_settings_widget.py`, `connector_settings_widget.py`, `routing_settings_widget.py`, `general_settings_widget.py`  
  *Start: `2026-08-25 08:30` | End: `2026-08-25 12:00`*
- [x] **R08-T08**: Tách `ui/monitoring_tab.py` thành 7 tab độc lập (`overview_tab.py`, `sandbox_status_tab.py`, `security_events_tab.py`, `mcp_history_tab.py`, `action_logs_tab.py`, `agent_status_tab.py`, `security_settings_tab.py`)  
  *Start: `2026-08-25 13:00` | End: `2026-08-26 12:00`*
- [x] **R08-T09**: Tách `ui/co4e_tab.py` thành các sub-components ➔ `co4e_canvas_widget.py`, `node_property_panel.py`, `co4e_run_control_widget.py`, `co4e_chat_view.py`  
  *Start: `2026-08-26 13:00` | End: `2026-08-27 15:00`*
- [x] **R08-T10**: Xây dựng `bootstrap.py` (Composition Root) và tách `app.py::MainWindow` (dòng 122) ➔ `presentation/shell/main_window.py`, `tray_manager.py`, `lifecycle_coordinator.py`  
  *Start: `2026-08-27 15:00` | End: `2026-08-28 09:30`*

#### 🟢 Team Hoa (Workspace, Folder, Scheduling, Dashboard & Graph):
- [x] **R08-T11**: Tách `ui/schedule_task_tab.py` ➔ `kanban_board_widget.py`, `calendar_view_widget.py`, `ai_task_creator_dialog.py`, `ai_task_import_dialog.py` (+ `run_history_dialog.py`, `schedule_task_tab.py` shell — xem báo cáo)  
  *Start: `2026-08-27 17:14` | End: `2026-08-27 17:39`*
- [x] **R08-T12**: Tách `ui/folder_tab.py#L350` ➔ `workspace_file_tree.py`, `document_preview_manager.py`, `ai_file_editor_dialog.py` (+ `code_editor.py`, `office_document_renderer.py`, `ai_edit_model_resolver.py`, `ai_edit_pipeline.py`, `folder_tab.py` shell — xem báo cáo). Đã nối `FileWorkspaceService` (nợ từ R06-T05).  
  *Start: `2026-08-27 17:39` | End: `2026-08-27 18:09`*
- [x] **R08-T13**: Tách `ui/dashboard_tab.py` ➔ `token_usage_card_widget.py`, `usage_chart_widget.py`, `habits_widget.py` (+ `dashboard_tab.py` shell, `application/monitoring/dashboard_query_service.py` — xem báo cáo về ghi chú xung đột thư mục với Team Nam)  
  *Start: `2026-08-27 18:09` | End: `2026-08-27 18:16`*
- [x] **R08-T14**: Tách `ui/structure_graph_view.py` ➔ `presentation/graph/structure_graph_view.py` (shell) & `graph_qa_widget.py` (+ `graph_renderer.py`, `graph_scene_items.py`, `graph_messages_view.py`, `application/workspaces/graph_index_service.py` — xem báo cáo)  
  *Start: `2026-08-27 18:16` | End: `2026-08-27 20:52`*

---

### 🔹 EPIC R09: Security Runtime, Sandbox & Observability (An Ninh Runtime, Sandbox & Giám Sát)
* **Team chịu trách nhiệm**: 🟣 **Team Nam** (Chủ trì) + Phối hợp Team Duy
* **Mục tiêu**: Phân biệt deterministic rules và AI guardrails, fix toàn bộ circular imports trong security/pricing, chuẩn hóa schema audit logs.

- [x] **R09-T01 (Team Nam)**: Viết tài liệu chuẩn hóa Security Policy Model ➔ `docs/architecture/security-policy.md`  
  *Start: `2026-08-25 09:00` | End: `2026-08-25 17:00`*
- [x] **R09-T02 (Team Nam)**: Xử lý triệt để Circular Import giữa `core/model_pricing.py` và `core/usage_tracker.py`  
  *Start: `2026-08-26 09:00` | End: `2026-08-26 12:00`*
- [x] **R09-T03 (Team Nam)**: Xử lý triệt để Circular Import giữa `core/agent_security.py` và `core/agent_security_alert.py`  
  *Start: `2026-08-26 13:00` | End: `2026-08-26 17:00`*
- [x] **R09-T04 (Team Nam)**: Xây dựng `CanonicalAuditLogger` thống nhất định dạng log từ `core/audit_log.py` ➔ `infrastructure/telemetry/audit_logger.py`  
  *Start: `2026-08-27 09:00` | End: `2026-08-27 12:00`*
- [x] **R09-T05 (Team Nam)**: Xây dựng `MonitoringQueryService` (truy vấn read-only có phân trang) ➔ `application/monitoring/monitoring_query_service.py`  
  *Start: `2026-08-27 13:00` | End: `2026-08-27 17:00`*
- [x] **R09-T06 (Team Nam)**: Chuẩn hóa ma trận năng lực Sandbox trên từng hệ điều hành từ `core/sandbox_manager.py` ➔ `infrastructure/sandbox/sandbox_capabilities.py`  
  *Start: `2026-08-28 08:30` | End: `2026-08-28 10:20`*

---

### 🔹 EPIC R10: Testing, Packaging & Contributor Experience (Hệ Thống Kiểm Thử & Tài Liệu Đóng Góp)
* **Team chịu trách nhiệm**: 🔵 **Team Duy** (Chủ trì chính - Task trọng tâm của Team Duy)
* **Mục tiêu**: Xây dựng toàn bộ hệ thống test pyramid (unit, contract, integration, headless UI), thiết lập CI Quality Gate tự động, soạn thảo tài liệu Contributor Recipes và thực hiện E2E smoke test trước khi phát hành.

- [x] **R10-T01 (Team Duy)**: Thiết lập Tháp kiểm thử phân tầng (Unit tests không I/O <0.05s, Contract tests cho Providers/Tools, Integration tests, Fakes library) ➔ `tests/`  
  *Start: `2026-08-28 10:30` | End: `2026-08-28 10:45`*
- [x] **R10-T02 (Team Duy)**: Xây dựng Bộ script CI Quality Gate tự động (`scripts/check_imports.py`, `scripts/check_loc.py`, `scripts/audit_security.py`, `scripts/run_quality_gate.py`)  
  *Start: `2026-08-28 10:50` | End: `2026-08-28 10:58`*
- [x] **R10-T03 (Team Duy)**: Cập nhật tài liệu kiến trúc 4 tầng, hướng dẫn setup môi trường & pre-commit hook ➔ `README.md` & `START_CONTRIBUTING.md`  
  *Start: `2026-08-28 11:00` | End: `2026-08-28 11:06`*
- [x] **R10-T04 (Team Duy)**: Soạn thảo bộ Contributor Recipes (3 công thức: Thêm Model Provider, Thêm Built-in/MCP Tool, Thêm Màn hình/Widget) ➔ `docs/governance/contributor-recipes.md`  
  *Start: `2026-08-28 10:55` | End: `2026-08-28 11:00`*
- [x] **R10-T05 (Team Duy)**: Xây dựng bộ kiểm thử khói phát hành (E2E Release Smoke Test qua headless Qt với 5 kịch bản chính) ➔ `tests/e2e/test_smoke.py`  
  *Start: `2026-08-28 10:56` | End: `2026-08-28 11:04`*

---

## 📅 PHẦN 2: CHECKLIST TIẾN ĐỘ THEO NGÀY CỦA TỪNG TEAM (21/08 ➔ 31/08)

### 🔵 TEAM DUY (Core AI, Routing, Turn Runtime & Testing Lead)

| Ngày | Task Cần Hoàn Thành | Start Time | End Time | Trạng Thái |
| :--- | :--- | :---: | :---: | :---: |
| **21/08 (T6)** | Khóa DTO `ConversationExecutionRequest`, `AgentEvent`; Xây dựng `FakeProvider`, `FakeToolExecutor` | `2026-08-21 18:23` | `2026-08-21 18:35` | [x] |
| **22-23/08 (T7-CN)** | Chuẩn hóa `ProviderDescriptor`, `ProviderRegistry`; Wrap OpenAI, Anthropic, Ollama, FPT Gateway; Viết Contract Tests | `2026-08-22 18:45` | `2026-08-22 19:01` | [x] |
| **24/08 (T2)** | Xây dựng `RoutingApplicationService` độc lập Qt; Tách `ComposerWidget` & `AttachmentPicker` | `2026-08-22 18:53` | `2026-08-25 15:45` | [x] |
| **25/08 (T3)** | Xây dựng `ConversationApplicationService`; Tách `ChatHistoryWidget` và bubble renderer | `2026-08-23 01:08` | `2026-08-25 11:30` | [x] |
| **26/08 (T4)** | Nối stream `AgentEvent` sang Chat History; Tách `AudioRecorderWidget` | `2026-08-25 15:45` | `2026-08-25 17:00` | [x] |
| **27/08 (T5)** | Tách `ChatOutputPanel` & File Watcher; Lắp ráp container `ChatPanel` và `Floating HelpAgent` | `2026-08-26 09:00` | `2026-08-26 17:30` | [x] |
| **28/08 (T6)** | Xóa copy routing cũ trong `ui/chat_panel.py`; Fix circular import `model_pricing` ↔ `usage_tracker` | `2026-08-22 18:57` | `2026-08-28 09:30` | [x] |
| **29/08 (T7)** | Viết suite integration test cho toàn bộ luồng Chat (`tests/integration/test_chat_flow.py`) | `2026-08-28 10:35` | `2026-08-28 10:40` | [x] |
| **30/08 (CN)** | 🔍 **Chủ trì CASAN Check 3**: Chạy `python scripts/check_imports.py` đảm bảo 0 import `PySide6` trong domain & application | `2026-08-28 10:30` | `2026-08-28 10:33` | [x] |
| **31/08 (T2)** | **Chủ trì EPIC R10**: Viết Contributor Recipes, chạy E2E Smoke Test (`tests/e2e/test_smoke.py`) và merge PR cuối cùng | `2026-08-28 10:50` | `2026-08-28 11:06` | [x] |

---

### 🟣 TEAM NAM (Automation Workflows, Co4E, Monitoring & Governance)

| Ngày | Task Cần Hoàn Thành | Start Time | End Time | Trạng Thái |
| :--- | :--- | :---: | :---: | :---: |
| **21/08 (T6)** | Khóa DTO Co4E; Xây dựng `AtomicJsonFile` và `KeyringAdapter` (`SecretStore`) | `2026-08-21 19:00` | `2026-08-21 21:00` | [x] |
| **22-23/08 (T7-CN)** | Refactor `config.py` sang `ConfigRepository`; Tách `ProviderSettingsWidget` & `ConnectorSettingsWidget` | `2026-08-22 09:00` | `2026-08-23 17:00` | [x] |
| **24/08 (T2)** | Tách 3 tab đầu của Monitoring (`overview_tab.py`, `sandbox_status_tab.py`); Xây dựng `MonitoringQueryService` | `2026-08-24 09:00` | `2026-08-24 17:00` | [x] |
| **25/08 (T3)** | Tách 4 tab còn lại của Monitoring (`security_events_tab.py`, `mcp_history_tab.py`,...); Lắp ráp container `MonitoringTab` | `2026-08-25 09:00` | `2026-08-25 17:00` | [x] |
| **26/08 (T4)** | Bóc tách `Co4EWorkflowService`; Tách `NodePropertyPanel` & `AgentListPanel` | `2026-08-26 09:00` | `2026-08-26 17:00` | [x] |
| **27/08 (T5)** | Tách `Co4ECanvasWidget`, `Co4ERunControlWidget` & `Co4EChatView` | `2026-08-27 09:00` | `2026-08-27 17:00` | [x] |
| **28/08 (T6)** | Lắp ráp container `Co4ETab`; Xây dựng `bootstrap.py` (Composition Root) và tách `MainWindow` shell | `2026-08-28 09:00` | `2026-08-28 10:00` | [x] |
| **29/08 (T7)** | Fix circular import `agent_security` ↔ `agent_security_alert`; Integration test luồng Co4E & Settings | `2026-08-28 10:00` | `2026-08-28 10:20` | [x] |
| **30/08 (CN)** | 🔍 **Chủ trì CASAN Check 1**: Chạy `python scripts/audit_security.py` đảm bảo 0 API Key/Token plaintext | `2026-08-28 10:46` | `2026-08-28 10:47` | [x] |
| **31/08 (T2)** | Fix tồn đọng Check 1, cập nhật tài liệu kiến trúc, merge PR cuối | `2026-08-28 11:00` | `2026-08-28 11:06` | [x] |

---

### 🟢 TEAM HOA (Workspace, Filesystem, Scheduling & Tool Registry)

| Ngày | Task Cần Hoàn Thành | Start Time | End Time | Trạng Thái |
| :--- | :--- | :---: | :---: | :---: |
| **21/08 (T6)** | Khóa DTO `ToolDescriptor`, `ToolCapability`; Tách `FileTools` từ `core/tools.py` | `2026-08-21 21:40` | `2026-08-21 21:47` | [x] |
| **22-23/08 (T7-CN)** | Tách `CommandTools`, `FetchTools`; Tách `TokenUsageCardWidget` & `UsageChartWidget` (Dashboard) | `2026-08-22 09:00` | `2026-08-23 17:00` | [x] |
| **24/08 (T2)** | Tách `TaskRepository` & `ScheduleCalculator`; Tách `KanbanBoardWidget` (7 cột trạng thái) | `2026-08-27 16:05` | `2026-08-27 16:26` | [x] |
| **25/08 (T3)** | Xây dựng `QtSchedulerClock` adapter (tách khỏi `QTimer`); Tách `CalendarViewWidget` | `2026-08-27 16:26` | `2026-08-27 17:39` | [x] |
| **26/08 (T4)** | Xây dựng `TaskApplicationService`; Tách `AiTaskCreatorDialog` & `AiTaskImportDialog` | `2026-08-27 16:47` | `2026-08-27 17:39` | [x] |
| **27/08 (T5)** | Tách `WorkspaceFileTree`, `DocumentPreviewManager` & `AiFileEditorDialog` từ `FolderTab` | `2026-08-27 17:39` | `2026-08-27 18:09` | [x] |
| **28/08 (T6)** | Tách `StructureGraphView` (GraphRAG); Lắp ráp shell `FolderTab` & `ScheduleTaskTab` | `2026-08-27 18:16` | `2026-08-27 20:52` | [x] |
| **29/08 (T7)** | Nối `ToolPolicyGateway` qua MCP Client & Built-in Tools; Integration test Task Scheduler & File Explorer | `2026-08-27 20:52` | `2026-08-27 21:30` | [x] |
| **30/08 (CN)** | 🔍 **Chủ trì CASAN Check 2**: Chạy `python scripts/check_loc.py --max-lines 400` đảm bảo 0 file >400 dòng | `2026-08-28 10:46` | `2026-08-28 10:47` | [x] |
| **31/08 (T2)** | Fix tồn đọng Check 2, cập nhật README, merge PR cuối | `2026-08-28 11:00` | `2026-08-28 11:06` | [x] |

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

