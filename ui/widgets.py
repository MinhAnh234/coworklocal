"""Reusable widgets: a collapsible list section, a plan checklist, a thin
collapse strip, and a scroll-wheel guard for value widgets in scrollable
forms."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QEvent, QObject, QPoint, QPointF, QRect, QRectF, QSize, Qt, Signal,
)
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractSpinBox, QCheckBox, QComboBox, QDoubleSpinBox, QFrame,
    QHBoxLayout, QLabel, QLayout, QListWidget, QListWidgetItem, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from ..core.flows import STEP_DONE, STEP_ERROR, STEP_PENDING, STEP_RUNNING
from ..theme import current_palette
from .icons import DOT_BLUE, DOT_GREEN, DOT_GREY, DOT_RED, dot_icon, icon
# Chuyen sang ui/segmented_control.py de file nay khong vuot tran no cu cua
# cong LOC; noi lai duoi ten cu vi 2 cho goi dang import tu day.
from .segmented_control import SegmentedControl  # noqa: F401


def badge_pill_widget(text: str, object_name: str) -> QWidget:
    """A small rounded pill for a table cell — a coloured role/status tag
    (``object_name`` is one of theme.py's ``badge*`` QLabel names). Wrapped in
    a transparent container rather than passed as a bare label: a
    ``setCellWidget()`` widget is stretched to fill the whole cell, and
    without the container's own ``background: transparent`` the app-wide
    ``QWidget { background: $bg }`` rule (theme.py) paints that stretched
    area opaque, hiding the pill inside a solid block instead of a snug tag."""
    container = QWidget()
    container.setStyleSheet("background: transparent;")
    lay = QHBoxLayout(container)
    lay.setContentsMargins(4, 2, 4, 2)
    lbl = QLabel(text)
    lbl.setObjectName(object_name)
    lay.addWidget(lbl, 0, Qt.AlignVCenter)
    lay.addStretch(1)
    return container


def enable_height_for_width(widget: QWidget) -> None:
    """Flag ``widget`` as height-for-width so a PARENT layout reserves the
    right amount of vertical space for it — needed at every widget boundary
    between a :class:`FlowLayout` and the outermost layout, since each
    ``addWidget()`` hop asks the WIDGET's own sizePolicy, not its layout's
    (see FlowLayout's docstring)."""
    policy = widget.sizePolicy()
    policy.setHeightForWidth(True)
    widget.setSizePolicy(policy)


class FlowLayout(QLayout):
    """A left-aligned layout that wraps its children onto new lines as the
    container narrows, each item kept at its own natural size — the
    ``.card`` grids in ui-audit_v2.html ("không kéo giãn lấp đầy hàng": cards
    stay sized to their own content, never stretched to fill a row). Qt has
    no built-in equivalent; this is the standard recipe (Qt's own C++
    FlowLayout example, ported)."""

    def __init__(self, parent=None, margin: int = 0, h_spacing: int = 8, v_spacing: int = 8):
        """Layout tự xuống dòng khi hết bề ngang.

        Phải bật ``heightForWidth`` trên widget cha, nếu không Qt không hỏi lại chiều
        cao và hàng tràn ra bị cắt mất.
        """
        super().__init__(parent)
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self._items: list = []
        self.setContentsMargins(margin, margin, margin, margin)
        if parent is not None:
            enable_height_for_width(parent)

    def addItem(self, item) -> None:  # noqa: N802 - Qt override
        """Thêm một item vào cuối dòng chảy."""
        self._items.append(item)

    def count(self) -> int:  # noqa: N802 - Qt override
        """Số item đang có trong layout."""
        return len(self._items)

    def itemAt(self, index: int):  # noqa: N802 - Qt override
        """Item ở vị trí ``index``; ``None`` nếu ngoài phạm vi."""
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int):  # noqa: N802 - Qt override
        """Lấy item ra khỏi layout và trả về; ``None`` nếu ngoài phạm vi."""
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):  # noqa: N802 - Qt override
        """Không tự bung theo hướng nào — chiều cao do ``heightForWidth`` quyết định."""
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self) -> bool:  # noqa: N802 - Qt override
        """Luôn ``True``: chiều cao của layout phụ thuộc bề rộng được cấp."""
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802 - Qt override
        """Chiều cao cần có nếu chỉ được cấp ``width`` — tính bằng cách xếp thử, không vẽ thật."""
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect) -> None:  # noqa: N802 - Qt override
        """Xếp lại các item vào vùng được cấp."""
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):  # noqa: N802 - Qt override
        """Kích thước mong muốn — bằng kích thước tối thiểu."""
        return self.minimumSize()

    def minimumSize(self):  # noqa: N802 - Qt override
        """Kích thước tối thiểu: đủ chứa item lớn nhất cộng lề."""
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect, test_only: bool) -> int:
        """Xếp item thành nhiều dòng, xuống dòng khi hết bề rộng.

        ``test_only=True`` chỉ TÍNH chiều cao mà không dời widget nào — dùng cho
        ``heightForWidth``, vì Qt hỏi chiều cao trước khi thật sự cấp vùng.
        """
        m = self.contentsMargins()
        effective = QRect(rect.x() + m.left(), rect.y() + m.top(),
                          rect.width() - m.left() - m.right(),
                          rect.height() - m.top() - m.bottom())
        x, y = effective.x(), effective.y()
        line_height = 0
        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width() + self._h_spacing
            if next_x - self._h_spacing > effective.right() and line_height > 0:
                x = effective.x()
                y = y + line_height + self._v_spacing
                next_x = x + hint.width() + self._h_spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y() + m.bottom()


