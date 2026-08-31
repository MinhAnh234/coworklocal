"""Panel trang "Runs" (danh sách các lần chạy flow) của Co4E — tách khỏi
``ui/co4e_tab.py``.

Vấn đề đang có: giống ``AgentListPanel``/``SkillsListPanel`` (xem
``presentation/co4e/agent_list_panel.py``/``presentation/co4e/skills_list_panel.py``),
đoạn dựng widget trang "Runs" (nguyên bản ở ``ui/co4e_tab.py``, method
``_build_runs_page``, dòng 869-928) nằm nguyên trong thân một method của
``Co4ETab``. Đoạn này chỉ tạo ``QWidget``/``QPushButton``/``QLabel``/
``QTableWidget`` + layout bọc — không đọc/ghi trạng thái nào của ``Co4ETab``
khi DỰNG (chỉ khi người dùng bấm nút mới cần tới
``_show_runs``/``_open_workspace_folder``/``_stop_selected_run``/... của
``Co4ETab``) — nên tách được thành một ``QWidget`` con độc lập.

Cách làm: dời nguyên phần dựng widget sang đây, KHÔNG đổi tên thuộc tính so
với bản gốc ngoại trừ đổi TÊN THUỘC TÍNH cho khớp quy ước panel công khai
(``runs_back_btn`` → ``back_btn``, ``runs_title`` → ``title_label``,
``run_stop_btn`` → ``stop_btn``, ``run_rename_btn`` → ``rename_btn``,
``run_del_btn`` → ``del_btn``, ``run_clear_btn`` → ``clear_btn``,
``runs_table`` → ``table``); riêng ``ws_folder_btn`` GIỮ NGUYÊN TÊN vì
``ui/co4e_tab.py`` (dòng ~1669) còn chỗ kiểm ``hasattr(self, "ws_folder_btn")``
— đổi tên sẽ làm nhánh đó không còn nhận ra thuộc tính này. Giá trị/thứ tự
dựng widget giữ y hệt bản gốc.

Panel KHÔNG tự nối bất kỳ signal nào (``.clicked``/``.itemDoubleClicked``/
``.customContextMenuRequested``) và KHÔNG tự gọi ``_refresh_ws_folder_btn()``
— theo đúng nguyên tắc "một việc rẽ ra một lần" đã dùng cho
``AgentListPanel``/``SkillsListPanel``: việc dựng widget (ở đây) tách khỏi
việc nối hành vi (vẫn ở ``Co4ETab``, nơi biết ``_stop_selected_run``/
``_rename_selected_run``/``_delete_selected_run``/``_open_run_from_table``/
``_open_workspace_folder``/``_runs_context_menu``/``_refresh_ws_folder_btn``
là gì). Gộp hai việc đó vào panel sẽ buộc panel phải biết về ``Co4ETab``, xoá
mất lý do tách nó ra.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget, QVBoxLayout,
    QWidget,
)

from ...i18n import tr
from ...ui.icons import icon


class RunsPagePanel(QWidget):
    """Widget trang "Runs" của Co4E: thanh tiêu đề + hàng nút thao tác + bảng.

    Vai trò: một widget con thuần ở tầng presentation, chỉ dựng cấu trúc UI
    (đúng những gì ``ui/co4e_tab.py`` dòng 869-928 làm trước đây), không biết
    gì về ``Co4ETab``/``_show_runs``/``_stop_selected_run``/... Bên gọi (hiện
    là ``Co4ETab``) tự đọc 8 thuộc tính công khai dưới đây để nối signal, gọi
    ``_refresh_ws_folder_btn()`` và nạp dữ liệu — panel không tự làm hộ, để
    giữ đúng ranh giới "một nơi một việc" đã dùng cho ``AgentListPanel``/
    ``SkillsListPanel``.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Trang danh sách lượt chạy.

        Tự mang nút quay lại vì trang này phủ kín thanh công cụ — nút đã mở nó ra
        nằm ngoài màn hình.
        """
        super().__init__(parent)
        v = QVBoxLayout(self)
        hdr = QHBoxLayout()
        # The Runs page covers the flow toolbar, so it carries its own way back —
        # otherwise the toggle that opened it is off screen.
        self.back_btn = QPushButton(tr("co4e.back_to_flow"))
        self.back_btn.setIcon(icon("chevron-left"))
        self.back_btn.setToolTip(tr("co4e.tt_back_to_flow"))
        # KHONG noi .clicked o day: ben goi (Co4ETab) tu quyet dinh slot nao
        # xu ly - panel chi dung widget, khong biet _show_runs la gi.
        hdr.addWidget(self.back_btn)
        self.title_label = QLabel(tr("co4e.running_flows"))
        self.title_label.setObjectName("hint")
        hdr.addWidget(self.title_label)
        # Show + open the workspace folder where flow outputs land (below the tab,
        # next to the title) so the files a flow produced are easy to find.
        self.ws_folder_btn = QPushButton()
        self.ws_folder_btn.setIcon(icon("folder"))
        self.ws_folder_btn.setFlat(True)
        self.ws_folder_btn.setCursor(Qt.PointingHandCursor)
        # KHONG noi .clicked va KHONG tu goi _refresh_ws_folder_btn() o day:
        # ca hai deu thuoc Co4ETab (can ctx/manager de biet duong dan that).
        hdr.addWidget(self.ws_folder_btn)
        hdr.addStretch(1)
        self.stop_btn = QPushButton(tr("co4e.stop"))
        self.stop_btn.setIcon(icon("stop"))
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setToolTip(tr("co4e.tt_stop_run"))
        # KHONG noi .clicked o day: cung ly do nhu back_btn o tren.
        self.rename_btn = QPushButton(tr("co4e.rename_run"))
        self.rename_btn.setIcon(icon("edit"))
        self.rename_btn.setToolTip(tr("co4e.tt_rename_run"))
        # KHONG noi .clicked o day: cung ly do nhu back_btn o tren.
        self.del_btn = QPushButton(tr("co4e.delete_run"))
        self.del_btn.setIcon(icon("trash"))
        self.del_btn.setToolTip(tr("co4e.tt_delete_run"))
        # KHONG noi .clicked o day: cung ly do nhu back_btn o tren.
        self.clear_btn = QPushButton(tr("co4e.clear_done"))
        self.clear_btn.setToolTip(tr("co4e.tt_clear_runs"))
        # KHONG noi .clicked o day: cung ly do nhu back_btn o tren. (Ban goc
        # noi thang toi lambda: self.manager.clear_finished(), khong qua mot
        # method rieng - Co4ETab van giu dung quirk do khi noi lai signal nay.)
        hdr.addWidget(self.stop_btn)
        hdr.addWidget(self.rename_btn)
        hdr.addWidget(self.del_btn)
        hdr.addWidget(self.clear_btn)
        v.addLayout(hdr)
        self.table = QTableWidget(0, 5)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setToolTip(tr("co4e.tt_runs_list"))
        # KHONG noi .itemDoubleClicked o day: cung ly do nhu back_btn o tren.
        # Right-click a run → Open / Delete (delete a single old run from history).
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        # KHONG noi .customContextMenuRequested o day: cung ly do nhu tren.
        v.addWidget(self.table, 1)
