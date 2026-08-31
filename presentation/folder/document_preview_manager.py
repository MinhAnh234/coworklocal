"""DocumentPreviewManager — the view/edit pane of the Folder Explorer
(R08-T12, extracted from ``ui/folder_tab.py::FolderTab``, lines 295-373/
410-449/649-699 of the original 1587-line file: the preview
``QStackedWidget`` + open/save/create/external dispatch. HTML/PPTX/Excel/
PDF/office rendering lives in ``office_document_renderer.py``; the code
editor widget lives in ``code_editor.py`` — both split out to keep this file
under the 400-line cap.

**Closes the R06-T05 loop**: ``application/workspaces/file_workspace_service.
py::FileWorkspaceService`` existed since R06 but had zero production call
sites (confirmed by grep before this task — ``ui/folder_tab.py`` wrote files
with raw ``Path.write_text`` instead). Every plain-text write this class does
(``save``, ``create_new_file``, ``write_content``) now goes through it —
same path-containment check, same auto ``mkdir``, and (new, from
``infrastructure/filesystem/file_tools.py::write_file``) a Python-syntax
warning on a bad ``.py`` write, which the original code never had. A ``.pptx``
save still goes through ``core/pptx_edit.py`` directly — that's a binary
package build, not a text write, and ``FileWorkspaceService`` has no opinion
on it.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QScrollArea, QStackedWidget,
    QTextBrowser, QVBoxLayout, QWidget,
)

from cowork_local.application.workspaces import FileWorkspaceService
from cowork_local.application.workspaces.file_preview_helpers import (
    is_probably_text, pptx_available, read_text,
)
from cowork_local.domain.workspaces.workspace_session import WorkspaceSession
from cowork_local.i18n import tr
from cowork_local.presentation.folder.code_editor import CodeEditor
from cowork_local.presentation.folder.office_document_renderer import OfficeDocumentRenderer
from cowork_local.ui.icons import icon
from cowork_local.ui.libreoffice_view import DOC_SUFFIXES

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico"}
_HTML_SUFFIXES = {".html", ".htm"}
_PPTX_SUFFIXES = {".pptx"}          # text-editable in-app via python-pptx (no PowerPoint)
_EXCEL_SUFFIXES = {".xlsx", ".xlsm"}  # viewed as a real table via openpyxl (no LibreOffice)
_MAX_EDIT_BYTES = 2_000_000        # above this, view read-only / note only


class DocumentPreviewManager(QWidget):
    """View/edit pane: header (file name, Preview⇄Edit toggle, Save, Open
    externally) above a ``QStackedWidget`` that renders whichever preview a
    file's suffix calls for."""

    status_message = Signal(str)
    ai_reset_requested = Signal()   # a DIFFERENT file was opened by the user

    def __init__(self, root: str, parent=None):
        """Khung xem tài liệu.

        Mọi lượt đọc tệp đi qua ``FileWorkspaceService`` nên không thoát ra ngoài
        thư mục gốc, kể cả khi đường dẫn có ``..``.
        """
        super().__init__(parent)
        self._root = root
        self._file_service = FileWorkspaceService(WorkspaceSession.unscoped(Path(root)))
        self._office = OfficeDocumentRenderer(self)
        self._edit_kind: Optional[str] = None   # None | "html" | "pptx"
        self._current_file: Optional[str] = None

        rl = QVBoxLayout(self)
        rl.setContentsMargins(0, 0, 0, 0)

        hdr = QHBoxLayout()
        self.file_label = QLabel("")
        self.file_label.setStyleSheet("font-weight:600;")
        self.file_label.setWordWrap(True)
        hdr.addWidget(self.file_label, 1)
        self.mode_btn = QPushButton()      # Preview⇄Edit toggle (HTML / PPTX)
        self.mode_btn.setCheckable(True)
        self.mode_btn.clicked.connect(self._office.toggle_edit_mode)
        self.mode_btn.setVisible(False)
        hdr.addWidget(self.mode_btn)
        self.save_btn = QPushButton()
        self.save_btn.setIcon(icon("save"))
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self.save)
        self.save_btn.setVisible(False)
        hdr.addWidget(self.save_btn)
        self.ext_btn = QPushButton()
        self.ext_btn.setIcon(icon("upload"))
        self.ext_btn.clicked.connect(self.open_external)
        self.ext_btn.setVisible(False)
        hdr.addWidget(self.ext_btn)
        rl.addLayout(hdr)
        # Exposed so the shell can insert its own AI-panel toggle button into
        # this same header row (between mode_btn and save_btn, matching the
        # original single-class layout) without this class knowing the AI
        # panel exists.
        self.header_layout = hdr

        self.stack = QStackedWidget()
        self._placeholder = QLabel("")
        self._placeholder.setObjectName("hint")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self.stack.addWidget(self._placeholder)                       # 0

        self.editor = CodeEditor()                                    # 1
        self.stack.addWidget(self.editor)

        self.web = QTextBrowser()                                     # 2
        self.web.setOpenExternalLinks(True)
        self.stack.addWidget(self.web)

        self.doc_view = QTextBrowser()                                # 3
        self.doc_view.setObjectName("docPreview")
        self.stack.addWidget(self.doc_view)

        self._img_scroll = QScrollArea()                              # 4
        self._img_scroll.setWidgetResizable(True)
        self._img_label = QLabel("")
        self._img_label.setAlignment(Qt.AlignCenter)
        self._img_scroll.setWidget(self._img_label)
        self.stack.addWidget(self._img_scroll)

        rl.addWidget(self.stack, 1)
        self.retranslate()

    def retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn cho các nút và ô trống."""
        self.save_btn.setText(tr("folder.save"))
        self.ext_btn.setText(tr("folder.open_external"))
        if not self._current_file:
            self._placeholder.setText(tr("folder.select_file"))
        self._retranslate_mode_btn()

    def _retranslate_mode_btn(self) -> None:
        """Nhãn nút chuyển chế độ đổi theo trạng thái: đang xem thì ghi "Sửa" và ngược lại."""
        self.mode_btn.setText(tr("folder.edit") if not self.mode_btn.isChecked()
                              else tr("folder.preview"))

    # ---- public API used by the shell / AI panel --------------------------- #
    @property
    def current_file(self) -> Optional[str]:
        """Đường dẫn tệp đang mở; ``None`` nếu chưa mở tệp nào."""
        return self._current_file

    @property
    def edit_kind(self) -> Optional[str]:
        """Loại nội dung đang sửa ('pptx', 'html', 'text'…); ``None`` nếu đang chỉ xem."""
        return self._edit_kind

    @property
    def root(self) -> str:
        """Thư mục gốc mà mọi thao tác ghi phải nằm bên trong."""
        return self._root

    def set_root(self, root: str) -> None:
        """Đổi thư mục gốc và dựng lại dịch vụ ghi tệp gắn với phạm vi mới."""
        self._root = root
        self._file_service = FileWorkspaceService(WorkspaceSession.unscoped(Path(root)))

    def open_file(self, path: str, reset_ai: bool = True) -> None:
        # Switching to a DIFFERENT file starts a fresh AI-edit conversation
        # (reset_ai=False when the AI itself just CREATED this file — keep
        # that chat). Whether/how to reset is the AI panel's own business —
        # this class only announces that a genuine file switch happened.
        """Mở một tệp, tự chọn cách hiển thị theo đuôi và kích thước.

        Thứ tự ưu tiên: ảnh → HTML → PowerPoint → Excel → tài liệu Office → nhị
        phân (quá lớn hoặc không phải văn bản) → mã nguồn. Đổi sang tệp KHÁC thì
        báo cho panel AI biết để nó bắt đầu hội thoại mới; ``reset_ai=False`` dùng
        khi chính AI vừa tạo ra tệp này — giữ nguyên đoạn chat đang dở.
        """
        if reset_ai and path != self._current_file:
            self.ai_reset_requested.emit()
        self._current_file = path
        self.file_label.setText(path)
        suffix = Path(path).suffix.lower()
        self.mode_btn.setVisible(False)
        self.save_btn.setVisible(False)
        self.ext_btn.setVisible(False)
        self._edit_kind = None
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0

        if suffix in _IMAGE_SUFFIXES:
            self._show_image(path)
        elif suffix in _HTML_SUFFIXES:
            self._office.show_html(path, mode_preview=True)
        elif suffix in _PPTX_SUFFIXES and pptx_available():
            self._office.show_pptx(path, mode_preview=True)
        elif suffix in _EXCEL_SUFFIXES:
            self._office.show_excel(path)
        elif suffix in DOC_SUFFIXES:
            self._office.show_document(path)
        elif size > _MAX_EDIT_BYTES or not is_probably_text(path):
            self._show_binary(path)
        else:
            self._show_code(path)

    def ensure_editable_for_ai(self) -> bool:
        """Make the current file editable in the code editor (switching an
        HTML preview to edit, or loading a text file). Returns False when
        there's no file open or it isn't a text/code file."""
        path = self._current_file
        if not path or not os.path.isfile(path):
            return False
        suffix = Path(path).suffix.lower()
        if suffix in _HTML_SUFFIXES:
            self._office.show_html(path, mode_preview=False)
            return True
        if suffix in _PPTX_SUFFIXES and pptx_available():
            self._office.show_pptx(path, mode_preview=False)
            return True
        if suffix in DOC_SUFFIXES or suffix in _IMAGE_SUFFIXES:
            return False
        if is_probably_text(path):
            self._show_code(path)
            return True
        return False

    def save(self) -> None:
        """Lưu nội dung đang sửa xuống tệp; pptx ghi ngược vào bản trình chiếu."""
        if not self._current_file:
            return
        try:
            if self._edit_kind == "pptx":
                if not self._office.write_pptx(self.editor.toPlainText()):
                    return
            else:
                self._write_plain_text(self._current_file, self.editor.toPlainText())
            self.status_message.emit(tr("folder.saved", name=Path(self._current_file).name))
        except Exception as exc:  # noqa: BLE001
            self.status_message.emit(tr("folder.save_error", err=str(exc)))

    def write_content(self, content: str, skip_image_confirm: bool = False) -> None:
        """Persist AI-confirmed content to disk AND refresh the preview.
        pptx text is written back into the deck (no PowerPoint window)."""
        if not self._current_file:
            return
        try:
            if self._edit_kind == "pptx":
                if not self._office.write_pptx(content, skip_confirm=skip_image_confirm):
                    return
            else:
                self._write_plain_text(self._current_file, content)
        except Exception as exc:  # noqa: BLE001
            self.status_message.emit(tr("folder.save_error", err=str(exc)))
            return
        suffix = Path(self._current_file).suffix.lower()
        if suffix in _HTML_SUFFIXES:
            self._office.show_html(self._current_file, mode_preview=True)
        elif suffix in _PPTX_SUFFIXES:
            self._office.show_pptx(self._current_file, mode_preview=True)

    def create_new_file(self, target: str, content: str) -> Optional[str]:
        """Create ``target`` (relative to the folder root) with ``content``
        and open it — like Cowork's save_file. Refuses paths escaping the
        root (enforced by ``FileWorkspaceService``/``WorkspaceSession``)."""
        root = os.path.normpath(self._root)
        dest = target if os.path.isabs(target) else os.path.join(root, target)
        dest = os.path.normpath(dest)
        try:
            if Path(dest).suffix.lower() in _PPTX_SUFFIXES and pptx_available():
                # A .pptx is a binary package — build a real deck from the
                # marker text (writing text straight to .pptx would corrupt it).
                from cowork_local.core import pptx_edit
                os.makedirs(os.path.dirname(dest) or root, exist_ok=True)
                pptx_edit.create_pptx_from_text(dest, content)
            else:
                self._write_plain_text(dest, content)
        except Exception as exc:  # noqa: BLE001 - OS error, containment error, or pptx build failure
            self.status_message.emit(tr("folder.save_error", err=str(exc)))
            return None
        self.open_file(dest, reset_ai=False)   # show the new file; keep the AI chat
        return dest

    def open_external(self) -> None:
        """Mở tệp đang xem bằng ứng dụng mặc định của hệ điều hành."""
        if self._current_file:
            from cowork_local.ui.osutil import open_location
            open_location(self._current_file)

    # ---- writes ------------------------------------------------------------- #
    def _write_plain_text(self, path: str, content: str) -> None:
        """Write ``content`` to ``path`` (must resolve inside the current
        root) via ``FileWorkspaceService`` — same containment check, ``mkdir``
        and Python-syntax warning the agent's own ``write_file`` tool gets."""
        rel = os.path.relpath(path, self._root)
        result = self._file_service.write_file(rel, content)
        if not result.get("ok"):
            raise OSError(result.get("output") or "write failed")

    # ---- simple renderers (HTML/PPTX/Excel/PDF/office live in
    # office_document_renderer.py) --------------------------------------------- #
    def _show_code(self, path: str) -> None:
        """Hiện tệp trong ô soạn thảo có tô màu cú pháp, cho phép sửa và lưu."""
        text = read_text(path)
        self.editor.setReadOnly(False)
        self.editor.load_file(path, text)
        self.save_btn.setVisible(True)
        self.stack.setCurrentWidget(self.editor)

    def _show_image(self, path: str) -> None:
        """Hiện ảnh; ảnh hỏng hoặc không đọc được thì rơi về khung nhị phân."""
        from PySide6.QtGui import QPixmap
        pix = QPixmap(path)
        if pix.isNull():
            self._show_binary(path)
            return
        self._img_label.setPixmap(pix)
        self._img_label.resize(pix.size())
        self.ext_btn.setVisible(True)
        self.stack.setCurrentWidget(self._img_scroll)

    def _show_binary(self, path: str) -> None:
        """Hiện thông báo "tệp nhị phân" kèm nút mở bằng ứng dụng ngoài."""
        self._placeholder.setText(tr("folder.binary_file"))
        self.ext_btn.setVisible(True)
        self.stack.setCurrentWidget(self._placeholder)


__all__ = ["DocumentPreviewManager"]
