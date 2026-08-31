"""Panel khu vực AGENTS của sidebar Co4E — tách khỏi ``ui/co4e_tab.py``.

Vấn đề đang có: giống ``SkillsListPanel`` (xem
``presentation/co4e/skills_list_panel.py``), đoạn dựng widget khu vực AGENTS
nằm nguyên trong thân hàm dựng cả cột sidebar của ``ui/co4e_tab.py`` (nguyên
bản ở dòng 549-568): nút "+ Mới", danh sách kéo-thả và 2 nút icon Sửa/Xoá.
Đoạn này không đọc/ghi bất kỳ trạng thái nào của ``Co4ETab`` khi DỰNG (chỉ khi
người dùng bấm nút mới cần tới ``_new_agent``/``_edit_agent``/``_delete_agent``
của ``Co4ETab``), nên tách được thành một ``QWidget`` con độc lập.

Cách làm: dời nguyên phần dựng widget sang đây, KHÔNG đổi tên thuộc tính so
với bản gốc ngoại trừ đổi TÊN THUỘC TÍNH cho khớp quy ước panel công khai
(``ag_new_btn`` → ``new_btn``, ``agent_list`` → ``list_widget``,
``ag_edit_btn`` → ``edit_btn``, ``ag_del_btn`` → ``del_btn``); giá trị/thứ tự
dựng thì giữ y hệt. Panel KHÔNG tự nối ``.clicked`` của bất kỳ nút nào — theo
đúng nguyên tắc "một việc rẽ ra một lần" đã dùng cho ``SkillsListPanel``: việc
dựng widget (ở đây) tách khỏi việc nối hành vi (vẫn ở ``Co4ETab``, nơi biết
``_new_agent``/``_edit_agent``/``_delete_agent`` là gì). Gộp hai việc đó vào
panel sẽ buộc panel phải biết về ``Co4ETab``, xoá mất lý do tách nó ra.

``new_btn`` được tạo nhưng KHÔNG add vào layout của panel này — giống hệt
``wf_new_btn``/``sk_manage_btn`` ở bản gốc: nút này được ``Co4ETab`` truyền
riêng làm "action" của tiêu đề section (tham số ``action`` của ``_section``),
không nằm trong phần thân (list + nút icon) mà panel này đóng vai trò thay
thế. Panel do đó chỉ tự dựng layout cho list_widget + hàng nút edit/del.

Cập nhật 25/08: ``_PaletteList`` đã dời khỏi ``ui/co4e_tab.py`` sang
``presentation/co4e/palette_list.py`` (module dùng chung, không phụ thuộc
``ui/``) — import thẳng ở top-level như bên dưới, không còn cần deferred-import
né vòng lặp nữa (xem docstring đầu ``presentation/co4e/palette_list.py`` để
biết lý do dời).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ...i18n import tr
from ...ui.icons import icon
from .palette_list import _PaletteList


class AgentListPanel(QWidget):
    """Widget khu vực AGENTS của sidebar Co4E: nút mới + danh sách + sửa/xoá.

    Vai trò: một widget con thuần ở tầng presentation, chỉ dựng cấu trúc UI
    (đúng những gì ``ui/co4e_tab.py`` dòng 549-568 làm trước đây), không biết
    gì về ``Co4ETab``/``_new_agent``/``_edit_agent``/``_delete_agent``. Bên
    gọi (hiện là ``Co4ETab``) tự đọc ``.new_btn``/``.list_widget``/
    ``.edit_btn``/``.del_btn`` để nối signal và nạp dữ liệu — panel không tự
    làm hộ, để giữ đúng ranh giới "một nơi một việc" đã dùng cho
    ``SkillsListPanel``.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Danh sách agent ở cột trái Co4E Studio, kèm nút tạo mới."""
        super().__init__(parent)
        self.new_btn = QPushButton(tr("co4e.new"))
        self.new_btn.setIcon(icon("plus"))
        self.new_btn.setToolTip(tr("co4e.tt_new_agent"))
        self.new_btn.setObjectName("co4eSectionAction")
        self.new_btn.setFlat(True)
        self.new_btn.setCursor(Qt.PointingHandCursor)
        # KHONG noi .clicked o day: ben goi (Co4ETab) tu quyet dinh slot nao
        # xu ly - panel chi dung widget, khong biet _new_agent la gi.

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.list_widget = _PaletteList()
        layout.addWidget(self.list_widget, 1)

        btns = QHBoxLayout()
        btns.setSpacing(4)
        # Edit/delete act on the selected row, so they stay with the list.
        self.edit_btn = QPushButton()
        self.edit_btn.setIcon(icon("edit"))
        self.edit_btn.setToolTip(tr("co4e.tt_edit_agent"))
        self.edit_btn.setFixedWidth(34)
        self.del_btn = QPushButton()
        self.del_btn.setIcon(icon("trash"))
        self.del_btn.setToolTip(tr("co4e.tt_del_agent"))
        self.del_btn.setFixedWidth(34)
        # KHONG noi .clicked o day: cung ly do nhu new_btn o tren.
        btns.addWidget(self.edit_btn)
        btns.addWidget(self.del_btn)
        btns.addStretch(1)
        layout.addLayout(btns)
