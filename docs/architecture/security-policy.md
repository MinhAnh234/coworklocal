# Mô hình chính sách an toàn — CoworkLocal

R09-T01 · Team Gamma · viết 22/08/2026

Tài liệu này mô tả **hệ thống đang chạy**, không phải hệ thống mong muốn. Mọi
khẳng định đều chỉ tới file và dòng cụ thể để đối chiếu được.

---

## 1. Câu hỏi quan trọng nhất: đây có phải rào chắn an ninh không

**Không.** `core/agent_security.py` nói thẳng ngay ở đầu file:

> *"this is a business productivity tool, not a hard security boundary"*

Điều đó quyết định mọi thứ còn lại. Cụ thể: **mọi tầng dùng AI đều mở khi
hỏng** (`allowed=True` khi không gọi được validator, `core/agent_security.py:150`).
Mạng chập chờn hay gateway trục trặc thì agent vẫn chạy, không bị khoá cứng.

Đánh đổi có chủ đích: chọn *dùng được* thay vì *chặn tuyệt đối*. Ai đọc tài
liệu này để đánh giá rủi ro cần hiểu đúng điều đó — đây là lớp giảm tai nạn,
không phải lớp chống kẻ tấn công có chủ đích.

---

## 2. Hai loại quy tắc, đừng lẫn

| | Quy tắc xác định | Quy tắc do AI phán |
|---|---|---|
| Cách hoạt động | So khớp mẫu cố định | Hỏi một model |
| Kết quả | Luôn giống nhau | Có thể khác nhau giữa hai lần |
| Khi hỏng | Vẫn chạy | **Mở** (cho qua) |
| Tắt được không | Không — luôn bật | Có, từng tầng một |
| Ở đâu | Bộ phân loại mẫu chặn + sandbox | 3 tầng validate |

Câu ở `core/agent_security.py:250` nói rõ ranh giới:

> *"always-on block-pattern classifier + sandbox still apply regardless"*

Nghĩa là **tắt hết ba tầng AI thì vẫn còn hai lớp xác định**. Đây là điểm dễ
hiểu nhầm nhất khi đọc màn Cài đặt: mấy công tắc ở đó **chỉ tắt phần AI**.

---

## 3. Ba tầng AI

Bật/tắt độc lập trong `agent_security` của `config.json`.

| Tầng | Kiểm cái gì | Khoá cấu hình | Khi nào chạy |
|---|---|---|---|
| Prompt | Yêu cầu của chính người dùng | `validate_prompt` | Trước khi agent làm gì |
| Attachment | Văn bản trích ra từ tệp đính kèm | `validate_attachments` | Trước khi vào ngữ cảnh model |
| Command | `run_command` / `install_package` | `validate_commands` | Trước khi thực thi |

Cả ba đọc chung một bộ luật: file cục bộ `core/security_rules.py` cộng thêm
tài liệu quản trị viên đặt trên OneDrive (nếu có cấu hình). Riêng agent Code
dùng bộ luật khác — `RULEforCode.md` thay vì `RULEBASE.md`.

Công tắc tổng `agent_security.enabled` tắt cả ba.

---

## 4. Chuyện gì xảy ra khi bị chặn

Theo đúng thứ tự trong `core/agent_security.py:266-273`:

1. Hiện thông báo trong khung chat — người dùng thấy ngay, kèm lý do
2. Ghi `audit_log.record("security_block", …)` — vào nhật ký kiểm toán
3. `notify_admin(...)` — gửi email quản trị viên
4. Ném `SecurityBlocked` — dừng lượt chạy

Ba bước đầu **không được phép ném lỗi**. `audit_log.record()` có ghi rõ trong
docstring: *"never raises — audit logging must never break a chat turn"*. Ghi
nhật ký hỏng không được kéo theo cả phiên làm việc.

---

## 5. Hỏi người dùng: trạng thái thứ ba

Ngoài cho/chặn còn một trạng thái nữa mà hệ thống hiện tại **có nhưng chưa gọi
tên**: hỏi người dùng.

