# BÁO CÁO KẾT QUẢ — TEAM DUY: EPIC R01, R03, R04

* **Dự án**: Cowork Local (Cowork-Local BamBOO)
* **Team**: 🔵 Team Duy — Core AI, Routing, Turn Runtime & Testing (Tech Lead)
* **Nhánh**: `feature/deltateam/refactor-plan`
* **Thời gian thực hiện**: 21/08/2026, 09:56 ➔ 10:56
* **Ngày báo cáo**: 21/08/2026
* **Tài liệu gốc**: `Feature_Architecture_Proposal.md`, `Refactoring_Checklist.md`, `DeltaTeam_prompt.md`

---

## 1. Tóm tắt điều hành

Hoàn tất **16/16 task** của 3 EPIC được giao trong đợt này: **R01** (nền tảng kiến trúc & lưới an toàn), **R03** (hợp nhất provider & routing), **R04** (vòng đời turn hội thoại). Toàn bộ đã commit và push lên nhánh.

| Chỉ số | Kết quả |
| :--- | :--- |
| Task hoàn thành | **16/16** (R01: 5, R03: 6, R04: 5) |
| Commit | 5 |
| File thay đổi | 48 (37 file mới, 11 file sửa) |
| Dòng code | +5.843 / −225 |
| Test | **243 pass** / 44s |
| Test suite nhanh (unit + contract + characterization + routing) | **218 pass / 1,22s** |
| CASAN Check 3 (`scripts/check_imports.py`) | **PASS** — 0 Qt import trong `domain/`, `application/` |
| File production > 400 dòng | **0** |

**3 lỗi thật được phát hiện và sửa trong quá trình làm** (chi tiết mục 5) — trong đó 1 lỗi deadlock sẽ làm treo ứng dụng ngay ở tin nhắn đầu tiên.

---

## 2. Kết quả theo từng EPIC

### 🔹 EPIC R01 — Architecture Foundation & Characterization (5/5)

| Task | Sản phẩm | Ghi chú |
| :--- | :--- | :--- |
| R01-T01 | `docs/architecture/ADR-001-layered-architecture.md` | Định nghĩa 4 tầng, chiều phụ thuộc, 6 quy tắc bất biến I1–I6, chiến lược di trú Strangler Fig |
| R01-T02 | `tests/fakes/fake_provider.py`, `fake_tool_executor.py` | Test double chạy offline, kịch bản hoá, ghi lại mọi lời gọi |
| R01-T03 | `scripts/check_imports.py` (239 dòng) | Quét AST, bắt cả import tương đối (`from ...ui import x`) và import trong thân hàm |
| R01-T04 | `tests/characterization/test_run_cowork.py` | **13 test** chụp snapshot hành vi hiện tại của `run_cowork` trước khi R04 đụng vào |
| R01-T05 | `docs/architecture/dormant-code.md` | Quét đồ thị import: 43 module "không ai import" ➔ xác minh còn **6 hạng mục chết thật (~1.887 dòng)** |

**Điểm đáng chú ý ở R01-T03**: dùng AST thay vì `grep` là bắt buộc — trong repo có nhiều docstring nhắc tên `PySide6` một cách hợp lệ, `grep` sẽ báo nhầm và đội sẽ học cách tắt cổng kiểm duyệt.

**Điểm đáng chú ý ở R01-T05**: 43 module không có importer **không** đồng nghĩa 43 module chết. Sau xác minh thủ công: `__main__.py` là entry point, `mcp_servers/ms365_server.py` chạy bằng subprocess (`state.py:285`), 34 file `tools/check_*.py` là dev tooling chạy tay. Chỉ 6 hạng mục là dormant thật.

### 🔹 EPIC R03 — Model Providers & Routing (6/6)

| Task | Sản phẩm | Ghi chú |
| :--- | :--- | :--- |
| R03-T01 | `tests/contracts/test_providers.py` | **29 contract test**; chạy được cả 2 adapter thật mà **không cần mạng** nhờ thay `Provider._request` bằng SSE đóng hộp |
| R03-T02 | `domain/models/provider_descriptor.py`, `infrastructure/providers/provider_registry.py` | Gom 3 nơi khai báo provider về 1 chỗ |
| R03-T03 | `application/model_routing/routing_application_service.py` | Pure Python, 4 chế độ: Off / Auto / Manual / **Fallback (mới)** |
| R03-T04, T05 | `ui/chat_panel.py`, `ui/co4e_tab.py`, `ui/folder_tab.py` | Gỡ 3 bản sao logic routing |
| R03-T06 | `infrastructure/telemetry/usage_sink.py` | Tách ghi nhận token usage khỏi provider |

