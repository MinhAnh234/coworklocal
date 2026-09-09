# Output Contract — `defect_record`

Do `ui-bug-triage` sinh ra. Giữ **đúng** thứ tự và tên mục. Không có dữ liệu thì ghi
`unknown` hoặc `N/A` kèm lý do — **không xoá mục**.

---

```yaml
---
defect_id: UI-<YYYYMMDD>-<NN>
from_agent: ui-bug-triage
next_agent: <ui-visual-fixer | ux-flow-fixer | i18n-a11y-fixer | RETURN_TO_REPORTER>
category: <visual | flow | i18n-a11y | not-ui>
severity: <S1 | S2 | S3 | S4>
confidence: <low | medium | high>
reproducible: <yes | no | intermittent>
security_review: <required | not-required>
affected_files: []
themes_verified: []
languages_verified: []
blocked_on: []
---
```

# 1. Tóm tắt

Một câu: cái gì hỏng, ở màn nào, với ai.

# 2. Quan sát vs kỳ vọng

| | |
|---|---|
| **Người dùng thấy** | |
| **Người dùng mong** | |
| **Người dùng suy đoán (chưa xác minh)** | |

# 3. Môi trường

| Trường | Giá trị |
|---|---|
| Phiên bản app / commit | |
| OS + độ phân giải + mức scale | |
| Theme lúc xảy ra | |
| Ngôn ngữ lúc xảy ra | |
| Project / workspace liên quan | (mô tả, **không** nêu tên khách hàng) |

# 4. Các bước tái hiện

1.
2.
3.

**Tỉ lệ tái hiện:** _luôn / thỉnh thoảng (n/m lần) / không_

# 5. Ma trận biến thể đã thử

| Biến thể | Đã thử | Kết quả |
|---|---|---|
| Theme dark | | |
| Theme light | | |
| Ngôn ngữ vi / ja / en | | |
| Cửa sổ nhỏ nhất / maximize | | |
| Đổi theme/ngôn ngữ **trước** rồi mới mở màn (bẫy P07) | | |

# 6. Khoanh vùng

| | |
|---|---|
| Nav row | Dashboard / Schedule / Workspace / Monitoring |
| Sub-tab / dialog | |
| `manifest.json` slug | |
| Widget dựng tại | `file.py:line` |
| Control (`controls.json`) | `var`, `type`, `object_name` |
| Đã kiểm cả `ui/` và `presentation/` | có / không |

# 7. Giả thuyết nguyên nhân gốc

| # | Giả thuyết | Mã pitfall | Đã xác minh thế nào | Còn / loại |
|---|---|---|---|---|
| 1 | | P__ | | |
| 2 | | P__ | | |

**Kết luận:** _(một nguyên nhân + `file:line`, hoặc "chưa xác định" nếu `confidence: low`)_

# 8. Tác động

- Ai bị ảnh hưởng:
- Chặn công việc gì:
- Có đường vòng không:
- Lý do chọn mức `severity` này:

# 9. Cân nhắc bảo mật

- Chạm permission / credential / monitoring bảo mật / isolation / routing? _có / không_
- Dữ liệu người dùng gửi lên đã redact? _có / không — mô tả đã bỏ gì_
- Có dấu hiệu ở `system/security.md` S4 không?

# 10. Open Questions (tối đa 3)

| # | Câu hỏi | Mặc định nếu không trả lời | Có chặn không |
|---|---|---|---|
| 1 | | | có / không |

# 11. Out of scope

Vấn đề khác phát hiện được, **không** sửa trong lần này — đề xuất issue riêng.
