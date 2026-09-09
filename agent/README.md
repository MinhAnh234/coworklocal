# Agent Library — UI/UX Bug Fixing cho Cowork Local

Bộ instruction chuyên biệt để xử lý **bug UI/UX do người dùng báo** trong Cowork Local
(PySide6 desktop, 4-tier Clean Architecture).

Thiết kế theo **Production Agent Architecture** (FSG AI Core — Instruction Engineering
Training): mỗi agent có Role → Mission → Input → Process → Output → Quality Gate →
Self Review, và dùng chung một lớp `system/` (guardrail), `knowledge/` (project
knowledge), `checklist/`, `output/` (contract), `examples/`.

---

## 1. Vì sao tách như thế này

Anti-pattern mà bộ này cố tình tránh (mục 10 của tài liệu training):

| Anti-pattern | Cách bộ agent này xử lý |
|---|---|
| Hard-code theo project | Rule chung nằm ở `roles/`, tri thức riêng của Cowork Local nằm ở `knowledge/` |
| Prompt quá dài | Mỗi role là 1 file; knowledge được **tham chiếu**, không copy vào từng role |
| Không có Output Contract | Mọi output đi qua template trong `output/` |
| Không có Quality Gate | Mỗi role có Quality Gate riêng + `checklist/` dùng chung |
| Không có example | `examples/good_fix.md` và `examples/bad_fix.md` |
| Effort cố định bất kể lỗi to nhỏ | `roles/0_fix_dispatcher.md` chấm tier trước, lỗi 4px chạy 0 agent |

Sáu role **không** bị tách thành 7 file nhỏ mỗi role (role/task/process/...). Lý do:
phần bị lặp giữa các role chính là guardrail, knowledge và checklist — chúng đã được
tách ra thành module dùng chung. Phần còn lại của mỗi role gắn chặt với nhau
(process quyết định output contract, output contract quyết định quality gate), tách ra
chỉ tạo thêm chỗ để lệch nhau.

---

## 2. Cấu trúc

```text
agent/
├─ README.md                 ← bạn đang ở đây: index + routing map
├─ system/
│  ├─ guardrail.md           ← luật bất biến cho MỌI agent
│  ├─ security.md            ← xử lý log/screenshot/PII người dùng gửi lên
│  └─ response_policy.md     ← ngôn ngữ, format, khi nào được hỏi lại
├─ knowledge/
│  ├─ project_map.md         ← ui/ vs presentation/, tầng nào gọi được tầng nào
│  ├─ theme_tokens.md        ← luật màu sắc: KHÔNG file nào ngoài theme/ được đặt tên màu
│  ├─ i18n_rules.md          ← tr(), on_language_changed, 3 ngôn ngữ
│  ├─ screen_map.md          ← map câu chữ người dùng → màn hình → file:line
│  ├─ qt_pitfalls.md         ← 20 nguyên nhân gốc hay gặp của bug UI PySide6
│  ├─ secrets_and_config.md  ← SecretStore, schema migration, bẫy .get() trên config merge
│  └─ quality_gates.md       ← CASAN gate, lệnh chạy, test headless
├─ roles/                    ← 1 hub + 7 agent chuyên biệt
│  ├─ 0_fix_dispatcher.md   ← HUB: chấm tier T0/T1/T2/T3, chọn lane, tách defect
│  ├─ 1_ui_bug_triage.md
│  ├─ 2_ui_visual_fixer.md
│  ├─ 3_ux_flow_fixer.md
│  ├─ 4_i18n_a11y_fixer.md
│  ├─ 5_fix_implementer.md
│  ├─ 6_regression_reviewer.md
│  └─ 7_security_defect_fixer.md
├─ commands/
│  └─ fix.md                 ← nguồn của slash command /fix (điểm vào của hub)
├─ workflow/
│  ├─ intake_to_fix.md       ← pipeline end-to-end, 4 lane theo tier
│  └─ handoff_contract.md    ← envelope truyền giữa các agent
├─ checklist/
│  ├─ ui_review.md
│  ├─ ux_review.md
│  └─ pr_readiness.md
├─ output/
│  ├─ dispatch_plan.md       ← template điều phối (output của Hub)
│  ├─ defect_record.md       ← template hồ sơ lỗi (output của Triage)
│  ├─ fix_plan.md            ← template phương án sửa (output của Fixer)
│  ├─ fix_report.md          ← template báo cáo sau khi sửa (output của Implementer)
│  └─ pr_body.md             ← template PR khớp .gitea/PULL_REQUEST_TEMPLATE.md
└─ examples/
   ├─ good_fix.md
   └─ bad_fix.md
```

---

## 3. Một hub + bảy agent, và khi nào dùng

