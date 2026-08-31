# Báo cáo chạy — tách `StepConfigPanel` khỏi `ui/co4e_config_panel.py`

- **Ngày:** 2026-08-24
- **Người:** hiephv3@fpt.com
- **Nhánh:** gamma/refactor
- **Làn:** N3 — Co4E Studio, phạm vi `node_property_panel`

Ghi chú: repo này có nhiều phiên Claude chạy song song trên cùng một thư mục
làm việc. Báo cáo dưới đây chỉ trả lời 5 câu bắt buộc, không lan sang phần đã
viết ở các lượt trước (chi tiết cắt-dán từng dòng xem
`docs/architecture/co4e-split-map-node-property.md`/`.json`).

## 1. Số test thay đổi thế nào so với baseline

Lệnh đo (baseline Phase 0, chạy trước khi làn này bắt đầu):

```
.venv/Scripts/python.exe -m pytest tests -q --tb=no -rA --continue-on-collection-errors
279 passed, 1 skipped
```

Lệnh đo lại (chạy ngay bây giờ, sau khi làn này đã xong):

```
$ .venv/Scripts/python.exe -m pytest tests -q --tb=no -rA --continue-on-collection-errors
330 passed, 1 skipped in 10.15s
```

| | passed | failed | collection_errors | skipped |
|---|---|---|---|---|
| Trước (Phase 0) | 279 | 0 | 0 | 1 |
| Sau (bây giờ) | 330 | 0 | 0 | 1 |

- **Không có test fail nào**, mới hay cũ. `passed` sau ≥ passed trước
  (330 ≥ 279) → không hồi quy theo tiêu chí so lệch.
- Chênh lệch +51 **không** đến từ riêng làn này. Làn này chỉ thêm đúng 1 test
  mới (`tests/characterization/test_node_property_panel.py`). +50 còn lại đến
  từ các làn song song khác đã nhập vào cùng thư mục làm việc trong lúc làn
  này chạy (`test_co4e_agent_panel.py`, `test_co4e_canvas_geometry.py`,
  `test_co4e_canvas_widget.py`, `test_co4e_skills_panel.py`,
  `test_build_co4e_tab.py`, `test_co4e_workflow_service.py`, ...) — thấy rõ
  trong `git status --porcelain` ở câu 2, không phải việc của làn N3.
- **1 skip** là mốc cũ có từ trước, không phải do lượt này gây ra:
  `tests/characterization/test_co4e_run_manager_behavior.py:140` — tự skip
  vì `cowork_local.config` bị file test khác import với `HOME` thật trước nó
  trong cùng phiên pytest (giới hạn đã biết, ghi rõ trong docstring đầu file
  đó, không liên quan `StepConfigPanel`).
- Test flaky đã biết của repo
  (`tests/test_atomic_json.py::test_ghi_de_nhieu_lan_van_dung`, do
  `os.replace()` gặp khoá file tạm trên Windows) **không xuất hiện** trong
  lần chạy này — không có gì để báo thêm về nó.
- Chưa cần chạy lại lần hai để xác nhận vì không có test nào đỏ ở cả hai lần
  đo (Phase 0 và bây giờ) — không có ca nghi flaky cần phân xử.

## 2. File đã tạo, file đã sửa

`git status --porcelain` (nguyên văn, chạy ngay lúc viết báo cáo):

```
AM application/workflows/co4e_workflow_service.py
A  docs/architecture/co4e-refactor-run-report-node-property.md
A  docs/architecture/co4e-split-map-node-property.json
A  docs/architecture/co4e-split-map-node-property.md
A  domain/workflows/run_record.py
A  presentation/co4e/agent_list_panel.py
A  presentation/co4e/canvas_geometry.py
A  presentation/co4e/co4e_tab.py
A  presentation/co4e/node_property_actions_mixin.py
A  presentation/co4e/node_property_panel.py
A  presentation/co4e/skills_list_panel.py
A  presentation/co4e/step_config_section.py
A  tests/characterization/test_co4e_agent_panel.py
AM tests/characterization/test_co4e_canvas_geometry.py
A  tests/characterization/test_co4e_canvas_widget.py
AM tests/characterization/test_co4e_run_manager_behavior.py
AM tests/characterization/test_co4e_skills_panel.py
A  tests/characterization/test_node_property_panel.py
A  tests/fakes/fake_co4e_workflow_service.py
A  tests/test_build_co4e_tab.py
AM tests/test_co4e_workflow_service.py
 M ui/co4e_canvas.py
M  ui/co4e_config_panel.py
 M ui/co4e_tab.py
?? .codegraph/
?? cowork_local
?? docs/architecture/co4e-refactor-run-report.md
?? docs/architecture/co4e-split-map.json
?? docs/architecture/co4e-split-map.md
?? run_app.bat
?? stop_running.ps1
```