def style_card(frame: QFrame) -> None:
    """Give a stat/budget card its surface. Flat by design: the raised surface
    plus a hairline is what separates it from the page — the old drop shadow
    made a grid of these look like it was hovering off the screen."""
    p = current_palette()
    frame.setStyleSheet(
        f"QFrame {{ background: {p.surface}; border: 1px solid {p.border};"
        f" border-radius: {p.radius_lg}px; }}")


class StatCard(QFrame):
    """A titled value card (e.g. token count + its cost as the subtitle) —
    shared by Dashboard and Monitoring's token/cost displays."""

    def __init__(self):
        """Thẻ một con số kèm nhãn — viên gạch của Bảng điều khiển và Giám sát."""
        super().__init__()
        self.setFrameShape(QFrame.NoFrame)
        style_card(self)
        lay = QVBoxLayout(self)
        self.title_lbl = QLabel("")
        self.title_lbl.setObjectName("hint")
        self.title_lbl.setStyleSheet("border: none;")
        self.value_lbl = QLabel("—")
        self.value_lbl.setStyleSheet("border: none; font-size: 22px; font-weight: 600;")
        self.sub_lbl = QLabel("")
        self.sub_lbl.setObjectName("hint")
        self.sub_lbl.setStyleSheet("border: none;")
        # Word-wrap the sub-label: a long note (e.g. the "estimated tokens"
        # sentence on the cost card) would otherwise report a single-line
        # sizeHint hundreds of px wide, forcing its WHOLE grid column open and
        # throwing every card in the row out of alignment.
        self.sub_lbl.setWordWrap(True)
        # Number first, name under it — the figure is what the eye is looking
        # for, and it is how the audit page's tiles are drawn.
        lay.addWidget(self.value_lbl)
        lay.addWidget(self.title_lbl)
        lay.addWidget(self.sub_lbl)

    def set(self, title: str, value: str, sub: str = "") -> None:
        """Đặt tiêu đề, giá trị và dòng phụ cho thẻ."""
        self.title_lbl.setText(title)
        self.value_lbl.setText(value)
        self.sub_lbl.setText(sub)

    def as_hero(self) -> "StatCard":
        """Make this the headline card: bigger number, accent colour.

        Used for the one figure a screen is really about (Dashboard's total
        cost), so a row of otherwise identical tiles has a clear first read.
        """
        from ..theme import current_palette
        p = current_palette()
        self.value_lbl.setStyleSheet(
            f"border: none; font-size: 34px; font-weight: 700; color: {p.accent};")
        self.setObjectName("heroCard")
        return self


