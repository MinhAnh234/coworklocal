"""DF-007 — Microsoft 365 sign-in dialog + cloud (OneDrive/SharePoint)
folder picker. Deliberately its own module rather than reusing the
similarly-named orphaned keys under ``settings.ms365_*`` in ``cowork_tab.py``/
``settings_dialog.py`` — those are leftovers from a MS365 sign-in UI that was
removed (see ``ui/settings_dialog.py`` module docstring) and the two files
disagree with each other on wording for several duplicate keys, so reusing
them risked resurrecting an inconsistency rather than a clean, tested string
set."""
from __future__ import annotations

STRINGS = {
    # ---- ui/ms365_signin_dialog.py ----
    "ms365_signin.title": {
        "en": "Sign in to Microsoft 365", "ja": "Microsoft 365 にサインイン",
        "vi": "Đăng nhập Microsoft 365",
    },
    "ms365_signin.already": {
        "en": "Signed in as {who}.", "ja": "{who} としてサインイン済みです。",
        "vi": "Đã đăng nhập với {who}.",
    },
    "ms365_signin.intro": {
        "en": "Sign in with your Microsoft work/school (or personal) account to "
              "browse OneDrive/SharePoint folders.",
        "ja": "OneDrive/SharePoint のフォルダーを参照するには、Microsoft の職場/学校\n"
              "(または個人) アカウントでサインインしてください。",
        "vi": "Đăng nhập bằng tài khoản Microsoft (công ty/trường học hoặc cá nhân) "
              "để duyệt thư mục OneDrive/SharePoint.",
    },
    "ms365_signin.button": {
        "en": "Sign in", "ja": "サインイン", "vi": "Đăng nhập",
    },
    "ms365_signin.signing_in": {
        "en": "Signing in…", "ja": "サインイン中…", "vi": "Đang đăng nhập…",
    },
    "ms365_signin.code_hint": {
        "en": "Open {url} and enter this code:", "ja": "{url} を開いてこのコードを入力してください:",
        "vi": "Mở {url} và nhập mã sau:",
    },
    "ms365_signin.open_link": {
        "en": "Open link", "ja": "リンクを開く", "vi": "Mở link",
    },
    "ms365_signin.failed": {
        "en": "Sign-in failed: {err}", "ja": "サインインに失敗しました: {err}",
        "vi": "Đăng nhập thất bại: {err}",
    },
    "ms365_signin.cancel": {
        "en": "Cancel", "ja": "キャンセル", "vi": "Hủy",
    },
    # ---- ui/cloud_folder_picker_dialog.py ----
    "cloud_picker.title": {
        "en": "Choose a OneDrive/SharePoint folder", "ja": "OneDrive/SharePoint フォルダーを選択",
        "vi": "Chọn thư mục OneDrive/SharePoint",
    },
    "cloud_picker.source_onedrive": {
        "en": "My OneDrive", "ja": "自分の OneDrive", "vi": "OneDrive của tôi",
    },
    "cloud_picker.source_sharepoint": {
        "en": "SharePoint site", "ja": "SharePoint サイト", "vi": "Site SharePoint",
    },
    "cloud_picker.search_sites_placeholder": {
        "en": "Search SharePoint sites…", "ja": "SharePoint サイトを検索…",
        "vi": "Tìm site SharePoint…",
    },
    "cloud_picker.search_btn": {
        "en": "Search", "ja": "検索", "vi": "Tìm",
    },
    "cloud_picker.up": {
        "en": ".. (up)", "ja": ".. (上へ)", "vi": ".. (lùi lại)",
    },
    "cloud_picker.choose_here": {
        "en": "Choose this folder", "ja": "このフォルダーを選択", "vi": "Chọn thư mục này",
    },
    "cloud_picker.cancel": {
        "en": "Cancel", "ja": "キャンセル", "vi": "Hủy",
    },
    "cloud_picker.load_failed": {
        "en": "Could not load this folder: {err}", "ja": "フォルダーを読み込めませんでした: {err}",
        "vi": "Không tải được thư mục này: {err}",
    },
    "cloud_picker.no_sites": {
        "en": "No matching SharePoint sites.", "ja": "一致する SharePoint サイトがありません。",
        "vi": "Không tìm thấy site SharePoint phù hợp.",
    },
    # ---- ui/workspace_tab.py additions ----
    "workspace.cloud_pick": {
        "en": "Choose from OneDrive/SharePoint…", "ja": "OneDrive/SharePoint から選択…",
        "vi": "Chọn từ OneDrive/SharePoint…",
    },
    "workspace.cloud_sync": {
        "en": "Sync with cloud", "ja": "クラウドと同期", "vi": "Đồng bộ với cloud",
    },
    "workspace.cloud_badge_onedrive": {
        "en": "☁ Local mirror of OneDrive: {path}", "ja": "☁ OneDrive のローカルミラー: {path}",
        "vi": "☁ Bản sao cục bộ của OneDrive: {path}",
    },
    "workspace.cloud_badge_sharepoint": {
        "en": "☁ Local mirror of SharePoint ({site}): {path}",
        "ja": "☁ SharePoint ({site}) のローカルミラー: {path}",
        "vi": "☁ Bản sao cục bộ của SharePoint ({site}): {path}",
    },
    "workspace.cloud_sync_result": {
        "en": "Sync done — {up} uploaded, {down} downloaded.",
        "ja": "同期完了 — アップロード {up} 件、ダウンロード {down} 件。",
        "vi": "Đồng bộ xong — {up} tệp đẩy lên, {down} tệp tải về.",
    },
    "workspace.cloud_sync_errors": {
        "en": "{n} item(s) had errors — see details below.",
        "ja": "{n} 件のエラーがありました — 詳細は下記のとおりです。",
        "vi": "{n} mục bị lỗi — chi tiết bên dưới.",
    },
    "workspace.cloud_sync_skipped": {
        "en": "{n} file(s) skipped (over 4 MB, not supported yet).",
        "ja": "{n} 件のファイルはスキップされました (4 MB 超、未対応)。",
        "vi": "{n} tệp bị bỏ qua (quá 4 MB, chưa hỗ trợ).",
    },
}
