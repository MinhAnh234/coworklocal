# Báo cáo hoàn tất — extract:co4e_canvas_widget (lane N3 — Co4E Studio)

- **Ngày:** 2026-08-25
- **Người:** hiephv3@fpt.com (N3)
- **Nhánh:** `gamma/refactor`
- **Lệnh đo dùng xuyên suốt:** `.venv/Scripts/python.exe -m pytest tests -q --tb=no -rA --continue-on-collection-errors`

---

## 1. Số test thay đổi so với baseline

Baseline (Phase 0, trước khi tách):

```
323 passed, 1 skipped in 9.34s
```

Đo lại sau khi tách — chạy 3 lần liên tiếp trong lượt này:

| Lần | Kết quả |
|---|---|
| 1 | `1 failed, 345 passed, 1 skipped in 12.25s` — `FAILED tests/test_no_ignored_source.py::test_khong_file_py_nao_bi_bo_quen_chua_theo_doi` |
| 2 | `346 passed, 1 skipped in 13.31s` |
| 3 | `346 passed, 1 skipped in 12.48s` |

| | passed | failed | collection_errors | skipped |
|---|---|---|---|---|
| Trước (baseline) | 323 | 0 | 0 | 1 |
| Sau (lần 2, 3 — ổn định) | 346 | 0 | 0 | 1 |

**Về cái fail ở lần 1 — KHÔNG phải hồi quy của lane canvas-widget.** Tại đúng thời điểm chạy lần 1, `git status --porcelain` cho thấy `tests/characterization/test_co4e_runs_page.py` và `presentation/co4e/co4e_run_control_widget.py` đang ở trạng thái untracked (`??`) — đây là sản phẩm của một phiên Claude khác (lane run-control) đang làm việc song song trên cùng thư mục và chưa kịp `git add`. `test_no_ignored_source` kiểm tra "mọi file `.py` phải đã được git add trong clone sạch", nên nó bắt trúng khoảnh khắc file kia chưa staged — đây chính là kiểu hiện tượng "nhiều phiên Claude song song" mà tài liệu hướng dẫn có cảnh báo. Kiểm tra lại `git status` ngay sau đó xác nhận hai file này đã chuyển sang trạng thái `A` (đã add), và lần đo 2, 3 chạy lại đều xanh ổn định (346 passed, 0 failed cả hai lần) — không phải flaky do code của lane này, không phải do `test_atomic_json` (test flaky đã biết) xuất hiện lần nào trong 3 lần chạy.

Kết luận: `passed` tăng 323 → 346 (+23, đến từ bộ test đặc tả mới `test_co4e_canvas_widget.py` của lane này cộng với các lane khác đang chạy song song trên cùng nhánh). Không có test fail mới thuộc phạm vi lane canvas-widget. `collection_errors` = 0 ở cả hai mốc. `skipped` giữ nguyên 1 (mốc cũ có giải thích trong docstring, không phải nợ phát sinh từ lane này).

---

## 2. File tạo mới / đã sửa

**Tạo mới (thuộc phạm vi lane canvas-widget):**
- `presentation/co4e/co4e_canvas_widget.py`
- `presentation/co4e/canvas_items.py`
- `presentation/co4e/canvas_interaction_mixin.py`
- `tests/characterization/test_co4e_canvas_widget.py`
- `docs/architecture/co4e-split-map-canvas-widget.md`
- `docs/architecture/co4e-split-map-canvas-widget.json`
- `docs/architecture/co4e-refactor-run-report-canvas-widget.md` (chính file này)

**Đã sửa:**
- `ui/co4e_canvas.py` — giữ lại làm shim tương thích ngược, xem mục 5.

