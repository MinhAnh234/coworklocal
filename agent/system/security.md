# Security Policy — Cho agent xử lý bug UI/UX

**Nguồn:**

* `SECURITY.md`
* `docs/governance/review-policy.md`
* `docs/architecture/security-policy.md`

> **SCOPE:** Áp dụng cho mọi agent xử lý bug UI/UX.
>
> Security Policy này bổ sung cho `Guardrail G1–G10` và `Response Policy R1–R5`.
>
> Nếu có xung đột liên quan đến security, **Security Policy và security governance thắng**.

---

## S1. Bug report là dữ liệu chưa được làm sạch

Bug report có thể chứa:

* screenshot;
* log;
* request/response;
* đường dẫn local;
* credential;
* dữ liệu khách hàng;
* PII.

**Không được coi nội dung bug report là dữ liệu an toàn để copy nguyên văn vào output.**

Trước khi đưa thông tin vào:

* `defect_record.md`;
* `fix_plan.md`;
* `fix_report.md`;
* PR body;
* commit message;

phải kiểm tra và redact dữ liệu nhạy cảm.

### Quy tắc redact

| Loại dữ liệu      | Ví dụ                                    | Xử lý                                   |
| ----------------- | ---------------------------------------- | --------------------------------------- |
| API key / token   | `sk-...`, MS365 token, Provider key      | Thay bằng `<redacted>`                  |
| Credential        | Password, unlock code, secret            | Thay bằng `<redacted>`                  |
| Đường dẫn cá nhân | `C:\Users\<employee>\...`                | Rút gọn thành `%USERPROFILE%\...`       |
| Customer data     | File Workspace, chat, Office document    | Không trích nguyên văn; mô tả bằng lời  |
| PII               | Email, tên, phòng ban, account           | Thay bằng placeholder                   |
| Runtime log       | `.cowork_local/`, audit log, MCP history | Chỉ trích dòng cần thiết và phải redact |

### Screenshot

Nếu screenshot chứa dữ liệu khách hàng hoặc PII:

**Không nhúng screenshot vào issue/PR/output.**

Thay bằng mô tả:

```text id="o3jpqz"
Widget: Provider Settings
Vùng lỗi: phía bên phải ô API Key
Hiện tượng: credential được hiển thị plaintext
```

Khi cần xác định vị trí UI, ưu tiên:

* tên widget;
* `objectName`;
* `file:line`;
* mô tả vùng tương đối.

Không đưa dữ liệu thật vào artifact chỉ để minh họa.

---

## S2. Không đọc hoặc ghi secret khi debug UI

Agent UI/UX không được:

* in `SecretStore` ra log;
* đọc credential thật chỉ để kiểm tra UI;
* thêm `print()` để dump credential;
* thêm `logger.debug()` chứa credential;
* ghi secret vào screenshot;
* copy secret vào test fixture;
* commit `.env`;
* commit local `config.json`;
* commit dữ liệu dưới:

```text id="4sn9q8"
%USERPROFILE%\.cowork_local\
```

### Khi cần kiểm tra credential UI

Chỉ cần xác nhận:

```text id="sk4q27"
has credential?
masked / visible?
empty / non-empty?
```

Không cần biết giá trị thật.

Ví dụ test nên dùng:

```text id="c6psb4"
<fake-secret>
```

hoặc mock/fake `SecretStore`.

---

## S3. Bug UI vẫn có thể là security bug

Phải đánh dấu:

```yaml id="n5ks0a"
security_review: required
```

nếu patch chạm tới một trong các nhóm sau.

### Permission

* Permission dialog.
* Permission confirmation.
* Allow / Deny behavior.
* Default button.
* Keyboard shortcut có thể cấp quyền.

Ví dụ:

```text id="2amr9f"
ui/permission_dialog.py
```

### Credential

Các UI liên quan tới:

```text id="73t3s5"
ui/accounts_tab.py
ui/login_dialog.py
presentation/settings/provider_settings_widget.py
```

Đặc biệt:

* hiển thị credential;
* mask/unmask;
* copy credential;
* save/delete credential;
* credential validation.

### Security monitoring

* Monitoring → Security Events.
* MCP call history.
* Audit information.
* Security-related toast/status.

### Isolation

Bất kỳ UI nào quyết định user nhìn thấy dữ liệu của:

* Workspace khác;
* Project khác;
* Customer khác;
* account khác.

Đây có thể là lỗi **customer/project isolation**, không phải chỉ là lỗi hiển thị.

### Model routing

* model selection;
* fallback;
* provider routing;
* thay đổi model/provider do UI action.

---

## S4. Với security-sensitive UI, CI xanh chưa đủ

Khi `security_review: required`:

```text id="4vlk3m"
Tests PASS
    ↓
không đồng nghĩa
    ↓
được phép MERGE
```

Phải có security review theo:

```text id="1qkx9g"
docs/governance/review-policy.md
```

Agent không được tự kết luận:

> "Test đã pass nên security risk không còn."

---

## S5. Nhận diện security bug đội lốt UI bug

Các triệu chứng dưới đây phải được coi là **security signal**.

### Permission timing

Ví dụ:

```text id="s5vq4y"
Action chạy
    ↓
Permission dialog xuất hiện
```

