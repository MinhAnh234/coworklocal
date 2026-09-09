# examples.md — Good / Bad examples

> Trách nhiệm của file này: cho AI học **cách sửa và cách báo cáo**, không phải học nghiệp vụ.
> Code trong ví dụ là code minh hoạ, không phải code thật của repo — không copy vào codebase.
> File này có ưu tiên **thấp nhất**: khi xung đột với `output_contract.md` thì contract thắng,
> và khi xung đột với convention của file đang sửa thì file đang sửa thắng.

---

## 1. Che triệu chứng vs. sửa nguyên nhân gốc

### BAD

```python
def load_workspace(self):
    try:
        return self._repo.get_active()
    except Exception:
        return None          # hết crash là được
```

**Sai ở đâu:** `except Exception` nuốt mọi lỗi, kể cả lỗi lập trình. Bug không mất, nó chỉ
chuyển thành `None` rồi nổ ở chỗ khác xa hơn, khó debug hơn. Không ai biết vì sao lỗi.
Vi phạm `quality_gate.md` G1.

### GOOD

```python
def load_workspace(self):
    # get_active() trả None khi config chưa nạp xong (repo khởi tạo lazy),
    # nên caller phải nạp config trước — xem CH-02.
    workspace = self._repo.get_active()
    if workspace is None:
        raise WorkspaceNotReadyError("Config chưa nạp, gọi load_config() trước")
    return workspace
```

**Đúng ở đâu:** nguyên nhân gốc (khởi tạo lazy) được nêu trong comment; lỗi được báo rõ ràng
thay vì bị nuốt; caller được sửa ở một change riêng có ID truy vết.

---

## 2. Layout: ép kích thước vs. để layout tự co giãn

### BAD

```python
self.title = QLabel(name)
self.title.setFixedHeight(24)        # ép cho vừa
self.title.setFixedWidth(180)
layout.addWidget(self.title)
```

**Sai ở đâu:** tên dài hơn 180px sẽ bị cắt; ở màn hình scale DPI 150% chữ cao hơn 24px
nên bị cắt ngang; cửa sổ phóng to thì label không giãn theo. Đây chính là dạng bug
"chữ bị cắt" mà lần sau lại phải fix tiếp. Vi phạm G5.

### GOOD

```python
self.title = QLabel(name)
self.title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
self.title.setWordWrap(True)
layout.addWidget(self.title, stretch=1)
```

**Đúng ở đâu:** chiều cao do nội dung và font quyết định (an toàn với mọi DPI);
chiều ngang giãn theo cửa sổ; text dài xuống dòng thay vì bị cắt.

> Kích thước cứng **được phép** khi nó thật sự là hằng số thiết kế — ví dụ ô icon 16×16 —
> và phải nêu lý do đó trong section Changes.

---

## 3. Màu và khoảng cách: hard-code vs. đi qua theme

### BAD

```python
self.card.setStyleSheet(
    "background: #2b2b2b; border-radius: 8px; padding: 12px;"
)
```

**Sai ở đâu:** màu `#2b2b2b` chỉ đúng ở theme tối — đổi sang theme sáng là chữ đen trên nền đen.
Bán kính và padding lệch với các card khác trong app. Sửa theme sau này không ảnh hưởng
được tới widget này. Vi phạm G3.

### GOOD

```python
# Hình dạng và màu do theme quyết định; ở đây chỉ đặt objectName để QSS bắt được.
self.card.setObjectName("workspaceCard")
```

```
/* theme/qss.py — thêm selector riêng, KHÔNG sửa selector dùng chung */
QWidget#workspaceCard {
    background: $surface;
    border-radius: ${radius}px;
    padding: 12px;
}
```

**Đúng ở đâu:** màu lấy từ token nên tự đúng ở cả hai theme; hình dạng nằm cùng chỗ với
phần còn lại của app; sửa một widget mà không đụng vào selector dùng chung.

---

## 4. Phạm vi diff: sửa lan vs. diff tối thiểu

### BAD

```
Đã sửa 9 file:
- ui/workspace_tab.py     (fix bug + đổi tên biến cho dễ đọc + sắp lại import)
- ui/chat_panel.py        (thấy code tương tự nên sửa luôn cho nhất quán)
- ui/sidebar.py           (format lại theo black)
- theme/qss.py            (gộp mấy selector trùng nhau)
- ...
```

