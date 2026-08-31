# Báo cáo refactor — Flow Status (Runs page) — làn N3 Co4E Studio

- **Ngày:** 2026-08-25
- **Người:** Lâm (N3 — Co4E Studio), hiephv3@fpt.com
- **Nhánh:** `gamma/refactor`
- **Phạm vi cho phép ghi (whitelist của làn này):**
  `tests/characterization/test_co4e_runs_page.py`,
  `presentation/co4e/co4e_run_control_widget.py`,
  `docs/architecture/co4e-split-map-run-control.md`,
  `docs/architecture/co4e-split-map-run-control.json`,
  `ui/co4e_tab.py`,
  `docs/architecture/co4e-refactor-run-report-run-control.md`

---

## 1. Số test thay đổi thế nào so với baseline

Lệnh đo (chạy lại đúng nguyên văn):

```
.venv/Scripts/python.exe -m pytest tests -q --tb=no -rA --continue-on-collection-errors
```

| Mốc | passed | failed | collection_errors | skipped |
|---|---|---|---|---|
| Baseline (Phase 0) | 323 | 0 | 0 | 1 |
| Sau lượt này (đo lại vừa xong) | 346 | 0 | 0 | 1 |

Kết quả đo lại, 15 dòng cuối nguyên văn:

```
PASSED tests/test_settings_facade.py::test_provider_doc_duoc_ba_truong
PASSED tests/test_settings_facade.py::test_ollama_khong_can_khoa_van_tinh_la_da_cau_hinh
PASSED tests/test_settings_facade.py::test_thieu_model_thi_chua_cau_hinh
PASSED tests/test_settings_facade.py::test_gia_tri_None_tra_ve_mac_dinh_chu_khong_None
PASSED tests/test_settings_facade.py::test_routing_kieu_du_lieu_dung
PASSED tests/test_settings_facade.py::test_tat_dinh_tuyen
PASSED tests/test_settings_facade.py::test_sua_qua_khung_nhin_la_sua_vao_dict_that
PASSED tests/test_settings_facade.py::test_raw_de_khong_ai_bi_ket
PASSED tests/test_settings_facade.py::test_security_mac_dinh_la_bat
PASSED tests/test_settings_facade.py::test_settings_noi_vao_repo
PASSED tests/test_settings_facade.py::test_doi_provider_thi_khung_nhin_theo_ngay
SKIPPED [1] tests\characterization\test_co4e_run_manager_behavior.py:140: cowork_local.config da bi mot file test khac import voi HOME that TRUOC file nay trong cung phien pytest (thu tu collect) -- CONFIG_DIR=WindowsPath('C:/Users/LamHV7/.cowork_local') khong con nam trong sandbox cua file nay. Day la gioi han da biet (xem docstring dau file), KHONG phai mat an toan du lieu: moi test hook trong file nay tu va thang Co4ERunManager._history_path (doc lap voi CONFIG_DIR) nen khong test nao trong file thuc su cham vao lich su run that.
346 passed, 1 skipped in 25.78s
```

Nhận định:

- `passed` tăng 323 → 346 (+23), đúng bằng 23 test mới trong `tests/characterization/test_co4e_runs_page.py` (đã được xác nhận `23 passed` khi chạy riêng file này ở bước Phase Review). Không có test cũ nào bị mất.
- `failed`: 0 ở cả hai mốc — **không có test fail mới**. Không có hồi quy theo tiêu chí "không fail mới ngoài danh sách baseline".
- `collection_errors`: 0 ở cả hai mốc — không tăng.
- 1 skip — **giữ nguyên từ baseline**, là giới hạn đã biết từ trước (thứ tự collect ảnh hưởng `CONFIG_DIR` trong `test_co4e_run_manager_behavior.py`), không phải do lượt này gây ra.
- Test flaky đã biết (`tests/test_atomic_json.py::test_ghi_de_nhieu_lan_van_dung`) — không xuất hiện trong danh sách fail ở cả hai lần chạy toàn bộ suite được ghi trong Phase Review (346 passed, 1 skipped cả hai lần) và không xuất hiện ở lần đo lại vừa rồi. Không có gì để báo về test này trong lượt này.

**Kết luận:** không có hồi quy.

---

