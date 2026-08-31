"""Dải nút chọn một trong nhiều — tách khỏi ``ui/widgets.py``.

Thay ``QComboBox`` ở những chỗ chỉ có hai đến bốn lựa chọn và người dùng nên
thấy hết cùng lúc: ngôn ngữ và giao diện trong Cài đặt. Mở một danh sách xổ
xuống chỉ để biết trong đó có gì là một cú bấm thừa.

Tách ra vì hai lẽ. Một, ``ui/widgets.py`` đã chạm đúng trần nợ cũ của cổng LOC
nên không nhận thêm được dòng nào. Hai, chỗ này có một luật riêng đáng đứng
một mình: bề rộng nút phải chừa sẵn cho chữ IN ĐẬM — xem
:meth:`SegmentedControl._reserve_bold_width`.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class SegmentedControl(QWidget):
    """Two-to-four choices shown side by side instead of hidden in a drop-list.

    Exposes the slice of the QComboBox API this app's settings code uses
    (addItem / findData / currentData / setCurrentIndex / currentIndexChanged),
    so it drops into an existing form without touching the save/load paths.
    """

    currentIndexChanged = Signal(int)

    #: Độ đậm mà ``theme/qss.py`` áp cho nút đang chọn
    #: (``QPushButton#segItem:checked { font-weight: 600 }``). Đổi ở QSS thì
    #: phải đổi cả ở đây, nếu không chữ lại bị cắt.
    _CHECKED_WEIGHT = QFont.DemiBold

    def __init__(self, parent=None):
        """Dải nút chọn một trong nhiều — thay ``QComboBox`` khi chỉ có vài lựa chọn và
        nên thấy hết cùng lúc.
        """
        super().__init__(parent)
        self._data: list = []
        self._buttons: list = []
        self._current = -1
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._lay = lay
        lay.addStretch(1)

    def addItem(self, text: str, data=None) -> None:  # noqa: N802 - Qt-style name
        """Thêm một lựa chọn kèm dữ liệu đi kèm."""
        btn = QPushButton(text)
        btn.setObjectName("segItem")
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        index = len(self._buttons)
        btn.clicked.connect(lambda _c=False, i=index: self.setCurrentIndex(i))
        self._lay.insertWidget(index, btn)
        self._buttons.append(btn)
        self._data.append(data)
        self._reserve_bold_width(btn)
        if self._current < 0:
            self.setCurrentIndex(0)

    @staticmethod
    def _reserve_bold_width(btn: QPushButton) -> None:
        """Chừa sẵn bề rộng cho chữ khi nút được chọn và bị in đậm.

        ``QPushButton`` tính ``sizeHint()`` theo phông ĐANG dùng, tức phông
        thường. Nhưng QSS lại đặt ``font-weight: 600`` cho nút đang chọn, và
        chữ đậm rộng hơn chữ thường — nên đúng lúc một mục được chọn thì nó
        không còn đủ chỗ và Qt cắt bớt chữ đi.

        Nhãn càng dài, thiếu càng nhiều: đo trên bản 30/08 thì "Tiếng Việt"
        thiếu 2px, "English" 2px, còn "Tự động (theo hệ thống)" thiếu tới 7px.
        Tiếng Việt lộ rõ nhất vì nó vừa là nhãn dài vừa có dấu, và với người
        dùng tiếng Việt thì nó luôn là mục ĐANG được chọn.

        Cách đo: lấy phần khung (viền + padding do QSS quy định) bằng cách trừ
        bề rộng chữ khỏi ``sizeHint()``, rồi cộng lại bề rộng của chính chữ ấy
        ở độ đậm khi được chọn. Không viết cứng con số padding nào — QSS đổi
        thì phép đo tự theo.
        """
        btn.ensurePolished()
        text = btn.text()
        normal = btn.font()
        chrome = btn.sizeHint().width() - QFontMetrics(normal).horizontalAdvance(text)
        bold = QFont(normal)
        bold.setWeight(SegmentedControl._CHECKED_WEIGHT)
        btn.setMinimumWidth(chrome + QFontMetrics(bold).horizontalAdvance(text))

    def findData(self, value) -> int:  # noqa: N802
        """Chỉ số của lựa chọn mang dữ liệu ``value``; -1 nếu không có."""
        return self._data.index(value) if value in self._data else -1

    def currentData(self):  # noqa: N802
        """Dữ liệu của lựa chọn đang chọn; ``None`` nếu chưa chọn gì."""
        return self._data[self._current] if 0 <= self._current < len(self._data) else None

    def currentIndex(self) -> int:  # noqa: N802
        """Chỉ số lựa chọn đang chọn; -1 nếu chưa chọn gì."""
        return self._current

    def count(self) -> int:
        """Số lựa chọn đang có."""
        return len(self._buttons)

    def setItemText(self, index: int, text: str) -> None:  # noqa: N802
        """Đổi nhãn một lựa chọn (dùng khi đổi ngôn ngữ).

        Tính lại bề rộng tối thiểu: nhãn mới dài ngắn khác nhau, giữ nguyên số
        cũ thì hoặc cắt chữ hoặc chừa một khoảng trống vô cớ.
        """
        if 0 <= index < len(self._buttons):
            btn = self._buttons[index]
            btn.setText(text)
            btn.setMinimumWidth(0)
            self._reserve_bold_width(btn)

    def setCurrentIndex(self, index: int) -> None:  # noqa: N802
        """Chọn một mục và phát tín hiệu đổi.

        Chỉ số không hợp lệ hoặc trùng mục đang chọn thì chỉ đồng bộ lại trạng thái
        nút, không phát tín hiệu — tránh vòng lặp khi chỗ gọi lại đặt lại chỉ số.
        """
        if not (0 <= index < len(self._buttons)) or index == self._current:
            for i, b in enumerate(self._buttons):
                b.setChecked(i == self._current)
            return
        self._current = index
        for i, b in enumerate(self._buttons):
            b.setChecked(i == index)
        self.currentIndexChanged.emit(index)


__all__ = ["SegmentedControl"]
