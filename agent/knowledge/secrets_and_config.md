# Secret & Config — Nơi credential được phép nằm

> Knowledge module dành cho `security-defect-fixer`.

## Nguồn chính

* `infrastructure/secrets/secret_store.py`
* `infrastructure/secrets/keyring_adapter.py`
* `infrastructure/config/schema_migration.py`
* `config.py`
* `SECURITY.md`

**Lưu ý:** Module này chỉ dành cho vấn đề security/config.
Ba module UI `theme_tokens`, `i18n_rules`, `screen_map` **không xử lý credential**.

---

# 1. Credential được phép lưu ở đâu?

Ưu tiên từ **an toàn nhất → kém an toàn hơn**:

| Bậc | Nơi lưu                                | Dùng cho                             | API / cách truy cập          |
| --- | -------------------------------------- | ------------------------------------ | ---------------------------- |
| 1   | **OS Keyring** thông qua `SecretStore` | API key, token, mật khẩu thật        | `secrets.set/get/has/delete` |
| 2   | **Environment variable**               | Giá trị do admin đặt khi triển khai  | `_apply_env_overrides`       |
| 3   | **`config.json`**                      | Chỉ dành cho config **không bí mật** | `ctx.config.<group>`         |
| 4   | **Hằng số trong source code**          | ❌ Không được chứa credential         | —                            |

### Rule quan trọng

Credential **không được hardcode trong source code**.

Nếu credential nằm trong code:

1. Gate A có thể phát hiện.
2. Credential có thể đã đi vào Git history.
3. Xóa ở commit hiện tại **không có nghĩa là credential đã biến mất khỏi Git history**.

---

# 2. `SecretStore` — interface để làm việc với secret

`SecretStore` là **interface (Protocol)**, không phải một hàm tiện ích.

File:

```python
# infrastructure/secrets/secret_store.py

@runtime_checkable
class SecretStore(Protocol):

    def get(self, key: str) -> str | None:
        ...

    def set(self, key: str, value: str) -> None:
        ...

    def delete(self, key: str) -> None:
        ...

    def has(self, key: str) -> bool:
        ...


def provider_key(name: str) -> str:
    return f"provider:{name}"
```

## Ý nghĩa của từng API

| API              | Ý nghĩa                                                        |
| ---------------- | -------------------------------------------------------------- |
| `get()`          | Lấy secret; thiếu key thì trả `None`, không được làm app crash |
| `set()`          | Lưu secret                                                     |
| `delete()`       | Xóa secret; không có key thì không cần báo lỗi                 |
| `has()`          | Kiểm tra secret có tồn tại hay không mà **không đọc giá trị**  |
| `provider_key()` | Chuẩn hóa cách đặt key cho provider                            |

## Vì sao dùng `Protocol`?

Bản thật sử dụng OS Keyring:

* có thể chậm;
* có thể phát sinh exception;
* môi trường CI có thể không có keyring backend.

Do đó test **không được truy cập keyring thật của máy**.

Thay vào đó, test sử dụng `FakeSecretStore`.

### Rule khi thêm secret mới

**Không tự tạo cách đặt key mới.**

Ví dụ đã có:

```python
provider_key(name)
```

thì hãy dùng nó.

Nếu loại secret mới chưa có quy ước:

```python
def xxx_key(...):
    ...
```

Hãy tạo một helper `*_key()` cạnh các helper hiện có.

**Không rải string literal của key khắp source code.**

---

## Settings: kiểm tra secret bằng `has()`

Nếu UI chỉ cần biết:

> "API key đã được cấu hình chưa?"

thì dùng:

```python
secrets.has(key)
```

**Không dùng:**

```python
secrets.get(key)
```

Chỉ để hiển thị dấu ✓.

Lý do: không cần đọc secret thật ra khỏi kho chỉ để kiểm tra trạng thái.

---

## Khi `KeyringAdapter.available == False`

Có thể xảy ra khi:

* Linux không có keyring backend;
* CI;
* môi trường triển khai không hỗ trợ OS Keyring.

App phải có **fallback phù hợp** và không được crash chỉ vì keyring không khả dụng.

Bản thật là `KeyringAdapter`.

Service:

```python
SERVICE = "cowork-local"
```

Có property:

```python
available
```

---

# 3. Schema migration — thay đổi cấu trúc config an toàn

File:

```text
infrastructure/config/schema_migration.py
```

Các thông tin chính:

```python
CURRENT_VERSION = 2
ASSUMED_VERSION = 1

STEPS = {
    1: _v1_to_v2,
}
```

Ý nghĩa:

* `CURRENT_VERSION`: version config hiện tại.
* `ASSUMED_VERSION`: nếu file không có `schema_version` thì coi là version 1.
* `STEPS`: mỗi entry nâng đúng **một version**.

Ví dụ:

```text
v1 → v2 → v3
```

Không được thiết kế kiểu:

```text
v1 → v3
```

---

## 4 luật migration bắt buộc

### 4.1 Backup trước khi migration

Trước khi nâng schema:

```text
backup()
```

tạo file dạng:

```text
config.json.v<timestamp>.bak
```

Mục đích:

* người dùng vẫn có bản backup;
* app cũ có thể còn đọc được config cũ;
* migration lỗi vẫn có đường quay lại.

---

### 4.2 Chỉ nâng version, không hạ version

Nếu file config mới hơn version mà app hiện tại hiểu:

```text
file version > CURRENT_VERSION
```

thì:

1. log warning;
2. giữ nguyên config;
3. **không cố đoán cách downgrade**.

Không được tự ý biến config mới thành config cũ.

---

### 4.3 Mỗi migration là một function riêng

Ví dụ:

```python
STEPS = {
    1: _v1_to_v2,
}
```

Mỗi function xử lý đúng:

```text
v(n) → v(n+1)
```

Không viết logic kiểu:

```text
"Nếu thấy key office thì chắc đây là config cũ"
```

Version phải được xác định bằng `schema_version`.

---

### 4.4 Migration không nâng được version thì phải dừng

Nếu migration không thành công:

* không lặp vô hạn;
* không tự đoán;
* không tiếp tục nâng version giả;
* phải giữ trạng thái an toàn và báo lỗi/warning phù hợp.

---

# 4. Tiền lệ quan trọng: `_v1_to_v2`

Đây là migration quan trọng cần **đọc trước khi thiết kế migration credential mới**.

Migration này từng xử lý việc:

```text
api_key
```

từ config file → `SecretStore`.

Mẫu chính:

```python
def _v1_to_v2(data, secrets):

    if secrets is None or not getattr(secrets, "available", True):
        log.info(
            "bỏ qua v1→v2: máy này chưa có kho bí mật dùng được"
        )
        return data

    ...

    secrets.set(provider_key(name), key)
    conf["api_key"] = ""
    out["schema_version"] = 2
```

## Có 2 bài học quan trọng

### 4.1 Không có Keyring thì không chuyển

Nếu Keyring không dùng được:

```text
KHÔNG MIGRATE
```

Giữ nguyên version cũ.

Ví dụ:

```text
v1 + không có keyring
        ↓
giữ nguyên v1
        ↓
lần sau có keyring
        ↓
migrate v1 → v2
```

Lý do:

> Mất credential của người dùng còn tệ hơn việc trì hoãn migration.

---

### 4.2 Bỏ qua placeholder

Ví dụ:

```python
api_key == "ollama"
```

chỉ là placeholder.

Không nên đưa placeholder vào Keyring.

Nếu không, Keyring sẽ chứa những secret giả không có giá trị.

---

# 5. ⚠️ Bẫy `.get(key, fallback)` với config đã deep-merge

Đây là một trong những bẫy quan trọng nhất của config.

Trong:

```text
config.py:265
```

có:

```python
_deep_merge(base, override)
```

Sau đó:

