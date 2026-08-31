# Báo cáo chạy — Co4E Studio (N3)

- **Ngày:** 2026-08-24
- **Người:** Lâm (N3 — Co4E Studio), hiephv3@fpt.com
- **Nhánh:** gamma/refactor

## 1. Số test thay đổi thế nào so với baseline?

Lệnh đo (đúng lệnh được giao), chạy **2 lần liên tiếp** cho báo cáo này:

```
.venv/Scripts/python.exe -m pytest tests -q --tb=no -rA --continue-on-collection-errors
```

Lần 1: `277 passed in 4.96s`
Lần 2: `277 passed in 22.35s`

| | Phase 0 (baseline, đề bài đưa vào) | Đo lại hôm nay (2 lần) |
|---|---|---|
| passed | 228 | 277 |
| failed | 0 | 0 |
| collection_errors | 0 | 0 |

- **Tăng đúng 49 passed** (`228 → 277`), khớp với các file test mới của đợt
  tách này: `tests/characterization/test_co4e_canvas_geometry.py` (42),
  `tests/characterization/test_co4e_run_manager_behavior.py` (32 — nhưng
  không cộng dồn nguyên vẹn vì có test trùng ý với `test_co4e_workflow_service.py`),
  `tests/characterization/test_co4e_skills_panel.py` (1), `tests/test_build_co4e_tab.py`
  (1), `tests/test_co4e_workflow_service.py` (nhiều test mới cho
  `Co4EWorkflowService`/`RunRecord`). Không có test nào khác đổi trạng thái so
  với baseline.
- **Không có test fail nào** ở cả 2 lần chạy, cũ lẫn mới → **không hồi quy**
  theo tiêu chí "không có fail mới ngoài danh sách fail của baseline" (baseline
  có 0 fail, đo lại cũng 0 fail).
- **`collection_errors` = 0 ở cả hai mốc**, không tăng. Món nợ cũ (4 module
  chết vì `.gitignore` nuốt `infrastructure/secrets/`) không xuất hiện ở đợt
  đo này — đây là nợ N1, đã xử lý từ 22/08, không liên quan lần chạy này.
- Test flaky đã biết trên Windows,
  `tests/test_atomic_json.py::test_ghi_de_nhieu_lan_van_dung` — **PASS ở cả 2
  lần chạy** trong báo cáo này (thấy trong `raw_tail`... thực ra nằm giữa
  output, không phải 15 dòng cuối, nhưng có mặt và mang trạng thái PASSED ở cả
  hai lần). Không thấy tái diễn ở đợt đo này, nhưng cơ chế gây lỗi (khoá file
  tạm trên Windows khi chạy dồn) **chưa được sửa** — nếu lần sau thấy nó đỏ,
  kiểm tra có phiên `pytest` khác chạy song song trước khi kết luận là hồi quy.

Raw tail (15 dòng cuối, nguyên văn, lần đo thứ hai — `277 passed in 22.35s`):

```
PASSED tests/test_schema_migration.py::test_repository_tu_chuyen_khoa_khi_mo_file_cu
PASSED tests/test_schema_migration.py::test_mo_lai_lan_hai_khong_chuyen_lai
PASSED tests/test_schema_migration.py::test_save_luon_ghi_so_phien_ban
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
277 passed in 22.35s
```

## 2. File nào đã tạo, file nào đã sửa

Theo `git status --porcelain` (đo ngay trước khi viết báo cáo này):

```
AM application/workflows/co4e_workflow_service.py
A  domain/workflows/run_record.py
A  presentation/co4e/canvas_geometry.py
A  presentation/co4e/co4e_tab.py
A  presentation/co4e/skills_list_panel.py
A  tests/characterization/test_co4e_canvas_geometry.py
A  tests/characterization/test_co4e_run_manager_behavior.py
A  tests/characterization/test_co4e_skills_panel.py
A  tests/fakes/fake_co4e_workflow_service.py
A  tests/test_build_co4e_tab.py
AM tests/test_co4e_workflow_service.py
 M ui/co4e_canvas.py
 M ui/co4e_tab.py
?? .codegraph/
?? cowork_local
?? docs/architecture/co4e-refactor-run-report.md
?? docs/architecture/co4e-split-map.json
?? docs/architecture/co4e-split-map.md
?? run_app.bat
?? stop_running.ps1
```

