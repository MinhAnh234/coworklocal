# Theme & Design Tokens — Luật màu sắc của Cowork Local

> Knowledge module dành cho các agent xử lý **UI Visual / Theme / QSS** của Cowork Local.

## Nguồn chính

* `theme/__init__.py` — docstring và API theme
* `theme/palettes.py` — định nghĩa Palette/token
* `theme/qss.py` — `_TEMPLATE` và stylesheet
* `theme/qss_controls.py` — style cho các Qt controls

---

# 1. Luật quan trọng nhất

> **Ngoài thư mục `theme/`, không file nào được tự định nghĩa màu.**

Luồng màu chuẩn của Cowork Local:

```text
Palette
   ↓
token ngữ nghĩa
   ↓
_TEMPL​ATE
   ↓
stylesheet(theme)
   ↓
QApplication.setStyleSheet(...)
```

Nói đơn giản:

> **Widget không tự chọn màu. Theme quyết định màu.**

---

# 2. Hai cách hợp lệ để widget có màu

## Cách 1 — Style bằng QSS

Đây là cách mặc định.

Widget đặt `objectName`, sau đó style được định nghĩa trong:

```text
theme/qss.py
```

Ví dụ:

```python
widget.setObjectName("my_widget")
```

và style tương ứng nằm trong `_TEMPLATE`.

---

## Cách 2 — Widget tự vẽ bằng `QPainter`

Dùng cho các thành phần như:

* chart;
* canvas;
* syntax highlighter;
* custom painting.

Code phải lấy màu từ:

```python
current_palette()
```

Ví dụ:

```python
palette = current_palette()
```

Sau đó dùng token từ palette.

---

# 3. Những cách KHÔNG được phép

Không được tự đặt màu trong UI code.

### ❌ Hardcode HEX

```python
self.label.setStyleSheet("color: #dc2626;")
```

### ❌ Hardcode tên màu

```python
pen.setColor(QColor("red"))
```

### ❌ Hardcode RGBA

```python
self.card.setStyleSheet(
    "background: rgba(0,0,0,.1)"
)
```

Các trường hợp này phải bị reject khi review.

### Rule ngắn gọn

```text
Không có màu literal ngoài theme/
```

Không chỉ tránh `#hex`, mà cả:

* tên màu;
* RGB;
* RGBA;
* stylesheet cục bộ chứa màu.

---

# 4. API Theme cần nhớ

| API                             | Dùng để                                             |
| ------------------------------- | --------------------------------------------------- |
| `theme.stylesheet(theme)`       | Tạo QSS cho toàn app                                |
| `theme.set_active_theme(theme)` | Ghi nhận theme hiện đang active                     |
| `theme.current_theme()`         | Lấy theme hiện tại: `dark` / `light`                |
| `theme.current_palette()`       | Lấy Palette của theme hiện tại                      |
| `theme.palette(theme)`          | Lấy Palette của một theme cụ thể                    |
| `theme.resolve_theme("system")` | Xác định dark/light theo OS                         |
| `theme.role_colors(theme)`      | Lấy màu theo role: user/assistant/tool/result/error |

---

## Khi đổi theme

Hai lệnh này phải đi cùng nhau:

```python
theme.set_active_theme(theme)
app.setStyleSheet(theme.stylesheet(theme))
```

Không được chỉ gọi `setStyleSheet()` mà quên cập nhật active theme.

---

# 5. `current_palette()` dùng để làm gì?

Code vẽ bằng `QPainter` phải dùng:

```python
current_palette()
```

Không được mỗi lần `paintEvent()` lại đọc:

```text
config.json
```

Lý do:

```text
paintEvent()
   ↓
repaint
   ↓
đọc config
   ↓
lặp lại rất nhiều lần
```

Điều này từng gây vấn đề hiệu năng thực tế.

Vì vậy:

> `current_palette()` tồn tại để custom painting lấy màu nhanh từ theme hiện tại.

---

# 6. Palette và Design Token

`Palette` là:

```python
@dataclass(frozen=True)
```

Token phải mang **ý nghĩa**, không phải tên màu.

### ❌ Không đặt token kiểu:

```text
blue
grey2
dark_blue
light_grey
```

### ✅ Đặt theo vai trò:

```text
accent
danger
text
text_muted
surface
surface_raised
```

Lợi ích:

> Thêm theme mới = thêm một `Palette`, không phải viết lại stylesheet.

---

# 7. Các nhóm token chính

