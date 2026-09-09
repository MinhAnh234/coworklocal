# i18n — Quy tắc xử lý chuỗi hiển thị

**Nguồn:** docstring `i18n/__init__.py`

---

## 1. Ngôn ngữ được hỗ trợ

Cowork Local hỗ trợ 3 ngôn ngữ:

```python
LANGUAGES = {
    "en": "English",
    "ja": "日本語",
    "vi": "Tiếng Việt",
}

LANGUAGE_SHORT = {
    "en": "EN",
    "ja": "JP",
    "vi": "VN",
}

DEFAULT_LANGUAGE = "vi"
```

Ngôn ngữ mặc định là **Tiếng Việt (`vi`)**.

### Hàm `tr()`

Sử dụng:

```python
tr(key, **kwargs)
```

để lấy chuỗi hiển thị theo ngôn ngữ hiện tại.

Thứ tự fallback:

```text
Ngôn ngữ hiện tại → English (en) → chính key
```

Ví dụ, nếu đang dùng tiếng Nhật nhưng key `workspace.tab_folder` chưa có bản dịch tiếng Nhật:

```text
JA → EN → workspace.tab_folder
```

Ứng dụng **không được crash** chỉ vì thiếu bản dịch.

Nếu UI hiển thị một chuỗi dạng:

```text
workspace.tab_folder
```

thì đây là dấu hiệu cho thấy **đang thiếu translation key**.

### Placeholder

Nếu chuỗi có placeholder, truyền giá trị thông qua `kwargs`:

```python
tr("composer.attachments", n=3)
```

Việc `.format(**kwargs)` được thực hiện sau khi lấy chuỗi dịch.

---

## 2. Widget nào phải cập nhật khi đổi ngôn ngữ?

Có 2 loại widget:

| Loại widget         | Cách xử lý                                            |
| ------------------- | ----------------------------------------------------- |
| **Widget sống lâu** | `bind_*` cho chuỗi tĩnh; `on_language_changed(cb)` cho phần còn lại |
| **Widget tạm thời** | Không cần đăng ký callback; gọi `tr()` khi tạo widget |

### 2.0. `bind_*` — cách mặc định cho chuỗi tĩnh

`w.setToolTip(tr("k"))` chỉ đúng ở đúng thời điểm chạy dòng đó. `bind_*` gộp "gán ngay"
và "gán lại sau mỗi lần đổi ngôn ngữ" vào một lời gọi, dùng `weakref` nên không giữ widget
sống thêm và tự dọn khi widget bị xoá:

```python
from ...i18n import bind_dynamic, bind_items, bind_placeholder, bind_text, bind_tip

self.save_btn = bind_text(QPushButton(), "co4e.save")     # thay QPushButton(tr(...))
bind_tip(self.save_btn, "co4e.tt_save")                   # thay .setToolTip(tr(...))
bind_placeholder(self.chat_input, "co4e.chat_placeholder")
bind_items(self.perm_combo, [f"co4e.perm.{p}" for p in PERMISSION_PRESETS])
form.addRow(bind_text(QLabel(), "co4e.f_label"), self.label_edit)   # KHÔNG addRow(tr(...))
```

Ba luật:

1. **Chuỗi tĩnh → `bind_*`.** Đổi tại chỗ, **không thêm dòng** — quan trọng với file đã
   sát trần Gate S hoặc đang bị bánh cóc `LEGACY_ALLOWANCE` chốt (`quality_gates.md` §4).
2. **Chữ phụ thuộc trạng thái → `bind_dynamic(w, setter, fn)`**, với `fn` đọc trạng thái:
   nút Chạy ⇄ Dừng, tooltip Thu gọn ⇄ Mở rộng, nhãn có số đếm. Các nhánh xử lý trạng thái
   **vẫn** gọi setter trực tiếp như cũ để phản hồi ngay khi bấm; `bind_dynamic` chỉ lo lúc
   đổi ngôn ngữ. Bind cứng một nhãn động sẽ **xoá** trạng thái khi người dùng đổi ngôn ngữ
   giữa lúc đang chạy.
3. **Chữ là DỮ LIỆU thì không bind.** Tên agent, tên project, tên nhà cung cấp trong
   `config.PROVIDER_LABELS` — dịch danh tính là sai.

`QFormLayout.addRow(tr(...), w)` và `_add_section(outer, tr(...))` là hai bẫy hay gặp:
chúng tự dựng `QLabel` bên trong, không giữ tham chiếu nào để áp lại. Truyền
`bind_text(QLabel(), key)` hoặc truyền **khoá** thay vì chuỗi đã dịch.

### 2.0b. Nút do CHÍNH Qt vẽ chữ — `ui/dialog_buttons.py`

`tr()` không với tới được nhãn nút của mấy widget dựng sẵn: Qt lấy chữ từ bảng dịch của
riêng nó, mà ứng dụng không cài `QTranslator` nào (bản PySide6 đang dùng cũng không đóng
gói file `qtbase_*.qm` nào để cài). Kết quả: **luôn là tiếng Anh ở cả ba ngôn ngữ.**