**Tạo mới (`A`), thuộc phạm vi làn N3, trong whitelist:**

- `domain/workflows/run_record.py` — `RunRecord`.
- `presentation/co4e/canvas_geometry.py` — 8 hàm hình học thuần, dời nguyên
  văn từ `ui/co4e_canvas.py`.
- `presentation/co4e/co4e_tab.py` — factory `build_co4e_tab(ctx, workflow_service)`.
- `presentation/co4e/skills_list_panel.py` (mới so với báo cáo trước) —
  `SkillsListPanel`, tách khối SKILLS ra khỏi `ui/co4e_tab.py`.
- `tests/characterization/test_co4e_canvas_geometry.py` — 42 test.
- `tests/characterization/test_co4e_run_manager_behavior.py` — 32 test.
- `tests/characterization/test_co4e_skills_panel.py` (mới) — 1 test.
- `tests/fakes/fake_co4e_workflow_service.py`.
- `tests/test_build_co4e_tab.py`.

**Tạo mới nhưng đã sửa tiếp trong cùng đợt (`AM`):**

- `application/workflows/co4e_workflow_service.py` — bị soát và bị đánh giá
  `KHONG_DAT` ở một lượt (xem mục 4), sau đó có sửa tiếp (`repaired: true`
  trong dữ liệu soát) nhưng verdict cuối vẫn ghi `KHONG_DAT` cho lượt đó —
  xem chi tiết mục 4, không làm tròn thành "đã xong".
- `tests/test_co4e_workflow_service.py`.

**Đã sửa (`M`):**

- `ui/co4e_canvas.py` — trong whitelist (`ui/co4e_canvas.py` được liệt kê rõ),
  OK. 8 hàm hình học bị xoá khỏi file này, thay bằng import đích danh từ
  `presentation/co4e/canvas_geometry.py`.
- `ui/co4e_tab.py` — **KHÔNG nằm trong whitelist** của làn này (chỉ
  `ui/co4e_canvas.py` được phép). Diff thêm
  `from ..presentation.co4e.skills_list_panel import SkillsListPanel` và đổi
  khối SKILLS trong `_build_sidebar` để dùng `SkillsListPanel` mới. Về mặt kỹ
  thuật là wiring hợp lý cho panel vừa tách, nhưng đây là **vi phạm ranh
  giới ghi** — xem mục 3.

**Untracked, khớp `docs/architecture/**`, trong whitelist:**

- `docs/architecture/co4e-refactor-run-report.md` (báo cáo này)
- `docs/architecture/co4e-split-map.json`, `docs/architecture/co4e-split-map.md`

**Untracked, ngoài whitelist, cần chú ý:**

- `.codegraph/` — gồm `.codegraph/.gitignore` (được coi là bỏ qua) và
  `.codegraph/codegraph.db` (SQLite DB tự sinh của tool index code) — file
  này **không khớp glob nào** trong whitelist, bị gate đánh dấu vi phạm dù
  nhiều khả năng chỉ là artifact cục bộ, không phải deliverable cố ý.
- `cowork_local` (file rỗng ở gốc repo), `run_app.bat`, `stop_running.ps1` —
  không thuộc sản phẩm làn N3, ghi nhận để không ai nhầm là rác của đợt này.

**Chưa đụng** file nào trong danh sách cấm (`app.py`, `theme.py`, `i18n.py`,
`config.py`, `bootstrap.py`, `.gitignore`, `.gitea/workflows/ci.yaml`).

## 3. Cổng chặn: xanh hay đỏ

**ĐỎ (FAIL).** `clean: false`. 2 vi phạm được gate ghi nhận:

