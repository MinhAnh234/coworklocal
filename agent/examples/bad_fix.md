# Ví dụ KHÔNG ĐẠT — các kiểu "sửa" phải bị FAIL

> ⚠️ **Kịch bản minh hoạ.** Mỗi mục là một anti-pattern có thật hay gặp khi vá bug UI, được
> dựng lại trên cùng defect với `good_fix.md` (`UI-20260907-03`: đổi sang tiếng Nhật trước
> khi mở màn Monitoring thì nhãn vẫn tiếng Việt).

---

## ❌ 1. Tin thẳng chẩn đoán của người dùng

> Người dùng: *"chắc thiếu bản dịch"* → agent đi thêm entry vào `i18n/monitoring_overview.py`.

**Vì sao sai:** bản dịch đã có đủ. Bug nằm ở vòng đời widget. Sau bản vá, key bị trùng, và
người dùng vẫn thấy tiếng Việt.

**Vi phạm:** `guardrail.md` G1 (không tự bịa), Triage bước 2 (tách triệu chứng khỏi chẩn đoán).

**Dấu hiệu nhận ra ngay:** `defect_record` phần "Người dùng suy đoán" bị dùng làm phần
"Nguyên nhân gốc".

---

## ❌ 2. Vá riêng một màn thay vì sửa chỗ chung

```diff
+    def showEvent(self, e):
+        self._retranslate()
+        super().showEvent(e)
```
_(thêm vào `ui/monitoring_tab.py`)_

**Vì sao sai:** Dashboard và Schedule cũng dựng lười, cũng hỏng y hệt. Bug sẽ được báo lại
sau hai tuần với màn khác. Ngoài ra `showEvent` chạy **mỗi lần** hiện màn, không chỉ lần đầu —
thêm một lần `_retranslate()` thừa cho mọi lần chuyển tab.

**Vi phạm:** Reviewer bước 2 — "sửa ở widget con thay vì chỗ phát sinh".

---

## ❌ 3. Hardcode màu để "cho nhanh"

```diff
-        self.badge.setObjectName("statusBadge")
+        self.badge.setStyleSheet("background: #1f6fb2; color: #ffffff;")
```

**Vì sao sai:** ba lỗi trong hai dòng — hex ngoài `theme/`; `setStyleSheet` cục bộ đè QSS
ứng dụng; và màu này chỉ đúng ở theme dark, sang light là chữ trắng trên nền sáng.

**Vi phạm:** `guardrail.md` G4, `theme_tokens.md` §1, `ui_review.md` mục B.

**Đúng ra phải làm:** giữ `objectName`, style trong `theme/qss.py`, dùng `accent_solid` cho
chữ trên nền đặc.

---

## ❌ 4. `setFixedWidth` để "cho khỏi tràn"

```diff
-        self.tab_label.setMinimumWidth(120)
+        self.tab_label.setFixedWidth(180)   # đủ cho tiếng Nhật
```

**Vì sao sai:** ghim một kích thước cho **một** ngôn ngữ ở **một** mức DPI. Tiếng Việt dài
hơn sẽ tràn; ở scale 150% sẽ tràn; ở cửa sổ hẹp sẽ chiếm chỗ vô lý.

**Vi phạm:** P02, `ui_review.md` mục C.

---

## ❌ 5. `QTimer.singleShot` để "đợi cho nó xong"

```diff
+        QTimer.singleShot(200, self._retranslate)
```

**Vì sao sai:** race condition vẫn nguyên, chỉ khó tái hiện hơn — nên lần sau nó sẽ được báo
là "thỉnh thoảng bị". Máy chậm hơn thì 200ms không đủ. Đây là làm cho bug **khó sửa hơn**.

**Vi phạm:** Reviewer bước 2 — che triệu chứng.

---

## ❌ 6. Test viết cho có

```python
def test_monitoring_tab_builds(qtbot, ctx):
    tab = MonitoringTab(ctx)
    assert tab is not None
```

**Vì sao sai:** test này **xanh cả trước lẫn sau** bản vá. Nó không bắt được gì.

**Cách reviewer phát hiện:** revert code, giữ test, chạy lại — vẫn xanh → FAIL
(Reviewer bước 4).

---

## ❌ 7. Ghi khống kết quả kiểm chứng

```yaml
themes_verified: [dark, light]
languages_verified: [vi, ja, en]
visual_check: done
```

...trong khi môi trường không chạy được GUI.

**Vì sao sai:** đây là lỗi nặng nhất trong cả danh sách. Reviewer và Cowork Team ra quyết
định dựa trên các trường này. Ghi khống làm hỏng toàn bộ giá trị của pipeline.

**Vi phạm:** `guardrail.md` G10, `handoff_contract.md` luật 6.

**Đúng ra phải ghi:**

```yaml
themes_verified: []
visual_check: not-done   # môi trường CI headless, không dựng được cửa sổ thật
```

---

## ❌ 8. Tiện tay dọn dẹp

```
 12 files changed, 486 insertions(+), 391 deletions(-)
```

Trong đó: 4 dòng sửa bug, phần còn lại là đổi f-string, sắp lại import, đổi tên biến "cho dễ đọc".

**Vì sao sai:** reviewer không còn nhìn ra 4 dòng thật sự quan trọng. Nếu PR gây regression,
không bisect được. Vi phạm "một PR một thay đổi logic".

**Vi phạm:** `guardrail.md` G8, `definition-of-done.md`.

---

## ❌ 9. Bỏ qua ràng buộc thiết kế có chủ ý