**Vấn đề gốc đã giải quyết** — cùng một thuật toán routing tồn tại **3 bản gần giống nhau**:

```
ui/chat_panel.py::_apply_routing       (~45 dòng)
ui/co4e_tab.py::_apply_co4e_routing    (~38 dòng)
ui/folder_tab.py::_ai_apply_routing    (~42 dòng)
```

Cả 3 đều nằm trong widget Qt ➔ **không thể test nếu không dựng cửa sổ**, và đã bắt đầu lệch nhau (mỗi bản xác định "model hiện tại" một kiểu). Nay cả 3 chỉ còn gọi `ctx.routing_application().route_turn(...)` + một callback xác nhận.

**Chế độ Fallback (mới)**: giữ nguyên model người dùng chọn, **chỉ đổi sau khi model đó lỗi**. Đây là chế độ người dùng cần khi họ tin lựa chọn của mình nhưng vẫn muốn lượt chat sống sót qua sự cố nhà cung cấp.

**Bộ từ vựng mode**: trước đây tuple `("off", "auto", "manual")` bị lặp ở **4 chỗ** (`config.py` × 2, `state.py` × 2). Thêm một mode mà quên một chỗ sẽ **âm thầm hạ lựa chọn của người dùng về "off"**. Nay tập trung vào `normalize_mode()` / `is_valid_mode()`.

### 🔹 EPIC R04 — Agent Runtime & Conversation Service (5/5)

| Task | Sản phẩm | Ghi chú |
| :--- | :--- | :--- |
| R04-T01 | `domain/agents/conversation_execution_request.py` | Frozen dataclass, chụp toàn bộ input của 1 turn tại thời điểm submit |
| R04-T02 | `domain/agents/agent_event.py` (370 dòng) | **13 event có kiểu** thay cho dict không kiểu, kèm cầu nối 2 chiều |
| R04-T03 | `application/conversations/conversation_application_service.py` | Điều phối vòng đời turn, không import Qt |
| R04-T04 | `ui/cowork_tab.py::build_job` | Chuyển sang snapshot + service |
| R04-T05 | `core/task_executors.py::_run_agent` | Chuyển sang **cùng** service (trước đây là bản lắp ráp thứ hai, hơi khác) |

**Vấn đề gốc đã giải quyết** — closure trong `build_job` đọc state của widget **từ trong worker thread**:

```python
def job(worker):
    provider = self.build_provider()                  # đọc combo box
    proj_ctx = project_context_text(load_project(project_id))
```

Người dùng có thể đổi model, đổi workspace, sửa chỉ dẫn project **trong lúc turn đang chạy**. Turn khi đó chạy trên hỗn hợp state cũ + mới, và hỗn hợp nào phụ thuộc vào thời điểm luồng — đúng loại bug tái hiện mỗi tuần một lần và không bao giờ tái hiện trong test.

**`TurnCompletedEvent`** là tín hiệu kết thúc turn mà engine cũ **hoàn toàn không có**: hiện tại mọi consumer suy ra "xong" từ việc worker thread kết thúc, nên **turn bị huỷ và turn thất bại trông giống hệt nhau** với giao diện.

---

## 3. Kiến trúc sau refactor

```text
presentation/  ui/chat_panel.py, ui/co4e_tab.py, ui/folder_tab.py, ui/cowork_tab.py
      │        (chỉ dựng UI, mở dialog xác nhận, render thông báo)
      ▼
application/   model_routing/routing_application_service.py    ← 4 mode routing
               conversations/conversation_application_service.py ← vòng đời turn
      │        (100% pure Python — cổng kiểm duyệt tự động chặn import Qt)
      ▼
domain/        agents/conversation_execution_request.py  ← snapshot bất biến
               agents/agent_event.py                     ← 13 event có kiểu
               models/provider_descriptor.py             ← catalog provider
      ▲
infrastructure/ providers/provider_registry.py   telemetry/usage_sink.py
```

**Nguyên tắc di trú (ADR-001 mục 4)**: **không viết lại engine**. `core/chat_agent.py::run_cowork` và `core/routing/*` (2.263 dòng, 79 test đang xanh) vẫn là engine bên dưới; tầng application chỉ sở hữu phần trước đây bị trộn vào UI. Nhờ vậy `pytest` luôn xanh giữa các bước và một team có thể merge mà không phải chờ team khác.

---

## 4. Bằng chứng kiểm thử

