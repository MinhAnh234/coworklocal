"""``kv_row`` — the "label — stretch — value" row shape that
``ui/monitoring_tab.py`` used to redefine as 3 byte-identical local closures
(Sandbox Details' ``_kv``, Permissions' ``_pkv``, the detail panel's
``_field``). Overview's Resource Usage row (``_pair``) is a genuinely
different layout (inline on one horizontal line with "·" separators, no
stretch) and is intentionally NOT folded into this helper — unifying it would
risk a visible layout change.
"""
from __future__ import annotations

from typing import Tuple

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout


def kv_row(outer_layout: QVBoxLayout, hint_object_name: str = "hint") -> Tuple[QLabel, QLabel]:
    """Appends a new ``label — stretch — value`` row to ``outer_layout``.
    Returns ``(label, value)``."""
    row = QHBoxLayout()
    label = QLabel()
    label.setObjectName(hint_object_name)
    value = QLabel()
    row.addWidget(label)
    row.addStretch(1)
    row.addWidget(value)
    outer_layout.addLayout(row)
    return label, value
