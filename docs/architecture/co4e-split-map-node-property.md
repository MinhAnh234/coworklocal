# Bản đồ tách `StepConfigPanel` (`ui/co4e_config_panel.py` → `presentation/co4e/`)

- **Phạm vi lượt này:** chỉ `StepConfigPanel` (nguyên bản dòng 1-528 của
  `ui/co4e_config_panel.py`). Không đụng file nào khác thuộc làn N1
  (`ui/co4e_tab.py`, `ui/co4e_canvas.py`, `docs/architecture/co4e-split-map.md`/`.json`).
- **Lý do phải tách thêm, dù chỉ 1 class:** `StepConfigPanel` một mình đã 396
  dòng (133-528); cộng thêm module docstring + khối import của một file riêng
  sẽ vượt trần 400 dòng (CASAN Check 2). Giải pháp: cắt-dán (không viết lại
  logic) thành 3 file theo trách nhiệm.

## File đích

| symbol | dòng gốc | file đích | ghi chú |
|---|---|---|---|
| `_SECTION_ANIM_MS` | 27 | `presentation/co4e/step_config_section.py` | hằng số dùng bởi `_add_section` |
| `_SectionHeader` | 30-52 | `presentation/co4e/step_config_section.py` | `QLabel` clickable, không có hành vi nghiệp vụ riêng |
| `_add_section` | 55-130 | `presentation/co4e/step_config_section.py` | khung ▶/▼ dùng chung cho 4 nhóm trường của `StepConfigPanel`; không đọc/ghi state của panel |
| `StepConfigPanel` (Signal + `__init__`) | 133-313 | `presentation/co4e/node_property_panel.py` | 4 Signal (`changed`/`run_node`/`run_from`/`delete_node`) + dựng toàn bộ form |
| `StepConfigPanel.load_step` | 316-354 | `presentation/co4e/node_property_panel.py` | nạp `Step` vào form |
| `StepConfigPanel.clear_step` | 356-359 | `presentation/co4e/node_property_panel.py` | xoá state, tắt panel |
| `StepConfigPanel._on_edit` | 362-378 | `presentation/co4e/node_property_panel.py` | ghi field UI ngược vào `Step` |
| `StepConfigPanel._available_agent_names` | 380-390 | `presentation/co4e/node_property_actions_mixin.py` (`_StepConfigActionsMixin`) | staticmethod, dùng bởi `_add_subagent`/`_edit_subagent` |
| `StepConfigPanel._add_subagent` | 392-408 | `presentation/co4e/node_property_actions_mixin.py` | |
| `StepConfigPanel._edit_subagent` | 410-428 | `presentation/co4e/node_property_actions_mixin.py` | |
| `StepConfigPanel._del_subagent` | 430-437 | `presentation/co4e/node_property_actions_mixin.py` | |
| `StepConfigPanel._add_attachment` | 439-453 | `presentation/co4e/node_property_actions_mixin.py` | |
| `StepConfigPanel._del_attachment` | 455-462 | `presentation/co4e/node_property_actions_mixin.py` | |
| `StepConfigPanel._ai_draft` | 464-498 | `presentation/co4e/node_property_actions_mixin.py` | dùng `AgentWorker` thật (không mock trong `__init__`) |
| `StepConfigPanel._load_models` | 500-528 | `presentation/co4e/node_property_actions_mixin.py` | dùng `AgentWorker` thật |

## Cách ghép lại: mixin + đa kế thừa

`node_property_panel.py`:
```python
class StepConfigPanel(_StepConfigActionsMixin, QScrollArea):
    ...
```

`_StepConfigActionsMixin` là mixin THUẦN — không `__init__` riêng, chỉ đọc/ghi
state có sẵn trên `self` do `StepConfigPanel.__init__` định nghĩa
(`self._step`, `self._node_id`, `self.ctx`, `self.sub_list`, `self.attach_list`,
`self.instructions_edit`, `self.gen_btn`, `self.model_combo`,
`self.load_models_btn`).

Khác với bước `co4e_canvas_widget.py` (Co4ECanvas override nhiều method Qt như
`paintEvent`/`mousePressEvent`, nên thứ tự mixin-trước-base là **bắt buộc** để
MRO ưu tiên override của mixin): ở đây **không có method nào của
`_StepConfigActionsMixin` trùng tên với `QScrollArea`**, nên thứ tự kế thừa
không ảnh hưởng hành vi. Giữ thứ tự mixin-trước chỉ để nhất quán quy ước, không
phải yêu cầu kỹ thuật bắt buộc.

