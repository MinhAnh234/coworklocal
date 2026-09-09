# quality_gate.md — Checklist kiểm soát chất lượng

> Trách nhiệm của file này: định nghĩa **checklist self-review** agent phải chạy ở Step 6
> của `process.md`, cách tính điểm và ngưỡng pass.
> Đây là file có ưu tiên cao nhất — không được đánh đổi vì lý do thời gian hay vì "sửa nhỏ".

## 1. Cách sử dụng

1. Chạy lần lượt 7 nhóm checklist dưới đây, đánh `Pass` / `Fail` cho từng mục.
2. Mục `Fail` → **sửa ngay**, không ghi "sẽ bổ sung sau".
3. Chạy lại checklist. Lặp tối đa **2 lần**.
4. Sau 2 lần vẫn `Fail` vì thiếu thông tin bên ngoài → chuyển thành Open Question (`OQ-xx`).
5. Tính điểm theo §3. Chưa đạt ngưỡng thì **không được trả kết quả**.

Nhóm áp dụng theo chế độ: **G5 chỉ áp dụng cho LAYOUT_FIX và MIXED**.
Với CODE_FIX thuần, bỏ G5 và chia lại điểm theo §3.

---

## 2. Checklist

### G1. Root cause — Sửa đúng nguyên nhân, không che triệu chứng

- [ ] Nguyên nhân gốc được nêu cụ thể tới `file:line`, không phải phỏng đoán ("có lẽ do...").
- [ ] Nguyên nhân gốc giải thích được **toàn bộ** triệu chứng đã quan sát, không sót phần nào.
- [ ] Không có `try/except` nuốt lỗi hay kiểm tra null được thêm vào chỉ để hết crash.
- [ ] Không sửa nhiều chỗ cùng lúc theo kiểu thử-xem-cái-nào-ăn.

### G2. Minimal & scoped diff — Diff nhỏ và đúng phạm vi

- [ ] Mỗi file trong diff đều có lý do rõ ràng trong section Changes.
- [ ] Không có drive-by cleanup: đổi tên biến, sắp xếp lại import, format lại file ngoài vùng sửa.
- [ ] Không có refactor kiến trúc kèm theo trong cùng lần fix.
- [ ] Không thêm dependency mới.
- [ ] Không đổi public API / signature mà nơi khác đang gọi (trừ khi yêu cầu nói rõ).
- [ ] Không xoá code chưa hiểu rõ mục đích.

### G3. Convention & consistency — Bám chuẩn codebase

- [ ] Style của đoạn sửa khớp với file xung quanh (đặt tên, type hint, comment, thứ tự import).
- [ ] Ngôn ngữ comment / docstring giữ đúng như file gốc.
- [ ] Không có mã màu rời rạc trong widget; màu đi qua `theme/palettes.py`.
- [ ] Không có `setStyleSheet` cục bộ chồng lên thứ `theme/qss.py` đã định nghĩa.
- [ ] Sửa đúng tầng theo bảng ở `process.md` Step 3.4 (layout code / qss / palette).
- [ ] Không còn code debug tạm: lệnh in tạm, log tạm, comment kiểu "sẽ sửa sau".

### G4. Correctness & regression — Đúng và không phá thứ khác

- [ ] Hành vi mong đợi đã được kiểm chứng thật, không phải suy đoán.
- [ ] Sửa logic → có test hồi quy **fail trước khi sửa** và **pass sau khi sửa**
      (hoặc nêu rõ vì sao không viết được test).
- [ ] Đã chạy test liên quan; kết quả được ghi **nguyên văn**, kể cả khi fail.
- [ ] Đã rà mọi nơi khác đang dùng thứ vừa sửa (hàm, widget, selector, token) và kết luận.
- [ ] Không có test nào bị nới lỏng assert để pass.
- [ ] Edge case liên quan đã được xét: giá trị rỗng, null, danh sách trống, dữ liệu rất dài.

### G5. Layout robustness — Chỉ áp dụng LAYOUT_FIX / MIXED

