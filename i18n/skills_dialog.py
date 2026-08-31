"""Chuỗi hiển thị — phần skills_dialog.

Cắt ra từ ``i18n.py``: một dict 3.000 dòng không mở nổi để sửa một chữ.
Cắt theo mốc phân đoạn có sẵn, nên mỗi cụm vẫn là các màn đi liền nhau.
``i18n.py`` gộp tất cả lại thành ``STRINGS``.
"""
from __future__ import annotations

from typing import Dict

STRINGS: Dict[str, Dict[str, str]] = {
    "settings.testing_connection": {"en": "Testing connection…", "ja": "接続を確認中…", "vi": "Đang kiểm tra kết nối…"},
    "settings.sending_test": {"en": "Sending test…", "ja": "テスト送信中…", "vi": "Đang gửi thử…"},
    "settings.test_failed": {"en": "Test failed: {err}", "ja": "テスト失敗: {err}", "vi": "Kiểm tra thất bại: {err}"},
    "settings.pick_hist_dir": {"en": "Choose history folder", "ja": "履歴フォルダを選択", "vi": "Chọn thư mục lưu lịch sử"},

    # ---- skills_dialog.py -----------------------------------------------
    "skills.edit_title": {"en": "Edit skill", "ja": "スキルを編集", "vi": "Sửa skill"},
    "skills.add_title": {"en": "Add skill", "ja": "スキルを追加", "vi": "Thêm skill"},
    "skills.name_label": {"en": "Skill name", "ja": "スキル名", "vi": "Tên skill"},
    "skills.name_placeholder": {
        "en": "e.g. Always write unit tests", "ja": "例：常に単体テストを書く", "vi": "vd. Luôn viết unit test"},
    "skills.desc_label": {"en": "Short description (optional)", "ja": "簡単な説明（任意）", "vi": "Mô tả ngắn (tuỳ chọn)"},
    "skills.instructions_label": {"en": "Instructions for the agent", "ja": "エージェントへの指示", "vi": "Hướng dẫn cho agent"},
    "skills.gen_from_desc": {"en": "Generate from description", "ja": "説明文から生成", "vi": "Tạo từ mô tả"},
    "skills.gen_from_desc_tooltip": {
        "en": "Use the AI agent to draft the instructions from the short description",
        "ja": "AI エージェントで短い説明から指示文の下書きを生成します",
        "vi": "Dùng AI để soạn hướng dẫn từ mô tả ngắn"},
    "skills.instructions_placeholder": {
        "en": "Describe the rules / guidance the agent must follow…",
        "ja": "エージェントが従うべきルール/ガイドラインを記述…",
        "vi": "Mô tả các quy tắc/hướng dẫn mà agent phải tuân theo…"},
    "skills.generating": {"en": "Generating…", "ja": "生成中…", "vi": "Đang tạo…"},
    "skills.title": {"en": "Skills", "ja": "スキル", "vi": "Skills"},
    "skills.hint": {
        "en": "Tick to enable a skill. Enabled skills are followed by the agent.",
        "ja": "チェックでスキルを有効化。有効なスキルはエージェントが従います。",
        "vi": "Tick để bật skill. Skill đang bật sẽ được agent tuân theo."},
    "skills.auto_generate": {"en": "Auto-generate", "ja": "自動生成", "vi": "Tự động tạo"},
    "skills.auto_generate_tooltip": {
        "en": ("Describe a skill in one line and let the AI draft the whole skill "
               "(name, description and instructions) for you to review."),
        "ja": "1行でスキルを説明すると、AI が名前・説明・指示文をまとめて下書きします。",
        "vi": "Mô tả skill trong 1 dòng, AI sẽ tự soạn cả skill (tên, mô tả, hướng dẫn) để bạn xem lại."},
    "skills.import_btn": {"en": "Import…", "ja": "インポート…", "vi": "Nhập…"},
    "skills.import_tooltip": {
        "en": "Import an external skill from a .skill, .json, .md or .txt file",
        "ja": ".skill / .json / .md / .txt ファイルから外部スキルをインポート",
        "vi": "Nhập skill từ file .skill, .json, .md hoặc .txt"},
    "skills.edit_btn": {"en": "Edit", "ja": "編集", "vi": "Sửa"},
    "skills.delete_btn": {"en": "Delete", "ja": "削除", "vi": "Xóa"},
    "skills.close_btn": {"en": "Close", "ja": "閉じる", "vi": "Đóng"},
    "skills.no_skills": {
        "en": "(No skills yet — click ' Auto-generate' or 'Import…')",
        "ja": "（スキルはまだありません。「 自動生成」または「インポート…」をクリック）",
        "vi": "(Chưa có skill nào — bấm ' Tự động tạo' hoặc 'Nhập…')"},
    "skills.auto_generate_title": {"en": "Auto-generate skill", "ja": "スキルを自動生成", "vi": "Tự động tạo skill"},
    "skills.auto_generate_unavailable": {
        "en": "AI generation isn't available right now.", "ja": "現在 AI 生成は利用できません。",
        "vi": "Tính năng tạo bằng AI hiện chưa dùng được."},
    "skills.auto_generate_prompt": {
        "en": "Describe the skill you want (what should the agent do?):",
        "ja": "欲しいスキルを説明してください（エージェントに何をさせたいか）:",
        "vi": "Mô tả skill bạn muốn (agent nên làm gì?):"},
    "skills.auto_generate_failed": {
        "en": "Couldn't generate a skill. Check the AI provider in Settings, or add one manually.",
        "ja": "スキルを生成できませんでした。設定の AI プロバイダーを確認するか、手動で追加してください。",
        "vi": "Không tạo được skill. Kiểm tra lại provider AI trong Settings, hoặc tự thêm thủ công."},
    "skills.import_dialog_title": {"en": "Import skill", "ja": "スキルをインポート", "vi": "Nhập skill"},
    "skills.import_dialog_filter": {
        "en": "Skills (*.skill *.json *.md *.txt *.yaml *.yml *.zip);;All files (*.*)",
        "ja": "スキル (*.skill *.json *.md *.txt *.yaml *.yml *.zip);;すべてのファイル (*.*)",
        "vi": "Skill (*.skill *.json *.md *.txt *.yaml *.yml *.zip);;Tất cả file (*.*)"},
    "skills.import_failed": {"en": "Could not import: {err}", "ja": "インポートできませんでした: {err}", "vi": "Không nhập được: {err}"},
    "skills.export_btn": {"en": "Export .md", "ja": ".md エクスポート", "vi": "Xuất .md"},
    "skills.export_tooltip": {
        "en": "Export the selected skill to a Markdown (.md) file",
        "ja": "選択したスキルを Markdown (.md) ファイルに書き出します",
        "vi": "Xuất skill đang chọn ra file Markdown (.md)"},
    "skills.export_pick": {
        "en": "Select a skill in the list first, then click Export .md.",
        "ja": "先にリストでスキルを選択してから「.md エクスポート」を押してください。",
        "vi": "Hãy chọn một skill trong danh sách trước, rồi bấm Xuất .md."},
    "skills.export_dialog_title": {
        "en": "Export skill to Markdown", "ja": "スキルを Markdown に書き出す",
        "vi": "Xuất skill ra Markdown"},
    "skills.export_dialog_filter": {
        "en": "Markdown (*.md);;All files (*.*)", "ja": "Markdown (*.md);;すべてのファイル (*.*)",
        "vi": "Markdown (*.md);;Tất cả file (*.*)"},
    "skills.export_done": {
        "en": "Exported to {path}", "ja": "{path} に書き出しました", "vi": "Đã xuất ra {path}"},
    "skills.export_failed": {
        "en": "Could not export: {err}", "ja": "書き出せませんでした: {err}", "vi": "Không xuất được: {err}"},
    "skills.duplicate_btn": {"en": "Duplicate", "ja": "複製", "vi": "Nhân bản"},
    "skills.duplicate_tooltip": {
        "en": "Duplicate the selected skill (a copy you can rename and edit)",
        "ja": "選択したスキルを複製します（名前を変更・編集できるコピー）",
        "vi": "Nhân bản skill đang chọn (bản sao có thể đổi tên và chỉnh sửa)"},
    "skills.copy_name": {"en": "{name} (copy)", "ja": "{name}（コピー）", "vi": "{name} (bản sao)"},
    "skills.from_template": {"en": "From template file…", "ja": "テンプレートファイルから…", "vi": "Từ file template…"},
    "skills.from_template_tooltip": {
        "en": ("Analyze a .pptx/.xlsx template's layout, fonts, colors and formatting "
               "and draft a skill so future generated files match it."),
        "ja": ".pptx/.xlsx テンプレートのレイアウト・フォント・色・書式を解析し、"
              "今後生成するファイルがそれに合うようスキルを下書きします。",
        "vi": "Phân tích layout/font/màu/định dạng của file template .pptx/.xlsx, soạn skill để các file tạo sau khớp với nó."},
    "skills.from_template_title": {
        "en": "Generate skill from template", "ja": "テンプレートからスキルを生成",
        "vi": "Tạo skill từ template"},
    "skills.from_template_dialog_title": {
        "en": "Select a template file", "ja": "テンプレートファイルを選択",
        "vi": "Chọn file template"},
    "skills.from_template_dialog_filter": {
        "en": "PowerPoint/Excel (*.pptx *.xlsx *.xlsm);;All files (*.*)",
        "ja": "PowerPoint/Excel (*.pptx *.xlsx *.xlsm);;すべてのファイル (*.*)",
        "vi": "PowerPoint/Excel (*.pptx *.xlsx *.xlsm);;Tất cả file (*.*)"},
    "skills.from_template_failed": {
        "en": ("Couldn't analyze this template. Make sure it's a valid .pptx/.xlsx file "
               "and the AI provider in Settings works, or add the skill manually."),
        "ja": "このテンプレートを解析できませんでした。有効な .pptx/.xlsx ファイルか、"
              "設定の AI プロバイダーが動作しているか確認するか、手動でスキルを追加してください。",
        "vi": "Không phân tích được template này. Kiểm tra file .pptx/.xlsx hợp lệ và provider AI trong Settings hoạt động tốt, hoặc tự thêm skill thủ công."},

    # ---- flow_dialog.py -----------------------------------------------
    "flow.title": {"en": "Flow Management", "ja": "Flow Management", "vi": "Flow Management"},
    "flow.tab_flow": {"en": "Flow", "ja": "フロー", "vi": "Flow"},
    "flow.tab_agents": {"en": "Agents", "ja": "エージェント", "vi": "Agents"},
    "flow.tab_skills": {"en": "Skills", "ja": "スキル", "vi": "Skills"},
    "flow.template": {"en": "Template:", "ja": "テンプレート:", "vi": "Template:"},
    "flow.load_builtin": {"en": "Load Req→Demo template", "ja": "Req→Demo テンプレートを読込", "vi": "Tải template Req→Demo"},
    "flow.new": {"en": "New", "ja": "新規", "vi": "Mới"},
    "flow.delete_template": {"en": "Delete template", "ja": "テンプレートを削除", "vi": "Xóa template"},
    "flow.name_label": {"en": "Flow name", "ja": "フロー名", "vi": "Tên flow"},
    "flow.description_label": {"en": "Description", "ja": "説明", "vi": "Mô tả"},
    "flow.stages": {"en": "Stages", "ja": "ステージ", "vi": "Các bước"},
    "flow.remove_stage": {"en": "Remove stage", "ja": "ステージを削除", "vi": "Xóa bước"},
    "flow.stage_name": {"en": "Stage name", "ja": "ステージ名", "vi": "Tên bước"},
    "flow.hint": {"en": "Hint", "ja": "ヒント", "vi": "Gợi ý"},
    "flow.task_prompt": {"en": "Task (prompt)", "ja": "タスク（プロンプト）", "vi": "Nhiệm vụ (prompt)"},
    "flow.skill": {"en": "Skill", "ja": "スキル", "vi": "Skill"},
    "flow.agent": {"en": "AI provider", "ja": "AI プロバイダー", "vi": "AI provider"},
    "flow.model_label": {"en": "Agent:", "ja": "Agent:", "vi": "Agent:"},
    "flow.default_model": {"en": "(provider default)", "ja": "（プロバイダー既定）", "vi": "(mặc định của provider)"},
    "flow.gen_task_from_hint": {"en": "Generate task from hint", "ja": "ヒントからタスクを生成", "vi": "Tạo task từ gợi ý"},
    "flow.gen_task_tooltip": {
        "en": "Use the AI agent to expand the hint into a task prompt",
        "ja": "AI エージェントでヒントをタスクプロンプトに展開します",
        "vi": "Dùng AI để mở rộng gợi ý thành task prompt"},
    "flow.attachments": {"en": "Attachments", "ja": "添付ファイル", "vi": "Đính kèm"},
    "flow.attach_files": {"en": "Attach files…", "ja": "ファイルを添付…", "vi": "Đính kèm file…"},
    "flow.attach_files_count": {
        "en": "{n} file(s) attached", "ja": "{n} 件添付済み", "vi": "Đã đính kèm {n} file"},
    "flow.compact_after_run": {
        "en": "Compact after run", "ja": "実行後に圧縮", "vi": "Compact after run (nén sau khi chạy)"},
    "flow.compact_after_run_tooltip": {
        "en": "Trim older history right after this stage, freeing up token space for the next one",
        "ja": "このステージの直後に古い履歴を切り詰め、次のステージ用にトークン余裕を確保します",
        "vi": "Rút gọn lịch sử cũ ngay sau bước này để nhường chỗ token cho bước tiếp theo"},
    "flow.self_verify": {
        "en": "Self-verify before handoff", "ja": "引き渡し前に自己検証", "vi": "Self-verify trước khi bàn giao"},
    "flow.self_verify_tooltip": {
        "en": "Ask the agent to confirm the stage is actually complete before moving on",
        "ja": "次に進む前に、このステージが本当に完了しているかエージェントに確認させます",
        "vi": "Yêu cầu agent tự xác nhận đã hoàn thành đầy đủ trước khi qua bước sau"},
    "flow.review_retries": {
        "en": "Review-completeness retries", "ja": "完全性レビューの再試行回数", "vi": "Số lần review lại nếu chưa xong"},
    "flow.review_retries_tooltip": {
        "en": "If the self-check says the stage is incomplete, re-run it up to this many times (0 = off)",
        "ja": "自己チェックで未完了と判定された場合、この回数まで再実行します（0 = 無効）",
        "vi": "Nếu tự kiểm tra thấy chưa hoàn thành, chạy lại bước này tối đa số lần này (0 = tắt)"},
    "flow.parallel_agents": {
        "en": "Parallel sub-agents", "ja": "並列サブエージェント", "vi": "Sub-agent chạy song song"},
    "flow.subagent_name_placeholder": {"en": "Name (e.g. backend)", "ja": "名前（例: backend）", "vi": "Tên (vd backend)"},
    "flow.subagent_task_placeholder": {
        "en": "Task for this sub-agent (optional — falls back to the stage task)",
        "ja": "このサブエージェントのタスク（任意 — 未入力ならステージのタスクを使用）",
        "vi": "Nhiệm vụ của sub-agent này (tùy chọn — bỏ trống thì dùng task của bước)"},
    "flow.subagent_add": {"en": "Add", "ja": "追加", "vi": "Thêm"},
    "flow.subagent_remove": {"en": "Remove", "ja": "削除", "vi": "Xóa"},
    "flow.subagent_add_from_agent": {
        "en": "Add from Agent", "ja": "エージェントから追加", "vi": "Thêm từ Agent"},
    "flow.subagent_no_agents": {
        "en": "(no saved Agents — create one in the Agents tab)",
        "ja": "（保存済みのエージェントがありません — Agents タブで作成してください）",
        "vi": "(chưa có Agent nào — tạo ở tab Quản lý Agent)"},
    "flow.subagent_hint": {
        "en": ("Add 2+ sub-agents to make this a PARALLEL stage — they run concurrently, then "
               "the stage's own Task field is used to consolidate their results into one."),
        "ja": ("サブエージェントを2つ以上追加すると、このステージは並列ステージになります — "
               "同時に実行され、その後ステージ自体のタスク欄で結果を1つに統合します。"),
        "vi": ("Thêm từ 2 sub-agent trở lên để bước này chạy SONG SONG — chúng chạy đồng thời, "
               "sau đó ô Task của chính bước này dùng để gộp kết quả lại thành một.")},
    "flow.add_stage": {"en": "Add stage", "ja": "ステージを追加", "vi": "Thêm bước"},
    "flow.update_stage": {"en": "Update stage", "ja": "ステージを更新", "vi": "Cập nhật bước"},
    "flow.save_template": {"en": "Save as template", "ja": "テンプレートとして保存", "vi": "Lưu làm template"},
    "flow.run": {"en": "Run flow", "ja": "フローを実行", "vi": "Chạy flow"},
    "flow.close": {"en": "Close", "ja": "閉じる", "vi": "Đóng"},
    "flow.none": {"en": "(none)", "ja": "（なし）", "vi": "(không có)"},
    "flow.default_agent": {"en": "Default", "ja": "デフォルト", "vi": "Mặc định"},
    "flow.select_template": {"en": "— select template —", "ja": "— テンプレートを選択 —", "vi": "— chọn template —"},
    "flow.new_flow_name": {"en": "New flow", "ja": "新しいフロー", "vi": "Flow mới"},
    "flow.default_name": {"en": "Flow", "ja": "フロー", "vi": "Flow"},

    # ---- agent_manager_tab.py -------------------------------------------
    "agentmgr.hint": {
        "en": "Create reusable Agent presets (name + task + provider) — pick them as "
              "parallel sub-agents from any Flow stage in the Code tab.",
        "ja": "再利用できるエージェントのプリセット（名前・タスク・プロバイダー）を作成します — "
              "Code タブの任意のフローステージから並列サブエージェントとして選択できます。",
        "vi": "Tạo sẵn các Agent (tên + nhiệm vụ + provider) để tái sử dụng — chọn làm "
              "sub-agent chạy song song từ bất kỳ bước Flow nào ở tab Code."},
    "agentmgr.list_label": {"en": "Saved agents", "ja": "保存済みエージェント", "vi": "Agent đã lưu"},
    "agentmgr.name_label": {"en": "Agent name", "ja": "エージェント名", "vi": "Tên agent"},
    "agentmgr.desc_label": {"en": "Description", "ja": "説明", "vi": "Mô tả"},
    "agentmgr.prompt_label": {"en": "Task (prompt)", "ja": "タスク（プロンプト）", "vi": "Nhiệm vụ (prompt)"},
    "agentmgr.gen_prompt_btn": {"en": "Generate from description", "ja": "説明から生成",
                                "vi": "Tạo prompt từ mô tả"},
    "agentmgr.gen_prompt_tooltip": {
        "en": "Use the AI agent to expand the name/description into a task prompt",
        "ja": "AI エージェントで名前・説明をタスクプロンプトに展開します",
        "vi": "Dùng AI để mở rộng tên/mô tả thành task prompt"},
    "agentmgr.provider_label": {"en": "AI provider", "ja": "AI プロバイダー", "vi": "Provider AI"},
    "agentmgr.new_btn": {"en": "New agent", "ja": "新規エージェント", "vi": "Agent mới"},
    "agentmgr.save_btn": {"en": "Save agent", "ja": "エージェントを保存", "vi": "Lưu agent"},
    "agentmgr.delete_btn": {"en": "Delete", "ja": "削除", "vi": "Xóa"},
    "agentmgr.delete_confirm": {
        "en": "Delete agent '{name}'?", "ja": "エージェント「{name}」を削除しますか？",
        "vi": "Xóa agent '{name}'?"},

    # ---- permission_dialog.py ------------------------------------------
    "permission.title": {"en": "Confirm action", "ja": "操作を確認", "vi": "Xác nhận thao tác"},
    "permission.default_action": {"en": "Action", "ja": "操作", "vi": "Thao tác"},
    "permission.subtitle_command": {
        "en": "The agent wants to run this command in the working folder:",
        "ja": "エージェントが作業フォルダで次のコマンドを実行しようとしています:",
        "vi": "Agent muốn chạy lệnh này trong thư mục làm việc:"},
    "permission.subtitle_diff": {
        "en": "The agent wants to change a file (diff below):",
        "ja": "エージェントがファイルを変更しようとしています（差分は下記）:",
        "vi": "Agent muốn thay đổi một tệp (xem diff bên dưới):"},
    "permission.subtitle_default": {
        "en": "The agent proposes an action:", "ja": "エージェントが操作を提案しています:",
        "vi": "Agent đề xuất một thao tác:"},
    "permission.approve": {"en": "Approve", "ja": "承認", "vi": "Duyệt"},
    "permission.reject": {"en": "Reject", "ja": "拒否", "vi": "Từ chối"},
    "permission.remember_whitelist": {
        "en": "Remember — add to the command whitelist",
        "ja": "記憶する — コマンドのホワイトリストに追加",
        "vi": "Ghi nhớ — thêm vào whitelist lệnh"},
    "permission.remember_whitelist_tooltip": {
        "en": "Future commands starting the same way will be auto-approved without asking again.",
        "ja": "同じように始まる今後のコマンドは、再確認なしで自動承認されます。",
        "vi": "Các lệnh sau bắt đầu giống vậy sẽ được tự động duyệt, không hỏi lại."},


    # ---- structure_graph_view.py ---------------------------------------
    "structure.path_placeholder": {"en": "Source / document folder", "ja": "ソース/ドキュメントフォルダ", "vi": "Thư mục source/tài liệu"},
    "structure.browse": {"en": "Browse…", "ja": "参照…", "vi": "Browse…"},
    "structure.mode_all": {"en": "All files", "ja": "すべてのファイル", "vi": "All files"},
    "structure.mode_code": {"en": "Code only", "ja": "コードのみ", "vi": "Code only"},
    "structure.mode_doc": {"en": "Docs only", "ja": "ドキュメントのみ", "vi": "Docs only"},
    "structure.project_none": {"en": "(no project — free path)", "ja": "（プロジェクトなし — 自由パス）", "vi": "(không gán project — path tự do)"},
    "structure.project_tooltip": {
        "en": "Lock the scan to a project's sandbox workspace — path becomes read-only and the "
              "Agent Q&A below follows that project's shared Instructions (safer, grounded answers).",
        "ja": "スキャン対象をプロジェクトのサンドボックスワークスペースに固定します — パスは読み取り専用になり、"
              "下のエージェントQ&Aはそのプロジェクトの共有指示に従います（より安全で根拠のある回答）。",
        "vi": "Khóa phạm vi quét vào đúng thư mục sandbox của 1 project — path chuyển sang chỉ đọc và "
              "khung hỏi-đáp Agent bên dưới sẽ theo Instructions chung của project đó (an toàn hơn, "
              "câu trả lời bám sát ngữ cảnh, giảm bịa đặt).",
    },
    "structure.scan": {"en": "Scan", "ja": "スキャン", "vi": "Scan"},
    "structure.export_png": {"en": "Export PNG", "ja": "PNG エクスポート", "vi": "Xuất PNG"},
    "structure.msgs_btn": {"en": "Messages", "ja": "メッセージ", "vi": "Tin nhắn"},
    "structure.graph_btn": {"en": "Graph", "ja": "グラフ", "vi": "Đồ thị"},
    "structure.msgs_tooltip": {
        "en": "Show all conversation messages grouped by day (as JSON).",
        "ja": "会話メッセージを日別にJSONで表示。",
        "vi": "Xem mọi message hội thoại nhóm theo ngày (dạng JSON)."},
    "structure.msgs_none": {"en": "No messages yet.", "ja": "メッセージがありません。",
                            "vi": "Chưa có message nào."},
    "structure.open_browser": {"en": "Open in browser", "ja": "ブラウザで開く", "vi": "Mở trong trình duyệt"},
    "structure.open_browser_tooltip": {
        "en": "Open the full interactive D3 graph in your default browser (works in every build, including the standalone .exe)",
        "ja": "既定のブラウザでフル機能の D3 グラフを開きます（スタンドアロン .exe を含むすべてのビルドで利用可能）",
        "vi": "Mở đồ thị D3 đầy đủ tính năng trong trình duyệt mặc định (dùng được ở mọi bản build, kể cả file .exe độc lập)",
    },
    "structure.opened_browser": {
        "en": "D3 graph opened in your browser at {url}",
        "ja": "ブラウザで D3 グラフを開きました: {url}",
        "vi": "Đã mở đồ thị D3 trong trình duyệt tại {url}",
    },
    "structure.cmem_ui_open": {"en": "Codebase Memory UI", "ja": "Codebase Memory UI", "vi": "Codebase Memory UI"},
    "structure.cmem_ui_back": {"en": "Back to D3 view", "ja": "D3 表示に戻る", "vi": "Về đồ thị D3"},
    "structure.cmem_ui_tooltip": {
        "en": "Open codebase-memory-mcp's own graph UI (Graph/Projects/Control) for the current scan path.",
        "ja": "現在のスキャンパスに対して codebase-memory-mcp 独自のグラフ UI（Graph/Projects/Control）を開きます。",
        "vi": "Mở UI đồ thị riêng của codebase-memory-mcp (Graph/Projects/Control) cho đường dẫn đang quét."},
    "structure.cmem_ui_starting": {
        "en": "Starting codebase-memory-mcp UI…", "ja": "codebase-memory-mcp の UI を起動中…",
        "vi": "Đang khởi động UI của codebase-memory-mcp…"},
    "structure.cmem_ui_opened_embedded": {
        "en": "codebase-memory-mcp UI loaded.", "ja": "codebase-memory-mcp の UI を読み込みました。",
        "vi": "Đã tải UI của codebase-memory-mcp."},
    "structure.cmem_ui_opened_browser": {
        "en": "codebase-memory-mcp UI opened in your browser at {url}",
        "ja": "ブラウザで codebase-memory-mcp の UI を開きました: {url}",
        "vi": "Đã mở UI của codebase-memory-mcp trong trình duyệt tại {url}"},
    "structure.cmem_ui_not_built": {
        "en": "This codebase-memory-mcp build has no embedded UI. Install the "
              "'codebase-memory-mcp-ui' release asset from the project's GitHub "
              "releases to use this view. ({err})",
        "ja": "この codebase-memory-mcp ビルドには UI が組み込まれていません。このビューを使うには "
              "GitHub リリースから 'codebase-memory-mcp-ui' をインストールしてください。({err})",
        "vi": "Bản build codebase-memory-mcp này không có UI nhúng. Cần cài "
              "release asset 'codebase-memory-mcp-ui' từ trang GitHub Releases của "
              "dự án để dùng chức năng này. ({err})"},
    "structure.cmem_ui_failed": {
        "en": "Could not open codebase-memory-mcp UI: {err}",
        "ja": "codebase-memory-mcp の UI を開けませんでした: {err}",
        "vi": "Không mở được UI của codebase-memory-mcp: {err}"},
    "structure.collapse_agent_tooltip": {"en": "Collapse the Agent panel", "ja": "エージェントパネルを折りたたむ", "vi": "Thu gọn bảng Agent"},
    "structure.expand_agent_tooltip": {
        "en": "Click to expand the Agent panel", "ja": "クリックしてエージェントパネルを展開",
        "vi": "Bấm để mở lại bảng Agent"},
    "structure.agent_header": {"en": "Agent — ask about the graph", "ja": "エージェント ― グラフについて質問", "vi": "Agent — hỏi về đồ thị"},
    "structure.ask_placeholder": {
        "en": "e.g. what calls main? which files define classes?",
        "ja": "例: main を呼んでいるのは？クラスを定義しているファイルは？",
        "vi": "vd. cái gì gọi hàm main? file nào định nghĩa class?"},
    "structure.ask": {"en": "Ask", "ja": "質問", "vi": "Hỏi"},
    "structure.detail_placeholder": {
        "en": "Click a node to open its folder, or ask the agent about the graph.",
        "ja": "ノードをクリックするとフォルダを開きます。またはエージェントにグラフについて質問できます。",
        "vi": "Nhấp node để mở thư mục, hoặc hỏi agent về đồ thị."},
    "structure.pick_folder_title": {"en": "Choose folder", "ja": "フォルダを選択", "vi": "Chọn thư mục"},
    "structure.scanning": {"en": "Scanning structure…", "ja": "構造をスキャン中…", "vi": "Đang quét cấu trúc…"},
    "structure.scan_error": {"en": "Scan error: {err}", "ja": "スキャンエラー: {err}", "vi": "Lỗi khi quét: {err}"},
    "structure.graph_summary": {"en": "Graph: {nodes} nodes, {edges} edges.{note}", "ja": "グラフ: ノード {nodes} 個、エッジ {edges} 個。{note}", "vi": "Đồ thị: {nodes} node, {edges} cạnh.{note}"},
    "structure.truncated_note": {"en": "  (truncated — too many nodes)", "ja": "  （切り捨て：ノードが多すぎます）", "vi": "  (đã cắt bớt — quá nhiều node)"},
}