| # | Agent | Pattern | Nhận vào | Trả ra |
|---|---|---|---|---|
| **0** | **Fix Dispatcher** (hub) | Router | Phản ánh thô của người dùng | `dispatch_plan.md` — tier + lane + tách defect |
| 1 | **UI Bug Triage** | Reviewer | Lời kể lộn xộn của user, ảnh chụp màn hình, log | `defect_record.md` + phân loại + route |
| 2 | **UI Visual Fixer** | Generator | defect_record (loại `visual`) | `fix_plan.md` — layout/QSS/theme/icon/DPI |
| 3 | **UX Flow Fixer** | Generator | defect_record (loại `flow`) | `fix_plan.md` — luồng, trạng thái, phản hồi |
| 4 | **i18n & A11y Fixer** | Generator | defect_record (loại `i18n`/`a11y`) | `fix_plan.md` — tr(), tràn chữ, contrast, bàn phím |
| 5 | **Fix Implementer** | Generator | `fix_plan.md` | Patch thật + `fix_report.md` |
| 6 | **Regression Reviewer** | Reviewer | Patch + fix_report | Verdict PASS/FAIL + `pr_body.md` |
| 7 | **Security Defect Fixer** | Generator | defect_record (loại `security`) | `fix_plan.md` — credential, secret, migration |

Đây là **Multi-Agent Pattern**: `Dispatcher (Router) → Triage (Planner) → Specialist →
Implementer (Executor) → Reviewer`.

**Số bước thực chạy do agent 0 quyết định, không phải mặc định 5.** Bộ v1.2 chạy đủ pipeline
cho mọi lỗi, kể cả đổi một giá trị 4px — đó là lý do agent 0 ra đời. Bốn lane:

| Tier | Lỗi kiểu gì | Lane | Gọi agent |
|---|---|---|---|
| **T0** | Đổi số đo hiển thị, sai chính tả chuỗi có key sẵn, đổi token màu có sẵn | DIRECT | **0 lần** — hub sửa luôn + 4 cổng máy |
| **T1** | Nguyên nhân gốc đã rõ kèm `file:line`, 1 màn, ≤ 3 file, ≤ 40 LOC | SOLO | 1 lần |
| **T2** | Nguyên nhân chưa rõ nhưng đã khoanh 1 màn; chạm QSS/token/i18n dùng chung | PAIR | 3 lần |
| **T3** | Mô tả thuần triệu chứng, không tái hiện được, nhiều category, > 150 LOC | FULL | 4–5 lần |

Bước 1 vẫn **không** được bỏ ở T3 — 80% bug UI báo lên là mô tả triệu chứng, không phải
nguyên nhân. Ở T1/T2, phần triage do hub tự làm trong `dispatch_plan`, và chỉ hợp lệ khi
phản ánh đã tự chỉ ra màn hình + triệu chứng cụ thể. Bước 6 chỉ được bỏ ở T0/T1, và phải
nêu rõ cổng nào thay thế.

Agent 7 là specialist thứ tư, ngang hàng 2/3/4 trong pipeline, nhưng khác ở hai điểm: nó
được phép chạm `config.py`, `infrastructure/`, `core/` (ba role kia bị chặn ở tầng
presentation), và nó **không được tự quyết chính sách bảo mật** — bốn câu hỏi bắt buộc trả
về cho Cowork Team.

### Routing rule (Hub chấm tier → Triage chọn specialist)

```text
Người dùng báo lỗi
   │
   ├─ agent 0 tách thành N defect_id, chấm tier từng cái
   │  (≤ 5 lệnh đọc/grep, 0 subagent; hết mà chưa chấm được → T2)
   │
   ├─ "nhìn sai / lệch / mất chữ / màu lạ / bị che"        → 2. UI Visual Fixer
   ├─ "bấm không ăn / không biết đang chạy / mất dữ liệu"  → 3. UX Flow Fixer
   ├─ "chữ tiếng Nhật bị tràn / đổi ngôn ngữ không đổi"    → 4. i18n & A11y Fixer
   ├─ "mật khẩu nằm trong code / mở khoá bằng ô trống"     → 7. Security Defect Fixer
   └─ "app crash / sai số liệu / sai nghiệp vụ"            → KHÔNG phải bug UI.
                                                             Trả về, mở issue type:bug thường.

Nhóm `security` THẮNG mọi nhóm khác: lỗi vừa lệch layout vừa lộ credential thì đi 7 trước.
Tín hiệu bảo mật cũng ép tier lên **T3-SEC** bất kể diff nhỏ cỡ nào — một dòng `==` so
mật khẩu không bao giờ là T0.
```

Tier chỉ đi **lên**. FAIL ở bước 6 → tier +1 rồi chạy lại, không sửa lại ở nguyên tier cũ.

---

## 4. Cách dùng

### 4.0 Điểm vào (khuyến nghị)