## 7.1. Surface — các mức bề mặt

| Token            | Dùng cho                                     |
| ---------------- | -------------------------------------------- |
| `bg`             | Nền chính của cửa sổ/canvas                  |
| `surface`        | Panel, card, group box                       |
| `surface_raised` | Input, list, tree — nơi người dùng nhập/chọn |
| `overlay`        | Menu, tooltip, popup                         |
| `sunken`         | Log, code, terminal — vùng chủ yếu để đọc    |
| `hover`          | Trạng thái hover                             |
| `active`         | Trạng thái đang active/pressed               |

### Lưu ý

`surface` **không có nghĩa là nav rail**.

Nav rail có chủ đích riêng về độ sáng/tối.

---

## 7.2. Text

Các token chính:

```text
text
text_muted
...
```

Dùng token theo vai trò thay vì tự chọn màu.

---

## 7.3. Accent

Có hai token:

```text
accent
accent_solid
```

**Hai token này khác nhau có chủ đích.**

### `accent`

Dùng cho accent thông thường, ví dụ:

* trạng thái;
* thành phần UI;
* điểm nhấn.

### `accent_solid`

Dùng khi accent trở thành **nền đặc và bên trên có chữ**.

Lý do:

> Một màu accent có thể đủ sáng để đọc khi dùng như chữ trên nền tối, nhưng lại quá sáng khi dùng làm nền cho chữ trắng.

Vì vậy:

```text
Chữ trên nền accent đặc
        ↓
accent_solid
```

Không tự lấy `accent` chỉ vì nó có vẻ "cùng màu".

---

## 7.4. State

Ví dụ:

```text
danger
...
```

Các state token cũng phải mang ý nghĩa, không đặt theo tên màu.

---

## 7.5. Conversation roles

Có các token:

```text
role_user
role_assistant
role_tool
role_result
role_error
```

Dùng để phân biệt các role trong giao diện hội thoại.

---

## 7.6. Code / Syntax

Ví dụ:

```text
code_string
...
```

Dùng cho syntax highlighting.

---

# 8. Các nguyên tắc thiết kế — đừng nhầm thành bug

Một số đặc điểm nhìn "khác mắt" nhưng **có chủ đích**.

Không được tự ý sửa chỉ vì người dùng nói "trông hơi tối" hoặc "không giống app hiện đại".

---

## 8.1. Không gradient, không glow

Thiết kế lấy cảm hứng từ:

```text
VS Code Dark Modern
VS Code Light Modern
```

Phong cách chính:

* surface phẳng;
* góc gần vuông;
* không gradient;
* không glow;
* một accent chính;
* accent dành cho thứ người dùng tương tác.

---

## 8.2. Độ sâu đến từ surface và border

Không tạo chiều sâu bằng cách:

```text
đổi màu quá mạnh
```

Thay vào đó dùng:

```text
surface hierarchy
+
border mảnh
```

---

# 9. Nav rail tối hơn là thiết kế có chủ đích

Silhouette của Cowork Local lấy theo VS Code:

```text
NAV RAIL
    ↓
tối hơn
    ↓
CONTENT AREA
```

Không phải:

```text
nav rail sáng hơn content
```

Vì vậy nếu user báo:

> "Menu bên trái tối quá."

thì **chưa được kết luận ngay là visual bug**.

Đây có thể là design intent.

Xem thêm:

```text
examples/bad_fix.md
```

để tránh sửa nhầm.

---

# 10. Contrast — WCAG AA

Body text và chữ trên button nền đặc phải đạt:

```text
Contrast ratio ≥ 4.5:1
```

Đây là yêu cầu tối thiểu.

Khi thay token/màu:

```text
Dark theme
+
Light theme
+
text/background
```

đều phải được kiểm tra.

---

## Không khôi phục màu VS Code cũ nếu màu đó không đạt AA

Một số màu gốc của VS Code không đạt yêu cầu AA.

Các giá trị đã được Cowork Local điều chỉnh vừa đủ, ví dụ:

| Trường hợp               | Contrast cũ |
| ------------------------ | ----------: |
| Dark line                |      3.59:1 |
| Chữ mờ trên sidebar sáng |      4.28:1 |
| Xanh lá sáng             |      4.33:1 |
| Hổ phách sáng            |      3.12:1 |

Các chỗ này có comment ghi lại giá trị gốc.

### Rule

**Không đưa chúng trở lại giá trị VS Code ban đầu.**