| Không dùng | Dùng thay |
| --- | --- |
| `QDialogButtonBox(Save \| Cancel)` | `dialog_buttons(Save \| Cancel)` |
| `QMessageBox.question(...) == QMessageBox.Yes` | `confirm(parent, title, body)` |
| `QInputDialog.getText / getMultiLineText / getItem` | `ask_text` / `ask_multiline` / `ask_item` |

Muốn một nút mang chữ riêng thì truyền khoá vào `dialog_buttons`, **không** `setText(tr(...))`
sau khi dựng — lần đổi ngôn ngữ kế tiếp, ràng buộc sẽ áp lại khoá mặc định và xoá mất chữ đó:

```python
self.buttons = dialog_buttons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                              ok="schedtask.ai_confirm")
```

Ba cổng trong `tests/ui/test_i18n_khong_hardcode_chu.py` canh việc này.

### 2.1. Widget sống lâu

Ví dụ:

* Chrome của cửa sổ chính.
* Tab.
* Sidebar.
* Composer.

Các widget này vẫn tồn tại khi người dùng đổi ngôn ngữ.

Vì vậy phải:

1. Đăng ký `on_language_changed(cb)`.
2. Trong callback, gọi lại `tr()` cho các text của chính widget.
3. Callback phải chạy:

   * Một lần ngay khi đăng ký.
   * Mỗi lần người dùng đổi ngôn ngữ.

Tên callback được sử dụng trong repo:

```text
_retranslate()
_apply_i18n()
```

Có thể tham khảo implementation chuẩn từ:

```text
ui/workspace_tab.py:484
```

### 2.2. Widget tạm thời

Ví dụ:

* Settings dialog.
* Skills dialog.
* Flow dialog.
* Permission dialog.

Các dialog này được tạo lại từ đầu mỗi lần mở.

Vì vậy chỉ cần gọi `tr()` khi construct widget.

**Không cần đăng ký `on_language_changed()`**.

### Bug thường gặp

Triệu chứng:

> Đổi ngôn ngữ nhưng một label/nút vẫn giữ ngôn ngữ cũ.

Nguyên nhân thường là:

* Widget sống lâu nhưng chưa đăng ký `on_language_changed()`.
* Callback có đăng ký nhưng quên cập nhật label đó.

**Cách sửa đúng:**

`bind_*` tại chính dòng đang gán (mục 2.0), hoặc — nếu chữ phụ thuộc trạng thái/dữ liệu —
sửa trong `_retranslate()` / `_apply_i18n()` của chính widget.

**Không** giải quyết bằng cách gọi `tr()` ở một nơi khác chỉ để ép label thay đổi.

### Cách TÌM ra hết các chỗ bị lỗi

Đừng grep chuỗi tiếng Việt trong source: lượt audit tháng 9/2026 grep ra 962 dòng mà
**không dòng nào** là lỗi thật (toàn docstring), trong khi 84 lỗi thật lại không xuất hiện
— vì chúng đi qua `tr()` đúng cách, chỉ thiếu người áp lại.

Phép đo đúng nằm ở `tests/ui/test_i18n_khong_con_chu_cu.py`: dựng `MainWindow` thật, thay
`tr()` bằng chuỗi **mốc**, gọi `set_language()`, rồi tìm chỗ **không** mang mốc. Hai chi
tiết mà bản kiểm ngây thơ sẽ sai:

* `from ...i18n import tr` copy tham chiếu vào namespace từng module → phải thay `tr` ở
  **mọi** module đã import, không chỉ `i18n.tr`;
* lưới vẽ lại bằng `deleteLater()` để lại widget cũ còn sống → không
  `sendPostedEvents(DeferredDelete)` thì báo oan hàng chục widget bóng ma (lượt audit đầu
  báo 84 lỗi, trong đó 65 là bóng ma và widget bị `id()` cấp lại làm cắt vòng quét).

Chạy: `QT_QPA_PLATFORM=offscreen pytest tests/ui/test_i18n_khong_con_chu_cu.py -q`

---

## 3. Tổ chức file translation

Thư mục `i18n/` được chia theo **màn hình/chức năng**, không gom tất cả translation vào một file lớn.

Ví dụ:

```text
i18n/
├── login_dialog.py
├── sidebar.py
├── composer.py
├── cowork_tab.py
├── settings_dialog.py
├── skills_dialog.py
├── libreoffice_view.py
├── agents_admin_tab.py
├── monitoring_overview.py
└── hint.py
```

Mỗi file export một dictionary có dạng:

```text
key → {
    "en": "...",
    "ja": "...",
    "vi": "..."
}
```

`i18n/__init__.py` sẽ import và gộp các dictionary này.

### Khi thêm key mới

Thực hiện theo 3 bước:

#### Bước 1 — Chọn đúng file

Đưa key vào file tương ứng với màn hình/chức năng.

Ví dụ:

```text
workspace.* → file liên quan đến workspace
composer.* → composer.py
settings.* → settings_dialog.py
```