class BudgetCard(QFrame):
    """Remaining/Budget box — same card chrome as :class:`StatCard`, plus a
    direct budget-entry field. The card is a dumb display: the owning tab
    (Dashboard/Monitoring, both share the same ``usage.budget_*`` config) wires
    ``apply_btn.clicked`` to persist a new budget and refresh, and calls
    :meth:`set` with pre-formatted text + whether to render in the ⚠ warn color
    (the app turns the remaining balance red past 85% budget used)."""

    def __init__(self):
        """Thẻ ngân sách: số đã dùng trên hạn mức, kèm thanh tiến độ."""
        super().__init__()
        self.setFrameShape(QFrame.NoFrame)
        style_card(self)
        lay = QVBoxLayout(self)
        self.title_lbl = QLabel("")
        self.title_lbl.setObjectName("hint")
        self.title_lbl.setStyleSheet("border: none;")
        self.value_lbl = QLabel("—")
        self._value_style = "border: none; font-size: 22px; font-weight: 600;"
        self.value_lbl.setStyleSheet(self._value_style)
        self.sub_lbl = QLabel("")
        self.sub_lbl.setObjectName("hint")
        self.sub_lbl.setStyleSheet("border: none;")
        # Word-wrap the sub-label: a long note (e.g. the "estimated tokens"
        # sentence on the cost card) would otherwise report a single-line
        # sizeHint hundreds of px wide, forcing its WHOLE grid column open and
        # throwing every card in the row out of alignment.
        self.sub_lbl.setWordWrap(True)
        # Same order as StatCard: the number first, its name under it.
        lay.addWidget(self.value_lbl)
        lay.addWidget(self.title_lbl)
        lay.addWidget(self.sub_lbl)

        row = QHBoxLayout()
        row.setSpacing(4)
        self.budget_spin = QDoubleSpinBox()
        self.budget_spin.setRange(0, 100_000_000)
        self.budget_spin.setDecimals(2)
        self.budget_spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.apply_btn = QPushButton()
        self.apply_btn.setFixedWidth(30)
        row.addWidget(self.budget_spin, 1)
        row.addWidget(self.apply_btn)
        lay.addLayout(row)

    def set(self, title: str, value: str, sub: str, warn: bool = False) -> None:
        """Đặt nội dung thẻ; ``warn=True`` tô con số bằng màu cảnh báo."""
        self.title_lbl.setText(title)
        self.value_lbl.setText(value)
        self.value_lbl.setStyleSheet(
            self._value_style + (f" color: {current_palette().danger};" if warn else ""))
        self.sub_lbl.setText(sub)


def fmt_tokens(n: int) -> str:
    """Rút gọn số token cho dễ đọc: ``1_500`` → '1.5K', ``2_000_000`` → '2.00M'."""
    if n >= 1_000_000:
        return f"{n / 1e6:.2f}M"
    if n >= 1_000:
        return f"{n / 1e3:.1f}K"
    return str(n)


class _WheelGuard(QObject):
    """Swallows wheel events on a value widget unless the user has clicked
    into it first (i.e. it has keyboard focus). Without this, scrolling a
    Settings/task-editor form accidentally spins whatever combo box or
    spin box the cursor happens to pass over, silently changing values."""

    def eventFilter(self, obj, event):  # noqa: N802
        """Chặn lăn chuột trên widget chưa có focus.

        Không chặn thì lăn qua một combo box giữa trang sẽ âm thầm đổi giá trị của
        nó thay vì cuộn trang — nuốt sự kiện để vùng cuộn nhận được.
        """
        if event.type() == QEvent.Wheel and not obj.hasFocus():
            event.ignore()
            return True   # eat it → the scroll area scrolls instead
        return False


_wheel_guard = _WheelGuard()


