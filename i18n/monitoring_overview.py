"""Chuỗi hiển thị — phần monitoring_overview.

Cắt ra từ ``i18n.py``: một dict 3.000 dòng không mở nổi để sửa một chữ.
Cắt theo mốc phân đoạn có sẵn, nên mỗi cụm vẫn là các màn đi liền nhau.
``i18n.py`` gộp tất cả lại thành ``STRINGS``.
"""
from __future__ import annotations

from typing import Dict

STRINGS: Dict[str, Dict[str, str]] = {
    "monitoring.overview_sandbox_id": {"en": "Sandbox ID", "ja": "サンドボックス ID", "vi": "Sandbox ID"},
    "monitoring.overview_status": {"en": "Status", "ja": "状態", "vi": "Trạng thái"},
    "monitoring.overview_status_running": {"en": "Running", "ja": "実行中", "vi": "Đang chạy"},
    "monitoring.overview_created": {"en": "Created", "ja": "作成日時", "vi": "Tạo lúc"},
    "monitoring.overview_uptime": {"en": "Uptime", "ja": "稼働時間", "vi": "Thời gian hoạt động"},
    "monitoring.overview_resource_limits": {
        "en": "Resource Limits", "ja": "リソース制限", "vi": "Giới hạn tài nguyên"},
    "monitoring.overview_edit": {"en": "Edit", "ja": "編集", "vi": "Sửa"},
    "monitoring.overview_network_label": {"en": "Network", "ja": "ネットワーク", "vi": "Mạng"},
    "monitoring.overview_network_disabled": {"en": "Disabled", "ja": "無効", "vi": "Đã tắt"},
    "monitoring.overview_network_enabled": {"en": "Enabled", "ja": "有効", "vi": "Đang mở"},
    "monitoring.overview_permissions_title": {"en": "Permissions", "ja": "権限", "vi": "Quyền"},
    "monitoring.overview_perm_fs": {"en": "File System", "ja": "ファイルシステム", "vi": "Hệ thống file"},
    "monitoring.overview_perm_fs_value": {"en": "Read/Write", "ja": "読み書き", "vi": "Đọc/Ghi"},
    "monitoring.overview_perm_network": {"en": "Network", "ja": "ネットワーク", "vi": "Mạng"},
    "monitoring.overview_perm_network_blocked": {"en": "Blocked", "ja": "ブロック", "vi": "Bị chặn"},
    "monitoring.overview_perm_network_allowed": {"en": "Allowed", "ja": "許可", "vi": "Cho phép"},
    "monitoring.overview_perm_process": {"en": "Process", "ja": "プロセス", "vi": "Tiến trình"},
    "monitoring.overview_perm_process_value": {"en": "Limited", "ja": "制限あり", "vi": "Bị hạn chế"},
    "monitoring.overview_perm_env": {"en": "Environment", "ja": "実行環境", "vi": "Môi trường"},
    "monitoring.overview_perm_env_value": {"en": "Restricted", "ja": "制限あり", "vi": "Bị giới hạn"},
    "monitoring.overview_audit_title": {"en": "Audit Log", "ja": "監査ログ", "vi": "Audit Log"},
    "monitoring.overview_view_all": {"en": "View all", "ja": "すべて表示", "vi": "Xem tất cả"},
    "monitoring.time_just_now": {"en": "just now", "ja": "たった今", "vi": "vừa xong"},
    "monitoring.time_minutes_ago": {"en": "{n}m ago", "ja": "{n}分前", "vi": "{n} phút trước"},
    "monitoring.time_hours_ago": {"en": "{n}h ago", "ja": "{n}時間前", "vi": "{n} giờ trước"},
    "monitoring.time_days_ago": {"en": "{n}d ago", "ja": "{n}日前", "vi": "{n} ngày trước"},
    "monitoring.na": {"en": "—", "ja": "—", "vi": "—"},
}