**Không thuộc lane này** (xuất hiện trong `git status --porcelain` chung của repo, do các lane khác — node-property, run-control, v.v. — đang chạy song song, liệt kê để tránh nhận vơ): `application/workflows/co4e_workflow_service.py`, `domain/workflows/run_record.py`, `presentation/co4e/agent_list_panel.py`, `presentation/co4e/canvas_geometry.py`, `presentation/co4e/co4e_tab.py`, `presentation/co4e/node_property_panel.py`, `presentation/co4e/node_property_actions_mixin.py`, `presentation/co4e/skills_list_panel.py`, `presentation/co4e/step_config_section.py`, `presentation/co4e/co4e_run_control_widget.py`, `ui/co4e_tab.py`, `ui/co4e_config_panel.py`, `tests/characterization/test_co4e_agent_panel.py`, `tests/characterization/test_co4e_run_manager_behavior.py`, `tests/characterization/test_co4e_skills_panel.py`, `tests/characterization/test_node_property_panel.py`, `tests/characterization/test_co4e_runs_page.py`, `tests/fakes/fake_co4e_workflow_service.py`, `tests/test_build_co4e_tab.py`, `tests/test_co4e_workflow_service.py`, `docs/architecture/co4e-split-map.md`, `docs/architecture/co4e-split-map.json`, `docs/architecture/co4e-split-map-node-property.md`, `docs/architecture/co4e-split-map-node-property.json`, `docs/architecture/co4e-split-map-run-control.md`, `docs/architecture/co4e-split-map-run-control.json`, `docs/architecture/co4e-refactor-run-report.md`, `docs/architecture/co4e-refactor-run-report-node-property.md`.

---

## 3. Kết quả cổng ranh giới

**ĐỎ (FAIL)** — theo kết quả Phase 5 đã chạy (`clean: false`). Chi tiết:

- **13 vi phạm FORBIDDEN**: đều là các đường dẫn thuộc quyền sở hữu N1 (node-property, run-control) hoặc file dùng chung cấm sửa cho mọi lane — ví dụ `ui/co4e_tab.py`, `ui/co4e_config_panel.py`, `presentation/co4e/node_property_panel.py`, `node_property_actions_mixin.py`, `step_config_section.py`, `docs/architecture/co4e-split-map-node-property.*`, `co4e-refactor-run-report-node-property.md`, `co4e-split-map.md/json`, `co4e-refactor-run-report.md`, `co4e-split-map-run-control.*`. **Không cái nào trong số này do lane canvas-widget đụng tới trong lượt làm việc này.**
- **14 vi phạm OUT-OF-WHITELIST**: `application/workflows/co4e_workflow_service.py`, `domain/workflows/run_record.py`, `presentation/co4e/agent_list_panel.py`, `presentation/co4e/canvas_geometry.py`, `presentation/co4e/co4e_tab.py`, `presentation/co4e/skills_list_panel.py`, `tests/characterization/test_co4e_agent_panel.py`, `tests/characterization/test_co4e_canvas_geometry.py`, `tests/characterization/test_co4e_run_manager_behavior.py`, `tests/characterization/test_co4e_skills_panel.py`, `tests/characterization/test_node_property_panel.py`, `tests/fakes/fake_co4e_workflow_service.py`, `tests/test_build_co4e_tab.py`, `tests/test_co4e_workflow_service.py`, và mới phát sinh `tests/characterization/test_co4e_runs_page.py`. **Cũng không phải sản phẩm của lane canvas-widget** — đây là artefact của các lane khác đang chạy song song, cùng nằm trong `git status` chung của repo vì cổng chặn quét trạng thái toàn repo chứ không tách theo phiên.

Đối chiếu với whitelist được cấp cho chính lane này (`tests/characterization/test_co4e_canvas_widget.py`, `presentation/co4e/co4e_canvas_widget.py`, `presentation/co4e/canvas_items.py`, `presentation/co4e/canvas_interaction_mixin.py`, `ui/co4e_canvas.py`, `docs/architecture/co4e-split-map-canvas-widget.md/json`): **không có mục nào trong 7 file này xuất hiện trong danh sách vi phạm** — cổng đỏ hoàn toàn do trạng thái git dùng chung của các lane khác chưa dọn/commit, không phải do vi phạm ranh giới của lane canvas-widget.