> Người dùng: *"menu bên trái tối quá, làm sáng lên bằng phần còn lại đi"* → agent đổi token
> nền nav rail.

**Vì sao sai:** nav rail **tối hơn** vùng nội dung là silhouette VS Code có chủ ý, ghi rõ
trong docstring `theme/__init__.py`. Đây là phản hồi thiết kế, không phải bug.

**Đúng ra phải làm:** `next_agent: RETURN_TO_REPORTER`, giải thích kèm dẫn chứng, và nếu thấy
phản hồi có lý thì chuyển thành đề xuất thiết kế cho Cowork Team — họ sở hữu UI/UX
(`docs/governance/ownership.md`).

---

## ❌ 10. Tự merge

Agent chạy `git push` rồi merge PR vì "gate đã xanh hết".

**Vì sao sai:** quyết định merge thuộc Cowork Team. Với thay đổi chạm permission/credential/
routing, **CI xanh không đủ để merge** (`docs/governance/review-policy.md`).

**Vi phạm:** `guardrail.md` G9.

---

## ❌ 11. Thay bằng API "an toàn hơn" mà không kiểm miền đầu vào

> ⚠️ **Đây là ca CÓ THẬT**, không phải giả định. Xảy ra ở `SEC-20260907-01`, ngày
> 2026-09-07, và **lọt qua vòng review đầu tiên**.

Bản vá đổi phép so mật khẩu sang phiên bản timing-safe:

```diff
-        if pw == self._sandbox_pw:
+        if secrets.compare_digest(pw, self._sandbox_pw):
```

Trông đúng. Timing-safe thật. Nhưng:

```python
>>> secrets.compare_digest("mật khẩu", "mật khẩu")
TypeError: comparing strings with non-ASCII characters is not supported
```

**Vì sao sai:** `compare_digest` an toàn hơn `==` về timing, nhưng **miền đầu vào hẹp hơn** —
chỉ nhận ASCII-`str` hoặc bytes. Cowork Local mặc định tiếng Việt và phục vụ khách Nhật.
Người dùng gõ một chữ có dấu vào ô mật khẩu là exception thoát ra khỏi Qt slot.

**Vì sao nó lọt review:** mọi test đều dùng mật khẩu ASCII (`K7MNP2QRSTVW`). Test xanh hết.
Chỉ khi reviewer **tự đọc diff và nghi ngờ** mới lộ ra — không checklist nào bắt được.

**Đúng ra phải làm:**

```python
return secrets.compare_digest(entered.encode("utf-8"), stored.encode("utf-8"))
```

**Bài học đã đưa vào thư viện:** `knowledge/secrets_and_config.md` §9.3 và
`roles/6_regression_reviewer.md` Bước 2.1 — bốn câu bắt buộc hỏi trước mọi lần thay một
phép toán bằng "phiên bản chuẩn hơn".

---

## ❌ 12. Test rỗng ruột — xanh vì chẳng kiểm gì

Cũng từ `SEC-20260907-01`. Test quét toàn repo tìm credential hardcode:

```python
_SCANNED_DIRS = ("ui", "presentation", "core")

def test_khong_con_fallback_credential_trong_ma_nguon():
    offenders = [...]
    assert not offenders
```

**Ba lỗi trong một bài test:**

1. **Quét thiếu.** Sai sót gốc của commit `3827552` là sửa `config.py` mà quên `ui/` — lỗi
   đi xuyên thư mục. Vậy mà phép quét lại bỏ `config.py`, `infrastructure/`, `application/`.
2. **Xanh khi quét rỗng.** Đổi tên thư mục là duyệt được 0 file, `offenders` rỗng, test xanh
   mãi mãi. Cần lưới an toàn: `assert seen > 200`.
3. **Regex quá rộng.** Bản đầu bắt cả `it.get("key", "?")` của Jira — mã issue, không phải
   credential. False positive làm người ta bỏ qua test.

Kiểu thứ hai còn có biến thể **nuốt side-effect**:

```python
monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)   # ❌ nuốt
```

Nuốt đi thì hai nhánh "chưa cấu hình mật khẩu" và "sai mật khẩu" gộp về một vẫn xanh. Phải
**ghi lại** lời gọi rồi assert nội dung.

**Bài học đã đưa vào thư viện:** `roles/6_regression_reviewer.md` Bước 4.1.

---

## Bảng tra nhanh cho Reviewer

| Thấy cái này trong diff | Phản ứng |
|---|---|
| Hex màu ngoài `theme/` | FAIL |
| `setStyleSheet` cục bộ mới | FAIL |
| `setFixedWidth` / `setFixedSize` mới | FAIL trừ khi có lý do được nêu rõ |
| `QTimer.singleShot` để đợi | FAIL |
| `try/except` bao quanh chỗ crash | FAIL |
| Test xanh cả trước lẫn sau | FAIL |
| `visual_check: done` mà không có bằng chứng | FAIL |
| Diff > phạm vi plan | FAIL, tách PR |
| Sửa ở widget con thay vì chỗ chung | FAIL |
| `compare_digest` trên `str` không `.encode()` | FAIL — vỡ với mật khẩu có dấu |
| Thay bằng API "an toàn hơn" mà không kiểm miền đầu vào | FAIL cho tới khi trả lời 4 câu ở Bước 2.1 |
| Test quét thư mục mà không có lưới `assert seen > N` | FAIL — xanh giả khi quét rỗng |
| Fixture nuốt side-effect thay vì ghi lại | FAIL — không phân biệt được hai nhánh |
| File `.py` mới chưa `git add` | Không phải lỗi bản vá — bảo tác giả stage lại |
