"""Panel khu vực SKILLS của sidebar Co4E — tách khỏi ``ui/co4e_tab.py``.

Vấn đề đang có: ``ui/co4e_tab.py`` đang gộp việc dựng widget (nút "Quản lý
skill" + danh sách kéo-thả) ngay bên trong thân hàm dựng cả cột sidebar,
khiến file đó (2000+ dòng) khó đọc và khó giữ dưới giới hạn CASAN (≤400 dòng
mỗi file production). Đoạn dựng widget khu vực SKILLS (nguyên bản ở
``ui/co4e_tab.py`` dòng 569-580) không phụ thuộc phần còn lại của
``Co4ETab`` — nó chỉ tạo ``QPushButton`` + ``_PaletteList`` + layout bọc — nên
tách được thành một ``QWidget`` con độc lập.

Cách làm: dời nguyên phần dựng widget sang đây, KHÔNG đổi tên thuộc tính so
với bản gốc (``sk_manage_btn`` → ``manage_btn``, ``skill_list`` →
``list_widget``, chỉ đổi TÊN THUỘC TÍNH cho khớp quy ước panel công khai, còn
giá trị/thứ tự dựng/không dựng gì thêm thì giữ y hệt). Panel KHÔNG tự nối
``.clicked`` của ``manage_btn`` và KHÔNG tự gọi ``_reload_sidebar`` — theo
đúng nguyên tắc "một việc rẽ ra một lần": việc dựng widget (ở đây) tách khỏi
việc nối hành vi (vẫn ở ``Co4ETab``, nơi biết ``_manage_skills`` là gì). Gộp
hai việc đó vào panel sẽ buộc panel phải biết về ``Co4ETab``, xoá mất lý do
tách nó ra.

Cập nhật 25/08: ``_PaletteList`` đã dời khỏi ``ui/co4e_tab.py`` sang
``presentation/co4e/palette_list.py`` (module dùng chung, không phụ thuộc
``ui/``) — import thẳng ở top-level như bên dưới, không còn cần deferred-import
né vòng lặp nữa (xem docstring đầu ``presentation/co4e/palette_list.py`` để
biết lý do dời).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from ...i18n import bind_text, bind_tip
from .palette_list import _PaletteList


class SkillsListPanel(QWidget):
    """Widget khu vực SKILLS của sidebar Co4E: nút quản lý + danh sách kéo-thả.

    Vai trò: một widget con thuần ở tầng presentation, chỉ dựng cấu trúc UI
    (đúng những gì ``ui/co4e_tab.py`` dòng 569-580 làm trước đây), không biết
    gì về ``Co4ETab``/``_manage_skills``/``_reload_sidebar``. Bên gọi (hiện là
    ``Co4ETab``) tự đọc ``.manage_btn``/``.list_widget`` để nối signal và nạp
    dữ liệu — panel không tự làm hộ, để giữ đúng ranh giới "một nơi một việc".
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Danh sách skill ở cột trái Co4E Studio, kèm nút quản lý.

        Không nối ``clicked`` ở đây: bên gọi (``Co4ETab``) tự quyết định nút ấy mở
        cái gì.
        """
        super().__init__(parent)
        # Bound, like AgentListPanel's: the panel owns how its own button reads,
        # so no embedder has to remember it in a retranslate method.
        self.manage_btn = bind_text(QPushButton(), "co4e.manage_skills")
        bind_tip(self.manage_btn, "co4e.tt_manage_skills")
        self.manage_btn.setObjectName("co4eSectionAction")
        self.manage_btn.setFlat(True)
        self.manage_btn.setCursor(Qt.PointingHandCursor)
        # KHONG noi .clicked o day: ben goi (Co4ETab) tu quyet dinh slot nao
        # xu ly - panel chi dung widget, khong biet _manage_skills la gi.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.list_widget = _PaletteList()
        layout.addWidget(self.list_widget, 1)