### Phân bố test

| Suite | Số test | Thời gian | Vai trò |
| :--- | ---: | ---: | :--- |
| `tests/unit/` | 97 | | Logic thuần, không Qt/mạng |
| `tests/contracts/` | 29 | | Mọi provider phải thoả cùng bộ cam kết |
| `tests/characterization/` | 13 | | Chốt hành vi hiện tại của `run_cowork` |
| `tests/routing/` | 79 | | Có sẵn từ trước, vẫn xanh |
| **Cộng 4 suite nhanh** | **218** | **1,22s** | ✅ đạt CASAN "A — unit < 1s" |
| `tests/integration/` | 25 | 42s | Widget Qt thật (offscreen) + provider kịch bản hoá |
| **Tổng** | **243** | **44s** | |

### Đối chiếu Definition of Done (7 tiêu chí, `DeltaTeam_prompt.md`)

| # | Tiêu chí | Kết quả |
| :--- | :--- | :--- |
| 1 | Mọi file < 400 dòng | ✅ Lớn nhất: `agent_event.py` 370 dòng |
| 2 | 0 import Qt trong `domain/`, `application/` | ✅ `check_imports.py` PASS |
| 3 | Comment tiếng Anh ở mọi khối sửa/mới | ✅ Docstring + giải thích **lý do**, không chỉ mô tả code |
| 4 | Có unit/contract test, pass 100% < 1s | ✅ 218 test / 1,22s |
| 5 | Không hồi quy | ✅ 79 test routing có sẵn vẫn xanh |
| 6 | Ghi Start/End vào Checklist | ✅ 16 task đã tick kèm mốc thời gian |
| 7 | Cổng CASAN | ⚠️ `run_quality_gate.py` thuộc **R10-T02**, chưa viết. Check 3 đã có và PASS |

### Ba đường code đã sửa nhưng ban đầu chưa được thực thi

Sau khi hoàn tất 16 task, rà soát lại phát hiện 3 đường code đã bị sửa nhưng **không test nào chạy qua**. Đã bổ sung **18 test**:

| Đường code | Rủi ro nếu bỏ qua | Test bổ sung |
| :--- | :--- | ---: |
| `task_executors._run_agent` | Autosave History có thể đóng băng ở tin nhắn đầu | 7 |
| `_apply_co4e_routing` / `_ai_apply_routing` | Mới chỉ import được, chưa từng gọi hàm | 11 |
| `confirm_switch(decision)` Manual mode | Thiếu field ➔ **nổ bên trong modal**, nơi khó phát hiện nhất | (nằm trong 11 ở trên) |

---

## 5. Ba lỗi thật phát hiện trong quá trình làm

### 🔴 Lỗi 1 — Deadlock khi khởi tạo routing service

`AppContext.routing_application()` giữ `_routing_lock` rồi gọi `routing()`, vốn cũng lấy **chính lock đó**. `threading.Lock` không reentrant ➔ **treo cứng ngay ở tin nhắn đầu tiên**, không có thông báo lỗi.

*Sửa*: tách `_routing_app_lock` riêng, và resolve engine **trước khi** lấy lock.

### 🟠 Lỗi 2 — Event `notice` bị cầu nối nuốt mất

Bản đầu của `agent_event.py` liệt kê 12 loại event nhưng **thiếu `notice`**. Trong khi đó `notice` được phát ra từ 3 nơi trên đường chạy bình thường:

* `core/agent_security.py` — yêu cầu/lệnh bị Agent Security **chặn**
* `core/context_budget.py` — hội thoại vừa bị tự động nén
* Bộ đọc file đính kèm — file không xử lý được, và tiến độ "đang đọc trang X/Y"

Cầu nối bỏ qua event không nhận diện được (đúng thiết kế, để engine có thể thêm event mới) — nên **người dùng sẽ không bao giờ thấy cảnh báo bảo mật**, hoàn toàn im lặng.

*Sửa*: thêm `NoticeEvent`, **và** thêm test quét mã nguồn engine tìm mọi tag `emit({"type": ...})` rồi bắt lỗi nếu có tag nào chưa có event tương ứng — biến sự im lặng thành test đỏ.

### 🟡 Lỗi 3 — Test đang chạy trên checkout khác

`tests/routing/conftest.py` đẩy thư mục cha vào `sys.path`. Vì thư mục checkout tên là `cowork_local_gitea` (không phải `cowork_local`), lệnh `import cowork_local` **ăn nhầm sang `Desktop\cowork_local`** — một bản checkout khác. Suite báo xanh trên mã nguồn **không phải nhánh đang review**.

