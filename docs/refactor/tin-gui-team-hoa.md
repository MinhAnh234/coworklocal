# Tin nhắn gửi Team Hoa — 25/08/2026

*Nam (Team Gamma) soạn. Hai việc, không cần trả lời, chỉ cần đọc trước khi
bắt đầu R07-T03 và R06.*

---

Chào team Hoa,

Có hai thứ trong nhánh `gamma/refactor` ảnh hưởng trực tiếp tới phần các bạn
sắp làm. Gửi trước để khỏi mất thời gian truy lỗi.

## 1. `platform/` đã đổi tên thành `adapters/` — plan.md ghi tên cũ

Plan chỉ đích danh `platform/qt/qt_scheduler_clock.py` (R07-T03, dòng 407 và
lịch 25/08 ở dòng 229). **Đừng tạo thư mục `platform/`.**

Lý do: `platform` là tên một module trong thư viện chuẩn của Python. Tạo thư
mục `platform/` ở gốc repo là nó che mất module chuẩn khi chạy từ chính thư
mục gốc — mà đó là cách toàn bộ script trong `tools/` và `scripts/` đang chạy.
Triệu chứng không hề chỉ về đúng chỗ:

    AttributeError: module 'platform' has no attribute 'system'

Ném ra từ `import keyring`, không liên quan gì tới file bạn vừa tạo.

Tôi đã mắc đúng lỗi này hôm 21/08. Lúc thử thì đứng ở thư mục cha nên không
tái hiện được, tưởng an toàn. Đổi tên thành `adapters/` và thêm
`tests/test_no_stdlib_shadow.py` để lần sau đỏ ngay.

**Việc cần làm**: tạo `adapters/qt/qt_scheduler_clock.py` thay vì
`platform/qt/...`. Thư mục `adapters/qt/` đã có sẵn `__init__.py` trên nhánh
`gamma/refactor`, kéo về là dùng được.

## 2. `AtomicJsonFile` vừa vá một lỗi Windows — lấy bản mới trước khi dựng lên

Plan giao các bạn hai repository ngồi trên `AtomicJsonFile`:

* `infrastructure/persistence/json/task_repository_impl.py` (R07-T01, dòng 403)
* `infrastructure/persistence/json/workspace_repository_impl.py` (R06, dòng 387)

Và tiêu chí nghiệm thu **A** (dòng 244) bắt mọi thao tác ghi tệp phải đi qua nó.

Hôm nay tôi bắt được lỗi thật trong đó:

    PermissionError: [WinError 5] Access is denied
      .dem.json.xxxxxxx.tmp -> dem.json

`os.replace` trên Windows bị từ chối khi Defender hoặc Search Indexer đang giữ
handle lên file vừa tạo — vài chục mili-giây rồi nhả. Đo được: hỏng 1 trong 7
lượt chạy 20 lần ghi, tức **khoảng 1 trên 140 lần lưu**. Người dùng thỉnh
thoảng bấm Lưu là văng lỗi và không tài nào tái hiện để báo.

Đã thêm vòng thử lại (commit `9d6a7be`). Nếu các bạn dựng repository trên bản
trước đó thì lưu task và lưu workspace cũng hỏng với tần suất y hệt — nhân lên
ba nơi ghi file.

**Việc cần làm**: `git pull` nhánh `gamma/refactor` (hoặc chờ nó vào `main`)
trước khi bắt đầu R06/R07-T01.

## Tiện thể

`domain/security/tool_policy.py` là bản đề xuất DTO `ToolPolicyGateway` tôi
viết hộ cho R05 của các bạn — ba trạng thái ALLOW/DENY/ASK, kèm fake và test
contract. Không có gì của Gamma phụ thuộc vào nó, nên các bạn cứ sửa hoặc bỏ
thoải mái, không phải giữ ý.

Nam
