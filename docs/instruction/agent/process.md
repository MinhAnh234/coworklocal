# process.md — Quy trình xử lý

> Trách nhiệm của file này: định nghĩa **các bước AI phải thực hiện**, theo thứ tự,
> mỗi bước có điều kiện hoàn thành riêng. Không nhảy bước, không gộp bước.

## Tổng quan

```
Step 1        Step 2        Step 3        Step 4        Step 5        Step 6
Tái hiện &  → Nguyên nhân → Phương án  → Thực hiện  → Kiểm chứng → Self-review
khoanh vùng   gốc            sửa           sửa          & hồi quy     & báo cáo
```

**Cấm nhảy từ Step 1 sang Step 4.** Không có Step 2 thì mọi thứ sau đó chỉ là sửa mò.

---

## Step 1 — Tái hiện & khoanh vùng

**Việc phải làm**

1. Đọc input theo `input_contract.md`, xác định chế độ CODE_FIX / LAYOUT_FIX / MIXED.
2. Phát biểu lại vấn đề thành hai câu: **hiện tại đang sai thế nào** và **mong đợi là gì**.
3. Khoanh vùng file:
   - Có stack trace (I-03) → đi thẳng tới `file:line` trong trace, đọc cả frame gọi phía trên.
   - Không có trace → lần từ điểm vào UI (`ui/<màn hình>.py`) theo signal-slot xuống lớp xử lý.
   - LAYOUT_FIX → tìm nơi tạo layout của widget đó, **và** kiểm tra `theme/qss.py`
     xem selector nào đang áp lên nó.
4. Đọc **toàn bộ** hàm/lớp liên quan trước khi kết luận, không chỉ dòng bị nghi.

**Exit criteria:** nêu được danh sách `file:line` nghi vấn kèm lý do; phát biểu được
repro cụ thể (hoặc ghi rõ chưa tái hiện được và còn thiếu gì).

---

## Step 2 — Xác định nguyên nhân gốc

**Việc phải làm**

1. Trả lời được: **dòng nào**, và **vì sao** dòng đó gây ra triệu chứng đã quan sát.
2. Phân biệt rõ triệu chứng với nguyên nhân. Hai ví dụ điển hình:
   - Triệu chứng: crash vì giá trị null. Nguyên nhân gốc: nơi khởi tạo trả về null khi config
     chưa nạp — **không phải** chỗ crash.
   - Triệu chứng: chữ bị cắt. Nguyên nhân gốc: chiều cao bị đặt cứng nên widget không co giãn —
     **không phải** cỡ font.
3. Nếu có từ 2 nguyên nhân khả dĩ trở lên, nêu cách phân biệt (đọc thêm code, thêm log tạm,
   chạy một test nhỏ) rồi phân biệt thật. Không sửa cả hai cho chắc.
4. Kiểm tra xem lỗi có phải do thay đổi gần đây — dùng `git log` / `git blame` cho vùng đó.
   Nếu đúng, nêu commit liên quan.

**Exit criteria:** một phát biểu nguyên nhân gốc **duy nhất**, cụ thể tới `file:line`,
giải thích được **toàn bộ** triệu chứng đã quan sát — không còn phần nào "chưa rõ vì sao".

Nếu không đạt exit criteria này: **dừng, không sang Step 3.** Báo cáo theo
`output_contract.md` §6 (Không xác định được nguyên nhân gốc).

---

## Step 3 — Lập phương án sửa

**Việc phải làm**

1. Đề ra phương án sửa **tối thiểu**, đánh trực tiếp vào nguyên nhân gốc.
2. Xét ít nhất một phương án thay thế, nêu lý do chọn / không chọn (một câu mỗi phương án).
3. Xác định trước danh sách file sẽ chạm và **lý do từng file**. File nào không giải thích được
   thì loại ra khỏi phạm vi.
4. Với LAYOUT_FIX, chọn đúng tầng để sửa — đây là quyết định quan trọng nhất của bước này:

   | Loại vấn đề | Sửa ở |
   |---|---|
   | Sai thứ tự / tỉ lệ / khả năng co giãn của widget | Code layout trong `ui/` hoặc `presentation/`: layout manager, stretch, size policy |
   | Sai khoảng cách, bán kính góc, padding, đường viền | `theme/qss.py` (hình dạng và khoảng cách) |
   | Sai màu | `theme/palettes.py` (**chỉ** nơi này) |
   | Chỉ lệch ở một widget duy nhất | Selector riêng theo `objectName`, **không** đổi selector dùng chung |

5. Nếu sửa logic → xác định trước sẽ viết hoặc cập nhật test nào.

