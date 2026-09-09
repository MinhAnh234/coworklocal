# Output Contract — `fix_plan`

Do `ui-visual-fixer` / `ux-flow-fixer` / `i18n-a11y-fixer` sinh ra.
Đây là thứ `fix-implementer` thi hành — mơ hồ chỗ nào thì chỗ đó sẽ bị đoán bừa.

---

```yaml
---
defect_id: UI-<YYYYMMDD>-<NN>
from_agent: <tên specialist>
next_agent: <fix-implementer | RETURN_TO_REPORTER>
root_cause_file: path/to/file.py:123
root_cause_pitfall: P__
confidence: <medium | high>
security_review: <required | not-required>
loc_risk: <none | near-limit | exceeds>
blast_radius: []          # màn/widget khác dùng chung phần bị sửa
---
```

# 1. Nguyên nhân gốc

**Đúng một.** Nêu `file:line`, trích đoạn code, và giải thích *tại sao dòng đó sinh ra
triệu chứng người dùng thấy*.

```python
# path/to/file.py:118
```

**Vì sao đây là nguyên nhân gốc chứ không phải triệu chứng:**

**Các giả thuyết đã loại và lý do loại:**

# 2. Ràng buộc thiết kế đã kiểm

- [ ] Không mâu thuẫn với ràng buộc có chủ ý ở `theme_tokens.md` §4.
- [ ] Nếu phản ánh của người dùng thực ra là thiết kế đúng: nêu ở đây và chuyển
      `next_agent: RETURN_TO_REPORTER`.

# 3. Phương án sửa

| # | File | Thay đổi | Vì sao chọn mức này |
|---|---|---|---|
| 1 | | | |

**Mức can thiệp đã chọn** (theo thang ưu tiên của role):

**Các phương án đã cân nhắc và bị loại:**

# 4. Diff dự kiến

```diff
```

# 5. Ảnh hưởng lan toả

| Chỗ khác dùng chung | Đã kiểm | Kết luận |
|---|---|---|
| | | |

Lệnh đã chạy để tìm:

```bash
grep -rn "<...>" --include=*.py .
```

# 6. Ràng buộc kiến trúc

| | |
|---|---|
| Tầng bị sửa | presentation / ui / theme / i18n |
| Có chạm `application/` hoặc `domain/` không | không — hoặc **lý do bắt buộc phải chạm** |
| LOC file sau khi sửa | `___ / 400` |
| Cần tách module không | có/không — nếu có, tách thế nào |
| File mới có được import ngay không (Gate O) | |

# 7. i18n

| Key | en | ja | vi | File |
|---|---|---|---|---|
| | | | | `i18n/____.py` |

Không thêm chuỗi mới thì ghi `N/A`.

# 8. Cách kiểm chứng

## 8.1 Test tự động

```python
# tests/ui/test_____.py
def test_...(qtbot, ctx):
    """Regression: <triệu chứng> (defect UI-...)."""
```

Test này phải **đỏ** trước khi sửa. Nếu không viết được test tự động: nêu lý do cụ thể.

## 8.2 Kiểm bằng mắt

| Trục | Giá trị phải thử | Kết quả mong đợi |
|---|---|---|
| Theme | dark, light | |
| Ngôn ngữ | | |
| Kích thước cửa sổ | nhỏ nhất, maximize | |
| Thứ tự thao tác | có kịch bản P07 | |

# 9. Rủi ro

| Rủi ro | Khả năng | Giảm thiểu |
|---|---|---|

# 10. Out of scope

Cố ý **không** làm trong lần này, và vì sao.
