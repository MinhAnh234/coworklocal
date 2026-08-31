"""Base chat panel shared by the Cowork and Code tabs.

Provides: streaming transcript, a message queue, and history autosave.

Several messages can run **at the same time** inside one tab: each turn owns its
own worker thread and its own turn-context (assistant bubble, transcript record,
message list, output folder), so their streaming output and files never collide.
The number of simultaneous turns is capped by ``cowork.max_parallel`` (default 5);
extra messages wait in the composer queue and start automatically as slots free
up. Graph events are still forwarded per session.
"""
from __future__ import annotations

from .chat_event_stream import ChatEventStreamMixin
from .chat_panel_layout import ChatPanelLayoutMixin
from .chat_live_turns import ChatLiveTurnsMixin
from .chat_helpers import (  # noqa: F401 — giữ đường vào cũ
    _TOOL_STATUS, _format_plan_steps, _is_scratch,
)

from .attachment_picker import AttachmentMixin
from .chat_output_panel import OutputPanelMixin
from .chat_agents import ChatAgentsMixin
from .chat_turn_runner import ChatTurnRunnerMixin
from .chat_session_store import ChatSessionMixin

from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtCore import QFileSystemWatcher
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QSplitter,
    QVBoxLayout, QWidget,
)

from ...core.worker import AgentWorker
from ...i18n import on_language_changed, tr
from ...state import AppContext
from ...theme import current_palette
from .chat_bubble_style import ThinkingIndicator
from .chat_history_widget import ChatView
from .composer_widget import Composer
from ...ui.icons import collapse_right_icon, icon as app_icon
from ...ui.osutil import is_image, open_path
from ...ui.widgets import CollapsibleSection, CollapseStrip, PlanSection


_PLAN_ICONS = {"pending": "○", "running": "▶", "done": "✓", "error": "✗"}

# Friendly "what the agent is doing now" translation keys for the working
# indicator, so a long file/document build reads as "Creating…" rather than a
# generic "Running".