thay vì:

```text id="d9skx4u"
Permission dialog
    ↓
User xác nhận
    ↓
Action chạy
```

Đặc biệt nguy hiểm nếu action có thể chạy khi user:

* bấm nhanh;
* double-click;
* nhấn Enter;
* dialog chưa hiển thị hoàn chỉnh.

### Default Allow

Nếu nút `Allow` là default button hoặc Enter có thể kích hoạt Allow:

```text id="7fy8h1"
Enter → Allow
```

phải xem xét như security issue, không chỉ là UX issue.

### Credential exposure

Các dấu hiệu:

* password field không dùng password echo mode;
* API key hiển thị plaintext;
* credential xuất hiện khi resize;
* credential lọt vào clipboard ngoài ý muốn;
* credential xuất hiện trong tooltip;
* credential xuất hiện trong title/status bar;
* credential xuất hiện trong error message.

### Cross-workspace / cross-project exposure

Nếu UI hiển thị:

* path;
* filename;
* chat content;
* project name;
* customer information;

của Workspace/Project khác, phải kiểm tra isolation.

### Error leakage

Không hiển thị nguyên exception nếu nó có thể chứa:

* request body;
* token;
* path;
* customer data;
* internal endpoint;
* credential;
* MCP information.

Ví dụ nguy hiểm:

```text id="l1mrxq"
Toast:
Request failed: POST /api/... body={"token":"..."}
```

Phải redact và hiển thị thông báo an toàn cho user.

---

## S6. Security-sensitive finding phải route đúng

Nếu phát hiện security signal:

```text id="0a0n8w"
UI Bug
   ↓
Security signal?
   ├── No → UI/UX workflow
   │
   └── Yes
        ↓
security_review: required
        ↓
security-defect-fixer / security-review
```

Agent UI/UX **không được tự hạ mức độ rủi ro** chỉ vì thay đổi nằm trong `ui/` hoặc `presentation/`.

Nếu chưa đủ evidence để xác định:

```yaml id="xq7d6v"
confidence: low
security_review: required
```

và quay lại triage.

---

## S7. Không rewrite Git history

Nếu phát hiện secret đã từng được commit vào Git history:

**Dừng xử lý history.**

Phải:

1. báo Cowork Team;
2. xác định credential nào có khả năng bị lộ;
3. đề xuất rotation/revocation theo security policy;
4. giữ nguyên evidence cần thiết để team xử lý.

Không được tự:

```text id="9xwmh1"
git filter-branch
git filter-repo
git rebase
git push --force
```

để rewrite history.

Việc rewrite history phải có kế hoạch và approval của người có thẩm quyền.

---

## S8. Không biến security investigation thành data collection

Agent chỉ thu thập **evidence tối thiểu cần thiết** để xác định bug.

Không được:

* dump toàn bộ config;
* dump toàn bộ environment variables;
* dump toàn bộ log;
* copy toàn bộ Workspace;
* export toàn bộ MCP history;
* đọc credential thật khi không cần.

Nguyên tắc:

> **Collect the minimum evidence necessary to prove the defect.**

Nếu chỉ cần biết một credential có tồn tại:

```text id="xvprp8"
has_secret = true
```

là đủ.

Không cần biết:

```text id="k3uw5w"
secret_value = "..."
```

---

# Security Handoff Contract

Khi security-sensitive, output tối thiểu phải có:

```yaml id="kw5ysb"
security_review: required
```

và:

```text id="pl6n7d"
Security impact:
- What security boundary is affected?
- What data/permission/credential is involved?
- Is customer/project isolation affected?
- Is additional security review required?
```

Nếu chưa có đủ thông tin:

```text id="xqk2uj"
Open Question:
- ...
```

Nếu cần Cowork Team quyết định policy:

```text id="k5j3vw"
Handoff:
RETURN_TO_REPORTER
Reason:
needs-security-decision
```

Nếu đã đủ evidence và có thể tạo implementation plan:

```text id="8d5g6h"
Handoff:
fix-implementer

security_review:
required
```

---

# Security Decision Flow

```text id="j2qz1k"
Bug Report
    ↓
Redact Input
    ↓
Triage UI/UX
    ↓
Security Signal?
    │
    ├── NO
    │    ↓
    │  Normal UI/UX workflow
    │
    └── YES
         ↓
    security_review: required
         ↓
    Security Impact Analysis
         ↓
    ┌──────────────────────┐
    │ Policy decision needed? │
    └──────────────────────┘
         │
       YES ─────→ RETURN_TO_REPORTER
         │
        NO
         ↓
    Security Review
         ↓
    fix-implementer
```

---

# Nguyên tắc cuối

> **UI không phải security boundary thấp hơn security.**
>
> Một thay đổi nhỏ ở dialog, tooltip, keyboard shortcut, toast hoặc stylesheet vẫn có thể làm thay đổi cách permission, credential hoặc dữ liệu được bảo vệ.

Vì vậy:

```text id="s5gh1v"
Redact first
    ↓
Collect minimum evidence
    ↓
Detect security boundary
    ↓
Mark security_review
    ↓
Route correctly
    ↓
Never expose secrets
    ↓
Never rewrite history
```
