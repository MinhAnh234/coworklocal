# Checklist review bản vá UI (Visual)

Checklist này được sử dụng bởi:

* `ui-visual-fixer` — kiểm tra ở bước 7.
* `regression-reviewer` — kiểm tra ở bước 5.

Mục tiêu: đảm bảo bản vá UI sửa đúng nguyên nhân, không phá theme, layout, icon hoặc vòng đời của giao diện.

---

## A. Kiểm tra đúng file

* [ ] Đã tìm kiếm trong **cả `ui/` và `presentation/`** để xác định file thực sự được ứng dụng sử dụng khi chạy.

* [ ] Đã kiểm tra xem widget có file/bản triển khai trùng tên ở thư mục còn lại hay không.

* [ ] Nếu có nhiều file cùng chức năng, đã xác định rõ **file nào thực sự được import và chạy**.

---

## B. Kiểm tra màu sắc và Theme

* [ ] Không thêm mã màu trực tiếp như `#rrggbb` hoặc tên màu như `"red"` bên ngoài thư mục `theme/`.

* [ ] Không thêm `setStyleSheet()` trực tiếp vào widget.
  Style phải được quản lý thông qua:

  ```
  `objectName` → `theme/qss.py`
  ```

* [ ] Nếu thêm token màu mới, token đó phải được khai báo cho **cả `DARK` và `LIGHT`**.

* [ ] Khi đặt chữ trên nền màu đặc, dùng `accent_solid`.
  Không dùng `accent` cho trường hợp này.

* [ ] Dùng đúng loại màu nền theo mục đích:

  ```
  - `bg` — nền chính.
  - `surface` — bề mặt thông thường.
  - `surface_raised` — bề mặt nổi.
  - `overlay` — lớp phủ.
  - `sunken` — khu vực chìm.
  ```

* [ ] Contrast của chữ đạt tối thiểu **4.5:1** đối với:
  - Body text.
  - Chữ trên nút có nền đặc.
  - Cả Dark Mode và Light Mode.

* [ ] Không thêm:
  - Gradient.
  - Glow.

  ```
  Đây là các kiểu không phù hợp với design constraint hiện tại.
  ```

* [ ] `Nav rail` vẫn **tối hơn khu vực nội dung**.
  Đây là thiết kế có chủ ý, không tự ý làm sáng lên.

* [ ] Không khôi phục các giá trị màu cũ theo VS Code nếu các giá trị hiện tại đã được điều chỉnh để đạt WCAG AA.

* [ ] Nếu thay đổi `_TEMPLATE`:
  đã đánh giá và ghi rõ **phạm vi ảnh hưởng trên toàn ứng dụng** vì `_TEMPLATE` có thể ảnh hưởng nhiều màn hình.

---

## C. Kiểm tra Layout và kích thước

* [ ] Không thêm mới:

  ```
  - `setFixedWidth()`
  - `setFixedHeight()`
  - `setFixedSize()`

  để che hoặc né lỗi layout.
  ```

* [ ] `stretch factor` và `size policy` được thiết lập rõ ràng khi cần.

* [ ] Nếu sử dụng `QScrollArea`, phải có:

  ```
  `setWidgetResizable(True)`
  ```

* [ ] Kiểm tra margin và spacing của các layout lồng nhau.
  Không được để chúng cộng dồn khiến UI bị lệch hoặc quá rộng.

* [ ] UI vẫn hiển thị đúng ở:
  - Kích thước cửa sổ nhỏ nhất.
  - Cửa sổ maximize.

* [ ] Nếu bản vá liên quan đến kích thước, phải kiểm tra thêm ở:
  - Scale 125%.
  - Scale 150%.

---

## D. Kiểm tra Icon và Custom Painting

* [ ] Icon phải được lấy thông qua:

  ```
  `ui/icons.py::icon`

  Không tự load file icon trực tiếp.
  ```

* [ ] Trong `paintEvent()`, màu sắc phải lấy từ:

  ```
  `current_palette()`

  Không đọc lại màu trực tiếp từ config.
  ```

* [ ] Trong các vòng lặp hoặc thao tác cập nhật UI, dùng:

  ```
  `update()`

  Không dùng `repaint()` nếu không thực sự cần thiết.
  ```

* [ ] `QPainter` được kết thúc đúng cách bằng `end()` khi sử dụng thủ công.

* [ ] Nền của khu vực custom painting được xử lý/xóa đúng cách, không để lại hình ảnh hoặc pixel cũ.

---

## E. Kiểm tra vòng đời UI

* [ ] UI vẫn hoạt động đúng nếu người dùng:

  ```
  1. Đổi theme trước.
  2. Sau đó mới mở màn hình được tạo theo kiểu lazy.

  Đặc biệt kiểm tra lỗi **P07**.
  ```

* [ ] Nếu dùng `setProperty()` để thay đổi style động:
  phải gọi `unpolish()` và `polish()` khi cần để QSS được áp dụng lại.

* [ ] Không gọi `connect()` nhiều lần trong một hàm có thể được gọi nhiều lần.

* [ ] Không tạo signal/slot bị kết nối lặp, gây ra:
  - Event chạy nhiều lần.
  - UI cập nhật nhiều lần.
  - Memory leak hoặc hành vi bất thường.

---

## F. Kiểm tra bằng chứng

* [ ] Đã đối chiếu với screenshot trong:

  ```
  `docs/screens/<slug>-dark.png`

  và

  `docs/screens/<slug>-light.png`
  ```

* [ ] Nếu bản vá làm thay đổi giao diện, đã xác định screenshot nào cần cập nhật.

* [ ] Nếu cần cập nhật screenshot trong `docs/screens/`, phải ghi rõ trong phạm vi thay đổi.

* [ ] Có regression test cho lỗi đã sửa.

* [ ] Regression test chạy được ở chế độ headless:

  ```
  `QT_QPA_PLATFORM=offscreen`
  ```

* [ ] Regression test chứng minh được:

  ```
  **Trước khi sửa → FAIL**

  **Sau khi sửa → PASS**
  ```

---

## Kết luận

Chỉ đánh giá bản vá là **PASS** khi:

1. Sửa đúng file thực sự chạy.
2. Không phá theme hoặc layout hiện có.
3. Không dùng workaround để che lỗi.
4. Không tạo regression.
5. Có regression test phù hợp.
6. Có đủ bằng chứng kiểm chứng.
7. Các vấn đề liên quan đến security hoặc product decision đã được route đúng agent/người phụ trách.