class ChatPanel(ChatLiveTurnsMixin, ChatPanelLayoutMixin, ChatEventStreamMixin, AttachmentMixin,
                OutputPanelMixin,
                ChatAgentsMixin,
                ChatTurnRunnerMixin,
                ChatSessionMixin,
                QWidget):
    """Khung chat dùng chung, ghép từ 8 mixin: bố cục, dòng sự kiện, tệp đính kèm,
    ô vào/ra, bộ chọn agent, chạy lượt, lưu phiên và các lượt đang chạy.

    Màn Cowork kế thừa lớp này và chỉ ghi đè phần khác biệt của mình.
    """
    graph_event = Signal(str, dict)   # (session_name, event)
    turn_finished = Signal(dict)
    status_message = Signal(str)
    output_changed = Signal(str)      # workspace dir; emitted when a file is written
    history_changed = Signal()        # a session was created/updated → refresh History

    def __init__(self, ctx: AppContext, kind: str, session_name: str,
                 placeholder_key: str = "composer.placeholder_default"):
        """Dựng khung chat cho một bề mặt (``kind``) và mở một phiên mới.

        ``placeholder_key`` là khoá i18n chứ không phải chữ sẵn, để đổi ngôn ngữ là
        chữ gợi ý đổi theo.
        """
        super().__init__()
        from ...core.history import new_session_id

        self.ctx = ctx
        self.kind = kind
        self.session_name = session_name
        self.session_id = new_session_id()
        self.title = ""
        self._notify_title()
        # Which project (workspace) this conversation belongs to — every new
        # thread inherits the currently selected project (Claude-Projects style).
        self.project_id = "default"
        self.messages: List[Dict[str, Any]] = []
        # self.worker points at the most-recently-started worker (kept for
        # back-compat); every running turn is tracked in self._active so several
        # can run concurrently. Each value is a turn-context dict — see _start_turn.
        self.worker: AgentWorker | None = None
        self._active: Dict[AgentWorker, Dict[str, Any]] = {}
        self._turn_seq: int = 0
        # session_id -> its live messages list, for every conversation that still has
        # a turn running. Lets you start a new chat / reopen an old one WHILE work
        # runs: the running turn keeps writing to its own conversation in the
        # background, and reopening it attaches to the SAME list (never a stale disk
        # copy), so the two never race on save.
        self._sessions_live: Dict[str, List[Dict[str, Any]]] = {}
        self._teams_worker: AgentWorker | None = None
        self.turns: List[Dict[str, Any]] = []

        # File system watcher — watches the workspace/output folder for new files
        # and auto-loads them into the agent's context on the next turn.
        self._file_watcher = QFileSystemWatcher(self)
        self._file_watcher.directoryChanged.connect(self._on_watched_dir_changed)
        self._known_files: set = set()  # set of known file paths in the watched dir
        self._watch_debounce = QTimer(self)
        self._watch_debounce.setSingleShot(True)
        self._watch_debounce.setInterval(800)  # debounce rapid file changes
        self._watch_debounce.timeout.connect(self._process_new_watched_files)
        self._watched_dir: Optional[Path] = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._toolbar = QWidget()
        self.toolbar_v = QVBoxLayout(self._toolbar)
        self.toolbar_v.setContentsMargins(10, 8, 10, 4)
        self.toolbar_v.setSpacing(4)
        self.toolbar_layout = QHBoxLayout()   # first row; tabs may add more rows
        self.toolbar_layout.setSpacing(8)
        self.toolbar_v.addLayout(self.toolbar_layout)
        root.addWidget(self._toolbar)

        self.chat_view = ChatView()
        self.composer = Composer(placeholder_key)
        self.composer.submitted.connect(self.submit)
        self.composer.stop_requested.connect(self.stop)
        self.composer.attachments_added.connect(self._on_attachments_added)
        self.composer.attachment_removed.connect(self._on_attachment_removed)
        self.composer.attach_limit_note.connect(self.status_message)
        self.composer.manage_skills.connect(self._open_skills_manager)
        self.composer.set_max_attachments(
            int(ctx.config.data.get("attachments", {}).get("max_files", 10) or 0))
        # Conversation token/cost total (↓in ↑out ▤total $cost) — bottom-left,
        # updated after each turn; cost uses the Monitoring model-price table.
        self._usage_total_lbl = QLabel("")
        self._usage_total_lbl.setObjectName("hint")
        self._usage_total_lbl.setStyleSheet(f"color: {current_palette().text_faint};")


        # Per-tab "Agent" = which MODEL this tab uses (e.g. deepseek / gemma /
        # qwen for the local provider). Cowork and Code pick independently and
        # run in parallel. The list is fetched from the active provider.
        # The per-tab Agent defaults to the Settings model on startup; a manual
        # pick (override) is remembered only until the active provider changes.
        self._model = ctx.config.provider_conf().get("model", "")
        self._agent_provider = ctx.config.active_provider
        self._agent_user_override = False
        self._admin_agent = None   # selected Admin-defined agent preset, if any
        # Auto Model Routing override for the NEXT turn (set by _apply_routing when
        # the router picks a different model). None → use the tab's own selection.
        self._routed_provider: Optional[str] = None
        self._routed_model: Optional[str] = None
        self._last_turn_agent_signature = None   # what ran the LAST turn (see _note_agent_switch)
        self._pending_agent_switch_review = False
        self._agent_worker: AgentWorker | None = None
        self._agent_lbl = QLabel(tr("chatpanel.agent_label"))
        self._agent_lbl.setObjectName("hint")
        self.agent_combo = QComboBox()
        self.agent_combo.setMinimumWidth(150)
        self.agent_combo.setToolTip(tr("chatpanel.agent_tooltip"))
        self.agent_combo.currentIndexChanged.connect(self._on_agent_changed)
        self.composer.add_bottom_left(self._agent_lbl)
        self.composer.add_bottom_left(self.agent_combo)
        # Off/Auto/Manual routing toggle — lets the router pick the best-fit
        # model per message (see core/routing + _apply_routing).
        from ...ui.routing_toggle import RoutingToggle
        self.routing_toggle = RoutingToggle(ctx, self.kind)
        # The drawing reads the strip left to right as
        #   Agent: … · Định tuyến: … · ↓in ↑out · $cost · 📁 folder
        # so these sit together on the left, with the folder box the Cowork tab
        # appends landing after them. Nén and Tự chạy stay on the right, where
        # the control inventory marks them "giữ nguyên tại chỗ".
        self.composer.add_bottom_left(self.routing_toggle)
        self.composer.add_bottom_left(self._usage_total_lbl)
        # Manual "compress conversation" — trim old history to cut tokens.
        self.compress_btn = QPushButton(tr("chatpanel.compress_btn"))
        self.compress_btn.setIcon(app_icon("compress"))
        self.compress_btn.setToolTip(tr("chatpanel.compress_tooltip"))
        self.compress_btn.clicked.connect(self._compress_messages)
        self.composer.add_bottom_right(self.compress_btn)
        self.refresh_agents()

        self._build_layout(root)

    def _retranslate_base(self) -> None:
        """Re-apply the current language to the chrome shared by every tab
        (Cowork/Code toolbars call their own retranslate on top of this)."""
        self._agent_lbl.setText(tr("chatpanel.agent_label"))
        self.agent_combo.setToolTip(tr("chatpanel.agent_tooltip"))
        self.compress_btn.setText(tr("chatpanel.compress_btn"))
        self.compress_btn.setToolTip(tr("chatpanel.compress_tooltip"))
        self.input_section.set_title(tr("widgets.input_files"))
        self.output_section.set_title(tr("widgets.output_files").upper())
        self.plan_section.set_title(tr("widgets.plan_title"))
        self._io_collapse_btn.setToolTip(tr("chatpanel.collapse_files_tooltip"))
        self._files_header.setText(tr("chatpanel.files_header"))
        self._io_strip.setToolTip(tr("chatpanel.expand_files_tooltip"))

    def apply_theme(self) -> None:
        """Re-apply theme styles to the chat view so all existing message bubbles
        adapt when the app switches between light and dark modes."""
        self.chat_view.apply_theme()

    # ---- hooks for subclasses ---------------------------------------


    def assistant_title(self) -> str:
        """Nhãn hiện trên bong bóng trả lời; lớp con ghi đè để đổi tên trợ lý."""
        return tr("chat.assistant")



    # ---- file system watcher for auto-loading new files --------------











    # ---- skills management (shared by Cowork and Code) ---------------


    # ---- per-tab agent (model / admin-agent preset) selection --------
    _ADMIN_AGENT_PREFIX = "admin:"
    # Sent (invisibly — folded into the outgoing content, never the visible
    # chat bubble) as a one-shot prefix on the FIRST turn run under a newly
    # picked model/agent, when the conversation already has prior turns: asks
    # the new model to check over the most recent step before doing anything
    # new, so a mid-conversation switch doesn't silently drop continuity.
    _MODEL_SWITCH_REVIEW_NOTE = (
        "[Note: the AI model/agent for this conversation was just switched.] Before "
        "addressing the request below, briefly re-check the most recent step above — "
        "if anything there looks incomplete, inconsistent, or wrong, redo or fix it "
        "first, then continue."
    )












    # ---- shared split-pane collapse helpers (used by subclasses too) ----


    # ---- delete a turn (message + its input/output files) ------------


    # ---- turn lifecycle ---------------------------------------------


    # File types considered valid input data in the workspace/output folder
    _INPUT_EXTS = {
        ".csv", ".json", ".txt", ".md", ".log", ".xml", ".yaml", ".yml",
        ".docx", ".docm", ".xlsx", ".xlsm", ".pptx", ".pdf", ".odt", ".ods", ".odp",
        ".rtf", ".tsv",
    }
























    # ---- token / cost accounting (shown in the chat, Claude-style) ----------










    # ---- Teams auto-notify ------------------------------------------
    def _last_assistant_text(self) -> str:
        """Nội dung trả lời cuối cùng của trợ lý trong hội thoại; '' nếu chưa có."""
        for m in reversed(self.messages):
            if m.get("role") == "assistant" and m.get("content"):
                return m["content"]
        return ""


    # ---- persistence -------------------------------------------------

    def _busy(self) -> bool:
        """True while any turn is still running in this tab (any conversation)."""
        return bool(self._active)

    def _view_busy(self) -> bool:
        """True while the CURRENTLY-VIEWED conversation has a turn running."""
        return any(c.get("home_id") == self.session_id for c in self._active.values())

    def _sync_indicators(self) -> None:
        """Reflect the CURRENT conversation's agent status in the chat box + composer.
        Switching chats, or hitting History → Refresh, shows whether THIS chat is
        still processing (a background turn) or idle."""
        if self._view_busy():
            self.thinking.start("chat.running")   # this conversation is still working
        else:
            self.thinking.stop()
        self.composer.set_running(bool(self._active))   # Stop shows while anything runs
        self.composer.set_busy(self._view_busy() or len(self._active) >= self._max_parallel())

    def refresh_status(self) -> None:
        """Public: re-sync the on-screen agent status for the current conversation
        (used by the History Refresh button)."""
        self._sync_indicators()

    def _max_parallel(self) -> int:
        """Unlimited concurrent turns — no cap (the old Settings limit was removed).
        A large sentinel keeps the queue logic intact without ever gating."""
        return 100000

    def active_workers(self) -> List[AgentWorker]:
        """Workers for turns still running (used to stop them all on quit)."""
        return list(self._active)