def guard_wheel(root: QWidget) -> None:
    """Protect every QComboBox / spin box / date-time edit under ``root``:
    the mouse wheel only changes their value after an explicit click into
    the widget (StrongFocus excludes wheel-acquired focus), otherwise the
    wheel scrolls the surrounding form like the user expects."""
    targets = root.findChildren(QComboBox) + root.findChildren(QAbstractSpinBox)
    for w in targets:
        w.setFocusPolicy(Qt.StrongFocus)
        w.installEventFilter(_wheel_guard)


def tidy_popup(combo) -> None:
    """Make a drop-list show its options and nothing else.

    Two platform habits to undo. macOS marks the current row with a checkmark,
    drawn by the menu-style delegate a combo gets by default; the row is already
    tinted by selection-background-color, so the tick says nothing twice and, in
    a combo only as wide as "VN", covered the letters it was marking. Handing
    the view a plain QStyledItemDelegate switches it to item-view painting,
    where no such glyph exists.

    And the popup inherits the combo's width unless told otherwise, which had
    the project and provider names cut off here regardless of platform. So
    measure the longest item — plus an indicator's worth of room, in case a
    style still draws one — and set that as the view's minimum.
    """
    from PySide6.QtWidgets import QStyle, QStyledItemDelegate

    view = combo.view()
    combo.setItemDelegate(QStyledItemDelegate(combo))
    fm = view.fontMetrics()
    longest = max((fm.horizontalAdvance(combo.itemText(i))
                   for i in range(combo.count())), default=0)
    tick = combo.style().pixelMetric(QStyle.PM_IndicatorWidth, None, combo)
    pad = combo.style().pixelMetric(QStyle.PM_FocusFrameHMargin, None, combo) * 2
    view.setMinimumWidth(longest + tick + pad + 16)


def ui_scale(widget: QWidget) -> float:
    """How much bigger this machine draws things than the design baseline.

    Breakpoints written as raw pixels only hold on the screen they were tuned
    on. At 125%/150% display scaling Qt still reports logical pixels, but every
    label, button and margin is taller — so the same layout needs MORE logical
    width before it stops being cramped. Font height is the honest proxy for
    that: it moves with the display scale and with a user's font-size choice,
    both of which change how much fits.

    1.0 at the 15px line height the layouts were measured against.
    """
    return max(0.75, min(2.5, widget.fontMetrics().height() / 15.0))


class _NarrowGuard(QObject):
    """Calls back when the WINDOW crosses a width threshold.

    Watching the widget's own width does not work: a pane whose minimum width is
    larger than the space available never reports being narrow — it just gets
    clipped, which is the very problem being solved. The window always knows its
    real size, so that is what gets watched.

    A fold the user did by hand is never undone: auto-expand only reverses an
    auto-collapse.
    """

    def __init__(self, owner: QWidget, threshold: int, apply):
        """Tự gập một panel khi cửa sổ hẹp lại dưới ``threshold``.

        ``_auto`` phân biệt "ta đang giữ nó gập" với "người dùng tự gập": không
        phân biệt thì kéo rộng cửa sổ ra sẽ bung cả panel mà người dùng cố ý gập.
        """
        super().__init__(owner)
        self._owner = owner
        self._threshold = threshold
        self._apply = apply
        self._auto = False          # True while WE are the ones holding it folded
        self._window = None

    def attach(self) -> None:
        """Bắt đầu theo dõi sự kiện đổi kích thước của cửa sổ chứa widget."""
        win = self._owner.window()
        if win is not None and win is not self._owner and win is not self._window:
            win.installEventFilter(self)
            self._window = win
            # Dragging the window to a monitor with different scaling changes
            # how much fits without changing its width, so re-decide then too.
            handle = win.windowHandle()
            if handle is not None:
                handle.screenChanged.connect(lambda *_a: self.check())
        self.check()

    def eventFilter(self, obj, ev):  # noqa: N802 - Qt override
        """Cửa sổ đổi kích thước thì kiểm lại xem có phải chuyển sang bố cục hẹp không."""
        if ev.type() == QEvent.Resize and obj is self._window:
            self.check()
        return super().eventFilter(obj, ev)

    def check(self) -> None:
        """Áp bố cục hẹp/rộng theo bề rộng cửa sổ.

        Ngưỡng được viết theo tỉ lệ hiển thị chuẩn và nhân lên theo tỉ lệ thật của
        máy (xem ``ui_scale()``), nên màn 125%/150% không bị chuyển nhầm sớm.
        """
        win = self._owner.window()
        width = win.width() if win is not None else self._owner.width()
        # The threshold is written for the baseline scale and grows with the
        # machine's — see ui_scale().
        narrow = width < self._threshold * ui_scale(self._owner)
        if narrow == self._auto:
            return
        self._auto = narrow
        self._apply(narrow)