- [ ] Đã kiểm ở tối thiểu 2 kích thước cửa sổ, gồm cả kích thước nhỏ nhất còn dùng được.
- [ ] Đã kiểm cả theme **sáng** và **tối**.
- [ ] Đã kiểm với nội dung text dài bất thường: không tràn, không chồng, không cắt chữ.
- [ ] Đã kiểm trạng thái rỗng, nếu widget hiển thị danh sách.
- [ ] Không dùng kích thước cứng để ép cho vừa; nếu buộc phải dùng, đã nêu lý do.
- [ ] Widget vẫn co giãn đúng khi cửa sổ đổi kích thước (layout và size policy,
      không phải toạ độ tuyệt đối).
- [ ] Thay đổi trên selector dùng chung đã được kiểm ở các widget khác cùng dùng selector đó.

### G6. Safety — An toàn

- [ ] Không có credential, token, API key, connection string trong code, log, test hay report.
- [ ] Không có dữ liệu cá nhân thật trong test fixture hay ví dụ.
- [ ] Không thêm log ghi ra dữ liệu nhạy cảm.
- [ ] Vùng critical trong `SECURITY.md` không bị chạm; nếu buộc phải chạm,
      đã nêu rõ và xin xác nhận.
- [ ] Không tự `git commit`, `git push` hay tạo pull request khi người dùng chưa yêu cầu.

### G7. Reviewability — Sẵn sàng cho người khác review

- [ ] Fix Report đủ section theo `output_contract.md`, không section nào bị bỏ trắng.
- [ ] Reviewer không cần hỏi lại: nguyên nhân gốc là gì, sửa ở đâu, đã kiểm thế nào,
      có phá gì không.
- [ ] Mỗi thay đổi (`CH-xx`) nối được về nguyên nhân gốc hoặc về một `AS-xx`.
- [ ] Mọi Open Question đều cụ thể, có người cần trả lời và có `Blocking`.
- [ ] Mọi Assumption đều nêu tác động nếu giả định sai.
- [ ] Điểm không giải quyết được đã ghi thành Limitation (`LM-xx`) — không bị bỏ qua im lặng,
      không trình bày như đã trọn vẹn, và không có quyết định nghiệp vụ nào do agent tự chốt.
- [ ] Không còn placeholder kiểu `TBD`, `???`, `sẽ bổ sung sau`.
- [ ] Có đề xuất commit message theo Conventional Commit.

---

## 3. Scoring & Ngưỡng pass

| Nhóm | Tiêu chí | Điểm (LAYOUT_FIX / MIXED) | Điểm (CODE_FIX thuần) |
|---|---|---|---|
| G1 | Root cause | 25 | 30 |
| G2 | Minimal & scoped diff | 15 | 20 |
| G3 | Convention & consistency | 10 | 10 |
| G4 | Correctness & regression | 20 | 25 |
| G5 | Layout robustness | 15 | — |
| G6 | Safety | 10 | 10 |
| G7 | Reviewability | 5 | 5 |
| | **Tổng** | **100** | **100** |

Điểm mỗi nhóm = `(số mục Pass / tổng số mục) × điểm tối đa của nhóm`, làm tròn xuống.

| Tổng điểm | Kết luận | Hành động |
|---|---|---|
| ≥ 85 | Pass | Được trả kết quả |
| 70 - 84 | Conditional | Sửa các mục Fail rồi chạy lại checklist |
| < 70 | Fail | Quay lại `process.md` từ Step 2, làm lại phân tích |

## 4. Điều kiện chặn tuyệt đối

Bất kể tổng điểm bao nhiêu, **không được trả kết quả** nếu vi phạm bất kỳ điều nào sau:

1. **Chưa xác định được nguyên nhân gốc** mà vẫn sửa code.
2. **Nhóm G6 Safety có bất kỳ mục Fail.**
3. **Báo test pass mà không thực sự chạy test**, hoặc che kết quả fail.
4. **Nới lỏng assert của test** để test pass.
5. **Diff chạm file không giải thích được lý do.**
6. Còn credential hoặc dữ liệu cá nhân thật trong code, test hay report.
7. Đã tự commit / push / tạo pull request khi người dùng không yêu cầu.

Vi phạm điều 1 → dùng khối `Root Cause Not Confirmed` trong `output_contract.md` §6
thay vì trả bản sửa.
