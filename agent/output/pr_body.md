# Output Contract — `pr_body`

Do `regression-reviewer` sinh ra khi verdict là PASS / PASS_WITH_NOTES.
Khớp **đúng** `.gitea/PULL_REQUEST_TEMPLATE.md` — giữ nguyên tiêu đề mục để reviewer quen mắt.

Tiêu đề PR: `fix(ui): <mô tả ngắn, tiếng Anh, thể mệnh lệnh>`

---

## Summary

_Nói **tại sao**, không chỉ **cái gì**. Nêu triệu chứng người dùng, nguyên nhân gốc kèm
`file:line`, và vì sao chọn cách sửa này._

Root cause: `path/to/file.py:123` (pitfall P__)
Defect: `UI-<YYYYMMDD>-<NN>`

## Change Type

- [ ] Cowork feature
- [x] Bug fix
- [ ] Core AI contribution
- [ ] Test / hardening
- [ ] Performance
- [ ] Documentation

## Related Work

Cowork Task:

Core Repo: http://34.143.229.138/gitea-admin/fsg-ai-core-assets

Core AI Issue:

Core Task:

Related PR:

## Scope

**Cố ý bao gồm:**

**Cố ý KHÔNG bao gồm:** _(các phát hiện out-of-scope, kèm issue đề xuất)_

## Validation

- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual verification
- [ ] Regression check

Commands / evidence:

```bash
python scripts/run_quality_gate.py
QT_QPA_PLATFORM=offscreen pytest tests/ui/test_<...>.py -q
```

```
<output thật>
```

Ma trận kiểm bằng mắt:

| Trục | Kết quả |
|---|---|
| dark / light | |
| vi / ja / en | |
| cửa sổ nhỏ nhất / maximize | |

## Security Impact

_Permission / credential / network / customer data impact._

Điền cả khi là "không có". Nếu `security-review: required`: ghi rõ tại sao, và nhắc rằng
**CI xanh không đủ để merge** (`docs/governance/review-policy.md`).

## Compatibility

- [ ] No breaking change
- [ ] Breaking change documented

## Reviewer Notes

_Chỉ đúng chỗ cần soi kỹ nhất. Kèm các finding `should-fix` / `nit` mà reviewer agent đã
ghi nhận nhưng không chặn merge._

Ảnh `docs/screens/` cần chụp lại: _có/không — liệt kê slug_
