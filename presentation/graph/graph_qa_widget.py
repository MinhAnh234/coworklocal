"""GraphQaWidget — the right-side "ask questions about this graph" panel of
GraphRAG (R08-T14, extracted from
``ui/structure_graph_view.py::StructureGraphView``, lines 288-334/342-360
(partial)/647-663/704-955 of the original 1035-line file).

Reads the current graph and scene selection from a
``graph_renderer.py::GraphRenderer`` instance passed at construction
(``renderer.graph``, ``renderer.selected_node_data()``,
``renderer.active_project_id``) and reacts to its
``node_selected``/``graph_rendered``/``raw_json_ready`` signals — this class
has no rendering state of its own, matching how
``presentation/folder/ai_file_editor_dialog.py`` reads
``DocumentPreviewManager`` rather than duplicating file state.

File-content extraction for grounding the answer goes through
``application/workspaces/graph_index_service.py`` (R08-T14 also moved that
out of this file, as pure Python — see its own docstring).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple

from PySide6.QtCore import QUrl, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextBrowser, QVBoxLayout, QWidget

from cowork_local.application.workspaces.graph_index_service import extract_file_contents
from cowork_local.core.worker import AgentWorker
from cowork_local.i18n import tr
from cowork_local.ui.icons import collapse_right_icon, icon
from cowork_local.ui.osutil import open_folder, open_location
from cowork_local.ui.widgets import CollapseStrip


class GraphQaWidget(QWidget):
    """The collapsible pane itself (strip + header + ask row + detail
    browser) — the shell adds ONE widget to its splitter."""

    status_message = Signal(str)
    collapse_changed = Signal(bool)   # so the shell can resize its own splitter

    def __init__(self, ctx, renderer, parent=None):
        """Panel Hỏi đáp bên phải màn GraphRAG.

        Có cache trích xuất vì cùng một node hay bị hỏi lại nhiều lần trong một
        phiên, mà mỗi lần trích lại phải đọc tệp.
        """
        super().__init__(parent)
        self.ctx = ctx
        self._renderer = renderer
        self._ask_worker: Optional[AgentWorker] = None
        self._answer = ""
        self._detail_mode = "idle"   # "answer" | "node" | "idle"
        self._extract_cache: dict = {}
        self._extract_dir = None

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self._strip = CollapseStrip(tr("structure.expand_agent_tooltip"), expand_dir="left")
        self._strip.clicked.connect(lambda: self._set_collapsed(False))
        self._strip.setVisible(False)
        outer.addWidget(self._strip)

        self._panel = QWidget()
        rl = QVBoxLayout(self._panel)
        rl.setContentsMargins(0, 0, 0, 0)
        ag_hdr = QHBoxLayout()
        self._collapse_btn = QPushButton()
        self._collapse_btn.setIcon(collapse_right_icon())
        self._collapse_btn.setFixedWidth(28)
        self._collapse_btn.clicked.connect(lambda: self._set_collapsed(True))
        self._label = QLabel()
        ag_hdr.addWidget(self._collapse_btn)
        ag_hdr.addWidget(self._label, 1)
        rl.addLayout(ag_hdr)

        ask_row = QHBoxLayout()
        self.ask_edit = QLineEdit()
        self.ask_edit.returnPressed.connect(self._ask)
        self._ask_btn = QPushButton()
        self._ask_btn.setIcon(icon("chat"))
        self._ask_btn.setObjectName("primary")
        self._ask_btn.clicked.connect(self._ask)
        ask_row.addWidget(self.ask_edit, 1)
        ask_row.addWidget(self._ask_btn)
        rl.addLayout(ask_row)

        self.detail = QTextBrowser()
        self.detail.setReadOnly(True)
        self.detail.setOpenLinks(False)
        self.detail.anchorClicked.connect(self._on_detail_link)
        rl.addWidget(self.detail, 1)
        outer.addWidget(self._panel, 1)

        renderer.node_selected.connect(self._on_node_selected)
        renderer.graph_rendered.connect(self._preserve_answer)
        renderer.raw_json_ready.connect(self._show_raw_json)
        renderer.project_changed.connect(self.clear_extracts)

        self.retranslate()

    def retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn cho tiêu đề, ô hỏi và tooltip."""
        self._collapse_btn.setToolTip(tr("structure.collapse_agent_tooltip"))
        self._label.setText(tr("structure.agent_header"))
        self.ask_edit.setPlaceholderText(tr("structure.ask_placeholder"))
        self._ask_btn.setText(tr("structure.ask"))
        if self._detail_mode == "idle":
            self.detail.setPlaceholderText(tr("structure.detail_placeholder"))
        self._strip.setToolTip(tr("structure.expand_agent_tooltip"))

    # ---- collapse ------------------------------------------------------------- #
    def _set_collapsed(self, collapsed: bool) -> None:
        """Gập/mở panel hỏi-đáp và báo ra ngoài để vỏ chỉnh lại splitter."""
        self._panel.setVisible(not collapsed)
        self._strip.setVisible(collapsed)
        self.collapse_changed.emit(collapsed)

    # ---- reacting to the renderer ----------------------------------------------- #
    def _on_node_selected(self, data) -> None:
        """Chọn một node trên đồ thị: hiện chi tiết của node đó ở khung dưới."""
        self.detail.setPlainText(f"[{data.kind.upper()}] {data.label}\n\n{data.detail}")
        self._detail_mode = "node"

    def _show_raw_json(self, html_text: str) -> None:
        """Hiện JSON thô của một hội thoại được chọn ở tab Tin nhắn."""
        self.detail.setHtml(html_text)

    def _preserve_answer(self) -> None:
        """Vẽ lại câu trả lời AI sau khi khung chi tiết bị dùng cho việc khác — nếu"""
        if self._detail_mode == "answer" and self._answer.strip():
            self._render_answer()

    # ---- Q&A -------------------------------------------------------------------- #
    @staticmethod
    def _graph_context(graph) -> str:
        """Tóm tắt đồ thị thành văn bản gọn để nhét vào prompt: gom node theo loại,"""
        from collections import defaultdict
        by_kind = defaultdict(list)
        for n in graph.nodes:
            by_kind[n.kind].append(n.label)
        lines = []
        for kind in ("file", "class", "function", "method", "module", "section"):
            items = by_kind.get(kind, [])
            if items:
                lines.append(f"{kind} ({len(items)}): " + ", ".join(items[:60]))
        id2label = {n.id: n.label for n in graph.nodes}
        rels = [f"{id2label.get(e.source, e.source)} -{e.type}-> {id2label.get(e.target, e.target)}"
                for e in graph.edges[:140]]
        if rels:
            lines.append("Relationships (sample):\n" + "\n".join(rels))
        return "\n".join(lines)[:7000]

    def _matched_sources(self, text: str):
        """Các node có tên xuất hiện trong câu trả lời — dùng để gắn link nguồn kiểm"""
        graph = self._renderer.graph
        if graph is None or not text:
            return []
        found: dict = {}
        for n in graph.nodes:
            if not n.path:
                continue
            label = n.label.rstrip("()")
            if len(label) < 3:
                continue
            if n.path not in found and re.search(rf"\b{re.escape(label)}\b", text):
                found[n.path] = (n.kind, n.label, n.detail or n.path)
        return sorted(found.items(), key=lambda kv: kv[1][1].lower())[:12]

    def _linkify_files(self, text: str, sources) -> str:
        """Turn file/entity NAMES mentioned in the answer into clickable
        links that open the file."""
        for path, (kind, label, rel) in sources:
            href = QUrl.fromLocalFile(path).toString(QUrl.ComponentFormattingOption.FullyEncoded)
            tokens = []
            base = Path(path).name
            if base and len(base) >= 3:
                tokens.append(base)
            lab = (label or "").rstrip("()").strip()
            if lab and lab != base and len(lab) >= 3:
                tokens.append(lab)
            for tok in tokens:
                esc = re.escape(tok)
                text = re.sub(rf"`{esc}`", f"[`{tok}`]({href})", text)
                text = re.sub(rf"(?<![\w`/\\.\]\)]){esc}(?![\w`\]\(])", f"[{tok}]({href})", text)
        return text

    def _render_answer(self) -> None:
        """Vẽ câu trả lời dạng markdown kèm danh sách nguồn bấm mở được."""
        text = self._answer
        sources = self._matched_sources(text)
        if sources:
            text = self._linkify_files(text, sources)
            lines = [text, "", "---", f"**{tr('structure.related_sources')}**"]
            for path, (kind, label, rel) in sources:
                href = QUrl.fromLocalFile(path).toString(QUrl.ComponentFormattingOption.FullyEncoded)
                kind_badge = f" [{kind.upper()}]" if kind not in ("file",) else ""
                lines.append(f"- **[{label}⧉]({href})**{kind_badge} — `{rel}`")
            text = "\n".join(lines)
        self.detail.setMarkdown(text)

    def _on_detail_link(self, url: QUrl) -> None:
        """Bấm một link trong khung chi tiết: là tệp thì mở tệp, còn lại mở bằng trình
        duyệt.
        """
        if url.isLocalFile():
            p = url.toLocalFile()
            if Path(p).is_file():
                open_location(p)
            else:
                open_folder(p)

    def _ask(self) -> None:
        """Gửi câu hỏi về đồ thị tới model, chạy ở luồng nền."""
        question = self.ask_edit.text().strip()
        if not question:
            return
        from cowork_local.core.skills import parse_skill_command
        skill_prefix, question, info = parse_skill_command(question)
        if info is not None:
            self.detail.setMarkdown(info)
            self._detail_mode = "answer"
            self.ask_edit.clear()
            return
        graph = self._renderer.graph
        if graph is None:
            self.status_message.emit(tr("structure.scan_first"))
            return
        context = self._graph_context(graph)
        file_paths = self._candidate_file_paths()
        extract_cache = dict(self._extract_cache)
        extract_dir = str(self._extract_tmp_dir())
        self._answer = ""
        self._detail_mode = "answer"
        self.detail.setPlainText("…")
        self.ask_edit.clear()

        active_project_id = self._renderer.active_project_id
        selected_nodes = self._renderer.selected_node_data()
        selected_context = self._selection_context(selected_nodes, graph)

        def job(worker: AgentWorker):
            """Chạy nền: ghép ngữ cảnh đồ thị + nội dung tệp đã trích rồi gọi model."""
            provider = self.ctx.build_active_provider()
            system = self._system_prompt(skill_prefix, active_project_id)
            user_content = f"Graph context:\n{context}"
            if selected_context:
                user_content += f"\n\nSelected node(s) context (focus your answer on these):\n{selected_context}"
            content_block, new_cache = extract_file_contents(file_paths, extract_cache, extract_dir)
            if content_block:
                user_content += ("\n\nExtracted file contents (read these to answer about file "
                                 "details/data; cite the file path):\n" + content_block)
            user_content += f"\n\nQuestion: {question}"
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ]
            from cowork_local.core import agent_roles, audit_log
            ok = True
            try:
                provider.chat(messages, on_text=lambda t: worker.emit_event({"type": "text", "delta": t}),
                              cancel=worker.is_cancelled)
            except Exception:
                ok = False
                raise
            finally:
                audit_log.record("tool_call", "graphrag_ask", ok, question[:500],
                                 agent_role=agent_roles.KNOWLEDGE)
            return {"extracted": new_cache}

        w = AgentWorker(job)
        w.event.connect(self._on_ask_event)
        w.finished_ok.connect(self._on_ask_done)
        w.failed.connect(lambda e: self.detail.setPlainText(f"Error: {e}"))
        self._ask_worker = w
        w.start()

    @staticmethod
    def _selection_context(selected_nodes, graph) -> str:
        """Phần ngữ cảnh thêm cho các node người dùng đang chọn — câu hỏi "cái này là"""
        if not selected_nodes:
            return ""
        node_lines = []
        for nd in selected_nodes:
            node_lines.append(f"- {nd.label} (kind: {nd.kind}, path: {getattr(nd, 'path', '')})")
            if nd.detail:
                node_lines.append(f"  detail: {nd.detail}")
        connected_ids = set()
        for nd in selected_nodes:
            for edge in graph.edges:
                if edge.source == nd.id:
                    connected_ids.add(edge.target)
                elif edge.target == nd.id:
                    connected_ids.add(edge.source)
        connected_nodes = [n for n in graph.nodes if n.id in connected_ids]
        if connected_nodes:
            node_lines.append("\nConnected nodes:")
            for cn in connected_nodes:
                node_lines.append(f"- {cn.label} (kind: {cn.kind})")
        return "\n".join(node_lines)

    @staticmethod
    def _system_prompt(skill_prefix: str, active_project_id: str) -> str:
        """Prompt hệ thống cho khung hỏi-đáp."""
        system = ("You answer questions about a code/document knowledge graph. Use the provided "
                  "graph context AND the extracted file contents to retrieve, synthesize and "
                  "explain the answer. Be concise. Answer ONLY from what is provided (graph "
                  "context + extracted contents) — never invent files, functions, or facts that "
                  "aren't in it.\n\n"
                  "EACH answer MUST include source citations so the user can verify where "
                  "information came from. For every factual claim, file reference, or code "
                  "element you mention, add a citation using this format:\n\n"
                  "  [source: filename.ext, line/section: XXX]\n\n"
                  "Rules for citations:\n"
                  "  1. Cite the EXACT file path from the graph context (use the path field).\n"
                  "  2. For Python files: cite the function/class name and approximate line "
                  "     if available, or the module name.\n"
                  "  3. For document files (.md, .txt): cite the section heading.\n"
                  "  4. For JSON files: cite the key path (e.g. settings > database > host).\n"
                  "  5. Place citations inline after the relevant sentence or fact.\n"
                  "  6. At the end of your answer, add a '---' separator followed by a "
                  "     numbered **Sources cited:** section listing each unique source with "
                  "     its full path so the user can click to open it.\n\n"
                  "Example citation format in text:\n"
                  "  The `process_data()` function handles CSV parsing "
                  "[source: src/utils/parser.py, function: process_data].\n\n"
                  "Example end-of-answer source list:\n"
                  "  ---\n"
                  "  **Sources cited:**\n"
                  "  1. `src/utils/parser.py` — process_data function\n"
                  "  2. `docs/api.md` — Section: Authentication\n")
        if skill_prefix:
            system += "\n\nFollow this skill:\n" + skill_prefix
        if active_project_id:
            from cowork_local.core.projects import load_project, project_context_text
            proj_ctx = project_context_text(load_project(active_project_id))
            if proj_ctx:
                system += "\n\n" + proj_ctx
        return system

    def _on_ask_event(self, ev: dict) -> None:
        """Nhận từng mẩu trả lời đang phát dần và vẽ dần vào khung chi tiết."""
        if ev.get("type") == "text":
            if self._answer == "":
                self.detail.clear()
            self._answer += ev.get("delta", "")
            self.detail.setPlainText(self._answer)

    def _on_ask_done(self, result: dict) -> None:
        # Keep the (temporary) extracted content so repeated questions reuse
        # it without re-extracting — dropped when leaving the tab.
        """Trả lời xong: giữ lại nội dung tệp đã trích để câu hỏi sau không phải trích"""
        if isinstance(result, dict):
            self._extract_cache.update(result.get("extracted", {}) or {})
        self._render_answer()

    # ---- temporary file-content extraction for Q&A -------------------------------- #
    def _candidate_file_paths(self) -> List[str]:
        """File paths to read for a question: the SELECTED file nodes if
        any, else every file node in the graph (capped downstream)."""
        graph = self._renderer.graph
        if graph is None:
            return []
        sel = self._renderer.selected_node_data()
        nodes = sel or list(graph.nodes)
        out, seen = [], set()
        for nd in nodes:
            p = (getattr(nd, "path", "") or "").strip()
            if p and p not in seen and Path(p).is_file():
                seen.add(p)
                out.append(p)
        return out

    def _extract_tmp_dir(self) -> Path:
        """Thư mục tạm chứa nội dung tệp đã trích, tạo lười ở lần cần đầu tiên."""
        if self._extract_dir is None:
            import tempfile
            from cowork_local.config import CONFIG_DIR
            base = CONFIG_DIR / "tmp" / "graphrag_extract"
            base.mkdir(parents=True, exist_ok=True)
            self._extract_dir = Path(tempfile.mkdtemp(dir=str(base)))
        return self._extract_dir

    def clear_extracts(self) -> None:
        """Discard the temporary extracted content (on leaving the tab /
        switching project). The extraction is a scratch aid, never
        persisted."""
        self._extract_cache = {}
        d, self._extract_dir = self._extract_dir, None
        if d is not None:
            import shutil
            shutil.rmtree(d, ignore_errors=True)


__all__ = ["GraphQaWidget"]
