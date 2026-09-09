"""Chuỗi hiển thị — phần login_dialog.

Cắt ra từ ``i18n.py``: một dict 3.000 dòng không mở nổi để sửa một chữ.
Cắt theo mốc phân đoạn có sẵn, nên mỗi cụm vẫn là các màn đi liền nhau.
``i18n.py`` gộp tất cả lại thành ``STRINGS``.
"""
from __future__ import annotations

from typing import Dict

STRINGS: Dict[str, Dict[str, str]] = {
    # ---- login_dialog.py: startup login / bootstrap / offline ----
    "login.title": {"en": "Sign in", "ja": "サインイン", "vi": "Đăng nhập"},
    "login.header": {"en": "Cowork-Local BamBOO", "ja": "Cowork-Local BamBOO", "vi": "Cowork-Local BamBOO"},
    "login.account": {"en": "Account", "ja": "アカウント", "vi": "Tài khoản"},
    "login.code": {"en": "Access code", "ja": "アクセスコード", "vi": "Mã truy cập"},
    "login.department": {"en": "Department (optional)", "ja": "部署（任意）", "vi": "Phòng ban (không bắt buộc)"},
    "login.department_placeholder": {
        "en": "e.g. FA.PDS — groups you automatically", "ja": "例: FA.PDS — 自動でグループ分けされます",
        "vi": "vd: FA.PDS — sẽ tự động xếp vào nhóm tương ứng"},
    "login.login_btn": {"en": "Log in", "ja": "ログイン", "vi": "Đăng nhập"},
    "login.exit_btn": {"en": "Exit", "ja": "終了", "vi": "Thoát"},
    "login.err_invalid": {
        "en": "Invalid account or access code.", "ja": "アカウントまたはアクセスコードが無効です。",
        "vi": "Tài khoản hoặc mã truy cập không đúng."},
    "login.err_admin_exists": {
        "en": "An Admin account already exists for this shared folder — the app has exactly one. Log in with an account issued by the Admin instead.",
        "ja": "この共有フォルダには既に管理者アカウントが存在します（管理者は1人のみ）。管理者から発行されたアカウントでログインしてください。",
        "vi": "Thư mục dùng chung này đã có tài khoản Admin — app chỉ có duy nhất 1 Admin. Hãy đăng nhập bằng tài khoản do Admin cấp."},
    "login.err_missing_fields": {
        "en": "Enter both a shared folder path and an account name.",
        "ja": "共有フォルダのパスとアカウント名の両方を入力してください。",
        "vi": "Nhập đường dẫn thư mục chia sẻ và tên tài khoản."},
    "login.err_shared_dir": {
        "en": "Could not create the shared folder: {error}",
        "ja": "共有フォルダを作成できませんでした: {error}",
        "vi": "Không tạo được thư mục chia sẻ: {error}"},
    "login.bootstrap_hint": {
        "en": "No accounts exist yet. Choose a shared folder (a network share or a "
              "locally-synced OneDrive folder) and create the first Admin account.",
        "ja": "アカウントがまだありません。共有フォルダ（ネットワーク共有、または同期済みの "
              "OneDrive フォルダ）を選び、最初の管理者アカウントを作成してください。",
        "vi": "Chưa có tài khoản nào. Chọn một thư mục chia sẻ (network share hoặc thư mục "
              "OneDrive đã đồng bộ trên máy) và tạo tài khoản Admin đầu tiên."},
    "login.shared_dir": {"en": "Shared folder", "ja": "共有フォルダ", "vi": "Thư mục chia sẻ"},
    "login.browse": {"en": "Browse…", "ja": "参照…", "vi": "Chọn…"},
    "login.create_admin": {
        "en": "Create Admin account", "ja": "管理者アカウントを作成", "vi": "Tạo tài khoản Admin"},
    "login.code_shown_title": {"en": "Admin account created", "ja": "管理者アカウントを作成しました",
                                "vi": "Đã tạo tài khoản Admin"},
    "login.code_shown_body": {
        "en": "Account: {username}\nAccess code: {code}\n\nSave this code now — it will "
              "not be shown again. You are now logged in.",
        "ja": "アカウント: {username}\nアクセスコード: {code}\n\n今すぐこのコードを保存してくださ"
              "い — 二度と表示されません。ログインしました。",
        "vi": "Tài khoản: {username}\nMã truy cập: {code}\n\nHãy lưu lại mã này ngay — mã sẽ "
              "không hiển thị lại lần nào nữa. Bạn đã đăng nhập."},
    "login.unreachable": {
        "en": "Can't reach the shared folder:\n{path}", "ja": "共有フォルダに到達できません:\n{path}",
        "vi": "Không truy cập được thư mục chia sẻ:\n{path}"},
    "login.offline_hint": {
        "en": "Last successful login on this machine: {username} ({role}).",
        "ja": "このマシンでの最後の正常なログイン: {username} ({role})。",
        "vi": "Lần đăng nhập thành công gần nhất trên máy này: {username} ({role})."},
    "login.offline_btn": {"en": "Continue offline as {role}", "ja": "{role} としてオフラインで続行",
                           "vi": "Tiếp tục offline với vai trò {role}"},
    "login.no_offline_cache": {
        "en": "No previous successful login on this machine — contact your Admin.",
        "ja": "このマシンでの過去のログイン履歴がありません — 管理者に連絡してください。",
        "vi": "Chưa có lượt đăng nhập thành công nào trên máy này — liên hệ Admin."},
    "login.retry_btn": {"en": "Retry", "ja": "再試行", "vi": "Thử lại"},

    # ---- accounts_tab.py: Monitoring -> Accounts panel (Admin/Sub-admin) --
    "accounts.edit_title": {"en": "Edit account", "ja": "アカウントを編集", "vi": "Sửa tài khoản"},
    "accounts.add_title": {"en": "Add account", "ja": "アカウントを追加", "vi": "Thêm tài khoản"},
    "accounts.f_username": {"en": "Account", "ja": "アカウント", "vi": "Tài khoản"},
    "accounts.f_display_name": {"en": "Name", "ja": "名前", "vi": "Tên"},
    "accounts.f_email": {"en": "Email", "ja": "メール", "vi": "Email"},
    "accounts.f_email_placeholder": {
        "en": "name@company.com (optional)", "ja": "name@company.com（任意）",
        "vi": "name@company.com (không bắt buộc)"},
    "accounts.f_role": {"en": "Role", "ja": "役割", "vi": "Vai trò"},
    "accounts.f_department": {"en": "Department", "ja": "部門", "vi": "Bộ phận"},
    "accounts.f_group": {"en": "Group", "ja": "グループ", "vi": "Nhóm"},
    "accounts.f_group_name": {"en": "Group name", "ja": "グループ名", "vi": "Tên nhóm"},
    "accounts.no_group": {"en": "— No group —", "ja": "— グループなし —", "vi": "— Không có nhóm —"},
    "accounts.role.admin": {"en": "Admin", "ja": "管理者", "vi": "Admin"},
    "accounts.role.subadmin": {"en": "Sub-admin", "ja": "サブ管理者", "vi": "Sub-admin"},
    "accounts.role.user": {"en": "User", "ja": "ユーザー", "vi": "User"},
    "accounts.no_shared_dir": {
        "en": "No shared folder configured — set one in Settings to manage accounts.",
        "ja": "共有フォルダが設定されていません — 設定でアカウント管理用のフォルダを指定してください。",
        "vi": "Chưa cấu hình thư mục chia sẻ — thiết lập trong Settings để quản lý tài khoản."},
    "accounts.shared_dir_hint": {"en": "Shared folder: {path}", "ja": "共有フォルダ: {path}",
                                  "vi": "Thư mục chia sẻ: {path}"},
    "accounts.ungrouped": {"en": "Ungrouped", "ja": "未分類", "vi": "Chưa có nhóm"},
    "accounts.filter_all_groups": {"en": "All groups", "ja": "すべてのグループ", "vi": "Tất cả nhóm"},
    "accounts.delete_title": {"en": "Delete account", "ja": "アカウントを削除", "vi": "Xóa tài khoản"},
    "accounts.delete_confirm": {"en": "Delete account '{username}'?", "ja": "アカウント「{username}」を削"
                                 "除しますか？", "vi": "Xóa tài khoản '{username}'?"},
    "accounts.new_group_title": {"en": "New group", "ja": "新しいグループ", "vi": "Nhóm mới"},
    "accounts.add_btn": {"en": "Add", "ja": "追加", "vi": "Thêm"},
    "accounts.edit_btn": {"en": "Edit", "ja": "編集", "vi": "Sửa"},
    "accounts.delete_btn": {"en": "Delete", "ja": "削除", "vi": "Xóa"},
    "accounts.generate_code_btn": {"en": "Generate code", "ja": "コード発行", "vi": "Tạo mã"},
    "accounts.new_group_btn": {"en": "New group", "ja": "新しいグループ", "vi": "Nhóm mới"},
    "accounts.drag_move_hint": {
        "en": "Drag an account onto a group to move it there.",
        "ja": "アカウントをグループにドラッグすると移動できます。",
        "vi": "Kéo tài khoản thả vào một nhóm để di chuyển đến đó."},
    "accounts.err_admin_exists": {
        "en": "An Admin account already exists — the app has exactly one.",
        "ja": "管理者アカウントは既に存在します（1人のみ）。",
        "vi": "Đã có tài khoản Admin — app chỉ có duy nhất 1 Admin."},
    "accounts.search_placeholder": {
        "en": "Search accounts (or type a question and press )…",
        "ja": "アカウント検索（質問を入力しても可）…",
        "vi": "Tìm tài khoản (hoặc gõ câu hỏi rồi bấm )…"},
    "accounts.ai_search_btn": {"en": "AI", "ja": "AI", "vi": "AI"},
    "accounts.ai_search_tooltip": {
        "en": "AI turns your question into a search keyword (e.g. \"who in CAE has no department?\").",
        "ja": "質問をAIが検索キーワードに変換します。",
        "vi": "AI chuyển câu hỏi của bạn thành từ khóa tìm kiếm (vd: \"ai trong CAE chưa có phòng ban?\")."},
    "accounts.excel_template_btn": {
        "en": "Excel template", "ja": "Excelテンプレート", "vi": "Mẫu Excel"},
    "accounts.excel_import_btn": {
        "en": "Import Excel", "ja": "Excel取り込み", "vi": "Nhập từ Excel"},
    "accounts.excel_imported": {
        "en": "Created {n} account(s).", "ja": "{n} 件のアカウントを作成しました。",
        "vi": "Đã tạo {n} tài khoản."},
    "accounts.excel_codes_saved": {
        "en": "Access codes saved to: {path}", "ja": "アクセスコードの保存先: {path}",
        "vi": "Mã truy cập đã lưu tại: {path}"},
    "accounts.usage_title": {"en": "Usage & Cost by account", "ja": "アカウント別の使用量とコスト",
                              "vi": "Sử dụng & Chi phí theo tài khoản"},
    "accounts.period.day": {"en": "Day", "ja": "日", "vi": "Ngày"},
    "accounts.period.week": {"en": "Week", "ja": "週", "vi": "Tuần"},
    "accounts.period.month": {"en": "Month", "ja": "月", "vi": "Tháng"},
    "accounts.period.year": {"en": "Year", "ja": "年", "vi": "Năm"},
    "accounts.col_name": {"en": "Name", "ja": "名前", "vi": "Tên"},
    "accounts.col_account": {"en": "Account", "ja": "アカウント", "vi": "Tài khoản"},
    "accounts.col_machine": {"en": "Machine", "ja": "マシン", "vi": "Máy"},
    "accounts.col_department": {"en": "Department", "ja": "部門", "vi": "Bộ phận"},
    "accounts.col_tokens": {"en": "Tokens", "ja": "トークン", "vi": "Token"},
    "accounts.col_cost": {"en": "Cost", "ja": "コスト", "vi": "Chi phí"},

    # ---- app.py: top bar, tabs, toasts, tray ------------------------
    "app.logo": {"en": "Cowork-Local BamBOO", "ja": "Cowork-Local BamBOO", "vi": "Cowork-Local BamBOO"},
    "app.provider": {"en": "Provider:", "ja": "プロバイダー:", "vi": "Nhà cung cấp:"},
    "app.language": {"en": "Language:", "ja": "言語:", "vi": "Ngôn ngữ:"},
    "app.settings": {"en": "Settings", "ja": "設定", "vi": "Cài đặt"},
    # Shown on the cover while a language switch blocks the GUI thread. It is
    # deliberately read BEFORE the switch, so it appears in the language the
    # user is leaving — the only one they can still read at that moment.
    "app.lang.switching": {
        "en": "Switching language…", "ja": "言語を切り替えています…",
        "vi": "Đang đổi ngôn ngữ…"},
    "app.tab.dashboard": {"en": "Dashboard", "ja": "ダッシュボード", "vi": "Dashboard"},
    "app.tab.schedule": {"en": "Schedule Task", "ja": "タスクスケジュール", "vi": "Schedule Task"},
    "app.tab.cowork": {"en": "Cowork", "ja": "Cowork", "vi": "Cowork"},
    "app.tab.code": {"en": "Code", "ja": "Code", "vi": "Code"},
    "app.tab.structure": {"en": "GraphRAG", "ja": "GraphRAG", "vi": "GraphRAG"},
    "app.tab.workspace": {"en": "Workspace", "ja": "ワークスペース", "vi": "Workspace"},
    "app.tab.monitoring": {"en": "Monitoring", "ja": "モニタリング", "vi": "Giám sát"},
    "app.nav.collapse_tooltip": {"en": "Collapse menu to icons only", "ja": "メニューをアイコンのみに折りたたむ", "vi": "Thu gọn menu về icon"},
    "app.nav.expand_tooltip": {"en": "Expand menu", "ja": "メニューを展開", "vi": "Mở rộng menu"},
    "app.nav.menu_label": {"en": "MENU", "ja": "メニュー", "vi": "MENU"},
    # Shown on the rail rows the project gate disables (Cowork, GraphRAG) —
    # they stay listed and greyed instead of disappearing from the menu.
    "app.nav.needs_project": {
        "en": "Select a project first", "ja": "先にプロジェクトを選択してください",
        "vi": "Chọn project trước"},
    # Rail header: the project a new chat will be created in, and what to do
    # when there is no project yet.
    "app.nav.project_pick": {
        "en": "Project for new chats", "ja": "新しいチャットのプロジェクト",
        "vi": "Project cho đoạn chat mới"},
    "app.nav.no_project": {
        "en": "No project yet", "ja": "プロジェクトなし", "vi": "Chưa có project"},
    "app.nav.recents": {"en": "RECENTS", "ja": "最近", "vi": "GẦN ĐÂY"},
    "app.nav.all_projects": {
        "en": "All projects…", "ja": "すべてのプロジェクト…", "vi": "Tất cả project…"},
    "app.nav.create_project_first": {
        "en": "Create a project first", "ja": "先にプロジェクトを作成してください",
        "vi": "Tạo project trước"},

    # ---- workspace_tab.py (Projects — Claude-Projects style) -----------
    "workspace.header": {"en": "Manage projects", "ja": "プロジェクト管理", "vi": "Quản lý project"},
    "workspace.tab_cowork": {"en": "Cowork", "ja": "Cowork", "vi": "Cowork"},
    "workspace.tab_graphrag": {"en": "GraphRAG", "ja": "GraphRAG", "vi": "GraphRAG"},
    "workspace.tab_project": {"en": "Project", "ja": "プロジェクト", "vi": "Project"},
    "workspace.tab_folder": {"en": "Folder", "ja": "フォルダ", "vi": "Thư mục"},
    "folder.path_placeholder": {
        "en": "Folder path", "ja": "フォルダのパス", "vi": "Đường dẫn thư mục"},
    "folder.open_folder": {"en": "Open folder", "ja": "フォルダを開く", "vi": "Mở thư mục"},
    "folder.save": {"en": "Save", "ja": "保存", "vi": "Lưu"},
    "folder.open_external": {
        "en": "Open externally", "ja": "外部で開く", "vi": "Mở bằng app ngoài"},
    "folder.preview": {"en": "Preview", "ja": "プレビュー", "vi": "Xem trước"},
    "folder.edit": {"en": "Edit", "ja": "編集", "vi": "Chỉnh sửa"},
    "folder.select_file": {
        "en": "Select a file in the tree to view or edit it.",
        "ja": "ツリーでファイルを選択して表示・編集します。",
        "vi": "Chọn một tệp trong cây thư mục để xem hoặc chỉnh sửa."},
    "folder.binary_file": {
        "en": "Binary or very large file — open it externally to view.",
        "ja": "バイナリまたは非常に大きいファイルです — 外部で開いて表示してください。",
        "vi": "Tệp nhị phân hoặc quá lớn — mở bằng app ngoài để xem."},
    "folder.converting": {
        "en": "Rendering document… (converting to PDF via LibreOffice)",
        "ja": "ドキュメントを表示中…（LibreOffice で PDF に変換しています）",
        "vi": "Đang hiển thị tài liệu… (chuyển sang PDF bằng LibreOffice)"},
    "folder.doc_unreadable": {
        "en": "Could not extract text ({note}). Open it externally for the full document.",
        "ja": "テキストを抽出できませんでした ({note})。完全な文書は外部で開いてください。",
        "vi": "Không trích xuất được nội dung ({note}). Mở bằng app ngoài để xem đầy đủ."},
    "folder.saved": {"en": "Saved {name}", "ja": "{name} を保存しました", "vi": "Đã lưu {name}"},
    "folder.ai_edit": {"en": "AI Edit", "ja": "AI 編集", "vi": "AI Edit"},
    "folder.ai_edit_tooltip": {
        "en": "Edit the open file with AI (uses the Cowork conversation context)",
        "ja": "AI で開いているファイルを編集（Cowork の会話コンテキストを利用）",
        "vi": "Dùng AI chỉnh sửa file đang mở (dùng ngữ cảnh hội thoại Cowork)"},
    "folder.ai_placeholder": {
        "en": "Describe the edit… (e.g. add error handling)",
        "ja": "編集内容を入力…（例: エラー処理を追加）",
        "vi": "Mô tả chỉnh sửa… (vd: thêm xử lý lỗi)"},
    "folder.ai_send": {"en": "Send", "ja": "送信", "vi": "Gửi"},
    "folder.ai_no_file": {
        "en": "Open a text/code file in Edit mode first.",
        "ja": "先にテキスト/コードファイルを編集モードで開いてください。",
        "vi": "Hãy mở một file text/code ở chế độ Edit trước."},
    "folder.ai_applied": {
        "en": "✓ Applied the edit — review it and Save.",
        "ja": "✓ 編集を適用しました — 確認して保存してください。",
        "vi": "✓ Đã áp dụng chỉnh sửa — kiểm tra rồi Lưu."},
    "folder.ai_empty": {
        "en": "(the model didn't return an edited file)",
        "ja": "(モデルは編集後のファイルを返しませんでした)",
        "vi": "(model không trả về file đã chỉnh sửa)"},
    "folder.ai_error": {
        "en": "AI edit failed: {err}", "ja": "AI 編集に失敗しました: {err}",
        "vi": "AI edit thất bại: {err}"},
    "folder.ai_running": {
        "en": "AI is editing {name}… (keeps running while you do other things)",
        "ja": "AI が {name} を編集中…（他の作業をしていても継続します）",
        "vi": "AI đang chỉnh sửa {name}… (vẫn chạy tiếp khi bạn làm việc khác)"},
    "folder.ai_done": {
        "en": "AI edit finished for {name} — review it in the Folder tab.",
        "ja": "{name} の AI 編集が完了しました — Folder タブで確認してください。",
        "vi": "AI edit xong cho {name} — kiểm tra ở tab Folder."},
    "folder.ai_status_running": {
        "en": "processing…", "ja": "処理中…", "vi": "đang xử lí…"},
    "folder.ai_status_done": {
        "en": "done", "ja": "完了", "vi": "xong"},
    "folder.ai_planning": {
        "en": "Planning…", "ja": "計画中…", "vi": "Đang lập kế hoạch…"},
    "folder.ai_apply": {"en": "Apply", "ja": "適用", "vi": "Áp dụng"},
    "folder.ai_discard": {"en": "Discard", "ja": "破棄", "vi": "Hủy"},
    "folder.ai_proposed": {
        "en": "Proposed changes (review)", "ja": "変更案（確認）",
        "vi": "Thay đổi đề xuất (xem lại)"},
    "folder.ai_review_hint": {
        "en": "Review the diff, then Apply or Discard.",
        "ja": "差分を確認してから、適用または破棄してください。",
        "vi": "Xem lại diff rồi bấm Áp dụng hoặc Hủy."},
    "folder.ai_proposed_status": {
        "en": "AI proposed an edit for {name} — review & Apply.",
        "ja": "{name} の編集案が出ました — 確認して適用してください。",
        "vi": "AI đề xuất chỉnh sửa {name} — xem lại & Áp dụng."},
    "folder.ai_discarded": {
        "en": "Discarded — the file was not changed.",
        "ja": "破棄しました — ファイルは変更されていません。",
        "vi": "Đã hủy — file không bị thay đổi."},
    "folder.ai_new_file": {"en": "a new file", "ja": "新規ファイル", "vi": "file mới"},
    "folder.ai_proposed_new": {
        "en": "Proposed NEW file: {name} (review)",
        "ja": "新規ファイルの提案: {name}（確認）",
        "vi": "Đề xuất tạo file MỚI: {name} (xem lại)"},
    "folder.ai_created": {
        "en": "Created {name}", "ja": "{name} を作成しました", "vi": "Đã tạo {name}"},
    "folder.ai_image_confirm_title": {
        "en": "Confirm image change", "ja": "画像変更の確認", "vi": "Xác nhận sửa ảnh"},
    "folder.ai_image_confirm": {
        "en": "This edit replaces one or more images in the slide. Proceed?",
        "ja": "この編集はスライド内の画像を置き換えます。実行しますか？",
        "vi": "Chỉnh sửa này sẽ thay ảnh trong slide. Tiếp tục?"},
    "folder.ai_image_declined": {
        "en": "Image change cancelled.", "ja": "画像の変更をキャンセルしました。",
        "vi": "Đã hủy thay đổi ảnh."},
    "folder.ai_image_confirm_gen": {
        "en": "This will GENERATE image(s) with the AI model and save them into the folder. Proceed?",
        "ja": "AI モデルで画像を生成してフォルダに保存します。実行しますか？",
        "vi": "Sẽ TẠO ảnh bằng model AI và lưu vào thư mục. Tiếp tục?"},
    "folder.ai_image_plan": {
        "en": "Will generate these illustration image(s):",
        "ja": "以下のイラスト画像を生成します:",
        "vi": "Sẽ tạo các ảnh minh họa sau:"},
    "folder.ai_generating": {
        "en": "Generating image(s)…", "ja": "画像を生成中…", "vi": "Đang tạo ảnh…"},
    "folder.ai_image_created": {
        "en": "Generated image {name}", "ja": "画像 {name} を生成しました",
        "vi": "Đã tạo ảnh {name}"},
    "folder.ai_image_failed": {
        "en": "Image generation failed: {err}", "ja": "画像生成に失敗しました: {err}",
        "vi": "Tạo ảnh thất bại: {err}"},
    "folder.ai_model_label": {"en": "Model:", "ja": "モデル:", "vi": "Model:"},
    "folder.ai_model_auto": {
        "en": "(auto — provider default)", "ja": "(自動 — 既定モデル)",
        "vi": "(tự động — model mặc định)"},
    "folder.ai_image_suggest": {
        "en": "💡 Tip: pick model '{model}' above for image generation.",
        "ja": "💡 画像生成には上のモデル '{model}' を選ぶのがおすすめです。",
        "vi": "💡 Gợi ý: chọn model '{model}' ở trên để tạo ảnh."},
    "folder.ai_image_suggest_all": {
        "en": "💡 This request involves images. Image-capable models found on other providers:",
        "ja": "💡 このリクエストは画像を含みます。他プロバイダーで見つかった画像対応モデル:",
        "vi": "💡 Yêu cầu này liên quan đến ảnh. Model tạo ảnh tìm thấy ở các provider khác:"},
    "folder.ai_image_none": {
        "en": "💡 This request involves images, but no image-capable model was found on any configured provider.",
        "ja": "💡 このリクエストは画像を含みますが、設定済みのどのプロバイダーにも画像対応モデルが見つかりませんでした。",
        "vi": "💡 Yêu cầu này liên quan đến ảnh, nhưng không tìm thấy model tạo ảnh ở provider nào đã cấu hình."},
    "folder.ai_image_use_selected": {
        "en": "💡 No dedicated image model found — will use your selected model '{model}' to generate images.",
        "ja": "💡 専用の画像モデルが見つかりません — 選択中のモデル '{model}' で画像を生成します。",
        "vi": "💡 Không tìm thấy model tạo ảnh chuyên biệt — sẽ dùng model bạn đã chọn '{model}' để tạo ảnh."},
    "folder.ai_queued": {
        "en": "⏳ Queued (#{n}) — runs after the current edit.",
        "ja": "⏳ キューに追加 (#{n}) — 現在の編集の後に実行します。",
        "vi": "⏳ Đã thêm vào hàng đợi (#{n}) — chạy sau lệnh hiện tại."},
    "folder.ai_queue_count": {
        "en": "{n} queued", "ja": "{n} 件待機中", "vi": "{n} đang chờ"},
    "terminal.title": {"en": "Terminal", "ja": "ターミナル", "vi": "Terminal"},
    "terminal.run": {"en": "Run", "ja": "実行", "vi": "Chạy"},
    "terminal.placeholder": {
        "en": "Type a command and press Enter…", "ja": "コマンドを入力して Enter…",
        "vi": "Nhập lệnh rồi nhấn Enter…"},
    "terminal.expand_tooltip": {
        "en": "Expand terminal", "ja": "ターミナルを開く", "vi": "Mở terminal"},
    "terminal.collapse_tooltip": {
        "en": "Collapse terminal", "ja": "ターミナルを閉じる", "vi": "Thu gọn terminal"},
    "terminal.busy": {
        "en": "[a command is still running]", "ja": "[コマンドがまだ実行中です]",
        "vi": "[đang chạy một lệnh khác]"},
    "terminal.cd_error": {
        "en": "cd: no such directory: {path}", "ja": "cd: ディレクトリがありません: {path}",
        "vi": "cd: không có thư mục: {path}"},
    "terminal.launch_error": {
        "en": "[failed to launch the shell]", "ja": "[シェルの起動に失敗しました]",
        "vi": "[không khởi chạy được shell]"},
}