```text
infrastructure/config/json_config_repository.py:90
```

config được merge với:

```text
DEFAULT_CONFIG
```

Vì vậy config đưa tới UI **đã có sẵn các default key**.

Ví dụ `DEFAULT_CONFIG` có:

```python
"sandbox_pw": ""
```

thì:

```python
sec.get(
    "sandbox_pw",
    "<literal đã bị gỡ>"
)
```

sẽ trả:

```text
""
```

chứ **không trả fallback**.

## Vì sao?

`dict.get(key, fallback)` chỉ dùng `fallback` khi `key` **không tồn tại**.

Nhưng ở đây key đã được thêm bởi `DEFAULT_CONFIG`.

---

## Hậu quả

Code như:

```python
sec.get("sandbox_pw", "<safe fallback>")
```

có thể trông giống như có default an toàn.

Nhưng thực tế:

```text
DEFAULT_CONFIG
      ↓
sandbox_pw = ""
      ↓
deep_merge()
      ↓
sandbox_pw luôn tồn tại
      ↓
.get(..., fallback) không bao giờ dùng fallback
```

Vì vậy fallback đó thực tế là **dead code**.

---

## ⚠️ Nguy hiểm hơn: chuỗi rỗng

Nếu code sau đó dùng:

```python
entered == stored
```

thì:

```text
entered = ""
stored  = ""
```

sẽ trở thành:

```text
True
```

Tức là **input rỗng có thể mở khóa**.

Đây là security bug S1.

---

## Rule

Khi đọc credential từ config:

**Không dựa vào fallback của `.get()` để tạo security default.**

Thay vào đó:

1. lấy giá trị thật;
2. kiểm tra `None`/rỗng một cách rõ ràng;
3. chỉ cho phép tiếp tục nếu credential hợp lệ.

---

# 6. Environment variable override

File:

```text
config.py::_apply_env_overrides
```

Các biến hiện tại:

| Environment variable       | Config được ghi vào         |
| -------------------------- | --------------------------- |
| `COWORK_SANDBOX_PASSWORD`  | `agent_security.sandbox_pw` |
| `COWORK_MS365_UNLOCK_CODE` | `ms365.unlock_code`         |
| `COWORK_TEAMS_WEBHOOK`     | `teams.webhook_url`         |
| `COWORK_ACTIVE_PROVIDER`   | `active_provider`           |
| `COWORK_CA_BUNDLE`         | `tls_ca_bundle`             |

Environment override chạy **sau deep-merge**.

Do đó thứ tự ưu tiên là:

```text
DEFAULT_CONFIG
      ↓
config.json
      ↓
environment variable
```

Environment variable có giá trị ưu tiên cao nhất.

### Khi thêm credential mới

Hãy xem xét:

> Có cần hỗ trợ environment variable để admin có thể cấu hình khi deploy hay không?

Không phải secret nào cũng bắt buộc phải có env override.

---

# 7. Sinh credential/token — dùng lại implementation có sẵn

File:

```text
core/accounts.py:89
```

Hiện có:

```python
_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 12

def generate_code(existing_codes=None) -> str:
    ...
```

Alphabet bỏ các ký tự dễ nhìn nhầm:

```text
I L O 0 1
```

Mục đích là người dùng có thể đọc và nhập lại code dễ hơn.

## Rule

Dùng:

```python
secrets
```

**Không dùng:**

```python
random
```

Nếu cần access code cho người dùng:

```python
generate_code()
```

Không tự viết thêm một generator khác.

Nếu token là token nội bộ và không cần người đọc:

```python
secrets.token_urlsafe(32)
```

---

# 8. Gate A và Git history

Chạy:

```bash
python scripts/audit_security.py
```

Gate này quét:

* `.py`;
* config files;
* các vị trí có khả năng chứa secret.

Hiện repo có một số phát hiện **đã tồn tại từ trước** trong:

```text
tests/test_project_context_*.py
```

