# Guardrail — Luật bất biến cho mọi agent trong `agent/`

> **PRECEDENCE:** File này áp dụng cho **tất cả 6 role** trong `agent/`.
>
> Nếu role-specific instruction mâu thuẫn với bất kỳ quy tắc nào dưới đây, **Guardrail này thắng**.

---

## G1. Không tự bịa requirement

* Chỉ làm việc dựa trên:

  * bug report;
  * source code thực tế;
  * các tài liệu trong `knowledge/`;
  * governance và security policy liên quan.
* Nếu thiếu thông tin:

  * ghi vào `Assumption`; hoặc
  * ghi vào `Open Question`.
* **Không được tự suy diễn requirement rồi sửa theo suy diễn đó.**
* Không tự ý "tiện tay cải thiện UX", refactor hoặc đổi behavior ngoài phạm vi bug.
* Nếu phát hiện vấn đề khác:

  * ghi vào `Out of scope (đề xuất issue riêng)`;
  * không sửa trong cùng patch.

---

## G2. Không đoán vị trí code

* Không được kết luận về code khi chưa đọc code thực tế.
* Mọi khẳng định cụ thể về implementation phải kèm:

```text
path/file.py:line
```

Ví dụ:

```text
Root cause nằm tại presentation/shell/nav_rail.py:242
```

* Khi người dùng mô tả bằng tiếng Việt hoặc tiếng Nhật:

  1. tra `knowledge/screen_map.md`;
  2. tra `docs/screens/manifest.json`;
  3. tra `docs/screens/controls.json`;
  4. xác nhận `screen → view → widget → file → line`.
* **Không đoán file chỉ dựa vào tên widget hoặc tên màn hình.**
* Nếu chưa đủ bằng chứng để xác định vị trí:

  * `confidence: low`;
  * ghi rõ thông tin còn thiếu.

---

## G3. Sửa đúng tầng

Cowork Local sử dụng Clean Architecture 4 tầng:

```text
presentation/ → application/ → domain/ ← infrastructure/
```

### Quy tắc

* Bug UI/UX mặc định được xử lý tại:

  * `presentation/`
  * `ui/`
  * `theme/`
  * `i18n/`

* Nếu buộc phải sửa `application/` hoặc `domain/`:

  * phải giải thích trong `fix_plan.md` **tại sao không thể giải quyết ở tầng trên**;
  * phải đánh dấu đây là thay đổi cần reviewer chú ý.

### Pure Python boundary

`domain/` và `application/` phải là **100% Pure Python**.

**Tuyệt đối không thêm:**

```python
from PySide6 ...
from PyQt...
```

vào hai tầng này.

Gate C sẽ chặn vi phạm này.

### GUI boundary

Widget:

* chỉ gọi service/use case của `application/`;
* không query SQLite trực tiếp;
* không đọc/ghi JSON repository trực tiếp;
* không gọi LLM trực tiếp trong GUI thread.

---

## G4. Không đặt tên màu ngoài `theme/`

Ngoài `theme/`, tuyệt đối không định nghĩa màu trực tiếp.

### Không được dùng

```python
"#1f6fb2"
QColor("red")
setStyleSheet("color: blue")
```

Cũng không được tạo màu bằng:

* hex literal;
* color name;
* RGB/RGBA literal;
* stylesheet màu viết trực tiếp.

### Cách đúng

Màu phải đi qua theme system:

```text
Palette
  ↓
semantic token
  ↓
QSS template / current_palette()
  ↓
widget
```

Có hai cách hợp lệ:

1. Widget có `objectName` và được style trong `theme/qss.py`.
2. Custom painting dùng `current_palette()`.

Chi tiết xem:

```text
knowledge/theme_tokens.md
```

---

## G5. Không hardcode chuỗi hiển thị

Mọi text người dùng nhìn thấy phải đi qua:

```python
tr("key")
```

Chi tiết xem:

```text
knowledge/i18n_rules.md
```

Khi sửa hoặc thêm một label:

* phải cập nhật `en`;
* phải cập nhật `ja`;
* phải cập nhật `vi`.

**Không chỉ sửa tiếng Việt.**

Không hardcode trực tiếp các chuỗi UI trong widget nếu chuỗi đó cần được người dùng nhìn thấy.

---

## G6. Giữ Single Responsibility

Mọi production module phải:

```text
<= 400 LOC
```

Đây là giới hạn của Gate S.

### Nếu patch làm file vượt 400 dòng

Không được tiếp tục nhồi code vào file.

Phải:

1. xác định phần cần tách;
2. ghi kế hoạch tách trong `fix_plan.md`;
3. thực hiện việc tách như một phần rõ ràng của patch;
4. đảm bảo dependency direction không bị phá vỡ.

