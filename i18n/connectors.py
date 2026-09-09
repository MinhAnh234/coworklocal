"""Chuỗi hiển thị — nhóm Connector (Giám sát ▸ Công cụ ▸ Connector).

Tên bốn nhóm catalog trên bảng Connector. Đứng riêng một file vì
``libreoffice_view.py`` — nơi giữ các khoá ``connectors.*`` cũ — đã sát trần
400 dòng của Gate S; khoá connector thêm mới đi vào đây.

Ba nhóm CAD / CAE / MS365 là DANH SÁCH TÊN SẢN PHẨM nên giống hệt nhau ở cả ba
ngôn ngữ (đã khai vào ``KHOA_KHONG_CAN_DICH`` của test i18n). Chỉ nhóm "Other"
có chữ thật để dịch — đúng chỗ người dùng báo còn nguyên tiếng Anh.

``ui/connectors_panel.py`` tách nhãn tại chuỗi ``" ("`` để in phần trong ngoặc
bằng kiểu chữ phụ, nên bản dịch phải dùng ngoặc ĐƠN NỬA CHIỀU RỘNG kèm một dấu
cách phía trước — dùng ngoặc full-width ``（`` của tiếng Nhật thì không tách
được và cả cụm sẽ in đậm thành một khối.
"""
from __future__ import annotations

from typing import Dict

_CAD = "CAD (NX / CATIA / SolidWorks / AutoCAD)"
_CAE = "CAE (ANSA / ABAQUS / HyperWorks / ANSYS)"
_MS365 = "MS365 (Microsoft 365 / OneDrive / SharePoint)"

STRINGS: Dict[str, Dict[str, str]] = {
    "connectors.cat_cad": {"en": _CAD, "ja": _CAD, "vi": _CAD},
    "connectors.cat_cae": {"en": _CAE, "ja": _CAE, "vi": _CAE},
    "connectors.cat_ms365": {"en": _MS365, "ja": _MS365, "vi": _MS365},
    "connectors.cat_other": {
        "en": "Other (any generic MCP server)",
        "ja": "その他 (任意の汎用 MCP サーバー)",
        "vi": "Khác (MCP server bất kỳ)"},
}
