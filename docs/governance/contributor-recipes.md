# Contributor Recipes — Hướng Dẫn Mở Rộng Hệ Thống (EPIC R10-T04)

Tài liệu này cung cấp các công thức chuẩn hóa (Step-by-Step Recipes) giúp các lập trình viên mở rộng tính năng trong hệ thống **Cowork Local** mà vẫn tuân thủ tuyệt đối **Kiến trúc 4 Tầng Sạch (4-Tier Clean Architecture)** và các tiêu chuẩn kiểm duyệt **CASAN**.

---

## 🍳 Recipe 1: Thêm Một Model Provider Mới (AI Provider)

Khi bạn muốn tích hợp một nhà cung cấp mô hình AI mới (ví dụ: Cohere, Groq, DeepSeek, AWS Bedrock...):

### Bước 1: Khai báo định danh trong Domain Layer
Mở file [`domain/models/provider_descriptor.py`](file:///c:/Users/HuongLTT35/OneDrive%20-%20FPT%20Corporation/Documents/ITCorreTeam/CoworkLocal/cowork_local/domain/models/provider_descriptor.py):
- Thêm định danh provider vào enum hoặc hằng số.
- Khai báo model mặc định và năng lực hỗ trợ (Streaming, Tool Calling, Vision, Reasoning).

### Bước 2: Cài đặt Adapter trong Infrastructure Layer
Tạo file mới tại `infrastructure/providers/<provider_name>_provider.py` (hoặc mở rộng module hiện có):
- Kế thừa lớp `BaseModelProvider` hoặc cài đặt interface adapter tương ứng.
- Đảm bảo xử lý streaming qua generator / callbacks.
- Đọc API key từ `SecretStore` (Keyring), tuyệt đối không lưu hardcoded credentials.

```python
# infrastructure/providers/custom_provider.py
from cowork_local.domain.models.provider_descriptor import ProviderDescriptor

class CustomProviderAdapter:
    """Adapter for Custom AI Provider supporting streaming and tool execution."""
    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        self._api_key = api_key
        self._base_url = base_url

    def stream_chat(self, prompt: str, system_prompt: str = ""):
        # Yield text chunks
        yield "..."
```

### Bước 3: Đăng ký vào Provider Registry
Mở [`infrastructure/providers/provider_registry.py`](file:///c:/Users/HuongLTT35/OneDrive%20-%20FPT%20Corporation/Documents/ITCorreTeam/CoworkLocal/cowork_local/infrastructure/providers/provider_registry.py):
- Đăng ký adapter factory vào registry.

### Bước 4: Viết Contract Test
Mở [`tests/contracts/test_providers.py`](file:///c:/Users/HuongLTT35/OneDrive%20-%20FPT%20Corporation/Documents/ITCorreTeam/CoworkLocal/cowork_local/tests/contracts/test_providers.py):
- Thêm test case kiểm tra hợp đồng cho Provider mới bằng `FakeProvider` hoặc offline contract.

---

## 🛠️ Recipe 2: Thêm Một Tool Nội Bộ Hoặc Kết Nối MCP Server Mới

### Bước 1: Khai báo Tool Descriptor & Quyền Hạn
Mở [`domain/models/tool_descriptor.py`](file:///c:/Users/HuongLTT35/OneDrive%20-%20FPT%20Corporation/Documents/ITCorreTeam/CoworkLocal/cowork_local/domain/models/tool_descriptor.py):
- Định nghĩa tên tool, mô tả, JSON Schema tham số.
- Thiết lập cờ Capability: `READ_ONLY`, `GATED`, `DANGEROUS`, v.v.

### Bước 2: Cài đặt Tool Executor
- Nếu là Built-in Tool: Cài đặt trong `infrastructure/tools/` hoặc tích hợp qua `ToolPolicyGateway`.
- Nếu là MCP Server: Cấu hình qua `infrastructure/mcp/mcp_tool_source_manager.py` với stdin/stdout JSON-RPC protocol.

```python
# Example: Adding a safe read-only tool
descriptor = ToolDescriptor(
    name="system_disk_usage",
    description="Inspect available disk space on the local workstation.",
    parameters_schema={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
    capabilities=ToolCapability.READ_ONLY,
)
```

### Bước 3: Viết Unit Test & Kiểm Tra Gate
- Thêm test case vào `tests/unit/test_tool_registry_and_policy.py`.
- Xác nhận tool tôn trọng cờ an toàn (`ToolPolicyGateway`) trước khi thực thi.

---

## 🖥️ Recipe 3: Thêm Một Màn Hình / Tab / Widget Giao Diện Mới

### Bước 1: Tạo module dưới `presentation/<feature>/`
- Tạo thư mục riêng (ví dụ: `presentation/analytics/`).
- Tách các widget con nhỏ gọn, **mỗi file < 400 dòng code (LOC)**.
- Giao diện kế thừa `PySide6.QtWidgets.QWidget` và sử dụng CSS token từ `cowork_local.theme`.

```python
# presentation/analytics/analytics_tab.py
"""Analytics Tab Widget (LOC < 400)."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from cowork_local.state import AppContext
from cowork_local.i18n import tr

class AnalyticsTab(QWidget):
    """Analytics view displaying workspace telemetry."""
    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.title = QLabel(tr("analytics.title") if tr("analytics.title") != "analytics.title" else "Analytics Dashboard")
        layout.addWidget(self.title)
```

### Bước 2: Nối Dữ Liệu Qua Tầng Application Service
- **QUY TẮC CỐT TỬ**: Widget giao diện CHỈ ĐƯỢC gọi xuống các Service của tầng `application/` (ví dụ: `TaskApplicationService`, `DashboardQueryService`, `ConversationApplicationService`).
- Tuyệt đối không query trực tiếp SQLite/JSON hoặc thực thi AI logic trực tiếp trong GUI thread.

### Bước 3: Đăng Ký Vào Shell Navigation
- Mở [`presentation/shell/page_registry.py`](file:///c:/Users/HuongLTT35/OneDrive%20-%20FPT%20Corporation/Documents/ITCorreTeam/CoworkLocal/cowork_local/presentation/shell/page_registry.py) và thêm trang mới vào danh sách menu điều hướng (`NavRail`).

### Bước 4: Viết Integration Test Cho Widget
- Tạo file test dưới `tests/integration/` hoặc `tests/ui/`.
- Đảm bảo test chạy được ở chế độ headless (`QT_QPA_PLATFORM=offscreen`).

---

## 🛡️ Kiểm Duyệt Chất Lượng Trước Khi Gửi PR (Checklist CASAN)

Trước khi commit và tạo Pull Request, chạy lệnh kiểm tra tổng thể:
```bash
python scripts/run_quality_gate.py
```
Nếu toàn bộ 4 cổng báo `[PASS]` thì mã nguồn của bạn đã sẵn sàng được merge vào nhánh chính!