1. **`ui/co4e_tab.py` bị sửa (M) nhưng ngoài whitelist** — chỉ
   `ui/co4e_canvas.py` được cấp quyền ghi trong `ui/`, `ui/co4e_tab.py` thì
   không. Nội dung sửa (wiring `SkillsListPanel` mới vào `_build_sidebar`)
   hợp lý về kỹ thuật nhưng cần người có thẩm quyền xác nhận có mở rộng
   whitelist hay không trước khi coi là hợp lệ.
2. **`.codegraph/codegraph.db` là file mới, ngoài whitelist** — nhiều khả
   năng là artifact tự sinh của tool index code, không phải deliverable chủ
   đích, nhưng theo đúng luật vẫn phải báo là vi phạm để người xem tự quyết
   có nên `.gitignore` nó hay không.

Không vi phạm (đã kiểm, không tính là FAIL):

- `forbidden_paths` (`app.py`, `theme.py`, `i18n.py`, `config.py`,
  `bootstrap.py`, `.gitignore`, `.gitea/workflows/ci.yaml`) — không file nào
  bị đụng.
- `scripts/`, `requirements*.txt`, `tools/check_*.py` — không bị đụng.
- Không file production mới nào vượt ngưỡng 400 dòng (`loc_over_cap: []`).
- Không có PySide6 rò vào `domain/`/`application/` (`pyside_leaks: []`).

## 4. Bước soát output (Phase Review)

**7 lượt soát, mỗi lượt một file/chủ đề.** 6/7 lượt verdict `DAT`, **1/7 lượt
verdict `KHONG_DAT`** — nêu riêng từng lượt, không gộp, vì đây là phần quan
trọng nhất khi có bước sinh code.

- **Lượt 1 — `tests/characterization/test_co4e_canvas_geometry.py` — `DAT`,
  0 `CHAN`.** 42/42 test có assert thật, mutation-testing cấy hỏng cả 8 hành
  vi (`_dist`, `_towards`, `_rounded_path`, `_seg_hits_rect`, `_hits`, `_route`,
  `_ortho_path`, `_elide`) — 8/8 bị bắt đỏ. Không có finding nào.

- **Lượt 2 — `tests/characterization/test_co4e_run_manager_behavior.py` —
  `DAT`, 0 `CHAN`.** 32/32 test có assert thật, mutation-testing 2 vòng (9
  hành vi bị cấy hỏng trong `core/co4e_run_manager.py`) — 9/9 bị bắt đỏ. 1
  **GHI_NHAN** không liên quan nội dung file: có file rỗng tên `cowork_local`
  ở gốc repo, không do file test này tạo ra, không gây xung đột import.

- **Lượt 3 — `tests/characterization/test_co4e_skills_panel.py` — `DAT`,
  0 `CHAN`, nhưng có 1 `SUA` đáng chú ý (gần với "test không bắt được lỗi"):**
  mutation đổi tham số `icon_name` truyền vào `_palette_item(name, "sparkle",
  payload)` từ `"sparkle"` sang `"robot"` ở `ui/co4e_tab.py:723` — **test vẫn
  XANH**, vì không có assert nào đọc `item.icon()`. Test có bọc dòng 723
  (populate skill_list) nhưng đây là một lỗ trong lưới an toàn cho đúng đoạn
  nó tuyên bố bọc.

- **Lượt 4 — `presentation/co4e/co4e_tab.py` — `DAT`, 0 `CHAN`.** Thân hàm
  `build_co4e_tab` chỉ 1 import + 1 `return Co4ETab(ctx)`. Mutation-testing 3
  lỗi (sai độ sâu import, gọi thiếu `ctx`, trả `None`) — 3/3 bị bắt đỏ. Không
  có finding.

