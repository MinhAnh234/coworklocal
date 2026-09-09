"""Khung "section" gấp/mở (▶/▼) dùng chung cho các nhóm trường của
``StepConfigPanel`` — tách khỏi ``ui/co4e_config_panel.py`` (nguyên bản dòng
27-130).

Vấn đề đang có: ``StepConfigPanel`` (nay ở
``presentation/co4e/node_property_panel.py``) có 4 nhóm trường (Cơ bản, Model
& Quyền, Skills & Tệp, Agent song song), mỗi nhóm là một "card" gấp/mở độc
lập với animation riêng. Phần dựng card này (``_SectionHeader`` +
``_add_section``) không đọc/ghi bất kỳ trạng thái nào của ``StepConfigPanel``
(không có ``self._step``, không có ``ctx``) — nó chỉ nhận ``outer``/``title``
và trả về ``(form, card)`` để nơi gọi tự đổ các row vào — nên tách được thành
module riêng, giống cách ``AgentListPanel``/``SkillsListPanel`` đã tách khỏi
``ui/co4e_tab.py``. Giữ module riêng cũng là cách duy nhất để
``node_property_panel.py`` (chứa phần còn lại của ``StepConfigPanel``) không
vượt trần 400 dòng của CASAN Check 2.

Cách làm: dời NGUYÊN VĂN hằng số ``_SECTION_ANIM_MS``, class
``_SectionHeader`` và hàm ``_add_section`` sang đây — không đổi tên, không
đổi logic bên trong (kể cả các closure ``_on_finished``/``_toggle`` lồng
trong ``_add_section``); chỉ đường import đổi cho khớp độ sâu package mới
(``presentation/co4e/`` cách gốc ``cowork_local`` 3 cấp, thay vì 2 cấp như
``ui/``).
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QEasingCurve, QPropertyAnimation, Signal
from PySide6.QtWidgets import QFormLayout, QLabel, QVBoxLayout, QWidget

from ...i18n import bind_dynamic, tr
from ...theme import current_palette

_SECTION_ANIM_MS = 180


class _SectionHeader(QLabel):
    """A clickable label — a QPushButton's own style chrome (border, native
    button margin, focus rect) always leaves a taller minimum height than a
    plain label, even once its QSS padding is zeroed out, so the header that
    needs to sit tight against its neighbours is a label, not a button."""

    clicked = Signal()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        """Bấm trái vào tiêu đề mục thì gập/mở mục đó."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def showEvent(self, event) -> None:  # noqa: N802
        # fontMetrics() at construction time (before this label is ever part
        # of a shown top-level window) reflects the QSS font-size only if the
        # style has fully polished by then — on the very FIRST paint of the
        # Co4E screen it sometimes hasn't, so the fixed height computed in
        # _add_section is briefly wrong (too tall) until something else
        # triggers a relayout. Recomputing here, every time the label
        # actually becomes visible, means the first paint is never stale.
        """Tính lại chiều cao cố định mỗi lần nhãn thật sự hiện ra.

        ``fontMetrics()`` lúc dựng chỉ phản ánh cỡ chữ trong QSS nếu style đã được
        áp xong — ở lần vẽ ĐẦU TIÊN của màn Co4E thì đôi khi chưa, nên chiều cao
        tính trong ``_add_section`` bị sai (quá cao) cho tới khi có gì đó buộc bố
        cục tính lại. Tính lại ở đây thì lần vẽ đầu không bao giờ còn lệch.
        """
        self.setFixedHeight(self.fontMetrics().height())
        super().showEvent(event)


def _add_section(outer: QVBoxLayout, title_key: str) -> tuple[QFormLayout, QWidget]:
    """One group of fields, collapsed to just its heading by default and
    independently expandable, so a long step config reads as a short list of
    group names until you open the one you need. Deliberately bare — no card
    border/background/box — the ▶/▼ marker and the heading text are the only
    things separating one group from the next; opening one never closes
    another (not an accordion, not a tab bar). Returns ``(form, card)``: add
    the group's rows to ``form``; ``card`` is the whole section (header +
    body) — hide it to remove the group entirely (e.g. for a section that
    only applies to some steps), rather than hiding individual rows inside
    an always-visible header.

    Nhận KHOÁ dịch, không nhận chuỗi đã dịch: nhãn mục do hàm này tự dựng nên
    nơi gọi không giữ tham chiếu nào để áp lại: truyền ``tr(...)`` vào đây thì
    bốn tiêu đề đứng nguyên ở ngôn ngữ lúc dựng panel."""
    p = current_palette()
    card = QWidget()
    card_lay = QVBoxLayout(card)
    card_lay.setContentsMargins(0, 0, 0, 0)
    card_lay.setSpacing(0)

    header = _SectionHeader()
    header.setCursor(Qt.PointingHandCursor)
    header.setStyleSheet(f"font-weight:400; font-size:13px; color:{p.text}; padding:0; margin:0;")
    header.setContentsMargins(0, 0, 0, 0)
    # QSS font-size only lands on the widget's actual QFont (and therefore
    # its fontMetrics()) once the style sheet is polished — ensurePolished()
    # forces that now, so the fixed height below is computed from the 12px
    # font just set above, not the default one this label was constructed
    # with. A label's natural sizeHint still reserves font leading above/
    # below the glyphs on top of the (now zeroed) QSS padding — pinning the
    # height to the text's actual cap-to-baseline span is what closes that
    # last gap without clipping the ▶ glyph, the title, or Vietnamese
    # diacritics.
    header.ensurePolished()
    header.setFixedHeight(header.fontMetrics().height())
    card_lay.addWidget(header)

    body = QWidget()
    body.setVisible(False)
    body.setMaximumHeight(0)
    form = QFormLayout(body)
    form.setContentsMargins(0, 6, 0, 0)
    card_lay.addWidget(body)

    anim = QPropertyAnimation(body, b"maximumHeight", body)
    anim.setDuration(_SECTION_ANIM_MS)
    anim.setEasingCurve(QEasingCurve.InOutCubic)

    is_open = False

    def _sync_header() -> None:
        """Nhãn mục: dấu gập/mở hiện tại + tiêu đề theo ngôn ngữ đang chọn."""
        header.setText(f"{'▼' if is_open else '▶'} {tr(title_key)}")

    # Ràng buộc ĐỘNG chứ không bind cứng một chuỗi: nhãn này mang cả trạng thái
    # gập/mở, nên bind cứng sẽ trả nó về ▶ mỗi lần người dùng đổi ngôn ngữ.
    bind_dynamic(header, _sync_header)

    def _on_finished() -> None:
        """Hiệu ứng gập/mở chạy xong: bỏ trần chiều cao khi đang mở, để bước có nhiều
        trường không bị cắt cụt.
        """
        if is_open:
            # Uncapped once open, so switching to a step whose fields make
            # this section taller/shorter (e.g. a parallel node's sub-agent
            # list appearing) is never clipped by the height this animation
            # last landed on.
            body.setMaximumHeight(16_777_215)
        else:
            body.setVisible(False)
    anim.finished.connect(_on_finished)

    def _toggle() -> None:
        """Lật trạng thái gập/mở của một mục và chạy hiệu ứng tương ứng."""
        nonlocal is_open
        is_open = not is_open
        _sync_header()
        anim.stop()
        if is_open:
            body.setVisible(True)
            anim.setStartValue(body.height())
            anim.setEndValue(body.sizeHint().height())
        else:
            anim.setStartValue(body.height())
            anim.setEndValue(0)
        anim.start()
    header.clicked.connect(_toggle)

    outer.addWidget(card)
    return form, card