Không được nhầm chúng với lỗi do patch hiện tại tạo ra.

---

## Nếu credential đã xuất hiện trong Git history

Nếu phát hiện secret thật trong Git history:

### 1. Dừng phân phối

Không tiếp tục phát hành artifact có nguy cơ chứa credential.

### 2. Báo Cowork Team

Đây là vấn đề cần xử lý ở cấp team.

### 3. Không tự rewrite history

Không tự:

```text
git filter
git rebase
force-push
```

nếu chưa có kế hoạch phối hợp rõ ràng.

### 4. Rotate credential

Credential đã lộ phải được xem là có khả năng bị compromise và cần rotate khi phù hợp.

---

## Rule quan trọng

Xóa secret khỏi source code hôm nay:

```text
KHÔNG XÓA SECRET KHỎI GIT HISTORY
```

Vì vậy `fix_plan` phải ghi rõ nếu credential từng xuất hiện trong history.

---

# 9. Quyết định phải hỏi Cowork Team

Thay đổi liên quan credential không được tự quyết chỉ vì:

```text
CI xanh
```

Theo:

```text
docs/governance/review-policy.md
```

credential-related change cần được security review phù hợp.

## 4 câu hỏi agent phải đưa cho người quyết định

### 1. Đây là loại nào?

* khóa chống bấm nhầm;
* hay credential/security mechanism thật?

Điều này quyết định mức độ bảo vệ cần thiết.

### 2. Lưu gì trong Keyring?

* plaintext;
* hay hash để kể cả admin cũng không đọc được?

Agent chỉ đề xuất, không tự quyết.

### 3. Người dùng hiện tại xử lý thế nào?

* giữ credential cũ;
* migrate;
* hay bắt buộc reset?

Đây là quyết định về backward compatibility và UX.

### 4. Credential được tạo ra hiển thị thế nào?

Cần xác định:

* có hiển thị cho người dùng không;
* hiển thị ở đâu;
* hiển thị trong bao lâu;
* người dùng được xem lại bao nhiêu lần.

---

# 10. So sánh credential — hai lỗi cần nhớ

Nguồn tham chiếu:

```text
SEC-20260907-01
```

Đây là defect thật đã từng xảy ra trong repo.

Có **hai bẫy liên tiếp**.

---

## 10.1 Chặn chuỗi rỗng trước khi so sánh

Credential default thường là:

```python
""
```

Do cơ chế deep-merge ở §5, giá trị rỗng này có thể đi thẳng tới code kiểm tra.

Nếu viết:

```python
entered == stored
```

thì:

```text
entered = ""
stored = ""
```

→ `True`

Đây là bypass bằng input rỗng.

---

## Mẫu đúng đã có trong repo

Trong:

```text
infrastructure/config/json_config_repository.py
```

có:

```python
if (code or "") and code == self.ms365.get("unlock_code", ""):
```

Phần quan trọng là:

```python
(code or "")
```

kết hợp với:

```python
and
```

Nó đảm bảo code rỗng bị chặn **trước khi thực hiện phép so sánh**.

### Rule

Credential rỗng:

```text
MUST FAIL
```

Không được coi:

```text
"" == ""
```

là thành công.

---

# 11. ⚠️ `secrets.compare_digest()` và Unicode

Một lỗi khác rất dễ mắc phải:

> Thấy `==` không an toàn về timing → đổi ngay sang `compare_digest()`.

Hướng đi đúng, nhưng phải kiểm tra **miền input**.

Ví dụ:

```python
secrets.compare_digest("mật khẩu", "mật khẩu")
```

có thể gây:

```text
TypeError
```

với `str` chứa ký tự non-ASCII.

Điều này đặc biệt quan trọng với Cowork Local vì app:

* mặc định dùng tiếng Việt;
* phục vụ khách Nhật;
* credential có thể chứa Unicode.

Mật khẩu có dấu **không phải edge case**.

---

## Cách đúng: chuyển sang bytes

Dùng:

```python
return secrets.compare_digest(
    entered.encode("utf-8"),
    stored.encode("utf-8"),
)
```

Như vậy phép so sánh hoạt động trên UTF-8 bytes.

---

# 12. Bài học tổng quát: API an toàn hơn có thể có input hẹp hơn

Đây là rule quan trọng cần nhớ khi review security.

Một API mới có thể:

```text
an toàn hơn
```

nhưng đồng thời:

```text
nhận ít loại input hơn
```

Ví dụ:

```text
== 
↓
compare_digest()
```

`compare_digest()` tốt hơn về timing attack, nhưng có thêm ràng buộc về kiểu dữ liệu/input.

---

## Trước khi thay một API bằng phiên bản "an toàn hơn", phải kiểm tra

### 1. API mới nhận kiểu dữ liệu nào?

Ví dụ:

* `str`;
* `bytes`;
* ASCII;
* Unicode;
* `None`;
* empty string.

### 2. Input thật của app có nằm trong miền đó không?

Phải kiểm tra:

* EN;
* VI;
* JA;
* Unicode;
* độ dài;
* `None`;
* empty;
* boundary values.

### 3. Input ngoài miền sẽ xảy ra chuyện gì?

API mới có thể:

```text
return False
```

hoặc:

```text
raise TypeError
```

Không được giả định behavior.

### 4. Có regression test cho input đó chưa?

Đặc biệt phải test các input trước đây API cũ chấp nhận nhưng API mới có thể không chấp nhận.

---

# 13. Checklist nhanh cho `security-defect-fixer`

Trước khi tạo `fix_plan`, kiểm tra:

* [ ] Credential có đang nằm trong source code không?
* [ ] Credential có xuất hiện trong Git history không?
* [ ] Secret có nên nằm trong `SecretStore` không?
* [ ] Có thể dùng `provider_key()` hoặc helper `*_key()` hiện có không?
* [ ] UI có dùng `has()` thay vì `get()` để kiểm tra trạng thái không?
* [ ] Có xử lý `KeyringAdapter.available == False` không?
* [ ] Migration có backup trước không?
* [ ] Migration có chỉ nâng version không?
* [ ] Mỗi migration có một step rõ ràng không?
* [ ] Migration có dừng khi không thể nâng version không?
* [ ] Có đang dùng `.get(key, fallback)` sai trên config đã deep-merge không?
* [ ] Credential rỗng có bị chặn trước khi compare không?
* [ ] Nếu dùng `compare_digest()`, input có thể là Unicode không?
* [ ] Có chuyển credential sang UTF-8 bytes khi cần không?
* [ ] Có test `None`, empty, Unicode, long và boundary input không?
* [ ] Có cần environment variable override không?
* [ ] Có quyết định product/security nào cần Cowork Team không?
* [ ] `security_review: required` đã được ghi trong `fix_plan` chưa?

---

# 14. Nguyên tắc cuối cùng

Khi xử lý credential, luôn đi theo chuỗi:

```text
Defect
  ↓
Xác định credential thật hay chỉ là UI guard
  ↓
Xác định nơi credential đang được lưu
  ↓
Trace 4 bước:
generate → store → read → compare
  ↓
Kiểm tra config deep-merge / DEFAULT_CONFIG
  ↓
Kiểm tra empty-input bypass
  ↓
Kiểm tra miền input của API bảo mật
  ↓
Kiểm tra migration + backward compatibility
  ↓
Kiểm tra Git history
  ↓
Xác định quyết định cần Cowork Team
  ↓
Tạo fix_plan
  ↓
security_review: required
```

**Không tự thiết kế policy bảo mật thay cho Cowork Team.**

Agent chịu trách nhiệm:

```text
phát hiện
→ phân tích
→ chứng minh root cause
→ đề xuất phương án
→ ghi rõ rủi ro
→ route đúng
```

Agent **không tự quyết** những vấn đề thuộc policy, product hoặc security governance.
