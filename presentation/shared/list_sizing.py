"""Width of a navigation list whose current row is drawn bold.

The theme draws the selected ``sectionIndex`` row with ``font-weight: 600``
and 10px padding each side (``theme/qss.py``). Sizing the list from the plain
font left the selected label too wide for its row, so "Sandbox Security
Layer" was cut off in Settings as soon as it was picked.
"""
from __future__ import annotations

from typing import Iterable

from PySide6.QtGui import QFont, QFontMetrics

#: Item padding (10px x 2) + item radius + list frame, with a little slack.
ROW_CHROME_PX = 48


def selected_label_width(widget, labels: Iterable[str]) -> int:
    """Pixels needed to show the widest of ``labels`` in the bold selected style."""
    widget.ensurePolished()
    bold = QFont(widget.font())
    bold.setWeight(QFont.Weight.DemiBold)
    metrics = QFontMetrics(bold)
    return max((metrics.horizontalAdvance(label) for label in labels), default=0) + ROW_CHROME_PX


__all__ = ["ROW_CHROME_PX", "selected_label_width"]
