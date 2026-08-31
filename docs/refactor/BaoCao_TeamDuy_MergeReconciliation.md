# BÁO CÁO — ĐỐI SOÁT & VÁ LỖI SAU MERGE ĐA NHÁNH (feature/delta-team/epic-R04)

* **Dự án**: Cowork Local (Cowork-Local BamBOO)
* **Người thực hiện**: Duy Lê Hữu (Team Duy — Tech Lead)
* **Nhánh**: `feature/delta-team/epic-R04`
* **Thời gian**: 27/08/2026 → 30/08/2026
* **Ngày ghi báo cáo**: 30/08/2026

---

## 1. Bối cảnh

Nhánh `feature/delta-team/epic-R04` vừa trải qua nhiều đợt merge liên tiếp gộp việc của cả 3 team (Duy, Nam/Gamma, Hoa) làm song song trên các epic R01→R10. Sau khi hoàn tất merge `origin/feature/teamhoa/r05-r06` (đưa vào R07 + phần còn lại của R08) và merge thêm 2 đợt cập nhật từ `origin/feature/delta-team/epic-R04` (R08 Chat UI Hub, toàn bộ R10, dọn dead code, CASAN Gate O, launcher chính thức), nhánh local có **3 commit merge chưa push** lên origin:

| Commit | Thời gian | Nội dung |
| :--- | :--- | :--- |
| `c7784de` | 28/08 11:40 | Hoàn tất merge `origin/feature/teamhoa/r05-r06` vào `feature/delta-team/epic-R04` |
| `4f0010a` | 28/08 11:57 | Merge cập nhật R08 Chat UI Hub + R10 từ origin |
| `98cee81` | 30/08 12:20 | Merge cập nhật dọn dead code, gộp i18n/theme, CASAN Gate O, launcher |

Đối soát `git diff origin/feature/delta-team/epic-R04..HEAD` cho thấy **7 file khác nhau thật sự** — phần lớn phát sinh từ việc giải quyết xung đột merge (nhánh Team Hoa tách `presentation/folder/*` từ một bản `ui/folder_tab.py` **chưa có** bản vá routing R03), cộng với một file test bị rớt mất qua các đợt merge trước đó nay được khôi phục lại.

Xác nhận trước khi push: `git merge-base --is-ancestor origin/feature/delta-team/epic-R04 HEAD` → **true**, tức đây là **fast-forward tuyệt đối** — không ghi đè, không mất bất kỳ commit nào của ai trên origin.

---

## 2. Các fix thật (thay đổi hành vi)

### 2.1. `presentation/folder/ai_edit_model_resolver.py::apply_routing()` — khôi phục bản vá routing R03 cho surface AI-Edit

**Vấn đề gốc**: nhánh Team Hoa tách `ui/folder_tab.py` thành `presentation/folder/*` (R08-T12) **trước khi** R03 (hợp nhất routing qua `RoutingApplicationService`) được merge vào nhánh đó (`git merge-base --is-ancestor f61c547 origin/feature/teamhoa/r05-r06` → **NO**, xác nhận trước khi vá). Vì vậy bản tách vẫn giữ nguyên lối gọi routing cũ, đã gãy:

```python
# Trước — gọi API routing cũ, constructor không còn khớp chữ ký hiện tại
decision = self.ctx.routing_application().route_turn(
    "ai_edit", instruction, cur_provider, cur_model,
    task_type=TaskType.CODING, confirm=self._confirm_switch,
)
```

**Sau khi vá** — gọi đúng `RoutingApplicationService` hiện hành qua `build_routing_application_service`, bọc `try/except` để một lỗi routing không bao giờ được phép chặn thao tác sửa file (đúng nguyên tắc "routing must never block an edit"):

```python
try:
    from cowork_local.application.model_routing import (
        RoutingRequest, build_routing_application_service,
    )
    from cowork_local.core.routing.models import TaskType

    cur_provider = self.ctx.config.active_provider
    picked = self._combo.currentData()
    cur_model = picked or self.ctx.config.provider_conf(cur_provider).get("model", "")
    outcome = build_routing_application_service(self.ctx).resolve(
        RoutingRequest(
            surface="ai_edit", prompt=instruction,
            current_provider=cur_provider, current_model=cur_model,
            task_type=TaskType.CODING,   # AI-Edit luôn là coding task, không cần phân loại từ prompt
        ),
        confirm=self._confirm_switch,
    )
    if not outcome.switched:
        return
    self._routed_provider = outcome.provider
    self._routed_model = outcome.model
    self._on_status(tr("routing.switched_notice", model=outcome.model,
                        task=outcome.task_type, gain=f"{outcome.score_gain:.2f}"))
except Exception:  # noqa: BLE001 — routing must never block an edit
    self._routed_provider = None
    self._routed_model = None
```

**Thay đổi kèm theo**: `presentation/folder/ai_file_editor_dialog.py::_confirm_routing_switch()` đổi chữ ký thêm tham số `timeout` truyền từ ngoài vào (bỏ việc tự đọc `ctx.config.routing.get("confirm_timeout_sec", 60)` bên trong — API mới của `RoutingApplicationService` cấp timeout qua tham số thay vì để callback tự tra config).

