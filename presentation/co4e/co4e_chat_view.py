"""Khu vực CHAT của Co4E (composer + autocomplete ``/skill:``/``/agent:``) —
tách khỏi ``ui/co4e_tab.py``.

Vấn đề đang có: 3 hàm module-level (``_skill_names``/``_agent_names``/
``_directive_token``), lớp ``_ChatInput`` (ô chat có popup autocomplete) và
phần DỰNG WIDGET của ``Co4ETab._build_chat`` (nguyên bản ở ``ui/co4e_tab.py``
dòng 63-73, 124-228 và 1030-1093) nằm rải trong file container 2000+ dòng —
vượt xa giới hạn CASAN (≤400 dòng mỗi file production) và không tách được
riêng để test mà không phải dựng cả ``Co4ETab``. Không phần nào trong số này
đọc/ghi trạng thái RIÊNG của ``Co4ETab`` lúc DỰNG (``_flow_logs`` là ngoại lệ —
xem chú thích ở ``ChatPanel`` bên dưới), nên tách được thành các hàm/lớp con
độc lập.

Cách làm: dời nguyên 3 hàm + ``_ChatInput`` — KHÔNG đổi tên, KHÔNG đổi hành vi
(kể cả các quirk trông như bug, xem docstring của ``tests/characterization/
test_co4e_chat_view.py``: agent chèn nguyên tên KHÔNG slugify còn skill có,
dedup theo tên hiển thị không theo slug, Enter có hai hành vi tuỳ popup còn
hiện hay đã ẩn, ...). Phần dựng widget của ``_build_chat`` được bọc vào một
lớp mới ``ChatPanel(QWidget)`` theo đúng khuôn mẫu đã dùng cho
``AgentListPanel``/``SkillsListPanel``/``RunsPagePanel`` (xem
``presentation/co4e/agent_list_panel.py``): panel chỉ dựng cấu trúc UI, KHÔNG
tự nối signal (``ui/co4e_tab.py`` mới là nơi biết ``_toggle_messages``/
``_chat_send`` là gì) và KHÔNG tự tạo ``_flow_logs`` (dict per-flow ChatView —
đó là STATE của ``Co4ETab``, ghi bởi ``_ensure_flow_log``/``_active_log`` nằm
ngoài phạm vi panel này). Tên thuộc tính giữ NGUYÊN so với bản gốc
(``msgs_icon``, ``msgs_title``, ``chat_toggle_btn``, ``chat_stack``,
``chat_input_row``, ``chat_input``, ``chat_send_btn``, ``co4e_routing_toggle``)
vì bị tham chiếu ở rất nhiều nơi khác của ``Co4ETab`` (``_toggle_messages``,
``_chat_send``, ``_refresh_usage_total``, ...) — đổi tên sẽ buộc phải sửa mọi
chỗ đó, vượt phạm vi lượt tách này. Riêng ``_mhdr`` (biến cục bộ đặt tên riêng
lẻ, không theo quy ước công khai) đổi thành ``.header`` và ``_usage_total_lbl``
đổi thành ``.usage_total_lbl`` — cả hai an toàn vì bản gốc chỉ dùng nội bộ
``_build_chat``/``_toggle_messages`` (đã kiểm bằng grep toàn file), và
``ui/co4e_tab.py`` sau khi tách vẫn gán lại các tên cũ (``self._mhdr``,
``self._usage_total_lbl``) làm alias trỏ vào hai thuộc tính công khai này, nên
mọi chỗ dùng tên cũ trên ``Co4ETab`` không phải sửa.
"""
from __future__ import annotations

import re
from typing import List

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from ...core import co4e, skills as skills_mod
from ...core.co4e_builtins import BUILTIN_AGENTS
from ...i18n import tr
from ...theme import current_palette
from ...ui.icons import icon
from ...ui.routing_toggle import RoutingToggle


def _skill_names() -> List[str]:
    """Tên mọi skill dùng được (tự tạo + dựng sẵn); lỗi đọc thì trả list rỗng."""
    try:
        return [s.name for s in skills_mod.list_skills() + skills_mod.builtin_skills()]
    except Exception:  # noqa: BLE001
        return []


def _agent_names() -> List[str]:
    """Tên mọi agent dùng được: agent tự tạo trước, rồi tới agent dựng sẵn chưa trùng tên."""
    names = [a.name for a in co4e.list_custom_agents()]
    names += [a.name for a in BUILTIN_AGENTS if a.name not in names]
    return names


def _directive_token(text: str, pos: int):
    """Locate a ``/skill[:x]`` or ``/agent[:x]`` directive the cursor is on,
    anywhere in the line. Returns ``(start, kind, partial)`` or ``None``."""
    before = text[:pos]
    start = re.search(r"\S*$", before).start()
    token = before[start:]
    m = re.match(r"^/(skill|agent):?([\w\-.]*)$", token)
    if m:
        return start, m.group(1), m.group(2)
    for kind in ("skill", "agent"):
        if len(token) >= 2 and ("/" + kind).startswith(token):
            return start, kind, ""
    return None


