"""Chuỗi hiển thị — phần composer.

Cắt ra từ ``i18n.py``: một dict 3.000 dòng không mở nổi để sửa một chữ.
Cắt theo mốc phân đoạn có sẵn, nên mỗi cụm vẫn là các màn đi liền nhau.
``i18n.py`` gộp tất cả lại thành ``STRINGS``.
"""
from __future__ import annotations

from typing import Dict

STRINGS: Dict[str, Dict[str, str]] = {
    "chatpanel.agent_tooltip": {
        "en": "Model/agent for THIS tab — independent of the other tab",
        "ja": "このタブ専用のモデル/エージェント（他のタブとは独立）",
        "vi": "Model/agent riêng cho tab này — độc lập với tab kia"},
    "chatpanel.agent_list_error": {
        "en": "Could not load the model list: {err}", "ja": "モデル一覧を読み込めませんでした: {err}",
        "vi": "Không tải được danh sách model: {err}"},
    "chatpanel.compress_btn": {"en": "Compress", "ja": "圧縮", "vi": "Nén"},
    "chatpanel.compress_tooltip": {
        "en": "Compress the conversation: trim old history to cut tokens (avoid exceeding the context limit)",
        "ja": "会話を圧縮：古い履歴を減らしてトークンを削減（コンテキスト上限超過を回避）",
        "vi": "Nén hội thoại: bỏ bớt lịch sử cũ để giảm token (tránh lỗi vượt giới hạn context)"},
    "chatpanel.files_header": {"en": "Files", "ja": "ファイル", "vi": "Files"},
    "chatpanel.collapse_files_tooltip": {
        "en": "Collapse the Files panel", "ja": "ファイルパネルを折りたたむ", "vi": "Thu gọn bảng Files"},
    "chatpanel.expand_files_tooltip": {
        "en": "Click to expand the Files panel", "ja": "クリックしてファイルパネルを展開",
        "vi": "Bấm để mở lại bảng Files"},
    "chatpanel.compress_busy": {
        "en": "Running — stop or wait before compressing.", "ja": "実行中です。停止するか完了を待ってから圧縮してください。",
        "vi": "Đang chạy — dừng hoặc đợi xong rồi hãy nén."},
    "chatpanel.compress_short": {
        "en": "Conversation is already short — no need to compress.",
        "ja": "会話はすでに短いため圧縮の必要はありません。",
        "vi": "Hội thoại đã ngắn — không cần nén."},
    "chatpanel.compress_done": {
        "en": "Compressed: dropped {cut} old messages, kept the last {keep} turns to cut tokens.",
        "ja": "圧縮しました：古いメッセージ{cut}件を削除し、直近{keep}ターンを保持してトークンを削減。",
        "vi": "Đã nén hội thoại: bỏ {cut} tin cũ, giữ {keep} lượt gần nhất để giảm token."},
    "chatpanel.compress_reduced": {
        "en": "Compressed to {pct}% of the original ({n} old messages digested).",
        "ja": "元の {pct}% まで圧縮（古いメッセージ {n} 件を要約）。",
        "vi": "Đã nén còn {pct}% so với ban đầu ({n} tin cũ được tóm gọn)."},
    "chatpanel.compress_digest_header": {
        "en": "Compressed summary of {n} earlier messages",
        "ja": "以前のメッセージ {n} 件の要約",
        "vi": "Tóm tắt nén của {n} tin nhắn trước đó"},
    "chatpanel.delete_confirm_title": {"en": "Delete message", "ja": "メッセージを削除", "vi": "Xóa tin nhắn"},
    "chatpanel.delete_confirm_files": {
        "en": "Delete this message and its {n} input/output file(s)?\n\n{preview}",
        "ja": "このメッセージと入出力ファイル{n}件を削除しますか？\n\n{preview}",
        "vi": "Xóa tin nhắn này và {n} tệp input/output của nó?\n\n{preview}"},
    "chatpanel.delete_confirm_plain": {"en": "Delete this message?", "ja": "このメッセージを削除しますか？", "vi": "Xóa tin nhắn này?"},
    "chatpanel.delete_done": {
        "en": "Message and its files deleted.", "ja": "メッセージとファイルを削除しました。",
        "vi": "Đã xóa tin nhắn và các tệp liên quan."},
    "chatpanel.working": {"en": "{name}: working…", "ja": "{name}: 処理中…", "vi": "{name}: đang xử lý…"},
    "chatpanel.done": {"en": "{name}: done.", "ja": "{name}: 完了。", "vi": "{name}: xong."},
    "chatpanel.failed": {"en": "{name}: error.", "ja": "{name}: エラー。", "vi": "{name}: lỗi."},
    "chatpanel.stopping": {"en": "{name}: stopping…", "ja": "{name}: 停止中…", "vi": "{name}: đang dừng…"},
    "chatpanel.attach_limit": {
        "en": "Max {n} attachments — extra files were skipped.",
        "ja": "添付は最大{n}件です。超過分はスキップされました。",
        "vi": "Tối đa {n} tệp đính kèm — bỏ qua phần dư."},
    "chatpanel.attached_hint": {"en": "Attached: {names}", "ja": "添付: {names}", "vi": "Đã đính kèm: {names}"},
    "chatpanel.skills_updated": {"en": "Skills updated.", "ja": "スキルを更新しました。", "vi": "Đã cập nhật skill."},
    "chatpanel.new_files_detected": {
        "en": "New file(s) detected in output folder: {names} ({n} file(s)). They will be auto-loaded as input on the next message.",
        "ja": "出力フォルダに新しいファイルを検出しました: {names} ({n}ファイル)。次のメッセージで自動的に入力として読み込まれます。",
        "vi": "Phát hiện tệp mới trong thư mục đầu ra: {names} ({n} tệp). Chúng sẽ được tự động tải làm dữ liệu đầu vào ở tin nhắn tiếp theo.",
    },
    # ---- composer.py -----------------------------------------------
    "composer.placeholder_default": {
        "en": "Type a message…  (Enter to send, Shift+Enter for newline)",
        "ja": "メッセージを入力…（Enterで送信、Shift+Enterで改行）",
        "vi": "Nhập tin nhắn…  (Enter để gửi, Shift+Enter xuống dòng)"},
    "composer.placeholder_cowork": {
        "en": "Type a request or attach a file to process…  (Enter to send)",
        "ja": "依頼内容を入力するかファイルを添付…（Enterで送信）",
        "vi": "Nhập yêu cầu hoặc đính kèm tệp để xử lí…  (Enter để gửi)"},
    "composer.placeholder_code": {
        "en": "Assign a task to the Code agent…  (Enter to send)",
        "ja": "Code エージェントにタスクを指示…（Enterで送信）",
        "vi": "Giao việc cho Code agent…  (Enter để gửi)"},
    "composer.queue_label": {"en": "Queue ({n})", "ja": "キュー ({n})", "vi": "Hàng đợi ({n})"},
    "composer.queue_tooltip": {
        "en": "Double-click to remove a queued message", "ja": "ダブルクリックでキューから削除",
        "vi": "Nhấp đúp để xoá một tin nhắn khỏi hàng đợi"},
    "composer.attachments_label": {"en": "Attachments ({n})", "ja": "添付ファイル ({n})", "vi": "Tệp đính kèm ({n})"},
    "composer.attachments_tooltip": {
        "en": "Click on a chip to remove a file added by mistake",
        "ja": "誤って追加したファイルは で削除できます",
        "vi": "Bấm trên thẻ để gỡ tệp đính kèm nhầm"},
    "composer.remove_tooltip": {
        "en": "Remove this file (added by mistake)", "ja": "このファイルを削除（誤って追加）",
        "vi": "Gỡ tệp này (đính kèm nhầm)"},
    "composer.attach_btn_tooltip": {
        "en": "Attach images or files (you can also paste or drag them in)",
        "ja": "画像やファイルを添付（貼り付け・ドラッグも可）",
        "vi": "Đính kèm ảnh hoặc tệp (có thể dán hoặc kéo-thả vào)"},
    "composer.send": {"en": "Send", "ja": "送信", "vi": "Gửi"},
    "composer.queue_btn": {"en": "Queue", "ja": "キューに追加", "vi": "Thêm vào hàng đợi"},
    "composer.stop": {"en": "Stop", "ja": "停止", "vi": "Dừng"},
    "composer.attach_dialog_title": {"en": "Attach files / images", "ja": "ファイル/画像を添付", "vi": "Đính kèm tệp / ảnh"},
    "composer.attach_dialog_filter": {
        "en": "Files (*.*);;Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp)",
        "ja": "ファイル (*.*);;画像 (*.png *.jpg *.jpeg *.gif *.bmp *.webp)",
        "vi": "Tệp (*.*);;Ảnh (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"},
    "composer.no_skills": {"en": "   (no skills yet)", "ja": "   （スキルはまだありません）", "vi": "   (chưa có skill nào)"},
    "composer.no_agents": {"en": "   (no agents found)", "ja": "   （エージェントが見つかりません）", "vi": "   (không tìm thấy agent)"},
    "composer.manage_skills": {"en": "Manage skills…", "ja": "スキルを管理…", "vi": "Quản lý skill…"},

    # ---- schedule_task_tab.py / task_editor_dialog.py -------------------
    "schedtask.title": {"en": "Schedule Task", "ja": "Schedule Task", "vi": "Schedule Task"},
    "schedtask.view.kanban": {"en": "Kanban", "ja": "Kanban", "vi": "Kanban"},
    "schedtask.view.calendar": {"en": "Calendar", "ja": "カレンダー", "vi": "Lịch"},
    "schedtask.no_title": {"en": "(untitled)", "ja": "（無題）", "vi": "(chưa có tên)"},
    "schedtask.cal_today": {"en": "Today", "ja": "今日", "vi": "Hôm nay"},
    "schedtask.cal_prev": {"en": "Previous", "ja": "前へ", "vi": "Trước"},
    "schedtask.cal_next": {"en": "Next", "ja": "次へ", "vi": "Sau"},
    "schedtask.cal_gran.week": {"en": "Week", "ja": "週", "vi": "Tuần"},
    "schedtask.cal_gran.month": {"en": "Month", "ja": "月", "vi": "Tháng"},
    "schedtask.cal_gran.year": {"en": "Year", "ja": "年", "vi": "Năm"},
    "schedtask.cal_weekday.mon": {"en": "Mon", "ja": "月", "vi": "T2"},
    "schedtask.cal_weekday.tue": {"en": "Tue", "ja": "火", "vi": "T3"},
    "schedtask.cal_weekday.wed": {"en": "Wed", "ja": "水", "vi": "T4"},
    "schedtask.cal_weekday.thu": {"en": "Thu", "ja": "木", "vi": "T5"},
    "schedtask.cal_weekday.fri": {"en": "Fri", "ja": "金", "vi": "T6"},
    "schedtask.cal_weekday.sat": {"en": "Sat", "ja": "土", "vi": "T7"},
    "schedtask.cal_weekday.sun": {"en": "Sun", "ja": "日", "vi": "CN"},
    "schedtask.cal_month_count": {"en": "{month} — {n} task(s)", "ja": "{month} — {n} 件",
                                  "vi": "{month} — {n} task"},
    "schedtask.search_ph": {"en": "Search tasks…", "ja": "タスクを検索…", "vi": "Tìm task…"},
    "schedtask.filter_all": {"en": "All types", "ja": "すべての種類", "vi": "Mọi loại"},
    "schedtask.add_btn": {"en": "Add Task", "ja": "タスク追加", "vi": "Thêm Task"},
    "schedtask.ai_btn": {"en": "AI Create Task", "ja": "AIでタスク作成", "vi": "AI tạo Task"},
    "schedtask.ai_tooltip": {
        "en": "Describe what you want in natural language — AI proposes tasks/schedule/chain, you confirm before anything is created.",
        "ja": "自然文で説明すると、AIがタスク・スケジュール・チェーンを提案します。確認後に作成されます。",
        "vi": "Mô tả bằng ngôn ngữ tự nhiên — AI đề xuất task/lịch/chuỗi, bạn xác nhận rồi mới tạo."},
    "schedtask.no_tasks": {"en": "No tasks", "ja": "タスクなし", "vi": "No tasks"},
    "schedtask.no_schedule": {"en": "No schedule", "ja": "スケジュールなし", "vi": "Chưa đặt lịch"},
    "schedtask.last_success": {"en": "Last: Success", "ja": "前回: 成功", "vi": "Lần cuối: Thành công"},
    "schedtask.last_failed": {"en": "Last: Failed", "ja": "前回: 失敗", "vi": "Lần cuối: Lỗi"},
    "schedtask.last_never": {"en": "Last: not run", "ja": "前回: 未実行", "vi": "Lần cuối: chưa chạy"},
    "schedtask.status.backlog": {"en": "Backlog", "ja": "Backlog", "vi": "Backlog"},
    "schedtask.status.scheduled": {"en": "Scheduled", "ja": "Scheduled", "vi": "Scheduled"},
    "schedtask.status.running": {"en": "Running", "ja": "Running", "vi": "Running"},
    "schedtask.status.waiting_input": {"en": "Waiting Input", "ja": "Waiting Input", "vi": "Waiting Input"},
    "schedtask.status.done": {"en": "Done", "ja": "Done", "vi": "Done"},
    "schedtask.status.failed": {"en": "Failed", "ja": "Failed", "vi": "Failed"},
    "schedtask.status.paused": {"en": "Paused", "ja": "Paused", "vi": "Paused"},
    "schedtask.type.cowork": {"en": "Cowork", "ja": "Cowork", "vi": "Cowork"},
    "schedtask.type.co4e_code": {"en": "Code", "ja": "Code", "vi": "Code"},
    "schedtask.type.flow": {"en": "Flow", "ja": "Flow", "vi": "Flow"},
    "schedtask.type.script": {"en": "Script", "ja": "Script", "vi": "Script"},
    "schedtask.type.manual": {"en": "Manual", "ja": "Manual", "vi": "Manual"},
    "schedtask.priority.low": {"en": "Low", "ja": "低", "vi": "Thấp"},
    "schedtask.priority.medium": {"en": "Medium", "ja": "中", "vi": "Trung bình"},
    "schedtask.priority.high": {"en": "High", "ja": "高", "vi": "Cao"},
    "schedtask.priority.critical": {"en": "Critical", "ja": "最重要", "vi": "Khẩn cấp"},
    "schedtask.menu_run": {"en": "Run now", "ja": "今すぐ実行", "vi": "Chạy ngay"},
    "schedtask.menu_edit": {"en": "Edit task", "ja": "タスクを編集", "vi": "Sửa task"},
    "schedtask.menu_duplicate": {"en": "Duplicate task", "ja": "タスクを複製", "vi": "Nhân bản task"},
    "schedtask.menu_pause": {"en": "Pause", "ja": "一時停止", "vi": "Tạm dừng"},
    "schedtask.menu_resume": {"en": "Resume", "ja": "再開", "vi": "Tiếp tục"},
    "schedtask.menu_logs": {"en": "View logs", "ja": "ログを表示", "vi": "Xem log"},
    "schedtask.menu_history": {"en": "Run history…", "ja": "実行履歴…", "vi": "Lịch sử chạy…"},
    "schedtask.hist_hint": {
        "en": "Double-click a row to open that run's artifact folder.",
        "ja": "行をダブルクリックすると、その実行のフォルダを開きます。",
        "vi": "Double-click một dòng để mở thư mục artifact của lần chạy đó."},
    "schedtask.hist_col_time": {"en": "Finished at", "ja": "完了時刻", "vi": "Hoàn thành lúc"},
    "schedtask.hist_col_status": {"en": "Status", "ja": "状態", "vi": "Trạng thái"},
    "schedtask.hist_col_run": {"en": "Run ID", "ja": "実行ID", "vi": "Run ID"},
    "schedtask.hist_col_error": {"en": "Error", "ja": "エラー", "vi": "Lỗi"},
    "schedtask.menu_create_next": {
        "en": "Create next task from output", "ja": "出力から次タスクを作成",
        "vi": "Tạo task tiếp theo từ output"},
    "schedtask.menu_delete": {"en": "Delete task", "ja": "タスクを削除", "vi": "Xóa task"},
    "schedtask.delete_confirm": {"en": "Delete '{title}'?", "ja": "「{title}」を削除しますか？", "vi": "Xóa '{title}'?"},
    "schedtask.menu_delete_selected": {"en": "Delete {n} selected", "ja": "選択した{n}件を削除", "vi": "Xóa {n} task đã chọn"},
    "schedtask.delete_multi_confirm": {
        "en": "Delete {n} selected tasks? This cannot be undone.",
        "ja": "選択した{n}件のタスクを削除しますか？元に戻せません。",
        "vi": "Xóa {n} task đã chọn? Không thể hoàn tác."},
    "schedtask.msg_created": {"en": "Task created.", "ja": "タスクを作成しました。", "vi": "Đã tạo task."},
    "schedtask.msg_running": {"en": "Running: {title}", "ja": "実行中: {title}", "vi": "Đang chạy: {title}"},
    "schedtask.msg_manual_norun": {
        "en": "Manual tasks are for tracking only — they don't execute.",
        "ja": "Manualタスクは管理用のため実行されません。",
        "vi": "Task Manual chỉ để quản lý — không tự chạy."},
    "schedtask.msg_no_scheduler": {"en": "Scheduler not available.", "ja": "スケジューラーが利用できません。", "vi": "Scheduler chưa sẵn sàng."},
    "schedtask.msg_ai_created": {"en": "Created {n} task(s) from AI plan.", "ja": "AI提案から{n}件のタスクを作成しました。", "vi": "Đã tạo {n} task từ đề xuất AI."},
    "schedtask.no_runs_yet": {"en": "This task has not run yet.", "ja": "このタスクはまだ実行されていません。", "vi": "Task này chưa chạy lần nào."},
    "schedtask.next_of": {"en": "Next: {title}", "ja": "次: {title}", "vi": "Tiếp theo: {title}"},
    # editor
    "schedtask.editor_title_new": {"en": "Add Task", "ja": "タスク追加", "vi": "Thêm Task"},
    "schedtask.editor_title_edit": {"en": "Edit Task", "ja": "タスク編集", "vi": "Sửa Task"},
    "schedtask.f_title": {"en": "Title", "ja": "タイトル", "vi": "Tiêu đề"},
    "schedtask.f_desc": {"en": "Description", "ja": "説明", "vi": "Mô tả"},
    "schedtask.f_type": {"en": "Task type", "ja": "タスク種別", "vi": "Loại task"},
    "schedtask.f_workspace": {"en": "Workspace", "ja": "ワークスペース", "vi": "Workspace"},
    "schedtask.no_workspace": {"en": "— No workspace —", "ja": "— ワークスペースなし —", "vi": "— Không có workspace —"},
    "schedtask.f_agent": {"en": "Agent", "ja": "エージェント", "vi": "Agent"},
    "schedtask.no_agent": {"en": "— No agent preset —", "ja": "— エージェントなし —", "vi": "— Không dùng agent —"},
    "schedtask.f_provider": {"en": "Provider", "ja": "プロバイダー", "vi": "Provider"},
    "schedtask.provider_default": {
        "en": "— Default (Settings) —", "ja": "— 既定（設定）—", "vi": "— Mặc định (Settings) —"},
    "schedtask.f_model": {"en": "Model", "ja": "モデル", "vi": "Model"},
    "schedtask.model_placeholder": {
        "en": "Default model (leave blank to use Settings)",
        "ja": "既定のモデル（空欄で設定を使用）",
        "vi": "Model mặc định (để trống dùng Settings)"},
    "schedtask.load_models_tooltip": {
        "en": "Fetch this provider's available models",
        "ja": "このプロバイダーの利用可能なモデルを取得",
        "vi": "Tải danh sách model của provider này"},
    "schedtask.load_models_empty": {
        "en": "No models could be loaded. Check the provider/API key in Settings.",
        "ja": "モデルを取得できませんでした。設定のプロバイダー/APIキーを確認してください。",
        "vi": "Không tải được model nào. Kiểm tra provider/API key trong Settings."},
    "schedtask.f_skill": {"en": "Skill", "ja": "スキル", "vi": "Skill"},
    "schedtask.no_skill": {"en": "— No skill —", "ja": "— スキルなし —", "vi": "— Không dùng skill —"},
    "schedtask.hint_provider": {
        "en": "Which AI provider runs this task. Leave as Default to use the machine's Settings provider.",
        "ja": "このタスクを実行するAIプロバイダー。既定のままにすると設定のプロバイダーを使用します。",
        "vi": "Provider AI chạy task này. Để Mặc định để dùng provider trong Settings."},
    "schedtask.hint_model": {
        "en": "Model to run this task. Leave blank to use the provider's Settings model; click the button to load the real list.",
        "ja": "このタスクを実行するモデル。空欄で設定のモデルを使用。ボタンで実際の一覧を取得します。",
        "vi": "Model chạy task này. Để trống dùng model trong Settings; bấm nút để tải danh sách thực."},
    "schedtask.hint_skill": {
        "en": "Apply a saved skill's instructions to this task's run (its guidance is prepended to the prompt).",
        "ja": "保存済みスキルの指示をこのタスクの実行に適用します（プロンプトの先頭に追加されます）。",
        "vi": "Áp dụng hướng dẫn của một skill đã lưu vào lần chạy task này (được thêm vào đầu prompt)."},
    "schedtask.hint_workspace": {
        "en": "The project/workspace this task's agent runs in — its sandbox folder and shared instructions apply.",
        "ja": "このタスクのエージェントが実行されるプロジェクト/ワークスペース。そのサンドボックスフォルダと共有指示が適用されます。",
        "vi": "Project/workspace mà agent của task này sẽ chạy trong đó — áp dụng sandbox và hướng dẫn chung của project."},
    "schedtask.f_priority": {"en": "Priority", "ja": "優先度", "vi": "Độ ưu tiên"},
    "schedtask.f_status": {"en": "Status", "ja": "ステータス", "vi": "Trạng thái"},
    "schedtask.f_script": {"en": "Script command", "ja": "スクリプトコマンド", "vi": "Lệnh script"},
    "schedtask.script_placeholder": {
        "en": "(script tasks only) e.g. python report.py", "ja": "（Scriptタスクのみ）例: python report.py",
        "vi": "(chỉ task Script) vd: python report.py"},
    # The title/description block at the top of the Task editor had no name
    # either — needed once the index had to list it.
    "schedtask.g_basic": {"en": "Basics", "ja": "基本", "vi": "Thông tin chung"},
    # The three steps the editor is split into: what to do, when, and what it
    # connects to. Each holds the same group boxes as before.
    "schedtask.step_content": {"en": "Content", "ja": "内容", "vi": "Nội dung"},
    "schedtask.step_schedule": {"en": "Schedule", "ja": "スケジュール", "vi": "Lịch chạy"},
    "schedtask.step_link": {"en": "Links", "ja": "連携", "vi": "Liên kết"},
    "schedtask.g_schedule": {"en": "Schedule Setup", "ja": "スケジュール設定", "vi": "Thiết lập lịch chạy"},
    "schedtask.sched_enable": {"en": "Enable schedule", "ja": "スケジュールを有効化", "vi": "Bật lịch chạy"},
    "schedtask.f_run_at": {"en": "Run at", "ja": "実行日時", "vi": "Chạy lúc"},
    "schedtask.f_repeat": {"en": "Repeat", "ja": "繰り返し", "vi": "Lặp lại"},
    "schedtask.repeat.none": {"en": "None (one-time)", "ja": "なし（1回のみ）", "vi": "Không (chạy 1 lần)"},
    "schedtask.repeat.daily": {"en": "Daily", "ja": "毎日", "vi": "Hằng ngày"},
    "schedtask.repeat.weekly": {"en": "Weekly", "ja": "毎週", "vi": "Hằng tuần"},
    "schedtask.repeat.monthly": {"en": "Monthly", "ja": "毎月", "vi": "Hằng tháng"},
    "schedtask.repeat.cron": {"en": "Cron expression", "ja": "Cron式", "vi": "Cron expression"},
    "schedtask.f_task_mode": {"en": "Task type", "ja": "タスク種別", "vi": "Loại task"},
    # Run kind: an AI agent vs a saved Co4E flow + multi-format import
    "schedtask.f_run_kind": {"en": "Run", "ja": "実行対象", "vi": "Chạy"},
    "schedtask.kind_agent": {"en": "AI agent (Cowork)", "ja": "AIエージェント（Cowork）",
                             "vi": "AI agent (Cowork)"},
    "schedtask.kind_flow": {"en": "Co4E flow", "ja": "Co4E フロー", "vi": "Co4E flow"},
    "schedtask.hint_run_kind": {
        "en": "AI agent = run one Cowork agent with the chosen model. Co4E flow = run a whole "
              "saved node-graph flow, step by step, in the sandbox.",
        "ja": "AIエージェント＝選択モデルで Cowork エージェントを1つ実行。Co4E フロー＝保存済みの"
              "ノードグラフ全体をサンドボックスで順に実行。",
        "vi": "AI agent = chạy một agent Cowork với model đã chọn. Co4E flow = chạy cả một flow "
              "node-graph đã lưu, tuần tự, trong sandbox."},
    "schedtask.f_flow": {"en": "Co4E flow", "ja": "Co4E フロー", "vi": "Co4E flow"},
    "schedtask.hint_flow": {
        "en": "Which saved Co4E flow this task runs (built-in or your own).",
        "ja": "このタスクが実行する保存済み Co4E フロー（組込み／自作）。",
        "vi": "Flow Co4E đã lưu mà task này sẽ chạy (có sẵn hoặc của bạn)."},
    "schedtask.flow_required": {
        "en": "Pick a Co4E flow to run (or switch Run to AI agent).",
        "ja": "実行する Co4E フローを選んでください（または実行対象を AI エージェントに）。",
        "vi": "Hãy chọn một flow Co4E để chạy (hoặc đổi Chạy sang AI agent)."},
    "schedtask.hint_task_mode": {
        "en": "Normal = runs once (or manually). Automation = a cronjob that repeats on a schedule "
              "(daily/weekly/monthly/cron). Switching to Automation reveals the recurrence options.",
        "ja": "通常＝1回（または手動）実行。自動化＝スケジュールで繰り返すCronジョブ（毎日/毎週/毎月/Cron）。"
              "自動化に切り替えると繰り返し設定が表示されます。",
        "vi": "Thông thường = chạy một lần (hoặc thủ công). Tự động = cronjob lặp theo lịch "
              "(ngày/tuần/tháng/cron). Chuyển sang Tự động sẽ hiện các tùy chọn lặp lại."},
    "schedtask.mode_normal": {
        "en": "Normal (one-time / manual)", "ja": "通常（1回 / 手動）",
        "vi": "Thông thường (một lần / thủ công)"},
    "schedtask.mode_automation": {
        "en": "Automation (cron / recurring)", "ja": "自動化（Cron / 繰り返し）",
        "vi": "Tự động (cronjob / lặp lại)"},
    "schedtask.f_cron": {"en": "Cron", "ja": "Cron", "vi": "Cron"},
    "schedtask.cron_sample_pick": {"en": "Sample ▾", "ja": "サンプル ▾", "vi": "Mẫu ▾"},
    "schedtask.cron_sample_tooltip": {
        "en": "Pick a ready-made schedule — it fills the cron box with correct syntax.",
        "ja": "定番スケジュールを選ぶと、正しい書式でCron欄に入力されます。",
        "vi": "Chọn một lịch mẫu — sẽ điền đúng cú pháp vào ô cron."},
    "schedtask.cron_s_weekday9": {"en": "Weekdays 9:00", "ja": "平日 9:00", "vi": "Ngày làm việc 9:00"},
    "schedtask.cron_s_daily8": {"en": "Every day 8:00", "ja": "毎日 8:00", "vi": "Mỗi ngày 8:00"},
    "schedtask.cron_s_weekly_mon": {"en": "Every Monday 9:00", "ja": "毎週月曜 9:00", "vi": "Thứ 2 hằng tuần 9:00"},
    "schedtask.cron_s_monthly1": {"en": "1st of month 9:00", "ja": "毎月1日 9:00", "vi": "Ngày 1 hằng tháng 9:00"},
    "schedtask.cron_s_every30m": {"en": "Every 30 minutes", "ja": "30分ごと", "vi": "Mỗi 30 phút"},
    "schedtask.cron_s_every2h": {"en": "Every 2 hours", "ja": "2時間ごと", "vi": "Mỗi 2 giờ"},
    "schedtask.cron_placeholder": {
        "en": "(repeat = Cron) e.g. 0 9 * * 1-5  — min hour day month weekday",
        "ja": "（繰り返し=Cron）例: 0 9 * * 1-5 — 分 時 日 月 曜日",
        "vi": "(khi lặp = Cron) vd: 0 9 * * 1-5 — phút giờ ngày tháng thứ"},
    "schedtask.cron_hint": {
        "en": "Only when Repeat = Cron. Fields: minute hour day-of-month month day-of-week "
              "(e.g. '0 9 * * 1-5' = 9:00 every weekday). Otherwise the run-time above is the "
              "daily/weekly/monthly notification time.",
        "ja": "繰り返し=Cronの場合のみ。書式: 分 時 日 月 曜日（例 '0 9 * * 1-5' = 平日9:00）。"
              "それ以外は上の実行時刻が毎日/毎週/毎月の通知時刻になります。",
        "vi": "Chỉ khi Lặp = Cron. Cú pháp: phút giờ ngày tháng thứ (vd '0 9 * * 1-5' = 9:00 các "
              "ngày trong tuần). Nếu không, giờ chạy ở trên là giờ thông báo hàng ngày/tuần/tháng."},
    "schedtask.cron_invalid": {
        "en": "Invalid cron expression: {err}", "ja": "Cron式が不正です: {err}",
        "vi": "Cron expression không hợp lệ: {err}"},
    "schedtask.cron_never_fires": {
        "en": "This cron expression never fires (within 2 years).",
        "ja": "このCron式は（2年以内に）一度も実行されません。",
        "vi": "Cron expression này không bao giờ chạy (trong vòng 2 năm)."},
    "schedtask.workdays_only": {"en": "Working days only (skip Sat/Sun)", "ja": "平日のみ（土日をスキップ）", "vi": "Chỉ ngày làm việc (bỏ T7/CN)"},
    "schedtask.skip_holidays": {
        "en": "Skip public holidays", "ja": "祝日をスキップ", "vi": "Bỏ qua ngày nghỉ lễ"},
    "schedtask.holiday_country": {"en": "Country:", "ja": "国:", "vi": "Quốc gia:"},
    "schedtask.f_notify": {"en": "Reminder", "ja": "リマインダー", "vi": "Nhắc nhở"},
    "schedtask.f_notify_email": {"en": "Send to", "ja": "送信先", "vi": "Gửi tới"},
    "schedtask.notify.none": {"en": "— No reminder —", "ja": "— リマインダーなし —", "vi": "— Không nhắc —"},
    "schedtask.notify.teams": {"en": "Teams (webhook)", "ja": "Teams（Webhook）", "vi": "Teams (webhook)"},
    "schedtask.notify.outlook": {
        "en": "Email via Outlook (this PC)", "ja": "Outlookでメール（このPC）",
        "vi": "Email qua Outlook (máy này)"},
}
