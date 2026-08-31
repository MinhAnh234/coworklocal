# NHẬT KÝ THEO DÕI VÀ PHÒNG NGỪA LỖI TÁI CẤU TRÚC (BUG & LESSONS LEARNED LOG)
## DỰ ÁN: COWORK LOCAL (COWORK-LOCAL BAMBOO)

Tài liệu này dùng để ghi nhận **toàn bộ các lỗi, xung đột kiến trúc và sự cố phát sinh** trong suốt quá trình refactoring của cả 3 team (Team Duy, Team Nam, Team Hoa).

> [!IMPORTANT]
> ### 🛡️ NGUYÊN TẮC VÀNG VỀ QUẢN TRỊ CHẤT LƯỢNG (ZERO RECURRENCE):
> 1. **Ghi nhận ngay lập tức**: Khi gặp bất kỳ lỗi nào (Syntax, Circular Import, Type Error, Test Failure, Thread Freeze, Data Corruption), kỹ sư/AI phải ghi ngay vào tài liệu này trước khi tiếp tục task.
> 2. **Phân tích nguyên nhân gốc rễ (Root Cause)**: Không chỉ sửa phần ngọn mà phải giải thích rõ bản chất vì sao lỗi xảy ra.
> 3. **Rút ra quy tắc phòng ngừa (Prevention Rule)**: Đặt ra nguyên tắc kỹ thuật để **TUYỆT ĐỐI KHÔNG TÁI PHẠM** ở các task tiếp theo.
> 4. **Checklist đầu vào**: Trước khi bắt đầu bất kỳ task mới nào, kỹ sư/AI **bắt buộc phải đọc lại toàn bộ file này**.

---

## 📌 BẢNG TỔNG HỢP CÁC LỖI ĐÃ PHÁT HIỆN & KHẮC PHỤC

| Bug ID | Ngày Phát Hiện | Phân Hệ / File Bị Ảnh Hưởng | Loại Lỗi | Trạng Thái | Team Phụ Trách |
| :--- | :---: | :--- | :--- | :---: | :---: |
| `BUG-001` | 2026-08-20 | `core/model_pricing.py` ↔ `core/usage_tracker.py` | Circular Dependency | 🟡 Đã có giải pháp (R09) | Team Duy & Team Nam |
| `BUG-002` | 2026-08-20 | `core/agent_security.py` ↔ `core/agent_security_alert.py` | Circular Dependency | 🟡 Đã có giải pháp (R09) | Team Nam |
| `BUG-003` | 2026-08-20 | `state.py::active_project_id` & `ui/workspace_tab.py` | Race Condition / Global State Leak | 🟡 Đã có giải pháp (R06) | Team Hoa |
| `BUG-004` | 2026-08-20 | `core/task_scheduler.py` ↔ `PySide6.QtCore.QTimer` | Architecture Violation (Qt in Domain/App) | 🟡 Đã có giải pháp (R07) | Team Hoa |
| `BUG-005` | 2026-08-20 | `ui/chat_panel.py#L638`, `ui/co4e_tab.py`, `ui/folder_tab.py` | Code Duplication (Copy Routing Logic) | 🟡 Đã có giải pháp (R03) | Team Duy |
| `BUG-006` | 2026-08-21 | `scripts/check_imports.py` | UnicodeEncodeError (Windows CP932 console emoji) | 🟢 Đã khắc phục (R01) | Team Duy |
| `BUG-007` | 2026-08-21 | `platform/` ➔ `infrastructure/platform/` | Standard Library Shadowing (`import platform`) | 🟢 Đã khắc phục (R01) | Team Duy |

---

## 🔍 CHI TIẾT TỪNG LỖI & QUY TẮC PHÒNG NGỪA

---

### 🔴 `BUG-001`: Circular Import giữa Module Định Giá (`model_pricing.py`) và Theo Dõi Token (`usage_tracker.py`)

