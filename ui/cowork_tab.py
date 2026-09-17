"""Cowork tab — chat with the local Internal Agent."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from ..core import agent_roles
from ..core.worker import AgentWorker
from ..i18n import on_language_changed, tr
from ..state import AppContext
from .chat_panel import ChatPanel
from .icons import icon

_FOLDER_LBL_MAX_CHARS = 42  # keep the composer's bottom row from crowding out Agent/Send


class CoworkTab(ChatPanel):
    """Màn Cowork: khung chat chính, gắn với một project và một thư mục kết quả.

    Khác :class:`ChatPanel` gốc ở chỗ kết quả được gom theo TỪNG hội thoại và
    chỉ hiện ra sau khi lượt chạy thành công — xem :meth:`register_output`.
    """
    def __init__(self, ctx: AppContext):
        """Màn Cowork — một ``ChatPanel`` kèm thanh công cụ riêng hiện provider, model và
        thư mục kết quả đang dùng.
        """
        super().__init__(ctx, "cowork", "Cowork", placeholder_key="composer.placeholder_cowork")

        self._title_lbl = QLabel()
        self._title_lbl.setStyleSheet("font-weight:700; font-size:15px;")
        self.skills_btn = QPushButton()
        self.skills_btn.setIcon(icon("book"))
        self.skills_btn.clicked.connect(self._open_skills_manager)

        self._new_btn = QPushButton()
        self._new_btn.setIcon(icon("new"))
        self._new_btn.clicked.connect(self.new_session)

        self.toolbar_layout.addWidget(self._title_lbl)
        self.toolbar_layout.addStretch(1)
        self.toolbar_layout.addWidget(self.skills_btn)
        self.toolbar_layout.addWidget(self._new_btn)

        # Where Cowork saves its deliverables — the project's sandbox workspace
        # (or, for a folder picked via the button, that folder). Only the
        # folder NAME shows beside the button (not the full path as a
        # link/hint text) — the full path is still available as a tooltip.
        self.folder_btn = QPushButton()
        self.folder_btn.setIcon(icon("folder"))
        self.folder_btn.clicked.connect(self._pick_output_folder)
        self.folder_lbl = QLabel("")
        self.folder_lbl.setObjectName("hint")
        folder_box = QWidget()
        _fbl = QHBoxLayout(folder_box)
        _fbl.setContentsMargins(0, 0, 0, 0)
        _fbl.setSpacing(6)
        _fbl.addWidget(self.folder_btn)
        _fbl.addWidget(self.folder_lbl)   # folder name BESIDE the button
        # Which project (workspace) the CURRENT thread belongs to. Cowork now
        # always lives INSIDE the Workspace screen for a single selected project,
        # so the project name beside the composer is redundant chrome — the label
        # is kept as a hidden member (its text still tracks the active project for
        # tooltips/tests) but no longer added to the layout.
        self.project_lbl = QLabel("")
        self.project_lbl.setObjectName("hint")
        self.project_lbl.setVisible(False)
        self.composer.add_bottom_left(folder_box)

        # Per-workspace "Auto-run" toggle (auto-approve commands in THIS
        # workspace) — sits next to the routing toggle the base class added.
        from .routing_toggle import AutoRunToggle
        self.autorun_toggle = AutoRunToggle(self.ctx)
        self.composer.add_bottom_right(self.autorun_toggle)

        self.refresh_header()
        # Start watching the output folder for new files
        wd = self.workspace_dir()
        if wd:
            self._start_watching(wd)
        # Cowork shows ONLY the final deliverables, refreshed from disk once a turn
        # succeeds (see _cleanup_turn) — never intermediate files or a folder name.
        on_language_changed(self._retranslate)

    def refresh_title(self) -> None:
        """Head the screen with the thread you are in, as the drawing does.

        It said "Cowork" on every conversation — the screen's own name, which
        the rail already shows. The thread's title is the thing that changes and
        the thing that tells you where you are; a thread with no title yet (a
        new chat, before its first turn) falls back to the screen name.
        """
        lbl = getattr(self, "_title_lbl", None)
        if lbl is None:
            return          # ChatPanel.__init__ sets self.title before we exist
        lbl.setText(getattr(self, "title", "") or tr("cowork.title"))

    def _retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn cho tiêu đề và các nút trên thanh công cụ."""
        # ChatPanel dựng phần chrome dùng chung (nhãn Agent, nút Nén, tiêu đề ba
        # bảng tệp) nhưng KHÔNG tự đăng ký dịch lại — lớp con là chỗ duy nhất có
        # đăng ký, nên bỏ dòng này là toàn bộ phần đó đứng ở ngôn ngữ lúc dựng.
        self._retranslate_base()
        self.refresh_title()
        self.skills_btn.setText(tr("cowork.skills_btn"))
        self.skills_btn.setToolTip(tr("cowork.skills_tooltip"))
        self._new_btn.setText(tr("cowork.new_chat"))
        self.folder_btn.setText(tr("cowork.pick_folder_btn"))
        self.folder_btn.setToolTip(tr("cowork.pick_folder_tooltip"))
        self._apply_output_folder_label()

    # ---- output folder --------------------------------------------------
    def _pick_output_folder(self) -> None:
        """Chọn thư mục kết quả cho hội thoại này."""
        start = str(self._session_output_dir())
        chosen = QFileDialog.getExistingDirectory(self, tr("cowork.pick_folder_title"), start)
        if not chosen:
            return
        if self.project_id not in ("", "default"):
            # Inside a project, the picked folder becomes THAT project's
            # workspace (its sandbox + shared-knowledge root) — not the
            # global default-output setting.
            from ..core.projects import save_project
            from ..presentation.workspace.project_folder_rules import folder_taken_blocked

            project = self._project()
            if project is not None:
                if folder_taken_blocked(self, chosen, self.project_id):
                    return
                project.output_dir = chosen
                save_project(project)
        else:
            self.ctx.config.cowork["output_dir"] = chosen
            self.ctx.save()
        self._apply_output_folder_label()
        self._refresh_outputs_from_disk()

    def _apply_output_folder_label(self) -> None:
        """Cập nhật nhãn cạnh nút chọn thư mục.

        Chỉ hiện TÊN thư mục; đường dẫn đầy đủ để trong tooltip — bày cả đường dẫn
        ra ngoài chỉ làm rối một giá trị mà người dùng vừa tự chọn.
        """
        full = str(self._session_output_dir())
        # Only the folder NAME is shown beside the button — the full path
        # (still available on hover) reads as noisy clutter for a value the
        # user just picked and already knows the location of.
        name = Path(full).name or full
        if len(name) > _FOLDER_LBL_MAX_CHARS:
            name = name[:_FOLDER_LBL_MAX_CHARS - 1] + "…"
        self.folder_lbl.setText(name)
        self.folder_lbl.setToolTip(full)
        # Text still tracks the active project (tooltip/tests read it), but the
        # label stays hidden — see its creation note above.
        project = self._project()
        if project is not None:
            self.project_lbl.setText(tr("cowork.project_label", name=project.name))
            self.project_lbl.setToolTip(tr("cowork.project_tooltip", name=project.name))
        else:
            self.project_lbl.setText("")
        # Start watching the output folder for new files
        wd = self.workspace_dir()
        if wd:
            self._start_watching(wd)

    # ---- project (workspace) --------------------------------------------
    def _project(self):
        """Project đang gắn với hội thoại này; ``None`` nếu không tìm thấy."""
        from ..core.projects import load_project

        return load_project(self.project_id)

    def set_project(self, project_id: str) -> None:
        """Assign the CURRENT thread to a project (called by the Workspace
        screen's 'New chat in project'). Output folder + shared context follow.

        Also makes this the ACTIVE workspace for per-workspace mode resolution
        and refreshes the routing/auto-run toggles to show THIS workspace's
        modes (so switching projects switches the visible modes)."""
        self.project_id = project_id or "default"
        self.ctx.active_project_id = self.project_id
        for t in (getattr(self, "routing_toggle", None), getattr(self, "autorun_toggle", None)):
            if t is not None:
                t.refresh()
        self._apply_output_folder_label()
        self._refresh_outputs_from_disk()

    def project_knowledge_dir(self):
        """A non-default project's shared-knowledge folder — its workspace
        ROOT. This is now the SAME folder every thread of the project already
        saves its deliverables into (no more per-session sub-folder — see
        _session_output_dir), so ChatPanel._augment's equality check skips the
        separate '[Project files]' scan and the '[Workspace files]' scan alone
        already covers everything in one shared place, Claude-Projects style."""
        if self.project_id in ("", "default"):
            return None
        project = self._project()
        return project.workspace_dir() if project else None

    # Generator/helper scripts are never a Cowork deliverable — keep them out of
    # the Output list entirely (only the final file is shown).
    _INTERMEDIATE_EXTS = {".py", ".pyw", ".js", ".mjs", ".cjs", ".ts",
                          ".sh", ".bat", ".ps1", ".rb", ".pl"}

    def assistant_title(self) -> str:
        """Nhãn hiện trên bong bóng trả lời của màn Cowork."""
        return tr("cowork.assistant_title")

    def _session_output_dir(self):
        """Where this session's deliverables are saved.

        Default: a sub-folder of the configured Output root named by the
        session id (a timestamp — never the chat content), so same-named
        outputs from different sessions don't overwrite each other.

        Once a folder has been EXPLICITLY specified — either "Chọn thư mục
        khác" (see _pick_output_folder) for the default project, or a
        project's own workspace folder — files are saved DIRECTLY into it
        instead, no auto-created per-session sub-folder: the Output box/link
        always points at exactly that folder, and every thread that shares it
        sees the same files (deliverables AND project knowledge together,
        Claude-Projects style). Running turns still get isolated '.turns/<id>'
        sandboxes (unique across every session in this tab — see
        _turn_output_dir/_turn_seq — moved up on success by
        _promote_turn_outputs, which de-dupes by name via _unique_path), so
        concurrent turns/threads sharing one folder never clash.

        Threads of a NON-default project are sandboxed inside that project's
        own workspace: the agent's tools are confined there (ToolContext
        rejects any path escape), and it's a single shared folder for the
        whole project — not one sub-folder per thread."""
        if self.project_id not in ("", "default"):
            project = self._project()
            if project is not None:
                return project.workspace_dir()
        custom = (self.ctx.config.cowork.get("output_dir") or "").strip()
        if custom:
            return Path(custom).expanduser()
        return self.ctx.config.cowork_output_dir() / self.session_id

    def workspace_dir(self):
        """Thư mục agent được phép đọc/ghi trong hội thoại này."""
        return self._session_output_dir()

    def _turn_output_dir(self, turn_id: str):
        """Each running turn writes into its own '.turns/<id>' sandbox so parallel
        turns never clobber each other's files (run_cowork's cleanup diffs the
        folder before/after, which would misfire on a shared dir). On success the
        finished turn's deliverables are moved up to the session root — see
        _cleanup_turn. The dot-prefixed folder is ignored by the Output list
        (which shows only top-level files)."""
        return self._session_output_dir() / ".turns" / turn_id

    def _is_intermediate_output(self, path: str) -> bool:
        """Tệp này có phải file trung gian (do bước dựng sinh ra) không.

        File trung gian không hiện lên ô "Tệp đầu ra" — người dùng chỉ quan tâm
        sản phẩm cuối.
        """
        from pathlib import Path
        return Path(path).suffix.lower() in self._INTERMEDIATE_EXTS

    def _existing_output_names(self):
        """Deliverables already sitting in this session's output folder (from
        earlier, already-finished turns) — the current turn writes into its own
        '.turns/<id>' sandbox, so this never includes its own in-flight files."""
        try:
            return sorted(p.name for p in self._session_output_dir().iterdir()
                          if p.is_file() and not p.name.startswith(".")
                          and not self._is_intermediate_output(str(p)))
        except OSError:
            return []

    def _session_notes(self) -> str:
        # Lets the agent (and the user, without re-uploading) reference/revise a
        # file it made earlier in this same conversation — e.g. "sửa lại tiêu đề
        # trong file báo cáo vừa tạo" — since it can read_file/edit_file/write_file
        # it directly by the exact name listed here.
        """Ghi chú đính kèm vào prompt: danh sách tệp hội thoại này đã tạo.

        Nhờ đó agent (và người dùng, không phải tải lên lại) tham chiếu và sửa được
        tệp nó vừa tạo ở lượt trước — ví dụ "sửa lại tiêu đề trong file báo cáo vừa
        tạo" — vì nó đọc/ghi được tệp đó theo đúng tên liệt kê ở đây.
        """
        names = self._existing_output_names()
        if not names:
            return ""
        listing = ", ".join(names)
        return (
            "[Session context] Files already created earlier in this conversation's output "
            "folder — read/revise them directly by their exact name with read_file/edit_file/"
            "write_file; the user does NOT need to re-upload them if they refer to \"the file "
            f"I made\" / \"file vừa tạo\" or similar: {listing}"
        )

    def _promote_turn_outputs(self, turn_dir, record, session_root) -> None:
        """Move a finished turn's files from its '.turns/<id>' sandbox up to its
        conversation's Output root (``session_root`` — the turn's HOME session, so a
        background turn lands in the right chat even after the user switched away),
        then remove the sandbox. run_cowork already flattened and stripped
        '.scratch'/generator scripts, so the sandbox root holds the final file(s).
        Every top-level file is moved (no extension filtering) so a file the user
        genuinely asked for is never dropped before the sandbox is removed — the
        Output list itself decides what to *show* (see _refresh_outputs_from_disk)."""
        import shutil
        from pathlib import Path

        from ..core.chat_agent import _unique_path

        turn_dir = Path(turn_dir)
        session_root = Path(session_root)
        try:
            if not turn_dir.is_dir() or turn_dir.resolve() == session_root.resolve():
                return
        except OSError:
            return
        session_root.mkdir(parents=True, exist_ok=True)
        remap = {}
        try:
            files = [p for p in turn_dir.iterdir() if p.is_file()]
        except OSError:
            files = []
        for p in files:
            try:
                dest = _unique_path(session_root, p.name)
                p.replace(dest)
                remap[str(p)] = str(dest)
            except OSError:
                pass
        shutil.rmtree(turn_dir, ignore_errors=True)
        # Keep this turn's recorded outputs pointing at the moved files so
        # deleting the message later still finds and removes them.
        if remap and record is not None:
            record["outputs"] = [remap.get(p, p) for p in record.get("outputs", [])]

    # ---- Output box: only the final, successful deliverables ----------
    def register_output(self, path: str) -> None:
        # Suppress live/intermediate updates during a run — the Output box is
        # rebuilt from the surviving files once the turn succeeds (see below).
        """Không làm gì: ô "Tệp đầu ra" của Cowork được dựng lại từ các tệp còn sống
        sau khi lượt chạy THÀNH CÔNG, chứ không cập nhật từng tệp giữa chừng.
        """
        return

    def on_file_written(self, path: str) -> None:
        """Không làm gì: Cowork không cập nhật danh sách tệp theo thời gian thực."""
        return  # no live file updates in Cowork

    def _refresh_outputs_from_disk(self) -> None:
        """Show only the final deliverable files now sitting in the session folder
        (no scripts/intermediate files, no hidden/`.scratch`, no folders)."""
        self.output_section.clear()
        try:
            files = sorted((p for p in self._session_output_dir().iterdir() if p.is_file()),
                           key=lambda p: p.name)
        except OSError:
            return
        for p in files:
            if not p.name.startswith(".") and not self._is_intermediate_output(str(p)):
                self.output_section.add(str(p))
        self.output_changed.emit(str(self._session_output_dir()))

    def new_session(self) -> None:
        # The new thread stays in the CURRENT project (Claude-style).
        """Mở hội thoại mới trong ĐÚNG project đang chọn, rồi trỏ lại thư mục kết quả."""
        super().new_session()
        # Refresh the project/folder labels + watch the new session's folder.
        self._apply_output_folder_label()

    def load_conversation(self, conv) -> None:
        """Mở lại một hội thoại cũ: khôi phục project của nó, dựng lại danh sách tệp
        đầu ra từ đĩa và trỏ lại nhãn thư mục.
        """
        super().load_conversation(conv)    # restores this conversation's project_id
        self._refresh_outputs_from_disk()  # show this session's deliverables from disk
        # Refresh the project/folder labels + watch this conversation's folder.
        self._apply_output_folder_label()

    def refresh_header(self) -> None:
        """Cập nhật các nhãn trên thanh công cụ Cowork.

        Dòng "provider · model" từng nằm ngay sau chữ "Cowork" đã được gỡ: nó
        lặp lại thông tin mà bộ chọn provider ở thanh trên đang hiển thị, và
        chiếm chỗ đắt nhất trên thanh công cụ cho một thứ chỉ để đọc.
        """
        self._apply_output_folder_label()  # picks up edits made via Settings too

    def build_job(self, text: str, messages, out_dir):
        """This turn's job: a frozen request run through the conversation service.

        Since R04-T04 the widget no longer drives the turn loop. Every value a
        turn depends on is read HERE, on the UI thread at submit time, and packed
        into an immutable ``ConversationExecutionRequest`` — so clicking a
        different model or switching workspace mid-answer cannot reach work
        already in flight.
        """
        output_dir = out_dir or self._session_output_dir()
        # The sandbox folder is named by the turn id ('.turns/t3'); with no
        # sandbox the session id identifies the turn well enough for the audit log.
        turn_id = out_dir.name if out_dir is not None else self.session_id
        session_id = self.session_id
        title = self.title
        project_id = self.project_id
        home_output_root = self.workspace_dir()
        # Captured at submit time (UI thread): the Admin-defined agent
        # preset's instructions, if one is selected in the Agent picker.
        agent_prompt = self.admin_agent_prompt()
        # Per-workspace Auto-run override wins, else the global "confirm before
        # running commands" setting. Frozen now, so a Settings change mid-turn
        # cannot flip the rules this turn started under.
        confirm_commands = self.ctx.project_confirm_commands()
        # What the turn is recorded as running on. A routing override (R03) wins
        # over the tab's own picker; '' means the provider's configured default.
        # Informational only — an Admin-agent preset builds its own provider
        # below, so treat these as the record, not the decision.
        provider_id = self._routed_provider or self.ctx.config.active_provider
        model = self._routed_model or self._model or ""

        def job(worker: AgentWorker):
            """Chạy nền một lượt Cowork qua ``ConversationApplicationService`` (R04-T04).

            Sự kiện của service được dịch ngược về khuôn dict cũ để giao diện hiện tại
            không phải sửa.
            """
            from ..application.conversations.core_runtime_adapter import (
                build_cowork_conversation_service,
                legacy_event_sink,
            )
            from ..application.conversations.cowork_turn_request import (
                build_cowork_turn_request,
            )
            from ..application.conversations.turn_runtime import combine_instructions
            from ..core.projects import load_project, project_context_text

            provider = self.build_provider()  # this tab's selected agent/model
            # 🔌 MCP Layer: every tool source flows through MCP now — the
            # external servers configured in Settings AND Microsoft 365 (a
            # built-in MCP server auto-registered while signed in, see
            # AppContext._ms365_builtin_connection / mcp_servers/ms365_server.py).
            extra_tools, extra_exec = self.ctx.build_mcp_tools()
            # Shared project instructions (Claude-Projects style) plus the Admin
            # agent's persona, refreshed each turn so edits in the Workspace
            # screen apply immediately.
            instructions = combine_instructions(
                project_context_text(load_project(project_id)), agent_prompt)
            # Permission Management (Sandbox Security Layer): off by default —
            # matches the pre-existing auto-run behavior. The gate lives on the
            # worker because the UI resolves it from the main thread.
            gate = None
            if confirm_commands:
                gate = worker.new_gate("confirm", agent_role=agent_roles.COWORK)

            service = build_cowork_conversation_service(
                provider, output_dir, worker.emit_event, title=title,
                project_context=instructions, extra_tools=extra_tools,
                extra_executor=extra_exec, security_config=self.ctx.config,
                gate=gate, agent_role=agent_roles.COWORK,
            )
            request = build_cowork_turn_request(
                turn_id=turn_id, session_id=session_id, surface=self.kind,
                project_id=project_id, title=title, messages=messages,
                provider_id=provider_id, model=model, instructions=instructions,
                output_dir=output_dir, home_output_root=home_output_root,
                confirm_commands=gate is not None, agent_role=agent_roles.COWORK,
            )
            # Hand the widget's own list over: _reattach_running_turn replays
            # from it while the turn is still running, and _finalize_turn slices
            # it afterwards, so the service must append into that very object.
            service.execute(request, legacy_event_sink(worker.emit_event),
                            cancel=worker.is_cancelled, messages=messages)
            return {"messages": messages, "turn_dir": str(output_dir)}

        return job

    def _cleanup_turn(self, ctx, ok) -> None:
        """A turn ended (successfully or not): promote whatever files it
        produced up to ITS conversation's Output root, THEN discard the
        (by then empty, or intermediate-only) sandbox.

        This runs the SAME promotion on failure as on success — a turn can
        genuinely create a deliverable (e.g. save_file succeeds) and THEN hit
        an unrelated error later in the same turn (a follow-up tool call, a
        network drop, a rate limit that didn't recover) which raises and
        marks the whole turn as failed. Discarding the sandbox unconditionally
        in that case would silently delete a file the user actually got —
        exactly the "file đã tạo bị xóa" bug. Promoting first is always safe:
        an empty/intermediate-only sandbox just promotes zero files.

        Refresh the visible Output list only when that conversation is the
        one on screen."""
        turn_dir = ctx.get("out_dir")
        home_root = ctx.get("home_out_root")
        live = ctx.get("home_id") == self.session_id and not ctx.get("detached")
        if turn_dir and home_root:
            self._promote_turn_outputs(turn_dir, ctx.get("record"), home_root)
        elif turn_dir:
            import shutil
            shutil.rmtree(turn_dir, ignore_errors=True)
        if live:
            self._refresh_outputs_from_disk()
