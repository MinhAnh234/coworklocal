"""Màn giới thiệu của khung chat khi hội thoại còn rỗng.

Bấm "Cuộc trò chuyện mới" trước đây để lại một khung trắng: không có gì nói
người dùng đang làm trong project nào, thư mục có bao nhiêu tệp, hay bắt đầu từ
đâu. Đây là trạng thái RỖNG — một trong bốn trạng thái mà mọi khung dữ liệu phải
có (xem ``agent/checklist/ux_review.md``), và là trạng thái duy nhất người dùng
nhìn thấy trước khi họ gõ chữ đầu tiên.

Bốn thẻ gợi ý ĐIỀN vào ô nhập chứ không gửi luôn: câu gợi ý là điểm bắt đầu, và
người dùng gần như luôn cần thêm chi tiết của riêng họ trước khi gửi. Gửi ngay
sẽ tiêu một lượt gọi model cho một câu hỏi chung chung.

Dấu trang trí phía trên lời chào không bấm được — nó là một dấu hiệu thị giác,
không phải nút. Một nút không làm gì tệ hơn không có nút.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget,
)

from ...i18n import on_language_changed, tr
from ...ui.icons import icon

#: Width of the four-card block. A FLOOR for the cap, not a fixed number: the
#: block never gets narrower than this, but the cap grows when the text needs
#: more room. One number measured against English at 100% scale is exactly how
#: the titles end up clipped in Vietnamese and Japanese (``qt_pitfalls.md`` P02).
_GRID_WIDTH_FLOOR = 460

#: (khoá tiêu đề, khoá mô tả, khoá câu gợi ý, tên icon) cho từng thẻ.
_CARDS = (
    ("welcome.card_docs", "welcome.card_docs_sub", "welcome.prompt_docs", "file"),
    ("welcome.card_data", "welcome.card_data_sub", "welcome.prompt_data", "table"),
    ("welcome.card_schedule", "welcome.card_schedule_sub", "welcome.prompt_schedule", "schedule"),
    ("welcome.card_graph", "welcome.card_graph_sub", "welcome.prompt_graph", "graph"),
)


class _Card(QPushButton):
    """Một thẻ gợi ý: icon, tiêu đề, và một dòng mô tả bên dưới."""

    def __init__(self, title_key: str, sub_key: str, icon_name: str,
                 parent: QWidget | None = None) -> None:
        """Thẻ gợi ý. Là ``QPushButton`` để có sẵn hover, focus và bàn phím."""
        super().__init__(parent)
        self._title_key = title_key
        self._sub_key = sub_key
        self.setObjectName("welcomeCard")
        self.setCursor(Qt.PointingHandCursor)
        # Vertically it must be able to GROW: QPushButton defaults to Fixed, so
        # a card whose description fits on one line was centred inside a row as
        # tall as its two-line neighbour — two cards side by side, staggered and
        # of different heights.
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(10)

        self._icon = QLabel()
        self._icon.setPixmap(icon(icon_name).pixmap(18, 18))
        self._icon.setAlignment(Qt.AlignTop)
        row.addWidget(self._icon)

        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(2)
        self.title_label = QLabel()
        self.title_label.setObjectName("welcomeCardTitle")
        self.sub_label = QLabel()
        self.sub_label.setObjectName("hint")
        self.sub_label.setWordWrap(True)
        col.addWidget(self.title_label)
        col.addWidget(self.sub_label)
        row.addLayout(col, 1)

        self.retranslate()

    # ---- size: taken from the child layout, not from the button's own text -- #
    # QPushButton computes sizeHint/minimumSizeHint from ITS OWN text and icon
    # and ignores the child layout. This card leaves both of those empty on
    # purpose (the two QLabels below draw the text; a non-empty text() prints
    # on top of them), so the button reported 54x15 while its layout asked for
    # 258x48 — the two QLabels and the icon cell were handed 0px of height, and
    # what the user saw was four empty frames with no text and no icon. The two
    # overrides below report the size the content actually needs.

    def sizeHint(self):  # noqa: N802 - Qt override
        """Size the card's own content needs, not the (empty) button label."""
        return self.layout().sizeHint()

    def minimumSizeHint(self):  # noqa: N802 - Qt override
        """Floor comes from the child layout, for the same reason."""
        return self.layout().minimumSize()

    def retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn."""
        self.title_label.setText(tr(self._title_key))
        self.sub_label.setText(tr(self._sub_key))
        # Nhãn của chính QPushButton để rỗng — chữ do hai QLabel bên trong vẽ,
        # đặt cả hai chỗ sẽ in đè lên nhau.
        self.setAccessibleName(tr(self._title_key))
        # New text means a new content size — Japanese and Vietnamese are not
        # the same length, and sizeHint is computed from those two QLabels.
        self.updateGeometry()


class ChatWelcome(QWidget):
    """Trạng thái rỗng của khung chat: lời chào, dòng bối cảnh, bốn thẻ gợi ý."""

    #: Người dùng chọn một thẻ. Mang theo câu gợi ý để chỗ nhận điền vào ô nhập.
    suggestion_picked = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Dựng màn giới thiệu. Chữ được điền qua :meth:`refresh`."""
        super().__init__(parent)
        self.setObjectName("chatWelcome")
        self._user_name = ""
        self._meta_parts: list = []

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.addStretch(1)

        mark_row = QHBoxLayout()
        mark_row.addStretch(1)
        self._mark = QLabel()
        self._mark.setObjectName("welcomeMark")
        self._mark.setPixmap(icon("sparkle").pixmap(20, 20))
        self._mark.setAlignment(Qt.AlignCenter)
        self._mark.setFixedSize(38, 38)
        mark_row.addWidget(self._mark)
        mark_row.addStretch(1)
        root.addLayout(mark_row)
        root.addSpacing(14)

        self.greeting_label = QLabel()
        self.greeting_label.setObjectName("welcomeGreeting")
        self.greeting_label.setAlignment(Qt.AlignCenter)
        root.addWidget(self.greeting_label)

        self.meta_label = QLabel()
        self.meta_label.setObjectName("hint")
        self.meta_label.setAlignment(Qt.AlignCenter)
        root.addWidget(self.meta_label)
        root.addSpacing(18)

        grid_row = QHBoxLayout()
        grid_row.addStretch(1)
        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(10)
        self.cards: list = []
        for i, (title_key, sub_key, prompt_key, icon_name) in enumerate(_CARDS):
            card = _Card(title_key, sub_key, icon_name)
            card.clicked.connect(
                lambda _checked=False, key=prompt_key: self.suggestion_picked.emit(tr(key)))
            self._grid.addWidget(card, i // 2, i % 2)
            self.cards.append(card)
        self._apply_grid_width()
        grid_row.addWidget(self._grid_host)
        grid_row.addStretch(1)
        root.addLayout(grid_row)

        root.addStretch(2)

        on_language_changed(self._retranslate)

    def _apply_grid_width(self) -> None:
        """Cap the card block at the wider of the design width and what text needs.

        Recomputed on every language change: ``vi`` and ``ja`` labels are not
        the same length as ``en``, and a cap fixed at build time clips whichever
        language happens to be longer.
        """
        self._grid_host.setMaximumWidth(
            max(_GRID_WIDTH_FLOOR, self._grid.sizeHint().width()))

    # ---- nội dung ----------------------------------------------------------

    def refresh(self, user_name: str = "", project: str = "",
                files: int = -1) -> None:
        """Cập nhật lời chào và dòng bối cảnh.

        ``files`` bằng ``-1`` nghĩa là KHÔNG BIẾT, và phần đó bị bỏ khỏi dòng
        meta — thà thiếu một mảnh còn hơn hiện số 0 mà người dùng vừa thấy có
        tệp trong thư mục.

        Không hiện số skill đang bật: nó không giúp người dùng quyết định gõ gì
        vào ô nhập, mà lại chiếm một phần ba của dòng bối cảnh.
        """
        self._user_name = (user_name or "").strip()
        parts = []
        if (project or "").strip():
            parts.append(tr("welcome.meta_project", name=project.strip()))
        if files >= 0:
            parts.append(tr("welcome.meta_files", n=files))
        self._meta_parts = parts
        self._retranslate()

    def _retranslate(self) -> None:
        """Áp lại chữ theo ngôn ngữ đang chọn."""
        if self._user_name:
            self.greeting_label.setText(tr("welcome.greeting", name=self._user_name))
        else:
            self.greeting_label.setText(tr("welcome.greeting_anon"))
        self.meta_label.setText(" · ".join(self._meta_parts))
        self.meta_label.setVisible(bool(self._meta_parts))
        for card in self.cards:
            card.retranslate()
        self._apply_grid_width()
