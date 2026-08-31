"""Co4E — node-graph workflow studio (a Workspace sub-tab).

Layout (3 columns): left sidebar (Workflows / Agents / Skills, with CRUD,
drag-to-canvas, run-in-background + a live "Running flows" status list) | center
(compact toolbar + node canvas + bottom Chat/Output) | right (step config panel).

Runs: pick a mode — Auto (each step's agent plans then executes), Plan
(read-only, each step only drafts a plan), or Manual (step-by-step, advance with
"Next step"). Adjacent steps feed the next automatically (no manual wiring).
Several flows can run at once (foreground on the canvas + background from the
Workflows list); the run manager keeps their status live across sub-tab switches.

Chat supports inline directives with autocomplete: ``/agent:<name>`` picks a
persona and ``/skill:<name>`` applies a skill — same as Cowork.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
    QListView, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QSpacerItem, QSplitter, QTabBar, QTableWidget,
    QTableWidgetItem, QTabWidget, QTextBrowser, QVBoxLayout, QWidget,
)

from ..core import co4e, skills as skills_mod
from ..core.co4e_builtins import BUILTIN_AGENTS
from ..core.co4e_run_manager import Co4ERunManager
from ..core.worker import AgentWorker
from ..i18n import on_language_changed, tr
from ..theme import current_palette
from .chat_view import ChatView
from .co4e_canvas import Co4ECanvas
from .co4e_config_panel import StepConfigPanel
from .icons import icon
from ..presentation.co4e.agent_list_panel import AgentListPanel
from ..presentation.co4e.co4e_chat_view import (
    ChatPanel, _ChatInput, _agent_names, _directive_token, _skill_names,
)
from ..presentation.co4e.co4e_run_control_widget import RunsPagePanel
from ..presentation.co4e.palette_list import _PaletteList
from ..presentation.co4e.skills_list_panel import SkillsListPanel


_PLAN_GLYPH = {"completed": "✓", "done": "✓", "in_progress": "▶", "running": "▶",
               "error": "✗", "pending": "○", "todo": "○"}


def _fmt_plan(steps) -> str:
    """Render plan steps ``[{title,status}]`` as a ticked-off checklist."""
    lines = []
    for s in steps or []:
        title = str((s or {}).get("title", "")).strip()
        if not title:
            continue
        glyph = _PLAN_GLYPH.get(str((s or {}).get("status", "pending")).lower(), "○")
        lines.append(f"{glyph} {title}")
    return "\n".join(lines)


class _EqualTabBar(QTabBar):
    """Icon-only sidebar tabs (Workflows / Agents / Skills), all the same width,
    sized to fill the sidebar with a comfortable minimum (~double the default
    icon-only width so they read as proper buttons) and an even gap between them.
    The icon sits centered in each tab."""

    _GAP = 6            # px between tabs — matches the QSS margin-right below

    def tabSizeHint(self, index):  # noqa: N802
        """Chia đều bề rộng cho mọi tab thay vì để Qt co theo độ dài nhãn.

        Nhãn dài ngắn khác nhau làm dải tab nhấp nhô mỗi khi đổi tên luồng.
        """
        base = super().tabSizeHint(index)
        n = self.count() or 1
        avail = self.width()
        if avail <= 1:                       # width not resolved yet → use parent
            p = self.parentWidget()
            avail = p.width() if p is not None else 0
        share = (avail - n * self._GAP) // n if avail > 1 else 0
        return QSize(max(56, share), max(30, base.height()))

    def resizeEvent(self, e):  # noqa: N802
        """Đổi bề rộng dải tab thì tính lại bề rộng từng tab."""
        super().resizeEvent(e)
        self.updateGeometry()                # re-hint tab widths when resized


from ..presentation.co4e.co4e_flow_tabs import Co4EFlowTabsMixin
from ..presentation.co4e.co4e_sidebar import Co4ESidebarMixin
from ..presentation.co4e.co4e_layout import Co4ELayoutMixin
from ..presentation.co4e.co4e_workflow_crud import Co4EWorkflowCrudMixin
from ..presentation.co4e.co4e_agents import Co4EAgentsMixin
from ..presentation.co4e.co4e_runs import Co4ERunsMixin
from ..presentation.co4e.co4e_chat import Co4EChatMixin


class Co4ETab(
        Co4EFlowTabsMixin,
        Co4ESidebarMixin,
        Co4ELayoutMixin,
        Co4EWorkflowCrudMixin,
        Co4EAgentsMixin,
        Co4ERunsMixin,
        Co4EChatMixin,
        QWidget):
    """Màn Co4E Studio, ghép từ 7 mixin: dải tab luồng, cột trái, bố cục, CRUD luồng,
    quản lý agent, chạy luồng, và khung chat.

    Tách thành mixin để mỗi phần nằm trong một file dưới trần 400 dòng; thứ tự
    kế thừa quan trọng — xem ghi chú ở đầu từng file mixin.
    """
    status_message = Signal(str)

    def __init__(self, ctx):
        """Dựng Co4E Studio: khung vẽ workflow, cột nguyên liệu và bảng Flow Status.

        Mở sẵn một workflow trống để người dùng kéo bước vào ngay, không phải bấm
        "tạo mới" trước.
        """
        super().__init__()
        self.ctx = ctx
        self._wf: co4e.Workflow = co4e.new_workflow(tr("co4e.untitled"))
        self._chat_worker: Optional[AgentWorker] = None
        # run state
        self.manager = Co4ERunManager(ctx)
        self.manager.changed.connect(self._refresh_runs)
        self.manager.event.connect(self._on_manager_event)
        # Per-flow run state so any number of flow tabs run in PARALLEL without
        # mixing (bounded only by the machine — each run is its own QThread).
        self._flow_runs: Dict[str, str] = {}        # wf_id -> its active canvas run id
        self._run_logs: Dict[str, "ChatView"] = {}  # run_id -> that flow's chat log
        self._flow_outputs: Dict[str, Dict[str, str]] = {}  # wf_id -> {node_id: output}
        # Running token/cost total per flow (↓in ↑out ▤ctx $cost), shown in the
        # Messages header like Cowork's conversation total.
        self._flow_usage: Dict[str, Dict[str, float]] = {}
        self._project_id: str = ""                  # selected Workspace project
        self._project_dir: Optional[Path] = None    # its workspace folder (flow output goes here)
        # manual mode
        self._manual_active = False
        self._manual_order: List[str] = []
        self._manual_idx = 0
        # open flows shown as browser-style tabs (each its own graph; runs are
        # independent via the run manager)
        self._flows: List[co4e.Workflow] = []
        self._active_flow_idx = -1

        root = QHBoxLayout(self)
        self._split = QSplitter(Qt.Horizontal)
        root.addWidget(self._split)

        sidebar = self._build_sidebar()
        sidebar.setMinimumWidth(180)      # 210 pushed the whole tab past 1214px min
        self._split.addWidget(sidebar)
        self._split.addWidget(self._build_center())
        self.config = StepConfigPanel(ctx)
        self.config.setMinimumWidth(300)     # so fields (incl. the model row) are never clipped
        self.config.changed.connect(self._on_config_changed)
        self.config.run_node.connect(lambda nid: self._run_single(nid))
        self.config.run_from.connect(self._run_from)
        self.config.delete_node.connect(self.canvas.delete_node)
        self._config_collapsed = False
        self._config_expanded_w = 360
        self._split.addWidget(self._wrap_config())
        from PySide6.QtCore import QTimer

        from .widgets import narrow_guard
        self._narrow_guard = narrow_guard(self, self._NARROW, self._apply_narrow_layout)
        # Deferred one tick: the parent chain (and therefore window()) only
        # exists after whoever is building this has finished adding it.
        QTimer.singleShot(0, self._narrow_guard.attach)
        # Start the sidebar wider than its 180px floor — at the floor the
        # "Chạy nền" button and the flow names are cut off.
        self._split.setSizes([230, 720, 360])
        self._split.setStretchFactor(0, 0)
        self._split.setStretchFactor(1, 1)
        self._split.setStretchFactor(2, 0)
        self._split.setStretchFactor(0, 0)
        self._split.setStretchFactor(1, 1)
        self._split.setStretchFactor(2, 0)
        self._split.setSizes([250, 780, 360])
        self._split.setChildrenCollapsible(True)

        self.canvas.node_selected.connect(self._on_node_selected)
        self.canvas.node_activated.connect(self._on_node_selected)
        self.canvas.graph_changed.connect(self._autosave)

        self._reload_sidebar()
        self._open_flow(self._wf)          # first browser-style flow tab
        self._retranslate()                # set Runs table headers etc.
        self._refresh_runs()
        on_language_changed(self._retranslate)

    # ---- flow tabs (browser-style: several open flows, independent) --------










    # ---- per-flow run helpers (parallel, isolated per flow) ---------------



    # ---- sidebar ----------------------------------------------------------

    _SIDE_RUNS = 6









    # ---- center -----------------------------------------------------------



    # Below this window width the three panes (rail + 180 sidebar + canvas +
    # 300 config) leave the canvas too little to draw a flow in, and the config
    # fields start clipping instead of shrinking. Measured with
    # tools/check_responsive.py — Co4E gets the full content area (no project or
    # history pane beside it), so the threshold is about its own screen only.
    _NARROW = 1300

    # Chỗ này từng có một ``showEvent`` thứ hai chỉ gọi
    # ``self._narrow_guard.attach()``. Lớp này còn một ``showEvent`` nữa ở phía
    # dưới, và Python giữ định nghĩa SAU CÙNG — nên bản ở đây chưa bao giờ chạy.
    # Đã gộp cả hai việc vào đúng một ``showEvent`` (xem bên dưới).







    # ---- per-flow chat logs (each flow = its own conversation) ------------





    # ---- workflow load/save ----------------------------------------------














    # ---- node selection / config -----------------------------------------


    # ---- custom agents ----------------------------------------------------





    # ---- running ----------------------------------------------------------








    # ---- manual mode (step-by-step) --------------------------------------



    # ---- run-manager events ----------------------------------------------






    # ---- workspace binding + output folder (where flow files land) --------
    def set_project(self, project_id: str) -> None:
        """Bind Co4E to the SELECTED Workspace project so flow output (and per-run
        folders) land in THAT project's workspace — mirroring how Cowork writes to
        the project folder — instead of the global/config output dir."""
        from ..core.projects import load_project
        self._project_id = project_id or ""
        self._project_dir = None
        if project_id and project_id not in ("", "default"):
            proj = load_project(project_id)
            if proj is not None:
                self._project_dir = Path(proj.workspace_dir())
        # Route the run manager's output at the selected workspace, and filter
        # Flow Status to this workspace's runs.
        self.manager.set_output_root(self._flow_output_root())
        self.manager.set_current_project(self._project_id)
        if hasattr(self, "ws_folder_btn"):
            self._refresh_ws_folder_btn()

    def _flow_output_root(self) -> Path:
        """The workspace folder flow outputs are written under (one subfolder per
        flow). Uses the SELECTED project's workspace when one is bound, else the
        global Cowork output dir. Mirrors co4e_run_manager._out_dir's base."""
        if self._project_dir is not None:
            return self._project_dir / "co4e"
        try:
            base = self.ctx.config.cowork_output_dir()
        except Exception:  # noqa: BLE001
            base = co4e.CO4E_DIR / "runs"
        return Path(base) / "co4e"

    def _refresh_ws_folder_btn(self) -> None:
        """Cập nhật nhãn nút thư mục làm việc, rút gọn còn hai cấp cuối cho đỡ dài."""
        root = self._flow_output_root()
        parts = root.parts
        short = "…/" + "/".join(parts[-2:]) if len(parts) > 2 else str(root)
        self.ws_folder_btn.setText(short)
        self.ws_folder_btn.setToolTip(tr("co4e.tt_open_workspace", path=str(root)))

    def _open_workspace_folder(self) -> None:
        """Mở thư mục kết quả của luồng trong trình quản lý tệp của hệ điều hành."""
        from .osutil import open_location
        root = self._flow_output_root()
        try:
            root.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        open_location(str(root))







    def showEvent(self, e):  # noqa: N802
        """Mỗi lần tab được hiện lại: làm mới bảng Flow Status và gắn lại bộ canh
        bố cục hẹp.

        Gắn lại bộ canh là cần: widget có thể đã được chuyển sang cửa sổ khác kể
        từ lần hiện trước, và bộ canh theo dõi CỬA SỔ chứ không theo dõi widget.
        """
        # Guarantee the status list is current whenever the tab is shown again.
        self._refresh_runs()
        self._narrow_guard.attach()
        super().showEvent(e)

    def _out_dir(self) -> Path:
        # Save chat/flow deliverables into the SELECTED workspace (the active
        # project's folder via _flow_output_root), so files land where the user
        # works with them — not in the config/install folder.
        """Thư mục ghi kết quả của luồng đang mở, tạo sẵn nếu chưa có.

        Ghi vào thư mục của workspace đang chọn để file rơi đúng chỗ người dùng làm
        việc, không rơi vào thư mục cài đặt.
        """
        d = self._flow_output_root() / co4e.slugify(self._wf.name or "flow")
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ---- chat (with /agent /skill directives) -----------------------------







    # ---- token / cost accounting (shown per-message + as a flow total) ------





    # ---- i18n -------------------------------------------------------------
    def _retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn cho tiêu đề các mục và tooltip."""
        for key in self._sections:
            self._sync_section_arrow(key)
        self.runs_more_btn.setToolTip(tr("co4e.tt_runs_tab"))
        self.wf_new_btn.setText(tr("co4e.new"))
        self.wf_new_btn.setToolTip(tr("co4e.tt_new_wf"))
        self.runs_btn.setText(tr("co4e.runs_tab"))
        self.runs_btn.setToolTip(tr("co4e.tt_runs_tab"))
        self.runs_back_btn.setText(tr("co4e.back_to_flow"))
        self.runs_back_btn.setToolTip(tr("co4e.tt_back_to_flow"))
        self.runs_title.setText(tr("co4e.running_flows"))
        self.run_stop_btn.setText(tr("co4e.stop"))
        self.run_rename_btn.setText(tr("co4e.rename_run"))
        self.run_del_btn.setText(tr("co4e.delete_run"))
        self.run_clear_btn.setText(tr("co4e.clear_done"))
        self._refresh_ws_folder_btn()
        self.runs_table.setHorizontalHeaderLabels([
            tr("co4e.runs_col_flow"), tr("co4e.runs_col_status"), tr("co4e.runs_col_steps"),
            tr("co4e.runs_col_by"), tr("co4e.runs_col_at")])
        self._reload_sidebar()
        self._refresh_runs()


def _html_escape(text: str) -> str:
    """Thoát ba ký tự HTML nguy hiểm, để nội dung người dùng không phá vỡ khung chat."""
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _qcolor(hex_str: str):
    """Đổi chuỗi màu hex thành ``QColor``. Import muộn để module này nạp được ở nơi
    chưa có Qt GUI.
    """
    from PySide6.QtGui import QColor
    return QColor(hex_str)