`ui/chat_panel.py:1312` kiểm `ctx.project_confirm_commands()` rồi bật
`PermissionDialog`. Đó là một quyết định chính sách thật, nhưng nằm rải ở tầng
giao diện chứ không phải một kết quả chính thức.

`domain/security/tool_policy.py` (đề xuất, chờ Team Hoa xác nhận) gộp lại
thành ba trạng thái:

| | Nghĩa |
|---|---|
| `ALLOW` | Chạy |
| `DENY` | Không chạy, có lý do |
| `ASK` | Hỏi người dùng đã |

**`ASK` không phải là `allowed`.** Coi ASK như ALLOW nghĩa là tool chạy trước
khi có ai đồng ý — bẫy dễ mắc nhất, đã có test riêng chặn.

Cổng chính sách **không tự bật hộp thoại**. Nó chỉ trả lời; hỏi ai và hỏi thế
nào là việc của tầng giao diện. Nhờ vậy Co4E chạy nền mới dùng chung cổng được
với Cowork chạy tương tác — Co4E không hỏi được thì đổi `ASK` thành `DENY`.

---

## 6. Bí mật

Từ 21/08 (R02-T05), API key **không còn nằm trong `config.json`**:

* Lưu trong kho của hệ điều hành qua `KeyringAdapter` — Windows Credential
  Manager, macOS Keychain, Linux Secret Service
* `provider_conf()` đọc từ kho rồi ghép vào dict trả về, nên chỗ gọi không
  đổi (đường A, `GammaTeam_decisions.md`)
* File cũ tự chuyển ở lần mở đầu tiên, có sao lưu trước khi chuyển

Máy không có kho bí mật (Linux headless, CI) thì **không chuyển** — thà để
khoá trong file còn hơn xoá đi rồi người dùng mất khoá.

Kiểm bằng `python scripts/audit_security.py`, chạy tự động trong CI.

---

## 7. Sandbox

`core/sandbox_manager.py` chạy lệnh trong môi trường hạn chế. Luôn bật, không
tắt được, không phụ thuộc công tắc AI nào.

Năng lực khác nhau theo hệ điều hành — ma trận đầy đủ sẽ nằm ở
`infrastructure/sandbox/sandbox_capabilities.py` (R09-T06, Hiệp phụ trách).
Chỗ này cập nhật khi task đó xong.

---

## 8. Những chỗ đã biết là yếu

Ghi ra để người sau khỏi tưởng đã kín:

1. **Mở khi hỏng.** Gateway chết là ba tầng AI cho qua hết. Có chủ đích, nhưng
   nghĩa là không chống được kẻ tấn công biết cách làm validator ngừng trả lời.
2. **Bí mật vẫn đi trong bộ nhớ.** Đường A ghép khoá vào dict `provider_conf()`
   trả về, nên khoá vẫn có thể lọt vào log gỡ lỗi hay ảnh chụp màn hình. Đường
   B (bỏ hẳn khỏi dict) đã ghi vào nợ kỹ thuật.
3. **Bộ luật lấy từ OneDrive không ký số.** Ai sửa được tài liệu đó là sửa được
   luật.
4. **`ASK` chưa được nối vào Co4E.** Co4E chạy nền, chưa có đường hỏi người
   dùng — hiện phải chọn giữa cho qua hết hoặc chặn hết.

---

## Đối chiếu nhanh

| Nội dung | Nguồn |
|---|---|
| Ba tầng AI, mở khi hỏng | `core/agent_security.py:1-25` |
| Phân loại mẫu + sandbox luôn bật | `core/agent_security.py:250` |
| Thứ tự khi bị chặn | `core/agent_security.py:266-273` |
| Nhật ký không được ném lỗi | `core/audit_log.py:46` |
| Hỏi người dùng | `ui/chat_panel.py:1312` |
| Ba trạng thái chính sách | `domain/security/tool_policy.py` |
| Bí mật | `infrastructure/secrets/keyring_adapter.py` |