**Sai ở đâu:** reviewer không phân biệt được đâu là fix, đâu là cleanup, nên không review nổi.
Nếu phải revert thì revert luôn cả phần cleanup. Bug ở `chat_panel.py` chưa được tái hiện và
kiểm chứng, chỉ "sửa cho nhất quán". Vi phạm G2.

### GOOD

```
| CH-ID | File:line | Loại | Thay đổi | Lý do |
|---|---|---|---|---|
| CH-01 | ui/workspace_tab.py:142 | Logic | Nạp config trước khi gọi get_active() | Nguyên nhân gốc: repo khởi tạo lazy |
| CH-02 | tests/test_workspace_tab.py (mới) | Test | Thêm test hồi quy cho trường hợp config chưa nạp | Chốt lại hành vi vừa sửa |
```

Phần phát hiện dọc đường được ghi vào Open Questions, **không** sửa trong lần này:

```
| OQ-02 | ui/chat_panel.py:88 có pattern tương tự, nghi cùng lỗi. Tách task riêng để tái hiện và fix? | Người dùng | Tách task riêng | No |
```

---

## 5. Bằng chứng kiểm chứng: suy đoán vs. output thật

### BAD

```
## 4. Verification
- Đã sửa xong, test chắc chắn pass.
- Layout giờ hiển thị đúng.
```

**Sai ở đâu:** "chắc chắn pass" là suy đoán, không phải bằng chứng — có thể chưa từng chạy test.
"Hiển thị đúng" không nói đã kiểm ở kích thước nào, theme nào. Đây là vi phạm **điều kiện chặn
tuyệt đối** số 3 trong `quality_gate.md`.

### GOOD

```
## 4. Verification
| EV-ID | Cách kiểm | Kết quả |
|---|---|---|
| EV-01 | python -m pytest tests/test_workspace_tab.py -q (trước khi sửa) | 1 failed, 12 passed - test hồi quy fail đúng như mong đợi |
| EV-02 | python -m pytest tests/test_workspace_tab.py -q (sau khi sửa) | 13 passed |
| EV-03 | python -m pytest tests -q | 248 passed, 3 skipped |
| EV-04 | Mở app, cửa sổ 1024x768 và 1920x1080, theme sáng và tối | Label không bị cắt ở cả 4 tổ hợp |
| EV-05 | Đặt tên workspace 120 ký tự | Text xuống dòng, card giãn cao, không tràn |
```

Khi có test fail còn lại thì **ghi ra**, không che:

```
| EV-06 | python -m pytest tests -q | 246 passed, 2 failed - tests/test_theme.py fail sẵn từ trước khi sửa (xác nhận bằng git stash), không liên quan thay đổi này |
```

---

## 6. Bảng tổng hợp style rules học từ ví dụ

| # | Rule | Ví dụ vi phạm |
|---|---|---|
| 1 | Sửa nguyên nhân gốc, không nuốt lỗi | `except Exception: return None` |
| 2 | Không thêm kiểm tra null khi chưa hiểu vì sao null | `if x is None: return` cho hết crash |
| 3 | Layout dùng size policy và stretch, không ép kích thước | `setFixedHeight(24)` |
| 4 | Màu đi qua `theme/palettes.py`, hình dạng qua `theme/qss.py` | `setStyleSheet("background: #2b2b2b")` |
| 5 | Lệch một widget thì thêm selector theo `objectName` | Sửa selector `QWidget` dùng chung |
| 6 | Một lần fix một việc, không kèm cleanup | Fix bug + format lại 9 file |
| 7 | Phát hiện dọc đường ghi vào Open Questions | Tự sửa luôn chỗ chưa tái hiện được |
| 8 | Bằng chứng là output thật, không phải suy đoán | "test chắc chắn pass" |
| 9 | Test fail thì ghi ra kèm output | Chỉ báo cáo phần pass |
| 10 | Layout phải kiểm đủ 2 kích thước × 2 theme × text dài | "Layout giờ hiển thị đúng" |
| 11 | Mỗi file trong diff phải giải thích được lý do | "sửa cho nhất quán" |
| 12 | Không nới assert để test pass | Đổi `assert x == 5` thành `assert x is not None` |