Cài một lần cho mỗi máy — `.claude/` nằm trong `.gitignore`, nên nó **không** theo
clone; `agent/` mới là bản gốc được version:

```bash
mkdir -p .claude/agents .claude/commands
cp agent/roles/[1-7]_*.md .claude/agents/
cp agent/commands/fix.md  .claude/commands/
```

Rồi:

```text
/fix màn Folder kéo to ra thì mất cây thư mục bên trái
```

Hub sẽ chấm tier, in `dispatch_plan`, rồi tự chạy đúng lane. Chỉ gọi trực tiếp role 1–7
khi đã biết chắc tier.

### 4.1 Dùng thủ công (mọi trợ lý AI)

Nạp theo đúng thứ tự này rồi dán bug report của user vào:

```text
agent/system/guardrail.md
agent/system/security.md
agent/system/response_policy.md
agent/roles/0_fix_dispatcher.md          ← luôn nạp trước, để biết cần chạy tới đâu
agent/roles/<role đang dùng>.md
+ các file knowledge/ mà role đó liệt kê ở mục "KNOWLEDGE"
```

### 4.2 Dùng trong Claude Code (subagent)

Mỗi file trong `roles/` có sẵn YAML frontmatter `name` + `description`. Để biến thành
subagent, copy sang `.claude/agents/`:

```bash
mkdir -p .claude/agents
cp agent/roles/[1-7]_*.md .claude/agents/
```

`0_fix_dispatcher.md` **không** copy vào `.claude/agents/`: hub cần quyền gọi agent khác,
mà subagent trong Claude Code không gọi được subagent. Hub chạy ở session chính, qua
`/fix` (`.claude/commands/fix.md`).

Sau đó gọi bằng tên: `ui-bug-triage`, `ui-visual-fixer`, `ux-flow-fixer`,
`i18n-a11y-fixer`, `fix-implementer`, `regression-reviewer`, `security-defect-fixer`.

### 4.3 Chạy cả pipeline

Xem `workflow/intake_to_fix.md`.

---

## 5. Versioning

Bộ instruction này được version bằng Git cùng source. Khi sửa một role, ghi lý do
trong commit message — instruction cũng là code.

| Version | Ngày | Thay đổi |
|---|---|---|
| 1.0 | 2026-09-07 | Bản đầu: 6 role, 6 knowledge module, 4 output contract |
| 1.1 | 2026-09-07 | Thêm role 7 `security-defect-fixer` + `knowledge/secrets_and_config.md`. Lý do: bộ v1.0 chỉ phủ UI/UX, nên credential hardcode phát hiện qua màn Settings bị rơi vào `not-ui` và không ai nhận |
| 1.4 | 2026-09-08 | Nạp bài học từ lượt audit i18n toàn app. `knowledge/i18n_rules.md` §2.0 (`bind_*` là cách mặc định cho chuỗi tĩnh, `bind_dynamic` cho chữ theo trạng thái, không bind dữ liệu), §"Cách TÌM ra hết các chỗ bị lỗi" (grep chuỗi tiếng Việt ra 962 dòng mà **không** dòng nào là lỗi thật; phép đo đúng là thay `tr()` bằng chuỗi mốc trên `MainWindow` thật), và 3 mục checklist mới. Lý do: bộ v1.3 không có cách nào phát hiện lỗi "chữ không được áp lại" — nó không để lại dấu vết nào trong source |
| 1.3 | 2026-09-08 | Thêm hub `0_fix_dispatcher` + `output/dispatch_plan.md` + `/fix`. Lý do: bộ v1.2 không có tầng điều phối, nên **mọi** lỗi đều kéo cả pipeline 4–5 agent — kể cả nới một `setMinimumWidth` lên 232px. Bổ sung 4 lane theo tier, danh sách đóng T0 (6 loại + 9 disqualifier), 4 cổng máy thay reviewer ở T0, luật escalate một chiều, và luật tách một phản ánh thành nhiều `defect_id` chấm tier riêng |
| 1.2 | 2026-09-07 | Nạp bài học từ lần chạy thật đầu tiên (`SEC-20260907-01`). Bản vá của bước 5 mang một blocker mà **không mục nào trong bộ v1.1 bắt được** — reviewer tìm ra bằng tay. Bổ sung: `secrets_and_config.md` §9 (chặn rỗng, `compare_digest` + ASCII, và luật "API an toàn hơn thường có miền đầu vào hẹp hơn"); `6_regression_reviewer.md` Bước 2.1 (ràng buộc miền đầu vào) và 4.1 (test rỗng ruột); `5_fix_implementer.md` + `quality_gates.md` (baseline bằng `comm -13` trên tên test, guard `git add`, và thực tế suite vốn đã đỏ 11+66); `bad_fix.md` ca 11-12 — hai ví dụ **có thật** đầu tiên trong file |