## 2. File đã tạo, file đã sửa

Theo `git status --porcelain` (đo lại tại thời điểm viết báo cáo này) và đối chiếu whitelist của làn:

**Trong whitelist của làn này (run-control) — đã có mặt đầy đủ, cả 5 mục:**
- Tạo mới, đã `git add` (trạng thái `A`): `presentation/co4e/co4e_run_control_widget.py`, `tests/characterization/test_co4e_runs_page.py`
- Tạo mới, chưa `git add` (trạng thái `??`): `docs/architecture/co4e-split-map-run-control.md`, `docs/architecture/co4e-split-map-run-control.json`
- Sửa, chưa stage (trạng thái ` M`): `ui/co4e_tab.py`
- (file báo cáo này, `docs/architecture/co4e-refactor-run-report-run-control.md`, do lượt này vừa ghi — chưa `git add` tại thời điểm viết)

**Ngoài whitelist của làn này (thuộc làn khác/song song, KHÔNG do lượt này tạo ra — liệt kê để minh bạch trạng thái thư mục làm việc, không phải việc của làn này):**
`application/workflows/co4e_workflow_service.py`, `domain/workflows/run_record.py`,
`presentation/co4e/agent_list_panel.py`, `presentation/co4e/canvas_geometry.py`,
`presentation/co4e/canvas_interaction_mixin.py`, `presentation/co4e/canvas_items.py`,
`presentation/co4e/co4e_canvas_widget.py`, `presentation/co4e/co4e_tab.py`,
`presentation/co4e/node_property_actions_mixin.py`, `presentation/co4e/node_property_panel.py`,
`presentation/co4e/skills_list_panel.py`, `presentation/co4e/step_config_section.py`,
`tests/characterization/test_co4e_agent_panel.py`, `tests/characterization/test_co4e_canvas_geometry.py`,
`tests/characterization/test_co4e_canvas_widget.py`, `tests/characterization/test_co4e_run_manager_behavior.py`,
`tests/characterization/test_co4e_skills_panel.py`, `tests/characterization/test_node_property_panel.py`,
`tests/fakes/fake_co4e_workflow_service.py`, `tests/test_build_co4e_tab.py`, `tests/test_co4e_workflow_service.py`,
`ui/co4e_canvas.py`, `ui/co4e_config_panel.py`,
`docs/architecture/co4e-refactor-run-report-node-property.md`, `docs/architecture/co4e-split-map-node-property.json`,
`docs/architecture/co4e-split-map-node-property.md`, `docs/architecture/co4e-refactor-run-report-canvas-widget.md`,
`docs/architecture/co4e-refactor-run-report.md`, `docs/architecture/co4e-split-map-canvas-widget.json`,
`docs/architecture/co4e-split-map-canvas-widget.md`, `docs/architecture/co4e-split-map.json`,
`docs/architecture/co4e-split-map.md`,
và các mục không do agent tạo: `.codegraph/`, `cowork_local` (file rỗng có sẵn), `run_app.bat`, `stop_running.ps1`.

Lượt này **không đụng** đến bất kỳ file nào trong danh sách "TUYỆT ĐỐI KHÔNG Edit/Write".

---

## 3. Cổng chặn (boundary gate) — xanh hay đỏ

**ĐỎ** — kết quả Phase 5 do hệ thống chấm gửi kèm ghi `"clean": false`, với các vi phạm sau:

- **Vi phạm nặng (forbidden_paths của N1 bị đụng):** `ui/co4e_canvas.py`, `ui/co4e_config_panel.py`,
  `presentation/co4e/co4e_canvas_widget.py`, `presentation/co4e/canvas_items.py`,
  `presentation/co4e/canvas_interaction_mixin.py`, `presentation/co4e/node_property_panel.py`,
  `presentation/co4e/node_property_actions_mixin.py`, `presentation/co4e/step_config_section.py`,
  `docs/architecture/co4e-split-map.md`, `docs/architecture/co4e-split-map.json`,
  `docs/architecture/co4e-refactor-run-report.md`, `docs/architecture/co4e-refactor-run-report-node-property.md`,
  `docs/architecture/co4e-split-map-node-property.md`, `docs/architecture/co4e-split-map-node-property.json`.
