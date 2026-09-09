# Workflow — từ phản ánh của người dùng tới PR

## 0. Lane theo tier — đọc trước

Pipeline dưới đây là **lane FULL (T3)**, không phải mặc định. `0_fix_dispatcher` chấm tier
trước và cắt bớt bước:

| Tier | Lane | Bước thực chạy | Gọi agent |
|---|---|---|---|
| **T0** | DIRECT | hub sửa → 4 cổng máy (`roles/0_fix_dispatcher.md` §4.1) | 0 |
| **T1** | SOLO | hub triage inline → **5** → hub review bằng `checklist/ui_review.md` | 1 |
| **T2** | PAIR | hub triage inline → **2/3/4** → **5** → **6** | 3 |
| **T3** | FULL | **1** → **2/3/4** → **5** → **6** | 4–5 |
| **T3-SEC** | FULL-SEC | **7** → *(Cowork Team)* → **5** → **6** | 3 + chờ người |

Bỏ bước nào cũng phải **nêu rõ trong `dispatch_plan`** cổng nào thay thế. Bước **6** chỉ
được bỏ ở T0 và T1.

## 1. Pipeline (lane FULL)

```text
  Người dùng báo lỗi (chat / issue / miệng)
              │
              ▼
  ┌───────────────────────────┐
  │ 0. fix-dispatcher   HUB   │  → dispatch_plan.md
  │    Router                 │     + tách N defect_id + tier + lane
  └───────────┬───────────────┘
              │ T0 → hub tự sửa, KHÔNG đi tiếp
              │ T1 → nhảy thẳng xuống bước 5
              │ T2 → nhảy thẳng xuống bước 2/3/4
              │ T3 → đi tiếp bước 1
              ▼
  ┌───────────────────────────┐
  │ 1. ui-bug-triage          │  → defect_record.md
  │    Planner                │     + category + severity + confidence
  └───────────┬───────────────┘
              │ route theo category  (security THẮNG mọi nhóm khác)
      ┌───────┬─┴──────┬──────────┬───────────┐
      ▼       ▼        ▼          ▼           ▼
  ┌────────┐┌────────┐┌──────────┐┌─────────┐ not-ui
  │ 2.     ││ 3.     ││ 4.       ││ 7.      │ → RETURN_TO_REPORTER
  │ visual ││ flow   ││ i18n-a11y││ security│   (mở issue type:bug thường)
  └────┬───┘└───┬────┘└────┬─────┘└────┬────┘
       └────────┼──────────┴───────────┘
                │   ⚠ role 7 có thể dừng ở đây:
                │   4 câu chính sách chưa có đáp án
                │   → RETURN_TO_REPORTER (needs-security-decision)
                ▼  fix_plan.md
  ┌───────────────────────────┐
  │ 5. fix-implementer        │  → patch + fix_report.md
  │    Executor (SỬA FILE)    │     + CASAN gate output
  └───────────┬───────────────┘
              ▼
  ┌───────────────────────────┐
  │ 6. regression-reviewer    │  → verdict + pr_body.md
  │    Reviewer               │
  └───────────┬───────────────┘
       FAIL ──┘ (quay lại 5, hoặc về 2/3/4 nếu sai nguyên nhân gốc)
       PASS ──▶ Cowork Team review → merge
```

## 2. Ai được làm gì

| Agent | Đọc | Sửa file | Chạy lệnh | Quyết định |
|---|---|---|---|---|
| 0. dispatcher | ✅ | ✅ **chỉ ở T0** | ✅ (grep, gate) | tier + lane + tách defect |
| 1. triage | ✅ | ❌ | ✅ (grep, tra manifest) | phân loại + route |
| 2/3/4. specialist | ✅ | ❌ | ✅ (đọc, kiểm LOC) | nguyên nhân gốc + phương án |
| 7. security | ✅ | ❌ | ✅ (đọc, `git log -S`) | lỗ hổng + migration; **không** quyết chính sách |
| 5. implementer | ✅ | ✅ | ✅ (git, pytest, gate) | cách hiện thực trong phạm vi plan |
| 6. reviewer | ✅ | ❌ | ✅ (git, pytest, gate) | PASS / FAIL |
| Cowork Team | — | — | — | **merge** |

Chỉ **một** agent được sửa file. Ranh giới này là thứ giữ cho pipeline review được.

Ngoại lệ duy nhất là hub ở **T0**, và nó bị bó rất chặt để đổi lại: danh sách đóng 6 loại
thay đổi, 9 disqualifier, trần ≤ 2 file / ≤ 10 dòng, và 4 cổng máy bắt buộc dán output thật.
Vượt bất kỳ ràng buộc nào → `git checkout --` rồi chấm lại T2. Hub **không** được sửa file ở
T1/T2/T3 — ở đó nó chỉ điều phối và (ở T1) review, vì reviewer không được là người viết patch.

