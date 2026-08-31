# Báo cáo refactor — Chat view / Composer (widget cuối) — làn N3 Co4E Studio

- **Ngày:** 2026-08-25
- **Người:** Lâm (hiephv3@fpt.com)
- **Nhánh:** `gamma/refactor`
- **Phạm vi:** trích xuất `_ChatInput`, `_skill_names`, `_agent_names`, `_directive_token`
  và phần dựng UI của `ChatPanel` (từ `_build_chat` cũ) trong `ui/co4e_tab.py` sang
  `presentation/co4e/co4e_chat_view.py`.

---

## 1. Số test thay đổi thế nào so với baseline

Lệnh đo (chạy lại đúng lệnh baseline ngay trước khi viết báo cáo này):

```
.venv/Scripts/python.exe -m pytest tests -q --tb=no -rA --continue-on-collection-errors
```

Kết quả vừa đo:

```
347 passed, 1 skipped in 8.10s
```

So với baseline được giao (Phase 0): `346 passed, 0 failed, 0 collection_errors, 1 skipped`.

| | Trước (Phase 0) | Sau (vừa đo lại) |
|---|---|---|
| passed | 346 | 347 |
| failed | 0 | 0 |
| collection_errors | 0 | 0 |
| skipped | 1 (giữ nguyên, lý do đã biết — thứ tự import `CONFIG_DIR` giữa các file test, không liên quan chat view) | 1 (cùng lý do) |

**+1 passed** đúng bằng đúng 1 test mới `tests/characterization/test_co4e_chat_view.py`
được thêm trong đợt này. Không có test fail mới, không có collection error mới →
**không hồi quy**.

- Lỗi MỐC CŨ có từ trước (nợ của làn khác): **không có** — 0 collection error, 0 failed
  ở cả trước và sau.
- Flaky đã biết (`tests/test_atomic_json.py::test_ghi_de_nhieu_lan_van_dung`,
  `PermissionError [WinError 5]` khi Windows giữ khoá file tạm): **không xuất hiện**
  trong lần đo cuối cùng này (347 passed, 0 failed). Trong lượt soát trước đó nó có
  xuất hiện đúng 1 lần trên 2 lần chạy (`1 failed, 346 passed, 1 skipped`), rồi lần
  chạy kế tiếp lại xanh (`347 passed, 1 skipped`) — đúng đặc điểm flaky đã biết, không
  quy cho đợt trích xuất này.

## 2. File đã tạo, file đã sửa

Theo `git status --porcelain` (đối chiếu với whitelist được cấp cho lượt chat-view):

**Tạo mới (thuộc lượt này):**
- `presentation/co4e/co4e_chat_view.py` — file production mới (258 dòng, ≤ 400 dòng,
  chỉ import PySide6.QtCore/QtWidgets, không đụng domain/application).
- `tests/characterization/test_co4e_chat_view.py` — test đặc trưng hoá hành vi cũ.
- `docs/architecture/co4e-split-map-chat-view.md`
- `docs/architecture/co4e-split-map-chat-view.json`
- `docs/architecture/co4e-refactor-run-report-chat-view.md` — chính file báo cáo này
  (trước lượt này file chưa tồn tại — đây là khoảng thiếu mà bước soát đã ghi nhận,
  nay bù lại).

**Sửa (thuộc lượt này):**
- `ui/co4e_tab.py` — dây lại để dùng `ChatPanel`/`_ChatInput` từ module mới thay vì
  định nghĩa tại chỗ.

**Các mục khác trong `git status` (canvas widget, node property, run control, agent
panel, run manager, v.v.) không thuộc lượt chat-view** — đó là dấu vết của các làn/
phiên khác đang chạy song song trên cùng thư mục làm việc (repo này có nhiều phiên
Claude chạy đồng thời). Không đụng, không sửa trong lượt này.

## 3. Cổng chặn (Phase 5)

**Kết quả: ĐỎ** (`"clean": false`).

Tuy nhiên toàn bộ vi phạm liệt kê **không thuộc phần lượt chat-view đã viết ra** — kiểm
tra riêng 5 đường dẫn thuộc whitelist của lượt này
(`presentation/co4e/co4e_chat_view.py`, `tests/characterization/test_co4e_chat_view.py`,
`docs/architecture/co4e-split-map-chat-view.md`, `.json`, `ui/co4e_tab.py`): **không có
đường dẫn nào trong 5 file này xuất hiện trong danh sách `violations`.**

Danh sách vi phạm thật (đỏ) đến từ file của các làn khác đang tồn tại chung trong working
tree (không do lượt chat-view tạo ra):

- `FORBIDDEN` (khớp `forbidden_paths` của N1): `presentation/co4e/canvas_interaction_mixin.py`,
  `canvas_items.py`, `co4e_canvas_widget.py`, `co4e_run_control_widget.py`,
  `node_property_actions_mixin.py`, `node_property_panel.py`, `step_config_section.py`,
  `ui/co4e_canvas.py`, `ui/co4e_config_panel.py`, cùng các `docs/architecture/co4e-split-map*.md/json`
  và `co4e-refactor-run-report*.md` khác của N1.
