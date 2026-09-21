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
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QProgressBar, QSplitter, QVBoxLayout, QWidget,
)

from cowork_local.i18n import on_language_changed, tr
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
        # Project ma man Workspace da ap xuong lan gan nhat. None = chua ap lan
        # nao, de lan goi dau tien khong bi bo qua ke ca khi pid la chuoi rong.
        self._workspace_project = None
        # Thư mục của project đó lúc áp gần nhất. Chốt theo CẢ đường dẫn chứ
        # không chỉ theo id — xem set_workspace_project.
        self._workspace_dir = None

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

        self._build_busy_panel()
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
    # ---- panel "đang tải" ---------------------------------------------------
    def _build_busy_panel(self) -> None:
        """Panel phủ lên khung đồ thị trong lúc nó đang được dựng.

        Vì sao cần: ``prewarm()`` chỉ chạy 3 giây sau khi cửa sổ hiện
        (``main_window.py``), nên người dùng bấm GraphRAG trong 3 giây đầu sẽ
        gặp ``_ensure_web()`` dựng ``QWebEngineView`` ĐỒNG BỘ trên GUI thread —
        đóng băng 1-2 giây mà trước đây không có gì báo.
        """
        self._busy = QWidget(self)
        self._busy.setObjectName("graphBusy")
        lay = QHBoxLayout(self._busy)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(12)
        self._busy_label = QLabel()
        bar = QProgressBar()
        bar.setRange(0, 0)          # chế độ vô định
        bar.setTextVisible(False)
        bar.setFixedWidth(120)
        lay.addWidget(self._busy_label)
        lay.addWidget(bar)
        self._busy.hide()
        self.renderer.graph_rendered.connect(self._hide_busy)
        # Đổi project ngay trên màn này thì renderer quét luôn, không chờ lần ghé
        # sau — nên panel phải bật theo, không thì lượt quét đó lại im lặng.
        self.renderer.project_changed.connect(self._on_project_scan_started)

    def _ensure_scan_path(self) -> None:
        """Điền ô đường dẫn từ project đang hoạt động nếu nó đang rỗng.

        ``GraphRenderer.auto_scan_and_fit`` thoát sớm khi ô đường dẫn rỗng,
        trong khi chính nút Scan lại có đường lùi (``path_edit.text() or
        Path.cwd()``). Bất đối xứng đó nghĩa là: vào màn thì không làm gì, bấm
        Scan thì chạy — đúng thứ người dùng phàn nàn.

        Điền từ project đang chọn chứ KHÔNG lấy ``cwd()`` làm đường lùi như nút
        Scan: quét thư mục làm việc của tiến trình là quét một cây không liên
        quan gì tới project, và nó có thể rất lớn.
        """
        if self.renderer.path_edit.text().strip():
            return
        ctx = getattr(self, "ctx", None)
        pid = (getattr(ctx, "active_project_id", "") or "").strip()
        if not pid or pid == "default":
            return
        try:
            from ...core.projects import load_project
            project = load_project(pid)
        except Exception:                                    # noqa: BLE001
            return
        if project is not None:
            self.renderer.path_edit.setText(str(project.workspace_dir()))

    def _on_project_scan_started(self) -> None:
        """Renderer vừa đổi project. Nó chỉ quét ngay khi màn này đang mở."""
        if self.renderer.isVisible():
            self._show_busy("structure.scanning")

    def _show_busy(self, key: str) -> None:
        """Hiện panel và ÉP VẼ NGAY.

        ``repaint()`` chứ không ``update()``: ``update()`` chỉ xếp hàng một lượt
        vẽ cho vòng lặp sự kiện, mà vòng lặp đó sắp bị chặn — panel sẽ chỉ hiện
        ra SAU khi hết đóng băng, đúng lúc không còn cần tới nó nữa.
        """
        self._busy_label.setText(tr(key))
        self._busy.adjustSize()
        self._center_busy()
        self._busy.show()
        self._busy.raise_()
        self._busy.repaint()

    def _hide_busy(self) -> None:
        """Ẩn panel khi đồ thị đã vẽ xong."""
        if getattr(self, "_busy", None) is not None:
            self._busy.hide()

    def _center_busy(self) -> None:
        """Giữ panel ở giữa khung, kể cả khi cửa sổ đổi kích thước."""
        busy = getattr(self, "_busy", None)
        if busy is None:
            return
        size = busy.sizeHint()
        busy.setGeometry((self.width() - size.width()) // 2,
                         (self.height() - size.height()) // 2,
                         size.width(), size.height())

    def resizeEvent(self, e):  # noqa: N802
        """Đổi kích thước cửa sổ thì panel phải theo."""
        super().resizeEvent(e)
        self._center_busy()

    def schedule_rescan(self, path: str = "") -> None:
        """Hẹn quét lại đồ thị sau khi thư mục có thay đổi."""
        self.renderer.schedule_rescan(path)

    def auto_scan_and_fit(self) -> None:
        """Vào màn GraphRAG: hiện đồ thị, chỉ quét lại khi thật sự cần.

        Panel "đang tải" bật TRƯỚC khi gọi xuống renderer: phần dựng khung xem
        chặn GUI thread, nên phải vẽ panel ra trước lúc đó. Nó tự ẩn khi
        ``graph_rendered`` phát — bao trọn cả lượt quét chạy ở luồng nền phía
        sau, chứ không tắt ngay khi hàm này trả về.
        """
        self._ensure_scan_path()
        da_dung_khung = self.renderer.web is not None
        self._show_busy("structure.scanning" if da_dung_khung else "structure.loading_view")
        try:
            self.renderer.auto_scan_and_fit()
        finally:
            # Khong co gi de ve (chua chon thu muc) thi graph_rendered khong phat
            # — panel se treo lai mai mai neu khong tu don o day.
            if not self.renderer.path_edit.text().strip():
                self._hide_busy()

    def set_project(self, project_id: str) -> None:
        """Khoá phạm vi quét vào một project (chuỗi rỗng là bỏ khoá)."""
        self.renderer.set_project(project_id)

    def set_workspace_project(self, project_id: str) -> None:
        """Áp project theo màn Workspace — bỏ qua nếu project KHÔNG đổi.

        ``WorkspaceTab._bind_project`` gọi xuống đây, và nó chạy lại mỗi lần
        người dùng vào lại màn Workspace (``_goto`` -> ``refresh`` ->
        ``_load_current`` -> ``_bind_project``). Áp vô điều kiện thì bộ chọn
        project của chính màn GraphRAG bị kéo về giá trị của Workspace: chọn một
        project ở đây, sang tab khác rồi quay lại là mất.

        Đổi sang project khác ở màn Workspace thì vẫn áp — cùng luật với tab Thư
        mục (``FolderTab.set_project_root``). Chỉ lần refresh trong CÙNG một
        project VÀ cùng một thư mục là không được đụng.

        Chốt theo cả đường dẫn chứ không chỉ theo id: đổi thư mục làm việc ở
        màn Project không làm id đổi, nên chốt theo mỗi id thì màn này giữ
        nguyên đường dẫn cũ và quét nhầm thư mục. Tab Thư mục vốn đã chốt theo
        đường dẫn — đây là đưa hai nơi về đúng cùng một luật như comment này
        vẫn nói.
        """
        thu_muc = self._thu_muc_cua(project_id)
        if project_id == self._workspace_project and thu_muc == self._workspace_dir:
            return
        self._workspace_project = project_id
        self._workspace_dir = thu_muc
        self.set_project(project_id)

    @staticmethod
    def _thu_muc_cua(project_id: str) -> str:
        """Thư mục làm việc hiện tại của project, chuỗi rỗng nếu không có."""
        from cowork_local.core.projects import load_project

        project = load_project(project_id) if project_id else None
        return str(project.workspace_dir()) if project is not None else ""

    def prewarm(self) -> None:
        """Dựng sẵn khung đồ thị trước khi người dùng bấm vào, để lần mở đầu không giật."""
        self.renderer.prewarm()

    def hideEvent(self, e):  # noqa: N802
        # Leaving the GraphRAG tab → drop the temporary extracted info.
        """Rời màn GraphRAG thì xoá phần trích xuất tạm của khung hỏi-đáp."""
        self.qa.clear_extracts()
        super().hideEvent(e)


__all__ = ["StructureGraphView"]
