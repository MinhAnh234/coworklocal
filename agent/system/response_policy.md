# Response Policy — Cách agent trả lời

> **SCOPE:** Áp dụng cho tất cả agent trong `agent/`.
>
> Response Policy quy định **cách agent giao tiếp và trình bày output**. Nếu mâu thuẫn với `Guardrail G1–G10`, **Guardrail thắng**.

---

## R1. Ngôn ngữ

### Trả lời người dùng nội bộ

* Sử dụng **tiếng Việt**.
* Giữ nguyên các thuật ngữ kỹ thuật bằng tiếng Anh, ví dụ:

  * widget
  * layout
  * stylesheet
  * signal
  * guardrail
  * root cause
  * regression
  * quality gate
  * handoff

Không dịch các thuật ngữ kỹ thuật nếu việc dịch làm mất ý nghĩa hoặc không phù hợp với codebase.

### Code

Docstring và comment trong code phải viết bằng **English**, phù hợp với convention hiện tại của codebase.

Ví dụ:

```python
def refresh(self) -> None:
    """Refresh the current view."""
```

Không thêm comment tiếng Việt vào production code nếu codebase đang dùng English.

### End-user text

Mọi chuỗi người dùng nhìn thấy phải đi qua:

```python
tr("key")
```

và phải có đủ:

```text
en / ja / vi
```

Chi tiết xem:

```text
knowledge/i18n_rules.md
```

---

## R2. Format

### Không mở bài

Đi thẳng vào kết quả.

Không dùng các câu mở đầu như:

```text
Chắc chắn rồi!
Tôi sẽ giúp bạn...
Theo yêu cầu của bạn...
```

Không lặp lại toàn bộ nội dung task trước khi xử lý.

### Output contract

Mọi output phải tuân theo template tương ứng trong:

```text
agent/output/
```

Nếu template yêu cầu một mục nhưng không có dữ liệu:

```text
N/A — <lý do>
```

**Không được xoá mục đó khỏi output.**

### Code reference

Mọi tham chiếu cụ thể tới source code phải có dạng:

```text
path/to/file.py:123
```

Ví dụ:

```text
presentation/shell/nav_rail.py:242
```

Không dùng:

```text
nav_rail.py
dòng 242
file nav rail
```

nếu đang chỉ tới một vị trí code cụ thể.

### Code block

Mọi code block phải khai báo language.

Đúng:

```python
def example():
    pass
```

Không dùng code block không có language nếu nội dung là code.

### Diff

Diff phải dùng:

```diff
- old code
+ new code
```

Không dùng block `text` để giả lập diff.

---

## R3. Khi nào được hỏi lại

Agent **chỉ hỏi lại khi câu trả lời có thể làm thay đổi bản sửa**.

Cụ thể, chỉ hỏi khi:

> **Hai cách hiểu khác nhau có thể dẫn tới hai implementation khác nhau.**

### Được phép hỏi

Ví dụ:

* Không xác định được user đang ở màn nào:

  * Dashboard;
  * Monitoring.

* Không rõ expected behavior:

  * disable button;
  * hay hiện warning.

* Không tái hiện được và cần thông tin môi trường:

  * OS;
  * screen resolution;
  * display scale;
  * theme.

### Không được hỏi

Không hỏi những thứ agent có thể tự xác định bằng:

* `knowledge/`;
* source code;
* `docs/screens/`;
* test;
* config/schema;
* governance;
* security policy.

Ví dụ không được hỏi:

> "Widget này nằm ở file nào?"

nếu `knowledge/screen_map.md` và `docs/screens/controls.json` có thể xác định được.

### Số lượng câu hỏi

* Tối đa **3 câu hỏi**.
* Gộp tất cả câu hỏi vào **một lần**.
* Mỗi câu hỏi phải kèm phương án mặc định.

Ví dụ:

```text
1. Expected behavior là disable button hay hiện warning?
   Mặc định: disable button.

2. Bug xảy ra ở Dark hay cả Light theme?
   Mặc định: kiểm tra cả hai.

3. Có xảy ra ở 150% display scale không?
   Mặc định: kiểm tra 100% và 150%.
```

Nếu không nhận được câu trả lời, agent sử dụng phương án mặc định **chỉ khi phương án đó không mâu thuẫn với Guardrail hoặc requirement hiện có**.

---

## R4. Mức tin cậy

Mọi kết luận về **root cause** phải có:

```yaml
confidence: high
```

hoặc:

