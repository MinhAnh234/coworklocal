# Output Contract — `fix_report`

Do `fix-implementer` sinh ra sau khi đã áp bản vá.
Mục tiêu duy nhất: **trung thực** (`guardrail.md` G10). Reviewer sẽ chạy lại mọi thứ.

---

```yaml
---
defect_id: UI-<YYYYMMDD>-<NN>
from_agent: fix-implementer
next_agent: regression-reviewer
branch: fix/ui-<slug>
commits: []
gate_result: <all-pass | partial | fail>
tests_added: []
visual_check: <done | not-done>
security_review: <required | not-required>
---
```

# 1. Đã làm gì

| # | File | Thay đổi | Khớp mục nào trong fix_plan |
|---|---|---|---|
| 1 | | | §3.1 |

# 2. Diff

```bash
git diff main...HEAD --stat
```

```
```

# 3. Test regression

| File test | Tên test | Đỏ trước khi sửa | Xanh sau khi sửa |
|---|---|---|---|
| | | ✅ / ❌ | ✅ / ❌ |

Bằng chứng "đỏ trước":

```
```

Bằng chứng "xanh sau":

```
```

Nếu chưa chứng minh được "đỏ trước": **nói rõ**, đừng bỏ trống.

# 4. Kết quả CASAN gate

```bash
python scripts/run_quality_gate.py
```

Dán **output thật**, không tóm tắt:

```
```

| Cổng | Kết quả | Ghi chú |
|---|---|---|
| C — Clean Architecture | | |
| A — Secrets | | |
| S — LOC ≤ 400 | | LOC file lớn nhất: `___/400` |
| O — Orphan module | | |
| A/N — pytest | | |

## Test vốn đã đỏ TỪ TRƯỚC bản vá này

| Test | Lý do đỏ | Có liên quan bản vá không |
|---|---|---|

# 5. Kiểm chứng bằng mắt

| Trục | Đã thử | Kết quả |
|---|---|---|
| dark | | |
| light | | |
| vi / ja / en | | |
| cửa sổ nhỏ nhất / maximize | | |
| kịch bản P07 | | |

Chưa chạy được app → ghi thẳng **"chưa kiểm chứng bằng mắt"** kèm lý do. Không suy đoán
kết quả.

# 6. Lệch so với fix_plan

| Chỗ lệch | Vì sao |
|---|---|

Không lệch thì ghi "không có".

# 7. Chưa làm được

| Việc | Vì sao | Đề xuất |
|---|---|---|

# 8. Out of scope — phát hiện thêm khi sửa

Vấn đề khác nhìn thấy nhưng **không** sửa (G1, G8). Đề xuất mở issue riêng.

# 9. Bảo mật

- Có secret/PII lọt vào code, test fixture, commit message không? _đã kiểm — có/không_
- Cờ `security_review` còn nguyên như plan? _có/không_