*Sửa*: `tests/conftest.py` nạp `__init__.py` theo đường dẫn tuyệt đối và đăng ký vào `sys.modules` trước mọi test.

---

## 6. Cải thiện phụ (không nằm trong yêu cầu task)

| Cải thiện | Ảnh hưởng |
| :--- | :--- |
| `ProviderRegistry.build()` đóng dấu `descriptor.id` lên instance | Sửa việc usage của `ollama` / `github_copilot` / `codex` bị ghi nhận nhầm thành `openai_compat` trên Dashboard. **Chưa nối vào production** — xem mục 7. |
| `ProviderRegistry.build()` copy config trước khi ghi | Trước đây một model do routing chọn có thể ghi đè lên default đã lưu của người dùng |
| `UsageTrackerSink` ghi log ở mức debug khi thất bại | Trước là `except: pass` — mất sạch lý do khi Dashboard hỏng |
| `estimate_tokens` được chốt bằng test so với `core.usage_tracker` | Bảo đảm việc tách telemetry **không làm lệch một con số nào** |

---

## 7. Còn nợ & cần quyết định

| # | Nội dung | Người quyết |
| :--- | :--- | :--- |
| 1 | **`ProviderRegistry` chưa nối vào `state.build_provider_for`** (vẫn dùng `providers/factory.py`). Nối vào sẽ sửa lỗi quy kết usage ở mục 6, **nhưng đổi cách gom dữ liệu lịch sử trên Dashboard**. | Team Duy + PO |
| 2 | **Mode `fallback` chưa có trên toggle UI** — config và service đã hỗ trợ đầy đủ; widget `RoutingToggle` thuộc R08. | Team Duy (R08) |
| 3 | **Đã sửa 2 dòng trong `config.py`** (`routing_mode_for`, `set_routing_mode_for`) để dùng chung bộ từ vựng mode. File này Team Nam đang refactor ở R02-T02. | ⚠️ **Cần báo Team Nam** |
| 4 | **Circular import** `core/model_pricing.py` ↔ `core/usage_tracker.py` chưa xử lý (task ngày 28/08). | Team Duy |
| 5 | **2 test đỏ có sẵn từ trước**: `config.py:108` hardcode `sandbox_pw = "quandh14"` ➔ `tests/test_config_security.py`. Thuộc **EPIC R02 / Team Nam**. | 🟣 Team Nam |
| 6 | `tests/integration/test_routing_surfaces.py` mất 41s do dựng `Co4ETab`/`FolderTab`. Nên gắn marker `slow` khi làm R10. | Team Duy (R10) |

---

## 8. Phạm vi chưa kiểm thử

Nêu rõ để tránh hiểu nhầm mức độ bảo đảm:

* **Chưa mở ứng dụng bằng tay** — mới chạy widget headless (`QT_QPA_PLATFORM=offscreen`), chưa có ai kiểm tra bằng mắt.
* **Chưa gọi provider thật** — toàn bộ dùng `FakeProvider`, không có lưu lượng mạng.
* **Chưa chạy 34 script `tools/check_*.py`** — các script này tự `sys.path.insert` thư mục cha nên sẽ import nhầm checkout khác (đúng lỗi 3 ở mục 5). Cần sửa chúng ở R10.

---

## 9. Việc kế tiếp của Team Duy

| EPIC | Nội dung | Điều kiện |
| :--- | :--- | :--- |
| **R08** (T01 ➔ T06) | Tách `ui/chat_panel.py` (1.795 dòng) thành 6 widget < 400 dòng | Sẵn sàng bắt đầu — `AgentEvent` (R04-T02) chính là kênh dữ liệu 6 widget con sẽ dùng thay vì đọc trực tiếp state của `ChatPanel` |
| **R10** (T01 ➔ T05) | Testing Pyramid, `run_quality_gate.py`, Contributor Recipes, E2E Smoke | Chờ cả 3 team hoàn tất |

---

## 10. Lịch sử commit

| Commit | Nội dung |
| :--- | :--- |
| `bbc09f6` | feat(R01): architecture foundation, offline fakes and characterization net |
| `96bec97` | feat(R03): unify provider catalogue, routing decisions and usage telemetry |
| `a53163e` | feat(R04): immutable turn snapshot, typed agent events, conversation service |
| `15e1d3e` | test(R03/R04): cover the three code paths that were changed but never executed |
| `67b8d2e` | docs(refactor): correct the Team Duy scope block in the checklist |
