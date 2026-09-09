"""Nhãn cho các nút CHUẨN của Qt (Save/Cancel/OK/Close, Yes/No).

Qt tự vẽ chữ cho những nút này từ bảng dịch của chính nó, mà ứng dụng không
cài ``QTranslator`` nào — nên chúng đứng nguyên tiếng Anh ở cả ba ngôn ngữ.
``ui/dialog_buttons.py`` gán lại nhãn bằng các khoá dưới đây.

Khoá dùng chung cho mọi hộp thoại nên đứng riêng một file, không nhét vào file
của một màn hình cụ thể.
"""
from __future__ import annotations

from typing import Dict

STRINGS: Dict[str, Dict[str, str]] = {
    "dialog.save": {"en": "Save", "ja": "保存", "vi": "Lưu"},
    "dialog.cancel": {"en": "Cancel", "ja": "キャンセル", "vi": "Hủy"},
    # "OK" giữ nguyên dạng ở cả ba ngôn ngữ — kể cả bản tiếng Nhật của Qt cũng
    # dùng "OK". Đã khai vào KHOA_KHONG_CAN_DICH của test i18n.
    "dialog.ok": {"en": "OK", "ja": "OK", "vi": "OK"},
    "dialog.close": {"en": "Close", "ja": "閉じる", "vi": "Đóng"},
    "dialog.yes": {"en": "Yes", "ja": "はい", "vi": "Có"},
    "dialog.no": {"en": "No", "ja": "いいえ", "vi": "Không"},
}
