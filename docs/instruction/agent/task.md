# task.md — Nhiệm vụ chính & Phạm vi xử lý

> Trách nhiệm của file này: định nghĩa **AI phải làm gì** và **phạm vi tới đâu**.
> Cách làm nằm ở `process.md`, hình thức kết quả nằm ở `output_contract.md`.

## 1. Nhiệm vụ chính (Mission)

Thực hiện **yêu cầu sửa code** và/hoặc **yêu cầu chỉnh layout / UI** trên codebase hiện có,
sao cho thay đổi **đúng nguyên nhân gốc**, **nhỏ nhất có thể**, **không gây hồi quy**,
và **review được** bởi người khác.

Kết quả cuối cùng gồm hai phần, không thiếu phần nào:

1. **Thay đổi trong code** (đã áp dụng vào file, không phải mô tả suông).
2. **Fix Report** theo `output_contract.md` — giải thích nguyên nhân gốc, thay đổi,
   và bằng chứng kiểm chứng.

## 2. Chế độ hoạt động

Agent nhận biết chế độ từ yêu cầu và xử lý khác nhau:

| Chế độ | Điều kiện nhận biết | Trọng tâm |
|---|---|---|
| **CODE_FIX** | Có lỗi sai hành vi, crash, sai dữ liệu, sai logic | Root cause → sửa logic → test hồi quy |
| **LAYOUT_FIX** | UI lệch, tràn, chồng chữ, sai khoảng cách, sai màu, không co giãn | Layout manager / size policy / theme token → kiểm ở nhiều kích thước và cả hai theme |
| **MIXED** | Yêu cầu chạm cả logic và hiển thị | Chạy đủ cả hai nhóm bước và cả hai nhóm quality gate |

Nếu không xác định được chế độ, chọn **CODE_FIX** và ghi rõ giả định đã chọn ở đầu Fix Report.

## 3. In scope

| # | Nội dung | Áp dụng cho |
|---|---|---|
| 1 | Tái hiện lỗi và khoanh vùng tới `file:line` | CODE_FIX, LAYOUT_FIX |
| 2 | Xác định và nêu rõ nguyên nhân gốc | CODE_FIX, LAYOUT_FIX |
| 3 | Sửa logic / xử lý dữ liệu / signal-slot | CODE_FIX |
| 4 | Sửa layout: container, stretch, size policy, margin, spacing, alignment | LAYOUT_FIX |
| 5 | Sửa hình dạng & khoảng cách qua `theme/qss.py`; sửa màu qua `theme/palettes.py` | LAYOUT_FIX |
| 6 | Thêm hoặc cập nhật test hồi quy | CODE_FIX (bắt buộc nếu sửa logic) |
| 7 | Chạy test liên quan và ghi lại kết quả thật | Cả hai |
| 8 | Nêu phạm vi ảnh hưởng và rủi ro hồi quy | Cả hai |
| 9 | Đề xuất commit message theo Conventional Commit | Cả hai |

## 4. Out of scope

- **Refactor kiến trúc** hoặc tách / gộp module khi yêu cầu chỉ là fix một lỗi.
- **Drive-by cleanup:** đổi tên biến, sắp xếp lại import, format lại file ngoài vùng đang sửa.
- **Thêm dependency** mới hoặc nâng version thư viện.
- **Thiết kế lại UI/UX**, đổi bố cục tổng thể, đổi bảng màu thương hiệu.
- **Đổi public API / signature** đang được nơi khác gọi (trừ khi yêu cầu nói rõ).
- **Tự commit / push / tạo pull request** khi người dùng chưa yêu cầu.
- **Sửa test cho pass** bằng cách nới lỏng assert thay vì sửa code (bị cấm tuyệt đối).
- Viết tài liệu thiết kế (BD/DD) hay sinh test case toàn diện — thuộc agent khác.

## 5. Definition of Done

Nhiệm vụ chỉ hoàn thành khi thỏa mãn **đồng thời**:

- [ ] Nguyên nhân gốc đã được nêu rõ, không phải phỏng đoán "có lẽ do...".
- [ ] Thay đổi đã được áp dụng thật vào file, không còn ở dạng đề xuất.
- [ ] Diff chỉ chạm những file thực sự cần; mỗi file bị chạm đều giải thích được lý do.
- [ ] Đã chạy test liên quan; kết quả (pass/fail) được ghi lại nguyên văn.
- [ ] Sửa logic → có test hồi quy fail trước khi sửa và pass sau khi sửa
      (hoặc nêu rõ vì sao không viết được test).
- [ ] LAYOUT_FIX → đã kiểm ở tối thiểu 2 kích thước cửa sổ và cả theme sáng lẫn tối.
- [ ] Đã chạy toàn bộ `quality_gate.md` và đạt ngưỡng pass.
- [ ] Fix Report đủ section theo `output_contract.md`.

## 6. Quy tắc ưu tiên khi xung đột

Khi hai chỉ dẫn xung đột nhau, thứ tự ưu tiên là:

1. `quality_gate.md` — an toàn và tính đúng đắn không được đánh đổi vì tốc độ.
2. `input_contract.md` — không bịa nguyên nhân, không sửa mò khi chưa đủ dữ kiện.
3. `output_contract.md` — báo cáo phải review được.
4. `process.md` — trình tự có thể linh hoạt nếu vẫn đạt exit criteria từng bước.
5. `examples.md` — chỉ là style tham khảo.

Ngoại lệ duy nhất vượt lên trên tất cả: **convention hiện có của file đang sửa**.
Nếu file đang sửa làm khác `examples.md`, bám theo file, và ghi một dòng trong Open Questions.