class _ChatInput(QLineEdit):
    """Chat box with ``/skill:`` and ``/agent:`` autocomplete (parity with the
    Cowork composer). The popup never grabs focus, so typing keeps flowing."""

    submit = Signal()

    def __init__(self, parent=None):
        """Ô soạn của khung chat Co4E, kèm danh sách gợi ý nổi lên khi gõ lệnh."""
        super().__init__(parent)
        self._popup = QListWidget()
        self._popup.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint
                                   | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint)
        self._popup.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._popup.setFocusPolicy(Qt.NoFocus)
        self._popup.itemClicked.connect(lambda _i: self._accept())
        self.textEdited.connect(self._maybe_popup)

    def _maybe_popup(self, *_a) -> None:
        """Mở bảng gợi ý khi con trỏ đang đứng trên một lệnh ``/skill`` hoặc ``/agent``."""
        tok = _directive_token(self.text(), self.cursorPosition())
        if tok is None:
            self._popup.hide()
            return
        _start, kind, partial = tok
        f = partial.lower()
        self._popup.clear()
        if kind == "skill":
            for name in _skill_names():
                if f in name.lower():
                    self._add_row(name, f"/skill:{co4e.slugify(name)} ", name)
        else:
            for name in _agent_names():
                if f in name.lower():
                    self._add_row(name, f"/agent:{name} ", name)
        if self._popup.count() == 0:
            self._popup.hide()
            return
        self._popup.setCurrentRow(0)
        rows = min(7, self._popup.count())
        h = 8 + rows * 22
        self._popup.resize(max(280, self.width()), h)
        tl = self.mapToGlobal(self.rect().topLeft())
        self._popup.move(tl.x(), tl.y() - h - 2)
        self._popup.show()

    def _add_row(self, label: str, replacement: str, tip: str) -> None:
        """Thêm một dòng vào bảng gợi ý, kèm chuỗi sẽ chèn và tooltip mô tả."""
        it = QListWidgetItem(label)
        it.setData(Qt.UserRole, replacement)
        it.setToolTip(tip)
        self._popup.addItem(it)

    def _accept(self) -> None:
        """Chọn một mục: chèn lệnh tương ứng vào ô nhập và đóng bảng gợi ý."""
        item = self._popup.currentItem()
        self._popup.hide()
        if item is None:
            return
        replacement = item.data(Qt.UserRole)
        tok = _directive_token(self.text(), self.cursorPosition())
        start = tok[0] if tok else self.cursorPosition()
        pos = self.cursorPosition()
        full = self.text()
        new_text = full[:start] + replacement + full[pos:]
        self.setText(new_text)
        self.setCursorPosition(start + len(replacement))
        self.setFocus()

    def focusOutEvent(self, e):  # noqa: N802
        """Bấm ra chỗ khác thì ẩn bảng gợi ý — trừ khi chuột đang ở trên chính bảng."""
        if not self._popup.underMouse():
            self._popup.hide()
        super().focusOutEvent(e)

    def keyPressEvent(self, e):  # noqa: N802
        """Bảng gợi ý đang mở thì lên/xuống chọn mục, Enter nhận, Esc đóng;
        không thì Enter gửi tin nhắn như bình thường.
        """
        if self._popup.isVisible():
            k = e.key()
            n = self._popup.count()
            if k in (Qt.Key_Down, Qt.Key_Up) and n:
                step = 1 if k == Qt.Key_Down else -1
                self._popup.setCurrentRow((self._popup.currentRow() + step) % n)
                return
            if k in (Qt.Key_Tab,):
                self._accept()
                return
            if k == Qt.Key_Escape:
                self._popup.hide()
                return
            if k in (Qt.Key_Return, Qt.Key_Enter):
                self._accept()
                return
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.submit.emit()
            return
        super().keyPressEvent(e)


