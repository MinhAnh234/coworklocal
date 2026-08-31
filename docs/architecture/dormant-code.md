# Danh Mục & Kế Hoạch Cô Lập Mã Nguồn Dormant / Dead Code (Dormant Code Catalog)

* **Tài liệu**: `docs/architecture/dormant-code.md`
* **Thuộc EPIC**: `R01: Architecture Foundation & Characterization`
* **Team phụ trách**: 🔵 **Team Duy (Tech Lead)**

---

## 1. Mục Đích & Nguyên Tắc Quản Trị

Trong quá trình phát triển nhanh, một số module, hàm hoặc script đã trở thành mã nguồn không hoạt động (**dormant**), mã nguồn thử nghiệm cũ (**legacy prototypes**), hoặc mã nguồn không còn được sử dụng (**dead code**).

> [!IMPORTANT]
> ### 🛡️ NGUYÊN TẮC CÔ LẬP MÃ NGUỒN CŨ:
> 1. **Tuyệt đối không import vào các tầng mới**: Các tầng `domain/`, `application/`, `infrastructure/` mới được xây dựng **cấm tuyệt đối import bất kỳ module dormant nào**.
> 2. **Không xóa vội vàng khi chưa có test bảo vệ**: Giữ nguyên mã nguồn cũ trong giai đoạn tái cấu trúc R01–R08; chỉ dọn dẹp hoặc xóa sau khi bộ kiểm thử khói E2E (EPIC R10) chạy pass 100%.
> 3. **Phân loại rõ ràng trạng thái**: Mỗi module dormant phải được gắn nhãn (DEPRECATED / ISOLATED / PENDING_DELETION).

---

## 2. Bảng Danh Mục Mã Nguồn Dormant / Dead Code Đã Rà Soát

| STT | File / Module / Ký Hiệu | Trạng Thái Hiện Tại | Lý Do Phân Loại & Phân Tích Kỹ Thuật | Kế Hoạch Xử Lý & Thời Điểm Gỡ Bỏ |
| :---: | :--- | :---: | :--- | :--- |
| **1** | `requirements (cloud copy).txt` | `PENDING_DELETION` | File sao chép dự phòng tạm thời trong quá khứ, không được tham chiếu bởi bất kỳ quy trình setup nào. | Gỡ bỏ trong EPIC R10 (Packaging & Clean-up). |
| **2** | `preview-desktop` | `ISOLATED` | Script shell rỗng/phác thảo cho môi trường dev container cũ. | Cô lập, không liên kết vào build workflow. |
| **3** | `scripts/bootstrap_gitea_repo.py` | `ISOLATED` | Script tiện ích bootstrap kho lưu trữ Gitea nội bộ; không thuộc runtime ứng dụng chính. | Di chuyển vào `docs/gitea/` làm tài liệu tham khảo ops. |
| **4** | Hàm routing sao chép tại `ui/chat_panel.py#L638` | `DEPRECATED` | Đoạn code logic chọn model lặp lại từ `core/routing/` nằm trực tiếp trong UI widget. | Thay thế hoàn toàn bằng `RoutingApplicationService` trong EPIC R03. |
| **5** | Biến toàn cục `state.py::active_project_id` | `DEPRECATED` | Biến global mutable gây race condition khi chạy background task song song. | Thay thế bằng `WorkspaceSession` trong EPIC R06. |
| **6** | Các hàm xử lý UI đồng bộ trong `core/tools.py` | `DEPRECATED` | `core/tools.py` chứa mã monolithic vừa xử lý file vừa gọi dialog xác thực trực tiếp. | Phân rã thành `file_tools.py`, `command_tools.py` và `ToolPolicyGateway` trong EPIC R05. |

---

## 3. Quy Trình Cô Lập & Kiểm Soát

1. **Kiểm tra tự động qua AST Guard**:
   - Bộ script `scripts/check_imports.py` tự động quét để đảm bảo không có bất kỳ import mới nào trỏ tới các thành phần đã đánh dấu deprecated.
2. **Kế hoạch dọn dẹp cuối cùng (Release Phase - 31/08/2026)**:
   - Sau khi hoàn thành EPIC R10 và pass toàn bộ bài test E2E (`tests/e2e/test_smoke.py`), các file đánh dấu `PENDING_DELETION` sẽ được gỡ bỏ khỏi nhánh `main`.
