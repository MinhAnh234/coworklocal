# Output Contract — `dispatch_plan`

Do `fix-dispatcher` sinh ra, trước khi bất kỳ agent nào khác chạy.
Đây là thứ quyết định **effort** của cả lượt xử lý, nên nó phải chứng minh được lựa chọn
của mình — nhưng phải ngắn. Trần: **30 dòng** cho phần người đọc.

---

```yaml
---
report_id: RPT-<YYYYMMDD>-<NN>     # một phản ánh của người dùng = một report_id
defects:
  - defect_id: UI-<YYYYMMDD>-<NN>
    tier: <T0 | T1 | T2 | T3 | T3-SEC>
    lane: <DIRECT | SOLO | PAIR | FULL | FULL-SEC>
    category: <visual | flow | i18n-a11y | security | not-ui>
    severity: <S1 | S2 | S3 | S4>
    confidence: <low | medium | high>
    reproducible: <yes | no | intermittent>
    security_review: <required | not-required>
    entry_agent: <fix-implementer | ui-visual-fixer | ux-flow-fixer | i18n-a11y-fixer | security-defect-fixer | ui-bug-triage | SELF | RETURN_TO_REPORTER>
    affected_files: [path/to/file.py:123]
    tier_evidence: "<dòng nào của roles/0_fix_dispatcher.md Bước 3 đã trúng>"
    budget_calls: <số lần gọi agent dự kiến>
execution:
  parallel: [[UI-...-01, UI-...-02]]   # các defect_id độc lập, chạy cùng lúc
  sequential: [UI-...-03]              # phụ thuộc, hoặc T3 cần triage trước
blocked_on: []
---
```

# 1. Phản ánh gốc

Nguyên văn của người báo lỗi, **đã redact** (`system/security.md`). Không diễn giải lại.

# 2. Tách defect

| defect_id | Triệu chứng người dùng thấy | Category | Tier |
|---|---|---|---|
| | | | |

Một dòng = một nguyên nhân gốc. Chỉ có một defect thì bảng có một dòng — không xoá bảng.

# 3. Bằng chứng chấm tier

Mỗi defect **một dòng**, trích đúng tiêu chí đã trúng. Không được viết "trông đơn giản".

| defect_id | Tier | Trúng tiêu chí | Lệnh đã dùng để xác nhận |
|---|---|---|---|
| | T0 | loại 1 (số đo hiển thị), 0 disqualifier | `check_loc.py`, `grep -rn` blast radius |
| | T2 | "chạm QSS/token dùng chung" | `grep -rn "<objectName>"` |

Với **T0** bắt buộc có cột lệnh — Gate S và blast radius phải đo, không được ước lượng.

# 4. Kế hoạch chạy

```text
UI-...-01  T0  DIRECT   → hub sửa luôn, cổng máy §4.1
UI-...-02  T2  PAIR     → ui-visual-fixer → fix-implementer → regression-reviewer
UI-...-03  T3  FULL     → ui-bug-triage → ... (chờ triage mới biết specialist nào)
```

Ngân sách tổng: `___` lần gọi agent (bảng §4 của role 0 cho phép `___`).

# 5. Điều đã cố ý KHÔNG làm

- Không gọi `ui-bug-triage` cho defect nào? Vì sao được phép bỏ (phản ánh đã tự chỉ ra
  màn hình + triệu chứng cụ thể).
- Không gọi `regression-reviewer` cho defect nào? Chỉ hợp lệ ở T0/T1 — nêu rõ cổng nào
  thay thế.

# 6. Open question

Tối đa 3, mỗi câu kèm phương án mặc định nếu người dùng không trả lời
(`response_policy.md` R3). Câu hỏi **chặn** thì đưa vào `blocked_on`.