- **Ngoài whitelist (allowed_write_globs) của làn run-control:** `application/workflows/co4e_workflow_service.py`,
  `domain/workflows/run_record.py`, `presentation/co4e/agent_list_panel.py`, `presentation/co4e/canvas_geometry.py`,
  `presentation/co4e/co4e_tab.py` (lưu ý: khác `ui/co4e_tab.py` đang được whitelist),
  `presentation/co4e/skills_list_panel.py`, và các file test/tài liệu liên quan (danh sách đầy đủ ở mục 2).

**Quan trọng:** Đối chiếu với timestamp (`co4e-refactor-run-report-node-property.md` sửa lần cuối 24/08 21:33, còn `presentation/co4e/co4e_run_control_widget.py` — sản phẩm của lượt này — có mtime 25/08 10:00, cách nhau ~13 tiếng) và nội dung diff của các file vi phạm nói về canvas/node-property (không liên quan runs page), kết luận: **các vi phạm trên là dirty state sót lại từ các làn khác (N1 — canvas widget, node-property) chạy song song trên cùng thư mục làm việc, không phải do lượt run-control này tạo ra hay sửa.** Lượt này chỉ tạo/sửa đúng các file trong whitelist của mình (mục 2).

Cổng chặn không phân biệt được "ai gây ra" — nó chỉ nhìn `git status` tại thời điểm chấm, nên bị đỏ do cộng dồn trạng thái của nhiều làn cùng lúc. Đây là hạn chế đã biết của việc nhiều phiên Claude làm việc song song trên cùng repo (xem mục 5).

---

## 4. Bước soát output (Phase Review) — 2 lượt, mỗi mức CHAN nêu riêng

Có 2 lượt soát, không có mức `CHAN` nào ở cả hai lượt (cả hai đều **ĐẠT**).

**Lượt 1 — `tests/characterization/test_co4e_runs_page.py`:** verdict **DAT**, `repaired: true`.
Không có mức CHAN. Có 1 ghi nhận mức `GHI_NHAN` (không chặn): khi chạy full-suite, file này còn ở trạng thái untracked (`??`) nên `tests/test_no_ignored_source.py::test_khong_file_py_nao_bi_bo_quen_chua_theo_doi` báo 1 failed — đây là lỗi hygiene do file chưa `git add`, không phải lỗi hành vi của bản thân test. (Ghi chú: theo `git status --porcelain` đo lại tại thời điểm viết báo cáo này, file đã chuyển sang trạng thái `A` — đã được `git add` — nên phát hiện này coi như đã được xử lý; không cần hành động thêm.)

Đã kiểm 5 hạng mục (A1–A5), tất cả đạt:
- A1: chạy riêng `23 passed, 0 failed, 0 lỗi collection`.
- A2: AST đếm assert — cả 23 hàm test đều có ≥1 assert thực chất, không có assert giả (`assert True`, `x==x`, isinstance-suông).
- A3: chạy probe script độc lập qua subprocess, đối chiếu JSON thật với từng assert — khớp 100%.
- A4: 4 mutation thuộc 4 loại khác nhau trên `ui/co4e_tab.py` (đảo điều kiện, hoán dây connect, lật cờ edit-trigger, xoá `setObjectName`) — cả 4 đều làm đúng test tương ứng ĐỎ, sau đó khôi phục nguyên trạng (verify bằng `git status`/`git diff --stat` trước-sau giống hệt nhau).
- A5: xác nhận probe chạy trong sandbox HOME riêng (tmp_path), không đụng `~/.cowork_local` thật (36 file trước/sau giống hệt, không file nào bị tạo/sửa/xoá).