---

## 4. Kết quả bước soát output (Phase Review) — 2 lượt

**Không có phát hiện nào ở mức CHAN trong cả 2 lượt soát.** Cả hai đều verdict `DAT` (đạt), `repaired: false` (không cần sửa lại trong lúc soát).

### Lượt 1 — subject: `tests/characterization/test_co4e_canvas_widget.py` (verdict: DAT)
- Mức CHAN: không có.
- Mức SUA: không có.
- Mức GHI_NHAN (4):
  1. `test_relayout_on_empty_canvas_is_a_safe_noop` (dòng 723-724): assert dựa trên giá trị hardcode `True` ngay sau khi gọi `relayout()` — chỉ là phép thử "không ném exception", không khoá được giá trị/hành vi cụ thể nào của `relayout()` trên canvas rỗng. Không phải lỗi, nhưng không phải lưới an toàn thật cho trường hợp này.
  2. Comment tại `test_zoom_in_clamps_at_max_after_7_steps_from_1_0` (dòng 686-696) lệch một đơn vị so với tính toán độc lập (chạm 3.0 ở lần áp dụng thứ 8, không phải thứ 7 như comment nói) — nhưng giá trị assert (mảng 20 phần tử) vẫn đúng 100% với hành vi thật, chỉ comment giải thích bị lệch.
  3. `ui/co4e_canvas.py` có 2 "equivalent mutant" phát hiện qua mutation-test: xoá điều kiện `src != target_id` trong `_finish_connect` và xoá guard `if source == target: return` trong `_make_edge` đều không làm test đỏ, vì các điểm gọi `_make_edge` đã tự lọc `source != target` từ trước — hai lớp bảo vệ trùng nhau. Không phải lỗi hành vi hiện tại, nhưng là điểm cần lưu ý cho người tách sau: nếu một lớp bảo vệ mất đi trong tương lai mà không có lớp kia, quirk "tự nối vào mình" sẽ mất hiệu lực mà test này không bắt được tại đúng điểm đó.
  4. Ghi nhận về git status: 2 file `docs/architecture/co4e-split-map-run-control.md/json` xuất hiện thêm giữa lúc soát — xác nhận là sản phẩm của một agent khác chạy song song (cùng mtime), không phải do lượt soát này gây ra; `ui/co4e_canvas.py` không đổi trạng thái và pytest 43/43 vẫn xanh sau khi khôi phục mutation.

### Lượt 2 — subject: `presentation/co4e/co4e_canvas_widget.py` (verdict: DAT)
- Mức CHAN: không có.
- Mức SUA (1): `co4e_canvas_widget.py` dòng 75-89 (`Co4ECanvas.load`) — điểm chuyển từ domain (list Node/Edge) sang item hiển thị thiếu comment giải thích quirk "edge có source/target không nằm trong `self._nodes` bị âm thầm bỏ qua". Quirk có thật, kế thừa nguyên văn từ `ui/co4e_canvas.py` gốc (không phải lỗi mới do lần tách này gây ra — đã đối chứng bằng `git show HEAD`), nhưng theo yêu cầu B4 (bắt buộc có comment tại các điểm chuyển tầng DTO), cần bổ sung comment trong lượt sửa tiếp theo.
- Mức GHI_NHAN (4):
  1. Hai khối comment mâu thuẫn nhau trong `canvas_items.py` dòng 128-133 (`_NodeItem.paint`) về vị trí cổng (một khối nói "top-center/bottom-center", khối liền sau nói "left-center/right-center" — code thực tế vẽ left-center/right-center). Lỗi tồn tại sẵn trong bản gốc, được dời nguyên văn đúng kỷ luật B1 "không đổi", không phải lỗi mới. Cần dọn ở lượt sau.
  2. Docstring của 3 file (`co4e_canvas_widget.py`, `canvas_items.py`, `canvas_interaction_mixin.py`) dẫn số dòng cụ thể của `ui/co4e_canvas.py` (ví dụ "289-317", "701 dòng tổng") không khớp với `ui/co4e_canvas.py` tại git HEAD hiện tại (791 dòng, class `Co4ECanvas` bắt đầu ở dòng 379, không phải 289). Nội dung code đã được xác minh khớp 100% bằng AST diff độc lập — đây là vấn đề chất lượng tài liệu (số dòng tham chiếu một trạng thái trung gian chưa commit), không phải lỗi hành vi.
  3. Suite tổng đỏ 1 test (`test_no_ignored_source`) tại thời điểm soát, do file `tests/characterization/test_co4e_runs_page.py` (thuộc nhánh tách khác) chưa được `git add` — không liên quan 3 file thuộc phạm vi soát này, đã tự hết khi lane kia add file (khớp với mục 1 của báo cáo này).
  4. `docs/architecture/co4e-refactor-run-report-canvas-widget.md` chưa được tạo tại thời điểm soát — ghi nhận thiếu deliverable, không chặn. (Báo cáo này chính là file được yêu cầu tạo, viết trong lượt hiện tại.)