def narrow_guard(owner: QWidget, threshold: int, apply):
    """Fold `owner`'s secondary panes below `threshold` px of window width.

    ``apply(narrow: bool)`` does the folding. Call ``.attach()`` from showEvent.
    """
    return _NarrowGuard(owner, threshold, apply)


class ToggleSwitch(QCheckBox):
    """A checkbox drawn as an on/off switch.

    Subclasses QCheckBox rather than replacing it, so every ``isChecked()`` /
    ``setChecked()`` / ``stateChanged`` call site keeps working untouched — only
    the painting changes. A switch reads as "this is on or off" where a tick box
    reads as "this is selected", which is what these settings actually mean.
    """

    _W, _H = 34, 18

    def __init__(self, text: str = "", parent=None):
        """Công tắc gạt kiểu iOS, vẽ thay cho ô tick."""
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)

    def sizeHint(self):  # noqa: N802 - Qt override
        """Chừa thêm chỗ cho phần gạt bên cạnh nhãn."""
        base = super().sizeHint()
        base.setWidth(base.width() + self._W)
        base.setHeight(max(base.height(), self._H + 4))
        return base

    def paintEvent(self, _e):  # noqa: N802 - Qt override
        """Tự vẽ rãnh và núm gạt theo màu của theme đang dùng."""
        from ..theme import current_palette
        p = current_palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        y = (self.height() - self._H) // 2
        track = QRectF(0, y, self._W, self._H)
        on = self.isChecked()
        enabled = self.isEnabled()
        fill = QColor(p.accent_solid if on else p.border_strong)
        if not enabled:
            fill.setAlpha(110)
        painter.setPen(Qt.NoPen)
        painter.setBrush(fill)
        painter.drawRoundedRect(track, self._H / 2, self._H / 2)
        knob = self._H - 4
        kx = self._W - knob - 2 if on else 2
        painter.setBrush(QColor("#FFFFFF" if enabled else p.text_faint))
        painter.drawEllipse(QRectF(kx, y + 2, knob, knob))
        if self.text():
            painter.setPen(QColor(p.text if enabled else p.text_faint))
            painter.drawText(
                QRectF(self._W + 8, 0, self.width() - self._W - 8, self.height()),
                int(Qt.AlignLeft | Qt.AlignVCenter), self.text())
        painter.end()


def section_panels(sections, width: int = 260):
    """Left list + right panel: pick a section, see that section only.

    ``sections`` is [(label, widget)]. Returns (list_widget, stack) for the
    caller to place side by side. Used by Settings and the Task editor so both
    are navigated the same way, instead of one long scroll where you cannot
    tell which group you are in or how many are left.
    """
    from PySide6.QtWidgets import QListWidget, QListWidgetItem, QStackedWidget

    index = QListWidget()
    index.setObjectName("sectionIndex")
    index.setFrameShape(QListWidget.NoFrame)
    index.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    index.setTextElideMode(Qt.ElideRight)
    index.setWordWrap(False)

    stack = QStackedWidget()
    for label, widget in sections:
        item = QListWidgetItem(label)
        item.setToolTip(label)
        index.addItem(item)
        stack.addWidget(widget)
    index.currentRowChanged.connect(stack.setCurrentIndex)
    index.setCurrentRow(0)

    natural = max(index.fontMetrics().horizontalAdvance(lab) for lab, _w in sections) + 36
    index.setFixedWidth(max(120, min(width, natural)))
    return index, stack


