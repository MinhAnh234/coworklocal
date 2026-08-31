"""StructureGraphView shell (R08-T14) — assembles
``graph_renderer.py::GraphRenderer`` and
``graph_qa_widget.py::GraphQaWidget`` behind the splitter that used to be
inline in ``ui/structure_graph_view.py::StructureGraphView.__init__`` (lines
188-343 of the original 1035-line file), and forwards the public methods
``app.py``/``ui/workspace_tab.py`` call: ``schedule_rescan``,
``auto_scan_and_fit``, ``set_project``, ``prewarm``.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from cowork_local.i18n import on_language_changed
from cowork_local.presentation.graph.graph_qa_widget import GraphQaWidget
from cowork_local.presentation.graph.graph_renderer import GraphRenderer
from cowork_local.state import AppContext
from cowork_local.ui.widgets import CollapseStrip

_COLLAPSED_SIZES_HINT = (840, 320)   # matches the original single-class default


class StructureGraphView(QWidget):
    """Màn GraphRAG: ghép khung đồ thị (:class:`GraphRenderer`) và khung hỏi-đáp
    (:class:`GraphQaWidget`) vào một splitter.

    Vỏ này chỉ lắp ráp và chuyển tiếp bốn phương thức mà ``app.py`` và
    ``ui/workspace_tab.py`` gọi tới; toàn bộ phần việc thật nằm ở hai widget con.
    """
    status_message = Signal(str)

    def __init__(self, ctx: AppContext):
        """Ghép hai nửa của màn GraphRAG: bên trái là đồ thị, bên phải là panel Hỏi
        đáp.
        """
        super().__init__()
        self.ctx = ctx

        root = QVBoxLayout(self)
        self.renderer = GraphRenderer(ctx)
        self.renderer.status_message.connect(self.status_message.emit)
        self.qa = GraphQaWidget(ctx, self.renderer)
        self.qa.status_message.connect(self.status_message.emit)
        self.qa.collapse_changed.connect(self._on_qa_collapse_changed)

        self._split = QSplitter(Qt.Horizontal)
        self._split.addWidget(self.renderer)
        self._split.addWidget(self.qa)
        self._split.setChildrenCollapsible(False)
        self._split.setSizes(list(_COLLAPSED_SIZES_HINT))
        root.addWidget(self._split, 1)

        on_language_changed(self._retranslate)

    def _retranslate(self) -> None:
        """Chuyển lệnh dịch lại xuống cho cả hai widget con."""
        self.renderer._retranslate()
        self.qa.retranslate()

    def _on_qa_collapse_changed(self, collapsed: bool) -> None:
        """Gập/mở khung hỏi-đáp: gập thì thu về đúng bề rộng dải nắm, mở thì trả
        splitter về tỉ lệ mặc định.
        """
        strip_w = CollapseStrip.WIDTH + 2
        if collapsed:
            self.qa.setMaximumWidth(strip_w)
            sizes = self._split.sizes()
            if len(sizes) == 2:
                self._split.setSizes([max(1, sum(sizes) - strip_w), strip_w])
        else:
            self.qa.setMaximumWidth(16777215)
            self._split.setSizes(list(_COLLAPSED_SIZES_HINT))

    # ---- public API (app.py / ui/workspace_tab.py) --------------------------- #
    def schedule_rescan(self, path: str = "") -> None:
        """Hẹn quét lại đồ thị sau khi thư mục có thay đổi."""
        self.renderer.schedule_rescan(path)

    def auto_scan_and_fit(self) -> None:
        """Vào màn GraphRAG: hiện đồ thị, chỉ quét lại khi thật sự cần."""
        self.renderer.auto_scan_and_fit()

    def set_project(self, project_id: str) -> None:
        """Khoá phạm vi quét vào một project (chuỗi rỗng là bỏ khoá)."""
        self.renderer.set_project(project_id)

    def prewarm(self) -> None:
        """Dựng sẵn khung đồ thị trước khi người dùng bấm vào, để lần mở đầu không giật."""
        self.renderer.prewarm()

    def hideEvent(self, e):  # noqa: N802
        # Leaving the GraphRAG tab → drop the temporary extracted info.
        """Rời màn GraphRAG thì xoá phần trích xuất tạm của khung hỏi-đáp."""
        self.qa.clear_extracts()
        super().hideEvent(e)


__all__ = ["StructureGraphView"]
