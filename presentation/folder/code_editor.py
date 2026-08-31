"""CodeEditor — the VS-Code-style code/text editor widget (R08-T12, split
out of ``document_preview_manager.py`` to keep that file under the 400-line
cap; originally ``ui/folder_tab.py``, lines 61-236 of the original
1587-line file: the Pygments token-colour helper, ``PygmentsHighlighter``,
``_LineNumbers``, ``CodeEditor``).
"""
from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import QPlainTextEdit, QWidget

from cowork_local.theme import current_palette

_MAX_HIGHLIGHT_CHARS = 300_000     # skip colouring huge files (keeps typing snappy)


# ── VS-Code-Dark+-ish token palette ────────────────────────────────────────
def _fmt(color: str, *, italic: bool = False, bold: bool = False) -> QTextCharFormat:
    """Dựng một định dạng ký tự cho bộ tô màu cú pháp."""
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if italic:
        f.setFontItalic(True)
    if bold:
        f.setFontWeight(QFont.Bold)
    return f


class PygmentsHighlighter(QSyntaxHighlighter):
    """Colour the whole document with Pygments and apply per-block. Re-lexes the
    full text (debounced) so multi-line strings/comments colour correctly."""

    def __init__(self, document):
        """Tô màu cú pháp bằng Pygments.

        Tô lại sau một nhịp trễ (``QTimer`` chạy một lần) thay vì ngay mỗi phím: gõ
        nhanh trong file lớn mà tô đồng bộ thì giao diện khựng.
        """
        super().__init__(document)
        from pygments.lexers.special import TextLexer
        self._lexer = TextLexer(stripnl=False)
        self._ranges: list[tuple[int, int, QTextCharFormat]] = []
        self._rules = self._build_rules()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._retokenize)
        document.contentsChanged.connect(self._timer.start)

    @staticmethod
    def _build_rules():
        """Dựng bảng ánh xạ loại token của Pygments sang màu theo theme đang dùng."""
        from pygments.token import (
            Comment, Error, Keyword, Name, Number, Operator, Punctuation, String,
        )
        p = current_palette()
        return [
            (Comment, _fmt(p.code_comment, italic=True)),
            (Keyword.Type, _fmt(p.code_type)),
            (Keyword, _fmt(p.code_keyword)),
            (Name.Function, _fmt(p.code_func)),
            (Name.Class, _fmt(p.code_type)),
            (Name.Decorator, _fmt(p.code_func)),
            (Name.Builtin, _fmt(p.code_type)),
            (Name.Tag, _fmt(p.code_keyword)),
            (Name.Attribute, _fmt(p.code_attr)),
            (String.Doc, _fmt(p.code_comment, italic=True)),
            (String, _fmt(p.code_string)),
            (Number, _fmt(p.code_number)),
            (Operator, _fmt(p.code_fg)),
            (Punctuation, _fmt(p.code_fg)),
            (Error, _fmt(p.code_error)),
        ]

    def set_filename(self, filename: str, text: str = "") -> None:
        """Chọn bộ phân tích cú pháp theo đuôi tệp; không nhận ra thì tắt tô màu."""
        from pygments.lexers import get_lexer_for_filename, guess_lexer
        from pygments.lexers.special import TextLexer
        from pygments.util import ClassNotFound
        try:
            self._lexer = get_lexer_for_filename(filename, stripnl=False)
        except ClassNotFound:
            try:
                self._lexer = guess_lexer(text) if text.strip() else TextLexer()
            except ClassNotFound:
                self._lexer = TextLexer(stripnl=False)
        self._retokenize()

    def _fmt_for(self, tok):
        """Định dạng của một token; leo dần lên token cha cho tới khi khớp một luật."""
        for ttype, fmt in self._rules:
            if tok in ttype:
                return fmt
        return None

    def _retokenize(self) -> None:
        """Phân tích lại toàn bộ tài liệu và ghi nhớ định dạng cho từng dòng.

        Pygments phân tích theo cả tệp chứ không theo từng dòng, nên không thể
        tô đúng nếu chỉ nhìn một dòng — ví dụ chuỗi nhiều dòng hay khối chú thích.
        """
        from pygments import lex
        text = self.document().toPlainText()
        self._ranges = []
        if len(text) <= _MAX_HIGHLIGHT_CHARS:
            pos = 0
            for tok, val in lex(text, self._lexer):
                fmt = self._fmt_for(tok)
                if fmt is not None and val:
                    self._ranges.append((pos, pos + len(val), fmt))
                pos += len(val)
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:  # noqa: N802 - Qt override
        """Áp định dạng đã tính sẵn cho một dòng. Qt gọi hàm này cho từng dòng hiện trên màn."""
        if not self._ranges:
            return
        bstart = self.currentBlock().position()
        bend = bstart + len(text)
        for start, end, fmt in self._ranges:
            if end <= bstart or start >= bend:
                continue
            s = max(start, bstart) - bstart
            e = min(end, bend) - bstart
            if e > s:
                self.setFormat(s, e - s, fmt)


