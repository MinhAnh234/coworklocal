"""Chuỗi hiển thị — phần sidebar.

Cắt ra từ ``i18n.py``: một dict 3.000 dòng không mở nổi để sửa một chữ.
Cắt theo mốc phân đoạn có sẵn, nên mỗi cụm vẫn là các màn đi liền nhau.
``i18n.py`` gộp tất cả lại thành ``STRINGS``.
"""
from __future__ import annotations

from typing import Dict

STRINGS: Dict[str, Dict[str, str]] = {
    "terminal.exit": {
        "en": "[process exited with code {code}]", "ja": "[プロセス終了 コード {code}]",
        "vi": "[tiến trình kết thúc, mã {code}]"},
    "folder.save_error": {
        "en": "Save failed: {err}", "ja": "保存に失敗しました: {err}", "vi": "Lưu thất bại: {err}"},

    "workspace.hint": {
        "en": ("Group chats into projects. Every thread in a project follows the shared "
               "Instructions, works inside the project's own sandbox folder, and auto-reads "
               "files placed at that folder's root (project knowledge)."),
        "ja": ("チャットをプロジェクトにまとめます。プロジェクト内の各スレッドは共有の指示に従い、"
               "プロジェクト専用のサンドボックスフォルダ内で動作し、そのルートに置かれたファイル"
               "（プロジェクトナレッジ）を自動的に読み込みます。"),
        "vi": ("Gom các cuộc chat thành project. Mọi thread trong một project tuân theo phần "
               "Instructions chung, làm việc trong thư mục sandbox riêng của project, và tự đọc "
               "các file đặt ở gốc thư mục đó (project knowledge)."),
    },
    "workspace.new_project": {"en": "New project", "ja": "新規プロジェクト", "vi": "Project mới"},
    "workspace.projects_heading": {"en": "PROJECTS", "ja": "プロジェクト", "vi": "PROJECT"},
    "workspace.folder_label": {"en": "Workspace folder", "ja": "作業フォルダ", "vi": "Thư mục làm việc"},
    "workspace.counts": {
        "en": "{chats} chats · {tasks} tasks",
        "ja": "チャット {chats} · タスク {tasks}",
        "vi": "{chats} đoạn chat · {tasks} task"},
    "workspace.delete": {"en": "Delete", "ja": "削除", "vi": "Xóa"},
    "workspace.delete_confirm": {
        "en": "Delete project “{name}”? Its conversations and files are kept (threads move to General).",
        "ja": "プロジェクト「{name}」を削除しますか？会話とファイルは保持されます（スレッドは General へ移動）。",
        "vi": "Xóa project “{name}”? Hội thoại và file vẫn được giữ (thread chuyển về General).",
    },
    "workspace.deleted": {"en": "Deleted project {name}.", "ja": "プロジェクト {name} を削除しました。", "vi": "Đã xóa project {name}."},
    "workspace.conversation_project_missing": {
        "en": "This conversation's project no longer exists — it can't be opened.",
        "ja": "この会話のプロジェクトは既に存在しないため開けません。",
        "vi": "Project của hội thoại này không còn tồn tại — không thể mở."},
    "workspace.name": {"en": "Name", "ja": "名前", "vi": "Tên"},
    "workspace.description": {"en": "Description", "ja": "説明", "vi": "Mô tả"},
    "workspace.instructions": {"en": "Instructions", "ja": "Instructions", "vi": "Instructions"},
    "workspace.instructions_placeholder": {
        "en": "e.g. \"All answers in Vietnamese. We are building the X reporting tool; always follow the naming rules …\"",
        "ja": "例:「回答はすべて日本語で。X レポートツールを開発中。命名規則に従うこと …」",
        "vi": "vd: \"Trả lời bằng tiếng Việt. Team đang xây tool báo cáo X; luôn theo quy tắc đặt tên …\"",
    },
    "workspace.browse": {"en": "Change", "ja": "変更", "vi": "Đổi"},
    "workspace.browse_tooltip": {
        "en": "Choose the project's workspace folder (agent sandbox + shared knowledge root)",
        "ja": "プロジェクトのワークスペースフォルダを選択（エージェントのサンドボックス＋共有ナレッジのルート）",
        "vi": "Chọn thư mục workspace của project (sandbox của agent + gốc chứa knowledge chung)",
    },
    "workspace.open_folder": {"en": "Open", "ja": "開く", "vi": "Mở"},
    "workspace.save": {"en": "Save project", "ja": "プロジェクトを保存", "vi": "Lưu project"},
    "workspace.saved": {"en": "Saved project {name}.", "ja": "プロジェクト {name} を保存しました。", "vi": "Đã lưu project {name}."},
    "workspace.threads": {"en": "Conversations in this project", "ja": "このプロジェクトの会話", "vi": "Hội thoại trong project này"},
    "workspace.new_chat": {"en": "New chat in this project", "ja": "このプロジェクトで新規チャット", "vi": "Chat mới trong project này"},
    "workspace.default_new_name": {"en": "New project", "ja": "新規プロジェクト", "vi": "Project mới"},
    "workspace.collapse_projects_tooltip": {"en": "Collapse the project list", "ja": "プロジェクト一覧を折りたたむ", "vi": "Thu gọn danh sách project"},
    "workspace.expand_projects_tooltip": {"en": "Click to expand the project list", "ja": "クリックしてプロジェクト一覧を展開", "vi": "Bấm để mở rộng danh sách project"},
    "app.status.ready": {"en": "Ready.", "ja": "準備完了。", "vi": "Sẵn sàng."},
    "app.status.using_provider": {"en": "Using {label}.", "ja": "{label} を使用中。", "vi": "Đang dùng {label}."},
    "app.status.settings_saved": {"en": "Settings saved.", "ja": "設定を保存しました。", "vi": "Đã lưu cài đặt."},
    "app.credit": {"en": "Made by QuanDH14", "ja": "Made by QuanDH14", "vi": "Made by QuanDH14"},
    "app.tray.open": {"en": "Open Cowork Local", "ja": "Cowork Local を開く", "vi": "Mở Cowork Local"},
    "app.tray.quit": {"en": "Quit", "ja": "終了", "vi": "Thoát"},
    "app.tray.running_body": {
        "en": "Running in the background — tasks keep working. Right-click the tray icon to Quit.",
        "ja": "バックグラウンドで実行中です。タスクは継続します。終了するにはトレイアイコンを右クリックしてください。",
        "vi": "Đang chạy nền — tác vụ vẫn tiếp tục. Chuột phải vào biểu tượng khay để Thoát.",
    },
    "app.toast.done": {"en": "{name}: done", "ja": "{name}: 完了", "vi": "{name}: hoàn thành"},
    "app.toast.error": {"en": "{name}: error", "ja": "{name}: エラー", "vi": "{name}: lỗi"},
    "app.toast.task_done": {"en": "Task done: {title}", "ja": "タスク完了: {title}",
                             "vi": "Task hoàn thành: {title}"},
    "app.toast.task_failed": {"en": "Task failed: {title}", "ja": "タスク失敗: {title}",
                               "vi": "Task lỗi: {title}"},

    # ---- sidebar.py (History) ----------------------------------------
    "sidebar.header": {"en": "History", "ja": "履歴", "vi": "Lịch sử"},
    "sidebar.filter.all": {"en": "All", "ja": "すべて", "vi": "Tất cả"},
    "sidebar.filter.cowork": {"en": "Cowork", "ja": "Cowork", "vi": "Cowork"},
    "sidebar.filter.code": {"en": "Code", "ja": "Code", "vi": "Code"},
    "sidebar.search_placeholder": {
        "en": "Search by title or content…", "ja": "タイトルまたは内容で検索…",
        "vi": "Tìm theo tiêu đề hoặc nội dung…"},
    "sidebar.search_tooltip": {
        "en": "Search conversation history by title or message content.",
        "ja": "会話履歴をタイトルまたはメッセージ内容で検索します。",
        "vi": "Tìm kiếm lịch sử hội thoại theo tiêu đề hoặc nội dung tin nhắn."},
    "sidebar.no_matches": {"en": "(no matches)", "ja": "（一致なし）", "vi": "(không tìm thấy)"},
    "sidebar.refresh": {"en": "Refresh", "ja": "更新", "vi": "Làm mới"},
    "sidebar.refresh_tooltip": {
        "en": "Update the list + this conversation's agent status",
        "ja": "一覧とこの会話のエージェント状態を更新",
        "vi": "Cập nhật danh sách + trạng thái agent của hội thoại đang xem",
    },
    "sidebar.empty": {"en": "(empty)", "ja": "（空）", "vi": "(trống)"},
    "sidebar.running_suffix": {"en": "   · running", "ja": "   · 実行中", "vi": "   · đang chạy"},
    "sidebar.expand_tooltip": {
        "en": "Click to expand the History panel", "ja": "クリックして履歴パネルを展開",
        "vi": "Bấm để mở lại bảng Lịch sử"},
    "sidebar.collapse_tooltip": {
        "en": "Collapse the History panel", "ja": "履歴パネルを折りたたむ",
        "vi": "Thu gọn bảng Lịch sử"},
    "sidebar.menu.pin": {"en": "Pin", "ja": "ピン留め", "vi": "Ghim"},
    "sidebar.menu.unpin": {"en": "Unpin", "ja": "ピン留め解除", "vi": "Bỏ ghim"},
    "sidebar.menu.rename": {"en": "Rename…", "ja": "名前を変更…", "vi": "Đổi tên…"},
    "sidebar.menu.delete": {"en": "Delete", "ja": "削除", "vi": "Xóa"},
    "sidebar.rename.title": {"en": "Rename conversation", "ja": "会話の名前を変更", "vi": "Đổi tên hội thoại"},
    "sidebar.rename.label": {"en": "New name:", "ja": "新しい名前:", "vi": "Tên mới:"},
    "sidebar.delete.title": {"en": "Delete conversation", "ja": "会話を削除", "vi": "Xóa hội thoại"},
    "sidebar.delete.confirm": {"en": "Delete '{title}'?", "ja": "「{title}」を削除しますか？", "vi": "Xóa '{title}'?"},
    "sidebar.menu.delete_selected": {"en": "Delete {n} selected", "ja": "選択した{n}件を削除", "vi": "Xóa {n} mục đã chọn"},
    "sidebar.delete_multi.confirm": {
        "en": "Delete {n} selected conversations? This cannot be undone.",
        "ja": "選択した{n}件の会話を削除しますか？元に戻せません。",
        "vi": "Xóa {n} hội thoại đã chọn? Không thể hoàn tác."},

    # ---- widgets.py (Plan / Files sections, collapse strips) ---------
    "widgets.plan_title": {"en": "Plan", "ja": "プラン", "vi": "Plan"},
    "widgets.input_files": {"en": "Input files", "ja": "入力ファイル", "vi": "Tệp đầu vào"},
    "widgets.output_files": {"en": "Output files", "ja": "出力ファイル", "vi": "Tệp đầu ra"},

    # ---- chat_view.py --------------------------------------------------
    "chat.running": {"en": "Running", "ja": "実行中", "vi": "Đang chạy"},
    "chat.thinking": {"en": "Thinking", "ja": "思考中", "vi": "Đang nghĩ"},
    "chat.creating": {"en": "Creating", "ja": "作成中", "vi": "Đang tạo"},
    "chat.editing": {"en": "Editing", "ja": "編集中", "vi": "Đang sửa"},
    "chat.installing": {"en": "Installing", "ja": "インストール中", "vi": "Đang cài đặt"},
    "chat.reading": {"en": "Reading", "ja": "読み込み中", "vi": "Đang đọc"},
    "chat.you": {"en": "You", "ja": "あなた", "vi": "Bạn"},
    "chat.assistant": {"en": "Assistant", "ja": "アシスタント", "vi": "Assistant"},
    "chat.error": {"en": "Error", "ja": "エラー", "vi": "Lỗi"},
    "help_agent.title": {
        # The audit page names this AI Assistant, and keeps it the same in every
        # language — it is a product name, not a description.
        "en": "AI Assistant", "ja": "AI Assistant", "vi": "AI Assistant"},
    "help_agent.greeting": {
        "en": "Hello {name}, have a great working day! How can I help you use the app?",
        "ja": "こんにちは {name} さん、良い一日を！アプリの使い方について何かお手伝いできますか？",
        "vi": "Xin chào {name}, chúc bạn một ngày làm việc vui vẻ! Mình có thể giúp gì cho bạn khi dùng app?"},
    "help_agent.default_user": {"en": "Admin", "ja": "Admin", "vi": "Admin"},
    "help_agent.placeholder": {
        "en": "Ask how to use the app…", "ja": "アプリの使い方を質問…",
        "vi": "Hỏi cách sử dụng app…"},
    "help_agent.open_tooltip": {
        "en": "AI Assistant — help using the app",
        "ja": "AI Assistant — アプリの使い方をサポート",
        "vi": "AI Assistant — hỗ trợ sử dụng app"},
    "help_agent.collapse_tooltip": {
        "en": "Minimize", "ja": "最小化", "vi": "Thu nhỏ"},
    "help_agent.hide_tooltip": {
        "en": "Hide to the edge", "ja": "端に隠す", "vi": "Ẩn vào cạnh phải"},
    "help_agent.dot_hint": {
        "en": "right-click to hide",
        "ja": "右クリックで非表示",
        "vi": "chuột phải để ẩn"},
    # The name on the launcher pill. Deliberately the same in every language —
    # it is a product name, and it only shows on hover, so length is not a
    # constraint the way it was on a permanently visible badge.
    "help_agent.badge": {
        "en": "AI Assistant", "ja": "AI Assistant", "vi": "AI Assistant"},
    "help_agent.more_tooltip": {
        "en": "More", "ja": "その他", "vi": "Thêm"},
    "help_agent.show_tooltip": {
        "en": "Show the AI Assistant", "ja": "AI Assistant を表示",
        "vi": "Hiện AI Assistant"},
    "help_agent.empty_reply": {
        "en": "(no answer)", "ja": "(回答なし)", "vi": "(không có phản hồi)"},
    "help_agent.error": {
        "en": "Sorry, I couldn't answer right now: {error}",
        "ja": "申し訳ありません、今は回答できませんでした: {error}",
        "vi": "Xin lỗi, hiện chưa thể trả lời: {error}"},
    "chat.model_switched": {
        "en": "↻ Auto-switched to {model} — re-checking the previous step, then continuing.",
        "ja": "↻ {model} に自動切り替え — 直前のステップを確認してから続行します。",
        "vi": "↻ Đã tự động chuyển sang {model} — kiểm tra lại bước trước rồi tiếp tục."},
    "chat.provider_default_short": {
        "en": "the provider's default model", "ja": "プロバイダー既定のモデル",
        "vi": "model mặc định của provider"},
    "chat.delete_link": {"en": "Delete", "ja": "削除", "vi": "Xóa"},
    "chat.delete_tooltip": {
        "en": "Delete this message and its input/output files",
        "ja": "このメッセージと入出力ファイルを削除",
        "vi": "Xóa tin nhắn này và các tệp input/output của nó"},
    "chat.open_workspace": {"en": "Open workspace", "ja": "作業フォルダを開く", "vi": "Mở thư mục làm việc"},
    "chat.open_folder": {"en": "Open folder", "ja": "フォルダを開く", "vi": "Mở thư mục"},
    "chat.open_output_folder": {"en": "Open output folder", "ja": "出力フォルダを開く", "vi": "Mở thư mục output"},
    "chat.done_marker": {"en": "Done", "ja": "完了しました", "vi": "Đã hoàn thành"},
    "chat.session_folder_marker": {
        "en": "This conversation's output folder", "ja": "この会話の出力フォルダ",
        "vi": "Thư mục output của hội thoại này"},
    "chat.open_folder_short": {"en": "Open folder", "ja": "フォルダを開く", "vi": "Mở thư mục"},
    "chat.diff_before": {"en": "Before", "ja": "編集前", "vi": "Trước khi sửa"},
    "chat.diff_after": {"en": "After", "ja": "編集後", "vi": "Sau khi sửa"},
    "chat.diff_added": {"en": "Added", "ja": "追加", "vi": "Thêm mới"},
    "chat.diff_removed": {"en": "Removed", "ja": "削除", "vi": "Đã xóa"},
    "chat.attachment_warning_title": {
        "en": "Attachment", "ja": "添付ファイル", "vi": "Tệp đính kèm"},
    "chat.attachment_failed": {
        "en": "Could not read \"{name}\": {note}",
        "ja": "「{name}」を読み込めませんでした: {note}",
        "vi": "Không đọc được nội dung \"{name}\": {note}"},
    "chat.reading_progress": {
        "en": "Reading {name} — page {page}/{total}…",
        "ja": "{name} を読み込み中 — {page}/{total} ページ…",
        "vi": "Đang đọc {name} — trang {page}/{total}…"},
    "chat.workspace_files_capped": {
        "en": "Folder has more files than the per-message limit — loaded {shown}/{total} (raise it in Settings → Attachments)",
        "ja": "フォルダ内のファイル数が1メッセージあたりの上限を超えています — {shown}/{total} 件を読み込みました（ 設定 → 添付ファイルで変更可）",
        "vi": "Thư mục có nhiều file hơn giới hạn mỗi tin nhắn — đã đọc {shown}/{total} file (đổi trong Settings → Attachments)"},

    # ---- chat_panel.py (shared by Cowork & Code) ----------------------
    "chatpanel.agent_label": {"en": "Agent:", "ja": "エージェント:", "vi": "Agent:"},
    # ---- Auto Model Assessment & Routing (core/routing/) -----------------
    "routing.toggle_label": {"en": "Routing:", "ja": "ルーティング:", "vi": "Định tuyến:"},
    "routing.autorun_label": {"en": "Auto-run", "ja": "自動実行", "vi": "Tự chạy"},
    "routing.autorun_tooltip": {
        "en": "Auto-approve commands in THIS workspace (no confirm dialog).\nUnchecked: ask before each command. Each workspace keeps its own setting.",
        "ja": "このワークスペースでコマンドを自動承認（確認なし）。\nオフ: 実行前に確認。ワークスペースごとに設定を保持します。",
        "vi": "Tự động duyệt lệnh trong workspace NÀY (không hỏi xác nhận).\nBỏ chọn: hỏi trước mỗi lệnh. Mỗi workspace giữ thiết lập riêng.",
    },
    "routing.mode_off": {"en": "Off", "ja": "オフ", "vi": "Tắt"},
    "routing.mode_auto": {"en": "Auto", "ja": "自動", "vi": "Tự động"},
    "routing.mode_manual": {"en": "Manual", "ja": "手動", "vi": "Thủ công"},
    # Fallback (R03-T03): resilience mode -- never switches for a better
    # score, only to rescue a selected model that cannot serve the turn.
    "routing.mode_fallback": {"en": "Fallback", "ja": "フォールバック", "vi": "Dự phòng"},
    "routing.toggle_tooltip": {
        "en": "Auto model routing for this chat.\nOff: always use the selected model.\nAuto: silently switch to the best-fit model.\nManual: ask before switching.\nFallback: keep the selected model, switch only if it is unavailable.",
        "ja": "このチャットの自動モデルルーティング。\nオフ: 選択したモデルを常に使用。\n自動: 最適なモデルへ自動切替。\n手動: 切替前に確認。\nフォールバック: 選択モデルを維持し、利用できない場合のみ切替。",
        "vi": "Tự động định tuyến model cho khung chat này.\nTắt: luôn dùng model đã chọn.\nTự động: tự chuyển sang model phù hợp nhất.\nThủ công: hỏi xác nhận trước khi chuyển.\nDự phòng: giữ model đã chọn, chỉ chuyển khi model đó không dùng được.",
    },
    "routing.confirm_title": {
        "en": "Switch model?", "ja": "モデルを切り替えますか？", "vi": "Chuyển model?",
    },
    "routing.confirm_body": {
        "en": "A better-fit model was found for this {task} task:\n\n{from_model}  →  {to_model}\n(fit gain +{gain})\n\n{reason}\n\nSwitch to it for this message?",
        "ja": "この {task} タスクにより適したモデルが見つかりました:\n\n{from_model}  →  {to_model}\n(適合度 +{gain})\n\n{reason}\n\nこのメッセージで切り替えますか？",
        "vi": "Đã tìm thấy model phù hợp hơn cho tác vụ {task} này:\n\n{from_model}  →  {to_model}\n(điểm phù hợp +{gain})\n\n{reason}\n\nChuyển sang model đó cho tin nhắn này?",
    },
    "routing.confirm_yes": {"en": "Switch", "ja": "切り替える", "vi": "Chuyển"},
    "routing.confirm_no": {"en": "Keep current", "ja": "現状維持", "vi": "Giữ nguyên"},
    "routing.confirm_countdown": {
        "en": "Keep current ({secs}s)", "ja": "現状維持 ({secs}秒)", "vi": "Giữ nguyên ({secs}s)",
    },
    "routing.switched_notice": {
        "en": "↪ Auto-routed to {model} ({task}, fit +{gain})",
        "ja": "↪ {model} へ自動ルーティング ({task}, 適合度 +{gain})",
        "vi": "↪ Đã tự chuyển sang {model} ({task}, phù hợp +{gain})",
    },
    "routing.reassessing": {
        "en": "Assessing models…", "ja": "モデルを評価中…", "vi": "Đang đánh giá model…",
    },
    "routing.reassess_done": {
        "en": "Model assessment complete: {count} model(s) scored.",
        "ja": "モデル評価完了: {count} 件を採点しました。",
        "vi": "Đánh giá model xong: đã chấm {count} model.",
    },
    # ---- Routing settings group (settings_dialog.py) ---------------------
    "routing.settings_group": {
        "en": "Auto Model Routing", "ja": "自動モデルルーティング", "vi": "Tự động định tuyến Model",
    },
    "routing.settings_mode": {"en": "Default mode", "ja": "既定モード", "vi": "Chế độ mặc định"},
    "routing.settings_policy": {"en": "Policy", "ja": "ポリシー", "vi": "Chính sách"},
    "routing.policy_quality": {"en": "Quality", "ja": "品質", "vi": "Chất lượng"},
    "routing.policy_cost": {"en": "Cost", "ja": "コスト", "vi": "Chi phí"},
    "routing.policy_latency": {"en": "Latency", "ja": "レイテンシ", "vi": "Độ trễ"},
    "routing.policy_balanced": {"en": "Balanced", "ja": "バランス", "vi": "Cân bằng"},
    "routing.settings_min_gain": {
        "en": "Min score gain to switch", "ja": "切替に必要な最小スコア差", "vi": "Chênh điểm tối thiểu để chuyển",
    },
    "routing.settings_timeout": {
        "en": "Confirm timeout (sec)", "ja": "確認タイムアウト (秒)", "vi": "Thời gian chờ xác nhận (giây)",
    },
    "routing.settings_interval": {
        "en": "Reassess every (hours, 0=off)", "ja": "再評価間隔 (時間, 0=無効)", "vi": "Đánh giá lại mỗi (giờ, 0=tắt)",
    },
    "routing.settings_concurrency": {
        "en": "Max probe calls per provider", "ja": "プロバイダーごとの最大プローブ数", "vi": "Số lần probe tối đa mỗi provider",
    },
    "routing.settings_judge": {
        "en": "Judge model (blank = auto)", "ja": "ジャッジモデル (空欄=自動)", "vi": "Model chấm điểm (trống = tự động)",
    },
    "routing.settings_reassess_now": {
        "en": "Reassess now", "ja": "今すぐ再評価", "vi": "Đánh giá lại ngay",
    },
    "routing.settings_hint": {
        "en": "The app benchmarks each model and routes chats to the best-fit one. Probing spends tokens, so it runs on a schedule / when you add a model / when you click Reassess.",
        "ja": "各モデルをベンチマークし、最適なモデルへチャットを振り分けます。プローブはトークンを消費するため、スケジュール・モデル追加時・「再評価」押下時のみ実行されます。",
        "vi": "Ứng dụng benchmark từng model và định tuyến chat tới model phù hợp nhất. Probe tốn token nên chỉ chạy theo lịch / khi thêm model / khi bấm Đánh giá lại.",
    },
    "chatpanel.menu_open": {"en": "Open", "ja": "開く", "vi": "Mở"},
    "chatpanel.menu_ai_edit": {"en": "View & AI edit", "ja": "表示 & AI編集", "vi": "Xem & sửa bằng AI"},
    # ---- file_edit_dialog.py (view file + AI edit) -----------------------
    "fileedit.title": {"en": "View & edit file", "ja": "ファイル表示・編集", "vi": "Xem & sửa file"},
    "fileedit.browse_tooltip": {"en": "Open another file…", "ja": "別のファイルを開く…",
                                "vi": "Mở file khác…"},
    "fileedit.reload_tooltip": {"en": "Reload from disk", "ja": "ディスクから再読み込み",
                                "vi": "Tải lại từ đĩa"},
    "fileedit.pick_hint": {"en": "Open a file to view or edit it.",
                           "ja": "表示・編集するファイルを開いてください。",
                           "vi": "Mở một file để xem hoặc chỉnh sửa."},
    "fileedit.instruction_placeholder": {
        "en": "Tell the AI how to edit this file (e.g. 'fix typos', 'translate to English')…",
        "ja": "このファイルの編集内容をAIに指示（例:「誤字修正」「英語に翻訳」）…",
        "vi": "Nói cho AI cách sửa file này (vd: 'sửa lỗi chính tả', 'dịch sang tiếng Anh')…"},
    "fileedit.ai_btn": {"en": "AI Edit", "ja": "AI編集", "vi": "Sửa bằng AI"},
    "fileedit.save_btn": {"en": "Save", "ja": "保存", "vi": "Lưu"},
    "fileedit.close_btn": {"en": "Close", "ja": "閉じる", "vi": "Đóng"},
    "fileedit.loaded_editable": {"en": "Text file — editable.", "ja": "テキストファイル — 編集可能。",
                                 "vi": "File văn bản — có thể sửa."},
    "fileedit.loaded_readonly": {
        "en": "Binary/large document — extracted text shown, read-only (view & ask only).",
        "ja": "バイナリ/大きい文書 — 抽出テキストを表示（閲覧のみ、編集不可）。",
        "vi": "Tài liệu nhị phân/lớn — hiển thị text trích xuất, chỉ đọc (chỉ xem & hỏi)."},
    "fileedit.not_found": {"en": "File not found: {path}", "ja": "ファイルが見つかりません: {path}",
                           "vi": "Không tìm thấy file: {path}"},
    "fileedit.needs_instruction": {"en": "Enter an edit instruction first.",
                                   "ja": "先に編集指示を入力してください。",
                                   "vi": "Hãy nhập yêu cầu chỉnh sửa trước."},
    "fileedit.ai_working": {"en": "AI is editing…", "ja": "AIが編集中…", "vi": "AI đang chỉnh sửa…"},
    "fileedit.ai_done": {"en": "AI edit applied — review, then Save.",
                         "ja": "AI編集を適用 — 確認して保存してください。",
                         "vi": "Đã áp dụng chỉnh sửa của AI — xem lại rồi Lưu."},
    "fileedit.ai_empty": {"en": "The AI returned no content.", "ja": "AIが内容を返しませんでした。",
                          "vi": "AI không trả về nội dung."},
    "fileedit.ai_failed": {"en": "AI edit failed: {err}", "ja": "AI編集に失敗: {err}",
                           "vi": "Sửa bằng AI thất bại: {err}"},
    "fileedit.saved": {"en": "Saved {path} (original backed up as .bak).",
                       "ja": "{path} を保存（元は .bak にバックアップ）。",
                       "vi": "Đã lưu {path} (bản gốc sao lưu thành .bak)."},
}
