"""Chuỗi hiển thị — phần hint.

Cắt ra từ ``i18n.py``: một dict 3.000 dòng không mở nổi để sửa một chữ.
Cắt theo mốc phân đoạn có sẵn, nên mỗi cụm vẫn là các màn đi liền nhau.
``i18n.py`` gộp tất cả lại thành ``STRINGS``.
"""
from __future__ import annotations

from typing import Dict

STRINGS: Dict[str, Dict[str, str]] = {
    "schedtask.notify_email_placeholder": {
        "en": "recipient@example.com (comma-separated)",
        "ja": "recipient@example.com（カンマ区切り）",
        "vi": "nguoinhan@example.com (cách nhau dấu phẩy)"},
    "schedtask.notify_hint": {
        "en": "When the scheduled/cron task finishes, send a reminder. Teams uses the webhook "
              "from Settings; Outlook sends from your signed-in Outlook desktop app — no login needed.",
        "ja": "スケジュール/Cronタスク完了時にリマインダーを送信。Teamsは設定のWebhookを使用、"
              "Outlookはサインイン済みのOutlookデスクトップから送信（ログイン不要）。",
        "vi": "Khi task theo lịch/cron chạy xong sẽ gửi nhắc. Teams dùng webhook trong Settings; "
              "Outlook gửi từ ứng dụng Outlook đã đăng nhập trên máy — không cần đăng nhập lại."},
    "schedtask.notify_need_email": {
        "en": "Enter a recipient address for the Outlook reminder.",
        "ja": "Outlookリマインダーの送信先アドレスを入力してください。",
        "vi": "Hãy nhập địa chỉ người nhận cho nhắc nhở qua Outlook."},
    "schedtask.notify_need_webhook": {
        "en": "Teams reminder needs a webhook URL — set it in Settings → Parameter first.",
        "ja": "TeamsリマインダーにはWebhook URLが必要です。先に設定→パラメータで設定してください。",
        "vi": "Nhắc qua Teams cần webhook URL — hãy đặt trong Settings → Parameter trước."},
    "schedtask.tz_local_note": {
        "en": "Times use this machine's local timezone.", "ja": "時刻はこのPCのローカルタイムゾーンです。",
        "vi": "Giờ dùng múi giờ local của máy này."},
    "schedtask.g_flow": {"en": "Flow Setup", "ja": "フロー設定", "vi": "Thiết lập Flow"},
    "schedtask.flow_hint": {
        "en": "(Flow tasks only) Steps run in order; each step's output feeds the next step's input.",
        "ja": "（Flowタスクのみ）ステップは順番に実行され、前ステップの出力が次の入力になります。",
        "vi": "(Chỉ task Flow) Các bước chạy tuần tự; output bước trước nối vào input bước sau."},
    "schedtask.flow_template": {"en": "Code template:", "ja": "Codeテンプレート:", "vi": "Template Code:"},
    "schedtask.import_flow_btn": {"en": "Import steps", "ja": "ステップ取込", "vi": "Nhập các bước"},
    "schedtask.flow_template_empty": {
        "en": "The selected template has no steps.", "ja": "選択したテンプレートにステップがありません。",
        "vi": "Template đã chọn không có bước nào."},
    "schedtask.step_name_ph": {"en": "Step name", "ja": "ステップ名", "vi": "Tên bước"},
    "schedtask.step_prompt_ph": {"en": "Prompt / command", "ja": "プロンプト/コマンド", "vi": "Prompt / lệnh"},
    "schedtask.stepexec.cowork": {"en": "Cowork", "ja": "Cowork", "vi": "Cowork"},
    "schedtask.stepexec.co4e": {"en": "Code", "ja": "Code", "vi": "Code"},
    "schedtask.stepexec.script": {"en": "Script", "ja": "スクリプト", "vi": "Script"},
    "schedtask.stepexec.manual": {"en": "Manual", "ja": "手動", "vi": "Thủ công"},
    "schedtask.del_step_tooltip": {"en": "Delete the selected step", "ja": "選択したステップを削除",
                                    "vi": "Xóa bước đang chọn"},
    "schedtask.guide_tooltip": {
        "en": "Open the Schedule Task user guide", "ja": "Schedule Task の使い方ガイドを開く",
        "vi": "Mở hướng dẫn sử dụng Schedule Task"},
    "schedtask.guide_missing": {
        "en": "Guide file not found (docs/schedule_task_user_guide.md).",
        "ja": "ガイドファイルが見つかりません (docs/schedule_task_user_guide.md)。",
        "vi": "Không tìm thấy file hướng dẫn (docs/schedule_task_user_guide.md)."},
    "schedtask.msg_set_schedule": {
        "en": "Set a run time so this task can actually run on schedule.",
        "ja": "実行時刻を設定するとスケジュール実行されます。",
        "vi": "Hãy đặt giờ chạy để task này thực sự chạy theo lịch."},
    # ---- hint tooltips (hover help) --------------------------------------
    "schedtask.add_tooltip": {
        "en": "Create a new task with full options (schedule, input, dependencies…).",
        "ja": "新しいタスクを作成（スケジュール・入力・依存など全設定）。",
        "vi": "Tạo task mới với đầy đủ tuỳ chọn (lịch, input, phụ thuộc…)."},
    "schedtask.search_tooltip": {
        "en": "Filter cards by title/description.", "ja": "タイトル/説明でカードを絞り込み。",
        "vi": "Lọc card theo tiêu đề/mô tả."},
    "schedtask.filter_tooltip": {
        "en": "Show only one task type.", "ja": "1つのタスク種別のみ表示。",
        "vi": "Chỉ hiện một loại task."},
    "schedtask.col_tip.backlog": {
        "en": "New tasks with no schedule yet. Drag a card here to shelve it.",
        "ja": "未スケジュールの新規タスク。", "vi": "Task mới, chưa đặt lịch. Kéo card vào đây để cất lại."},
    "schedtask.col_tip.scheduled": {
        "en": "On the calendar — runs automatically at its time. Drop a card here to schedule it.",
        "ja": "スケジュール済み — 時刻になると自動実行。", "vi": "Đã lên lịch — tự chạy khi đến giờ. Thả card vào đây để đặt lịch."},
    "schedtask.col_tip.running": {
        "en": "Currently executing. Drop a card here to RUN it immediately.",
        "ja": "実行中。ここにドロップすると即実行します。", "vi": "Đang chạy. Thả card vào đây để CHẠY NGAY."},
    "schedtask.col_tip.waiting_input": {
        "en": "Waiting: needs your Run-now approval, or its prerequisite tasks aren't Done yet.",
        "ja": "待機中: 手動承認待ち、または前提タスクが未完了。",
        "vi": "Đang chờ: cần bạn bấm Chạy ngay (phê duyệt), hoặc các task phụ thuộc chưa Done."},
    "schedtask.col_tip.done": {
        "en": "Finished successfully. Drop a card here to mark it done by hand.",
        "ja": "完了。ここにドロップすると手動で完了扱いにします。",
        "vi": "Đã xong. Thả card vào đây để tự đánh dấu hoàn thành."},
    "schedtask.col_tip.failed": {
        "en": "Last run errored — right-click → Run history to see why.",
        "ja": "前回失敗 — 右クリック→実行履歴で原因を確認。",
        "vi": "Lần chạy cuối bị lỗi — chuột phải → Lịch sử chạy để xem lý do."},
    "schedtask.col_tip.paused": {
        "en": "Paused: never auto-runs and is skipped by chains until resumed.",
        "ja": "一時停止中: 再開まで自動実行されず、チェーンでもスキップされます。",
        "vi": "Tạm dừng: không tự chạy và bị chuỗi bỏ qua cho tới khi tiếp tục."},
    "schedtask.hint_type": {
        "en": "Cowork = documents/answers · Code = coding agent · Script = shell command · Flow = multi-step · Manual = tracking only.",
        "ja": "Cowork=文書/回答 · Code=コーディング · Script=コマンド · Flow=複数ステップ · Manual=管理のみ。",
        "vi": "Cowork = tài liệu/trả lời · Code = agent code · Script = lệnh shell · Flow = nhiều bước · Manual = chỉ quản lý."},
    "schedtask.hint_status": {
        "en": "Current Kanban lane. Usually managed automatically by the scheduler.",
        "ja": "現在のKanbanレーン。通常はスケジューラーが自動管理。",
        "vi": "Cột Kanban hiện tại. Thường được scheduler tự quản lý."},
    "schedtask.hint_script": {
        "en": "Shell command to run (Script tasks). Runs in the task's artifact folder with a timeout.",
        "ja": "実行するシェルコマンド（Scriptタスク）。", "vi": "Lệnh shell sẽ chạy (task Script), trong thư mục artifact riêng, có timeout."},
    "schedtask.hint_sched_enable": {
        "en": "Off = the task never runs by itself.", "ja": "OFF = 自動実行されません。",
        "vi": "Tắt = task không bao giờ tự chạy."},
    "schedtask.hint_run_at": {
        "en": "First/next run time (this machine's local time).",
        "ja": "初回/次回の実行時刻（ローカル時刻）。", "vi": "Giờ chạy đầu/kế tiếp (giờ local của máy)."},
    "schedtask.hint_repeat": {
        "en": "After a successful run, the schedule rolls to the next occurrence automatically.",
        "ja": "成功後、次回分へ自動的に繰り越します。",
        "vi": "Sau khi chạy thành công, lịch tự dời sang kỳ kế tiếp."},
    "schedtask.hint_cron": {
        "en": "5 fields: minute hour day month weekday. E.g. '0 9 * * 1-5' = 9:00 on weekdays.",
        "ja": "5項目: 分 時 日 月 曜日。例 '0 9 * * 1-5' = 平日9時。",
        "vi": "5 trường: phút giờ ngày tháng thứ. VD '0 9 * * 1-5' = 9h các ngày thường."},
    "schedtask.hint_workdays": {
        "en": "Runs landing on Sat/Sun are pushed to the next working day.",
        "ja": "土日に当たる回は翌営業日に繰り越し。", "vi": "Lịch rơi vào T7/CN sẽ dời sang ngày làm việc kế."},
    "schedtask.hint_holidays": {
        "en": "Runs landing on a public holiday of the chosen country are pushed to the next allowed day.",
        "ja": "選択した国の祝日に当たる回は翌営業日に繰り越し。",
        "vi": "Lịch rơi vào ngày lễ của quốc gia đã chọn sẽ tự dời sang ngày hợp lệ kế."},
    "schedtask.hint_country": {
        "en": "ISO country code for the holiday calendar (VN, JP, US… — type any code).",
        "ja": "祝日カレンダーの国コード（VN, JP, US…）。", "vi": "Mã quốc gia cho lịch nghỉ lễ (VN, JP, US… — gõ được mã bất kỳ)."},
    "schedtask.hint_flow_template": {
        "en": "Import the stages of a saved Flow template as steps here.",
        "ja": "保存済みFlowテンプレートをステップとして取り込み。",
        "vi": "Nhập các stage của Flow template đã lưu thành các bước ở đây."},
    "schedtask.hint_input_mode": {
        "en": "What the agent receives besides the description: nothing, typed text, file contents, or the output of earlier tasks.",
        "ja": "説明に加えてエージェントへ渡す入力。", "vi": "Agent nhận gì ngoài mô tả: trống, văn bản gõ tay, nội dung tệp, hoặc output các task trước."},
    "schedtask.hint_prev_task": {
        "en": "Single explicit source task for 'previous task output' (leave (none) to use all waited-for tasks).",
        "ja": "「前タスクの出力」の明示的なソース。", "vi": "Task nguồn cụ thể cho 'output task trước' (để (không) sẽ dùng tất cả task đang chờ)."},
    "schedtask.hint_output_mode": {
        "en": "Expected output format — informational for now, files always land in the artifact folder.",
        "ja": "想定する出力形式（参考情報）。", "vi": "Định dạng output mong muốn — hiện mang tính thông tin, file luôn nằm trong thư mục artifact."},
    "schedtask.hint_next_task": {
        "en": "Task to trigger after this one finishes (chain).",
        "ja": "このタスク完了後に起動するタスク（チェーン）。", "vi": "Task được kích hoạt sau khi task này xong (chuỗi)."},
    "schedtask.hint_run_next": {
        "en": "When the next task fires: on success / always / only after you confirm.",
        "ja": "次タスクの起動条件: 成功時/常に/手動確認後。", "vi": "Khi nào task sau chạy: khi thành công / luôn / chờ bạn xác nhận."},
    "schedtask.hint_pass_output": {
        "en": "This task's output.md becomes the next task's input automatically.",
        "ja": "このタスクのoutput.mdを次タスクの入力に自動投入。",
        "vi": "output.md của task này tự thành input của task sau."},
    "schedtask.hint_depends": {
        "en": "Fan-in: this task waits until ALL ticked tasks are Done, then runs automatically with their outputs available.",
        "ja": "ファンイン: チェックした全タスクがDoneになるまで待機し、自動実行。",
        "vi": "Fan-in: task này đợi TẤT CẢ task được tick Done rồi mới tự chạy, kèm output của chúng."},
    "schedtask.hint_retry": {
        "en": "Auto-retry this many times when a run fails.", "ja": "失敗時の自動リトライ回数。",
        "vi": "Tự thử lại bấy nhiêu lần khi chạy lỗi."},
    "schedtask.hint_timeout": {
        "en": "Hard limit per run (Script tasks).", "ja": "1回あたりの上限時間（Script）。",
        "vi": "Giới hạn thời gian mỗi lần chạy (task Script)."},
    "schedtask.hint_approval": {
        "en": "Safety: the scheduler will NEVER auto-run this — it parks in Waiting Input until you right-click → Run now.",
        "ja": "安全: 自動実行されず、Run nowまで待機します。",
        "vi": "An toàn: scheduler KHÔNG BAO GIỜ tự chạy task này — nó nằm ở Waiting Input tới khi bạn chuột phải → Chạy ngay."},
    "schedtask.g_input": {"en": "Input", "ja": "入力", "vi": "Đầu vào"},
    "schedtask.f_input_mode": {"en": "Input mode", "ja": "入力モード", "vi": "Chế độ input"},
    "schedtask.inmode.empty": {"en": "Empty (default)", "ja": "空（既定）", "vi": "Trống (mặc định)"},
    "schedtask.inmode.manual": {"en": "Manual text", "ja": "手入力テキスト", "vi": "Văn bản nhập tay"},
    "schedtask.inmode.file": {"en": "File(s)", "ja": "ファイル", "vi": "Tệp"},
    "schedtask.inmode.previous_task_output": {
        "en": "Previous task output", "ja": "前タスクの出力", "vi": "Output của task trước"},
    "schedtask.f_manual_text": {"en": "Prompt", "ja": "プロンプト", "vi": "Prompt"},
    "schedtask.gen_input_tooltip": {
        "en": "AI-draft the prompt from the title/description", "ja": "タイトル/説明からプロンプトをAI生成",
        "vi": "AI soạn prompt từ tiêu đề/mô tả"},
    "schedtask.f_files": {"en": "Attach files", "ja": "添付ファイル", "vi": "Đính kèm tệp"},
    "schedtask.f_links": {"en": "Attach links", "ja": "添付リンク", "vi": "Đính kèm link"},
    "schedtask.files_placeholder": {
        "en": "Local file paths, separated by ;", "ja": "ローカルファイルパス（;区切り）",
        "vi": "Đường dẫn tệp local, cách nhau bằng ;"},
    "schedtask.links_placeholder": {
        "en": "https://…  URLs separated by ;", "ja": "https://…  URL（;区切り）",
        "vi": "https://…  các link, cách nhau bằng ;"},
    "schedtask.pick_files": {"en": "Browse…", "ja": "参照…", "vi": "Chọn tệp…"},
    "schedtask.add_link_title": {"en": "Add link", "ja": "リンクを追加", "vi": "Thêm link"},
    "schedtask.add_link_label": {"en": "URL:", "ja": "URL:", "vi": "URL:"},
    "schedtask.hint_files": {
        "en": "Attached files are always read and given to the agent as context, regardless of Input mode.",
        "ja": "添付ファイルはInputモードに関係なく常にエージェントへ渡されます。",
        "vi": "Tệp đính kèm luôn được đọc và đưa vào ngữ cảnh cho agent, bất kể chế độ Input."},
    "schedtask.hint_links": {
        "en": "Each URL is fetched (best-effort) and its text content given to the agent as context.",
        "ja": "各URLを取得し（ベストエフォート）、テキストをコンテキストとして渡します。",
        "vi": "Mỗi link được tải nội dung (khi có thể) và đưa vào ngữ cảnh cho agent."},
    "schedtask.f_prev_task": {"en": "Previous task", "ja": "前タスク", "vi": "Task trước"},
    "schedtask.g_output": {"en": "Output", "ja": "出力", "vi": "Đầu ra"},
    "schedtask.f_output_mode": {"en": "Output mode", "ja": "出力モード", "vi": "Chế độ output"},
    "schedtask.g_dependency": {"en": "Dependency / Next task", "ja": "依存 / 次タスク", "vi": "Phụ thuộc / Task tiếp theo"},
    "schedtask.f_next_task": {"en": "Next task", "ja": "次タスク", "vi": "Task tiếp theo"},
    "schedtask.f_run_next": {"en": "Run next task", "ja": "次タスクの実行", "vi": "Chạy task tiếp theo"},
    "schedtask.runnext.none": {"en": "Don't run next task", "ja": "実行しない", "vi": "Không chạy task sau"},
    "schedtask.runnext.run_after_success": {
        "en": "Run after success", "ja": "成功後に実行", "vi": "Chạy khi task này thành công"},
    "schedtask.runnext.run_always": {"en": "Always run", "ja": "常に実行", "vi": "Luôn chạy (kể cả lỗi)"},
    "schedtask.runnext.run_after_manual_confirm": {
        "en": "Wait for my confirmation", "ja": "手動確認後に実行", "vi": "Chờ tôi xác nhận rồi chạy"},
    "schedtask.pass_output": {
        "en": "Use this task's output as next task's input",
        "ja": "このタスクの出力を次タスクの入力にする",
        "vi": "Dùng output task này làm input task sau"},
    "schedtask.next_paused_warn": {
        "en": "The selected next task is paused — it will be skipped when this task finishes.",
        "ja": "選択した次タスクは一時停止中のため、完了時にスキップされます。",
        "vi": "Task tiếp theo đang tạm dừng — sẽ bị bỏ qua khi task này chạy xong."},
    "schedtask.none": {"en": "(none)", "ja": "（なし）", "vi": "(không)"},
    "schedtask.g_execution": {"en": "Execution", "ja": "実行設定", "vi": "Thực thi"},
    "schedtask.f_retry": {"en": "Max retry", "ja": "最大リトライ", "vi": "Số lần thử lại"},
    "schedtask.f_timeout": {"en": "Timeout", "ja": "タイムアウト", "vi": "Thời gian tối đa"},
    "schedtask.requires_approval": {
        "en": "Requires approval (scheduler will NOT auto-run; waits for Run now)",
        "ja": "承認必須（自動実行されず、手動のRun nowを待ちます）",
        "vi": "Cần phê duyệt (không tự chạy theo lịch; chờ bấm Chạy ngay)"},
    "schedtask.notify_ok": {"en": "Notify Teams on complete", "ja": "完了時にTeams通知", "vi": "Báo Teams khi xong"},
    "schedtask.notify_err": {"en": "Notify Teams on error", "ja": "エラー時にTeams通知", "vi": "Báo Teams khi lỗi"},
    "schedtask.title_required": {"en": "Please enter a title.", "ja": "タイトルを入力してください。", "vi": "Vui lòng nhập tiêu đề."},
    # AI create dialog
    "schedtask.ai_desc_label": {
        "en": "Describe what you want to automate:", "ja": "自動化したい内容を記述:",
        "vi": "Mô tả việc bạn muốn tự động hoá:"},
    "schedtask.ai_desc_ph": {
        "en": "e.g. Every Monday 9:00, use Code to read new CAE data and build a markdown report, then have Cowork draft a team email from it.",
        "ja": "例: 毎週月曜9時、CodeでCAEデータを読み込みレポート作成、その後Coworkでメール下書きを作成。",
        "vi": "vd: Mỗi thứ 2 lúc 9h, dùng Code đọc dữ liệu CAE mới tạo báo cáo markdown, sau đó Cowork soạn email draft gửi team."},
    "schedtask.ai_generate": {"en": "Generate plan", "ja": "プランを生成", "vi": "Tạo kế hoạch"},
    "schedtask.ai_generating": {"en": "Generating…", "ja": "生成中…", "vi": "Đang tạo…"},
    "schedtask.ai_preview_label": {
        "en": "Preview (nothing is created until you confirm):",
        "ja": "プレビュー（確認するまで作成されません）:",
        "vi": "Xem trước (chưa tạo gì cho tới khi bạn xác nhận):"},
    "schedtask.ai_confirm": {"en": "Create tasks", "ja": "タスクを作成", "vi": "Tạo các task"},
    "schedtask.tab_ai": {"en": "AI gen task", "ja": "AIタスク生成", "vi": "Tạo task bằng AI"},
    "schedtask.tab_import": {"en": "Import", "ja": "インポート", "vi": "Nhập"},
    "schedtask.export_template_btn": {
        "en": "Create Excel template…", "ja": "Excelテンプレートを作成…",
        "vi": "Tạo template Excel…"},
    "schedtask.import_pick_btn": {"en": "Choose file…", "ja": "ファイルを選択…", "vi": "Chọn file…"},
    "schedtask.drop_hint": {
        "en": "…or drag & drop the filled .xlsx here",
        "ja": "…または記入済みの .xlsx をここにドラッグ＆ドロップ",
        "vi": "…hoặc kéo-thả file .xlsx đã điền vào đây"},
    "schedtask.f_depends_on": {
        "en": "Wait for tasks (all must be Done)", "ja": "待機するタスク（全てDone必須）",
        "vi": "Chờ các task (tất cả phải Done)"},
    "schedtask.gen_desc_tooltip": {
        "en": "Generate the Prompt from this description (the title is not used)",
        "ja": "この説明からプロンプトを生成（タイトルは使用しません）",
        "vi": "Sinh Prompt từ mô tả này (không dùng tiêu đề)"},
    "schedtask.gen_needs_description": {
        "en": "Enter a description first — the Prompt is generated from it.",
        "ja": "先に説明を入力してください。プロンプトは説明から生成されます。",
        "vi": "Hãy nhập mô tả trước — Prompt được sinh ra từ mô tả."},
    # ---- dashboard_tab.py ------------------------------------------------
    "dashboard.title": {"en": "Dashboard — token usage & cost", "ja": "Dashboard — トークン使用量とコスト",
                         "vi": "Dashboard — token & chi phí"},
    "dashboard.period.today": {"en": "Today", "ja": "今日", "vi": "Hôm nay"},
    "dashboard.period.week": {"en": "Last 7 days", "ja": "過去7日", "vi": "7 ngày qua"},
    "dashboard.period.month": {"en": "Last 30 days", "ja": "過去30日", "vi": "30 ngày qua"},
    "dashboard.period.all": {"en": "All time", "ja": "全期間", "vi": "Toàn bộ"},
    "dashboard.source_all": {"en": "All tasks/sessions", "ja": "全タスク/セッション", "vi": "Mọi task/phiên"},
    "dashboard.refresh_tooltip": {"en": "Refresh now", "ja": "今すぐ更新", "vi": "Làm mới ngay"},
    "dashboard.card_total": {"en": "Total tokens", "ja": "合計トークン", "vi": "Tổng token"},
    "dashboard.card_in": {"en": "Input", "ja": "入力", "vi": "Input"},
    "dashboard.card_out": {"en": "Output", "ja": "出力", "vi": "Output"},
    "dashboard.card_cache": {"en": "Cache", "ja": "キャッシュ", "vi": "Cache"},
    "dashboard.card_cost": {"en": "Cost", "ja": "コスト", "vi": "Chi phí"},
    "dashboard.card_turns": {"en": "{n} turns", "ja": "{n} ターン", "vi": "{n} lượt"},
    "dashboard.prices_label": {
        "en": "Unit price (USD / 1M tokens):", "ja": "単価 (USD / 100万トークン):",
        "vi": "Đơn giá (USD / 1 triệu token):"},
    "dashboard.price_in": {"en": "In", "ja": "入力", "vi": "In"},
    "dashboard.price_out": {"en": "Out", "ja": "出力", "vi": "Out"},
    "dashboard.price_cache": {"en": "Cache", "ja": "キャッシュ", "vi": "Cache"},
    "dashboard.habits_title": {
        "en": "Usage habits overview", "ja": "利用傾向の概要", "vi": "Tổng quan thói quen sử dụng"},
    "dashboard.chart_title": {"en": "Tokens / cost over time", "ja": "トークン／コスト推移",
                              "vi": "Token / chi phí theo thời gian"},
    "dashboard.strategy_btn": {"en": "Apply saving strategy", "ja": "節約戦略を適用",
                               "vi": "Áp dụng chiến lược tiết kiệm"},
    "dashboard.strategy_tooltip": {
        "en": "Apply the AI's cost-saving strategy: auto-compress earlier + digest context before each turn.",
        "ja": "AIの節約戦略を適用：早めに自動圧縮＋各ターン前にコンテキストを要約。",
        "vi": "Áp dụng chiến lược tiết kiệm của AI: tự động nén sớm hơn + tóm gọn ngữ cảnh trước mỗi lượt."},
    "dashboard.strategy_title": {"en": "Apply saving strategy", "ja": "節約戦略の適用",
                                 "vi": "Áp dụng chiến lược tiết kiệm"},
    "dashboard.strategy_confirm": {
        "en": "Turn on auto-compress (earlier, at 60%) and compress context before each turn to cut tokens?",
        "ja": "自動圧縮（60%で早めに）とターン前のコンテキスト圧縮を有効にしてトークンを削減しますか？",
        "vi": "Bật tự động nén (sớm hơn, ở 60%) và nén ngữ cảnh trước mỗi lượt để giảm token?"},
    "dashboard.strategy_applied": {
        "en": "Saving strategy applied: auto-compress on, compress-before-send on.",
        "ja": "節約戦略を適用：自動圧縮ON、送信前圧縮ON。",
        "vi": "Đã áp dụng: bật tự động nén và nén trước khi gửi."},
    "dashboard.gran_day": {"en": "By day", "ja": "日別", "vi": "Theo ngày"},
    "dashboard.gran_week": {"en": "By week", "ja": "週別", "vi": "Theo tuần"},
    "dashboard.gran_month": {"en": "By month", "ja": "月別", "vi": "Theo tháng"},
    "dashboard.gran_year": {"en": "By year", "ja": "年別", "vi": "Theo năm"},
    "dashboard.ref_last_week": {"en": "Last week", "ja": "先週", "vi": "Tuần trước"},
    "dashboard.ref_last_month": {"en": "Last month", "ja": "先月", "vi": "Tháng trước"},
    "dashboard.ref_last_year": {"en": "Last year", "ja": "昨年", "vi": "Năm trước"},
    "usage.budget_title": {"en": "Budget", "ja": "予算", "vi": "Ngân sách"},
    "usage.budget_no_budget": {"en": "No budget set", "ja": "予算未設定", "vi": "Chưa đặt Budget"},
    "usage.budget_used_pct": {"en": "{pct}% used", "ja": "{pct}% 使用済み", "vi": "Đã dùng {pct}%"},
    "usage.budget_over_warning": {"en": "⚠ Over 85% of budget used",
                                  "ja": "⚠ 予算の85%以上を使用",
                                  "vi": "⚠ Đã dùng quá 85% Budget"},
    "usage.budget_apply_tooltip": {"en": "Set this as the budget (starts a fresh remaining-balance window)",
                                   "ja": "この金額を予算として設定（残高の計算を今から開始）",
                                   "vi": "Đặt số này làm Budget (tính số dư mới từ bây giờ)"},
    "usage.budget_spin_tooltip": {"en": "Enter the budget amount directly, then click ✓",
                                  "ja": "予算額を直接入力して ✓ をクリック",
                                  "vi": "Nhập Budget trực tiếp rồi bấm ✓"},
    "dashboard.chart_prev": {"en": "Previous period", "ja": "前の期間", "vi": "Kỳ trước"},
    "dashboard.chart_next": {"en": "Next period", "ja": "次の期間", "vi": "Kỳ sau"},
    "dashboard.metric_cost": {"en": "Cost", "ja": "コスト", "vi": "Chi phí"},
    "dashboard.metric_tokens": {"en": "Tokens", "ja": "トークン", "vi": "Token"},
    "dashboard.h_top": {"en": "Top token consumers (task/session)", "ja": "トークン消費上位（タスク/セッション）",
                         "vi": "Tiêu tốn token nhiều nhất (task/phiên)"},
    "dashboard.h_by_source": {"en": "By area", "ja": "領域別", "vi": "Theo khu vực"},
    "dashboard.h_avg": {"en": "Average per prompt", "ja": "1プロンプト平均", "vi": "Trung bình mỗi prompt"},
    "dashboard.h_busiest_day": {"en": "Busiest day", "ja": "最も使った日", "vi": "Ngày dùng nhiều nhất"},
    "dashboard.h_busiest_hour": {"en": "Busiest hour", "ja": "最も使う時間帯", "vi": "Khung giờ hay dùng"},
    "dashboard.no_data": {
        "en": "No usage recorded in this period yet — run a chat or a task first.",
        "ja": "この期間の使用記録はまだありません。チャットやタスクを実行してください。",
        "vi": "Chưa có dữ liệu sử dụng trong giai đoạn này — hãy chạy chat hoặc task trước."},
    # Lỗi hợp lệ hoá phụ thuộc/chuỗi task: ``core/tasks.py`` trả về KHOÁ, nơi
    # hiển thị mới gọi ``tr()`` (tầng core không biết ngôn ngữ đang chọn).
    "schedtask.err_self_wait": {
        "en": "A task cannot wait for itself.", "ja": "タスクは自分自身を待てません。",
        "vi": "Một task không thể chờ chính nó."},
    "schedtask.err_wait_cycle": {
        "en": "This would create a circular wait between tasks.",
        "ja": "タスク間で待ち合わせが循環してしまいます。",
        "vi": "Việc này sẽ tạo vòng chờ luẩn quẩn giữa các task."},
    "schedtask.err_self_chain": {
        "en": "A task cannot chain to itself.", "ja": "タスクは自分自身に連結できません。",
        "vi": "Một task không thể nối tiếp chính nó."},
    "schedtask.err_next_missing": {
        "en": "Next task does not exist.", "ja": "次のタスクが存在しません。",
        "vi": "Task kế tiếp không tồn tại."},
    "schedtask.err_chain_cycle": {
        "en": "This would create a circular task chain.",
        "ja": "タスクの連結が循環してしまいます。",
        "vi": "Việc này sẽ tạo chuỗi task luẩn quẩn."},
}