**Không** đưa key vào `login_dialog.py` chỉ vì file đó đang có nhiều key nhất.

#### Bước 2 — Điền đủ 3 ngôn ngữ

Mỗi key mới phải có:

```text
en
ja
vi
```

Thiếu `ja` là lỗi đặc biệt cần chú ý vì có thể chỉ được phát hiện khi khách hàng Nhật sử dụng.

#### Bước 3 — Đặt tên key nhất quán

Format khuyến nghị:

```text
<màn hình>.<thành phần>
```

Ví dụ:

```text
workspace.tab_folder
app.nav.recents
```

Tên key phải mô tả rõ nó được dùng ở đâu và cho thành phần nào.

---

## 4. Các rủi ro thường gặp với tiếng Nhật và tiếng Việt

| Vấn đề                             | Triệu chứng                                  | Cách xử lý                                                                                       |
| ---------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Độ dài chuỗi khác nhau             | EN vừa nút nhưng VI bị tràn hoặc JA bị `...` | Không đặt width cố định dựa trên tiếng Anh. Dùng `sizeHint()`, `minimumWidth` hoặc cho phép wrap |
| Dấu tiếng Việt bị cắt              | Các chữ như `Ắ`, `ộ` bị mất dấu              | Không dùng `setFixedHeight()` cho label. Để layout tự tính chiều cao                             |
| Thiếu font/glyph tiếng Nhật        | Xuất hiện `□□□`                              | Kiểm tra `_FONT` trong `theme/palettes.py` và khai báo font fallback                             |
| Sắp xếp chuỗi                      | Project có dấu được sắp xếp không đúng       | Dùng locale-aware sorting, không dùng `sorted()` một cách máy móc                                |
| Số ký tự không phản ánh chiều rộng | Text bị elide sai, đặc biệt với tiếng Nhật   | Dùng `QFontMetrics.horizontalAdvance()`, không dùng `len()` để đo chiều rộng                     |

### Đặc biệt lưu ý về độ dài text

Không được giả định:

```text
số ký tự = chiều rộng hiển thị
```

Ví dụ hai chuỗi có cùng số ký tự nhưng có thể có chiều rộng hiển thị khác nhau.

Khi cần đo text trên UI, dùng:

```python
QFontMetrics.horizontalAdvance(...)
```

---

## 5. Checklist khi sửa lỗi i18n

Trước khi hoàn thành bản vá i18n, phải kiểm tra:

* [ ] Key mới có đủ **`en` / `ja` / `vi`**?

* [ ] Đã chuyển qua cả 3 ngôn ngữ **ngay trong lúc app đang chạy** chưa?

  ```
  Không chỉ restart app rồi kiểm tra.
  ```

* [ ] `ja` có **khác** `en` không? Bằng nhau nghĩa là chưa dịch — trừ tên thương hiệu /
  ký hiệu, và khi đó phải khai vào `KHOA_KHONG_CAN_DICH` kèm lý do.

* [ ] Chuỗi tĩnh đã dùng `bind_text` / `bind_tip` / `bind_placeholder` / `bind_items`
  thay cho `setX(tr(...))` một lần?

* [ ] Chữ phụ thuộc trạng thái đã dùng `bind_dynamic` (không bind cứng, kẻo mất trạng thái)?

* [ ] Nếu widget sống lâu và còn phần không bind được, đã đăng ký:

  ```
  `on_language_changed(...)`
  ```

* [ ] Callback `_retranslate()` hoặc `_apply_i18n()` đã cập nhật **tất cả text liên quan**?

* [ ] Đã chạy `pytest tests/ui/test_i18n_khong_con_chu_cu.py -q` và nó **xanh**?

* [ ] Không còn chuỗi hardcode mới trong bản vá?

* [ ] Nút hộp thoại đi qua `ui/dialog_buttons.py` (mục 2.0b), không dựng
  `QDialogButtonBox` / `QMessageBox.question` / `QInputDialog.get*` trực tiếp?

* [ ] Layout vẫn đúng với **chuỗi dài nhất** trong 3 ngôn ngữ?

* [ ] Không dùng `len()` để tính chiều rộng text?

* [ ] Nếu có thay đổi UI, đã kiểm tra cả Dark Mode và Light Mode?

---

## 6. Nguyên tắc quan trọng

Khi sửa lỗi i18n, **không sửa triệu chứng ở nơi khác**.

Ví dụ:

```text
Đổi ngôn ngữ
      ↓
Label X không thay đổi
      ↓
Kiểm tra widget X
      ↓
Widget sống lâu?
      ↓
Có on_language_changed()?
      ↓
_retranslate() có cập nhật Label X?
```

Nếu thiếu callback hoặc callback bỏ sót label, hãy sửa **đúng callback của widget đó**.

Không thêm các lệnh `tr()` rải rác ở nơi khác chỉ để làm cho UI thay đổi.

Mục tiêu là đảm bảo cơ chế i18n hoạt động đúng và nhất quán cho toàn bộ ứng dụng.