* **Phân hệ**: `core/model_pricing.py` & `core/usage_tracker.py`
* **Triệu chứng (Symptom)**: Lỗi `ImportError: cannot import name 'ModelPricing' from partially initialized module` khi khởi động ứng dụng hoặc chạy test độc lập.
* **Nguyên nhân gốc rễ (Root Cause)**:
  - `model_pricing.py` import `UsageTracker` để cập nhật dữ liệu tiêu thụ.
  - Ngược lại, `usage_tracker.py` import `ModelPricing` để tính toán chi phí theo từng model ID.
* **Giải pháp khắc phục (Resolution)**:
  - Tách Data Transfer Object (DTO) `ModelPricing` sang tầng Domain thuần túy `domain/models/model_pricing.py`.
  - Cả `model_pricing.py` và `usage_tracker.py` đều import DTO từ `domain/models/`, chuyển quan hệ thành 1 chiều (Dependency Inversion).
* **Quy tắc phòng ngừa (Prevention Rule - TUYỆT ĐỐI KHÔNG TÁI PHẠM)**:
  > **Quy tắc**: Không bao giờ để 2 service hoặc 2 module nghiệp vụ import lẫn nhau. Mọi cấu trúc dữ liệu dùng chung (DTO/Value Object/Event) **phải được đặt tại tầng `domain/`**.

---

### 🔴 `BUG-002`: Circular Import giữa An Ninh Agent (`agent_security.py`) và Cảnh Báo (`agent_security_alert.py`)

* **Phân hệ**: `core/agent_security.py` & `core/agent_security_alert.py`
* **Triệu chứng (Symptom)**: Lỗi khởi tạo vòng tròn khi runtime bắn ra alert sự kiện bảo mật.
* **Nguyên nhân gốc rễ (Root Cause)**:
  - Module security vừa kiểm tra policy vừa khởi tạo trực tiếp instance alert dialog, trong khi alert dialog lại import ngược lại rule security để hiển thị chi tiết mã lỗi.
* **Giải pháp khắc phục (Resolution)**:
  - Tách sự kiện cảnh báo thành Event DTO `SecurityAlertEvent` tại `domain/security/security_event.py`.
  - Tầng Security chỉ phát ra Event (`emit_event`), tầng Presentation/UI tự lắng nghe Event để render Dialog.
* **Quy tắc phòng ngừa (Prevention Rule - TUYỆT ĐỐI KHÔNG TÁI PHẠM)**:
  > **Quy tắc**: Logic an ninh và xử lý nghiệp vụ không bao giờ được gọi trực tiếp UI Dialog. Luôn giao tiếp thông qua cơ chế Event-Driven (`AgentEvent`, `SecurityEvent`).

---

### 🔴 `BUG-003`: Xung Đột Race Condition do Sử Dụng Biến Toàn Cục `active_project_id` trong `state.py`

* **Phân hệ**: `state.py`, `ui/workspace_tab.py`, Scheduled Task Runners
* **Triệu chứng (Symptom)**: Khi task scheduler chạy ngầm hoặc người dùng chuyển tab nhanh, file bị ghi nhầm vào thư mục dự án khác với dự án đang hiển thị trên màn hình.
* **Nguyên nhân gốc rễ (Root Cause)**:
  - Ứng dụng đọc và ghi trực tiếp vào biến toàn cục `AppContext.active_project_id` từ nhiều luồng khác nhau mà không có cơ chế snapshot ngữ cảnh.
* **Giải pháp khắc phục (Resolution)**:
  - Xóa bỏ việc đọc biến toàn cục. Mỗi lần khởi chạy turn hoặc task, tạo một snapshot bất biến `WorkspaceSession(project_id, root_path, allowed_paths)`.
  - Luồng ngầm chỉ thao tác trên `WorkspaceSession` được truyền vào từ lúc khởi tạo.
