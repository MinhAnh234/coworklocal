"""Lớp phủ "đang xử lý" ở cấp cửa sổ, dành cho tác vụ chặn GUI thread.

Vì sao là file riêng chứ không nhét vào ``main_window.py``: file đó chỉ còn 9
dòng vật lý dưới trần 400 của Gate S, và một lớp phủ cấp cửa sổ là một trách
nhiệm riêng (guardrail G6).

Cùng lý do ``repaint()`` với panel bận của GraphRAG — xem
``presentation/graph/structure_graph_view.py:139-151``.
"""
from __future__ import annotations

from time import perf_counter
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

# Dưới mức này người dùng chưa kịp nhận ra mình đang đợi, nên một lớp phủ toàn
# cửa sổ chỉ kịp nháy lên rồi tắt — tự nó là một khuyết tật giao diện, không
# phải một lời trấn an.
_NOTICEABLE_MS = 400.0


class BusyOverlay(QWidget):
    """A window-wide "please wait" cover for work that blocks the GUI thread.

    Deliberately NOT registered with :func:`i18n.on_language_changed`: the text
    is supplied by the caller right before the block and must stay in the
    language the rest of the screen is still showing.
    """

    def __init__(self, parent: QWidget) -> None:
        """Build the cover hidden; it sizes itself to the parent on every show."""
        super().__init__(parent)
        self.setObjectName("busyOverlay")
        # A QWidget SUBCLASS ignores a stylesheet background without this
        # attribute; a plain QWidget instance (the panel below) does not need it.
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.NoFocus)
        # Chưa đo được lượt nào: xem mục ``run_blocking``.
        self._last_ms: float | None = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch(1)
        row = QHBoxLayout()
        row.addStretch(1)
        self._panel = QWidget()
        self._panel.setObjectName("busyOverlayPanel")
        inner = QHBoxLayout(self._panel)
        inner.setContentsMargins(24, 18, 24, 18)
        self._label = QLabel()
        inner.addWidget(self._label)
        row.addWidget(self._panel)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addStretch(1)
        self.hide()

    def text(self) -> str:
        """Chữ đang hiện trên lớp phủ (dùng cho test)."""
        return self._label.text()

    def run_blocking(self, message: str, work: Callable[[], None]) -> None:
        """Run ``work`` on the GUI thread, covered only when that is worth doing.

        Nothing can time the freeze WHILE it happens: the GUI thread stops, so
        no timer fires and no watchdog can raise the cover mid-way. The only
        honest clock is the PREVIOUS run of this same call, so that is what
        decides. No measurement yet (the first switch of a process) errs
        towards showing: one flash is a smaller defect than a multi-second
        freeze with nothing on screen to explain it.

        The result is self-calibrating. A fast machine flashes once per launch
        and then stays out of the way; a slow one, or a big skill library, gets
        the cover on every switch from the second one on.

        ``work`` is timed and its exceptions propagate — the cover still comes
        down, so a raising callback cannot leave it stuck on screen forever.
        """
        if self._last_ms is None or self._last_ms >= _NOTICEABLE_MS:
            self.show_busy(message)
        started = perf_counter()
        try:
            work()
        finally:
            self._last_ms = (perf_counter() - started) * 1000.0
            self.hide_busy()

    def show_busy(self, message: str) -> None:
        """Show the cover and FORCE it onto the screen right now.

        ``repaint()``, not ``update()``: the caller is about to block the GUI
        thread, so a queued paint would only run once the freeze is over — the
        one moment the cover is no longer needed.

        No animated progress bar on purpose: with no event loop running,
        nothing would move; only static text is guaranteed to be readable.
        """
        self._label.setText(message)
        self.setGeometry(self.parent().rect())
        self.show()
        self.raise_()
        self.repaint()

    def hide_busy(self) -> None:
        """Release the cover. Call from ``finally`` so a raising callback
        cannot leave it stuck on screen forever."""
        self.hide()