Mục tiêu của Cowork Local là:

```text
VS Code silhouette
+
WCAG AA
```

không phải copy nguyên xi mọi giá trị màu của VS Code.

---

# 11. ⚠️ Combo Box và `_chevron_asset`

Một lỗi dễ gặp:

> Combo box mất mũi tên.

Nguyên nhân liên quan đến cách Qt xử lý QSS.

---

## 11.1. `image:` trong QSS không nhận `QPixmap`

QSS:

```text
image:
```

chỉ nhận đường dẫn tới:

* file;
* resource.

Không nhận trực tiếp:

```text
QPixmap
```

---

## 11.2. Style `::drop-down` sẽ làm Qt ngừng vẽ arrow mặc định

Khi style các selector như:

```text
::drop-down
::up-button
::down-button
```

Qt có thể ngừng vẽ mũi tên mặc định.

---

## 11.3. Cowork Local dùng `_chevron_asset`

Trong:

```text
theme/palettes.py
```

`_chevron_asset`:

1. render chevron thành PNG;
2. lưu vào thư mục tạm;
3. cache theo:

```text
(direction, color)
```

---

## Khi debug combo box

Nếu thấy:

> Combo box mất mũi tên.

Hãy kiểm tra trước:

```text
stylesheet cục bộ
        ↓
::drop-down
```

Đây thường là nguyên nhân.

Cache nằm tại:

```text
%TEMP%/cowork_local_theme/chevron_*.png
```

Nếu đang test màu mới, có thể xóa cache để buộc render lại.

---

# 12. Checklist sửa bug màu sắc/theme

Trước khi hoàn thành visual fix, kiểm tra:

### Theme coverage

* [ ] Bug đã được kiểm tra trên **Dark** chưa?
* [ ] Bug đã được kiểm tra trên **Light** chưa?
* [ ] Có thể dùng screenshot:

  * `docs/screens/*-dark.png`
  * `docs/screens/*-light.png`

### Token

* [ ] Patch dùng semantic token thay vì hex literal?
* [ ] Không có `setStyleSheet()` cục bộ để thay màu?
* [ ] Không có `QColor("red")`, `QColor("blue")`, v.v.?
* [ ] Nếu thêm token mới, đã thêm cho **cả `DARK` và `LIGHT`**?
* [ ] Token mới có tên theo **ý nghĩa**, không theo màu?

### Accent

* [ ] Chữ trên nền accent đặc đã dùng `accent_solid`?
* [ ] Không dùng `accent` chỉ vì hai token có vẻ giống nhau?

### Accessibility

* [ ] Contrast đạt **≥ 4.5:1**?
* [ ] Đã kiểm tra cả text và button có nền đặc?

### Theme lifecycle

* [ ] Widget tạo sau khi đổi theme có nhận đúng stylesheet?
* [ ] Đã kiểm tra vấn đề lazy screen theo `qt_pitfalls.md` **P07**?

### Design intent

* [ ] Không vô tình thêm gradient?
* [ ] Không thêm glow?
* [ ] Không làm nav rail sáng hơn content?
* [ ] Không khôi phục các màu VS Code cũ đã bị loại vì không đạt WCAG AA?

---

# 13. Quy tắc review nhanh

Khi gặp một defect liên quan màu sắc, đi theo thứ tự:

```text
1. Xác định widget
       ↓
2. Kiểm tra objectName
       ↓
3. Tìm rule trong theme/qss.py
       ↓
4. Kiểm tra token trong palettes.py
       ↓
5. Kiểm tra DARK + LIGHT
       ↓
6. Kiểm tra contrast
       ↓
7. Kiểm tra local setStyleSheet()
       ↓
8. Kiểm tra lazy theme lifecycle (P07)
       ↓
9. Xác định đây là bug thật hay design intent
       ↓
10. Chỉ sau đó mới tạo fix_plan
```

## Nguyên tắc cuối

```text
UI code
  ↓
không tự chọn màu
  ↓
semantic token
  ↓
Palette
  ↓
_TEMPL​ATE / current_palette()
  ↓
theme
```

**Nếu một màu mới cần xuất hiện, trước tiên hỏi:**

> "Màu này đang đại diện cho vai trò gì?"

Sau đó tạo hoặc dùng **semantic token** phù hợp.

Không hỏi:

> "Mình muốn màu xanh nào?"

Vì trong Cowork Local, **ý nghĩa của màu quan trọng hơn bản thân màu**.