## Import thừa cố ý giữ nguyên

`PROVIDER_LABELS` (nguyên bản dòng 21, `from ..config import PROVIDER_LABELS`)
không được dùng ở đâu trong toàn bộ `ui/co4e_config_panel.py` gốc (đã xác minh
bằng grep). Vẫn giữ nguyên import này trong `node_property_panel.py` (chỉ đổi
số cấp `..` → `...`), không xoá, để đúng phạm vi "chỉ dời chỗ" của lượt tách
này — xoá một import "thừa" là một quyết định dọn dẹp ngoài phạm vi được giao.

## Thay đổi comment/test ngoài phạm vi "chỉ dời chỗ" (ghi riêng, không lẫn vào phần move)

1. **Docstring module của 3 file mới** (`step_config_section.py`,
   `node_property_actions_mixin.py`, `node_property_panel.py`) — viết MỚI hoàn
   toàn bằng tiếng Việt theo quy ước CASAN cho file mới trong `presentation/`
   (mẫu `infrastructure/persistence/json/atomic_json_file.py`). Đây không phải
   sửa một comment cũ bị sai do dời chỗ — module docstring nguyên bản (dòng
   1-9 của `ui/co4e_config_panel.py`) mô tả cả file cũ (đã bị chia làm 3), nên
   mỗi file mới cần một docstring kiến trúc riêng thay vì copy y hệt bản gốc.
2. **`ui/co4e_config_panel.py`** (file cũ) — docstring được viết lại (vẫn
   tiếng Anh, khớp quy ước "sửa file cũ tiếng Anh thì giữ tiếng Anh") để nói rõ
   `StepConfigPanel` đã dời đi đâu, thay vì mô tả hành vi như thể class còn
   định nghĩa tại chỗ — comment cũ sẽ SAI (nói rằng lớp "ở đây" trong khi
   không còn) nếu giữ nguyên.
3. **`tests/characterization/test_node_property_panel.py`** (dòng ~296-307
   nguyên bản) — SỬA kỹ thuật patch/restore của case
   `CASE_ADD_SUBAGENT_EMPTY_NAMES_USES_GETTEXT_QUIRK_OK`, không đổi bất kỳ
   assert/hành vi nào. Bản gốc dùng
   `StepConfigPanel.__dict__["_available_agent_names"]` để lưu lại method gốc
   trước khi monkey-patch, rồi gán lại y hệt lúc restore. Sau khi
   `_available_agent_names` chuyển vào `_StepConfigActionsMixin` (mixin riêng),
   nó không còn nằm trong `StepConfigPanel.__dict__` (chỉ được kế thừa qua
   MRO) → `KeyError`. Thay bằng: gán đè trực tiếp lên `StepConfigPanel` (vẫn
   shadow đúng như cũ), và khi xong dùng `del StepConfigPanel._available_agent_names`
   để nó rơi trở lại đúng method kế thừa từ mixin — hành vi quan sát được của
   test (các assert `sub_agents`) giữ nguyên 100%, chỉ đổi CÁCH lưu/khôi phục
   attribute bị monkey-patch. Đây là hệ quả tất yếu của yêu cầu tách mixin
   trong lượt này (test được viết khi class còn nguyên khối), không phải sửa
   test để che một thay đổi hành vi.

## Xác minh

- `.venv/Scripts/python.exe tools/check_co4e.py` — chạy TRƯỚC và SAU khi sửa,
  output giống hệt nhau cả 2 lần (`KET QUA: Co4E sap xep lai, khong mat control nao`).
- `.venv/Scripts/python.exe -m pytest tests/characterization/test_node_property_panel.py -q`
  — `1 passed` cả trước (đo trên code gốc, class còn ở `ui/co4e_config_panel.py`)
  lẫn sau khi tách.
- `.venv/Scripts/python.exe -m pytest tests -q --tb=short -rf --continue-on-collection-errors`
  — `287 passed, 1 skipped` sau khi tách (không có test nào khác vỡ vì import
  `StepConfigPanel` từ `ui/co4e_config_panel.py`).
- AST-scan `domain/`+`application/` cho import PySide6/PyQt: `KHONG CO`.
- Số dòng file mới: `node_property_panel.py` 293, `node_property_actions_mixin.py`
  202, `step_config_section.py` 134 — cả 3 đều ≤ 400.
