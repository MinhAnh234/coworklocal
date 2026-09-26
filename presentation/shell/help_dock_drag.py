"""Kéo nút trợ lý AI (Help) đi bất cứ đâu trong cửa sổ, và nhớ chỗ đó.

Vị trí lưu dưới dạng khoảng cách từ góc DƯỚI-PHẢI của nút tới góc dưới-phải của
cửa sổ, không phải toạ độ tuyệt đối. Nhờ vậy:

* đổi cỡ cửa sổ thì nút vẫn giữ đúng khoảng cách tới mép mà người dùng đã chọn;
* bấm mở panel chat (to hơn nút rất nhiều) thì panel "mọc" ra từ đúng góc đó,
  và bị kẹp vào trong cửa sổ nếu không đủ chỗ.

Kéo khác bấm ở chỗ con trỏ đi quá ``QApplication.startDragDistance()``; khi đã
kéo thì nhả chuột KHÔNG được tính là một cú bấm mở chat.

Mỗi lần đặt chỗ, dock còn được cắt (mask) theo đúng hình của nó: nút tròn, panel
bo góc. Phần trong suốt quanh nút tròn không hiện xuyên được qua vùng
QtWebEngine của tab GraphRAG mà bị tô thành ô vuông đen; cắt hẳn đi thì ngoài
hình tròn không còn pixel nào để tô.
"""
from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import QEvent, QObject, QPoint, QRectF, Qt
from PySide6.QtGui import QPainterPath, QRegion
from PySide6.QtWidgets import QApplication, QWidget

_CONFIG_KEY = "help_agent"
_DEFAULT_MARGIN = 18


def shape_mask(dock: QWidget) -> QRegion:
    """Vùng đúng bằng hình dock đang hiện: nút tròn/viên thuốc, panel hay thẻ mép
    bo góc. Ngoài vùng này dock không vẽ gì, kể cả trên nền QtWebEngine."""
    w, h = dock.width(), dock.height()
    state = getattr(dock, "_state", "")
    pal = getattr(dock, "_pal", None)
    if state == "launcher":
        radius = h / 2                                   # tròn, hoặc viên thuốc khi hover
    elif state == "panel":
        radius = getattr(pal, "radius_lg", 6)
    else:
        radius = getattr(pal, "radius", 4)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
    return QRegion(path.toFillPolygon().toPolygon())


class DockDragger(QObject):
    """Gắn vào ``handle`` (nút tròn) để kéo cả ``dock`` (widget nổi của trợ lý)."""

    def __init__(self, dock: QWidget, handle: QWidget, margin: int = _DEFAULT_MARGIN) -> None:
        super().__init__(dock)
        self._dock = dock
        self._handle = handle
        self._margin = margin
        self._press: Optional[QPoint] = None      # vị trí chuột (toàn cục) lúc nhấn
        self._start: Optional[QPoint] = None      # vị trí dock lúc nhấn
        self._dragging = False
        self.anchor: Optional[Tuple[int, int]] = self._load()
        handle.installEventFilter(self)

    # ---- đặt vị trí ---------------------------------------------------------
    def place(self) -> None:
        """Đặt dock theo vị trí người dùng đã kéo tới, hoặc góc mặc định."""
        p = self._dock.parentWidget()
        if p is None:
            return
        guard = getattr(self._dock, "_bottom_guard", 0)
        right, bottom = self.anchor or (self._margin, self._margin + guard)
        if getattr(self._dock, "_state", "") == "hidden":
            right = self._margin          # thẻ "gọi lại" luôn nằm sát mép phải
        x = p.width() - self._dock.width() - right
        y = p.height() - self._dock.height() - bottom
        self._dock.move(self._clamp(x, y))
        self._dock.setMask(shape_mask(self._dock))

    def _clamp(self, x: int, y: int) -> QPoint:
        """Giữ dock nằm trọn trong cửa sổ."""
        p = self._dock.parentWidget()
        max_x = max(0, p.width() - self._dock.width())
        max_y = max(0, p.height() - self._dock.height())
        return QPoint(min(max(0, x), max_x), min(max(0, y), max_y))

    # ---- kéo ---------------------------------------------------------------
    def eventFilter(self, obj, event):  # noqa: N802 - Qt override
        """Nhấn, kéo, nhả chuột trái trên nút tròn."""
        et = event.type()
        if et == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self._press = event.globalPosition().toPoint()
            self._start = self._dock.pos()
            self._dragging = False
        elif et == QEvent.MouseMove and self._press is not None \
                and event.buttons() & Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self._press
            if not self._dragging and delta.manhattanLength() >= QApplication.startDragDistance():
                self._dragging = True
                self._handle.setCursor(Qt.ClosedHandCursor)
            if self._dragging:
                target = self._start + delta
                self._dock.move(self._clamp(target.x(), target.y()))
                return True
        elif et == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton \
                and self._press is not None:
            was_dragging = self._dragging
            self._press = self._start = None
            self._dragging = False
            if was_dragging:
                self._handle.setDown(False)                # không tính là một cú bấm
                self._handle.setCursor(Qt.PointingHandCursor)
                self._remember()
                return True
        return False

    def _remember(self) -> None:
        """Lưu vị trí vừa thả dưới dạng khoảng cách tới góc dưới-phải cửa sổ."""
        p = self._dock.parentWidget()
        if p is None:
            return
        g = self._dock.geometry()
        self.anchor = (p.width() - g.right() - 1, p.height() - g.bottom() - 1)
        self._save()

    # ---- lưu / nạp -----------------------------------------------------------
    def _config(self):
        return getattr(getattr(self._dock, "ctx", None), "config", None)

    def _load(self) -> Optional[Tuple[int, int]]:
        try:
            raw = (self._config().data.get(_CONFIG_KEY) or {}).get("anchor")
            right, bottom = int(raw[0]), int(raw[1])
            return (max(0, right), max(0, bottom))
        except Exception:  # noqa: BLE001 - chưa lưu hoặc hỏng thì về góc mặc định
            return None

    def _save(self) -> None:
        cfg = self._config()
        if cfg is None or self.anchor is None:
            return
        try:
            cfg.data.setdefault(_CONFIG_KEY, {})["anchor"] = list(self.anchor)
            cfg.save()
        except Exception:  # noqa: BLE001 - lưu vị trí hỏng không được làm vỡ UI
            pass
