# Nguyên nhân gốc hay gặp của bug UI PySide6

Danh mục để **chẩn đoán**, không phải để đoán bừa. Mỗi mục: triệu chứng người dùng mô tả →
nguyên nhân → cách xác minh → hướng sửa.

---

## Nhóm A — Layout & kích thước

### P01. Widget bị bóp/giãn sai khi resize
**Triệu chứng:** "kéo cửa sổ to ra thì bảng bên phải nuốt hết chỗ", "panel trái biến mất".
**Nguyên nhân:** thiếu `stretch` factor, hoặc `QSizePolicy` sai (`Preferred` vs `Expanding`).
**Xác minh:** đọc `addWidget(w, stretch)` / `setStretchFactor` / `setSizePolicy` quanh chỗ dựng.
**Sửa:** đặt stretch tường minh trên `QSplitter`/`QBoxLayout`. Không sửa bằng `setFixedWidth`.

### P02. Chữ bị cắt / hiện `...` ở một số ngôn ngữ hoặc scale
**Triệu chứng:** "nút bị mất chữ", "tên project chỉ hiện một nửa".
**Nguyên nhân:** `setFixedWidth`/`setFixedSize` tính theo chuỗi tiếng Anh ở 100% scale.
**Xác minh:** `grep -n "setFixedWidth\|setFixedSize\|setMaximumWidth" <file>`; thử với `vi`/`ja`.
**Sửa:** dùng `minimumWidth` + `sizeHint`, hoặc `QFontMetrics.horizontalAdvance` cho chuỗi
dài nhất trong 3 ngôn ngữ. Xem `i18n_rules.md` §4.

### P03. Nội dung trong `QScrollArea` không cuộn được / bị nén
**Nguyên nhân:** quên `setWidgetResizable(True)`, hoặc đặt widget con vào scroll area
**sau** khi đã `setWidget`.
**Sửa:** `setWidgetResizable(True)` và dựng xong nội dung rồi mới `setWidget`.

### P04. Khoảng trắng thừa quanh panel
**Nguyên nhân:** `setContentsMargins`/`setSpacing` mặc định của layout lồng nhau cộng dồn.
**Xác minh:** đếm số layout lồng; repo dùng `setContentsMargins(10,10,10,10)` +
`setSpacing(10)` ở shell (`main_window.py:145`), layout con thường phải là `(0,0,0,0)`.

### P05. Bug chỉ xảy ra trên màn hình scale 125%/150%
**Triệu chứng:** "máy em bình thường, máy sếp bị lệch".
**Nguyên nhân:** hằng số pixel cứng, icon raster không có bản @2x, `QPixmap` không set
`devicePixelRatio`.
**Xác minh:** hỏi người dùng độ phân giải + mức scale Windows; test lại bằng biến môi trường
`QT_SCALE_FACTOR=1.5`.
**Sửa:** dùng đơn vị theo `QFontMetrics`, icon SVG hoặc `icon()` từ `ui/icons.py`.

---

## Nhóm B — Stylesheet & theme

### P06. `setStyleSheet` cục bộ đè mất style toàn app
**Triệu chứng:** "một chỗ nhìn khác hẳn phần còn lại", "combo box mất mũi tên".
**Nguyên nhân:** gọi `widget.setStyleSheet(...)` — QSS con **thay thế** chứ không merge với
QSS ứng dụng cho subcontrol đó. Riêng `::drop-down` bị style là Qt ngừng vẽ mũi tên mặc
định (xem `theme_tokens.md` §5).
**Sửa:** gỡ stylesheet cục bộ, gán `objectName`, style trong `theme/qss.py`.

### P07. Widget dựng lười không nhận theme / ngôn ngữ mới
**Triệu chứng:** "đổi sang giao diện sáng rồi mà màn Giám sát vẫn tối", "chỉ màn đó bị".
**Nguyên nhân:** Dashboard / Schedule / Monitoring chỉ được dựng ở lần mở đầu tiên
(`presentation/shell/page_registry.py::_ensure_page`). Chúng **bỏ lỡ** sự kiện đổi theme
hoặc đổi ngôn ngữ đã phát trước đó.
**Xác minh:** mở app → đổi theme → *rồi mới* bấm vào màn đó. Nếu lỗi tái hiện thì đúng P07.
**Sửa:** áp lại stylesheet/`tr()` trong `_ensure_page` sau khi dựng, hoặc để widget tự đăng ký
listener ngay trong `__init__`. Không sửa trong từng widget con.

### P08. Style không áp lại sau khi đổi property động
**Triệu chứng:** "nút vẫn xám sau khi đã chọn xong".
**Nguyên nhân:** QSS selector dạng `[state="active"]` chỉ được đánh giá lại khi ép polish.
**Sửa:** `w.style().unpolish(w); w.style().polish(w)` sau khi `setProperty`.