**Exit criteria:** có phương án cụ thể, có danh sách file kèm lý do, và
(với sửa logic) có tên test sẽ dùng làm bằng chứng.

---

## Step 4 — Thực hiện sửa

**Việc phải làm**

1. Sửa **đúng phạm vi đã chốt ở Step 3**. Phát sinh ngoài dự kiến thì quay lại Step 3,
   không âm thầm mở rộng.
2. Bám convention của file đang sửa: cách đặt tên, kiểu comment, type hint, thứ tự import.
   Ngôn ngữ comment và docstring theo đúng file đó, không đổi sang ngôn ngữ khác.
3. Những điều **không được làm** khi sửa:
   - Bọc khối lệnh trong một `try/except` nuốt lỗi để hết crash.
   - Thêm kiểm tra null chỉ để tránh lỗi, khi chưa hiểu vì sao giá trị bị null.
   - Đặt kích thước cứng (fixed size / fixed height / fixed width) để "ép cho vừa" —
     chỉ dùng khi kích thước thật sự là hằng số thiết kế, và phải nêu lý do.
   - Viết mã màu rời rạc trực tiếp trong widget.
   - Gọi `setStyleSheet` cục bộ để chồng lên thứ `theme/qss.py` đã định nghĩa.
   - Nới lỏng assert của test để test pass.
   - Format lại cả file hay sắp xếp lại toàn bộ import khi chỉ sửa vài dòng.
4. Nếu sửa logic → viết hoặc cập nhật test hồi quy **trước** khi coi bước này là xong.

**Exit criteria:** thay đổi đã áp dụng thật vào file; diff chỉ gồm những dòng cần thiết;
không còn code debug tạm (lệnh in tạm, log tạm, comment kiểu "sẽ sửa sau").

---

## Step 5 — Kiểm chứng & rà hồi quy

**Việc phải làm**

1. **Chạy test liên quan** và ghi lại output thật:

   ```bash
   python -m pytest tests -q
   ```

   Khi vùng sửa đã rõ, chạy hẹp trước cho nhanh (ví dụ `python -m pytest tests/test_<vùng>.py -q`),
   rồi mới chạy rộng.
2. **Sửa logic:** xác nhận test hồi quy **fail trước khi sửa** và **pass sau khi sửa**.
   Không xác nhận được điều này thì test đó không phải bằng chứng.
3. **LAYOUT_FIX:** kiểm tối thiểu
   - 2 kích thước cửa sổ (nhỏ nhất còn dùng được, và phóng to);
   - cả theme **sáng** và **tối**;
   - nội dung text dài bất thường, để kiểm tràn và cắt chữ;
   - trạng thái rỗng (không có dữ liệu), nếu widget hiển thị danh sách.
4. **Rà hồi quy:** tìm mọi nơi khác đang dùng thứ vừa sửa
   (hàm, widget, selector QSS, token theme) và đánh giá tác động.
5. Ghi lại **nguyên văn** kết quả: pass là pass, fail là fail kèm output.
   Không chạy được thì nói rõ chưa chạy và vì sao —
   **không suy đoán rồi ghi là đã pass**.

**Exit criteria:** có bằng chứng thật cho cả hành vi mong đợi và cho việc không phá thứ khác;
mọi nơi dùng chung đã được rà và kết luận.

---

## Step 6 — Self-review & báo cáo

**Việc phải làm**

1. Đọc lại diff của mình như một reviewer xa lạ: từng dòng thay đổi có giải thích được không?
2. Chạy toàn bộ checklist `quality_gate.md`, đánh Pass / Fail từng mục.
3. Mục Fail → **sửa ngay**, không ghi "sẽ bổ sung sau". Chạy lại checklist. Lặp tối đa **2 lần**.
4. Sau 2 lần vẫn Fail vì thiếu thông tin bên ngoài → chuyển thành `OQ-xx`.
5. Viết Fix Report theo `output_contract.md`, kèm khối Self-review Result.

**Exit criteria:** đạt ngưỡng pass của `quality_gate.md`, hoặc mọi mục Fail còn lại
đã được chuyển thành Open Question có `Blocking` rõ ràng.

---

## Nguyên tắc chung khi chạy process

- **Không trả kết quả giữa chừng.** Chỉ báo cáo sau khi hoàn thành Step 6.
- **Phát hiện sai ở bước trước thì quay lại bước đó,** không vá tiếp ở bước sau.
- **Không bỏ Step 5** vì lý do "sửa nhỏ, chắc chắn đúng". Sửa nhỏ vẫn phá được hồi quy.
- **Không commit, push hay tạo pull request** ở bất kỳ bước nào nếu người dùng chưa yêu cầu.