### Không được làm

Ví dụ file hiện có:

```text
380 LOC
```

Không được "sửa bug" bằng cách thêm:

```text
+150 LOC
```

chỉ để tránh tách module.

---

## G7. Không làm suy yếu kiểm thử

Tuyệt đối không:

* xoá test;
* disable test;
* dùng `@pytest.mark.skip` để né lỗi;
* nới lỏng assertion chỉ để pass;
* thay đổi test expectation mà không có lý do hợp lệ từ requirement.

Nếu test đang đỏ vì nguyên nhân khác:

* ghi nhận baseline;
* không sửa lén;
* báo rõ trong `fix_report.md`.

### UI bug

Mỗi UI bug được sửa nên có ít nhất một test tái hiện hoặc regression test phù hợp.

Test GUI phải có khả năng chạy headless khi phù hợp:

```bash
QT_QPA_PLATFORM=offscreen
```

Không được tạo test giả chỉ để đạt coverage.

---

## G8. Bản vá tối thiểu

Mục tiêu là:

> **Bản vá nhỏ nhất có thể sửa đúng nguyên nhân gốc.**

Không chỉ sửa triệu chứng.

### Không làm trong bug-fix PR

* refactor không liên quan;
* đổi architecture không cần thiết;
* format lại toàn file;
* đổi indent toàn file;
* rename hàng loạt;
* cleanup code ngoài phạm vi.

Một PR phải tuân theo:

```text
1 PR = 1 logical change
```

Diff phải:

* nhỏ;
* dễ đọc;
* dễ review;
* dễ rollback.

---

## G9. Không tự merge, không tự đóng issue

Agent chỉ:

* phân tích;
* đề xuất;
* tạo `fix_plan`;
* implement khi đúng role;
* kiểm chứng;
* tạo report;
* handoff.

Agent **không tự quyết định merge**.

Quyết định merge thuộc:

```text
Cowork Team
```

Theo:

```text
docs/governance/ownership.md
```

### Security review bắt buộc

Nếu thay đổi chạm tới bất kỳ nội dung nào sau đây:

* permission;
* credential;
* secret;
* MCP write/exec;
* sandbox;
* network;
* TLS;
* isolation;
* model routing;
* data deletion;
* security boundary;

thì output **bắt buộc phải có**:

```yaml
security_review: required
```

Điều này áp dụng **ngay cả khi thay đổi bắt đầu từ UI**.

`security_review: required` có nghĩa là thay đổi phải được đưa qua security review theo routing policy.

Không được tự kết luận:

> "Chỉ sửa UI nên không cần security review."

---

## G10. Trung thực về kết quả

Agent phải báo cáo đúng những gì thực sự đã làm.

### Chưa chạy test

Không được viết:

```text
Tests passed
```

Phải viết:

```text
Tests: not run
```

hoặc:

```text
Chưa chạy test do <lý do>.
```

### Chỉ sửa được một phần

Ví dụ:

```text
2/3 vấn đề đã được xử lý.
Vấn đề còn lại: ...
Lý do chưa xử lý: ...
```

Không được báo cáo như thể toàn bộ bug đã được giải quyết.

### Không chắc root cause

Phải ghi:

```yaml
confidence: low
```

hoặc:

```yaml
confidence: medium
```

hoặc:

```yaml
confidence: high
```

và nếu có:

```text
Alternative hypotheses:
- ...
- ...
```

### Nguyên tắc

> **Evidence trước, kết luận sau.**

Không được biến:

```text
chưa kiểm chứng
```

thành:

```text
đã xác nhận
```

---

# Bất biến tổng hợp

Mọi agent trong `agent/` phải tuân thủ chuỗi nguyên tắc sau:

```text
BUG REPORT
    ↓
EVIDENCE
    ↓
CORRECT FILE / LINE
    ↓
ROOT CAUSE
    ↓
MINIMAL FIX
    ↓
TEST
    ↓
QUALITY GATE
    ↓
REPORT
    ↓
HUMAN / COWORK TEAM REVIEW
```

Không được bỏ qua bước chỉ để hoàn thành nhanh hơn.

---

# Priority khi có xung đột

Khi các instruction mâu thuẫn, ưu tiên theo thứ tự:

```text
1. Guardrail G1–G10
2. Security policy / governance
3. knowledge/
4. Role-specific instruction
5. Bug report / task-specific detail
6. Agent assumption
```

Nếu có xung đột mà agent không thể tự giải quyết:

```text
Open Question
```

và handoff về reviewer/Cowork Team thay vì tự chọn một phương án.
