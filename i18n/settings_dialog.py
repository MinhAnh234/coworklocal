"""Chuỗi hiển thị — phần settings_dialog.

Cắt ra từ ``i18n.py``: một dict 3.000 dòng không mở nổi để sửa một chữ.
Cắt theo mốc phân đoạn có sẵn, nên mỗi cụm vẫn là các màn đi liền nhau.
``i18n.py`` gộp tất cả lại thành ``STRINGS``.
"""
from __future__ import annotations

from typing import Dict

STRINGS: Dict[str, Dict[str, str]] = {
    "settings.sandbox_block_network": {
        "en": "Block network (AI provider still allowed)",
        "ja": "ネットワークをブロック（AIプロバイダーのみ許可）",
        "vi": "Chặn mạng (vẫn cho gọi nhà cung cấp AI)"},
    "settings.allow_url_fetch": {
        "en": "Allow the agent to fetch URLs (web pages, SharePoint / OneDrive links)",
        "ja": "エージェントによるURL取得を許可（Webページ、SharePoint / OneDriveリンク）",
        "vi": "Cho phép agent lấy dữ liệu từ URL (trang web, link SharePoint / OneDrive)"},
    "settings.allow_url_fetch_tooltip": {
        "en": ("Lets the agent's fetch_url tool read web pages, online documents and "
               "SharePoint/OneDrive share links to search & process them. 'Block network' "
               "overrides this switch. Default: on."),
        "ja": "エージェントのfetch_urlツールがWebページ・オンライン文書・SharePoint/OneDrive共有リンクを"
              "読み取れるようにします。「ネットワークをブロック」がオンの場合はそちらが優先されます。既定: オン。",
        "vi": ("Cho phép tool fetch_url của agent đọc trang web, tài liệu online và link chia sẻ "
               "SharePoint/OneDrive để tìm kiếm & xử lý. 'Chặn mạng' được ưu tiên hơn công tắc "
               "này. Mặc định: bật.")},
    "settings.test_internet": {
        "en": "Test Internet", "ja": "インターネット接続テスト", "vi": "Kiểm tra Internet"},
    "settings.test_internet_tooltip": {
        "en": ("Live-checks the app's own outbound HTTPS path (the same one fetch_url uses) "
               "and reports the concrete reason if it can't reach the internet."),
        "ja": "アプリ自身の送信HTTPS経路（fetch_urlと同じ）を実際にテストし、インターネットに到達できない"
              "場合は具体的な理由を表示します。",
        "vi": ("Kiểm tra trực tiếp đường HTTPS ra ngoài của app (đúng đường mà fetch_url dùng) và "
               "báo lý do cụ thể nếu không truy cập được internet.")},
    "settings.testing_internet": {
        "en": "Testing internet access…", "ja": "インターネット接続をテスト中…",
        "vi": "Đang kiểm tra truy cập internet…"},
    "settings.sandbox_block_network_tooltip": {
        "en": ("Only the AI provider (chat, model list, model test) may reach the network. "
               "Agent shell commands and task scripts run in a Windows AppContainer with no "
               "network access; fetch_url, Jira, connectors/MCP, Microsoft 365, Teams, "
               "connector tests, pip auto-install and remote content in HTML previews are refused."),
        "ja": "ネットワークに接続できるのはAIプロバイダー（チャット・モデル一覧・モデルテスト）のみです。"
              "エージェントのシェルコマンドとタスクスクリプトはネットワークなしのWindows AppContainerで実行され、"
              "fetch_url・Jira・コネクタ/MCP・Microsoft 365・Teams・接続テスト・pip自動インストール・"
              "HTMLプレビューの外部リソースは拒否されます。",
        "vi": "Chỉ nhà cung cấp AI (chat, tải danh sách model, thử model) được ra mạng. Lệnh shell "
              "của agent và task script chạy trong Windows AppContainer không có mạng; fetch_url, "
              "Jira, connector/MCP, Microsoft 365, Teams, nút Test, tự cài thư viện và tài nguyên "
              "web trong xem trước HTML đều bị từ chối."},
    "settings.sandbox_unlimited": {"en": "Unlimited", "ja": "無制限", "vi": "Không giới hạn"},
    "settings.sandbox_cpu_label": {"en": "CPU limit", "ja": "CPU 制限", "vi": "Giới hạn CPU"},
    "settings.sandbox_memory_label": {"en": "Memory limit", "ja": "メモリ制限", "vi": "Giới hạn bộ nhớ"},
    "settings.sandbox_disk_label": {"en": "Disk I/O limit", "ja": "ディスク I/O 制限", "vi": "Giới hạn disk I/O"},
    "settings.sandbox_hint": {
        "en": ("Applies to every run_command/install_package the agent executes "
               "(Cowork, Code tab, and Schedule Task alike). 0 = unlimited. This layer is "
               "independent of \"Agent Security\" above — it still applies even while that "
               "toggle is off."),
        "ja": "エージェントが実行するすべての run_command/install_package に適用されます"
              "（Cowork、Code タブ、Schedule Task 共通）。0 = 無制限。この機能は上の「Agent "
              "Security」とは独立しており、そのトグルがオフの間も適用され続けます。",
        "vi": "Áp dụng cho mọi run_command/install_package mà agent chạy (Cowork, tab Code, "
              "và Schedule Task). 0 = không giới hạn. Lớp này độc lập với \"Agent Security\" "
              "ở trên — vẫn áp dụng ngay cả khi tắt Agent Security."},
    "settings.group.mcp": {"en": "MCP Servers", "ja": "MCP サーバー", "vi": "MCP Servers"},
    "settings.mcp_hint": {
        "en": ("Connect to external MCP (Model Context Protocol) servers — e.g. the official "
               "filesystem/GitHub/brave-search servers — and their tools become available to "
               "the agent alongside Microsoft 365 and the built-in file/command tools."),
        "ja": "外部の MCP（Model Context Protocol）サーバー（公式の filesystem/GitHub/brave-search "
              "サーバーなど）に接続すると、そのツールが Microsoft 365 や組み込みのファイル/コマンド"
              "ツールと並んでエージェントから利用できるようになります。",
        "vi": "Kết nối tới các MCP server bên ngoài (vd: server filesystem/GitHub/brave-search chính "
              "thức) — tool của chúng sẽ khả dụng cho agent cùng với Microsoft 365 và tool file/lệnh "
              "có sẵn."},
    "settings.mcp_add_btn": {"en": "Add server…", "ja": "サーバーを追加…", "vi": "Thêm server…"},
    "settings.mcp_edit_btn": {"en": "Edit", "ja": "編集", "vi": "Sửa"},
    "settings.mcp_delete_btn": {"en": "Delete", "ja": "削除", "vi": "Xóa"},
    "settings.mcp_no_servers": {
        "en": "(No MCP servers configured — click 'Add server…')",
        "ja": "（MCP サーバーが設定されていません。「サーバーを追加…」をクリック）",
        "vi": "(Chưa cấu hình MCP server nào — bấm 'Thêm server…')"},
    "settings.mcp_delete_confirm": {
        "en": "Remove MCP server \"{name}\"?", "ja": "MCP サーバー「{name}」を削除しますか？",
        "vi": "Xóa MCP server \"{name}\"?"},
    "mcp.add_title": {"en": "Add MCP server", "ja": "MCP サーバーを追加", "vi": "Thêm MCP server"},
    "mcp.edit_title": {"en": "Edit MCP server", "ja": "MCP サーバーを編集", "vi": "Sửa MCP server"},
    "mcp.name_label": {"en": "Name", "ja": "名前", "vi": "Tên"},
    "mcp.name_placeholder": {"en": "e.g. filesystem", "ja": "例: filesystem", "vi": "vd: filesystem"},
    "mcp.command_label": {"en": "Command", "ja": "コマンド", "vi": "Lệnh"},
    "mcp.command_placeholder": {"en": "e.g. npx", "ja": "例: npx", "vi": "vd: npx"},
    "mcp.args_label": {"en": "Arguments", "ja": "引数", "vi": "Tham số"},
    "mcp.args_placeholder": {
        "en": "e.g. -y @modelcontextprotocol/server-filesystem C:\\Data",
        "ja": "例: -y @modelcontextprotocol/server-filesystem C:\\Data",
        "vi": "vd: -y @modelcontextprotocol/server-filesystem C:\\Data"},
    "mcp.hint": {
        "en": ("The server is launched as a subprocess and talked to over stdio (the standard "
               "MCP transport) — the SAME way Claude Desktop/other MCP clients connect to it."),
        "ja": "サーバーはサブプロセスとして起動され、stdio（標準の MCP トランスポート）で通信します"
              "— Claude Desktop など他の MCP クライアントと同じ方式です。",
        "vi": "Server được khởi chạy như 1 subprocess và giao tiếp qua stdio (giao thức MCP chuẩn) "
              "— giống cách Claude Desktop hay các MCP client khác kết nối tới nó."},

    # ---- settings_dialog.py / ext_connector_dialog.py: External Connectors (CAD/CAE/Office) ----
    "settings.group.ext": {
        "en": "Connectors (MCP)",
        "ja": "コネクタ（MCP）",
        "vi": "Connectors (MCP)"},
    "settings.ext_moved_hint": {
        "en": "Connector (MCP / REST-API) setup moved to Monitoring → Tools → Connector.",
        "ja": "コネクター（MCP / REST-API）の設定は「モニタリング → ツール → Connector」へ移動しました。",
        "vi": "Thiết lập Connector (MCP / REST-API) đã chuyển sang Monitoring → Công cụ → Connector."},
    "settings.ext_hint": {
        "en": ("One place for every external tool source — grouped as CAD (NX/CATIA/SolidWorks/"
               "AutoCAD), CAE (ANSA/ABAQUS/HyperWorks/ANSYS), MS365 (Microsoft 365/OneDrive/"
               "SharePoint) and Other (any generic MCP server). MS365 auto-connects via the built-in "
               "server once you sign in; for the rest, point each connector at an MCP server you "
               "already have or a REST API it exposes (no vendor SDK is bundled)."),
        "ja": "外部ツール接続を1か所に集約 — CAD（NX/CATIA/SolidWorks/AutoCAD）、CAE（ANSA/ABAQUS/"
              "HyperWorks/ANSYS）、MS365（Microsoft 365/OneDrive/SharePoint）、Other（汎用 MCP サーバー）。"
              "MS365 はサインインすると内蔵サーバーで自動接続。その他は既存の MCP サーバーまたは REST API を"
              "指定してください（ベンダー SDK は同梱しません）。",
        "vi": "Một nơi duy nhất cho mọi nguồn tool ngoài — nhóm theo CAD (NX/CATIA/SolidWorks/AutoCAD), "
              "CAE (ANSA/ABAQUS/HyperWorks/ANSYS), MS365 (Microsoft 365/OneDrive/SharePoint) và Other "
              "(MCP server bất kỳ). MS365 tự kết nối qua server tích hợp sau khi đăng nhập; còn lại bạn "
              "trỏ mỗi connector tới MCP server bạn đã có hoặc REST API nó cung cấp (không kèm SDK hãng nào)."},
    "settings.ext_add_btn": {"en": "Add connector…", "ja": "コネクタを追加…", "vi": "Thêm connector…"},
    "settings.ext_edit_btn": {"en": "Edit", "ja": "編集", "vi": "Sửa"},
    "settings.ext_delete_btn": {"en": "Delete", "ja": "削除", "vi": "Xóa"},
    "settings.ext_delete_confirm": {
        "en": "Remove connector \"{name}\"?", "ja": "コネクタ「{name}」を削除しますか？",
        "vi": "Xóa connector \"{name}\"?"},
    "ext.add_title": {"en": "Add connector", "ja": "コネクタを追加", "vi": "Thêm connector"},
    "ext.edit_title": {"en": "Edit connector", "ja": "コネクタを編集", "vi": "Sửa connector"},
    "ext.category_label": {"en": "Category", "ja": "カテゴリ", "vi": "Nhóm"},
    "ext.preset_label": {"en": "App", "ja": "アプリ", "vi": "Ứng dụng"},
    "ext.preset_custom": {"en": "(Custom…)", "ja": "（カスタム…）", "vi": "(Tuỳ chỉnh…)"},
    "ext.name_label": {"en": "Display name", "ja": "表示名", "vi": "Tên hiển thị"},
    "ext.name_placeholder": {"en": "e.g. NX (Site A)", "ja": "例: NX（サイトA）", "vi": "vd: NX (Site A)"},
    "ext.mode_label": {"en": "Connection type", "ja": "接続方式", "vi": "Kiểu kết nối"},
    "ext.mode_mcp": {"en": "MCP server (stdio)", "ja": "MCP サーバー（stdio）", "vi": "MCP server (stdio)"},
    "ext.mode_rest": {"en": "REST API", "ja": "REST API", "vi": "REST API"},
    "ext.mode_builtin": {"en": "built-in, auto-connect", "ja": "内蔵・自動接続", "vi": "tích hợp, tự kết nối"},
    "settings.ms365_signin_btn": {"en": "Sign in to Microsoft 365", "ja": "Microsoft 365 にサインイン",
                                  "vi": "Đăng nhập Microsoft 365"},
    "settings.ms365_signout_btn": {"en": "Sign out", "ja": "サインアウト", "vi": "Đăng xuất"},
    "settings.ms365_signed_in": {"en": "Microsoft 365: signed in as {who}",
                                 "ja": "Microsoft 365: {who} でサインイン中",
                                 "vi": "Microsoft 365: đã đăng nhập ({who})"},
    "settings.ms365_signed_out": {
        "en": "Microsoft 365: not signed in — one click, no Tenant/Client ID needed.",
        "ja": "Microsoft 365: 未サインイン — ワンクリック、テナント/クライアント ID 不要。",
        "vi": "Microsoft 365: chưa đăng nhập — 1 cú click, không cần Tenant/Client ID."},
    "settings.ms365_signing_in": {
        "en": "Microsoft 365: opening sign-in… follow the code prompt.",
        "ja": "Microsoft 365: サインインを開始中… コードの案内に従ってください。",
        "vi": "Microsoft 365: đang mở đăng nhập… làm theo hướng dẫn mã code."},
    "settings.ms365_code_hint": {
        "en": ("The sign-in page opened in your browser (<a href='{url}'>{url}</a>) and the code "
               "below was copied to your clipboard — just paste it, then sign in with your Microsoft "
               "account. This window closes automatically when sign-in completes."),
        "ja": ("ブラウザでサインインページ（<a href='{url}'>{url}</a>）を開きました。下のコードはクリップボードに"
               "コピー済みです — 貼り付けて Microsoft アカウントでサインインしてください。完了すると自動で閉じます。"),
        "vi": ("Trang đăng nhập đã mở trong trình duyệt (<a href='{url}'>{url}</a>) và mã bên dưới đã được "
               "copy vào clipboard — chỉ cần dán, rồi đăng nhập bằng tài khoản Microsoft. Cửa sổ này tự đóng "
               "khi đăng nhập xong.")},
    "settings.ms365_copy_code": {"en": "Copy code", "ja": "コードをコピー", "vi": "Copy mã"},
    "settings.ms365_open_link": {"en": "Open link", "ja": "リンクを開く", "vi": "Mở link"},
    "settings.ms365_local_connected": {
        "en": "OneDrive / SharePoint: auto-connected via local sync — no sign-in needed.\nSynced folder: {path}",
        "ja": "OneDrive / SharePoint: ローカル同期で自動接続 — サインイン不要。\n同期フォルダ: {path}",
        "vi": "OneDrive / SharePoint: tự động kết nối qua thư mục sync local — không cần đăng nhập.\nThư mục đã sync: {path}"},
    "settings.ms365_local_none": {
        "en": "OneDrive / SharePoint: no locally-synced OneDrive folder found. Install/sign in to "
              "the OneDrive desktop app and sync a folder, then reopen Settings.",
        "ja": "OneDrive / SharePoint: ローカル同期の OneDrive フォルダが見つかりません。OneDrive デスクトップ"
              "アプリでサインインしフォルダを同期してから、設定を開き直してください。",
        "vi": "OneDrive / SharePoint: chưa tìm thấy thư mục OneDrive sync trên máy. Cài/đăng nhập OneDrive "
              "desktop và sync một thư mục, rồi mở lại Settings."},
    "ext.command_label": {"en": "Command", "ja": "コマンド", "vi": "Lệnh"},
    "ext.command_placeholder": {"en": "e.g. python or npx", "ja": "例: python または npx", "vi": "vd: python hoặc npx"},
    "ext.args_label": {"en": "Arguments", "ja": "引数", "vi": "Tham số"},
    "ext.args_placeholder": {"en": "e.g. -m nx_mcp_server", "ja": "例: -m nx_mcp_server", "vi": "vd: -m nx_mcp_server"},
    "ext.base_url_label": {"en": "Base URL", "ja": "ベース URL", "vi": "Base URL"},
    "ext.base_url_placeholder": {
        "en": "e.g. https://cad-api.internal.company.com",
        "ja": "例: https://cad-api.internal.company.com",
        "vi": "vd: https://cad-api.internal.company.com"},
    "ext.api_key_label": {"en": "API key", "ja": "API キー", "vi": "API key"},
    "ext.auth_header_label": {"en": "Auth header name", "ja": "認証ヘッダー名", "vi": "Tên header xác thực"},
    "ext.auth_scheme_label": {"en": "Auth scheme", "ja": "認証スキーム", "vi": "Auth scheme"},
    "ext.test_btn": {"en": "Test connection", "ja": "接続テスト", "vi": "Kiểm tra kết nối"},
    "ext.err_no_command": {
        "en": "Enter a command first.", "ja": "先にコマンドを入力してください。", "vi": "Hãy nhập lệnh trước."},
    "ext.test_mcp_ok": {
        "en": "MCP server started and responded.", "ja": "MCP サーバーが起動し応答しました。",
        "vi": "MCP server đã khởi chạy và phản hồi."},

    "settings.sec_enabled": {
        "en": "Enable AI-assisted agent security guardrails",
        "ja": "AI 支援のエージェント セキュリティ ガードレールを有効化",
        "vi": "Bật các lớp bảo mật agent có AI hỗ trợ"},
    "settings.sec_hint": {
        "en": "Three independent layers: an AI reviews the user's request and "
              "attachment content against the rules below before the agent "
              "acts, and a whitelist + AI control-agent checks every "
              "run_command/install_package call. A violation always blocks "
              "the action and emails the admin below. Each AI check fails "
              "OPEN (allows) if the model itself can't be reached — a gateway "
              "hiccup must never make the agent unusable.",
        "ja": "3つの独立した層があります：エージェントが行動する前に、AI がユーザーの"
              "リクエストと添付ファイルの内容を下記のルールと照合してチェックし、"
              "ホワイトリストと AI コントロールエージェントがすべての "
              "run_command/install_package 呼び出しをチェックします。違反時は常に"
              "操作をブロックし、下記の管理者にメールで通知します。各 AI チェックは"
              "モデルに到達できない場合は「許可」側に倒れます（フェイルオープン）— "
              "ゲートウェイの一時的な不調でエージェントが使えなくなることがあっては"
              "なりません。",
        "vi": "Ba lớp độc lập: AI kiểm tra yêu cầu của người dùng và nội dung file "
              "đính kèm theo các rule bên dưới TRƯỚC khi agent hành động, và một "
              "whitelist + AI control-agent kiểm tra mọi lệnh run_command/"
              "install_package. Vi phạm sẽ luôn CHẶN hành động và gửi email cho "
              "admin bên dưới. Mỗi lớp kiểm tra bằng AI sẽ MẶC ĐỊNH CHO PHÉP nếu "
              "không gọi được model — một sự cố gateway tạm thời không được phép "
              "làm agent ngừng hoạt động."},
    "settings.sec_validate_prompt": {
        "en": "Validate the user's request (prompt) before acting",
        "ja": "行動する前にユーザーのリクエスト（プロンプト）を検証",
        "vi": "Validate yêu cầu (prompt) của người dùng trước khi hành động"},
    "settings.sec_validate_attachments": {
        "en": "Scan attachment/file content for malicious payloads",
        "ja": "添付/ファイルの内容に悪意あるペイロードがないかスキャン",
        "vi": "Scan nội dung file đính kèm để phát hiện nội dung độc hại"},
    "settings.sec_validate_commands": {
        "en": "Check run_command / install_package against a whitelist",
        "ja": "run_command / install_package をホワイトリストと照合",
        "vi": "Kiểm tra run_command / install_package theo whitelist"},
    "settings.sec_command_ai_check": {
        "en": "Also let an AI control-agent judge commands not covered by the whitelist",
        "ja": "ホワイトリストに含まれないコマンドは AI コントロールエージェントにも判定させる",
        "vi": "Cho AI control-agent xét thêm các lệnh whitelist chưa liệt kê"},
    "settings.sec_whitelist_label": {"en": "Command whitelist", "ja": "コマンド ホワイトリスト", "vi": "Whitelist lệnh"},
    "settings.sec_whitelist_placeholder": {
        "en": "One regex pattern per line, e.g. ^pip install\\n^pytest\\n^git ",
        "ja": "1行に1つの正規表現、例: ^pip install\\n^pytest\\n^git ",
        "vi": "Mỗi dòng 1 regex, vd: ^pip install\\n^pytest\\n^git "},
    "settings.sec_whitelist_empty_warning": {
        "en": "Empty whitelist + AI check off = every command is BLOCKED "
              "(fail-closed) — add a pattern above or turn AI check back on.",
        "ja": "ホワイトリストが空でAIチェックも無効の場合、すべてのコマンドが"
              "ブロックされます（フェイルクローズ）。上にパターンを追加するか"
              "AIチェックを再度有効にしてください。",
        "vi": "Whitelist trống + tắt AI-check = MỌI lệnh sẽ bị CHẶN hết "
              "(fail-closed) — hãy thêm pattern ở trên hoặc bật lại AI-check."},
    "settings.sec_onedrive_label": {"en": "OneDrive rules link", "ja": "OneDrive ルールへのリンク", "vi": "Link OneDrive chứa rule"},
    "settings.sec_onedrive_placeholder": {
        "en": "(optional) sharing link to an admin-authored .md rules document",
        "ja": "（任意）管理者が作成した .md ルール文書への共有リンク",
        "vi": "(tuỳ chọn) link chia sẻ tới file .md rule do admin soạn"},
    "settings.sec_admin_email_label": {"en": "Admin email", "ja": "管理者メール", "vi": "Email admin"},
    "settings.sec_admin_email_placeholder": {
        "en": "admin@yourcompany.com — receives violation alerts via Microsoft 365",
        "ja": "admin@yourcompany.com — Microsoft 365 経由で違反アラートを受信",
        "vi": "admin@yourcompany.com — nhận cảnh báo vi phạm qua Microsoft 365"},
    "settings.sec_rules_path_hint": {
        "en": "Local admin rules file (optional, edited directly, always applied): {path}",
        "ja": "ローカルの管理者ルールファイル（任意・直接編集・常に適用）: {path}",
        "vi": "File rule admin cục bộ (tuỳ chọn, sửa trực tiếp, luôn được áp dụng): {path}"},
    "settings.group.history": {"en": "Conversation history", "ja": "会話履歴", "vi": "Lịch sử hội thoại"},
    "settings.history_local": {"en": "Local (this PC)", "ja": "ローカル（このPC）", "vi": "Local (máy này)"},
    "settings.history_onedrive": {"en": "OneDrive", "ja": "OneDrive", "vi": "OneDrive"},
    "settings.location": {"en": "Location", "ja": "保存先", "vi": "Nơi lưu"},
    "settings.folder": {"en": "Folder", "ja": "フォルダ", "vi": "Thư mục"},
    "settings.folder_placeholder": {
        "en": "(optional) specific folder — leave empty for default",
        "ja": "（任意）特定のフォルダ ― 空欄で既定値",
        "vi": "(tuỳ chọn) thư mục cụ thể — để trống dùng mặc định"},
    "settings.browse": {"en": "Browse…", "ja": "参照…", "vi": "Duyệt…"},
    "settings.autosave": {"en": "Auto-save history after each turn", "ja": "各ターン後に履歴を自動保存", "vi": "Tự động lưu lịch sử sau mỗi lượt"},
    "settings.group.cowork": {"en": "Cowork", "ja": "Cowork", "vi": "Cowork"},
    "settings.max_parallel": {"en": "Max parallel conversations", "ja": "同時実行する会話数の上限", "vi": "Số hội thoại chạy song song tối đa"},
    "settings.parallel_suffix": {"en": "  conversations at once", "ja": "  件を同時実行", "vi": "  hội thoại cùng lúc"},
    "settings.parallel_tooltip": {
        "en": ("How many conversations run in parallel. Within one conversation messages always "
               "run one at a time (queued); only different conversations run in parallel."),
        "ja": ("並列実行する会話数です。1つの会話内のメッセージは常に1件ずつ（キュー）実行され、"
               "異なる会話同士のみ並列に実行されます。"),
        "vi": ("Số cuộc trò chuyện chạy song song. Trong MỘT cuộc trò chuyện, tin nhắn luôn "
               "chạy lần lượt (xếp hàng) để không bị trộn lẫn; chỉ các cuộc trò chuyện khác "
               "nhau mới chạy song song.")},
    "settings.group.attachments": {"en": "Attachments", "ja": "添付ファイル", "vi": "Tệp đính kèm"},
    "settings.max_files": {"en": "Max files", "ja": "最大ファイル数", "vi": "Số tệp tối đa"},
    "settings.max_files_suffix": {"en": "  files / message", "ja": "  件 / メッセージ", "vi": "  tệp / tin nhắn"},
    "settings.max_files_tooltip": {
        "en": "Maximum number of files attachable to one message.",
        "ja": "1メッセージに添付できるファイル数の上限。",
        "vi": "Số tệp tối đa đính kèm vào một tin nhắn."},
    "settings.max_per_file": {"en": "Max per file", "ja": "ファイルあたりの上限", "vi": "Giới hạn mỗi tệp"},
    "settings.max_per_file_suffix": {"en": "  K tokens / file", "ja": "  Kトークン / ファイル", "vi": "  K tokens / tệp"},
    "settings.max_per_file_tooltip": {
        "en": ("Limits how much of each attached file's content is added to the prompt; anything "
               "beyond this is truncated (fewer tokens, avoids exceeding the context limit)."),
        "ja": "各添付ファイルの内容をプロンプトに含める量の上限。超過分は切り捨てられます（トークン削減、コンテキスト超過回避）。",
        "vi": ("Giới hạn nội dung mỗi tệp đính kèm đưa vào prompt; phần vượt sẽ bị cắt "
               "(giảm token, tránh lỗi vượt context).")},
    "settings.group.structure": {"en": "GraphRAG", "ja": "GraphRAG", "vi": "GraphRAG"},
    "settings.group.sandbox_limits": {"en": "Sandbox resource limits", "ja": "サンドボックスのリソース上限",
                                      "vi": "Giới hạn tài nguyên Sandbox"},
    "settings.max_nodes": {"en": "Max nodes", "ja": "最大ノード数", "vi": "Số node tối đa"},
    "settings.unlimited": {"en": "Unlimited", "ja": "無制限", "vi": "Không giới hạn"},
    "settings.nodes_suffix": {"en": "  nodes", "ja": "  ノード", "vi": "  node"},
    "settings.nodes_tooltip": {
        "en": ("Cap the number of nodes in the Structure graph (0 = unlimited). "
               "A lower cap speeds up scanning/layout for large folders."),
        "ja": "構造グラフのノード数上限（0＝無制限）。大きなフォルダでは低い値の方が高速です。",
        "vi": "Giới hạn số node trong đồ thị Cấu trúc (0 = không giới hạn). Giá trị thấp hơn giúp quét/vẽ nhanh hơn với thư mục lớn."},
    "settings.max_edges": {"en": "Max edges", "ja": "最大エッジ数", "vi": "Số cạnh tối đa"},
    "settings.edges_suffix": {"en": "  edges", "ja": "  エッジ", "vi": "  cạnh"},
    "settings.edges_tooltip": {
        "en": "Cap the number of edges in the Structure graph (0 = unlimited).",
        "ja": "構造グラフのエッジ数上限（0＝無制限）。",
        "vi": "Giới hạn số cạnh trong đồ thị Cấu trúc (0 = không giới hạn)."},
    "settings.tip": {
        "en": "Tip: set your Internal Gateway URL + API key above, then pick a model.",
        "ja": "ヒント: 上で社内ゲートウェイの URL と API キーを設定してからモデルを選んでください。",
        "vi": "Mẹo: điền URL Gateway nội bộ + API key ở trên, rồi chọn model."},
    "settings.loading_models": {"en": "Loading models…", "ja": "モデルを読み込み中…", "vi": "Đang tải danh sách model…"},
    "settings.loaded_models": {
        "en": "Loaded {n} model(s) for {provider}.", "ja": "{provider} のモデルを {n} 件読み込みました。",
        "vi": "Đã tải {n} model cho {provider}."},
    "settings.load_failed": {"en": "Load failed: {err}", "ja": "読み込み失敗: {err}", "vi": "Tải thất bại: {err}"},
    "settings.load_models_error": {
        "en": "No models loaded — {err}", "ja": "モデルを読み込めませんでした — {err}",
        "vi": "Không tải được model nào — {err}"},
    "settings.load_models_error_unknown": {
        "en": "unknown error (check base URL / API key / network).",
        "ja": "不明なエラー（URL・APIキー・ネットワークを確認）。",
        "vi": "lỗi không xác định (kiểm tra base URL / API key / kết nối mạng)."},
    "settings.test_connection": {"en": "Test connection", "ja": "接続テスト", "vi": "Test kết nối"},
    "settings.test_connection_tooltip": {
        "en": "Check connectivity to this provider right now and show the real reason if it fails.",
        "ja": "このプロバイダーへの接続を今すぐ確認し、失敗した場合は本当の理由を表示します。",
        "vi": "Kiểm tra kết nối tới provider này ngay và hiện lý do thật nếu thất bại."},
}