def section_index(scroll, sections, width: int = 260):
    """A clickable table of contents for a long scrolling dialog.

    ``sections`` is [(label, anchor_widget)]. Clicking a row scrolls its anchor
    into view; scrolling the dialog moves the highlight back. Purely navigation:
    every field stays exactly where it was, in the same one scrolling column —
    Settings and the Task editor were five stacked group boxes deep with no way
    to tell what was further down.

    Returns the QListWidget so the caller can place it.
    """
    from PySide6.QtWidgets import QListWidget, QListWidgetItem

    index = QListWidget()
    index.setObjectName("sectionIndex")
    index.setFrameShape(QListWidget.NoFrame)
    # Long section names (and 125%/150% display scaling) used to push a
    # horizontal scrollbar into this list. It elides instead, with the full
    # name on hover.
    index.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    index.setTextElideMode(Qt.ElideRight)
    index.setWordWrap(False)
    for label, anchor in sections:
        item = QListWidgetItem(label)
        item.setToolTip(label)
        item.setData(Qt.UserRole, anchor)
        index.addItem(item)
    index.setCurrentRow(0)
    # Wide enough for the longest name at the CURRENT font — so the width grows
    # with display scaling instead of eliding everything — but capped so it
    # never eats the form beside it. `width` is that cap, not a fixed size.
    natural = max(index.fontMetrics().horizontalAdvance(lab) for lab, _a in sections) + 36
    index.setFixedWidth(max(120, min(width, natural)))

    def _jump(item):
        """Bấm một mục trong cột mục lục: cuộn sao cho mép trên của mục đó lên đúng
        đỉnh vùng nhìn, chứ không chỉ "đâu đó trong tầm mắt".
        """
        anchor = item.data(Qt.UserRole)
        if anchor is not None:
            # Scroll so the section's top edge lands at the top of the viewport,
            # rather than merely "somewhere visible".
            bar = scroll.verticalScrollBar()
            top = anchor.mapTo(scroll.widget(), anchor.rect().topLeft()).y()
            bar.setValue(min(top, bar.maximum()))

    index.itemClicked.connect(_jump)

    def _follow(value: int):
        """Highlight the last section whose top has passed the viewport top."""
        row = 0
        for i in range(index.count()):
            anchor = index.item(i).data(Qt.UserRole)
            if anchor is None:
                continue
            top = anchor.mapTo(scroll.widget(), anchor.rect().topLeft()).y()
            if top <= value + 4:
                row = i
        if index.currentRow() != row:
            blocked = index.blockSignals(True)
            index.setCurrentRow(row)
            index.blockSignals(blocked)

    scroll.verticalScrollBar().valueChanged.connect(_follow)
    return index


