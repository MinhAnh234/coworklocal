# Quyết định của Team Gamma

Team: **Nam** (nhóm trưởng, nhánh N1) · **Hiệp** (N2) · **Lâm** (N3).

Ghi ở đây thay vì chôn trong comment, vì cả ba đều ảnh hưởng ra ngoài phạm vi
một người.

| # | Việc | Trạng thái |
|---|---|---|
| 1 | `provider_conf()` còn trả `api_key` | **Chốt 21/08 — đường A** |
| 2 | Số phận 24 checker UI | **Chốt 21/08 — đường A** |
| 3 | DTO `ToolPolicyGateway` viết hộ Team Hoa | Đã làm, chờ Hoa xác nhận |

---

## Quyết định 1 — `provider_conf()` còn trả `api_key` hay không

### Vì sao phải quyết trước khi code

R02-T05 chuyển API key sang Keyring. Câu hỏi là sau khi chuyển, dict do
`provider_conf()` trả về **còn chứa `api_key` không**.

Có 5 nơi đang đọc trực tiếp — đo trên `main` ngày 21/08:

| Nơi đọc | Thuộc |
|---|---|
| `providers/anthropic.py:26` | **Team Duy** |
| `providers/openai_compat.py:36` | **Team Duy** |
| `core/image_gen.py:50` | Team Duy (routing/model) |
| `core/ext_connectors.py:98` | Team Hoa |
| `ui/ext_connector_dialog.py:87` | Team Gamma |

Ba trong năm nằm ngoài team. Quyết một mình rồi im lặng là làm vỡ code người khác.

### Hai đường

**A. Giữ `api_key` trong dict, `ConfigRepository` tự lấy từ `SecretStore` rồi ghép vào**

- 5 nơi đọc **không phải sửa dòng nào**
- Không cần báo team khác, không cần đồng bộ lịch
- Đổi lại: bí mật vẫn đi lang thang trong dict, dễ lọt vào log hoặc màn hình debug
- CASAN Check 1 vẫn PASS vì nó quét **file trên đĩa**, không quét bộ nhớ

**B. Bỏ `api_key` khỏi dict, ai cần thì gọi `secrets.get(provider_key(name))`**

- Sạch về nguyên tắc: bí mật chỉ xuất hiện đúng chỗ cần
- Đổi lại: **5 nơi phải sửa**, 3 trong đó phải chờ team khác xếp lịch
- Rủi ro: quên một chỗ thì mất API key lúc chạy thật, mà test có fake nên không bắt được

### Đề xuất

**Đường A cho sprint này, đường B ghi vào nợ kỹ thuật.**

Lý do: mục tiêu của cổng CASAN là *không còn secret nằm trên đĩa*, và đường A
đạt được điều đó. Đường B giải quyết thêm chuyện secret trong bộ nhớ — đúng
nhưng không phải việc của 10 ngày này, và nó kéo hai team khác vào một thay đổi
họ không lên kế hoạch.

Nếu chọn B thì **phải báo Team Duy và Team Hoa trong hôm nay**, không phải lúc
đã sửa xong.

> **Nam chốt 21/08: đường A.**
>
> Việc kèm theo: `ConfigRepository` bản thật phải đọc key từ `SecretStore` rồi
> ghép vào dict do `provider_conf()` trả về. Năm nơi đọc không đổi một dòng,
> nên **không cần báo Duy và Hoa**.
>
> Nợ kỹ thuật đã ghi: đường B (bỏ `api_key` khỏi dict) để sau sprint này.

---

## Quyết định 2 — số phận 24 checker UI

### Vấn đề

`tools/check_*.py` là bộ kiểm tra giao diện viết trong 2 tuần vừa rồi, hiện
**24 file**. Chúng bám vào đường dẫn cũ:

| Import | Số chỗ |
|---|---|
| `cowork_local.config` | 34 |
| `cowork_local.app` | 16 |
| `cowork_local.state` | 22 |
| `cowork_local.ui.*` | ~12 |

R08 dời hết những module đó sang `presentation/`. Nghĩa là **cả 24 checker chết
ngay ngày N1 đụng `config.py`** — và đó là lưới an toàn duy nhất cho phần giao
diện, vì `pytest` không kiểm giao diện (90 test hiện tại là logic).

### Ba đường

**A. Ai dời file thì cập nhật checker tương ứng, ngay trong PR đó**

- Giữ được lưới suốt 10 ngày
- Tốn thêm ~15% thời gian mỗi PR
- Rủi ro: người sửa vội có thể nới lỏng phép kiểm cho nó xanh — đã xảy ra một
  lần trong quá trình làm UI, khi một checker được sửa thành *không thể đỏ*

**B. Đóng băng: bỏ khỏi CI, sửa một lượt ngày 31/08**

