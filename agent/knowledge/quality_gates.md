# CASAN Quality Gate — cổng bắt buộc trước PR

Nguồn: `README.md`, `scripts/run_quality_gate.py`.

---

## 1. Năm cổng

| Cổng | Script | Kiểm tra |
|---|---|---|
| **C** — Clean Architecture | `scripts/check_imports.py` | `domain/` và `application/` không import `PySide6`, `PySide2`, `PyQt6`, `PyQt5`, `ui`, `app` |
| **A** — Atomic & Secrets | `scripts/audit_security.py` | Secret/plaintext trong file `.py` và file config |
| **S** — Single Responsibility | `scripts/check_loc.py --max-lines 400` | Mọi module production `<= 400 LOC` |
| **O** — Orphan Module | `scripts/check_orphan_modules.py` | Module không được import từ đâu |
| **A/N** — Tests | `pytest` | Toàn bộ suite |

## 2. Lệnh

```bash
# Đủ 5 cổng — chạy trước khi tạo PR
python scripts/run_quality_gate.py

# Chỉ guard tĩnh, bỏ test — vòng lặp sửa nhanh
python scripts/run_quality_gate.py --skip-tests

# Từng cổng
python scripts/check_imports.py
python scripts/audit_security.py
python scripts/check_loc.py --max-lines 400
pytest tests/e2e/test_smoke.py -v
```

## 3. Chạy test UI headless

```bash
QT_QPA_PLATFORM=offscreen pytest tests/ui -q          # bash
$env:QT_QPA_PLATFORM="offscreen"; pytest tests/ui -q  # PowerShell
```

64/108 module test dựng widget thật và 20 module import PySide6 ở module scope, nên môi
trường test **phải** có đủ runtime dependency. Chỉ có **một** `requirements.txt`, không có
cặp runtime/test riêng.

## 4. Bẫy khi sửa bug UI

- **Gate S rất dễ vỡ khi vá bug.** Nhiều file UI đã sát 400 dòng. Trước khi thêm code:
  ```bash
  python scripts/check_loc.py --max-lines 400 | grep <tên file>
  ```
  Sắp vượt → tách module **và nêu trong `fix_plan.md` trước khi làm** (`guardrail.md` G6).

- **Gate O bắt module mồ côi.** Tách file mới ra mà chưa import vào đâu là Gate O đỏ.
  Tách và nối dây trong cùng một commit.

- **Gate C ít khi liên quan bug UI** — trừ khi bản vá "tiện tay" import widget vào
  `application/`. Đó là dấu hiệu sửa sai tầng.

- **File `.py` mới phải được `git add` ngay.**
  `tests/test_no_ignored_source.py::test_khong_file_py_nao_bi_bo_quen_chua_theo_doi` quét
  `git ls-files --others --exclude-standard` và làm suite đỏ nếu có file `.py` chưa theo dõi
  trong thư mục nguồn. File test mới cũng tính. Triệu chứng giống hệt regression, nhưng
  không phải:

  ```
  AssertionError: File mã nguồn chưa được git add — clone sạch sẽ thiếu:
      tests/ui/test_<...>.py
  ```

- **`.venv` không được nằm trong repo.** `install.bat` dựng venv ở
  `%LOCALAPPDATA%\CoworkLocal` chính vì gate đi bộ toàn cây thư mục — một `.venv` trong repo
  biến mọi module vendored thành vi phạm Gate O.

## 5. Định nghĩa "xong"

Từ `docs/governance/definition-of-done.md`:

- code xong;
- test liên quan pass;
- tài liệu cập nhật nếu cần;
- PR đã được review;
- đã merge vào nhánh mặc định.

**Một PR = một thay đổi logic.** Không gộp nhiều bug UI không liên quan vào một PR.

Đóng góp từ FSG AI Core Team chỉ "xong" khi PR đã merge vào Cowork Local — "Core AI code
xong" hoặc "pre-review pass" **không** phải Done. Bằng chứng bắt buộc: core issue reference,
PR, evidence test, reviewer phía Cowork, merge commit.

---

## 6. Suite này vốn đã KHÔNG xanh

Tại `e5fa21e` (2026-09-07), chạy đầy đủ trên Windows + Python 3.14 cho ra:

```
11 failed, 884 passed, 2 skipped, 66 errors
```

Nghĩa là **"pytest đỏ" không nói lên điều gì** về bản vá của bạn. Bắt buộc phải so với
baseline, và so bằng **danh sách tên test**:

```bash
git stash push --include-untracked -m baseline
QT_QPA_PLATFORM=offscreen pytest -q > /tmp/base.txt 2>&1
git stash pop
QT_QPA_PLATFORM=offscreen pytest -q > /tmp/after.txt 2>&1

grep "^FAILED" /tmp/base.txt  | sed 's/ - .*//' | sort > /tmp/f_base.txt
grep "^FAILED" /tmp/after.txt | sed 's/ - .*//' | sort > /tmp/f_after.txt
comm -13 /tmp/f_base.txt /tmp/f_after.txt      # rỗng = không regression
```

Không so con số tổng: một test cũ hỏng cộng một test mới xanh cho ra cùng con số.

Nhóm đỏ lớn nhất hiện nay là `tests/characterization/test_co4e_runs_page.py` —
`RuntimeError: libshiboken: Internal C++ object (QGraphicsScene) already deleted`
(bẫy P13 trong `qt_pitfalls.md`). Chưa ai nhận sửa.

Gate A và Gate S cũng đỏ sẵn:

- A — 3 phát hiện trong `tests/test_project_context_{e2e,issue,knowledge}.py`;
- S — `core/chat_agent.py` 423 LOC, `mcp_servers/project_context/providers/knowledge.py` 408 LOC.

Đừng nhận nhầm bốn thứ trên là do bản vá của mình (`guardrail.md` G10).