### P09. Bug chỉ có ở một theme
**Xác minh bắt buộc:** đối chiếu `docs/screens/<slug>-dark.png` và `<slug>-light.png`.
**Nguyên nhân thường gặp:** dùng `accent` ở chỗ cần `accent_solid`, hoặc token bề mặt sai bậc
(`surface` thay vì `surface_raised`).

---

## Nhóm C — Signal, slot, luồng

### P10. Bấm một lần chạy hai lần
**Triệu chứng:** "gửi 1 tin mà hiện 2", "tạo trùng task".
**Nguyên nhân:** `connect()` được gọi lại mỗi lần refresh/rebuild mà không `disconnect()`.
**Xác minh:** `grep -n "\.connect(" <file>` và tìm xem có nằm trong hàm được gọi nhiều lần không.
**Sửa:** connect một lần trong `__init__`, hoặc `Qt.UniqueConnection`.

### P11. UI đứng khi chạy tác vụ dài
**Triệu chứng:** "app treo khi bấm Phân tích", "vòng xoay không quay".
**Nguyên nhân:** gọi LLM / đọc file lớn / gọi MCP ngay trong GUI thread.
**Sửa:** đẩy xuống service của `application/` chạy async/worker; GUI chỉ nhận signal.
Đây cũng là vi phạm kiến trúc (`guardrail.md` G3), không chỉ là bug hiệu năng.

### P12. Widget biến mất không lý do
**Nguyên nhân:** không có parent, bị Python GC thu hồi; hoặc bị `deleteLater` sớm.
**Sửa:** truyền `parent` khi khởi tạo, hoặc giữ tham chiếu trên `self`.

### P13. Truy cập widget đã bị xoá → crash
**Triệu chứng:** "đóng dialog xong app tắt luôn".
**Nguyên nhân:** slot vẫn chạy sau khi C++ object đã destroy (`RuntimeError: Internal C++ object already deleted`).
**Sửa:** `disconnect` trong `closeEvent`, hoặc dùng `QPointer`/kiểm tra `shiboken6.isValid`.

### P14. Dữ liệu cũ hiện lại sau khi đã cập nhật
**Nguyên nhân:** view đọc từ cache/model không được `beginResetModel`/`endResetModel`,
hoặc widget được `hide()` chứ không rebuild.

---

## Nhóm D — Vẽ tay & hiệu năng

### P15. Nhấp nháy khi chuyển màn hoặc khi cuộn
**Nguyên nhân:** `repaint()` gọi tay trong vòng lặp, hoặc `paintEvent` đọc file/config.
**Sửa:** dùng `update()` (gộp lần vẽ), và đọc màu qua `current_palette()` — đã được cache
sẵn chính vì lý do này (`theme_tokens.md` §2).

### P16. Chart / canvas vẽ đè, để lại vệt
**Nguyên nhân:** không xoá nền trong `paintEvent`, hoặc `QPainter` không `end()`.

### P17. Icon mờ hoặc sai màu ở dark/light
**Nguyên nhân:** icon raster một màu cố định.
**Sửa:** lấy qua `ui/icons.py::icon`, không load PNG trực tiếp.

---

## Nhóm E — Vòng đời & dữ liệu

### P18. Trạng thái rỗng/đang tải/lỗi không có giao diện riêng
**Triệu chứng:** "màn hình trắng trơn, không biết đang chạy hay hỏng".
Đây là **bug UX**, không phải bug kỹ thuật → route sang `3_ux_flow_fixer.md`.

### P19. Người dùng mất dữ liệu khi đóng nhầm
**Triệu chứng:** "gõ instruction xong đóng tab, mất hết".
**Nguyên nhân:** không có dirty-state, không chặn `closeEvent`.
Đây là bug UX mức nghiêm trọng, ưu tiên cao hơn phần lớn bug hiển thị.

### P20. Dialog mở sau lưng cửa sổ chính / mở lệch màn hình
**Nguyên nhân:** dialog không truyền `parent`, hoặc set vị trí bằng toạ độ tuyệt đối.
**Sửa:** luôn truyền parent; căn giữa theo `parent.geometry()`, không theo `screen(0)`.

---

## Cách dùng danh mục này

1. Ánh xạ triệu chứng người dùng → 1-3 mục khả dĩ.
2. Với mỗi mục, chạy đúng bước **Xác minh** — đọc code hoặc tái hiện.
3. Loại trừ cho tới khi còn một nguyên nhân có `file:line` cụ thể.
4. Nếu không mục nào khớp: ghi giả thuyết mới vào `fix_plan.md`, và **bổ sung mục mới vào
   file này** khi đã xác nhận. Danh mục phải lớn dần theo bug thật của sản phẩm.