- Nhanh nhất trong 10 ngày
- Đổi lại: **không có gì canh hồi quy giao diện** suốt cả sprint. Refactor là lúc
  dễ vỡ giao diện nhất
- Rủi ro cuối sprint: sửa 24 file cùng lúc, không ai nhớ cái nào đo gì

**C. Bỏ hẳn**

Không khuyến nghị. Vứt đi hai tuần công sức kiểm chứng, và ba tài liệu refactor
không có gì thay thế cho phần giao diện.

### Đề xuất

**Đường A**, kèm một ràng buộc: PR nào *sửa* checker phải nói rõ trong mô tả
**sửa gì và vì sao** — để việc nới lỏng phép kiểm không lọt qua review.

`tools/check_probes_bite.py` đã có sẵn cơ chế chứng minh checker còn cắn được;
chạy nó sau mỗi đợt sửa là bắt được ngay chuyện đó.

> **Chốt 21/08: đường A** — ai dời file thì cập nhật checker tương ứng ngay
> trong PR đó.
>
> Kèm hai ràng buộc, vì rủi ro của đường A là người sửa vội nới lỏng phép kiểm:
>
> 1. PR nào *sửa* checker phải nói rõ trong mô tả **sửa gì và vì sao**.
> 2. Sửa xong chạy `python tools/check_probes_bite.py` — nó cắm lỗi cố ý vào
>    code rồi kiểm checker có bắt được không. Chính công cụ này đã từng bắt
>    được một checker bị sửa thành *không thể đỏ*.
>
> Không đưa 24 checker vào CI trong sprint này: chúng dựng `MainWindow` thật,
> mỗi lần chạy tốn hàng chục giây và thỉnh thoảng sập lúc Qt dọn dẹp. Chạy tay
> theo phạm vi mình đụng là đủ.

---

## Quyết định 3 — Gamma viết hộ DTO `ToolPolicyGateway` cho Team Hoa

**Đã làm, chờ Hoa xác nhận.** Ngày: 21/08.

### Vì sao làm thay

N3 (Co4E) cần gọi tool nhưng Team Hoa chưa bắt đầu. Ba đường:

| | Hệ quả |
|---|---|
| N3 ngồi đợi Hoa | Mất mấy ngày, trái nguyên tắc "không team nào chặn team nào" |
| N3 tự phỏng đoán | Phỏng đoán của một người, không ai soi, sửa lại chắc chắn |
| **Gamma viết bản đề xuất** | N3 chạy ngay, Hoa có cái cụ thể để duyệt hoặc sửa |

### Ranh giới không lấn

Sơ đồ phân hệ trong `plan.md` giao `domain/security/` cho **Team Gamma**, còn
`application/conversations/tool_policy_gateway.py` cho **Team Hoa**.

Nên chia đúng như vậy:

- **Gamma định nghĩa hình dạng** → `domain/security/tool_policy.py`
- **Hoa cài đặt gateway** → `application/conversations/tool_policy_gateway.py`,
  nối vào `core/mcp_client.py` và tool dựng sẵn

Không đụng file nào của Hoa.

### Đã bám vào code đang chạy, không bịa

| Nguồn | Lấy gì |
|---|---|
| `core/agent_security.py::SecurityVerdict` | `allowed` · `reason` · `layer` |
| `ui/permission_dialog.py` + `chat_panel.py:1312` | trạng thái "hỏi người dùng" |

Khác biệt duy nhất: gộp thành **một câu trả lời ba trạng thái**
(`ALLOW` / `DENY` / `ASK`) thay vì bắt chỗ gọi tự nhớ hỏi hai nơi.

Hai ràng buộc đưa vào có chủ đích:

1. `DENY` và `ASK` **bắt buộc có `reason`** — người dùng cần biết vì sao, và
   `audit_log` cần ghi lại. Thiếu là ném lỗi ngay lúc dựng, không phải lúc chạy.
2. `ASK` **không phải** `allowed` — bẫy dễ mắc nhất là coi ASK như ALLOW rồi tool
   chạy mà chưa ai đồng ý. Có test riêng cho chuyện này.

### Gửi Hoa cái gì

> Bên mình viết trước bản đề xuất `ToolPolicyGateway` ở
> `domain/security/tool_policy.py` vì N3 cần gọi tool mà bên Hoa chưa bắt đầu —
> để N3 khỏi phải tự đoán. Ba kiểu: `ToolCallRequest`, `PolicyDecision`,
> `ToolPolicyGateway`. Phần cài đặt vẫn để bên Hoa ở
> `application/conversations/tool_policy_gateway.py`, bọn mình không đụng.
> Thấy chỗ nào không hợp thì sửa thẳng file đó, đừng tạo kiểu thứ hai. Đổi bây
> giờ còn rẻ vì mới mình N3 dùng.

> Đã gửi Hoa: ☐ — ngày ____   Hoa xác nhận: ☐ đồng ý ☐ có sửa
