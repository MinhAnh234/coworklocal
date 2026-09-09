# Checklist review bản vá UX (Flow)

Checklist này được sử dụng bởi:

* `ux-flow-fixer` — kiểm tra ở bước 8.
* `regression-reviewer` — kiểm tra trong quá trình review bản vá.

Mục tiêu: đảm bảo người dùng luôn biết **hệ thống đang làm gì, chuyện gì xảy ra và cần làm gì tiếp theo**, đồng thời không bị mất dữ liệu.

---

## A. Kiểm tra 4 trạng thái chính

Đối với mỗi màn hình có dữ liệu hoặc thao tác chạy bất đồng bộ, phải kiểm tra đủ 4 trạng thái:

### 1. Trạng thái Rỗng (Empty)

* [ ] Khi chưa có dữ liệu, màn hình phải hiển thị thông báo có ý nghĩa.

* [ ] Thông báo phải cho người dùng biết **cần làm gì tiếp theo**.

* [ ] Không để màn hình trắng khiến người dùng không biết chuyện gì đang xảy ra.

### 2. Trạng thái Đang tải (Loading)

* [ ] Có dấu hiệu rõ ràng cho biết hệ thống đang xử lý, ví dụ loading indicator.

* [ ] Các nút có thể gây chạy lại cùng một thao tác được vô hiệu hóa trong lúc đang xử lý.

* [ ] Bấm liên tục hoặc bấm đúp không được tạo ra nhiều request/thao tác giống nhau.

### 3. Trạng thái Lỗi (Error)

* [ ] Thông báo lỗi phải cho biết:
  - **Chuyện gì đã xảy ra.**
  - **Người dùng cần làm gì tiếp theo.**

* [ ] Có cách để người dùng **thử lại** khi phù hợp.

* [ ] Không hiển thị nguyên exception, stack trace hoặc thông tin kỹ thuật khó hiểu cho người dùng.

### 4. Trạng thái Thành công (Success)

* [ ] Sau khi thao tác thành công, phải có thông báo/xác nhận rõ ràng.

* [ ] Với thao tác khó hoặc không thể hoàn tác, phải có cơ chế **Undo** nếu phù hợp.

---

## B. Kiểm tra an toàn dữ liệu

* [ ] Các ô nhập nội dung dài, ví dụ:
  - Instruction
  - Composer
  - Node property
  - AI Edit

  ```
  không được mất nội dung khi:

  - Chuyển tab.
  - Đóng/mở dialog.
  - Đổi project.
  ```

* [ ] Có cơ chế xác định **dirty-state** khi dữ liệu đã thay đổi nhưng chưa lưu.

* [ ] `closeEvent` phải cảnh báo hoặc chặn việc đóng màn hình khi vẫn còn thay đổi chưa lưu.

* [ ] Các thao tác có thể làm mất dữ liệu phải có bước xác nhận, ví dụ:
  - Xóa project.
  - Xóa task.
  - Ghi đè file.

* [ ] Nội dung xác nhận phải nói rõ **dữ liệu nào sẽ bị mất**.

  ```
  Không dùng thông báo quá chung chung như:

  `"Bạn có chắc không?"`
  ```

* [ ] Nút thực hiện thao tác phá hủy dữ liệu:
  - Không được đặt làm **default button**.
  - Không được thực hiện khi người dùng chỉ nhấn `Enter`.

---

## C. Kiểm tra phản hồi theo thời gian

Phản hồi của UI phải phù hợp với thời gian xử lý:

* [ ] **100ms – 1s:**
  Có thể thay đổi con trỏ hoặc vô hiệu hóa nút để người dùng biết thao tác đã được nhận.

* [ ] **1s – 10s:**
  Hiển thị chỉ báo tiến trình rõ ràng.

* [ ] **Trên 10s:**
  - Có chỉ báo tiến trình.
  - Người dùng có thể **hủy thao tác** khi phù hợp.
  - Không khóa toàn bộ UI nếu không cần thiết.

* [ ] Các tác vụ xử lý nặng không được chạy trực tiếp trên GUI thread.
  Phải chuyển phần xử lý nặng sang service trong `application/`.

* [ ] Một thao tác không được chạy hai lần khi người dùng bấm liên tục hoặc bấm đúp.

* [ ] Kiểm tra các `connect()` có bị đăng ký nhiều lần hay không, đặc biệt với lỗi **P10**.

---

## D. Kiểm tra khả năng khám phá chức năng

Người dùng phải dễ dàng biết **nút này làm gì và tìm chức năng ở đâu**.

* [ ] Tất cả các nút chỉ có icon (`icon-only`) đều có tooltip.

  ```
  Đặc biệt kiểm tra:
  - Nav rail khi thu gọn.
  - Toolbar Co4E.
  - Top bar.
  ```

* [ ] Nút đang bị vô hiệu hóa phải cho người dùng biết **tại sao không thể bấm**.

  ```
  Ví dụ sử dụng key:

  `app.nav.needs_project`
  ```

* [ ] Chức năng chính không được chỉ nằm trong menu chuột phải nếu không có cách truy cập khác.

* [ ] Thứ tự các control trên màn hình phải phù hợp với **thứ tự người dùng thực hiện công việc**.

---

## E. Kiểm tra tính nhất quán

* [ ] Một hành động phải sử dụng **cùng một thuật ngữ** trên toàn bộ ứng dụng.

  ```
  Ví dụ:

  Nếu dùng `"Lưu"` ở một màn hình thì không nên dùng `"Cập nhật"` ở màn hình khác cho cùng một hành động.
  ```

* [ ] Vị trí của nút chính và nút phụ phải nhất quán với các dialog khác.

* [ ] Chuỗi text mới phải sử dụng `tr()`.

* [ ] Chuỗi mới phải có bản dịch đầy đủ cho:

  ```
  - `en`
  - `ja`
  - `vi`
  ```

* [ ] Không hardcode text mới trực tiếp trong UI code nếu text đó cần hỗ trợ đa ngôn ngữ.

---

## F. Kiểm tra phạm vi thay đổi

* [ ] Bản vá sử dụng **cách can thiệp nhỏ nhất có thể**.

  ```
  Ưu tiên:

  **Bổ sung thông tin → cải thiện feedback → điều chỉnh control → thay đổi flow**

  Không thay đổi cả luồng khi chỉ cần bổ sung thông tin.
  ```

* [ ] Nếu cần thay đổi flow của người dùng, thay đổi đó phải được ghi rõ là:

  ```
  **ĐỀ XUẤT**
  ```

* [ ] Agent không tự quyết định thay đổi product/UX quan trọng.

* [ ] Các thay đổi flow cần được **Cowork Team xem xét và phê duyệt**.

* [ ] Có regression test kiểm tra:
  - Signal.
  - State.
  - Chuyển trạng thái.
  - Hành vi của user flow liên quan.

* [ ] Regression test chạy được ở chế độ headless:

  ```
  `QT_QPA_PLATFORM=offscreen`
  ```

---

## Kết luận

Bản vá UX chỉ nên được đánh giá là đạt khi:

1. Người dùng biết rõ trạng thái hiện tại của hệ thống.
2. Không có nguy cơ mất dữ liệu ngoài ý muốn.
3. UI phản hồi phù hợp với thời gian xử lý.
4. Chức năng dễ tìm và dễ hiểu.
5. Cách gọi tên và cách bố trí control nhất quán.
6. Thay đổi flow lớn đã được đánh dấu để Cowork Team phê duyệt.
7. Có regression test chứng minh flow vẫn hoạt động đúng.