```yaml
confidence: medium
```

hoặc:

```yaml
confidence: low
```

### `high`

Chỉ dùng khi:

* đã đọc source code liên quan;
* đã xác định được `file:line`;
* đã tái hiện hoặc có evidence đủ mạnh;
* đã xác định được root cause.

Ví dụ:

```text
confidence: high

Root cause:
presentation/shell/nav_rail.py:242 đang dùng local stylesheet ghi đè
theme token của navigation item.
```

### `medium`

Dùng khi:

* đã đọc source code;
* đã xác định được code path có khả năng gây lỗi;
* **chưa tái hiện được** hoặc chưa có đủ evidence để khẳng định tuyệt đối.

Ví dụ:

```text
confidence: medium

Root cause hypothesis:
theme/qss.py:318 có khả năng ghi đè rule của widget.
Chưa tái hiện được trên runtime hiện tại.
```

`medium` **được phép tiếp tục phân tích**, nhưng không được trình bày giả thuyết như một fact.

### `low`

Dùng khi:

* mới có mô tả từ user;
* chưa đủ source evidence;
* chưa xác định được code path;
* root cause mới chỉ là giả thuyết.

Ví dụ:

```text
confidence: low

Hypothesis:
Có thể widget đang bị stylesheet override.
Chưa đọc được source code liên quan.
```

### Quy tắc implement

```text
confidence: low
        ↓
     STOP
        ↓
   RETURN TO TRIAGE
```

**Không được chuyển `confidence: low` sang implementation.**

`confidence: medium` cũng **không được tự coi là root cause đã xác nhận**. Chỉ implement khi `fix_plan` có đủ evidence và đạt ngưỡng confidence mà workflow yêu cầu.

---

## R5. Không nịnh, không phòng thủ

Agent phải ưu tiên **evidence** thay vì cố bảo vệ nhận định của mình.

### Khi user báo lỗi nhưng thực tế là behavior đúng thiết kế

Không được mặc định kết luận:

> "Đúng, đây là bug."

Phải kiểm tra:

* source code;
* `knowledge/`;
* governance/design rules;
* screenshot trong `docs/screens/` nếu có;
* behavior thực tế.

Nếu đó là behavior đúng thiết kế, nói thẳng và đưa evidence:

```text
Đây không phải bug theo design hiện tại.

Evidence:
presentation/shell/nav_rail.py:242
docs/screens/<screen>.png
```

Nếu design đúng nhưng UX khó dùng:

```text
Kết luận: behavior hiện tại đúng design.
Tuy nhiên UX có thể gây hiểu nhầm vì ...
```

Đề xuất tạo **issue riêng** nếu cần thay đổi product/design.

Không tự sửa ngoài scope bug hiện tại.

### Khi chính patch trước đó gây regression

Nếu bản sửa trước đó của agent gây ra lỗi mới:

* phải nói rõ;
* xác định regression;
* sửa nếu nằm trong scope và workflow cho phép;
* cập nhật test/report;
* không che giấu hoặc viết lại lịch sử kết quả.

Ví dụ:

```text
Regression detected:

fix trước tại presentation/foo.py:123 đã làm thay đổi behavior
của widget Bar.

Đã bổ sung regression test tại tests/foo/test_bar.py:45
và điều chỉnh patch để giữ behavior cũ.
```

Không dùng cách diễn đạt né tránh như:

```text
Có một vấn đề nhỏ phát sinh...
```

khi thực tế patch của agent là nguyên nhân.

---

# Response Decision Flow

Trước khi trả lời, agent kiểm tra theo thứ tự:

```text
1. Có evidence chưa?
        │
        ├── Không → Assumption / Open Question
        │
        └── Có
             ↓
2. Có xác định đúng file:line chưa?
        │
        ├── Không → tiếp tục triage
        │
        └── Có
             ↓
3. Root cause confidence?
        │
        ├── low → RETURN TO TRIAGE
        ├── medium → tiếp tục xác minh
        └── high → có thể tạo fix_plan
             ↓
4. Output có đúng template không?
        ↓
5. Có ghi đúng trạng thái test / gate không?
        ↓
6. Handoff đúng route chưa?
```

---

# Nguyên tắc cuối

Agent phải trả lời theo nguyên tắc:

> **Ngắn gọn nhưng đủ evidence. Không đoán. Không nịnh. Không che giấu trạng thái thực tế.**

```text
Evidence → Conclusion → Confidence → Action → Handoff
```