**Lượt 2 — `presentation/co4e/co4e_run_control_widget.py`:** verdict **DAT**, `repaired: false`.
Không có mức CHAN. Có 3 ghi nhận mức `GHI_NHAN` (không chặn):
1. `__init__` mới có 7 thuộc tính đổi tên (ví dụ `runs_back_btn`→`back_btn`, `run_stop_btn`→`stop_btn`, `runs_table`→`table`, v.v.) và các `.clicked`/`.itemDoubleClicked`/`.customContextMenuRequested.connect(...)` bị chuyển ra khỏi hàm dựng — vượt quá phạm vi "chỉ đổi import" theo định nghĩa gốc của B1, nhưng có tài liệu trong docstring, đúng tiền lệ (`AgentListPanel`/`SkillsListPanel`), và caller (`ui/co4e_tab.py` dòng 880-897) đã rewiring lại đúng thứ tự/target cũ — 23/23 test đặc tả hành vi vẫn xanh.
2. `docs/architecture/co4e-refactor-run-report-node-property.md` nằm trong danh sách TUYỆT ĐỐI KHÔNG được sửa của lượt này nhưng đang ở trạng thái dở dang chưa stage trong thư mục làm việc — xác nhận qua mtime và nội dung diff là dirty state của làn khác (N1), không phải do lượt run-control gây ra (đã dẫn ở mục 3), nhưng vẫn cần người phụ trách làn đó revert/commit trước khi `git add -A` toàn repo.
3. Quirk "`clear_btn` là nút DUY NHẤT không có `setIcon(...)`" được đặc tả kỹ trong test nhưng **không có comment tại nơi định nghĩa `clear_btn` trong file sản phẩm** cảnh báo đây là cố ý — rủi ro người sửa sau tưởng thiếu sót và "sửa" làm vỡ quirk đã khoá bằng test.

Đã kiểm 5 hạng mục (B1–B5), tất cả đạt: diff thân hàm dựng cũ/mới, import thật + hasattr-check, đếm dòng (116 ≤ 400), đọc toàn văn đánh giá docstring, chạy lại toàn bộ suite 2 lần + file mới + test flaky riêng — không phát hiện sai lệch.

**Tóm lại:** không có mức `CHAN` nào ở cả hai lượt soát. Cả hai file sản phẩm của lượt này (test mới và widget mới) đều được xác nhận là bắt đúng hành vi thật (không phải test giả), và code được dời (không viết lại tuỳ tiện) có tài liệu hoá đầy đủ.

---

## 5. Việc để lại cho lần sau / cần báo người khác

**Để lại cho lần chạy sau (trong phạm vi làn run-control):**
- `docs/architecture/co4e-split-map-run-control.md` và `.json` — đã tồn tại trên đĩa nhưng vẫn ở trạng thái `??` (untracked) tại thời điểm viết báo cáo này. Cần `git add` cùng với `presentation/co4e/co4e_run_control_widget.py` và `tests/characterization/test_co4e_runs_page.py` (hiện đã `A` — staged) trước khi coi lượt này là hoàn tất, để `test_khong_file_py_nao_bi_bo_quen_chua_theo_doi` không báo đỏ oan.
- `ui/co4e_tab.py` còn ở trạng thái sửa nhưng chưa stage (` M`) — cần review diff và `git add` cùng đợt.
- Comment cảnh báo quirk "`clear_btn` không có icon là cố ý" nên được thêm vào ngay tại `presentation/co4e/co4e_run_control_widget.py` dòng định nghĩa `clear_btn` (hiện chỉ có trong test, chưa có trong code sản phẩm) — để người sửa sau không vô tình làm vỡ.

**Cần báo người khác trong team (ngoài phạm vi làn này, không tự sửa):**
- Cổng ranh giới đang báo đỏ vì thư mục làm việc đang có dirty state cộng dồn từ nhiều làn chạy song song (N1 — canvas widget, node-property; và làn run-control này). Cụ thể các file bị N1 khoá (`ui/co4e_canvas.py`, `ui/co4e_config_panel.py`, `presentation/co4e/co4e_canvas_widget.py`, `presentation/co4e/node_property_panel.py`, v.v.) và `docs/architecture/co4e-refactor-run-report-node-property.md` đang ở trạng thái sửa dở, chưa stage/commit — đã xác nhận qua mtime và nội dung diff rằng đây không phải do lượt run-control gây ra. Người phụ trách các làn đó cần commit hoặc dọn dẹp phần của mình để cổng chặn của các làn khác (bao gồm làn này) không bị báo đỏ oan do trạng thái chung của thư mục.
- Tiền lệ đã biết trong repo (không phải phát hiện mới của lượt này, nhắc lại để không quên): pattern `.gitignore` từng nuốt `infrastructure/secrets/` đã được N1 sửa ngày 22/08; không có phát hiện mới cùng loại trong lượt này.
