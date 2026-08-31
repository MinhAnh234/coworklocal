"""``_PaletteList`` — danh sách kéo-thả dùng chung của sidebar Co4E, tách khỏi
``ui/co4e_tab.py``.

Vấn đề đang có: lớp này (nguyên bản ở ``ui/co4e_tab.py``) được 3 nơi dùng —
``Co4ETab`` tự dùng cho ``wf_list`` (Workflows), còn
``presentation/co4e/agent_list_panel.py``/``presentation/co4e/skills_list_panel.py``
phải IMPORT NGƯỢC nó từ ``ui/co4e_tab.py`` bằng deferred-import bên trong
``__init__`` (để né vòng lặp import: ``ui/co4e_tab.py`` import 2 panel đó ở
đầu file, trong khi lớp ``_PaletteList`` lại định nghĩa Ở NGAY TRONG file đó).
Hướng phụ thuộc "presentation -> ui" đó ngược với ý đồ của cả đợt tách này
(``ui/co4e_tab.py`` đang co lại, ``presentation/co4e/`` là tầng con của nó, không
phải ngược lại) — Lâm (N3) quyết 25/08: tách hẳn ``_PaletteList`` sang module
RIÊNG, không thuộc ``ui/`` lẫn phụ thuộc vào ``ui/co4e_tab.py``, để 2 panel kia
import thẳng ở top-level như bình thường, không cần deferred-import nữa.

Không đổi tên/hành vi — dời NGUYÊN VĂN. ``ui/co4e_tab.py`` giữ khả năng
``from .co4e_tab import _PaletteList`` (qua re-export ở đầu file, giống khuôn
đã dùng cho ``_skill_names``/``_ChatInput``) vì
``tests/characterization/test_co4e_skills_panel.py`` import thẳng tên này từ
``cowork_local.ui.co4e_tab``.
"""
from __future__ import annotations

import json

from PySide6.QtCore import QMimeData, Qt
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QListWidget

from .co4e_canvas_widget import CO4E_MIME


class _PaletteList(QListWidget):
    """A list whose rows can be dragged onto the canvas. Each item carries a
    JSON-able drag payload (a step dict, or a workflow dict) in ``payload_role``.
    Workflow rows also keep a (kind, id) tuple in Qt.UserRole for load/delete."""

    def __init__(self, parent=None, payload_role=Qt.UserRole):
        """Danh sách nguyên liệu chỉ để kéo ra khung vẽ — không nhận thả vào."""
        super().__init__(parent)
        self._payload_role = payload_role
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.DragOnly)

    def startDrag(self, _actions):  # noqa: N802
        """Bắt đầu kéo: gói dữ liệu của mục đang chọn vào MIME riêng của Co4E, để khung
        vẽ nhận ra và dựng đúng loại node.
        """
        item = self.currentItem()
        if item is None:
            return
        payload = item.data(self._payload_role)
        if not payload:
            return
        md = QMimeData()
        md.setData(CO4E_MIME, json.dumps(payload).encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(md)
        drag.exec(Qt.CopyAction)
