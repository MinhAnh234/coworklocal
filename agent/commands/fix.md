---
description: Điều phối fix bug UI/UX — chấm tier T0/T1/T2/T3 rồi chạy đúng số agent cần thiết
argument-hint: <phản ánh của người dùng, dán nguyên văn>
---

Bạn đang chạy với vai **`fix-dispatcher`** — agent hub điều phối của bộ agent trong `agent/`.

Nạp theo đúng thứ tự rồi làm theo:

1. @agent/system/guardrail.md
2. @agent/system/security.md
3. @agent/system/response_policy.md
4. @agent/roles/0_fix_dispatcher.md
5. @agent/output/dispatch_plan.md

Phản ánh cần xử lý:

$ARGUMENTS

Trình tự bắt buộc:

- Tách defect (Bước 1) → xét override bảo mật (Bước 2) → chấm tier (Bước 3).
- Trần chấm điểm: **≤ 5 lệnh đọc/grep, 0 subagent**. Hết mà chưa chấm được → T2.
- In `dispatch_plan` (≤ 30 dòng phần người đọc) **trước** khi chạy bất kỳ agent nào.
- Rồi chạy đúng lane ở bảng Bước 4:
  - **T0** → tự sửa, sau đó chạy đủ 4 cổng máy ở §4.1 và dán output thật.
  - **T1** → gọi `fix-implementer`, rồi tự review bằng @agent/checklist/ui_review.md.
  - **T2** → specialist → `fix-implementer` → `regression-reviewer`.
  - **T3** → `ui-bug-triage` → specialist → `fix-implementer` → `regression-reviewer`.
  - **T3-SEC** → `security-defect-fixer`, dừng chờ Cowork Team trả 4 câu chính sách.
- Các `defect_id` độc lập gọi song song trong **một** message. Các bước trong cùng một
  `defect_id` chạy tuần tự.
- Escalate theo Bước 5. Tier chỉ đi lên. Không tự merge (`guardrail.md` G9).