class CollapseStrip(QWidget):
    """The slim bar shown in place of a collapsed side panel.

    It draws a clear chevron (▸ / ◂) near the top — the expand affordance — over
    a thin handle line, and the whole strip is clickable to expand the panel."""

    clicked = Signal()
    WIDTH = 18  # click target width; wide enough to show the expand arrow

    def __init__(self, tooltip: str = "Click to expand", expand_dir: str = "right"):
        """Dải mảnh còn lại sau khi gập một panel; bấm vào là bung ra.

        ``expand_dir`` quyết định mũi tên chỉ hướng nào — panel gập ở mép trái bung
        sang phải và ngược lại.
        """
        super().__init__()
        self._hover = False
        self._dir = "left" if expand_dir == "left" else "right"
        self.setFixedWidth(self.WIDTH)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tooltip)

    def enterEvent(self, e) -> None:  # noqa: N802
        """Rê chuột vào thì làm nổi dải lên."""
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:  # noqa: N802
        """Rời chuột thì trả dải về trạng thái thường."""
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e) -> None:  # noqa: N802
        """Bấm trái vào dải thì phát tín hiệu mở lại panel."""
        if e.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)

    def paintEvent(self, e) -> None:  # noqa: N802
        """Vẽ dải: nền theo theme cộng mũi tên chỉ hướng sẽ bung ra."""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        tok = current_palette()
        accent = QColor(tok.accent) if self._hover else QColor(tok.text_faint)

        # A small rounded "button" at the top carries the expand arrow so the
        # collapsed panel always shows a clear, clickable affordance.
        bw = min(w - 2.0, 16.0)
        btn = QRectF((w - bw) / 2.0, 6.0, bw, 18.0)
        p.setPen(QPen(QColor(tok.border_strong), 1.0))
        p.setBrush(QColor(tok.hover if self._hover else tok.surface))
        p.drawRoundedRect(btn, float(tok.radius_sm), float(tok.radius_sm))

        cx = w / 2.0
        cy = btn.center().y()
        s = 4.0
        pen = QPen(accent, 2.0)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        if self._dir == "right":   # '›' — expands content to the right
            tip_x, base_x = cx + s / 2.0, cx - s / 2.0
        else:                       # '‹' — expands content to the left
            tip_x, base_x = cx - s / 2.0, cx + s / 2.0
        p.drawLine(QPointF(base_x, cy - s), QPointF(tip_x, cy))
        p.drawLine(QPointF(tip_x, cy), QPointF(base_x, cy + s))

        # thin handle line below the button
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(tok.border_strong))
        line_w = 2.0
        x = (w - line_w) / 2.0
        ltop = btn.bottom() + 6.0
        lbottom = max(ltop, self.height() - 10.0)
        p.drawRoundedRect(QRectF(x, ltop, line_w, lbottom - ltop), 1.0, 1.0)
        p.end()


class PlanSection(QWidget):
    """A collapsible checklist of the current message's plan steps with live
    line-icon status markers (pending dot · running play · done check · error
    close). Hidden until it has steps; updated in place as the agent calls
    ``update_plan``."""

    @staticmethod
    def _step_color(status: str) -> str | None:
        """Row text colour per step status; None leaves the default. Resolved
        per call so it follows a live theme switch."""
        p = current_palette()
        return {STEP_RUNNING: p.accent, STEP_DONE: p.success, STEP_ERROR: p.danger}.get(status)

    @staticmethod
    def _step_icon(status: str):
        """Icon tương ứng trạng thái một bước: đang chạy, xong, lỗi hay còn chờ."""
        if status == STEP_RUNNING:
            return icon("play", color=DOT_BLUE)
        if status == STEP_DONE:
            return icon("check", color=DOT_GREEN)
        if status == STEP_ERROR:
            return icon("close", color=DOT_RED)
        return dot_icon(DOT_GREY)   # pending

    def __init__(self, title: str = "Plan", max_height: int = 150):
        """Khối kế hoạch nhiều bước trong bong bóng chat, có giới hạn chiều cao để một
        kế hoạch dài không đẩy phần trả lời ra khỏi màn hình.
        """
        super().__init__()
        self._title = title
        self._count = 0

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        self.header = QPushButton()
        self.header.setCheckable(True)
        self.header.setChecked(True)
        self.header.setStyleSheet("text-align:left; font-weight:600;")
        self.header.toggled.connect(self._toggle)
        lay.addWidget(self.header)

        self.list = QListWidget()
        self.list.setMaximumHeight(max_height)   # scrolls when longer
        lay.addWidget(self.list)

        self.setVisible(False)
        self._update_header()

    def set_steps(self, steps) -> None:
        """Replace the checklist with ``[{title, status}]`` (the agent sends the FULL
        list each update, so we rebuild in place)."""
        self.list.clear()
        self._count = 0
        for s in steps or []:
            title = str((s or {}).get("title", "")).strip()
            if not title:
                continue
            status = str((s or {}).get("status", STEP_PENDING)).strip().lower()
            item = QListWidgetItem(self._step_icon(status), f"  {title}")
            color = self._step_color(status)
            if color:
                item.setForeground(QColor(color))
            self.list.addItem(item)
            self._count += 1
        self.setVisible(self._count > 0)
        if self._count and not self.header.isChecked():
            self.header.setChecked(True)
        self.list.setVisible(self.header.isChecked())
        self._update_header()

    def clear(self) -> None:
        """Xoá sạch kế hoạch và ẩn cả khối đi."""
        self.list.clear()
        self._count = 0
        self.setVisible(False)
        self._update_header()

    def set_title(self, title: str) -> None:
        """Update the header label (for live language switching)."""
        self._title = title
        self._update_header()

    def _toggle(self, on: bool) -> None:
        """Gập/mở danh sách bước."""
        self.list.setVisible(on)
        self._update_header()

    def _update_header(self) -> None:
        """Cập nhật dòng tiêu đề: mũi tên gập/mở kèm số bước."""
        arrow = "▾" if self.header.isChecked() else "▸"
        self.header.setText(f"{arrow} {self._title} ({self._count})")


