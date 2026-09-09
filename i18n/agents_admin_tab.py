"""Chuỗi hiển thị — phần agents_admin_tab.

Cắt ra từ ``i18n.py``: một dict 3.000 dòng không mở nổi để sửa một chữ.
Cắt theo mốc phân đoạn có sẵn, nên mỗi cụm vẫn là các màn đi liền nhau.
``i18n.py`` gộp tất cả lại thành ``STRINGS``.
"""
from __future__ import annotations

from typing import Dict

STRINGS: Dict[str, Dict[str, str]] = {
    "co4e.tt_flow_name": {"en": "Flow name", "ja": "フロー名", "vi": "Tên flow"},
    "co4e.tt_add_step": {"en": "Add a step to the canvas", "ja": "キャンバスにステップを追加",
                         "vi": "Thêm một bước vào canvas"},
    "co4e.tt_zoom_in": {"en": "Zoom in (Ctrl+wheel / Ctrl++)", "ja": "拡大（Ctrl+ホイール / Ctrl++）",
                        "vi": "Phóng to (Ctrl+lăn chuột / Ctrl++)"},
    "co4e.tt_zoom_out": {"en": "Zoom out (Ctrl+wheel / Ctrl+-)", "ja": "縮小（Ctrl+ホイール / Ctrl+-）",
                         "vi": "Thu nhỏ (Ctrl+lăn chuột / Ctrl+-)"},
    "co4e.run_bg": {"en": "Run", "ja": "実行", "vi": "Chạy"},
    "co4e.tt_run_bg": {
        "en": "Run the selected flow in the background — several flows run in parallel",
        "ja": "選択フローをバックグラウンド実行 — 複数フローを並列実行",
        "vi": "Chạy flow đã chọn ở nền — nhiều flow chạy song song"},
    "co4e.running_flows": {"en": "Running flows", "ja": "実行中のフロー", "vi": "Flow đang chạy"},
    "co4e.runs_tab": {"en": "Flow Status", "ja": "フロー状態", "vi": "Flow Status"},
    # The flow tab strip was removed, so its pinned Flow Status tab became a
    # toggle in the flow toolbar — and that page needs its own way back.
    "co4e.tt_runs_tab": {
        "en": "Show every flow run", "ja": "すべてのフロー実行を表示",
        "vi": "Xem toàn bộ lần chạy flow"},
    "co4e.back_to_flow": {"en": "Back to flow", "ja": "フローに戻る", "vi": "Về flow"},
    "co4e.new_flow_ready": {
        "en": "New flow — type a name, then drag agents onto the canvas",
        "ja": "新しいフロー — 名前を入力し、エージェントをキャンバスへ",
        "vi": "Flow mới — đặt tên rồi kéo agent vào canvas"},
    "co4e.tt_back_to_flow": {
        "en": "Back to the flow editor", "ja": "フローエディタに戻る",
        "vi": "Quay lại màn dựng flow"},
    "co4e.runs_tab_n": {"en": "Flow Status ({n})", "ja": "フロー状態 ({n})", "vi": "Flow Status ({n})"},
    "co4e.runs_col_flow": {"en": "Flow", "ja": "フロー", "vi": "Flow"},
    "co4e.runs_col_status": {"en": "Status", "ja": "状態", "vi": "Trạng thái"},
    "co4e.runs_col_steps": {"en": "Steps", "ja": "ステップ", "vi": "Bước"},
    "co4e.runs_col_by": {"en": "Created by", "ja": "作成者", "vi": "Người tạo"},
    "co4e.runs_col_at": {"en": "Created at", "ja": "作成日時", "vi": "Ngày tạo"},
    "co4e.tt_runs_list": {
        "en": "Live status of every running/finished flow — always up to date. Double-click a run to run that flow again.",
        "ja": "実行中／完了フローのライブ状態 — 常に最新。実行をダブルクリックでそのフローを再実行。",
        "vi": "Trạng thái trực tiếp của mọi flow đang chạy/đã xong — luôn mới nhất. Nhấp đúp để chạy lại flow đó."},
    "co4e.flow_gone": {"en": "That flow no longer exists.", "ja": "そのフローは存在しません。",
                       "vi": "Flow đó không còn tồn tại."},
    "co4e.rename": {"en": "Rename", "ja": "名前を変更", "vi": "Đổi tên"},
    "co4e.rename_prompt": {"en": "New flow name (name it by its function / task):",
                           "ja": "新しいフロー名（機能／タスクで命名）:",
                           "vi": "Tên flow mới (đặt theo chức năng / task):"},
    "co4e.renamed_msg": {"en": "Renamed to: {name}", "ja": "名前変更: {name}", "vi": "Đã đổi tên: {name}"},
    "co4e.duplicate": {"en": "Duplicate", "ja": "複製", "vi": "Nhân bản"},
    "co4e.viewing_flow": {"en": "Viewing flow: {name}", "ja": "フロー表示: {name}", "vi": "Đang xem flow: {name}"},
    "co4e.stop": {"en": "Stop", "ja": "停止", "vi": "Dừng"},
    "co4e.tt_stop_run": {"en": "Stop the selected run (or all runs if none selected)",
                         "ja": "選択した実行を停止（未選択なら全実行）", "vi": "Dừng lần chạy đã chọn (hoặc tất cả nếu chưa chọn)"},
    "co4e.clear_done": {"en": "Clear done", "ja": "完了を消去", "vi": "Xóa đã xong"},
    "co4e.tt_clear_runs": {"en": "Remove finished/stopped runs from the list",
                           "ja": "完了／停止した実行を一覧から削除", "vi": "Bỏ các lần chạy đã xong/đã dừng khỏi danh sách"},
    "co4e.select_flow": {"en": "Select a flow first.", "ja": "先にフローを選択してください。",
                         "vi": "Hãy chọn một flow trước."},
    "co4e.delete_run": {"en": "Delete", "ja": "削除", "vi": "Xóa"},
    "co4e.tt_delete_run": {"en": "Delete the selected run from the history",
                           "ja": "選択した実行を履歴から削除", "vi": "Xóa lần chạy đang chọn khỏi lịch sử"},
    "co4e.open_run": {"en": "Open flow", "ja": "フローを開く", "vi": "Mở flow"},
    "co4e.open_output": {"en": "Open output folder", "ja": "出力フォルダを開く", "vi": "Mở thư mục output"},
    "co4e.open_output_link": {
        "en": "📂 Open output folder", "ja": "📂 出力フォルダを開く", "vi": "📂 Mở thư mục output"},
    "co4e.tt_open_workspace": {
        "en": "Open the workspace folder where flow outputs are saved:\n{path}",
        "ja": "フローの出力が保存されるワークスペースフォルダを開く:\n{path}",
        "vi": "Mở thư mục workspace nơi lưu output của flow:\n{path}"},
    "co4e.select_run": {"en": "Select a run first.", "ja": "先に実行を選択してください。",
                        "vi": "Hãy chọn một lần chạy trước."},
    "co4e.rename_run": {"en": "Rename", "ja": "名前変更", "vi": "Đổi tên"},
    "co4e.tt_rename_run": {"en": "Rename the selected flow run",
                           "ja": "選択した実行の名前を変更", "vi": "Đổi tên lần chạy đang chọn"},
    "co4e.rename_run_label": {"en": "New flow name:", "ja": "新しいフロー名:", "vi": "Tên flow mới:"},
    "co4e.run_done_title": {"en": "Flow finished", "ja": "フロー完了", "vi": "Flow đã xong"},
    "co4e.run_done_popup": {
        "en": "Flow \"{name}\" finished — {status}.",
        "ja": "フロー「{name}」が完了しました — {status}。",
        "vi": "Flow \"{name}\" đã chạy xong — {status}."},
    "co4e.duplicated_msg": {"en": "Duplicated: {name}", "ja": "複製しました: {name}", "vi": "Đã nhân bản: {name}"},
    "co4e.bg_started": {"en": "▶ Started in background: {name}", "ja": "▶ バックグラウンドで開始: {name}",
                        "vi": "▶ Đã chạy nền: {name}"},
    "co4e.bg_done": {"en": "Flow '{name}': {status}", "ja": "フロー '{name}': {status}",
                     "vi": "Flow '{name}': {status}"},
    "co4e.tool_failed": {"en": "⚠ tool failed: {name}", "ja": "⚠ ツール失敗: {name}", "vi": "⚠ tool lỗi: {name}"},
    "co4e.manual_started": {"en": "▶ Manual run: {name} — advance with Run/Next step.",
                            "ja": "▶ 手動実行: {name} — 「実行/次へ」で進む。",
                            "vi": "▶ Chạy thủ công: {name} — bấm Chạy/Bước tiếp để tiến."},
    "co4e.manual_step": {"en": "▶ Step {i}/{n}: {label}", "ja": "▶ ステップ {i}/{n}: {label}",
                         "vi": "▶ Bước {i}/{n}: {label}"},
    "co4e.status.running": {"en": "running", "ja": "実行中", "vi": "đang chạy"},
    "co4e.status.done": {"en": "done", "ja": "完了", "vi": "xong"},
    "co4e.status.error": {"en": "error", "ja": "エラー", "vi": "lỗi"},
    "co4e.status.stopped": {"en": "stopped", "ja": "停止", "vi": "đã dừng"},
    "co4e.chat_placeholder": {
        "en": "Chat with the flow — use /agent:<name> or /skill:<name>",
        "ja": "フローとチャット — /agent:<name> または /skill:<name>",
        "vi": "Chat với flow — dùng /agent:<name> hoặc /skill:<name>"},
    "co4e.send": {"en": "Send", "ja": "送信", "vi": "Gửi"},
    "co4e.tab_basic": {"en": "Basic", "ja": "基本", "vi": "Cơ bản"},
    "co4e.tab_model_perm": {"en": "Model & Permission", "ja": "モデルと権限", "vi": "Model & Quyền"},
    "co4e.tab_skills_files": {"en": "Skills & Files", "ja": "スキルとファイル", "vi": "Skills & Tệp"},
    "co4e.f_label": {"en": "Label", "ja": "ラベル", "vi": "Nhãn"},
    "co4e.f_role": {"en": "Role", "ja": "ロール", "vi": "Vai trò"},
    "co4e.f_name": {"en": "Name", "ja": "名前", "vi": "Tên"},
    "co4e.f_icon": {"en": "Icon", "ja": "アイコン", "vi": "Icon"},
    "co4e.f_icon_placeholder": {"en": "icon name (optional)", "ja": "アイコン名（任意）", "vi": "tên icon (tùy chọn)"},
    "co4e.f_instructions": {"en": "Instructions", "ja": "指示", "vi": "Hướng dẫn"},
    "co4e.f_context": {"en": "Context", "ja": "コンテキスト", "vi": "Ngữ cảnh"},
    "co4e.f_context_placeholder": {
        "en": "Extra background/info for this agent or step (added to its prompt at run time).",
        "ja": "このエージェント/ステップ用の追加情報（実行時にプロンプトへ追加されます）。",
        "vi": "Thông tin/ngữ cảnh bổ sung cho agent hoặc step này (thêm vào prompt khi chạy)."},
    "co4e.f_model": {"en": "Model", "ja": "モデル", "vi": "Model"},
    "co4e.f_permission": {"en": "Permissions", "ja": "権限", "vi": "Quyền"},
    "co4e.f_self_verify": {"en": "Self-verify", "ja": "自己検証", "vi": "Tự kiểm tra"},
    "co4e.f_verify_rounds": {"en": "rounds", "ja": "回数", "vi": "vòng"},
    "co4e.f_skills": {"en": "Skills", "ja": "スキル", "vi": "Skills"},
    "co4e.f_attachments": {"en": "Attachments", "ja": "添付ファイル", "vi": "Tệp đính kèm"},
    "co4e.attach_add": {"en": "Attach files", "ja": "ファイル添付", "vi": "Đính kèm tệp"},
    "co4e.attach_remove": {"en": "Remove", "ja": "削除", "vi": "Bỏ"},
    "co4e.f_subagents": {"en": "Parallel agents", "ja": "並列エージェント", "vi": "Agent song song"},
    "co4e.perm.inherit": {"en": "Inherit", "ja": "継承", "vi": "Kế thừa"},
    "co4e.perm.read-only": {"en": "Read-only", "ja": "読み取り専用", "vi": "Chỉ đọc"},
    "co4e.perm.standard": {"en": "Standard", "ja": "標準", "vi": "Tiêu chuẩn"},
    "co4e.perm.full": {"en": "Full", "ja": "フル", "vi": "Toàn quyền"},
    "co4e.add_subagent": {"en": "Add", "ja": "追加", "vi": "Thêm"},
    "co4e.del_subagent": {"en": "Remove", "ja": "削除", "vi": "Bỏ"},
    "co4e.run_this_step": {"en": "Run this step", "ja": "このステップを実行", "vi": "Chạy bước này"},
    "co4e.run_from_here": {"en": "Run from here", "ja": "ここから実行", "vi": "Chạy từ đây"},
    "co4e.delete_step": {"en": "Delete step", "ja": "ステップ削除", "vi": "Xóa bước"},
    "co4e.load_models_tooltip": {
        "en": "Load available models", "ja": "利用可能なモデルを取得", "vi": "Tải danh sách model"},
    "co4e.agent_edit_title": {"en": "Edit agent", "ja": "エージェント編集", "vi": "Sửa agent"},
    "co4e.agent_new_title": {"en": "New agent", "ja": "新規エージェント", "vi": "Agent mới"},
    "co4e.saved_msg": {"en": "Saved flow: {name}", "ja": "フローを保存: {name}", "vi": "Đã lưu flow: {name}"},
    "co4e.select_custom_agent": {
        "en": "Select a custom agent first.", "ja": "先にカスタムエージェントを選択してください。",
        "vi": "Hãy chọn một agent tùy chỉnh trước."},
    "co4e.no_steps": {"en": "Add at least one step first.", "ja": "先にステップを追加してください。",
                      "vi": "Hãy thêm ít nhất một bước."},
    "co4e.run_started": {"en": "▶ Running flow: {name}", "ja": "▶ フロー実行中: {name}",
                         "vi": "▶ Đang chạy flow: {name}"},
    "co4e.run_done": {"en": "✓ Flow finished.", "ja": "✓ フロー完了。", "vi": "✓ Flow xong."},
    "co4e.run_execute_phase": {
        "en": "▶ Plan done — now executing…", "ja": "▶ 計画完了 — 実行中…",
        "vi": "▶ Xong plan — đang thực thi…"},
    "co4e.agent_not_found": {
        "en": "Agent '{name}' not found.", "ja": "エージェント '{name}' が見つかりません。",
        "vi": "Không tìm thấy agent '{name}'."},

    # ---- agents_admin_tab.py — Admin-only agent catalog -------------------
    "agents_admin.page_title": {"en": "Agents Admin", "ja": "Agents Admin", "vi": "Agents Admin"},
    "agents_admin.edit_row_tooltip": {"en": "Edit", "ja": "編集", "vi": "Sửa"},
    "agents_admin.delete_row_tooltip": {"en": "Delete", "ja": "削除", "vi": "Xóa"},
    "agents_admin.hint": {
        "en": "System-management agents shared across every machine (stored in the shared accounts folder): the help agent and Schedule Task executors. These are NOT the agents you pick in Cowork or Co4E.",
        "ja": "全マシンで共有されるシステム管理用エージェント（共有フォルダーに保存）：ヘルプエージェントやスケジュールタスクの実行エージェントなど。CoworkやCo4Eで選択するエージェントではありません。",
        "vi": "Agent quản lý hệ thống, dùng chung mọi máy (lưu trong thư mục dùng chung): agent trợ giúp và agent chạy Schedule Task. Đây KHÔNG phải agent để chọn trong Cowork hay Co4E."},
    "agents_admin.add_title": {"en": "Add agent", "ja": "エージェント追加", "vi": "Thêm agent"},
    "agents_admin.edit_title": {"en": "Edit agent", "ja": "エージェント編集", "vi": "Sửa agent"},
    "agents_admin.delete_title": {"en": "Delete agent", "ja": "エージェント削除", "vi": "Xóa agent"},
    "agents_admin.delete_confirm": {
        "en": "Delete agent \"{name}\"?", "ja": "エージェント「{name}」を削除しますか？",
        "vi": "Xóa agent \"{name}\"?"},
    "agents_admin.add_btn": {"en": "Add", "ja": "追加", "vi": "Thêm"},
    "agents_admin.f_name": {"en": "Name", "ja": "名前", "vi": "Tên"},
    "agents_admin.f_kind": {"en": "App function", "ja": "アプリ機能", "vi": "Chức năng App"},
    "agents_admin.f_prompt": {"en": "Instructions", "ja": "指示", "vi": "Chỉ dẫn"},
    "agents_admin.f_prompt_placeholder": {
        "en": "Extra instructions this agent always follows (optional)…",
        "ja": "このエージェントが常に従う追加指示（任意）…",
        "vi": "Chỉ dẫn bổ sung agent này luôn tuân theo (tùy chọn)…"},
    "agents_admin.f_provider": {"en": "Provider", "ja": "プロバイダー", "vi": "Provider"},
    "agents_admin.provider_default": {
        "en": "(machine's active provider)", "ja": "（各マシンの現在のプロバイダー）",
        "vi": "(provider hiện tại của máy)"},
    "agents_admin.f_model": {"en": "Model", "ja": "モデル", "vi": "Model"},
    "agents_admin.f_model_placeholder": {
        "en": "empty = each machine's Settings model (currently: {model})",
        "ja": "空欄 = 各マシンの設定モデル（現在: {model}）",
        "vi": "để trống = model trong Settings của từng máy (hiện tại: {model})"},
    "agents_admin.load_models_tooltip": {
        "en": "Fetch this provider's real model list so you can pick a specific one from the dropdown.",
        "ja": "このプロバイダーの実際のモデル一覧を取得し、ドロップダウンから選択できるようにします。",
        "vi": "Lấy danh sách model thực tế của provider này để chọn từ dropdown."},
    "agents_admin.load_models_empty": {
        "en": "No models were returned — check the provider's settings/connection.",
        "ja": "モデルが取得できませんでした。プロバイダーの設定/接続を確認してください。",
        "vi": "Không lấy được model nào — kiểm tra lại cấu hình/kết nối provider."},
    "agents_admin.f_enabled": {"en": "Enabled", "ja": "有効", "vi": "Kích hoạt"},
    "agents_admin.col_name": {"en": "Name", "ja": "名前", "vi": "Tên"},
    "agents_admin.col_kind": {"en": "Function", "ja": "機能", "vi": "Chức năng"},
    "agents_admin.col_model": {"en": "Model", "ja": "モデル", "vi": "Model"},
    "agents_admin.col_enabled": {"en": "Enabled", "ja": "有効", "vi": "Kích hoạt"},
    "agents_admin.col_status": {"en": "Status", "ja": "状態", "vi": "Trạng thái"},
    "agents_admin.col_updated": {"en": "Updated", "ja": "更新", "vi": "Cập nhật"},
    "agents_admin.check_btn": {"en": "Check all", "ja": "すべてチェック", "vi": "Kiểm tra tất cả"},
    "agents_admin.check_tooltip": {
        "en": "Check each agent's effective provider/model connectivity",
        "ja": "各エージェントの実効プロバイダ/モデルの接続性を確認",
        "vi": "Kiểm tra kết nối provider/model hiệu lực của từng agent"},
    "agents_admin.status_unchecked": {"en": "— (not checked)", "ja": "— (未チェック)", "vi": "— (chưa kiểm tra)"},
    "agents_admin.status_unchecked_tip": {
        "en": "Press Check to test whether this agent's provider/model is reachable",
        "ja": "「チェック」でこのエージェントのプロバイダ/モデルへの到達性をテスト",
        "vi": "Nhấn Kiểm tra để test agent này có kết nối được provider/model không"},
    "agents_admin.status_checking": {"en": "checking…", "ja": "確認中…", "vi": "đang kiểm tra…"},
    "agents_admin.status_ok": {"en": "Active", "ja": "稼働中", "vi": "Hoạt động"},
    "agents_admin.status_bad": {"en": "Error", "ja": "エラー", "vi": "Lỗi"},
    "agents_admin.default_model": {
        "en": "(Settings default: {model})", "ja": "（設定既定: {model}）",
        "vi": "(mặc định Settings: {model})"},
    "agents_admin.kind.search": {"en": "Search", "ja": "検索", "vi": "Tìm kiếm"},
    "agents_admin.kind.monitor": {"en": "Monitoring", "ja": "監視", "vi": "Giám sát"},
    "agents_admin.kind.cowork": {"en": "Cowork chat", "ja": "Cowork チャット", "vi": "Cowork chat"},
    "agents_admin.kind.graphrag": {"en": "GraphRAG / Knowledge", "ja": "GraphRAG / ナレッジ", "vi": "GraphRAG / Tri thức"},
    "agents_admin.kind.schedule": {"en": "Schedule Task", "ja": "スケジュールタスク", "vi": "Schedule Task"},
    "agents_admin.kind.security": {"en": "Security", "ja": "セキュリティ", "vi": "Bảo mật"},
    "agents_admin.kind.help": {"en": "App Help", "ja": "アプリヘルプ", "vi": "Trợ giúp App"},

    "monitoring.filter_placeholder": {
        "en": "Filter rows (or type a question and press )…",
        "ja": "行をフィルター（質問を入力しても可）…",
        "vi": "Lọc dòng (hoặc gõ câu hỏi rồi bấm )…"},
    "monitoring.ai_filter_btn": {"en": "AI", "ja": "AI", "vi": "AI"},
    "monitoring.page_size_label": {
        "en": "Rows/page:", "ja": "1ページの行数:", "vi": "Số dòng/trang:"},
    "monitoring.pricing_title": {
        "en": "Model pricing (USD / 1M tokens)", "ja": "モデル価格表 (USD / 100万トークン)",
        "vi": "Bảng giá model (USD / 1 triệu token)"},
    "monitoring.pricing_col_model": {"en": "Model", "ja": "モデル", "vi": "Model"},
    "monitoring.pricing_col_in": {"en": "In", "ja": "入力", "vi": "In"},
    "monitoring.pricing_col_out": {"en": "Out", "ja": "出力", "vi": "Out"},
    "monitoring.pricing_col_cache": {"en": "Cache", "ja": "キャッシュ", "vi": "Cache"},
    "monitoring.pricing_add_btn": {"en": "Add model", "ja": "モデル追加", "vi": "Thêm model"},
    "monitoring.pricing_del_btn": {"en": "Remove", "ja": "削除", "vi": "Xóa"},
    "monitoring.pricing_link_label": {
        "en": "Reference:", "ja": "参考リンク:", "vi": "Link tham khảo:"},
    "monitoring.pricing_no_link": {
        "en": "No reference link set (Settings → Parameter → Pricing reference link).",
        "ja": "参考リンク未設定（設定 → Parameter）。",
        "vi": "Chưa đặt link tham khảo (Settings → Parameter → Link bảng giá)."},
    "monitoring.ai_filter_tooltip": {
        "en": "AI turns your question into a filter keyword (e.g. \"which commands failed today?\").",
        "ja": "質問をAIがフィルターキーワードに変換します。",
        "vi": "AI chuyển câu hỏi thành từ khóa lọc (vd: \"hôm nay lệnh nào bị lỗi?\")."},
    "monitoring.security_detail_title": {
        "en": "Event details", "ja": "イベント詳細", "vi": "Chi tiết sự kiện"},
    "monitoring.security_detail_close": {
        "en": "Close", "ja": "閉じる", "vi": "Đóng"},
    "monitoring.security_events_title": {
        "en": "Security Events", "ja": "セキュリティイベント", "vi": "Sự kiện bảo mật"},
    "monitoring.mcp_history_title": {
        "en": "MCP Call History", "ja": "MCP 呼び出し履歴", "vi": "Lịch sử gọi MCP"},
    "monitoring.action_logs_title": {
        "en": "Action Logs", "ja": "アクションログ", "vi": "Nhật ký hành động"},
    "monitoring.col_detail_block": {
        "en": "Block detail", "ja": "ブロック詳細", "vi": "Chi tiết chặn"},

    # ---- event-detail panel (ui-audit_v2.html openDetail()) --------------
    "monitoring.detail_section_general": {
        "en": "General info", "ja": "基本情報", "vi": "Thông tin chung"},
    "monitoring.detail_section_action": {
        "en": "Action", "ja": "アクション", "vi": "Hành động"},
    "monitoring.detail_section_metadata": {
        "en": "Metadata", "ja": "メタデータ", "vi": "Metadata"},
    "monitoring.detail_type": {"en": "Type", "ja": "種類", "vi": "Loại"},
    "monitoring.detail_status": {"en": "Status", "ja": "ステータス", "vi": "Trạng thái"},
    "monitoring.detail_event_id": {"en": "Event ID", "ja": "イベントID", "vi": "Event ID"},
    "monitoring.detail_policy": {"en": "Policy", "ja": "ポリシー", "vi": "Policy"},
    "monitoring.detail_severity": {"en": "Severity", "ja": "重大度", "vi": "Severity"},
    "monitoring.detail_copy": {"en": "Copy", "ja": "コピー", "vi": "Copy"},
    "monitoring.detail_copied": {"en": "Copied", "ja": "コピー済み", "vi": "Đã copy"},

    # Trạng thái pill — which rule fired, phrased as the enforcement outcome
    # (distinct wording from the Loại/action_* labels below, matching
    # ui-audit_v2.html's statusInfo() vs actionLabel).
    "monitoring.status_blocked": {"en": "Blocked", "ja": "ブロック済み", "vi": "Đã chặn"},
    "monitoring.status_path": {"en": "Path blocked", "ja": "パスをブロック", "vi": "Path chặn"},
    "monitoring.status_network": {"en": "Network blocked", "ja": "ネットワークをブロック", "vi": "Mạng chặn"},
    "monitoring.status_secret": {"en": "Secret leaked", "ja": "シークレット漏洩", "vi": "Bí mật lộ"},
    "monitoring.status_ok": {"en": "Succeeded", "ja": "成功", "vi": "Thành công"},
    "monitoring.status_failed": {"en": "Failed", "ja": "失敗", "vi": "Thất bại"},

    "monitoring.severity_critical": {"en": "CRITICAL", "ja": "CRITICAL", "vi": "CRITICAL"},
    "monitoring.severity_medium": {"en": "MEDIUM", "ja": "MEDIUM", "vi": "MEDIUM"},
    "monitoring.severity_info": {"en": "INFO", "ja": "INFO", "vi": "INFO"},

    # Loại field — a human label for the raw event name (audit_log ``name``).
    "monitoring.action_prompt": {"en": "Risky prompt", "ja": "危険なプロンプト", "vi": "Prompt rủi ro"},
    "monitoring.action_dangerous_command": {
        "en": "Dangerous command", "ja": "危険なコマンド", "vi": "Lệnh nguy hiểm"},
    "monitoring.action_install_package": {
        "en": "Package install", "ja": "パッケージインストール", "vi": "Cài đặt gói"},
    "monitoring.action_path_outside_sandbox": {
        "en": "Path outside sandbox", "ja": "サンドボックス外のパス", "vi": "Path ngoài sandbox"},
    "monitoring.action_network_blocked": {
        "en": "Network blocked", "ja": "ネットワークブロック", "vi": "Mạng bị chặn"},
    "monitoring.action_secret_in_output": {
        "en": "Secret disclosed", "ja": "シークレット漏洩", "vi": "Tiết lộ bí mật"},

    "monitoring.overview_activity_title": {
        "en": "Recent log", "ja": "最近のログ", "vi": "Nhật ký gần đây"},
    "monitoring.overview_no_activity": {
        "en": "No activity yet.", "ja": "まだアクティビティはありません。", "vi": "Chưa có hoạt động nào."},
    "monitoring.overview_resource_title": {
        "en": "Resources", "ja": "リソース", "vi": "Tài nguyên"},
    "monitoring.overview_res_cpu": {"en": "CPU", "ja": "CPU", "vi": "CPU"},
    "monitoring.overview_res_mem": {"en": "Memory", "ja": "メモリ", "vi": "Bộ nhớ"},
    "monitoring.overview_res_disk": {"en": "Disk I/O", "ja": "ディスク I/O", "vi": "Disk I/O"},
    "monitoring.overview_res_network": {"en": "Network", "ja": "ネットワーク", "vi": "Mạng"},
    # ---- model pricing list (Overview, beside the resource group) ----
    "monitoring.pricing_title": {"en": "Model pricing", "ja": "モデル料金", "vi": "Bảng giá model"},
    "monitoring.pricing_currency": {"en": "Currency", "ja": "通貨", "vi": "Tiền tệ"},
    "monitoring.pricing_import": {"en": "Import", "ja": "取込", "vi": "Nhập"},
    "monitoring.pricing_export": {"en": "Template", "ja": "テンプレート", "vi": "Mẫu"},
    "monitoring.pricing_add": {"en": "Add", "ja": "追加", "vi": "Thêm"},
    "monitoring.pricing_autolink": {"en": "Auto-link", "ja": "自動取得", "vi": "Tự lấy"},
    "monitoring.pricing_delete": {"en": "Delete", "ja": "削除", "vi": "Xóa"},
    "monitoring.pricing_add_prompt": {"en": "Model name:", "ja": "モデル名:", "vi": "Tên model:"},
    "monitoring.pricing_imported": {"en": "Imported {n} model prices.", "ja": "{n} 件の料金を取込。",
                                    "vi": "Đã nhập {n} dòng giá."},
    "monitoring.pricing_exported": {"en": "Price template exported.", "ja": "料金テンプレートを出力。",
                                    "vi": "Đã xuất mẫu bảng giá."},
    "monitoring.pricing_linked": {"en": "Linked {n} models from providers.",
                                  "ja": "プロバイダから {n} モデルを取得。",
                                  "vi": "Đã lấy {n} model từ provider."},
    "monitoring.pricing_col_model": {"en": "Model", "ja": "モデル", "vi": "Model"},
    "monitoring.pricing_col_context": {"en": "Context", "ja": "コンテキスト", "vi": "Context"},
    "monitoring.pricing_col_maxout": {"en": "Max output", "ja": "最大出力", "vi": "Max output"},
    "monitoring.pricing_col_input": {"en": "Input price", "ja": "入力単価", "vi": "Giá input"},
    "monitoring.pricing_col_output": {"en": "Output price", "ja": "出力単価", "vi": "Giá output"},
    "monitoring.overview_sandbox_details_title": {
        # One section now, holding both the sandbox facts and the permissions.
        "en": "Sandbox & Permissions", "ja": "サンドボックスと権限",
        "vi": "Sandbox & Quyền"},
}
