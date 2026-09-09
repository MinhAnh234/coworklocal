# Checklist sẵn sàng tạo PR

Checklist này được sử dụng bởi:

* `fix-implementer` — kiểm tra ở bước 9.
* `regression-reviewer` — kiểm tra ở bước 8.

Tham chiếu:

* `.gitea/PULL_REQUEST_TEMPLATE.md`
* `docs/governance/definition-of-done.md`

---

## A. Kiểm tra chất lượng

* [ ] Chạy `python scripts/run_quality_gate.py`.
  Cả **5 quality gate đều phải PASS** và phải ghi lại **output thực tế**.

* [ ] **Gate C:** Các thư mục `domain/` và `application/` không được import:
  - `PySide6`
  - `PyQt`
  - `ui`
  - `app`

* [ ] **Gate A:** Không tạo thêm secret hoặc thông tin nhạy cảm dạng plaintext.

* [ ] **Gate S:** Không có file nào vượt quá **400 dòng code (LOC)**.

* [ ] **Gate O:** Không có file/module mới bị bỏ quên.
  File Python mới phải được sử dụng/import trong cùng thay đổi.

* [ ] **Gate A/N:** Test phải PASS.
  Nếu đã có test FAIL từ trước thì phải ghi rõ đó là **lỗi có sẵn**, không phải lỗi do bản sửa này gây ra.

---

## B. Kiểm tra bản sửa

* [ ] Có **regression test** cho lỗi đã sửa.

* [ ] Regression test phải chứng minh được:
  - **Trước khi sửa:** test FAIL.
  - **Sau khi sửa:** test PASS.

* [ ] Test chạy được ở chế độ headless:
  `QT_QPA_PLATFORM=offscreen`

* [ ] Nếu thay đổi liên quan đến UI:
  - Đã kiểm tra giao diện ở **Dark Mode**.
  - Đã kiểm tra giao diện ở **Light Mode**.
  - Nếu chưa thể kiểm tra bằng mắt, phải ghi rõ:
  **"Chưa kiểm chứng bằng mắt"** và nêu lý do.

* [ ] Nếu thay đổi liên quan đến ngôn ngữ:
  đã kiểm tra các ngôn ngữ bị ảnh hưởng.

---

## C. Kiểm tra phạm vi thay đổi và Git

* [ ] Một PR chỉ giải quyết **một thay đổi logic chính**.
  Không đưa refactor không liên quan vào cùng PR.

* [ ] Không tự ý format hoặc thay đổi indent của toàn bộ file.
  Diff phải rõ ràng và dễ review.

* [ ] Làm việc trên **branch riêng**.
  Không commit trực tiếp vào `main`.

* [ ] Commit message phải nêu:
  - Nguyên nhân gốc của lỗi.
  - Vị trí code liên quan (`file:line`).
  - Issue liên quan.

* [ ] Không commit các file/dữ liệu sau:
  - `.env`
  - `config.json` local
  - `.cowork_local/`
  - `.venv/`

---

## D. Kiểm tra bảo mật

* [ ] Không có các thông tin sau trong code, test fixture, commit message hoặc PR body:
  - Secret
  - PII/thông tin cá nhân
  - Đường dẫn chứa thông tin cá nhân trên máy local

* [ ] Nếu có ảnh chụp màn hình trong PR:
  đã che (redact) toàn bộ thông tin nhạy cảm trước khi đính kèm.

* [ ] Nếu thay đổi liên quan đến một trong các nội dung sau:

  ```
  - Permission/quyền truy cập
  - Credential/thông tin xác thực
  - MCP write/exec
  - Sandbox
  - Network
  - TLS
  - Isolation
  - Model routing
  - Xóa dữ liệu

  thì phải:

  1. Đặt `security-review: required`.
  2. Ghi rõ trong PR rằng:
     **"CI xanh không có nghĩa là có thể merge ngay."**
  3. Chờ security review theo quy trình trước khi merge.
  ```

---

## E. Kiểm tra nội dung PR

* [ ] **Summary** phải giải thích **tại sao cần sửa**, không chỉ mô tả đã sửa cái gì.

* [ ] Đã chọn **Change Type** phù hợp.

* [ ] **Scope** phải ghi rõ:
  - Những gì đã thay đổi.
  - Những gì **cố ý không thay đổi**.

* [ ] **Validation** phải ghi:
  - Lệnh đã chạy.
  - Kết quả thực tế/output.

* [ ] **Security Impact** phải được điền.
  Nếu không ảnh hưởng bảo mật, ghi rõ **"Không có"**.

* [ ] Đã chọn **Compatibility** phù hợp.

* [ ] **Reviewer Notes** phải chỉ ra những phần reviewer cần kiểm tra kỹ nhất.

* [ ] Đã cập nhật tài liệu nếu cần:
  - `docs/`
  - Ảnh màn hình trong `docs/screens/`

---

## F. Giới hạn quyền của Agent

* [ ] Agent **không được tự merge PR**.

* [ ] Agent **không được tự đóng issue**.

* [ ] Nếu đây là đóng góp từ **FSG AI Core**, cần hiểu rằng trạng thái **"Done"** chỉ được xác nhận khi PR đã thực sự được merge vào Cowork Local và có đầy đủ:

  ```
  - Core issue reference
  - PR reference
  - Evidence
  - Reviewer phía Cowork
  - Merge reference
  ```