## 3. Cổng chuyển bước

Không bước nào được đi tiếp nếu chưa đạt:

| Từ → Đến | Điều kiện |
|---|---|
| 0 → bất kỳ | Mỗi defect_id có đúng 1 tier + 1 lane, tier ≠ T0 dẫn được về một dòng cụ thể của Bước 3, đã xét override bảo mật trước |
| 0 → tự sửa (T0) | Trúng danh sách đóng, 0 disqualifier, Gate S + blast radius đã **đo bằng lệnh** |
| 1 → 2/3/4 | `confidence >= medium`, có ít nhất một `file:line`, đã redact |
| 2/3/4 → 5 | Đúng **một** nguyên nhân gốc, có cách kiểm chứng, không vượt 400 LOC (hoặc đã có kế hoạch tách) |
| 7 → 5 | Như trên, **cộng thêm**: có đường di trú cho cả 4 nhóm người dùng, và 4 câu chính sách đã có đáp án của Cowork Team |
| 5 → 6 | 5 cổng CASAN xanh, test regression đỏ-trước-xanh-sau |
| 6 → người | Verdict PASS/PASS_WITH_NOTES + `pr_body` |

`confidence: low` ở bất kỳ đâu → quay về bước 1. Không đoán tiếp.

## 4. Vòng lặp và giới hạn

- FAIL ở bước 6 → về bước 5 (lỗi hiện thực) hoặc về 2/3/4 (sai nguyên nhân gốc).
- **Tier +1 mỗi lần FAIL.** Chạy lại ở nguyên tier cũ là lỗi điều phối: hai lần thất bại ở
  cùng độ sâu gần như luôn có nghĩa là hồ sơ lỗi sai từ đầu.
- Tier chỉ đi **lên**. Không có đường hạ tier giữa dòng, kể cả khi diff hoá ra nhỏ.
- Quá **2 vòng** mà vẫn FAIL → dừng, đưa người thật vào. Vòng thứ ba thường có nghĩa là
  `defect_record` sai từ đầu, không phải bản vá sai.

## 5. Đường tắt hợp lệ

Đây là các đường tắt hub được phép chọn ở Bước 3. Chúng **thay thế** phần "đường tắt" của
bộ v1.2 — trước đây tự phát, giờ có tier và có cổng bù.

| Tình huống | Tier | Đường tắt |
|---|---|---|
| Nới một số đo hiển thị (px, margin, spacing) | T0 | hub sửa, 0 agent |
| Sai chính tả / sai dấu một chuỗi đã có key | T0 | hub sửa, đủ 3 ngôn ngữ, **vẫn phải có test** |
| Đổi token màu có sẵn sang token có sẵn | T0 | hub sửa, 0 agent |
| Thiếu key i18n, UI hiện ra `a.b_c`, đã biết file | T1 | 5 → hub review |
| Nguyên nhân gốc đã có `file:line` từ người báo (dev) | T1 | 5 → hub review |
| Chạm QSS/token dùng chung, phải kiểm 2 theme | T2 | 4 (hoặc 2) → 5 → 6 |
| Lỗi do chính bản vá vừa merge | T3 | đủ pipeline — regression nghĩa là nguyên nhân gốc lần trước sai |
| Dev báo thẳng một lỗ hổng | T3-SEC | vào thẳng 7, bỏ bước 1 |

Bước **6** chỉ được bỏ ở T0 và T1. Ở T0 nó được thay bằng 4 cổng máy; ở T1 nó được thay bằng
hub review với `checklist/ui_review.md` (hợp lệ vì hub không viết patch ở T1). Ở T2/T3/T3-SEC
không có đường tắt nào bỏ qua bước 6.

## 6. Chạy bằng Claude Code

```bash
mkdir -p .claude/agents .claude/commands
cp agent/roles/[1-7]_*.md .claude/agents/
cp agent/commands/fix.md  .claude/commands/
```

`.claude/` nằm trong `.gitignore` (dòng 109) nên phải cài lại trên mỗi clone — `agent/`
là bản gốc. `0_fix_dispatcher.md` không copy sang `agents/`: hub chạy ở session chính vì
subagent không gọi được subagent. Điểm vào:

```text
> /fix màn Folder kéo to ra thì mất cây thư mục bên trái
```

Hub in `dispatch_plan` rồi tự chạy lane. Muốn chạy tay lane FULL:

```text
> dùng ui-bug-triage cho phản ánh này: "màn Folder kéo to ra thì mất cây thư mục bên trái"
> dùng ui-visual-fixer với defect_record ở trên
> dùng fix-implementer với fix_plan ở trên
> dùng regression-reviewer với patch vừa rồi
```

Các bước trong **một** `defect_id` chạy tuần tự — mỗi bước phụ thuộc output của bước trước.
Các `defect_id` **độc lập** thì chạy song song được, gọi trong cùng một message.