- **Lượt 5 — `application/workflows/co4e_workflow_service.py` —
  `KHONG_DAT` (`repaired: true`).** **Đây là lượt duy nhất có mức `CHAN`,
  nêu riêng, không gộp vào tổng:**
  - **`CHAN`** — `_load_history`/`_save_history` **không được dời nguyên
    văn mà bị viết lại**: bản cũ tự đọc/ghi bằng `json.loads`/`tmp.replace()`
    trong `try/except`; bản mới thay bằng `AtomicJsonFile.read()`/`write()`.
    Hành vi khác nhau **thật** khi file `run_history.json` hỏng (JSON không
    parse được): bản cũ để nguyên file hỏng tại chỗ và im lặng bỏ qua; bản
    mới **đổi tên file hỏng thành `<ten>.bad-<timestamp>`** (quarantine)
    trước khi trả về mặc định. Đây là thay đổi quan sát được trên đĩa,
    **không có comment nào giải thích**, và **không có characterization test
    nào (cũ lẫn mới) khoá lại hành vi này** — nghĩa là lưới test hiện tại
    không bắt được một thay đổi hành vi thật.
  - `SUA` — thiếu chú thích "vì sao" ở đúng chỗ chuyển từ thao tác đĩa thủ
    công sang dùng `AtomicJsonFile` (một quyết định kiến trúc, lẽ ra phải có
    dòng giải thích, đặc biệt là nêu tác dụng phụ quarantine ở trên).
  - `GHI_NHAN` — `remove()`/`clear_finished()` thêm dòng
    `self._worker_handles.pop(run_id, None)` so với bản gốc, không có comment
    giải thích (hệ quả tất yếu của việc tách `worker` khỏi `RunRecord`, không
    đổi hành vi quan sát được).
  - `GHI_NHAN` — cơ chế ghi (`_save_history`) đổi từ tmp cố định
    (`path.with_suffix('.json.tmp')`) sang `AtomicJsonFile.write()`
    (`tempfile.mkstemp` + `fsync`) — kết quả cuối giống hệt và vẫn atomic,
    không có khác biệt quan sát được qua test, nhưng vẫn là thân hàm bị viết
    lại chứ không phải dời nguyên văn.
  - Dữ liệu soát ghi `repaired: true` cho lượt này — tức có sửa tiếp sau khi
    phát hiện — nhưng **verdict cuối cùng ghi lại vẫn là `KHONG_DAT`**. Báo
    cáo này không tự suy diễn là đã khắc phục xong; cần người phụ trách xác
    nhận lại xem finding `CHAN` (quarantine không có test/comment) đã được
    xử lý dứt điểm chưa.

- **Lượt 6 — `presentation/co4e/canvas_geometry.py` — `DAT`, 0 `CHAN`.**
  AST diff xác nhận 8 hàm **identical tuyệt đối** với bản gốc (dời nguyên
  văn). Mutation-testing 8/8 bị bắt đỏ. 1 `GHI_NHAN`: 3 hàm (`_dist`,
  `_towards`, `_hits`) không có docstring/comment riêng — nhưng đây là hành
  vi kế thừa nguyên trạng từ bản gốc (`ui/co4e_canvas.py` cũng không có),
  không phải lỗi của người tách.

- **Lượt 7 — `presentation/co4e/skills_list_panel.py` — `DAT`, 0 `CHAN`.**
  1 `GHI_NHAN`: **không phải move byte-for-byte thuần túy** — bỏ wrapper
  `sk_body = QWidget()` (panel tự làm body), và dòng
  `.clicked.connect(self._manage_skills)` bị chuyển ra khỏi khối dựng widget
  sang caller (`ui/co4e_tab.py`). Đã xác minh cả hai không đổi hành vi bằng
  test thật (`test_co4e_skills_panel.py` + `test_build_co4e_tab.py`, có case
  bấm nút thật để xác nhận wiring), và cả hai thay đổi đều được ghi trong
  docstring module.

## 5. Việc để lại / cần báo người khác

**Để lại cho lần chạy sau (trong phạm vi làn N3):**