---

## 5. Việc để lại cho lần sau

- **`ui/co4e_canvas.py` vẫn còn chạy song song** với `presentation/co4e/co4e_canvas_widget.py` — hiện đóng vai trò shim/re-export để các chỗ import cũ (`from .co4e_canvas import Co4ECanvas, CO4E_MIME`) không vỡ. Cần dọn các nơi còn import theo đường cũ, chuyển sang import trực tiếp từ `presentation/co4e/co4e_canvas_widget.py`, rồi mới an toàn để rút gọn/xoá shim.
- **1 điểm SUA từ lượt soát 2 chưa được sửa**: bổ sung comment giải thích quirk bỏ-qua-edge-mồ-côi tại `presentation/co4e/co4e_canvas_widget.py` (hàm `load`, dòng 75-89) theo đúng yêu cầu B4.
- **2 GHI_NHAN không chặn nhưng nên dọn cùng đợt sau**: (a) comment mâu thuẫn vị trí cổng trong `canvas_items.py` dòng 128-133 (kế thừa từ bản gốc); (b) số dòng tham chiếu trong docstring của 3 file mới không khớp trạng thái HEAD hiện tại — cần cập nhật lại số dòng khi file được commit để người đọc sau đối chiếu lại được.
- `docs/architecture/co4e-split-map-canvas-widget.md/json` là input cho bước dọn shim `ui/co4e_canvas.py` ở lượt tiếp theo.
- Cổng ranh giới hiện đang đỏ do trạng thái git dùng chung của nhiều lane chưa commit/dọn — cần các lane liên quan (node-property, run-control, v.v.) tự commit hoặc dọn phần của mình để cổng có thể xanh trở lại cho toàn repo; lane canvas-widget không có vi phạm nào trong whitelist của chính nó (xem mục 3).

## 6. Cần báo người khác trong team

- Không có phát hiện mới nằm ngoài phạm vi lane này cần báo riêng (không có kiểu phát hiện như vụ `.gitignore` nuốt `infrastructure/secrets/` trước đây).
- Đáng lưu ý (không cần hành động thêm, chỉ để các lane khác biết): trong lúc đo baseline lần 1 của lượt này, `test_no_ignored_source` đỏ thoáng qua vì lane run-control (`tests/characterization/test_co4e_runs_page.py`, `presentation/co4e/co4e_run_control_widget.py`) chưa kịp `git add` hai file mới của họ. Tự hết ở lần đo thứ 2 sau khi họ add xong. Gợi ý: các lane nên `git add` sớm sau khi tạo file mới để tránh gate/test đỏ giả khi nhiều phiên Claude chạy song song trên cùng thư mục.