class ChatPanel(QWidget):
    """Widget khu vực CHAT của Co4E: header "Messages" + ``chat_stack`` (một
    ``ChatView`` mỗi flow) + composer (ô chat + routing toggle + nút gửi).

    Vai trò: một widget con thuần ở tầng presentation, chỉ dựng cấu trúc UI
    (đúng những gì ``ui/co4e_tab.py`` dòng 1030-1093 làm trước đây), không biết
    gì về ``Co4ETab``/``_toggle_messages``/``_chat_send``. Bên gọi (hiện là
    ``Co4ETab``) tự đọc các thuộc tính công khai dưới đây để nối signal và nạp
    dữ liệu — panel không tự làm hộ, để giữ đúng ranh giới "một nơi một việc"
    đã dùng cho ``AgentListPanel``/``SkillsListPanel``/``RunsPagePanel``.

    KHÔNG tự tạo ``_flow_logs``: dict ``{wf_id: ChatView}`` là STATE của
    ``Co4ETab`` (ghi bởi ``_ensure_flow_log``, đọc bởi ``_active_log``/
    ``chat_log``) — panel chỉ dựng cái ``chat_stack`` (vỏ chứa) rỗng, việc nạp
    từng ``ChatView`` vào đó khi có flow mới vẫn ở ``Co4ETab``.

    Panel TỰ đặt trạng thái hiển thị mặc định là COLLAPSED (chỉ header hiện,
    thân chat ẩn) ngay trong ``__init__`` — đây là phần "hình dạng lúc mới
    dựng" của chính panel, khác với ``_msgs_collapsed``/``_vsplit_sizes`` (cờ +
    kích thước để khôi phục splitter khi mở lại) vẫn là STATE của ``Co4ETab``
    vì chỉ ``_toggle_messages`` (ở lại ``Co4ETab``, đọc ``self._vsplit`` của cả
    tab) mới dùng tới.
    """

    def __init__(self, ctx) -> None:
        """Khung chat của Co4E Studio.

        Tiêu đề "Tin nhắn" nằm TRÊN hộp chat và đóng vai công tắc: bấm vào là ẩn/hiện
        cả khối bên dưới, để lấy chỗ cho khung vẽ.
        """
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        # "Messages" header at the TOP, above the chat box. Toggling it shows or
        # hides the WHOLE chat box (message list + composer) below it.
        self.header = QWidget(); self.header.setObjectName("msgHeader")
        mh = QHBoxLayout(self.header); mh.setContentsMargins(6, 3, 6, 3); mh.setSpacing(6)
        self.msgs_icon = QLabel(); self.msgs_icon.setPixmap(icon("message").pixmap(14, 14))
        self.msgs_title = QLabel(tr("co4e.messages")); self.msgs_title.setObjectName("hint")
        self.chat_toggle_btn = QPushButton()
        self.chat_toggle_btn.setObjectName("msgToggle")
        self.chat_toggle_btn.setFlat(True)
        self.chat_toggle_btn.setIcon(icon("chevron-up"))    # collapsed → points up (click to expand)
        self.chat_toggle_btn.setFixedSize(22, 22)
        # KHONG noi .clicked o day: ben goi (Co4ETab) tu quyet dinh slot nao
        # xu ly (_toggle_messages) - panel chi dung widget, khong biet no la gi.
        mh.addWidget(self.msgs_icon)
        mh.addWidget(self.msgs_title)
        mh.addStretch(1)
        mh.addWidget(self.chat_toggle_btn)
        lay.addWidget(self.header)               # header on top
        # Point-conversation (message bubbles) like Cowork, not a flat textbox.
        # ONE ChatView PER FLOW (keyed by workflow id) inside a stack, so each flow
        # tab has its OWN separate conversation and they never bleed into each other.
        self.chat_stack = QStackedWidget()
        lay.addWidget(self.chat_stack, 1)
        self.chat_input_row = QWidget()
        crow = QVBoxLayout(self.chat_input_row)
        crow.setContentsMargins(0, 4, 0, 0); crow.setSpacing(3)
        # Running conversation token/cost TOTAL for this flow (↓in ↑out ▤ctx
        # $cost) at the bottom, exactly like Cowork's conversation total.
        self.usage_total_lbl = QLabel("")
        self.usage_total_lbl.setObjectName("hint")
        self.usage_total_lbl.setStyleSheet(
            f"color: {current_palette().text_faint}; font-size: 11px;")
        crow.addWidget(self.usage_total_lbl)
        _inp = QWidget(); row = QHBoxLayout(_inp); row.setContentsMargins(0, 0, 0, 0)
        self.chat_input = _ChatInput()
        self.chat_input.setPlaceholderText(tr("co4e.chat_placeholder"))
        # KHONG noi .submit o day: cung ly do nhu chat_toggle_btn o tren
        # (ben goi noi toi _chat_send cua chinh no).
        self.chat_send_btn = QPushButton(tr("co4e.send")); self.chat_send_btn.setIcon(icon("send"))
        # KHONG noi .clicked o day: cung ly do nhu tren.
        row.addWidget(self.chat_input, 1)
        # Off/Auto/Manual routing toggle for Co4E (surface key "co4e").
        self.co4e_routing_toggle = RoutingToggle(ctx, "co4e")
        row.addWidget(self.co4e_routing_toggle)
        row.addWidget(self.chat_send_btn)
        crow.addWidget(_inp)
        lay.addWidget(self.chat_input_row)
        # Default = COLLAPSED: only the "Messages" header shows; the chat box is
        # hidden and the canvas gets the room until the user expands it.
        self.chat_stack.hide()
        self.chat_input_row.hide()
        self.chat_toggle_btn.setToolTip(tr("co4e.tt_expand_msgs"))
        self.setMaximumHeight(self.header.sizeHint().height() + 6)
