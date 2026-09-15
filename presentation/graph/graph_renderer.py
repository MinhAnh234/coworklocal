"""GraphRenderer — the toolbar, scan/render pipeline, and graph/messages
stack of GraphRAG (R08-T14, extracted from
``ui/structure_graph_view.py::StructureGraphView``, lines 188-286/336-661/
664-702 of the original 1035-line file — everything except the right-side
Q&A panel, which is ``graph_qa_widget.py::GraphQaWidget``).

Talks to the Q&A panel only through signals (:attr:`node_selected`,
:attr:`graph_rendered`) and a small read API (:attr:`graph`,
:meth:`selected_node_data`, :attr:`active_project_id`) — this class has no
idea ``GraphQaWidget`` exists, matching how
``presentation/folder/document_preview_manager.py`` doesn't know about the
AI-edit panel either.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QPointF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QGraphicsScene, QHBoxLayout, QLineEdit,
    QPushButton, QStackedWidget, QTabBar, QVBoxLayout, QWidget,
)

from cowork_local.core.worker import AgentWorker
from cowork_local.i18n import on_language_changed, tr
from cowork_local.presentation.graph import graph_export
from cowork_local.presentation.graph.graph_messages_view import GraphMessagesView
from cowork_local.presentation.graph.graph_scene_builder import build_scene
from cowork_local.presentation.graph.graph_scene_items import _Bridge, _Edge, _GraphView, _Node
from cowork_local.presentation.shared import HAS_WEB_ENGINE
from cowork_local.state import AppContext
from cowork_local.theme import current_palette
from cowork_local.ui.icons import icon


class GraphRenderer(QWidget):
    """Nửa "đồ thị" của màn GraphRAG: thanh công cụ, khung xem và vòng đời quét."""
    status_message = Signal(str)
    node_selected = Signal(object)   # a node's .data, whenever the scene selection changes
    graph_rendered = Signal()        # a scan just finished rendering (fresh OR re-fit)
    raw_json_ready = Signal(str)     # pre-formatted HTML for a clicked Messages entry
    project_changed = Signal()       # a DIFFERENT project was selected (or cleared)

    def __init__(self, ctx: AppContext):
        """Dựng thanh công cụ, khung xem 2D và chỗ chờ cho khung D3.

        Khung D3 KHÔNG được dựng ở đây: ``QWebEngineView`` mất vài trăm mili giây
        để khởi tạo, mà phần lớn người dùng mở màn này chỉ để xem cảnh Qt. Nó được
        dựng muộn trong :meth:`_ensure_web`.
        """
        super().__init__()
        self.ctx = ctx
        self._worker: Optional[AgentWorker] = None
        self._node_items: List[_Node] = []
        self._edge_items: List[_Edge] = []
        self._centroid = QPointF(0, 0)
        self._graph = None
        self._needs_scan = False
        self._scan_seq = 0   # only the latest scan's result is rendered (no stale overwrite)
        self._active_project_id = ""  # "" = free path; set = scan locked to that project's sandbox

        self._rescan_timer = QTimer(self)
        self._rescan_timer.setSingleShot(True)
        self._rescan_timer.setInterval(1500)
        self._rescan_timer.timeout.connect(self._scan)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        bar = QHBoxLayout()
        self.path_edit = QLineEdit(str(ctx.config.cowork_output_dir()))
        self.path_edit.setPlaceholderText(tr("structure.path_placeholder"))
        self._pick_btn = QPushButton()
        self._pick_btn.setIcon(icon("folder"))
        self._pick_btn.setObjectName("primary")
        self._pick_btn.clicked.connect(self._pick)
        self.project_combo = QComboBox()
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        self._scan_btn = QPushButton()
        self._scan_btn.setIcon(icon("search"))
        self._scan_btn.setObjectName("primary")
        self._scan_btn.clicked.connect(self._scan)
        self._export_btn = QPushButton()
        self._export_btn.setIcon(icon("upload"))
        self._export_btn.setObjectName("primary")
        self._export_btn.clicked.connect(self._export)
        bar.addWidget(self.path_edit, 1)
        bar.addWidget(self._pick_btn)
        bar.addWidget(self.project_combo)
        bar.addWidget(self._scan_btn)
        bar.addWidget(self._export_btn)
        root.addLayout(bar)
        self._refresh_project_combo()

        # Đồ thị | Tin nhắn as a real pair of tabs.
        self.view_tabs = QTabBar()
        self.view_tabs.setObjectName("viewTabs")
        self.view_tabs.setDrawBase(False)
        self.view_tabs.setExpanding(False)
        self.view_tabs.addTab(icon("graph"), "")
        self.view_tabs.addTab(icon("message"), "")
        self.view_tabs.currentChanged.connect(self._on_view_tab)
        tab_row = QHBoxLayout()
        tab_row.setContentsMargins(0, 0, 0, 0)
        tab_row.addWidget(self.view_tabs)
        tab_row.addStretch(1)
        root.addLayout(tab_row)

        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QColor(current_palette().bg))
        self.scene.selectionChanged.connect(self._on_selection)
        self.view = _GraphView(self.scene)

        self._stack = QStackedWidget()
        self._stack.addWidget(self.view)
        self.web = None
        self._bridge = None
        self._channel = None
        root.addWidget(self._stack, 1)
        # "Messages" view: all conversation messages grouped BY DAY, shown as
        # JSON — a separate concern composed in (see graph_messages_view.py).
        self._messages = GraphMessagesView(self)

        on_language_changed(self._retranslate)

    def _retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn cho thanh công cụ và tên tab."""
        self.path_edit.setPlaceholderText(tr("structure.path_placeholder"))
        self._pick_btn.setText(tr("structure.browse"))
        self._scan_btn.setText(tr("structure.scan"))
        self._export_btn.setText(tr("structure.export_png"))
        self.view_tabs.setTabText(0, tr("structure.graph_btn"))
        self.view_tabs.setTabText(1, tr("structure.msgs_btn"))
        self.view_tabs.setTabToolTip(1, tr("structure.msgs_tooltip"))
        self.project_combo.setToolTip(tr("structure.project_tooltip"))
        self._refresh_project_combo()

    # ---- public read API for GraphQaWidget ----------------------------------- #
    @property
    def graph(self):
        """Đồ thị đã quét gần nhất; ``None`` nếu chưa quét lần nào."""
        return self._graph

    @property
    def active_project_id(self) -> str:
        """Id dự án đang chọn trong bộ chọn; '' nếu chưa chọn."""
        return self._active_project_id

    def selected_node_data(self) -> list:
        """Dữ liệu của các node đang được chọn trên cảnh — panel Hỏi đáp đọc cái này
        để biết người dùng đang hỏi về cái gì.
        """
        return [item.data for item in self.scene.selectedItems() if isinstance(item, _Node)]

    # ---- project sandbox lock ------------------------------------------------- #
    def _refresh_project_combo(self) -> None:
        """Nạp lại danh sách project vào bộ chọn, giữ nguyên project đang chọn."""
        from cowork_local.core.projects import list_projects

        keep = self._active_project_id
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        self.project_combo.addItem(tr("structure.project_none"), "")
        row_to_select = 0
        for i, p in enumerate(list_projects(), start=1):
            self.project_combo.addItem(p.name, p.project_id)
            if p.project_id == keep:
                row_to_select = i
        self.project_combo.setCurrentIndex(row_to_select)
        self.project_combo.blockSignals(False)

    def set_project(self, project_id: str) -> None:
        """Khoá phạm vi quét vào một project (chuỗi rỗng là bỏ khoá)."""
        pid = project_id or ""
        self._refresh_project_combo()
        target = self.project_combo.findData(pid)
        if target < 0:
            target = 0
        if self.project_combo.currentIndex() == target:
            self._on_project_changed(target)
        else:
            self.project_combo.setCurrentIndex(target)

    def _on_project_changed(self, _idx: int) -> None:
        """Áp trạng thái khoá: đường dẫn chuyển sang chỉ đọc và trỏ vào thư mục"""
        from cowork_local.core.projects import load_project

        pid = self.project_combo.currentData() or ""
        project_changed = pid != self._active_project_id
        self._active_project_id = pid
        locked = bool(pid)
        self.path_edit.setReadOnly(locked)
        self._pick_btn.setEnabled(not locked)
        if locked:
            project = load_project(pid)
            if project is not None:
                self.path_edit.setText(str(project.workspace_dir()))
        if project_changed:
            self.project_changed.emit()   # GraphQaWidget drops its temp extraction cache
            # Mark it and scan on the next visit rather than now — see
            # auto_scan_and_fit()'s docstring for why.
            self._needs_scan = True
            # ...except when this screen is the one on show. The picker lives HERE,
            # so a user changing project is already looking at the graph: there is
            # no "next visit" to defer to, and they had to press Scan by hand.
            # Deferring still applies when the change came from the Workspace
            # screen while this one is hidden, which is what it was for.
            if self.isVisible() and self.path_edit.text().strip():
                self._needs_scan = False
                self._scan()

    # ---- helpers ---------------------------------------------------------------- #
    def _pick(self) -> None:
        """Mở hộp thoại chọn thư mục gốc để quét."""
        chosen = QFileDialog.getExistingDirectory(self, tr("structure.pick_folder_title"), self.path_edit.text())
        if chosen:
            self.path_edit.setText(chosen)

    def schedule_rescan(self, path: str = "") -> None:
        """Hẹn quét lại sau khi có thay đổi trên đĩa."""
        if self._graph is None:
            self._needs_scan = True
            return
        self._rescan_timer.start()

    # ---- Messages (by day, as JSON) — see graph_messages_view.py --------------- #
    def _on_view_tab(self, index: int) -> None:
        """Đổi giữa tab đồ thị và tab Tin nhắn."""
        self._messages.on_view_tab(index)

    def _toggle_messages(self) -> None:
        """Kept for callers that still ask for a flip (e.g. keyboard paths)."""
        self._messages.toggle()

    # ---- prewarm / scan lifecycle -------------------------------------------------- #
    def prewarm(self) -> None:
        """Pay for the graph view before it is clicked on, not during."""
        if self.web is not None:
            return
        self._ensure_web()
        if self._graph is None and self.path_edit.text().strip():
            self._needs_scan = False
            self._scan()

    def _ensure_web(self) -> None:
        """Dựng khung D3 nếu máy có WebEngine và chưa dựng.

        Gọi được nhiều lần — lần thứ hai trở đi không làm gì. Máy không có
        WebEngine thì bỏ qua im lặng và người dùng ở lại với cảnh Qt.
        """
        if self.web is not None or not HAS_WEB_ENGINE:
            return
        from PySide6.QtWebChannel import QWebChannel
        from PySide6.QtWebEngineWidgets import QWebEngineView

        self.web = QWebEngineView()
        self.web.setHtml(
            f"<body style='margin:0;background:{current_palette().bg}'></body>")
        self._bridge = _Bridge()
        self._channel = QWebChannel()
        self._channel.registerObject("py", self._bridge)
        self.web.page().setWebChannel(self._channel)
        self._stack.addWidget(self.web)
        self._stack.setCurrentWidget(self.web)
        if self._graph is not None:
            self._render_d3()

    def auto_scan_and_fit(self) -> None:
        """Vào màn GraphRAG: hiện đồ thị, chỉ quét lại khi thật sự cần."""
        self._ensure_web()
        if not self.path_edit.text().strip():
            return
        if self._worker is not None and self._worker.isRunning():
            self._fit()
            self.graph_rendered.emit()
            return
        if self._graph is not None and not self._needs_scan:
            self._fit()
            self.graph_rendered.emit()
            return
        self._needs_scan = False
        self._scan()

    # ---- scan --------------------------------------------------------------------- #
    def _scan(self) -> None:
        """Quét thư mục gốc ở luồng nền rồi vẽ kết quả.

        Mỗi lượt quét mang một số thứ tự ``_scan_seq``; kết quả về mà số không còn
        khớp thì bị bỏ, để lượt quét cũ không đè lên lượt mới.
        """
        path = self.path_edit.text().strip() or str(Path.cwd())
        mode = "files"
        use_cmem = bool(self.ctx.config.codebase_memory.get("enabled"))
        cmem_bin = self.ctx.config.codebase_memory.get("binary_path", "")
        st = self.ctx.config.structure
        max_nodes = int(st.get("max_nodes", 500) or 0)
        max_edges = int(st.get("max_edges", 500) or 0)
        self._scan_seq += 1
        seq = self._scan_seq
        self.status_message.emit(tr("structure.scanning"))

        def job(worker: AgentWorker):
            """Chạy nền: dựng đồ thị từ thư mục rồi tính toạ độ.

            Ưu tiên đọc từ codebase-memory nếu có sẵn — nhanh hơn nhiều so với quét lại
            cả cây thư mục; không có thì quét trực tiếp.
            """
            from cowork_local.core.structure_graph import (
                build_from_codebase_memory, build_from_directory, force_layout,
            )
            if use_cmem:
                from cowork_local.core.codebase_memory import CodebaseMemory
                mem = CodebaseMemory(cmem_bin)
                graph = (build_from_codebase_memory(mem, path, mode, max_nodes, max_edges)
                         if mem.available else build_from_directory(path, mode, max_nodes, max_edges))
            else:
                graph = build_from_directory(path, mode, max_nodes, max_edges)
            pos = force_layout(graph)
            return {"graph": graph, "pos": pos, "seq": seq}

        w = AgentWorker(job)
        w.finished_ok.connect(self._render)
        w.failed.connect(lambda e: self.status_message.emit(tr("structure.scan_error", err=e)))
        self._worker = w
        w.start()

    def _render(self, result: dict) -> None:
        """Vẽ kết quả quét ra khung Qt 2D (và ra D3 nếu đang bật).

        Lượt quét cũ về muộn thì bỏ: ``seq`` của nó không còn khớp
        ``_scan_seq``. Không chặn ở đây thì người dùng đổi dự án nhanh sẽ thấy
        đồ thị của dự án TRƯỚC đè lên dự án đang chọn.
        """
        if result.get("seq") is not None and result["seq"] != self._scan_seq:
            return
        graph = result.get("graph")
        pos = result.get("pos", {})
        if graph is None:
            return
        self._graph = graph

        self._node_items, self._edge_items, self._centroid = build_scene(
            self.scene, graph, pos, current_palette().bg)
        self._fit()

        if self.web is not None:
            self._render_d3()

        note = tr("structure.truncated_note") if getattr(graph, "truncated", False) else ""
        self.status_message.emit(tr(
            "structure.graph_summary", nodes=len(graph.nodes), edges=len(graph.edges), note=note))
        self.graph_rendered.emit()

    def _render_d3(self) -> None:
        """Nạp lại trang D3 từ đồ thị hiện có. Lỗi dựng HTML chỉ báo lên thanh trạng
        thái chứ không ném ra — cảnh Qt vẫn xem được.
        """
        if self.web is None or self._graph is None:
            return
        from cowork_local.core.d3_graph import build_html
        try:
            self.web.setHtml(build_html(self._graph), QUrl("https://cowork.local/"))
        except Exception as exc:
            self.status_message.emit(f"D3 view error: {exc}")

    # ---- native interactions ------------------------------------------------------- #
    def _on_selection(self) -> None:
        """Chọn một node trên cảnh thì báo cho panel Hỏi đáp biết."""
        for item in self.scene.selectedItems():
            if isinstance(item, _Node):
                self.node_selected.emit(item.data)
                return

    def _fit(self) -> None:
        """Canh toàn bộ đồ thị vừa khung nhìn."""
        if self.web is not None and self._stack.currentWidget() is self.web:
            self.web.page().runJavaScript("window.fitGraph && window.fitGraph();")
            return
        rect = self.scene.itemsBoundingRect()
        if not rect.isNull():
            self.view.fitInView(rect.adjusted(-40, -40, 40, 40), Qt.KeepAspectRatio)

    def _export(self) -> None:
        """Xuất khung đang xem ra PNG.

        Cách chụp tuỳ khung nào đang hiện — xem ``graph_export.py``.
        """
        graph_export.export_png(
            parent=self,
            showing=self._stack.currentWidget(),
            web=self.web,
            is_web_visible=self._stack.currentWidget() is self.web,
            status=self.status_message.emit,
        )


__all__ = ["GraphRenderer"]