1. **Xử lý finding `CHAN` ở `application/workflows/co4e_workflow_service.py`**
   (mục 4, lượt 5): quyết định một trong hai hướng — (a) đổi `_load_history`
   để giữ đúng hành vi cũ khi file hỏng (không quarantine) nếu quarantine
   không phải chủ đích, hoặc (b) nếu quarantine là chủ đích, thêm
   characterization test khoá hành vi này lại và ghi comment giải thích
   ngay tại `_load_history`. Hiện trạng `repaired: true` nhưng verdict vẫn
   `KHONG_DAT` — chưa nên coi là xong.
2. **Đóng lỗ hổng test ở `test_co4e_skills_panel.py`** (mục 4, lượt 3): thêm
   assert đọc `item.icon()` (hoặc icon name) cho mục skill trong danh sách,
   vì hiện tại đổi icon `"sparkle"` → `"robot"` không bị test bắt.
3. **Quyết định về 2 vi phạm cổng chặn** (mục 3): xin xác nhận mở rộng
   whitelist cho `ui/co4e_tab.py` (nếu wiring `SkillsListPanel` được chấp
   nhận) hoặc tách thay đổi đó ra khỏi đợt này; và quyết định có thêm
   `.codegraph/` vào `.gitignore` hay không (không tự sửa `.gitignore` vì
   nằm trong danh sách cấm của làn này).
4. **Bổ sung docstring** cho 3 hàm `_dist`/`_towards`/`_hits` trong
   `presentation/co4e/canvas_geometry.py` (GHI_NHAN lượt 6) — cơ hội cải
   thiện, không bắt buộc, kế thừa từ bản gốc.
5. **`docs/architecture/co4e-split-map.md`/`.json`** vẫn là input cho các
   bước tách kế tiếp của `ui/co4e_tab.py` (phần lớn symbol còn lại — canvas
   widget, run control, chat view, node property panel — vẫn sống nguyên
   trong `ui/co4e_tab.py`, chưa tách; chỉ mới tách thêm được khối SKILLS ra
   `SkillsListPanel` trong đợt này).
6. `core/co4e_run_manager.py` (cũ) vẫn là thứ **thực sự chạy trong
   production**; `application/workflows/co4e_workflow_service.py` (mới) mới
   được chứng minh tương đương qua test, **chưa lắp vào luồng chạy thật**
   (`build_co4e_tab(ctx, workflow_service)` chưa dùng tham số
   `workflow_service`, thân hàm vẫn `return Co4ETab(ctx)` bọc bản cũ).

**Cần báo người khác trong team:**

Đã xử lý xong cả hai việc từng phải nhắn Nam (N1). Nêu lại chỉ để xác nhận
đóng, **không phiên nào cần nêu lại nữa**:

1. `.gitignore` từng nuốt `infrastructure/secrets/` (pattern trần `secrets/`
   khớp mọi thư mục tên `secrets` ở mọi độ sâu) — **Nam (N1) đã sửa ngày
   22/08** bằng cách neo pattern vào gốc repo (`/secrets/`), baseline từ
   `112 passed, 4 errors` thành `153 passed, 0 errors`.
2. `.gitignore` cũng nuốt `.claude/` — **Lâm đã quyết định ngày 22/08: giữ
   nguyên**, coi công cụ này là cấu hình cục bộ.

**Việc mới cần báo (phát hiện ở đợt đo này, ngoài hai việc đã đóng ở trên):**

3. `ui/co4e_tab.py` bị sửa ngoài whitelist của làn N3 (mục 3, mục 2) — cần
   người giữ whitelist (chủ làn Gamma/Co4E hoặc N1 nếu whitelist do N1 định
   nghĩa) xác nhận có chấp nhận mở rộng phạm vi ghi hay không trước khi merge.
4. `.codegraph/codegraph.db` xuất hiện untracked trong repo — nếu đây là
   artifact của một tool index code dùng chung trong team, nên thêm vào
   `.gitignore` (qua người có quyền sửa `.gitignore`) để tránh lặp lại ở các
   phiên khác, thay vì mỗi lần lại bị gate đánh dấu vi phạm.