class CollapsibleSection(QWidget):
    """A pull-down header + a scrollable list. Hidden until it has items."""

    activated = Signal(str)  # emits the path of a clicked item

    def __init__(self, title: str, max_height: int | None = 130):
        """``max_height`` caps the list so it scrolls instead of growing
        (the default, e.g. for a section sharing space with siblings).
        ``None`` instead lets it expand to fill whatever room its parent
        layout hands it — for a section that owns the whole panel."""
        super().__init__()
        self._title = title
        self._paths: list[str] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        self.header = QPushButton()
        self.header.setCheckable(True)
        self.header.setChecked(False)
        self.header.setStyleSheet("text-align:left; font-weight:600;")
        self.header.toggled.connect(self._toggle)
        lay.addWidget(self.header)

        self.list = QListWidget()
        if max_height is not None:
            self.list.setMaximumHeight(max_height)   # scrolls when longer
        else:
            self.list.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.list.setVisible(False)
        self.list.itemActivated.connect(self._emit)
        self.list.itemClicked.connect(self._emit)
        lay.addWidget(self.list, 1 if max_height is None else 0)

        self.setVisible(False)
        self._update_header()

    def add(self, path: str) -> None:
        """Thêm một đường dẫn vào mục; đã có rồi thì bỏ qua."""
        if not path or path in self._paths:
            return
        self._paths.append(path)
        item = QListWidgetItem(Path(path).name)
        item.setData(Qt.UserRole, path)
        item.setToolTip(path)
        self.list.addItem(item)
        self.setVisible(True)
        # Auto-open so added / restored files are visible without a click.
        if not self.header.isChecked():
            self.header.setChecked(True)
        self._update_header()

    def remove(self, path: str) -> None:
        """Gỡ một đường dẫn khỏi mục."""
        if path not in self._paths:
            return
        i = self._paths.index(path)
        self._paths.pop(i)
        item = self.list.takeItem(i)
        del item
        self.setVisible(bool(self._paths))
        self._update_header()

    def paths(self) -> list[str]:
        """Bản sao danh sách đường dẫn đang hiện trong mục."""
        return list(self._paths)

    def clear(self) -> None:
        """Xoá sạch mục."""
        self._paths.clear()
        self.list.clear()
        self.setVisible(False)
        self._update_header()

    def set_title(self, title: str) -> None:
        """Update the header label (for live language switching)."""
        self._title = title
        self._update_header()

    def _toggle(self, on: bool) -> None:
        """Gập/mở danh sách."""
        self.list.setVisible(on)
        self._update_header()

    def _update_header(self) -> None:
        """Cập nhật dòng tiêu đề: mũi tên gập/mở kèm số mục."""
        arrow = "▾" if self.header.isChecked() else "▸"
        self.header.setText(f"{arrow} {self._title} ({len(self._paths)})")

    def _emit(self, item: QListWidgetItem) -> None:
        """Bấm một dòng: phát đường dẫn lên để chỗ gọi mở tệp."""
        path = item.data(Qt.UserRole)
        if path:
            self.activated.emit(path)