class _LineNumbers(QWidget):
    """Máng số dòng vẽ bên trái ô soạn thảo."""
    def __init__(self, editor):
        """Dải số dòng bên trái ô soạn mã."""
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        """Bề rộng máng số dòng, do ô soạn thảo tính theo số chữ số của dòng cuối."""
        return QSize(self._editor.line_number_width(), 0)

    def paintEvent(self, event):  # noqa: N802
        """Nhờ ô soạn thảo vẽ — nó mới biết dòng nào đang hiện ở đâu."""
        self._editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    """A dark, monospaced editor with a line-number gutter + Pygments colouring —
    the Sublime/VS-Code look for viewing & editing source files."""

    def __init__(self):
        """Ô soạn mã: phông đều, không tự xuống dòng, tab rộng 4 ký tự.

        Không tự xuống dòng là cố ý — mã bị bẻ dòng thì lệch thụt đầu dòng và khó
        đọc hơn là phải cuộn ngang.
        """
        super().__init__()
        self.setObjectName("codeEditor")
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        font = QFont("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(10)
        self.setFont(font)
        self._gutter = _LineNumbers(self)
        self.blockCountChanged.connect(lambda _=0: self._update_gutter_width())
        self.updateRequest.connect(self._on_update_request)
        self._highlighter = PygmentsHighlighter(self.document())
        self._update_gutter_width()

    def line_number_width(self) -> int:
        """Bề rộng cần cho máng số dòng, tính theo số chữ số của dòng cuối cùng."""
        digits = max(2, len(str(max(1, self.blockCount()))))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_gutter_width(self) -> None:
        """Chừa lề trái đúng bằng bề rộng máng số dòng."""
        self.setViewportMargins(self.line_number_width(), 0, 0, 0)

    def _on_update_request(self, rect, dy: int) -> None:
        """Cuộn hoặc vẽ lại vùng nào thì máng số dòng cuộn/vẽ lại đúng vùng đó."""
        if dy:
            self._gutter.scroll(0, dy)
        else:
            self._gutter.update(0, rect.y(), self._gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_gutter_width()

    def resizeEvent(self, event):  # noqa: N802
        """Đổi kích thước thì đặt lại hình chữ nhật của máng số dòng."""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._gutter.setGeometry(QRect(cr.left(), cr.top(), self.line_number_width(), cr.height()))

    def paint_line_numbers(self, event) -> None:
        """Vẽ số của các dòng đang hiện trên màn, bỏ qua dòng bị gập hoặc nằm ngoài khung."""
        p = current_palette()
        painter = QPainter(self._gutter)
        painter.fillRect(event.rect(), QColor(p.code_gutter_bg))
        block = self.firstVisibleBlock()
        num = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        painter.setPen(QColor(p.code_gutter_fg))
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(0, int(top), self._gutter.width() - 6,
                                 self.fontMetrics().height(), Qt.AlignRight,
                                 str(num + 1))
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            num += 1

    def load_file(self, path: str, text: str) -> None:
        """Nạp nội dung tệp vào ô soạn thảo và bật tô màu theo đuôi tệp."""
        self.setPlainText(text)
        self._highlighter.set_filename(path, text)


__all__ = ["CodeEditor", "PygmentsHighlighter"]