**Ý nghĩa**: khôi phục đúng hiệu lực R03-T05 ("Hợp nhất luồng định tuyến từ `ui/co4e_tab.py` và `ui/folder_tab.py`") cho surface AI-Edit — trước khi vá, surface này sẽ crash hoặc bỏ qua routing hoàn toàn khi người dùng bật Auto/Manual routing trong Folder Explorer.

### 2.2. `config.py` — sửa circular import khi khởi tạo `JsonConfigRepository`

**Trước**: `from .infrastructure.config.json_config_repository import JsonConfigRepository` nằm ở đầu file, trước khi hằng `CONFIG_DIR` được định nghĩa.

**Sau** — dời xuống sau `CONFIG_DIR`, kèm comment giải thích lý do kỹ thuật:

```python
# Deferred: JsonConfigRepository's own import chain (infrastructure.persistence
# .json -> task_repository_impl -> core.tasks) reads CONFIG_DIR back from this
# module, so importing it before CONFIG_DIR exists here is a circular import.
from .infrastructure.config.json_config_repository import JsonConfigRepository
```

**Ý nghĩa**: `JsonConfigRepository` kéo theo `infrastructure/persistence/json/task_repository_impl.py` → `core/tasks.py`, mà `core/tasks.py` (sau R07-T01/T02) lại import `CONFIG_DIR` ngược từ chính `config.py` — import `JsonConfigRepository` quá sớm (trước khi `CONFIG_DIR` tồn tại trong namespace module) tạo vòng lặp import, có thể vỡ tuỳ thứ tự nạp module của Python.

---

## 3. Khôi phục lưới an toàn: `tests/integration/test_routing_surfaces.py` (+254 dòng, 9 test)

File test này tồn tại ở điểm gốc chung (`8ab2980`) giữa các nhánh nhưng bị rớt mất qua một đợt merge trước đó (không xác định được nguyên nhân chính xác — nghi do một conflict resolution merge trước đây chọn nhầm hướng). Team Hoa vẫn giữ nguyên file này trên nhánh của họ và có sửa thêm; đã khôi phục lại vào nhánh chính.

Phạm vi kiểm thử: dựng `CoworkTab`/`Co4ETab`/`FolderTab` thật (offscreen), gọi `RoutingApplicationService` dùng chung, xác nhận: đúng surface key theo từng màn hình, Auto chuyển model đúng luật, Off không hỏi engine, Manual chỉ chuyển khi người dùng xác nhận, một Admin Agent đã ghim vẫn thắng routing, và **surface AI-Edit** (liên quan trực tiếp mục 2.1) cho ra quyết định đúng.

**Đã verify**: `pytest tests/integration/test_routing_surfaces.py -q` → **9 passed**.

---

## 4. Thay đổi không ảnh hưởng hành vi (chỉ docstring)

Phát sinh từ việc giải xung đột merge các file `__init__.py` (chọn bản mô tả đầy đủ hơn thay vì placeholder một dòng) — import/export giữ nguyên 100%:

| File | Thay đổi |
| :--- | :--- |
| `domain/tasks/__init__.py` | Docstring mô tả rõ phạm vi EPIC R07 |
| `infrastructure/persistence/json/__init__.py` | Docstring nêu rõ EPIC R06 + R07 cùng dùng chung layer này |
| `application/monitoring/__init__.py` | Docstring ghi chú vấn đề sở hữu thư mục giữa Team Nam (R08-T07→T10) và Team Hoa (R08-T13) — cần Team Nam xác nhận khi bắt đầu phần của họ |

---

## 5. Kết quả kiểm chứng trước khi push

| # | Kiểm tra | Lệnh | Kết quả |
| :---: | :--- | :--- | :--- |
| 1 | Fast-forward an toàn | `git merge-base --is-ancestor origin/... HEAD` | ✅ true |
| 2 | Test routing surfaces (khôi phục) | `pytest tests/integration/test_routing_surfaces.py -q` | ✅ 9 passed |
| 3 | CASAN Quality Gate đầy đủ (C/A/S/O + pytest toàn repo) | `python scripts/run_quality_gate.py` | ✅ ALL GATES PASSED |
| 4 | App khởi động thật | `run.bat` | ✅ Cửa sổ "Cowork-Local BamBOO" mở, không lỗi |

---

## 6. Còn nợ / cần theo dõi tiếp

* `application/monitoring/__init__.py` cần Team Nam xác nhận quyền sở hữu thư mục khi họ bắt đầu R08-T07→T10 (đã ghi chú ngay trong docstring).
* Chưa xác định được **nguyên nhân gốc** khiến `tests/integration/test_routing_surfaces.py` từng bị rớt khỏi nhánh chính ở một merge trước đó — nên rà lại quy trình resolve conflict cho các lần merge lớn tiếp theo để tránh lặp lại (đã có 2 trường hợp tương tự: file test này và class `ToolInvocation` trong `tests/fakes/fake_tool_executor.py`).