* **Quy tắc phòng ngừa (Prevention Rule - TUYỆT ĐỐI KHÔNG TÁI PHẠM)**:
  > **Quy tắc**: Tuyệt đối không dùng biến toàn cục (Global State / Singletons có trạng thái thay đổi) để điều khiển luồng thực thi nền. Mọi ngữ cảnh phải được truyền tường minh qua DTO snapshot.

---

### 🔴 `BUG-004`: Vi Phạm Ranh Giới Kiến Trúc Khi Import `PySide6.QtCore.QTimer` trong Domain / Scheduling Engine

* **Phân hệ**: `core/task_scheduler.py#L20`
* **Triệu chứng (Symptom)**: Không thể viết Unit Test cho thuật toán tính toán lịch chạy (cron/interval) trên môi trường CI/CD (GitHub Actions / Linux Server headless) nếu thiếu driver màn hình X11/Wayland hoặc chưa cài `PySide6`.
* **Nguyên nhân gốc rễ (Root Cause)**:
  - Động cơ lập lịch bị gắn chặt cứng với `QTimer` của framework Qt thay vì tách riêng logic tính toán thời gian.
* **Giải pháp khắc phục (Resolution)**:
  - Tách thuật toán tính lịch sang `domain/tasks/schedule_calculator.py` (Pure Python 100%).
  - Tạo `platform/qt/qt_scheduler_clock.py` làm adapter bọc `QTimer` cho app chạy thật, và `tests/fakes/fake_clock.py` cho unit test.
* **Quy tắc phòng ngừa (Prevention Rule - TUYỆT ĐỐI KHÔNG TÁI PHẠM)**:
  > **Quy tắc**: Tầng Domain và Application tuyệt đối không import thư viện GUI (`PySide6`, `PyQt`). Luôn bọc các thành phần phụ thuộc framework bên ngoài qua Adapter Interface.

---

### 🔴 `BUG-005`: Nhân Bản Mã Nguồn (Code Duplication) Logic Routing Mô Hình AI tại Nhiều Màn Hình

* **Phân hệ**: `ui/chat_panel.py#L638`, `ui/co4e_tab.py`, `ui/folder_tab.py`
* **Triệu chứng (Symptom)**: Khi cập nhật thêm model provider mới (như FPT Gateway hay Claude 3.7), phải sửa code thủ công ở 3 file UI khác nhau; phát sinh sai lệch quy tắc fallback giữa các màn hình.
* **Nguyên nhân gốc rễ (Root Cause)**:
  - Thiếu một tầng Application Service tập trung, dẫn đến việc lập trình viên copy-paste hàm chọn model từ `ChatPanel` sang các tab khác.
* **Giải pháp khắc phục (Resolution)**:
  - Xây dựng `application/model_routing/routing_application_service.py` duy nhất, cung cấp API `route_request(request) -> ModelRouteDecision`.
  - Mọi màn hình UI chỉ gọi service này, không tự viết lại logic kiểm tra key hay fallback.
* **Quy tắc phòng ngừa (Prevention Rule - TUYỆT ĐỐI KHÔNG TÁI PHẠM)**:
  > **Quy tắc**: Nghiệp vụ dùng chung giữa các màn hình phải được đưa vào `application/` services. Không bao giờ viết logic nghiệp vụ trực tiếp trong các file Widget UI.

---

### 🟢 `BUG-006`: `UnicodeEncodeError` khi in Emojis trên Console Windows (CP932/CP1252)

* **Phân hệ / File**: `scripts/check_imports.py`
* **Triệu chứng (Symptom)**:
  ```text
  Traceback (most recent call last):
    File "scripts/check_imports.py", line 127, in main
      print(f"\U0001f6e1\ufe0f  Running Clean Architecture Import Guard...")
  UnicodeEncodeError: 'cp932' codec can't encode character '\U0001f6e1' in position 0: illegal multibyte sequence
  ```
