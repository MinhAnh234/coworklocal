"""OfficeDocumentRenderer — HTML/PPTX/Excel/PDF/office-doc preview for
``document_preview_manager.py`` (R08-T12, split out to keep that file under
the 400-line cap; originally ``ui/folder_tab.py``, lines 451-647/679-694 of
the original 1587-line file).

A plain (non-Qt-widget) helper composed BY a ``DocumentPreviewManager``
rather than a widget of its own: these renderers are tightly coupled to the
manager's shared ``QStackedWidget``/toolbar/editor — genuinely one screen's
internal state, not an independent concern — so this is a composition split
to respect the line-count cap, the same way
``presentation/scheduling/kanban_board_widget.py`` composes
``TaskApplicationService`` rather than owning that logic inline.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QTabWidget, QTableWidget, QTableWidgetItem

from cowork_local.application.workspaces.file_preview_helpers import read_text
from cowork_local.core.worker import AgentWorker
from cowork_local.i18n import tr
from cowork_local.presentation.shared import HAS_WEB_ENGINE

try:
    from PySide6.QtPdf import QPdfDocument  # noqa: F401
    from PySide6.QtPdfWidgets import QPdfView  # noqa: F401
    HAS_PDF = True
except Exception:  # pragma: no cover - QtPdf not bundled
    HAS_PDF = False


class OfficeDocumentRenderer:
    """Renders HTML/PPTX/Excel/PDF/office docs into ``owner.stack``.

    ``owner`` is the ``DocumentPreviewManager`` — this class reaches into
    ``owner.stack``/``owner.editor``/``owner.mode_btn``/``owner.ext_btn``/
    ``owner.save_btn``/``owner.doc_view``/``owner.web`` because those widgets
    are shared with the manager's simpler renderers (code/image/binary);
    duplicating them here would mean two stacked widgets fighting over which
    one is "the" preview.
    """

    def __init__(self, owner) -> None:
        """Bộ hiện tài liệu Office.

        Có cache PDF vì mỗi lần chuyển đổi phải gọi LibreOffice — xem lại cùng một
        tệp mà chuyển lại từ đầu thì chờ vài giây mỗi lượt.
        """
        self._owner = owner
        self._engine = None
        self._pdf_view = None
        self._pdf_doc = None
        self._pdf_tmp: Optional[str] = None
        self._pdf_cache: dict = {}
        self._convert_worker = None
        self._xlsx_view = None

    def show_html(self, path: str, mode_preview: bool) -> None:
        """Hiện tệp HTML: xem đã dựng hình hoặc sửa mã nguồn, tuỳ ``mode_preview``."""
        o = self._owner
        o._edit_kind = "html"
        o.mode_btn.setVisible(True)
        o.mode_btn.setChecked(not mode_preview)   # checked = Edit
        o._retranslate_mode_btn()
        if mode_preview:
            from PySide6.QtCore import QUrl
            html = read_text(path)
            engine = self._ensure_engine()
            if engine is not None:
                engine.setHtml(html, QUrl.fromLocalFile(path))
                o.stack.setCurrentWidget(engine)
            else:
                o.web.setHtml(html)
                o.stack.setCurrentWidget(o.web)
            o.save_btn.setVisible(False)
        else:
            o._show_code(path)

    def show_pptx(self, path: str, mode_preview: bool) -> None:
        """PPTX: Preview renders the slides (PDF via LibreOffice); Edit shows the
        deck's text (marker-delimited per box) in the editor."""
        o = self._owner
        o._edit_kind = "pptx"
        o.mode_btn.setVisible(True)
        o.mode_btn.setChecked(not mode_preview)   # checked = Edit
        o._retranslate_mode_btn()
        o.ext_btn.setVisible(True)
        if mode_preview:
            self.show_document(path)                # PDF render of the slides
            o.mode_btn.setVisible(True)             # show_document doesn't touch it
        else:
            from cowork_local.core.pptx_edit import pptx_to_text
            try:
                text = pptx_to_text(path)
            except Exception as exc:  # noqa: BLE001
                text = f"[could not read pptx text: {exc}]"
            o.editor.setReadOnly(False)
            o.editor.load_file(path + ".txt", text)   # .txt → plain highlighting
            o.save_btn.setVisible(True)
            o.stack.setCurrentWidget(o.editor)

    def _ensure_engine(self):
        """Create the QWebEngineView on first HTML preview (only when WebEngine
        is safe to use); otherwise stay on the QTextBrowser fallback."""
        if not HAS_WEB_ENGINE:
            return None
        if self._engine is None:
            try:
                from PySide6.QtWebEngineWidgets import QWebEngineView
                self._engine = QWebEngineView()
                self._owner.stack.addWidget(self._engine)
            except Exception:  # noqa: BLE001
                self._engine = None
        return self._engine

    def toggle_edit_mode(self) -> None:
        """Lật giữa Xem và Sửa cho tệp đang mở (HTML và PowerPoint)."""
        o = self._owner
        if not o.current_file:
            return
        preview = not o.mode_btn.isChecked()   # checked = Edit
        if o._edit_kind == "pptx":
            self.show_pptx(o.current_file, mode_preview=preview)
        else:
            self.show_html(o.current_file, mode_preview=preview)

    def show_excel(self, path: str) -> None:
        """View a spreadsheet as a real TABLE (openpyxl) — one tab per sheet."""
        o = self._owner
        o.ext_btn.setVisible(True)
        try:
            from cowork_local.core.deps import ensure_module
            ensure_module("openpyxl", "openpyxl")
            from openpyxl import load_workbook
            wb = load_workbook(path, read_only=True, data_only=True)
        except Exception:  # noqa: BLE001 - no openpyxl / unreadable → try PDF/text
            self.show_document(path)
            return
        MAX_ROWS, MAX_COLS = 2000, 100
        if self._xlsx_view is None:
            self._xlsx_view = QTabWidget()
            o.stack.addWidget(self._xlsx_view)
        tabs = self._xlsx_view
        while tabs.count():
            w = tabs.widget(0); tabs.removeTab(0); w.deleteLater()
        try:
            for ws in wb.worksheets:
                rows = list(ws.iter_rows(max_row=MAX_ROWS, max_col=MAX_COLS, values_only=True))
                ncols = max((len(r) for r in rows), default=0)
                table = QTableWidget(len(rows), ncols)
                table.setEditTriggers(QTableWidget.NoEditTriggers)
                table.horizontalHeader().setVisible(False)
                for r, row in enumerate(rows):
                    for c, val in enumerate(row):
                        if val is not None:
                            table.setItem(r, c, QTableWidgetItem(str(val)))
                table.resizeColumnsToContents()
                title = ws.title + (" (…)" if (ws.max_row or 0) > MAX_ROWS
                                    or (ws.max_column or 0) > MAX_COLS else "")
                tabs.addTab(table, title)
        finally:
            wb.close()
        if tabs.count() == 0:
            self.show_document(path)
            return
        o.stack.setCurrentWidget(tabs)

    def show_document(self, path: str) -> None:
        """Office docs + PDF are RENDERED via QtPdf — LibreOffice converts
        them to PDF first. Falls back to text extraction when QtPdf/
        LibreOffice aren't available."""
        o = self._owner
        o.ext_btn.setVisible(True)
        suffix = Path(path).suffix.lower()
        if not HAS_PDF:
            self.show_document_text(path)
            return
        if suffix == ".pdf":
            self._render_pdf(path)
            return
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = 0
        cached = self._pdf_cache.get((path, mtime))
        if cached and os.path.exists(cached):
            self._render_pdf(cached)
            return
        from cowork_local.core.doc_extract import convert_to_pdf, find_soffice
        if not find_soffice() and os.name != "nt":
            self.show_document_text(path)
            return
        o.doc_view.setPlainText(tr("folder.converting"))
        o.stack.setCurrentWidget(o.doc_view)
        if self._pdf_tmp is None:
            import tempfile
            self._pdf_tmp = tempfile.mkdtemp(prefix="cowork_folder_pdf_")
        src, out_dir = path, self._pdf_tmp

        def job(worker):
            """Chạy nền: chuyển tài liệu Office sang PDF bằng LibreOffice."""
            return {"src": src, "mtime": mtime, "pdf": convert_to_pdf(src, out_dir)}

        def done(result):
            """Hiện PDF vừa chuyển và ghi vào bộ nhớ đệm theo (đường dẫn, thời điểm sửa).

            Bỏ kết quả nếu người dùng đã chuyển sang tệp khác trong lúc chờ chuyển đổi.
            """
            if result.get("src") != o.current_file:
                return   # user moved on to another file
            pdf = result.get("pdf")
            if pdf:
                self._pdf_cache[(result["src"], result["mtime"])] = pdf
                self._render_pdf(pdf)
            else:
                self.show_document_text(src)

        worker = AgentWorker(job)
        worker.finished_ok.connect(done)
        worker.failed.connect(lambda _e, p=src: self.show_document_text(p))
        self._convert_worker = worker
        worker.start()

    def _ensure_pdf_view(self):
        """Dựng khung xem PDF một lần duy nhất; không có ``QtPdf`` thì trả ``None``
        để chỗ gọi rơi về cách hiện văn bản thuần.
        """
        if not HAS_PDF:
            return None
        if self._pdf_view is None:
            from PySide6.QtPdf import QPdfDocument
            from PySide6.QtPdfWidgets import QPdfView
            self._pdf_doc = QPdfDocument(self._owner)
            self._pdf_view = QPdfView(self._owner)
            self._pdf_view.setDocument(self._pdf_doc)
            try:
                self._pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
                self._pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
            except Exception:  # noqa: BLE001 - enum names vary slightly across versions
                pass
            self._owner.stack.addWidget(self._pdf_view)
        return self._pdf_view

    def _render_pdf(self, pdf_path: str) -> None:
        """Nạp và hiện một tệp PDF; thiếu ``QtPdf`` thì rơi về trích văn bản."""
        view = self._ensure_pdf_view()
        if view is None:
            self.show_document_text(pdf_path)
            return
        self._pdf_doc.load(pdf_path)
        self._owner.stack.setCurrentWidget(view)

    def show_document_text(self, path: str) -> None:
        """Cách dự phòng cuối: trích văn bản từ tài liệu và hiện dưới dạng chữ thuần.

        Dùng khi không có LibreOffice để chuyển PDF, hoặc không có khung xem PDF.
        """
        from cowork_local.core.doc_extract import extract_text
        o = self._owner
        try:
            text, note = extract_text(path)
        except Exception as exc:  # noqa: BLE001
            text, note = None, str(exc)
        body = text if text else tr("folder.doc_unreadable", note=note or "?")
        o.doc_view.setPlainText(body)
        o.stack.setCurrentWidget(o.doc_view)

    def write_pptx(self, content: str, skip_confirm: bool = False) -> bool:
        """Write edited pptx text back into the deck. If the edit REPLACES any
        image, ask the user to confirm first. ``skip_confirm`` is used when
        the image was already confirmed (e.g. just generated). Returns False
        if the user declined."""
        from cowork_local.core import pptx_edit
        o = self._owner
        if not skip_confirm and pptx_edit.image_change_requested(content):
            from PySide6.QtWidgets import QMessageBox
            ok = QMessageBox.question(o, tr("folder.ai_image_confirm_title"),
                                      tr("folder.ai_image_confirm"))
            if ok != QMessageBox.Yes:
                o.status_message.emit(tr("folder.ai_image_declined"))
                return False
        pptx_edit.apply_text_to_pptx(o.current_file, content)
        return True


__all__ = ["OfficeDocumentRenderer", "HAS_PDF"]
