# output_contract.md — Hợp đồng đầu ra

> Trách nhiệm của file này: định nghĩa **format, thứ tự section và tiêu chuẩn trình bày**
> của **Fix Report**. Đây là hợp đồng — không được thêm, bớt hay đổi thứ tự section.

## 1. Quy định chung

| Hạng mục | Quy định |
|---|---|
| Sản phẩm giao | **Hai phần:** (1) thay đổi đã áp dụng vào code, (2) Fix Report dưới đây |
| Định dạng report | Markdown thuần |
| Ngôn ngữ | Tiếng Việt cho phần diễn giải; giữ nguyên tiếng Anh cho tên file, hàm, class, widget, token |
| Trích dẫn vị trí code | Luôn viết dạng `path/to/file.py:123` để click được |
| Heading | `#` cho tiêu đề report, `##` cho section, `###` cho sub-section |
| Code block | Có tag ngôn ngữ (```python, ```bash, ```diff) |
| Section trống | **Cấm.** Không áp dụng thì ghi `N/A - <lý do>` |
| Độ dài | Ngắn gọn, ưu tiên bảng. Không dán lại nguyên file khi chỉ sửa vài dòng |

## 2. Quy ước ID

| Tiền tố | Dùng cho | Ví dụ |
|---|---|---|
| `CH-xx` | Một thay đổi (change) trong code | `CH-01` |
| `EV-xx` | Một bằng chứng kiểm chứng (evidence) | `EV-01` |
| `RG-xx` | Một điểm rủi ro hồi quy (regression) | `RG-01` |
| `AS-xx` | Assumption | `AS-01` |
| `OQ-xx` | Open Question | `OQ-01` |
| `LM-xx` | Limitation — giới hạn đã biết, không giải quyết được trong lần sửa này | `LM-01` |

## 3. Cấu trúc Fix Report (bắt buộc, đúng thứ tự)

```
# Fix Report - <mô tả ngắn vấn đề>

## 0. Summary
## 1. Root Cause
## 2. Changes
## 3. Diff
## 4. Verification
## 5. Regression & Impact
## 6. Assumptions, Open Questions & Limitations
```

### 0. Summary

Bảng gồm: `Mode` (CODE_FIX / LAYOUT_FIX / MIXED), `Triệu chứng`, `Hành vi mong đợi`,
`Số file đã sửa`, `Trạng thái test` (Pass / Fail / Chưa chạy + lý do).

Tiếp theo là **2-3 câu** mô tả: đã sửa gì, ở đâu, vì sao.
Người đọc chỉ đọc mục 0 phải hiểu được toàn cảnh.

### 1. Root Cause

- **Nguyên nhân gốc:** một phát biểu duy nhất, chỉ rõ `file.py:line`.
- **Cơ chế gây lỗi:** giải thích chuỗi nhân quả từ nguyên nhân tới triệu chứng.
- **Vì sao code cũ như vậy:** nếu tra được qua `git blame` / comment, nêu ra —
  giúp tránh sửa hỏng chủ ý ban đầu.
- **Phương án đã xét và loại:** bảng `Phương án | Lý do không chọn` (tối thiểu 1 dòng).

Cấm dùng cách diễn đạt phỏng đoán ở section này: "có lẽ do", "có thể vì", "chắc là".
Chưa chắc thì không được sửa — xem `process.md` Step 2.

### 2. Changes

Bảng `CH-ID | File:line | Loại (Logic/Layout/Theme/Test) | Thay đổi | Lý do`.

- Mỗi file bị chạm phải có ít nhất một dòng.
- Cột **Lý do** phải nối được về nguyên nhân gốc ở section 1, hoặc về một `AS-xx`.
- File bị chạm mà không giải thích được lý do → phải loại khỏi diff,
  không phải viết lý do cho nó.

### 3. Diff

- Diff thật của thay đổi, dạng ```diff hoặc trích đoạn before/after.
- **Chỉ đoạn liên quan** kèm vài dòng ngữ cảnh. Không dán cả file.
- Với LAYOUT_FIX chạm `theme/`: nêu rõ đã sửa `theme/qss.py` (hình dạng, khoảng cách)
  hay `theme/palettes.py` (màu), và selector nào bị ảnh hưởng.

### 4. Verification

Bảng `EV-ID | Cách kiểm | Kết quả`.

Yêu cầu bắt buộc theo chế độ:

| Chế độ | Bằng chứng tối thiểu |
|---|---|
| CODE_FIX | Lệnh test đã chạy + output nguyên văn; với sửa logic: test hồi quy **fail trước / pass sau** |
| LAYOUT_FIX | Đã kiểm ở 2 kích thước cửa sổ, cả theme sáng và tối, và với text dài |
| MIXED | Đủ cả hai nhóm trên |

Ghi lại **nguyên văn** kết quả. Quy tắc tuyệt đối:

- Test fail → ghi `Fail` kèm output, **không** che đi.
- Chưa chạy được → ghi `Chưa chạy - <lý do>`, **không** ghi là pass.
- Không suy đoán kết quả kiểm chứng chưa từng thực hiện.

### 5. Regression & Impact

Bảng `RG-ID | Nơi bị ảnh hưởng | Loại (Hàm/Widget/QSS selector/Theme token/Test) | Mức rủi ro | Đã kiểm chưa`.

- Phải nêu **mọi nơi khác** đang dùng thứ vừa sửa (kết quả rà ở `process.md` Step 5.4).
- Không có nơi nào khác dùng → ghi rõ `Không có nơi nào khác sử dụng` kèm cách đã rà
  (ví dụ: đã grep tên hàm / tên selector trên toàn repo).

### 6. Assumptions, Open Questions & Limitations

- Bảng Assumption: `AS-ID | Nội dung giả định | Căn cứ | Tác động nếu giả định sai`.
- Bảng Open Question: `OQ-ID | Câu hỏi | Người cần trả lời | Phương án đề xuất | Blocking (Yes/No)`.
- Bảng Limitation: `LM-ID | Giới hạn | Nguyên nhân | Ảnh hưởng tới kết quả | Cần gì để vượt qua`.
- Nơi ghi các việc **cố ý không làm**: code xấu phát hiện dọc đường, refactor nên làm sau,
  test còn thiếu. Ghi ở đây thay vì tự ý sửa trong cùng lần fix.

**Phân biệt ba loại** — dùng sai loại thì reviewer không biết phải làm gì với nó:

| Loại | Khi nào dùng | Ai xử lý tiếp |
|---|---|---|
| `AS-xx` Assumption | Bạn **đã chọn** một cách hiểu hợp lý và đã sửa theo cách đó | Reviewer xác nhận hoặc bác bỏ giả định |
| `OQ-xx` Open Question | Bạn **không được phép chọn** — cần người khác quyết định (nhất là quyết định nghiệp vụ) | Người được nêu trong cột owner trả lời |
| `LM-xx` Limitation | Không ai cần quyết định gì, nhưng **có giới hạn khách quan** khiến kết quả chưa trọn vẹn: không tái hiện được trên môi trường hiện có, không viết được test vì thiếu fixture, chỉ sửa được một phần vì phần còn lại thuộc module bị khoá | Chấp nhận, hoặc mở task riêng |

Quy tắc: giới hạn không giải quyết được thì **phải ghi thành `LM-xx`**, không được im lặng bỏ qua
và không được trình bày kết quả như đã trọn vẹn.

## 4. Đề xuất commit (không tự chạy)

Cuối report, đề xuất commit message theo convention của repo — Conventional Commit,
scope là optional:

```
fix(<scope>): <mô tả ngắn ở thể mệnh lệnh>
```

Prefix cho phép: `feat:` `fix:` `test:` `docs:` `refactor:` `perf:` `chore:`.

**Chỉ đề xuất.** Không tự `git add`, `git commit`, `git push` hay tạo pull request
khi người dùng chưa yêu cầu. Nếu đang ở nhánh mặc định (`main`), nêu rõ rằng
cần tạo nhánh riêng trước khi commit.

## 5. Khối Self-review Result

Đặt **sau** Fix Report, không lẫn vào trong:

```
### Self-review Result
| Nhóm | Pass/Tổng | Điểm |
|---|---|---|
| G1 Root cause | 4/4 | 25 |
| ... | ... | ... |
| **Tổng** | | **xx/100** |

Số vòng sửa: <n>
Mục đã chuyển thành Open Question: OQ-xx
```

## 6. Định dạng khi không thể tiến hành

Ba trường hợp không xuất Fix Report (xem `input_contract.md` §3 và `process.md` Step 2).
Dùng đúng khối tương ứng, ngắn gọn, không kèm code sửa:

**Thiếu input bắt buộc**

```
## Missing Required Input
| # | Thông tin cần cung cấp | Vì sao cần |
|---|---|---|
| 1 | ... | ... |
```

**Không tái hiện được lỗi**

```
## Cannot Reproduce
- Repro đã thử: ...
- Kết quả quan sát: ...
- Cần thêm: ...
```

**Không xác định được nguyên nhân gốc**

```
## Root Cause Not Confirmed
| # | Nguyên nhân khả dĩ | Bằng chứng ủng hộ | Cách kiểm chứng đề xuất |
|---|---|---|---|
| 1 | ... | ... | ... |

Lý do chưa sửa: chưa phân biệt được các khả năng trên, sửa lúc này sẽ là sửa mò.
```