**Của đúng làn N3 (`node_property_panel`) — khớp danh sách đường dẫn được
cấp quyền:**

- Mới: `presentation/co4e/node_property_panel.py` (293 dòng),
  `presentation/co4e/node_property_actions_mixin.py` (202 dòng),
  `presentation/co4e/step_config_section.py` (134 dòng),
  `tests/characterization/test_node_property_panel.py`,
  `docs/architecture/co4e-split-map-node-property.md`,
  `docs/architecture/co4e-split-map-node-property.json`,
  `docs/architecture/co4e-refactor-run-report-node-property.md` (chính file
  này).
- Sửa: `ui/co4e_config_panel.py` (528 dòng → 14 dòng, chỉ còn re-export
  `StepConfigPanel`).
- Cả 3 file production mới đều ≤ 400 dòng (293/202/134).

**Không thuộc làn N3 — xuất hiện trong `git status` vì có phiên khác đang
chạy song song trên cùng thư mục, làn này không đụng tới:**
`application/workflows/co4e_workflow_service.py`,
`domain/workflows/run_record.py`, `presentation/co4e/agent_list_panel.py`,
`presentation/co4e/canvas_geometry.py`, `presentation/co4e/co4e_tab.py`,
`presentation/co4e/skills_list_panel.py`,
`tests/characterization/test_co4e_agent_panel.py`,
`tests/characterization/test_co4e_canvas_geometry.py`,
`tests/characterization/test_co4e_canvas_widget.py`,
`tests/characterization/test_co4e_run_manager_behavior.py`,
`tests/characterization/test_co4e_skills_panel.py`,
`tests/fakes/fake_co4e_workflow_service.py`, `tests/test_build_co4e_tab.py`,
`tests/test_co4e_workflow_service.py`, `ui/co4e_canvas.py`,
`ui/co4e_tab.py`, cùng các file untracked
`docs/architecture/co4e-split-map.md`/`.json`,
`docs/architecture/co4e-refactor-run-report.md`, `.codegraph/`,
`cowork_local`, `run_app.bat`, `stop_running.ps1`.

## 3. Cổng ranh giới: xanh hay đỏ

**Đỏ** (`clean: false`), nhưng **không phải vì làn N3 tự ý sửa các file cấm**
— tất cả vi phạm đều là file thuộc phạm vi làn khác (N1) hoặc làn song song
khác đang có mặt trong cùng thư mục làm việc tại thời điểm chạy cổng chặn:

- **FORBIDDEN** (đúng danh sách cấm tuyệt đối của N3, thuộc làn N1):
  `ui/co4e_tab.py` (M), `ui/co4e_canvas.py` (M),
  `docs/architecture/co4e-split-map.md` (mới), `docs/architecture/co4e-split-map.json` (mới),
  `docs/architecture/co4e-refactor-run-report.md` (mới).
- **OUTSIDE-WHITELIST** (không khớp `allowed_write_globs` của N3):
  `application/workflows/co4e_workflow_service.py`,
  `domain/workflows/run_record.py`,
  `presentation/co4e/agent_list_panel.py`,
  `presentation/co4e/canvas_geometry.py`, `presentation/co4e/co4e_tab.py`,
  `presentation/co4e/skills_list_panel.py`,
  `tests/characterization/test_co4e_agent_panel.py`,
  `tests/characterization/test_co4e_canvas_geometry.py`,
  `tests/characterization/test_co4e_canvas_widget.py`,
  `tests/characterization/test_co4e_run_manager_behavior.py`,
  `tests/characterization/test_co4e_skills_panel.py`,
  `tests/fakes/fake_co4e_workflow_service.py`, `tests/test_build_co4e_tab.py`,
  `tests/test_co4e_workflow_service.py`.
- `loc_over_cap`: rỗng — không file nào của làn N3 vượt 400 dòng.
- `pyside_leaks`: rỗng — không có import PySide6/PyQt trong
  `domain/`/`application/` (kiểm bằng AST parse, không phải grep).

Kết luận: 8 file đúng phạm vi được cấp cho làn N3 (danh sách 400-file ở đầu
prompt) đều nằm gọn trong whitelist, không file nào của làn N3 chạm vào danh
sách cấm. Cổng đỏ là do **trạng thái chung của working tree** (nhiều làn ghi
song song), không phải hồi quy do thay đổi của làn này gây ra. Người quyết
định commit cần biết: nếu commit y nguyên `git status` hiện tại, sẽ commit
luôn cả các thay đổi của những làn khác (N1 và các làn Co4E khác) — cần
tách bằng `git add` đúng danh sách 8 file của N3 trước khi commit, không
`git add -A`.

## 4. Bước soát output — 2 lượt, tách riêng theo mức `CHAN`

