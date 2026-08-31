"""Tệp đính kèm của một lượt chat — R08-T03.

Đọc nội dung tệp người dùng kèm vào rồi ghép vào câu hỏi. Ba thứ đáng
chú ý:

* ``_enforce_attachment_security`` chạy TRƯỚC khi nội dung vào ngữ cảnh
  model — đây là một trong ba tầng kiểm của R09.
* ``_attach_char_limit`` cắt bớt tệp quá dài; không cắt thì một tệp log
  vài chục MB đủ làm hỏng cả lượt.
* Kèm cả thư mục thì chỉ lấy DANH SÁCH tệp, không đọc nội dung từng cái.
"""
from __future__ import annotations

from pathlib import Path
from typing import List
from PySide6.QtCore import Qt
from ...core.worker import AgentWorker
from ...i18n import tr
from ...ui.osutil import is_image


class AttachmentMixin:
    """Trộn vào ChatPanel."""

    def _on_attachments_added(self, paths: List[str]) -> None:
        # Push attachments into the Input box as soon as they're attached.
        """Tệp vừa được đính kèm: đưa luôn vào mục "Tệp đầu vào" để người dùng thấy ngay."""
        for p in paths:
            self.input_section.add(p)

    def _on_attachment_removed(self, path: str) -> None:
        # A file added by mistake was removed in the composer — drop it from the
        # Input panel too (only matters before the message is sent).
        """Gỡ tệp đính kèm nhầm khỏi cả mục "Tệp đầu vào" (chỉ có ý nghĩa trước khi gửi)."""
        self.input_section.remove(path)

    def _attach_char_limit(self) -> int:
        """Per-file content cap (characters) from the Settings token limit
        (~4 chars/token)."""
        try:
            tokens = int(self.ctx.config.data.get("attachments", {}).get("max_tokens", 500000))
        except (TypeError, ValueError):
            tokens = 500000
        return max(1000, tokens) * 4

    def _augment(self, text: str, attachments: List[str], notify=None) -> str:
        """Embed attachment paths AND their extracted contents into the prompt so
        the agent actually reads and analyses each attached file.

        Additionally, scans the workspace/output folder for existing files and
        loads them as input data so the agent can read/process them automatically.

        ``notify``, if given, is called with UI-visible events (a live "reading
        page X/Y" progress notice, and a warning when a file's content could not
        be read) instead of failures being silently handed to the model as an
        opaque inline note."""
        has_attachments = bool(attachments)
        limit = self._attach_char_limit()
        lines = [text] if text else []

        # --- User-attached files ---
        if has_attachments:
            lines.append("\n[Attachments] — read and use these files to answer the request:")
            for p in attachments:
                lines.extend(self._read_one_attachment(p, limit, notify))

        # --- Auto-load existing workspace/output folder files as input data ---
        # This is what makes "📁 Chọn thư mục khác" useful as an INPUT folder
        # too: every file already in the chosen folder is read and embedded so
        # the agent can act on their contents without manual attaching.
        workspace = self.workspace_dir()
        max_files = int(self.ctx.config.data.get("attachments", {})
                        .get("max_files", 10) or 0)
        if workspace is not None:
            lines.extend(self._folder_input_lines(
                workspace,
                "[Workspace files] — existing files in output folder, "
                "read and use as input data. The user expects you to "
                "process these files automatically:",
                limit, max_files, notify))

        # --- Project knowledge (Claude-Projects style) ---
        # Only scanned separately when it's a DIFFERENT folder from the
        # session's own workspace — for Cowork the two are now the same
        # folder (a project has one shared workspace, no per-thread
        # sub-folder), so this never double-scans the same directory.
        knowledge = self.project_knowledge_dir()
        if knowledge is not None and knowledge != workspace:
            lines.extend(self._folder_input_lines(
                knowledge,
                "[Project files] — shared knowledge files of this project, "
                "available to every conversation in it. Read and use them "
                "as context for the request:",
                limit, max_files, notify))

        return "\n".join(lines)

    def _folder_input_lines(self, folder: Path, header: str, limit: int,
                            max_files: int, notify=None) -> list:
        """Embed a folder's readable files into the prompt — recursing into
        every sub-folder, any depth, not just the top level, so files placed
        in nested folders are read and processed too (same per-message file
        cap as manual attachments — Settings → Attachments → max files;
        0 = unlimited — so a folder with dozens of files can't blow the
        context window)."""
        from ...core.doc_extract import find_input_files

        out: list = []
        shown, total = find_input_files(folder, self._INPUT_EXTS, max_files)
        if shown:
            out.append("\n" + header)
            for f in shown:
                out.extend(self._read_one_attachment(str(f), limit, notify))
        if total > len(shown):
            skipped = total - len(shown)
            out.append(f"…({skipped} more files in the folder were not "
                       "loaded — per-message attachment limit; mention a "
                       "file by name if the user asks about it)")
            if notify is not None:
                notify({"type": "notice", "level": "warning",
                        "text": tr("chat.workspace_files_capped",
                                   shown=len(shown), total=total)})
        return out

    def _read_one_attachment(self, path: str, limit: int, notify=None) -> list:
        """Read and format one attachment/workspace file. Returns list of lines.

        Handles every file type: images (noted with path), MS Office / PDF /
        OpenDocument / text (extracted), and ZIP archives — which are auto-
        extracted into the workspace and their contents read + processed."""
        name = Path(path).name
        result = []
        if is_image(path):
            result.append(f"- {name} (image at {path})")
            return result
        from ...core.doc_extract import is_zip
        if is_zip(path):
            result.extend(self._read_zip_attachment(path, name, limit, notify))
            return result

        def progress(page: int, total: int, _name=name) -> None:
            """Báo tiến độ trích nội dung, chỉ với tệp nhiều trang — tệp một trang thì dòng
            tiến độ chỉ làm nhiễu.
            """
            if notify is not None and total > 1:
                notify({"type": "notice", "level": "progress",
                        "text": tr("chat.reading_progress", name=_name, page=page, total=total)})

        content, note = self._read_attachment_text(path, progress=progress)
        if content is None:
            result.append(f"- {name} ({note}; located at {path})")
            if notify is not None:
                notify({"type": "notice", "level": "warning",
                        "text": tr("chat.attachment_failed", name=name, note=note)})
            return result
        self._enforce_attachment_security(name, content)   # raises SecurityBlocked on a violation
        extra = ""
        if len(content) > limit:
            content = content[:limit]
            extra = f"\n…(truncated to ~{limit // 4} tokens)…"
        result.append(f"- {name} ({path})")
        result.append(f"\n--- Content of {name} ---\n{content}{extra}\n--- end of {name} ---")
        return result

    def _read_zip_attachment(self, path: str, name: str, limit: int, notify=None) -> list:
        """Auto-extract a .zip into the workspace and read+process its files, so
        an attached archive is unpacked and its contents used automatically."""
        from ...core.doc_extract import extract_archive
        ws = self.workspace_dir()
        dest = (Path(ws) if ws is not None else Path(path).parent) / Path(name).stem
        files = extract_archive(path, dest)
        result = [f"- {name} (archive) — extracted {len(files)} file(s) into the workspace at "
                  f"{dest}. Read/edit them there as needed."]
        if self.workspace_dir() is not None:
            self.output_changed.emit(str(self.workspace_dir()))   # let the graph/folder refresh
        max_files = int(self.ctx.config.data.get("attachments", {}).get("max_files", 10) or 0)
        shown = files[:max_files] if max_files else files
        for f in shown:
            result.extend(self._read_one_attachment(str(f), limit, notify))
        if max_files and len(files) > max_files:
            result.append(f"- …and {len(files) - max_files} more file(s) in {dest} "
                          "(not inlined; open/read them from the workspace as needed).")
        return result

    def _enforce_attachment_security(self, filename: str, content: str) -> None:
        """Agent Security's attachment layer (Settings → 🛡 Agent Security) —
        scans extracted file content for malicious payloads BEFORE it enters
        the model's context. No-op when disabled. Raises SecurityBlocked
        (propagates out of _augment → the worker job → AgentWorker.failed,
        which the panel shows as a chat error) on a violation."""
        sec = self.ctx.config.data.get("agent_security", {})
        if not sec.get("enabled") or not sec.get("validate_attachments", True):
            return
        from ...core.agent_security import SecurityBlocked, combined_rules_text, validate_attachment
        from ...core.agent_security_alert import notify_admin

        rules_text = combined_rules_text(self.ctx.config)
        verdict = validate_attachment(self.build_provider(), filename, content, rules_text)
        if verdict.allowed:
            return
        notify_admin(self.ctx.config, verdict, detail=f"file: {filename}")
        raise SecurityBlocked(verdict)

    @staticmethod
    def _read_attachment_text(path: str, progress=None):
        """Best-effort text extraction so the agent can read the attachment.
        Returns (text, note); text is None when nothing readable was found.

        Delegates to core.doc_extract, which parses docx/xlsx/pptx/odf directly
        (stdlib, no extra packages), uses pypdf for PDFs (reporting per-page
        ``progress`` for multi-page files), and falls back to a headless
        LibreOffice conversion for anything else."""
        from ...core.doc_extract import extract_text

        return extract_text(path, progress=progress)

    def project_knowledge_dir(self):
        """Folder of project-level shared knowledge files (None = no project
        knowledge). Overridden by the Cowork tab for non-default projects."""
        return None