* **Nguyên nhân gốc rễ (Root Cause)**:
  - Trên hệ điều hành Windows sử dụng locale tiếng Nhật (mã trang CP932) hoặc tiếng Anh (CP1252), `sys.stdout` mặc định không hỗ trợ các ký tự Unicode/Emoji ngoài bảng mã, dẫn đến crash khi in log dòng lệnh.
* **Giải pháp khắc phục (Resolution)**:
  - Tự động bọc lại `sys.stdout` và `sys.stderr` bằng `io.TextIOWrapper` với `encoding="utf-8"` và `errors="replace"`.
  - Thay thế các emoji phức tạp bằng các tag văn bản ASCII chuẩn hóa như `[Clean Arch Guard]`, `[PASS]`, `[FAIL]`.
* **Quy tắc phòng ngừa (Prevention Rule - TUYỆT ĐỐI KHÔNG TÁI PHẠM)**:
  > **Quy tắc**: Mọi script CLI (`scripts/*.py`) phải có cơ chế cấu hình `utf-8` stream wrapper và ưu tiên sử dụng text tags (`[INFO]`, `[WARN]`, `[ERROR]`) thay vì emoji Unicode trực tiếp để đảm bảo chạy mượt mà trên mọi môi trường Windows đa ngôn ngữ.

---

### 🟢 `BUG-007`: Xung Đột Tên Thư Mục Trùng Với Standard Library (`platform/` Shadowing `import platform`)

* **Phân hệ / File**: `platform/` ➔ Chuyển thành `infrastructure/platform/`
* **Triệu chứng (Symptom)**:
  ```text
  INTERNALERROR> File "_pytest/terminal.py", line 853: verinfo = platform.python_version()
  INTERNALERROR> AttributeError: module 'platform' has no attribute 'python_version'
  ```
* **Nguyên nhân gốc rễ (Root Cause)**:
  - Khi tạo một package ở thư mục gốc có tên trùng với module thư viện chuẩn của Python (`platform`, `email`, `test`, `asyncio`, `logging`), Python trên `sys.path` sẽ ưu tiên import thư mục local thay vì thư viện chuẩn của Python runtime, dẫn đến crash toàn bộ pytest runner và các thư viện bên thứ ba.
* **Giải pháp khắc phục (Resolution)**:
  - Xóa bỏ package `platform/` ở root.
  - Đưa adapter Qt Scheduler Clock vào đúng vị trí hạ tầng: `infrastructure/platform/qt/`.
* **Quy tắc phòng ngừa (Prevention Rule - TUYỆT ĐỐI KHÔNG TÁI PHẠM)**:
  > **Quy tắc**: Tuyệt đối không đặt tên package/thư mục ở root trùng với tên các module built-in của Python (`platform`, `logging`, `types`, `time`, `io`, `os`, `sys`). Mọi platform adapter phải nằm trong `infrastructure/platform/` hoặc `platform_adapters/`.

---

## 📝 MẪU GHI NHẬN BUG MỚI (BUG REPORT TEMPLATE)

Khi gặp bất kỳ bug mới nào trong quá trình làm việc, hãy sao chép khối mẫu sau và điền vào cuối tài liệu:

```markdown
### 🔴 `BUG-XXX`: [Tóm tắt ngắn gọn tên lỗi]

* **Phân hệ / File**: `[Đường dẫn file bị lỗi]`
* **Triệu chứng (Symptom)**: `[Mô tả hiện tượng lỗi, paste thông báo traceback hoặc kết quả test fail]`
* **Nguyên nhân gốc rễ (Root Cause)**: `[Giải thích tại sao lỗi lại xảy ra]`
* **Giải pháp khắc phục (Resolution)**: `[Mô tả cách sửa, file DTO/Service tạo mới hoặc cách refactor]`
* **Quy tắc phòng ngừa (Prevention Rule - TUYỆT ĐỐI KHÔNG TÁI PHẠM)**:
  > **Quy tắc**: `[Nguyên tắc kỹ thuật cụ thể để không bao giờ tái phạm lỗi này]`
```