**Không lượt soát nào phát hiện mức `CHAN`.** (Mức `CHAN` = test không bắt
được lỗi, hoặc code bị viết lại thay vì dời — không có trường hợp nào như
vậy trong cả 2 lượt.)

- **Lượt 1 — chủ thể `tests/characterization/test_node_property_panel.py`,
  verdict: ĐẠT.**
  1 phát hiện mức **SUA** (không phải `CHAN`): file test mới chưa
  `git add`, nên khi chạy full suite làm đỏ
  `tests/test_no_ignored_source.py::test_khong_file_py_nao_bi_bo_quen_chua_theo_doi`.
  Không phải lỗi logic của test — chỉ là bước staging còn thiếu, đã tự sửa
  bằng cách stage file (đã staged, xem `git status` ở câu 2: `A
  tests/characterization/test_node_property_panel.py`).
  Xác nhận qua bite-test: phá 14/14 hành vi riêng của
  `ui/co4e_config_panel.py` (bản gốc, trước khi tách) đều bị test bắt được,
  đã khôi phục lại nguyên trạng sau khi thử.

- **Lượt 2 — chủ thể `presentation/co4e/node_property_panel.py`, verdict:
  ĐẠT.**
  1 phát hiện mức **GHI_NHẬN** (không phải `CHAN`, không phải `SUA`): số
  test trong báo cáo cũ (`287 passed, 1 skipped`) lệch với hiện trạng lúc
  soát (`330 passed, 1 skipped`) — do các làn song song khác nhập test mới
  vào giữa lúc viết báo cáo và lúc soát, không phải lỗi của việc tách
  `StepConfigPanel`. Báo cáo này (bản viết lại) đã cập nhật đúng số thật
  330/1 ở mục 1.
  Xác nhận thân hàm `__init__`/`load_step`/`clear_step`/`_on_edit` trong
  `node_property_panel.py` **giống byte-for-byte** (240/240 dòng) với bản
  gốc `ui/co4e_config_panel.py` tại HEAD; 8 method trong
  `node_property_actions_mixin.py` chỉ khác đúng độ sâu import
  (`..core` → `...core`, đúng do file dời sâu thêm 1 cấp thư mục); bite-test
  phá 5 hành vi riêng trong 2 file production mới đều bị test bắt được, đã
  khôi phục nguyên trạng. `tools/check_co4e.py` (cổng kiểm soát riêng): giữ
  nguyên `27/27` control cũ.

## 5. Việc để lại cho lần sau / cần báo người khác

**Để lại cho lần sau (thuộc phạm vi làn N3 hoặc làn kế tiếp có liên quan):**

1. `docs/architecture/co4e-split-map.md` (làn N1, không được sửa ở đây) vẫn
   liệt kê `node_property_panel.py` như một đích còn dở của việc tách
   `ui/co4e_tab.py`/`ui/co4e_canvas.py` qua Signal
   `node_selected`/`node_activated`. Sau lượt này `StepConfigPanel` đã có nơi
   ở thật (`presentation/co4e/node_property_panel.py`); làn phụ trách tách
   `ui/co4e_tab.py` có thể import thẳng từ đó thay vì qua
   `ui/co4e_config_panel.py`, nhưng đó là quyết định của làn N1, không tự
   đổi ở đây.
2. `_ai_draft`/`_load_models` trong `node_property_actions_mixin.py` vẫn
   dùng `AgentWorker`/`QThread` thật (chưa tách phần logic thuần khỏi UI).
   Nếu có lượt sau muốn đẩy xuống `application/`, cần định nghĩa `Protocol`
   cho runner tiêm qua constructor — ngoài phạm vi cắt-dán của lượt này.
3. `ui/co4e_config_panel.py` (14 dòng) vẫn còn sống song song làm lớp
   re-export — chưa xoá, vì `ui/co4e_tab.py` (thuộc N1) còn import từ đó.
   Xoá file này là quyết định của người sở hữu `ui/co4e_tab.py`.

**Cần báo người khác trong team:**

Không có phát hiện mới ngoài phạm vi làn này (không có kiểu phát hiện như
tiền lệ `.gitignore`/`secrets/` nêu trong hướng dẫn). Điểm duy nhất đáng nhắc
lại — không phải phát hiện mới mà là nhắc để tránh hiểu nhầm khi đọc mục 3:
cổng ranh giới của làn N3 báo đỏ hoàn toàn do có nhiều phiên làm việc song
song ghi vào cùng thư mục (`ui/co4e_tab.py`, `ui/co4e_canvas.py`,
`presentation/co4e/agent_list_panel.py`, v.v. — thuộc N1 và các làn Co4E
khác), không phải do thay đổi của làn N3. Ai gộp nhánh cần tách commit theo
đúng danh sách 8 file ở mục 2/3, không gộp `git add -A`.
