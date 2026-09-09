"""Chuỗi hiển thị — phần cowork_tab.

Cắt ra từ ``i18n.py``: một dict 3.000 dòng không mở nổi để sửa một chữ.
Cắt theo mốc phân đoạn có sẵn, nên mỗi cụm vẫn là các màn đi liền nhau.
``i18n.py`` gộp tất cả lại thành ``STRINGS``.
"""
from __future__ import annotations

from typing import Dict

STRINGS: Dict[str, Dict[str, str]] = {
    "dashboard.estimated_note": {
        "en": "~{pct}% of turns are estimated (~4 chars/token) — the gateway didn't report exact usage.",
        "ja": "約{pct}%のターンは推定値（約4文字/トークン）です。",
        "vi": "~{pct}% lượt là ước tính (~4 ký tự/token) — gateway không trả về usage chính xác."},
    "dashboard.ai_analyze_btn": {"en": "AI analyze", "ja": "AI分析", "vi": "AI phân tích"},
    "dashboard.ai_analyzing": {"en": "Analyzing…", "ja": "分析中…", "vi": "Đang phân tích…"},
    "dashboard.ai_analyze_tooltip": {
        "en": "AI reviews the aggregated numbers (never your prompt contents) and suggests how to prompt better and spend fewer tokens.",
        "ja": "集計値のみをAIがレビューし（プロンプト内容は送信しません）、トークン削減のコツを提案します。",
        "vi": "AI xem các con số tổng hợp (không gửi nội dung prompt) và gợi ý cách viết prompt tốt hơn, tốn ít token hơn."},
    "dashboard.ai_advice_title": {
        "en": "AI recommendations", "ja": "AIの提案", "vi": "Khuyến nghị từ AI"},
    "dashboard.period_tooltip": {
        "en": "Time range for all numbers on this page.", "ja": "このページ全体の集計期間。",
        "vi": "Khoảng thời gian tính mọi con số trên trang này."},
    "dashboard.source_tooltip": {
        "en": "Filter by one task/session, or all.", "ja": "タスク/セッション単位で絞り込み。",
        "vi": "Lọc theo 1 task/phiên, hoặc tất cả."},
    "dashboard.currency_tooltip": {
        "en": "Display currency (rates: fixed USD→VND/JPY, editable in config).",
        "ja": "表示通貨（USD→VND/JPYの固定レート、configで変更可）。",
        "vi": "Tiền tệ hiển thị (tỉ giá USD→VND/JPY cố định, sửa được trong config)."},
    "dashboard.price_in_tooltip": {
        "en": "USD per 1M input tokens (your gateway's price).",
        "ja": "入力100万トークンあたりのUSD単価。", "vi": "USD cho 1 triệu token input (giá của gateway bạn dùng)."},
    "dashboard.price_out_tooltip": {
        "en": "USD per 1M output tokens.", "ja": "出力100万トークンあたりのUSD単価。",
        "vi": "USD cho 1 triệu token output."},
    "dashboard.price_cache_tooltip": {
        "en": "USD per 1M cached tokens.", "ja": "キャッシュ100万トークンあたりのUSD単価。",
        "vi": "USD cho 1 triệu token cache."},
    # ---- cowork_tab.py -------------------------------------------------
    "cowork.title": {"en": "Cowork", "ja": "Cowork", "vi": "Cowork"},
    "cowork.skills_btn": {"en": "Skills", "ja": "スキル", "vi": "Skills"},
    "cowork.skills_tooltip": {
        "en": "Add / manage skills the agent follows (or type /skill).",
        "ja": "エージェントが従うスキルを追加/管理（/skill と入力も可）。",
        "vi": "Thêm/quản lý skill mà agent tuân theo (hoặc gõ /skill)."},
    "cowork.new_chat": {"en": "New chat", "ja": "新しいチャット", "vi": "Cuộc trò chuyện mới"},
    "cowork.assistant_title": {"en": "Internal Agent", "ja": "内部エージェント", "vi": "Internal Agent"},
    "cowork.project_label": {"en": "{name}", "ja": "{name}", "vi": "{name}"},
    "cowork.project_tooltip": {
        "en": "This thread belongs to project “{name}” — its shared instructions and workspace apply. Manage projects in the Workspace screen.",
        "ja": "このスレッドはプロジェクト「{name}」に属します — 共有指示とワークスペースが適用されます。プロジェクトはワークスペース画面で管理できます。",
        "vi": "Thread này thuộc project “{name}” — instructions chung và workspace của project được áp dụng. Quản lý project trong màn hình Workspace.",
    },
    "cowork.pick_folder_btn": {"en": "Local folder…",
                                "ja": "ローカルフォルダ…",
                                "vi": "Thư mục Local…"},
    "cowork.pick_folder_tooltip": {
        "en": "Save Cowork's output directly into a folder you choose, instead of "
              "auto-creating a new session folder under Output.",
        "ja": "Output 配下に新しいセッションフォルダを自動作成する代わりに、選んだフォルダに直接保存します。",
        "vi": "Lưu output của Cowork trực tiếp vào thư mục bạn chọn, thay vì tự tạo "
              "folder phiên mới trong Output."},
    "cowork.pick_folder_title": {"en": "Choose the Cowork output folder",
                                  "ja": "Cowork の出力フォルダを選択",
                                  "vi": "Chọn thư mục output cho Cowork"},

    # ---- code_tab.py -----------------------------------------------
    "code.title": {"en": "Code", "ja": "Code", "vi": "Code"},
    "code.files_header": {"en": "Files", "ja": "ファイル", "vi": "Files"},
    "code.collapse_file_panel": {
        "en": "Collapse the file panel", "ja": "ファイルパネルを折りたたむ", "vi": "Thu gọn bảng cây thư mục"},
    "code.expand_file_panel": {
        "en": "Click to expand the file panel", "ja": "クリックしてファイルパネルを展開",
        "vi": "Bấm để mở lại bảng cây thư mục"},
    "code.local_btn": {"en": "Local…", "ja": "ローカル…", "vi": "Local…"},
    "code.onedrive_btn": {"en": "OneDrive", "ja": "OneDrive", "vi": "OneDrive"},
    "code.onedrive_badge": {"en": "OneDrive", "ja": "OneDrive", "vi": "OneDrive"},
    "code.auto_run": {"en": "Auto-run", "ja": "自動実行", "vi": "Tự động"},
    "code.auto_run_tooltip": {
        "en": "On: agent writes files / runs commands automatically. Off: ask before each action.",
        "ja": "オン：エージェントが自動でファイル書き込み/コマンド実行。オフ：毎回確認します。",
        "vi": "Bật: agent tự ghi file/chạy lệnh. Tắt: hỏi xác nhận trước mỗi thao tác."},
    "code.skills_tooltip": {
        "en": "Add / set skills for the agent to follow (or type /skill).",
        "ja": "エージェントが従うスキルを追加/設定（/skill と入力も可）。",
        "vi": "Thêm/đặt skill mà agent tuân theo (hoặc gõ /skill)."},
    "code.flow_chk": {"en": "Flow", "ja": "フロー", "vi": "Flow"},
    "code.flow_chk_tooltip": {
        "en": "Enable the predefined Req→Demo flow feature (off by default).",
        "ja": "定義済みの Req→Demo フロー機能を有効化（初期値はオフ）。",
        "vi": "Bật tính năng Flow Req→Demo dựng sẵn (mặc định tắt)."},
    "code.flow_btn": {"en": "Flow Management", "ja": "フロー管理", "vi": "Flow Management"},
    "code.flow_btn_tooltip": {
        "en": "Build and run a multi-stage flow from requirement to demo.",
        "ja": "要件からデモまでの多段フローを作成・実行します。",
        "vi": "Xây dựng và chạy quy trình nhiều bước từ yêu cầu đến bản demo."},
    "code.new_session": {"en": "New session", "ja": "新しいセッション", "vi": "Phiên mới"},
    "code.cli_tooltip": {
        "en": "Open a terminal (CLI) at the current working folder",
        "ja": "現在の作業フォルダでターミナル(CLI)を開く",
        "vi": "Mở CLI (terminal) tại thư mục làm việc hiện tại"},
    "code.cli_not_found": {
        "en": "No terminal application was found on this system.",
        "ja": "このシステムにはターミナルアプリが見つかりませんでした。",
        "vi": "Không tìm thấy ứng dụng terminal nào trên máy này."},
    "code.skills_btn_count": {"en": "Skills ({n})", "ja": "スキル ({n})", "vi": "Skills ({n})"},
    "code.assistant_title": {"en": "Code agent", "ja": "Code エージェント", "vi": "Code agent"},
    "code.plan": {"en": "Plan", "ja": "プラン", "vi": "Plan"},
    "code.act": {"en": "Act", "ja": "実行", "vi": "Act"},
    "code.mode_toggle_tooltip": {
        "en": "Plan = analyze only (no file writes). Act = execute. Auto-switches to Act on gencode.",
        "ja": "Plan＝分析のみ（書き込みなし）。Act＝実行。コード生成指示で自動的に Act に切替。",
        "vi": "Plan = chỉ phân tích (không ghi file). Act = thực thi. Tự chuyển sang Act khi phát hiện yêu cầu sinh code."},
    "code.act_status": {"en": "Code: Act mode (executes).", "ja": "Code: Act モード（実行）。", "vi": "Code: chế độ Act (thực thi)."},
    "code.plan_status": {"en": "Code: Plan mode (analyze only).", "ja": "Code: Plan モード（分析のみ）。", "vi": "Code: chế độ Plan (chỉ phân tích)."},
    "code.cloud_sync_suffix": {"en": "  —  files sync to cloud", "ja": "  —  クラウドに同期", "vi": "  —  file sẽ đồng bộ lên cloud"},
    "code.mode_auto_status": {"en": "Code: Auto-run mode.", "ja": "Code: 自動実行モード。", "vi": "Code: chế độ Tự động."},
    "code.mode_confirm_status": {"en": "Code: Confirm mode.", "ja": "Code: 確認モード。", "vi": "Code: chế độ Xác nhận."},
    "code.pick_local_title": {"en": "Choose working folder (Local)", "ja": "作業フォルダを選択（ローカル）", "vi": "Chọn thư mục làm việc (Local)"},
    "code.pick_onedrive_title": {"en": "Choose a folder in OneDrive", "ja": "OneDrive 内のフォルダを選択", "vi": "Chọn thư mục trong OneDrive"},
    "code.onedrive_choose_folder": {
        "en": "Choose a folder in OneDrive…", "ja": "OneDrive 内のフォルダを選択…", "vi": "Chọn thư mục trong OneDrive…"},
    "code.no_onedrive": {"en": "No OneDrive detected", "ja": "OneDrive が見つかりません", "vi": "Không phát hiện OneDrive"},
    "code.flow_running": {
        "en": "Running flow '{name}' (Act) — {n} stages.",
        "ja": "フロー「{name}」を実行中（Act）— {n} ステージ。",
        "vi": "Đang chạy flow '{name}' (Act) — {n} bước."},

    # ---- settings_dialog.py --------------------------------------------
    "settings.title": {"en": "Settings", "ja": "設定", "vi": "Cài đặt"},
    "settings.active_provider": {"en": "Active provider", "ja": "使用中のプロバイダー", "vi": "Nhà cung cấp đang dùng"},
    "settings.theme": {"en": "Theme", "ja": "テーマ", "vi": "Giao diện"},
    "settings.theme_dark": {"en": "Dark", "ja": "ダーク", "vi": "Tối"},
    "settings.theme_light": {"en": "Light", "ja": "ライト", "vi": "Sáng"},
    "settings.theme_system": {"en": "Auto (System)", "ja": "自動（システム）", "vi": "Tự động (theo hệ thống)"},
    "settings.language": {"en": "Language", "ja": "言語", "vi": "Ngôn ngữ"},
    "settings.tray_keep": {
        "en": "Keep running in the system tray when the window is closed",
        "ja": "ウィンドウを閉じてもシステムトレイで実行を継続",
        "vi": "Giữ chạy nền trong khay hệ thống khi đóng cửa sổ"},
    "settings.tray_notify": {
        "en": "Show a tray notification when a task finishes or fails",
        "ja": "タスク完了/失敗時にトレイ通知を表示",
        "vi": "Hiện thông báo khay hệ thống khi tác vụ xong hoặc lỗi"},
    "settings.group.openai": {"en": "OpenAI-compatible (Internal Gateway)", "ja": "OpenAI 互換（社内ゲートウェイ）", "vi": "OpenAI-compatible (Gateway nội bộ)"},
    "settings.group.anthropic": {"en": "Anthropic Claude", "ja": "Anthropic Claude", "vi": "Anthropic Claude"},
    # Name for the language/tray block at the top of Settings — it had none,
    # because until the index existed nothing had to refer to it.
    "settings.group.general": {"en": "General", "ja": "一般", "vi": "Chung"},
    "settings.group.provider": {"en": "AI Provider", "ja": "AI プロバイダー", "vi": "Nhà cung cấp AI"},
    "settings.group.parameter": {"en": "Parameter", "ja": "パラメータ", "vi": "Tham số"},
    "settings.group.about": {"en": "About", "ja": "このアプリについて", "vi": "Giới thiệu"},
    "settings.param_section_pricing": {
        "en": "Model pricing", "ja": "モデル価格", "vi": "Bảng giá model"},
    "settings.pricing_url_label": {
        "en": "Pricing reference link", "ja": "価格表の参考リンク", "vi": "Link bảng giá tham khảo"},
    "settings.pricing_url_placeholder": {
        "en": "https://… (the provider's public price list)",
        "ja": "https://…（プロバイダーの公開価格表）",
        "vi": "https://… (trang bảng giá công khai của provider)"},
    "settings.pricing_url_tooltip": {
        "en": "Shown as a reference link beside the Monitoring pricing table. Prices themselves are entered by hand in that table.",
        "ja": "監視画面の価格表の横に参考リンクとして表示されます。価格自体は表に手入力します。",
        "vi": "Hiển thị làm link tham khảo cạnh bảng giá trong Monitoring. Giá vẫn do Admin nhập tay vào bảng."},
    "settings.group.accounts": {
        "en": "Shared accounts folder", "ja": "共有アカウントフォルダー", "vi": "Thư mục tài khoản dùng chung"},
    "settings.accounts_dir_label": {"en": "Folder", "ja": "フォルダー", "vi": "Thư mục"},
    "settings.accounts_dir_placeholder": {
        "en": "OneDrive/network folder holding the shared accounts & groups",
        "ja": "アカウント/グループを保存する OneDrive・共有フォルダー",
        "vi": "Thư mục OneDrive/mạng chứa danh sách tài khoản & nhóm dùng chung"},
    "settings.accounts_dir_hint": {
        "en": "Where accounts, groups and shared telemetry live. Every machine must point at the SAME folder.",
        "ja": "アカウント・グループ・共有テレメトリの保存先。全マシンで同じフォルダーを指定してください。",
        "vi": "Nơi lưu tài khoản, nhóm và telemetry dùng chung. Mọi máy phải trỏ về CÙNG một thư mục."},
    "settings.accounts_dir_admin_only": {
        "en": "Only an Admin can change this folder.",
        "ja": "このフォルダーを変更できるのは管理者のみです。",
        "vi": "Chỉ Admin mới thay đổi được thư mục này."},
    "settings.group.monitoring_visibility": {
        "en": "Monitoring tab visibility (Sub-admin)", "ja": "モニタリングタブの表示（サブ管理者）",
        "vi": "Hiển thị tab Monitoring (Sub-admin)"},
    "settings.mv_security_events": {"en": "Security Events", "ja": "セキュリティイベント",
                                    "vi": "Security Events"},
    "settings.mv_mcp_history": {"en": "MCP Call History", "ja": "MCP 呼び出し履歴", "vi": "MCP Call History"},
    "settings.mv_action_logs": {"en": "Action Logs", "ja": "アクションログ", "vi": "Action Logs"},
    "settings.mv_agent_status": {"en": "Agent Status", "ja": "エージェント状態", "vi": "Trạng thái Agent"},
    "settings.mv_hint": {
        "en": "Admin always sees every Monitoring tab. Turn one off here to hide it from Sub-admin too (it stays available to Admin).",
        "ja": "管理者は常にすべてのタブを見られます。ここでオフにすると、そのタブはサブ管理者からも隠されます（管理者には影響しません）。",
        "vi": "Admin luôn thấy mọi tab Monitoring. Tắt một mục ở đây sẽ ẩn tab đó với Sub-admin (Admin vẫn thấy như thường)."},
    "settings.sec_unlock_user_placeholder": {
        "en": "Admin account", "ja": "管理者アカウント", "vi": "Tài khoản admin"},
    "settings.sec_unlock_code_placeholder": {
        "en": "Access code", "ja": "アクセスコード", "vi": "Mã truy cập"},
    "settings.sec_unlock_btn": {"en": "Unlock", "ja": "ロック解除", "vi": "Mở khóa"},
    "settings.sec_locked_hint": {
        "en": "Locked — enter an Admin account + access code to change these settings.",
        "ja": "ロック中 — 変更するには管理者アカウントとアクセスコードを入力してください。",
        "vi": "Đang khóa — nhập tài khoản Admin + mã truy cập để thay đổi các thiết lập này."},
    "settings.sec_unlocked_hint": {
        "en": "Unlocked — changes will be saved; the group locks again after Save.",
        "ja": "ロック解除中 — 保存後に再びロックされます。",
        "vi": "Đã mở khóa — thay đổi sẽ được lưu; nhóm sẽ tự khóa lại sau khi Save."},
    "settings.sec_unlock_failed": {
        "en": "Not an Admin account (or wrong code / accounts folder unreachable).",
        "ja": "管理者アカウントではありません（またはコード誤り・フォルダー未接続）。",
        "vi": "Không phải tài khoản Admin (hoặc sai mã / không truy cập được thư mục tài khoản)."},
    "settings.sec_no_lock_hint": {
        "en": "No shared accounts folder configured yet — the group is editable without an admin unlock.",
        "ja": "共有アカウントフォルダー未設定のため、ロックなしで編集できます。",
        "vi": "Chưa cấu hình thư mục tài khoản dùng chung — nhóm này đang chỉnh sửa được mà không cần mở khóa."},
    "settings.base_url": {"en": "Base URL", "ja": "ベース URL", "vi": "Base URL"},
    "settings.api_key": {"en": "API Key", "ja": "API キー", "vi": "API Key"},
    "settings.model": {"en": "Model", "ja": "モデル", "vi": "Model"},
    "settings.load": {"en": "Load", "ja": "読み込み", "vi": "Tải"},
    "settings.load_tooltip": {
        "en": "Fetch the available models/agents from this provider",
        "ja": "このプロバイダーから利用可能なモデル/エージェントを取得",
        "vi": "Lấy danh sách model/agent khả dụng từ nhà cung cấp này"},
    "settings.group.teams": {"en": "Microsoft Teams", "ja": "Microsoft Teams", "vi": "Microsoft Teams"},
    "settings.teams_webhook": {"en": "Webhook URL", "ja": "Webhook URL", "vi": "Webhook URL"},
    "settings.teams_webhook_placeholder": {
        "en": "https://…  (Workflows or Incoming Webhook URL)",
        "ja": "https://…（Workflows または Incoming Webhook の URL）",
        "vi": "https://…  (URL của Workflows hoặc Incoming Webhook)"},
    "settings.teams_test": {"en": "Test", "ja": "テスト", "vi": "Kiểm tra"},
    "settings.teams_notify": {
        "en": "Auto-send to Teams when a task completes", "ja": "タスク完了時に Teams へ自動送信",
        "vi": "Tự động gửi sang Teams khi tác vụ hoàn thành"},
    "settings.teams_hint": {
        "en": ("Get a webhook: Teams channel → ⋯ → Connectors → Incoming Webhook, "
               "OR Power Automate → 'When a HTTP request is received' → 'Post message in a chat or channel'. "
               "URL must contain logic.azure.com or webhook.office.com."),
        "ja": ("Webhook の取得: Teams チャンネル → ⋯ → コネクタ → Incoming Webhook、"
               "または Power Automate → 'HTTP要求の受信時' → 'チャットまたはチャネルにメッセージを投稿'。"
               "URL には logic.azure.com か webhook.office.com を含める必要があります。"),
        "vi": ("Lấy webhook: kênh Teams → ⋯ → Connectors → Incoming Webhook, "
               "HOẶC Power Automate → 'When a HTTP request is received' → 'Post message in a chat or channel'. "
               "URL phải chứa logic.azure.com hoặc webhook.office.com.")},
    "settings.group.ms365": {
        "en": "Microsoft 365 connections", "ja": "Microsoft 365 連携",
        "vi": "Kết nối Microsoft 365"},
    "settings.ms365_unlock_code": {"en": "Unlock code", "ja": "解除コード", "vi": "Mã mở khóa"},
    "settings.ms365_unlock_placeholder": {
        "en": "Enter the unlock code", "ja": "解除コードを入力",
        "vi": "Nhập mã để mở khóa"},
    "settings.ms365_unlock_btn": {"en": "Unlock", "ja": "解除", "vi": "Mở khóa"},
    "settings.ms365_locked_hint": {
        "en": "Locked — enter the unlock code above to edit this section.",
        "ja": "ロック中 — このセクションを編集するには上の解除コードを入力してください。",
        "vi": "Đang khóa — nhập mã ở trên để chỉnh sửa mục này."},
    "settings.ms365_unlocked_hint": {
        "en": "Unlocked — remember to click Save; this section re-locks automatically afterward.",
        "ja": "解除しました — 保存を忘れずに。保存後は自動的に再ロックされます。",
        "vi": "Đã mở khóa — nhớ bấm Save; mục này sẽ tự khóa lại ngay sau đó."},
    "settings.ms365_wrong_code": {
        "en": "Wrong code.", "ja": "コードが違います。", "vi": "Mã không đúng."},
    "settings.ms365_connector.outlook": {"en": "Outlook", "ja": "Outlook", "vi": "Outlook"},
    "settings.ms365_connector.teams": {"en": "Teams", "ja": "Teams", "vi": "Teams"},
    "settings.ms365_connector.onedrive": {"en": "OneDrive", "ja": "OneDrive", "vi": "OneDrive"},
    "settings.ms365_connector.sharepoint": {"en": "SharePoint", "ja": "SharePoint", "vi": "SharePoint"},
    "settings.ms365_connector.meeting_transcript": {
        "en": "Meeting transcript", "ja": "会議の文字起こし", "vi": "Meeting transcript"},
    "settings.ms365_allow_internet": {
        "en": "Allow external internet access", "ja": "外部インターネットアクセスを許可",
        "vi": "Cho phép truy cập Internet bên ngoài"},
    "settings.ms365_internet_off_hint": {
        "en": ("External internet access is OFF — every connector was turned off to avoid "
               "leaking data outside. Turn it back on, then re-tick the connectors you want."),
        "ja": ("外部インターネットアクセスがオフです — データが外部に漏れないよう、すべてのコネクタ"
               "がオフになりました。再度オンにしてから、必要なコネクタを選び直してください。"),
        "vi": ("Đã tắt truy cập Internet bên ngoài — mọi connector đã tự tắt để tránh rò rỉ "
                "thông tin ra ngoài. Bật lại rồi tick lại từng connector muốn dùng.")},
    "settings.ms365_signin_btn": {"en": "Sign in with Microsoft", "ja": "Microsoft でサインイン",
                                  "vi": "Đăng nhập Microsoft"},
    "settings.ms365_signout_btn": {"en": "Sign out", "ja": "サインアウト", "vi": "Đăng xuất"},
    "settings.ms365_not_signed_in": {
        "en": "Not signed in to Microsoft 365.", "ja": "Microsoft 365 にサインインしていません。",
        "vi": "Chưa đăng nhập Microsoft 365."},
    "settings.ms365_signed_in_as": {
        "en": "Signed in as {user}", "ja": "{user} としてサインイン中",
        "vi": "Đã đăng nhập với {user}"},
    "settings.ms365_missing_ids": {
        "en": "Enter the Tenant ID and Client ID first.", "ja": "先に Tenant ID と Client ID を入力してください。",
        "vi": "Hãy nhập Tenant ID và Client ID trước."},
    "settings.ms365_signing_in": {
        "en": "Starting sign-in…", "ja": "サインインを開始しています…", "vi": "Đang bắt đầu đăng nhập…"},
    "settings.ms365_signin_failed": {
        "en": "Sign-in failed: {err}", "ja": "サインインに失敗しました: {err}",
        "vi": "Đăng nhập thất bại: {err}"},
    "settings.ms365_teams_link_label": {
        "en": "Or just paste a Teams channel/chat link — no ID needed:",
        "ja": "または Teams のチャネル/チャットのリンクを貼り付けるだけ — ID は不要です:",
        "vi": "Hoặc chỉ cần paste link kênh/chat Teams — không cần ID:"},
    "settings.ms365_teams_link_placeholder": {
        "en": "Paste a link from Teams ('Get link to channel' or a message's 'Copy link')",
        "ja": "Teams のリンクを貼り付け（「チャネルへのリンクを取得」またはメッセージの「リンクをコピー」）",
        "vi": "Dán link từ Teams ('Get link to channel' hoặc 'Copy link' của 1 tin nhắn)"},
    "settings.ms365_teams_connect_btn": {"en": "Connect", "ja": "接続", "vi": "Kết nối"},
    "settings.ms365_teams_not_connected": {
        "en": "No Teams chat/channel connected yet.", "ja": "Teams のチャット/チャネルはまだ接続されていません。",
        "vi": "Chưa kết nối chat/kênh Teams nào."},
    "settings.ms365_teams_connected_channel": {
        "en": "Connected to a Teams channel.", "ja": "Teams のチャネルに接続済みです。",
        "vi": "Đã kết nối vào một kênh Teams."},
    "settings.ms365_teams_connected_chat": {
        "en": "Connected to a Teams chat.", "ja": "Teams のチャットに接続済みです。",
        "vi": "Đã kết nối vào một đoạn chat Teams."},
    "settings.ms365_teams_link_missing": {
        "en": "Paste a Teams link first.", "ja": "先に Teams のリンクを貼り付けてください。",
        "vi": "Hãy dán link Teams trước."},
    "settings.ms365_teams_connecting": {
        "en": "Connecting…", "ja": "接続しています…", "vi": "Đang kết nối…"},
    "settings.ms365_teams_connect_failed": {
        "en": "Connect failed: {err}", "ja": "接続に失敗しました: {err}",
        "vi": "Kết nối thất bại: {err}"},
    "settings.ms365_teams_intro_message": {
        "en": "Hi, I'm the Cowork agent — just connected to this chat/channel.",
        "ja": "こんにちは、Cowork エージェントです — このチャット/チャネルに接続しました。",
        "vi": "Xin chào, mình là Cowork agent — vừa kết nối vào chat/kênh này."},
    "settings.group.agent_security": {
        "en": "Agent Security (AI)", "ja": "エージェント セキュリティ（AI）",
        "vi": "Agent Security (AI)"},
    "settings.group.sandbox": {
        "en": "Sandbox Security Layer", "ja": "サンドボックス セキュリティ層",
        "vi": "Sandbox Security Layer"},
    "settings.sec_enabled": {
        "en": "Enable Agent Security (command validation)",
        "ja": "エージェントセキュリティを有効化（コマンド検証）",
        "vi": "Bật Agent Security (kiểm tra lệnh)"},
    "settings.sec_enabled_tooltip": {
        "en": "Turn the whole Agent Security layer on or off.",
        "ja": "エージェントセキュリティ層全体をオン/オフします。",
        "vi": "Bật/tắt toàn bộ tầng Agent Security."},
    "settings.ai_check": {
        "en": "AI check commands", "ja": "AIによるコマンド検査",
        "vi": "AI kiểm tra lệnh"},
    "settings.ai_check_tooltip": {
        "en": "Let the control agent review a command with AI before it runs.",
        "ja": "実行前に制御エージェントがAIでコマンドを確認します。",
        "vi": "Cho control-agent dùng AI xét lệnh trước khi chạy."},
    "settings.sandbox_pw_unset_title": {
        "en": "Sandbox Security", "ja": "サンドボックスセキュリティ", "vi": "Bảo mật Sandbox"},
    "settings.sandbox_pw_unset_body": {
        "en": "No sandbox password is set yet, so these settings stay locked. Set COWORK_SANDBOX_PASSWORD, or ask your administrator.",
        "ja": "サンドボックスのパスワードが未設定のため、この設定はロックされたままです。COWORK_SANDBOX_PASSWORD を設定するか、管理者にお問い合わせください。",
        "vi": "Chưa đặt mật khẩu sandbox nên nhóm thiết lập này vẫn khóa. Hãy đặt COWORK_SANDBOX_PASSWORD, hoặc liên hệ quản trị viên."},
    "settings.sandbox_confirm_commands": {
        "en": "Confirm before Cowork runs a command",
        "ja": "Cowork がコマンドを実行する前に確認する",
        "vi": "Xác nhận trước khi Cowork chạy lệnh"},
    "settings.sandbox_confirm_commands_tooltip": {
        "en": ("Shows an Approve/Reject dialog before run_command/install_package "
               "executes in Cowork — off by default (auto-run), same as before."),
        "ja": "Cowork で run_command/install_package を実行する前に承認/拒否ダイアログを表示します — "
              "デフォルトはオフ（自動実行）で、これまでと同じです。",
        "vi": "Hiện hộp thoại Duyệt/Từ chối trước khi Cowork chạy run_command/install_package — "
              "mặc định tắt (tự chạy), giống hành vi cũ."},
}
