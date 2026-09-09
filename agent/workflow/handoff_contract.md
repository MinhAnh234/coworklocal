# Handoff Contract — envelope truyền giữa các agent

Mọi agent kết thúc lượt bằng khối YAML này, đặt **ngay trên** phần nội dung chính.
Đây là phần máy đọc; phần dưới nó là phần người đọc.

```yaml
---
defect_id: UI-2026-0907-01        # UI-<YYYYMMDD>-<số thứ tự trong ngày>
from_agent: ui-bug-triage
next_agent: ui-visual-fixer       # xem bảng giá trị hợp lệ bên dưới
tier: T2                          # T0 | T1 | T2 | T3 | T3-SEC — do fix-dispatcher chấm
category: visual                  # visual | flow | i18n-a11y | security | not-ui
severity: S2                      # S1 | S2 | S3 | S4
confidence: high                  # low | medium | high
reproducible: yes                 # yes | no | intermittent
security_review: not-required     # required | not-required
affected_files:
  - presentation/folder/folder_tab.py:118
  - theme/qss.py:204
themes_verified: [dark, light]    # [] nếu chưa kiểm
languages_verified: [vi]          # [] nếu không liên quan
blocked_on: []                    # danh sách open question CHẶN bước tiếp theo
---
```

## Giá trị hợp lệ của `next_agent`

| Giá trị | Nghĩa |
|---|---|
| `fix-dispatcher` | Escalate về hub: vượt phạm vi tier hiện tại, cần chấm lại |
| `ui-visual-fixer` / `ux-flow-fixer` / `i18n-a11y-fixer` | Route sang specialist UI |
| `security-defect-fixer` | Route sang specialist bảo mật (`category: security`) |
| `fix-implementer` | Plan đã sẵn sàng để hiện thực |
| `regression-reviewer` | Patch đã sẵn sàng để review |
| `HUMAN_REVIEW` | Xong phía agent; chờ Cowork Team |
| `RETURN_TO_REPORTER` | Không phải bug, hoặc thiếu thông tin chặn, hoặc cần quyết định sản phẩm |

## Luật

1. **`defect_id` không đổi** suốt vòng đời một lỗi, kể cả khi quay vòng FAIL.
2. Một defect_record = **một nguyên nhân gốc**. Triage phát hiện hai nguyên nhân → tách
   thành hai `defect_id`.
3. `confidence: low` → `next_agent` chỉ được là `ui-bug-triage` hoặc `RETURN_TO_REPORTER`.
4. `blocked_on` khác rỗng → agent nhận **không** được implement; chỉ được điều tra thêm.
5. `security_review: required` là **cờ dính**: một khi bật, không agent nào được tắt.
   Chỉ Cowork Team gỡ được. `category: security` thì cờ này **luôn** bật.
6. `themes_verified` / `languages_verified` chỉ ghi thứ **thực sự đã kiểm**. Đây là chỗ hay
   bị ghi khống nhất (`guardrail.md` G10).
7. Agent nhận envelope phải kiểm envelope trước khi làm việc. Thiếu trường hoặc mâu thuẫn
   (ví dụ `confidence: low` mà `next_agent: fix-implementer`) → trả về ngay, không xử lý.
8. `category: security` thắng mọi nhóm khác. Một lỗi vừa lệch layout vừa lộ credential thì
   `next_agent: security-defect-fixer`; phần UI tách thành `defect_id` riêng, xử lý sau.
9. `blocked_on` của role 7 có thể chứa câu hỏi **chính sách** (`needs-security-decision`).
   Đó là chờ hợp lệ — người trả lời là Cowork Team, không phải agent khác.
10. **`tier` chỉ đi lên.** Không agent nào được hạ `tier` trong envelope nhận được. Thấy
    việc lớn hơn tier đang mang → đặt `next_agent: fix-dispatcher`, ghi lý do vào
    `blocked_on`, dừng. Hub là chỗ duy nhất được ghi `tier`.
11. `tier: T0` mà `next_agent` khác `HUMAN_REVIEW` là mâu thuẫn: T0 không gọi agent nào.
    `tier: T3-SEC` thì `security_review` **luôn** là `required`.
12. `report_id` (nếu có) gom các `defect_id` tách ra từ **cùng một** phản ánh. Nó chỉ để
    truy vết ngược về người báo lỗi; không dùng nó để gộp PR — một PR vẫn là một
    `defect_id` (`guardrail.md` G8).
