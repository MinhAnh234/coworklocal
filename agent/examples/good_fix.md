# Ví dụ ĐẠT — một vòng xử lý bug UI hoàn chỉnh

> ⚠️ **Kịch bản minh hoạ để dạy format.** Số dòng và defect_id là giả định, không trỏ tới
> một lỗi có thật trong repo. Cái cần học ở đây là *hình dạng* của một vòng xử lý đúng.

---

## Phản ánh gốc từ người dùng

> "Chị Hoa bên BRSE bảo là bật app lên chọn tiếng Nhật thì màn Giám sát vẫn hiện tiếng Việt.
> Mà lạ là màn Workspace thì đổi bình thường. Chắc thiếu dịch."

## ✅ Bước 1 — Triage (rút gọn)

```yaml
defect_id: UI-20260907-03
next_agent: i18n-a11y-fixer
category: i18n-a11y
severity: S2
confidence: high
reproducible: yes
themes_verified: [dark, light]
languages_verified: [vi, ja, en]
```

**Quan sát vs kỳ vọng**

| | |
|---|---|
| Người dùng thấy | Đổi ngôn ngữ sang `ja` ở top bar; Workspace đổi ngay; Monitoring vẫn `vi` |
| Người dùng mong | Mọi màn đổi cùng lúc |
| Suy đoán (chưa xác minh) | "thiếu bản dịch" |

**Điểm mấu chốt Triage tìm ra:** suy đoán của người dùng **sai**. Bản dịch có đủ.
Triage thử thêm một biến thể mà người dùng không nghĩ tới:

| Thứ tự thao tác | Kết quả |
|---|---|
| Mở Monitoring **trước**, rồi đổi sang `ja` | ✅ đổi đúng |
| Đổi sang `ja` **trước**, rồi mới mở Monitoring | ❌ vẫn `vi` |

→ Không phải thiếu key. Là bẫy **P07** (widget dựng lười bỏ lỡ sự kiện đã phát).

**Khoanh vùng:** `presentation/shell/page_registry.py::_ensure_page` — Monitoring dựng lười,
Workspace dựng ngay. Đúng khớp với việc chỉ Monitoring bị.

> Đây là giá trị thật của bước Triage: nếu tin theo chẩn đoán của người dùng, cả pipeline sẽ
> đi thêm bản dịch — sửa xong bug vẫn còn.

## ✅ Bước 4 — i18n-a11y-fixer (rút gọn)

**Nguyên nhân gốc:** `_ensure_page` dựng widget rồi `insertWidget` luôn, không áp lại
ngôn ngữ hiện tại. Widget đăng ký `on_language_changed` trong `__init__`, nhưng callback chạy
lần đầu với ngôn ngữ *lúc đăng ký* — mà lúc đó nó chưa được dựng, nên nó không thể "bỏ lỡ"
gì cả... trừ khi listener của nó được đăng ký **sau** lần phát cuối cùng.

**Đã loại các giả thuyết:**

| Giả thuyết | Cách loại |
|---|---|
| Thiếu key `ja` | `grep -c '"ja"' i18n/monitoring_overview.py` → đủ |
| `MonitoringTab` quên đăng ký listener | Có đăng ký, `ui/monitoring_tab.py:__init__` |
| Do theme, không phải ngôn ngữ | Tái hiện được ở cả dark và light |

**Mức can thiệp đã chọn:** thấp nhất — sửa **một chỗ** ở `_ensure_page`, không đụng
`MonitoringTab`. Sửa ở `_ensure_page` khắc phục luôn cho **cả ba** màn dựng lười
(Dashboard, Schedule, Monitoring), thay vì vá riêng từng màn.

**Đã cân nhắc và loại:** thêm `_retranslate()` vào `MonitoringTab.showEvent` — vá được
Monitoring nhưng Dashboard và Schedule vẫn hỏng. Đó là sửa triệu chứng.

**Blast radius:** cả 3 màn dựng lười. Đã `grep` `_ensure_page` — chỉ được gọi từ `_goto`.

**LOC:** `page_registry.py` 111/400 — an toàn.

**Cách kiểm chứng:**

```python
# tests/ui/test_lazy_page_i18n.py
def test_lazy_page_uses_current_language_when_built_late(qtbot, ctx):
    """Regression: đổi ngôn ngữ trước khi mở màn dựng lười thì nhãn vẫn ngôn ngữ cũ (UI-20260907-03)."""
```

## ✅ Bước 5 — Implementer (rút gọn)

**Test viết trước, xác nhận đỏ:**

```
tests/ui/test_lazy_page_i18n.py::test_lazy_page_uses_current_language_when_built_late FAILED
AssertionError: assert 'Tổng quan' == '概要'
```

**Diff — 4 dòng:**

```diff
--- a/presentation/shell/page_registry.py
+++ b/presentation/shell/page_registry.py
@@
         real = builder()
+        # A lazily-built page misses every language/theme signal emitted before
+        # its first visit, so re-apply the current state right after building.
+        apply_current_language(real)
         placeholder = self._page_widgets[row]
```

**Gate — output thật:**

```
>> Running Gate: [C] Clean Architecture ...        [PASS]  0.8s
>> Running Gate: [A] Secrets Audit ...             [PASS]  1.9s
>> Running Gate: [S] LOC <= 400 ...                [PASS]  0.6s
>> Running Gate: [O] Orphan Modules ...            [PASS]  0.7s
>> Running Gate: [A/N] pytest ...                  [PASS]  74.2s
```

**Kiểm bằng mắt:** đã chạy `run.bat`; thử `vi→ja→en` với cả ba màn dựng lười, dark và light.

## ✅ Bước 6 — Reviewer (rút gọn)

**Kiểm test có thật sự bắt bug** — bước hay bị bỏ nhất:

```bash
git stash push -- presentation/shell/page_registry.py
QT_QPA_PLATFORM=offscreen pytest tests/ui/test_lazy_page_i18n.py -q   # 1 failed  ✅
git stash pop
QT_QPA_PLATFORM=offscreen pytest tests/ui/test_lazy_page_i18n.py -q   # 1 passed  ✅
```

**Verdict: PASS**

**Ghi chú không chặn merge:** cùng cơ chế này cũng nên áp lại *theme* cho màn dựng lười —
diff hiện tại chỉ xử lý ngôn ngữ. Đã mở issue riêng thay vì nhét vào PR này.

---

## Vì sao vòng này ĐẠT

| Tiêu chí | Bằng chứng |
|---|---|
| Triage bác bỏ chẩn đoán sai của người dùng | Thử thêm biến thể thứ tự thao tác |
| Đúng một nguyên nhân gốc, có `file:line` | `_ensure_page` |
| Sửa nguyên nhân, không sửa triệu chứng | Sửa ở chỗ chung, không vá riêng Monitoring |
| Mức can thiệp thấp nhất | 4 dòng, khắc phục cho cả 3 màn |
| Có test, và test được chứng minh là bắt được bug | Revert-and-rerun |
| Gate output thật, không tóm tắt | Dán nguyên |
| Phát hiện out-of-scope được tách ra | Issue riêng cho theme |
