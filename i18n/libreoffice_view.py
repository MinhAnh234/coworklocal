"""Chuỗi hiển thị — phần libreoffice_view.

Cắt ra từ ``i18n.py``: một dict 3.000 dòng không mở nổi để sửa một chữ.
Cắt theo mốc phân đoạn có sẵn, nên mỗi cụm vẫn là các màn đi liền nhau.
``i18n.py`` gộp tất cả lại thành ``STRINGS``.
"""
from __future__ import annotations

from typing import Dict

STRINGS: Dict[str, Dict[str, str]] = {
    "structure.export_title": {"en": "Export graph PNG", "ja": "グラフを PNG でエクスポート", "vi": "Xuất đồ thị ra PNG"},
    "structure.export_done": {"en": "Graph exported to {path}", "ja": "グラフを {path} にエクスポートしました", "vi": "Đã xuất đồ thị ra {path}"},
    "structure.export_failed": {"en": "Export failed: {err}", "ja": "エクスポート失敗: {err}", "vi": "Xuất thất bại: {err}"},
    "structure.scan_first": {"en": "Scan a graph first.", "ja": "先にグラフをスキャンしてください。", "vi": "Hãy Scan đồ thị trước."},
    "structure.related_sources": {
        "en": "Related files (click to open):",
        "ja": "関連ファイル（クリックで開く）:",
        "vi": "Tệp liên quan (bấm để mở):"},
    "structure.legend.dir": {"en": "Folder", "ja": "フォルダ", "vi": "Thư mục"},
    "structure.legend.file": {"en": "File", "ja": "ファイル", "vi": "Tệp"},
    "structure.legend.class": {"en": "Class", "ja": "クラス", "vi": "Class"},
    "structure.legend.function": {"en": "Function", "ja": "関数", "vi": "Function"},
    "structure.legend.method": {"en": "Method", "ja": "メソッド", "vi": "Method"},
    "structure.legend.module": {"en": "Module", "ja": "モジュール", "vi": "Module"},
    "structure.legend.section": {"en": "Section", "ja": "セクション", "vi": "Mục"},
    "structure.legend.json_key": {"en": "JSON key", "ja": "JSONキー", "vi": "Khóa JSON"},
    "structure.legend.entities": {"en": "Entities", "ja": "エンティティ", "vi": "Thực thể"},
    "structure.legend.relationships": {"en": "Relationships", "ja": "関係", "vi": "Quan hệ"},
    "structure.show_label": {"en": "Show label", "ja": "ラベル表示", "vi": "Hiện nhãn"},
    "structure.show_relationship": {
        "en": "Show relationship", "ja": "関係を表示", "vi": "Hiện quan hệ"},
    "structure.edge.contains": {"en": "contains", "ja": "含む", "vi": "chứa"},
    "structure.edge.defines": {"en": "defines", "ja": "定義", "vi": "định nghĩa"},
    "structure.edge.method": {"en": "method", "ja": "メソッド", "vi": "phương thức"},
    "structure.edge.imports": {"en": "imports", "ja": "インポート", "vi": "import"},
    "structure.edge.subsection": {"en": "subsection", "ja": "サブセクション", "vi": "mục con"},

    # ---- libreoffice_view.py -------------------------------------------
    "libreoffice.open_btn": {"en": "Open in LibreOffice", "ja": "LibreOffice で開く", "vi": "Mở bằng LibreOffice"},
    "libreoffice.not_found": {
        "en": ("LibreOffice was not found. Install LibreOffice (or set the "
               "SOFFICE_PATH environment variable) to view and edit documents here."),
        "ja": "LibreOffice が見つかりません。ここで文書を表示/編集するには LibreOffice をインストールするか、環境変数 SOFFICE_PATH を設定してください。",
        "vi": "Không tìm thấy LibreOffice. Hãy cài LibreOffice (hoặc đặt biến môi trường SOFFICE_PATH) để xem/sửa tài liệu tại đây."},
    "libreoffice.windows_only": {
        "en": "Embedding the editor is available on Windows. Click below to open this document in LibreOffice.",
        "ja": "エディタの埋め込みは Windows でのみ利用可能です。下のボタンで LibreOffice で開いてください。",
        "vi": "Nhúng trình soạn thảo chỉ khả dụng trên Windows. Bấm bên dưới để mở tài liệu bằng LibreOffice."},
    "libreoffice.start_failed": {"en": "Could not start LibreOffice ({err}).", "ja": "LibreOffice を起動できませんでした（{err}）。", "vi": "Không khởi động được LibreOffice ({err})."},
    "libreoffice.opening": {"en": "Opening the document in LibreOffice…", "ja": "LibreOffice で文書を開いています…", "vi": "Đang mở tài liệu bằng LibreOffice…"},
    "libreoffice.embed_failed": {
        "en": "Couldn't embed the LibreOffice window. You can open it in a separate window instead.",
        "ja": "LibreOffice ウィンドウを埋め込めませんでした。別ウィンドウで開くことができます。",
        "vi": "Không nhúng được cửa sổ LibreOffice. Bạn có thể mở nó ở cửa sổ riêng."},
    "libreoffice.embed_error": {"en": "Couldn't embed LibreOffice ({err}).", "ja": "LibreOffice を埋め込めませんでした（{err}）。", "vi": "Không nhúng được LibreOffice ({err})."},

    # ---- monitoring_tab.py (📊 Monitoring Dashboard) --------------------
    "monitoring.title": {"en": "Monitoring Dashboard", "ja": "モニタリングダッシュボード", "vi": "Bảng giám sát"},
    "monitoring.refresh": {"en": "Refresh", "ja": "更新", "vi": "Làm mới"},
    "monitoring.tab_security": {"en": "Security", "ja": "セキュリティ", "vi": "Bảo mật"},
    "monitoring.tab_mcp": {"en": "MCP", "ja": "MCP", "vi": "MCP"},
    "monitoring.tab_actions": {"en": "Actions", "ja": "アクション", "vi": "Hành động"},
    "monitoring.tab_agents": {"en": "Agent", "ja": "エージェント", "vi": "Agent"},
    "monitoring.tab_accounts": {"en": "Accounts", "ja": "アカウント", "vi": "Tài khoản"},
    "monitoring.col_time": {"en": "Time", "ja": "時刻", "vi": "Thời gian"},
    "monitoring.col_role": {"en": "Agent Role", "ja": "エージェント役割", "vi": "Vai trò Agent"},
    "monitoring.col_name": {"en": "Action", "ja": "アクション", "vi": "Hành động"},
    "monitoring.col_result": {"en": "Result", "ja": "結果", "vi": "Kết quả"},
    # Security Events shows WHICH rule fired instead of a result that is always
    # the same — every security_block is recorded with ok=False.
    "monitoring.col_action": {"en": "Action", "ja": "アクション", "vi": "Hành động"},
    # The fourth KPI tile on Overview, as the wireframe labels it.
    "monitoring.overview_calls": {"en": "Calls", "ja": "呼び出し", "vi": "Lượt gọi"},
    # The fold under the Sandbox summary line — the wireframe shows only the
    # summary, so the ID / created / uptime / limits rows live behind this.
    "monitoring.overview_disk_free": {
        "en": "{size} free", "ja": "空き {size}", "vi": "{size} trống"},
    "monitoring.overview_disk_label": {"en": "Disk", "ja": "ディスク", "vi": "Đĩa"},
    "monitoring.overview_sbx_detail": {
        "en": "Details", "ja": "詳細", "vi": "Chi tiết"},
    "monitoring.col_detail": {"en": "Detail", "ja": "詳細", "vi": "Chi tiết"},
    "monitoring.col_account": {"en": "Account", "ja": "アカウント", "vi": "Tài khoản"},
    "monitoring.col_machine": {"en": "Machine", "ja": "マシン", "vi": "Máy"},
    "monitoring.col_agent": {"en": "Agent", "ja": "エージェント", "vi": "Agent"},
    "monitoring.col_source": {"en": "Source", "ja": "ソース", "vi": "Nguồn"},
    "monitoring.active_n": {"en": "{n} running", "ja": "{n} 件実行中", "vi": "{n} đang chạy"},
    "monitoring.idle": {"en": "Idle", "ja": "アイドル", "vi": "Rảnh"},
    "monitoring.agent_status_title": {
        "en": "Agent Status", "ja": "エージェント状態", "vi": "Trạng thái Agent"},
    "monitoring.source_cowork": {
        "en": "Cowork tab's active turns", "ja": "Cowork タブの実行中ターン",
        "vi": "Lượt đang chạy của tab Cowork"},
    "monitoring.source_task": {
        "en": "Schedule Task's running tasks", "ja": "Schedule Task の実行中タスク",
        "vi": "Task đang chạy trong Schedule Task"},
    "monitoring.source_knowledge": {
        "en": "GraphRAG's Ask box", "ja": "GraphRAG の Ask ボックス", "vi": "Ô hỏi của GraphRAG"},
    "monitoring.source_code": {
        "en": "Runs inside a Task Agent run when the task type is Code",
        "ja": "タスクタイプが Code の場合、Task Agent の実行内で動作します",
        "vi": "Chạy bên trong một lượt Task Agent khi loại task là Code"},
    "monitoring.source_planner": {
        "en": "A phase inside a running Cowork/Task turn (update_plan) — not tracked separately",
        "ja": "実行中の Cowork/Task ターン内の一段階（update_plan）— 個別には追跡されません",
        "vi": "Một giai đoạn trong lượt Cowork/Task đang chạy (update_plan) — không theo dõi riêng"},
    "monitoring.source_reasoning": {
        "en": "The model's streamed reasoning within a running turn — not tracked separately",
        "ja": "実行中のターン内でモデルがストリーミングする推論 — 個別には追跡されません",
        "vi": "Luồng suy luận (reasoning) của model trong lượt đang chạy — không theo dõi riêng"},
    "monitoring.source_security": {
        "en": "Agent Security's prompt/attachment/command validation — runs inline on the active turn",
        "ja": "エージェントセキュリティのプロンプト/添付/コマンド検証 — 実行中のターン内でインライン実行",
        "vi": "Kiểm duyệt prompt/đính kèm/lệnh của Agent Security — chạy inline trong lượt đang chạy"},
    "monitoring.on": {"en": "On", "ja": "オン", "vi": "Bật"},
    "monitoring.off": {"en": "Off", "ja": "オフ", "vi": "Tắt"},

    # ---- monitoring_tab.py — Overview card dashboard ---------------------
    "monitoring.tab_overview": {"en": "Overview", "ja": "概要", "vi": "Tổng quan"},
    "monitoring.overview_usage_title": {
        "en": "Token & Cost", "ja": "トークンとコスト", "vi": "Token & Chi phí"},
    "monitoring.overview_currency": {"en": "Currency:", "ja": "通貨:", "vi": "Tiền tệ:"},
    "monitoring.tab_agents_admin": {
        "en": "Agents Admin", "ja": "エージェント管理", "vi": "Agents Admin"},
    "monitoring.tab_tools": {"en": "Tools", "ja": "ツール", "vi": "Công cụ"},

    # ---- tools_admin_tab.py — govern built-in tools + Connectors/MCP -------
    "tools_admin.hint": {
        "en": "Enable or disable the built-in agent tools below. A tool toggled off is removed "
              "from the agent's toolset. MCP / REST-API connectors are set up in the Connector "
              "sub-tab.",
        "ja": "下の組み込みエージェントツールをオン/オフします。オフにしたツールはツールセットから除外"
              "されます。MCP / REST-APIコネクターは「Connector」サブタブで設定します。",
        "vi": "Bật/tắt các tool tích hợp bên dưới. Tool bị tắt sẽ bị loại khỏi bộ công cụ của agent. "
              "Connector MCP / REST-API được thiết lập ở tab con Connector."},
    "tools_admin.refresh": {"en": "Refresh", "ja": "更新", "vi": "Làm mới"},
    # Mô tả tool HIỂN THỊ trên thẻ, một khoá cho mỗi ``TOOL_SPECS[].name``.
    # KHÔNG dùng ``spec.description``: chuỗi đó là mô tả gửi cho mô hình trong
    # schema function-calling, phải giữ nguyên tiếng Anh và viết cho máy đọc.
    "tools_admin.desc.read_file": {
        "en": "Read the contents of a text file in the working folder.",
        "ja": "作業フォルダー内のテキストファイルの内容を読み取ります。",
        "vi": "Đọc nội dung một tệp văn bản trong thư mục làm việc."},
    "tools_admin.desc.list_dir": {
        "en": "List files and subfolders at a path (defaults to the workdir root).",
        "ja": "指定パスのファイルとサブフォルダーを一覧表示します（既定は作業フォルダー直下）。",
        "vi": "Liệt kê tệp và thư mục con tại một đường dẫn (mặc định là gốc thư mục làm việc)."},
    "tools_admin.desc.write_file": {
        "en": "Create a new file or fully rewrite one. For small edits, prefer edit_file.",
        "ja": "ファイルを新規作成、または全体を書き換えます。小さな修正には edit_file を使います。",
        "vi": "Tạo tệp mới hoặc ghi đè toàn bộ. Sửa nhỏ thì nên dùng edit_file."},
    "tools_admin.desc.edit_file": {
        "en": "Replace an exact snippet inside an existing file — preferred for small edits.",
        "ja": "既存ファイル内の特定の箇所を置き換えます。小さな修正に適しています。",
        "vi": "Thay chính xác một đoạn trong tệp có sẵn — hợp cho các sửa đổi nhỏ."},
    "tools_admin.desc.run_command": {
        "en": "Run a shell command in the working folder and return its output.",
        "ja": "作業フォルダーでシェルコマンドを実行し、その出力を返します。",
        "vi": "Chạy một lệnh shell trong thư mục làm việc và trả về kết quả."},
    "tools_admin.desc.install_package": {
        "en": "Install a Python package (pip) so the task can use a missing library.",
        "ja": "不足しているライブラリを使えるよう Python パッケージ（pip）をインストールします。",
        "vi": "Cài gói Python (pip) để tác vụ dùng được thư viện còn thiếu."},
    "tools_admin.desc.fetch_url": {
        "en": "Fetch a web page or online document by URL and return its text.",
        "ja": "URL から Web ページやオンライン文書を取得し、テキストを返します。",
        "vi": "Tải trang web hoặc tài liệu trực tuyến theo URL và trả về nội dung văn bản."},
    "tools_admin.desc.jira_search": {
        "en": "Search Jira issues with a JQL query and return a summary list. Read-only.",
        "ja": "JQL クエリで Jira の課題を検索し、一覧を返します。読み取り専用です。",
        "vi": "Tìm issue Jira bằng truy vấn JQL và trả về danh sách tóm tắt. Chỉ đọc."},
    "tools_admin.desc.jira_get_issue": {
        "en": "Read one Jira issue's details by key, e.g. ABX-123.",
        "ja": "キー（例: ABX-123）を指定して Jira 課題の詳細を読み取ります。",
        "vi": "Đọc chi tiết một issue Jira theo mã, ví dụ ABX-123."},
    "tools_admin.url_fetch_group": {
        "en": "Web access (fetch_url)", "ja": "Webアクセス (fetch_url)",
        "vi": "Truy cập web (fetch_url)"},
    "tools_admin.internet_disabled": {
        "en": "Web access is OFF — enable the fetch_url tool above to allow internet access.",
        "ja": "Web アクセスはオフです — 上の fetch_url ツールを有効にするとインターネットに接続できます。",
        "vi": "Truy cập web đang TẮT — bật tool fetch_url ở trên để cho phép truy cập internet."},
    "tools_admin.subtab_tool": {"en": "Tool", "ja": "ツール", "vi": "Tool"},
    "tools_admin.subtab_connector": {"en": "Connector", "ja": "コネクター", "vi": "Connector"},
    "monitoring.tab_icons": {"en": "Icons", "ja": "アイコン", "vi": "Icon"},
    "icons_admin.title": {"en": "Icons", "ja": "アイコン", "vi": "Icon"},
    "icons_admin.hint": {
        "en": "Icons you can use for agents and flows. Type a name into a step/agent's Icon field to "
              "use it. Add your own SVG icons below — they become usable by name immediately.",
        "ja": "エージェントやフローに使えるアイコン。ステップ/エージェントのアイコン欄に名前を入力すると使えます。"
              "下から独自のSVGアイコンを追加でき、名前ですぐ使えます。",
        "vi": "Các icon dùng cho agent và flow. Gõ tên vào ô Icon của step/agent để dùng. Thêm icon SVG "
              "của bạn ở dưới — dùng được ngay bằng tên."},
    "icons_admin.search": {"en": "Search icons by name…", "ja": "名前でアイコンを検索…", "vi": "Tìm icon theo tên…"},
    "icons_admin.builtin": {"en": "Built-in icons", "ja": "組込みアイコン", "vi": "Icon tích hợp"},
    "icons_admin.custom": {"en": "Custom icons", "ja": "カスタムアイコン", "vi": "Icon tùy chỉnh"},
    "icons_admin.add": {"en": "Add SVG file", "ja": "SVGファイルを追加", "vi": "Thêm tệp SVG"},
    "icons_admin.paste": {"en": "Paste SVG", "ja": "SVGを貼付", "vi": "Dán SVG"},
    "icons_admin.paste_prompt": {"en": "Paste the SVG markup:", "ja": "SVGマークアップを貼り付け：",
                                 "vi": "Dán mã SVG:"},
    "icons_admin.delete": {"en": "Delete custom", "ja": "カスタムを削除", "vi": "Xóa tùy chỉnh"},
    "icons_admin.name_prompt": {"en": "Icon name (used in the Icon field)", "ja": "アイコン名（アイコン欄で使用）",
                                "vi": "Tên icon (dùng ở ô Icon)"},
    "icons_admin.select_custom": {"en": "Select a custom icon to delete.",
                                  "ja": "削除するカスタムアイコンを選択してください。",
                                  "vi": "Hãy chọn một icon tùy chỉnh để xóa."},
    "tools_admin.jira_note": {
        "en": "Jira connection setup moved to the Connector tab → set it up there; here you only turn "
              "the jira_search / jira_get_issue tools on or off.",
        "ja": "Jira接続の設定はConnectorタブに移動しました。設定はそちらで。ここでは jira_search / "
              "jira_get_issue ツールの有効/無効のみ切り替えます。",
        "vi": "Phần thiết lập kết nối Jira đã chuyển sang tab Connector → cài đặt ở đó; ở đây chỉ bật/tắt "
              "tool jira_search / jira_get_issue."},
    "connectors.jira_group": {"en": "Jira (read)", "ja": "Jira（読み取り）", "vi": "Jira (đọc)"},
    "connectors.jira_hint": {
        "en": "Connect once, then just paste a Jira link into Cowork or a Co4E step — the agent reads it "
              "automatically (no issue key needed). Read-only. A public Jira link works with no setup; "
              "a private one needs this connection. Create a token: id.atlassian.com → Security → API tokens.",
        "ja": "一度接続すれば、Cowork や Co4E ステップに Jira リンクを貼るだけで自動で読み取ります（課題キー不要）。"
              "読み取り専用。公開リンクは設定不要、非公開はこの接続が必要。トークン作成: id.atlassian.com → セキュリティ → APIトークン。",
        "vi": "Kết nối một lần, rồi chỉ cần dán link Jira vào Cowork hoặc bước Co4E — agent tự đọc (không cần "
              "issue key). Chỉ đọc. Link Jira công khai không cần cài đặt; link riêng tư cần kết nối này. "
              "Tạo token: id.atlassian.com → Security → API tokens."},
    "connectors.jira_paste": {"en": "Paste a link", "ja": "リンクを貼付", "vi": "Dán link"},
    "connectors.jira_paste_placeholder": {
        "en": "Paste any Jira link — fills the base URL for you",
        "ja": "Jiraのリンクを貼ると、ベースURLが自動入力されます",
        "vi": "Dán bất kỳ link Jira nào — tự điền Base URL"},
    "connectors.jira_url": {"en": "Base URL", "ja": "ベースURL", "vi": "Base URL"},
    "connectors.jira_email": {"en": "Email", "ja": "メール", "vi": "Email"},
    "connectors.jira_token": {"en": "API token", "ja": "APIトークン", "vi": "API token"},
    "connectors.jira_save": {"en": "Save", "ja": "保存", "vi": "Lưu"},
    "connectors.jira_test": {"en": "Test connection", "ja": "接続テスト", "vi": "Kiểm tra kết nối"},
    "connectors.jira_saved": {"en": "Saved.", "ja": "保存しました。", "vi": "Đã lưu."},
    "connectors.jira_connected": {"en": "connected", "ja": "接続済み", "vi": "đã kết nối"},
    "connectors.jira_not_set": {"en": "not configured", "ja": "未設定", "vi": "chưa cấu hình"},
    "connectors.jira_setup_hint": {
        "en": "Double-click to connect Jira (paste any Jira link — no per-request setup after that).",
        "ja": "ダブルクリックで Jira に接続（Jira リンクを貼るだけ、以降は設定不要）。",
        "vi": "Nhấp đúp để kết nối Jira (dán bất kỳ link Jira nào — sau đó không cần thiết lập gì thêm)."},
    "connectors.builtin_auto": {
        "en": "Built-in, connects automatically", "ja": "組み込み、自動接続",
        "vi": "Tích hợp, tự kết nối"},
    "connectors.connect_external": {
        "en": "Connect to external connectors",
        "ja": "外部コネクタに接続する",
        "vi": "Kết nối tới connector bên ngoài"},
    "connectors.connect_external_tooltip": {
        "en": ("Master switch (default ON): when off, the agent connects to NO external "
               "connector or MCP server — the per-connector settings below are ignored."),
        "ja": "マスタースイッチ（既定オン）: オフにすると、エージェントは外部コネクタ／MCPサーバーに"
              "一切接続しません（下の個別設定は無視されます）。",
        "vi": ("Công tắc tổng (mặc định BẬT): khi tắt, agent sẽ KHÔNG kết nối tới bất kỳ connector "
               "hay MCP server bên ngoài nào — các thiết lập từng connector bên dưới bị bỏ qua.")},
    "connectors.jira_testing": {"en": "Testing…", "ja": "テスト中…", "vi": "Đang kiểm tra…"},
    "connectors.jira_ok": {"en": "✓ Connected to Jira.", "ja": "✓ Jiraに接続できました。", "vi": "✓ Kết nối Jira thành công."},
    "connectors.jira_fail": {"en": "✗ {err}", "ja": "✗ {err}", "vi": "✗ {err}"},
    "connectors.jira_need_fields": {
        "en": "Enter base URL, email and API token first.",
        "ja": "先にベースURL・メール・APIトークンを入力してください。",
        "vi": "Hãy nhập Base URL, Email và API token trước."},
    "tools_admin.jira_group": {"en": "Jira connection", "ja": "Jira 接続", "vi": "Kết nối Jira"},
    "tools_admin.jira_hint": {
        "en": "Connect once, then just paste a Jira issue link into Cowork or a Co4E step — the agent "
              "reads it automatically (no issue key needed). Read-only. Private Jira needs this one-time "
              "connection; a public Jira link works with no setup. API token: id.atlassian.com → "
              "Security → API tokens. Turn the jira tools on/off in the list above.",
        "ja": "一度接続すれば、あとは Cowork や Co4E ステップに Jira のリンクを貼るだけで自動的に読み取ります"
              "（課題キー不要）。読み取り専用。非公開Jiraはこの一度の接続が必要、公開リンクは設定不要。"
              "APIトークン: id.atlassian.com → セキュリティ → APIトークン。ツールの有効/無効は上の一覧で。",
        "vi": "Kết nối một lần, sau đó chỉ cần dán link Jira vào Cowork hoặc bước Co4E — agent tự đọc "
              "(không cần nhập issue key). Chỉ đọc. Jira riêng tư cần kết nối một lần này; link Jira công "
              "khai thì không cần cài đặt. API token: id.atlassian.com → Security → API tokens. Bật/tắt "
              "tool jira ở danh sách phía trên."},
    "tools_admin.jira_url": {"en": "Base URL", "ja": "ベースURL", "vi": "Base URL"},
    "tools_admin.jira_email": {"en": "Email", "ja": "メール", "vi": "Email"},
    "tools_admin.jira_token": {"en": "API token", "ja": "APIトークン", "vi": "API token"},
    "tools_admin.jira_save": {"en": "Save", "ja": "保存", "vi": "Lưu"},
    "tools_admin.jira_test": {"en": "Test connection", "ja": "接続テスト", "vi": "Kiểm tra kết nối"},
    "tools_admin.jira_saved": {"en": "Saved.", "ja": "保存しました。", "vi": "Đã lưu."},
    "tools_admin.jira_testing": {"en": "Testing…", "ja": "テスト中…", "vi": "Đang kiểm tra…"},
    "tools_admin.jira_ok": {"en": "✓ Connected to Jira.", "ja": "✓ Jiraに接続できました。", "vi": "✓ Kết nối Jira thành công."},
    "tools_admin.jira_fail": {"en": "✗ {err}", "ja": "✗ {err}", "vi": "✗ {err}"},
    "tools_admin.jira_need_fields": {
        "en": "Enter base URL, email and API token first.",
        "ja": "先にベースURL・メール・APIトークンを入力してください。",
        "vi": "Hãy nhập Base URL, Email và API token trước."},
    # ---- Co4E (node-graph workflow studio) --------------------------------
    "workspace.tab_co4e": {"en": "Co4E", "ja": "Co4E", "vi": "Co4E"},
    "workspace.tab_co4e_tooltip": {
        "en": "Co4E — Code for Everyone, Cowork for Everyone",
        "ja": "Co4E — Code for Everyone, Cowork for Everyone",
        "vi": "Co4E — Code for Everyone, Cowork for Everyone",
    },
    "co4e.untitled": {"en": "Untitled flow", "ja": "無題のフロー", "vi": "Flow chưa đặt tên"},
    "co4e.tab_workflows": {"en": "Workflows", "ja": "ワークフロー", "vi": "Workflows"},
    "co4e.tab_agents": {"en": "Agents", "ja": "エージェント", "vi": "Agents"},
    "co4e.tab_skills": {"en": "Skills", "ja": "スキル", "vi": "Skills"},
    "co4e.new": {"en": "New", "ja": "新規", "vi": "Mới"},
    "co4e.load": {"en": "Load", "ja": "読み込み", "vi": "Tải"},
    "co4e.delete": {"en": "Delete", "ja": "削除", "vi": "Xóa"},
    "co4e.edit": {"en": "Edit", "ja": "編集", "vi": "Sửa"},
    "co4e.new_agent": {"en": "New agent", "ja": "新規エージェント", "vi": "Agent mới"},
    "co4e.manage_skills": {"en": "Manage skills…", "ja": "スキル管理…", "vi": "Quản lý skill…"},
    "co4e.template": {"en": "template", "ja": "テンプレート", "vi": "mẫu"},
    "co4e.saved": {"en": "saved", "ja": "保存済み", "vi": "đã lưu"},
    "co4e.custom": {"en": "custom", "ja": "カスタム", "vi": "tùy chỉnh"},
    "co4e.parallel_node": {"en": "Parallel (fan-out)", "ja": "並列（ファンアウト）", "vi": "Song song (fan-out)"},
    "co4e.add_step": {"en": "Add step", "ja": "ステップ追加", "vi": "Thêm bước"},
    "co4e.canvas_add_next": {
        "en": "Add next step", "ja": "次のステップを追加", "vi": "Thêm bước kế"},
    "co4e.canvas_connect_from": {
        "en": "Connect from here", "ja": "ここから接続", "vi": "Nối từ đây"},
    "co4e.canvas_delete_edge": {
        "en": "Delete connection", "ja": "接続を削除", "vi": "Xóa liên kết"},
    "co4e.fit": {"en": "Fit", "ja": "全体表示", "vi": "Vừa màn hình"},
    "co4e.fit_tooltip": {
        "en": "Auto-fit: zoom to show every step", "ja": "自動フィット：全ステップを表示",
        "vi": "Tự canh: thu phóng để thấy tất cả bước"},
    "co4e.drag_hint": {
        "en": "Drag a flow or agent onto the canvas (double-click a flow to load it).",
        "ja": "フローやエージェントをキャンバスにドラッグ（フローはダブルクリックで読み込み）。",
        "vi": "Kéo một flow hoặc agent vào canvas (double-click flow để tải)."},
    "co4e.blank_step": {"en": "Blank step", "ja": "空のステップ", "vi": "Bước trống"},
    "co4e.pick_agent": {"en": "Choose an agent", "ja": "エージェントを選択", "vi": "Chọn agent"},
    "co4e.ai_draft": {"en": "Draft with AI", "ja": "AIで下書き", "vi": "Soạn bằng AI"},
    "co4e.ai_draft_tooltip": {
        "en": "Let AI write this agent's instructions from its name and role (no skill needed).",
        "ja": "エージェントの名前と役割から指示文をAIが作成（スキル不要）。",
        "vi": "Để AI viết hướng dẫn cho agent từ tên và vai trò (không cần skill)."},
    "co4e.ai_draft_hint_title": {"en": "Draft with AI", "ja": "AIで下書き", "vi": "Soạn bằng AI"},
    "co4e.ai_draft_hint_label": {
        "en": "Describe what this agent should do (optional — leave blank to draft from just "
              "the name/role). More detail here → more detailed instructions.",
        "ja": "このエージェントが何をすべきか説明してください（任意 — 空欄なら名前/役割のみから"
              "下書き）。詳しく書くほど、生成される指示も詳細になります。",
        "vi": "Mô tả agent này nên làm gì (không bắt buộc — để trống sẽ soạn chỉ từ tên/vai trò). "
              "Mô tả chi tiết hơn → hướng dẫn được tạo ra chi tiết hơn."},
    "co4e.tt_add_step": {"en": "Add a blank step to the canvas", "ja": "空のステップをキャンバスに追加",
                         "vi": "Thêm một bước trống vào canvas"},
    "co4e.tt_save": {"en": "Save this flow", "ja": "このフローを保存", "vi": "Lưu flow này"},
    "co4e.tt_save_template": {"en": "Save as a reusable template", "ja": "再利用テンプレートとして保存",
                             "vi": "Lưu thành mẫu dùng lại"},
    "co4e.tt_run": {"en": "Run the flow (or Interrupt while running)", "ja": "フローを実行（実行中は中断）",
                    "vi": "Chạy flow (hoặc Dừng khi đang chạy)"},
    "co4e.tt_mode": {
        "en": "Auto = each step plans then runs · Plan = dry-run a plan (read-only) · Manual = step-by-step (advance with Next step)",
        "ja": "Auto=各ステップが計画して実行 · Plan=計画のみ（読取専用）· Manual=1ステップずつ（「次へ」で進む）",
        "vi": "Auto = mỗi bước tự lập kế hoạch rồi chạy · Plan = chỉ lập kế hoạch (chỉ đọc) · Manual = từng bước (bấm Bước tiếp)"},
    "co4e.tt_new_wf": {"en": "Start a new empty flow", "ja": "新しい空のフロー", "vi": "Tạo flow mới trống"},
    "co4e.tt_load_wf": {"en": "Load the selected flow into the canvas",
                        "ja": "選択したフローをキャンバスに読み込み", "vi": "Tải flow đã chọn vào canvas"},
    "co4e.tt_del_wf": {"en": "Delete the selected saved flow", "ja": "選択した保存フローを削除",
                       "vi": "Xóa flow đã lưu đang chọn"},
    "co4e.tt_edit_wf": {"en": "Edit the selected flow", "ja": "選択したフローを編集",
                        "vi": "Sửa flow đang chọn"},
    "co4e.tt_new_agent": {"en": "Create a custom agent persona", "ja": "カスタムエージェントを作成",
                          "vi": "Tạo một agent tùy chỉnh"},
    "co4e.tt_edit_agent": {"en": "Edit the selected custom agent", "ja": "選択したカスタムエージェントを編集",
                           "vi": "Sửa agent tùy chỉnh đang chọn"},
    "co4e.tt_del_agent": {"en": "Delete the selected custom agent", "ja": "選択したカスタムエージェントを削除",
                          "vi": "Xóa agent tùy chỉnh đang chọn"},
    "co4e.tt_manage_skills": {"en": "Open the Skills manager", "ja": "スキル管理を開く",
                              "vi": "Mở trình quản lý Skill"},
    "co4e.save": {"en": "Save", "ja": "保存", "vi": "Lưu"},
    "co4e.save_template": {"en": "Save as Template", "ja": "テンプレートとして保存", "vi": "Lưu làm mẫu"},
    "co4e.flow_name": {"en": "Flow", "ja": "フロー", "vi": "Flow"},
    "co4e.run": {"en": "Run", "ja": "実行", "vi": "Chạy"},
    "co4e.interrupt": {"en": "Interrupt", "ja": "中断", "vi": "Dừng"},
    "co4e.add": {"en": "Add", "ja": "追加", "vi": "Thêm"},
    "co4e.config_title": {"en": "Step config", "ja": "ステップ設定", "vi": "Cấu hình bước"},
    "co4e.tt_collapse_config": {"en": "Collapse the config panel", "ja": "設定パネルを折りたたむ",
                                "vi": "Thu gọn bảng cấu hình"},
    "co4e.tt_expand_config": {"en": "Expand the config panel", "ja": "設定パネルを展開",
                              "vi": "Mở rộng bảng cấu hình"},
    "co4e.messages": {"en": "Messages", "ja": "メッセージ", "vi": "Tin nhắn"},
    "co4e.tt_collapse_msgs": {"en": "Collapse the messages panel", "ja": "メッセージを折りたたむ",
                              "vi": "Thu gọn khung tin nhắn"},
    "co4e.tt_expand_msgs": {"en": "Expand the messages panel", "ja": "メッセージを展開",
                            "vi": "Mở rộng khung tin nhắn"},
    "co4e.mode.auto": {"en": "Auto", "ja": "自動", "vi": "Auto"},
    "co4e.mode.plan": {"en": "Plan", "ja": "計画", "vi": "Plan"},
    "co4e.mode.manual": {"en": "Manual", "ja": "手動", "vi": "Manual"},
    # --- Co4E run manager / duplicate / status / zoom (parallel flows) ---
    "co4e.copy_suffix": {"en": "copy", "ja": "コピー", "vi": "bản sao"},
    "co4e.tt_dup_wf": {"en": "Duplicate the selected flow (run copies in parallel)",
                       "ja": "選択フローを複製（コピーを並列実行）", "vi": "Nhân bản flow đã chọn (chạy bản sao song song)"},
}
