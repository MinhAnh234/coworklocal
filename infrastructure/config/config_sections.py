"""Các nhóm cấu hình đọc thẳng từ dict — tách khỏi ``json_config_repository.py``.

Mỗi thành viên ở đây chỉ làm đúng một việc: đặt tên cho một khoá trong file
cấu hình và nói rõ giá trị mặc định khi khoá đó chưa có. Không có hành vi nào
đáng bàn, nhưng có đến hơn hai mươi cái — để chung với phần có logic thật
(trộn mặc định, kho bí mật, di trú schema, ghi nguyên tử) thì phần ấy bị chìm.

Dùng ``setdefault`` chứ không ``get``: bên gọi sửa thẳng vào dict trả về
(``cfg.routing["switch_mode"] = ...``) rồi mới ``save()``, nên cái trả về phải
là dict THẬT nằm trong ``data``, không phải một bản sao rồi bị vứt đi.

Mixin chứ không phải lớp riêng: 29 file đang gọi ``ctx.config.<tên>`` thẳng,
nên tách thành ``ctx.config.sections.<tên>`` sẽ là đổi API công khai — việc
này chỉ chia file, không chia bề mặt.
"""
from __future__ import annotations

import copy
from typing import Any, Dict


class ConfigSectionsMixin:
    """Phần truy cập nhóm cấu hình của :class:`JsonConfigRepository`.

    Chỉ trông vào hai thứ của lớp chủ: ``self.data`` (dict cấu hình đã trộn
    mặc định) và ``self.save()``. Không tự đứng một mình được — và cũng không
    cần, vì không có ai khác dùng.
    """


    @property
    def code(self) -> Dict[str, Any]:
        """Nhóm ``code``: thiết lập của agent lập trình (thư mục làm việc, model)."""
        return self.data["code"]

    @property
    def teams(self) -> Dict[str, Any]:
        """Nhóm ``teams``: thiết lập tích hợp Microsoft Teams."""
        return self.data["teams"]

    @property
    def history(self) -> Dict[str, Any]:
        """Nhóm ``history``: lưu lịch sử hội thoại (bật/tắt, giới hạn)."""
        return self.data["history"]

    @property
    def codebase_memory(self) -> Dict[str, Any]:
        """Nhóm ``codebase_memory``: bộ nhớ mã nguồn cho agent lập trình."""
        return self.data["codebase_memory"]

    @property
    def cowork(self) -> Dict[str, Any]:
        """Nhóm ``cowork``: thiết lập màn Cowork (thư mục kết quả, model mặc định)."""
        return self.data["cowork"]

    @property
    def mcp_servers(self) -> list:
        """Danh sách máy chủ MCP đã khai báo; rỗng nếu chưa có cái nào."""
        return self.data.setdefault("mcp_servers", [])

    @property
    def structure(self) -> Dict[str, Any]:
        """Nhóm ``structure``: trần số node/cạnh khi vẽ đồ thị GraphRAG.

        Mặc định 400/400 — vượt ngưỡng đó thì đồ thị vừa vẽ chậm vừa rối, không
        còn đọc được nữa.
        """
        return self.data.setdefault("structure", {"max_nodes": 400, "max_edges": 400})

    @property
    def monitoring_visibility(self) -> Dict[str, bool]:
        """Nhóm ``monitoring_visibility``: tab nào của màn Giám sát được hiện.

        Lấy bản sao sâu của mặc định khi khoá chưa có, để người dùng tắt một tab
        không vô tình sửa luôn bộ mặc định dùng chung.
        """
        return self.data.setdefault(
            "monitoring_visibility",
            copy.deepcopy(self._defaults["monitoring_visibility"]))

    @property
    def ext_connectors(self) -> Dict[str, list]:
        """Connector (MCP) gom theo nhóm CAD/CAE/MS365/Other."""
        d = self.data.setdefault(
            "ext_connectors", {"cad": [], "cae": [], "ms365": [], "other": []})
        for cat in ("cad", "cae", "ms365", "other"):
            d.setdefault(cat, [])
        return d

    # ---- công tắc tổng cho connector -------------------------------------

    @property
    def connect_external(self) -> bool:
        """Tắt cái này là agent không nối tới connector ngoài nào cả. Mặc định
        BẬT để cấu hình đang chạy không đổi hành vi."""
        return bool(self.data.setdefault("tools", {}).get("connect_external", True))

    def set_connect_external(self, enabled: bool) -> None:
        """Bật/tắt công tắc tổng cho connector ngoài, ghi đĩa ngay."""
        self.data.setdefault("tools", {})["connect_external"] = bool(enabled)
        self.save()

    # ---- những thứ đã gieo sẵn -------------------------------------------

    @property
    def seeded_library_skills(self) -> list:
        """Slug của skill thư viện đã gieo — để cái người dùng xoá đi không bị
        lặng lẽ gieo lại."""
        return list(self.data.setdefault("seeded_library_skills", []))

    @seeded_library_skills.setter
    def seeded_library_skills(self, slugs) -> None:
        """Ghi lại danh sách slug đã gieo, bỏ trùng và giữ nguyên thứ tự."""
        self.data["seeded_library_skills"] = list(dict.fromkeys(slugs or []))

    @property
    def seeded_builtin_flows(self) -> list:
        """Id của flow Co4E dựng sẵn đã gieo (cùng quy tắc tôn trọng việc người
        dùng đã xoá như seeded_library_skills)."""
        return list(self.data.setdefault("seeded_builtin_flows", []))

    @seeded_builtin_flows.setter
    def seeded_builtin_flows(self, ids) -> None:
        """Ghi lại danh sách id flow đã gieo, bỏ trùng và giữ nguyên thứ tự."""
        self.data["seeded_builtin_flows"] = list(dict.fromkeys(ids or []))


__all__ = ["ConfigSectionsMixin"]