- `OUTSIDE_WHITELIST` (file mới không khớp `allowed_write_globs` của *lượt này*):
  `application/workflows/co4e_workflow_service.py`, `domain/workflows/run_record.py`,
  `presentation/co4e/agent_list_panel.py`, `canvas_geometry.py`,
  `presentation/co4e/co4e_tab.py` (khác `ui/co4e_tab.py` được phép), `skills_list_panel.py`,
  và các test/fakes tương ứng (`test_co4e_agent_panel.py`, `test_co4e_canvas_geometry.py`,
  `test_co4e_canvas_widget.py`, `test_co4e_run_manager_behavior.py`, `test_co4e_runs_page.py`,
  `test_co4e_skills_panel.py`, `test_node_property_panel.py`, `fake_co4e_workflow_service.py`,
  `test_build_co4e_tab.py`, `test_co4e_workflow_service.py`).

Kết luận: cổng chặn báo đỏ ở mức **toàn working tree**, không phải đỏ do lượt
chat-view — vì cổng chặn quét nguyên `git status` chung, còn nhiều làn/phiên khác đang
ghi đè cùng thư mục. Phần việc riêng của lượt chat-view (5 đường dẫn whitelist) **sạch**.

## 4. Bước soát output — 2 lượt

Không có phát hiện ở mức **CHAN** (chặn) trong bất kỳ lượt soát nào — cả hai lượt đều
có `verdict: "DAT"` (đạt).

**Lượt 1 — soát `tests/characterization/test_co4e_chat_view.py`:** verdict **DAT**.
Một phát hiện mức `SUA`:
- Dòng 193: `assert ci._popup.width() == max(280, ci.width())` — assertion rỗng nghĩa
  cho riêng claim "280" vì `ci.width()` mặc định (chưa show/setFixedWidth) là 640 trong
  môi trường test, luôn thắng trong `max()` bất kể 280 đổi thành gì < 640. Xác nhận bằng
  mutation thật (280→300 trong `ui/co4e_tab.py`): test vẫn xanh (`1 passed in 2.01s`).
  23 case còn lại trong file đều bắt được mutation tương ứng (11/12 hành vi bị làm hỏng
  → test đỏ đúng như kỳ vọng).

**Lượt 2 — soát `presentation/co4e/co4e_chat_view.py`:** verdict **DAT**. Hai phát hiện
mức `SUA`, một mức `GHI_NHAN`:
- `SUA`: `docs/architecture/co4e-refactor-run-report-chat-view.md` (đúng file này) chưa
  tồn tại tại thời điểm soát — thiếu deliverable bắt buộc của quy trình. **Đã bù lại
  bằng chính báo cáo này.**
- `SUA`: docstring module (dòng 6-7, 15-18) trích sai số dòng gốc trong `ui/co4e_tab.py`
  (lệch 3-35 dòng, ví dụ `_build_chat` ghi "1030-1093" nhưng thật là "1065-1128" theo
  `git show HEAD`). Không ảnh hưởng hành vi — thân hàm đã được đối chiếu bằng
  `ast.get_source_segment` + `difflib` và **IDENTICAL** 100% với bản gốc. Đây là lỗi
  trích dẫn tài liệu, chưa sửa trong lượt viết báo cáo này (ngoài phạm vi được giao cho
  lượt này — chỉ viết báo cáo, không sửa code sản xuất).
- `GHI_NHAN`: hai file `docs/architecture/co4e-refactor-run-report-node-property.md` và
  `co4e-refactor-run-report-run-control.md` (thuộc `forbidden_paths` của lượt chat-view)
  có thay đổi/tồn tại — nhưng nội dung xác nhận thuộc lane khác (node-property, run-control),
  không phải do lượt chat-view đụng vào. Không quy lỗi cho lượt này.

Ngoài ra, bước soát đã tự chạy lại bộ test 2 lần độc lập để loại trừ flaky trước khi kết
luận: lần 1 gặp `1 failed` (đúng flaky `test_atomic_json` đã biết), lần 2 `347 passed,
1 skipped, 0 failed` — nhất quán với con số ở mục 1.

## 5. Việc để lại cho lần chạy sau / cần báo người khác

**Để lại cho lần sau (trong phạm vi lượt chat-view, chưa làm ở lượt viết báo cáo này):**
- Sửa docstring module trong `presentation/co4e/co4e_chat_view.py` (dòng 6-7, 15-18) để
  khớp đúng số dòng thật trong `ui/co4e_tab.py` (HEAD): `_skill_names` 60-64,
  `_agent_names` 67-70, `_directive_token` 121-133, `_ChatInput` 136-225, `_build_chat`
  1065-1128 — hiện ghi sai (63-73, 124-228, 1030-1093).
- Làm chặt lại assertion popup-width-floor tại `tests/characterization/test_co4e_chat_view.py:193`
  (claim "280" hiện không được khoá thật vì `ci.width()` mặc định 640 luôn thắng trong
  `max()`) — cần set `ci` về chiều rộng nhỏ hơn 280 trước khi assert, hoặc mock riêng, để
  test thực sự khoá hằng số 280.
- `ui/co4e_tab.py` vẫn còn nhiều phần khác chưa tách (không thuộc phạm vi widget
  chat/composer) — các widget khác đã có báo cáo riêng của N1
  (`canvas-widget`, `node-property`, `run-control`).

**Cần báo người khác trong team:** không có phát hiện mới nào ngoài phạm vi làn này cần
escalate ở lượt này. Ghi nhận (không phải lỗi mới, chỉ là quan sát): repo đang có nhiều
phiên Claude/nhiều làn chạy song song trên cùng một working tree, khiến cổng chặn của
lượt chat-view báo đỏ ở mức toàn cục do file của các làn khác — điều này không phải do
lượt chat-view gây ra và không cần hành động thêm từ N3, nhưng đội điều phối nên biết để
không hiểu nhầm là lượt này làm vỡ ranh giới của N1.
