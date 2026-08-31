"""GraphMessagesView — the "Messages by day" tab of GraphRAG (R08-T14, split
out of ``graph_renderer.py`` to keep that file under the 400-line cap;
originally ``ui/structure_graph_view.py``, lines 427-497 of the original
1035-line file: ``_on_view_tab``, ``_toggle_messages``, ``_reload_messages``,
``_show_msg_json``).

A plain (non-Qt-widget) helper composed BY ``GraphRenderer`` — same
composition-to-respect-the-line-cap pattern as
``office_document_renderer.py``. Owns the ``QTreeWidget`` itself (built
here, added to the owner's stack at construction) since nothing else needs
it, but reaches into ``owner._stack``/``owner.web``/``owner.view``/
``owner.active_project_id`` to switch the shared stack and scope by project.
"""
from __future__ import annotations

from collections import OrderedDict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

from cowork_local.i18n import tr


class GraphMessagesView:
    """Tab "Tin nhắn" của GraphRAG: cây hội thoại gom theo ngày, bấm vào xem JSON.

    Một helper thuần (không phải widget) do ``GraphRenderer`` sở hữu; nó tự dựng
    cây và đưa vào stack dùng chung của chủ sở hữu.
    """
    def __init__(self, owner) -> None:
        """Dựng cây tin nhắn và đưa vào stack dùng chung của chủ sở hữu — helper thuần,
        không phải widget độc lập.
        """
        self._owner = owner
        self.widget = QTreeWidget()
        self.widget.setHeaderHidden(True)
        self.widget.itemClicked.connect(self._show_msg_json)
        owner._stack.addWidget(self.widget)

    def on_view_tab(self, index: int) -> None:
        """Tab 0 = graph, tab 1 = messages."""
        o = self._owner
        if index == 1:
            self.reload()
            o._stack.setCurrentWidget(self.widget)
        else:
            o._stack.setCurrentWidget(o.web if o.web is not None else o.view)

    def toggle(self) -> None:
        """Kept for callers that still ask for a flip (e.g. keyboard paths)."""
        o = self._owner
        showing = o._stack.currentWidget() is self.widget
        o.view_tabs.setCurrentIndex(0 if showing else 1)

    def reload(self) -> None:
        """Build the tree: day -> conversation. Click a conversation to see
        its messages as JSON. Scoped to the current project's history."""
        from cowork_local.core.history import list_conversations

        o = self._owner
        self.widget.clear()
        pid = o.active_project_id or ""
        by_day: "OrderedDict[str, list]" = OrderedDict()
        try:
            convs = list_conversations(o.ctx.config.history_dir())
        except Exception:  # noqa: BLE001
            convs = []
        for conv in convs:
            if pid and conv.get("project_id", "default") != pid:
                continue
            day = (conv.get("created") or "")[:10] or "—"
            by_day.setdefault(day, []).append(conv)
        if not by_day:
            self.widget.addTopLevelItem(QTreeWidgetItem([tr("structure.msgs_none")]))
            return
        for day in sorted(by_day, reverse=True):
            convs_d = by_day[day]
            day_item = QTreeWidgetItem([f"{day}   ({len(convs_d)})"])
            for conv in convs_d:
                it = QTreeWidgetItem([conv.get("title", "(untitled)")])
                it.setData(0, Qt.UserRole, str(conv.get("path", "")))
                day_item.addChild(it)
            self.widget.addTopLevelItem(day_item)
            day_item.setExpanded(True)

    def _show_msg_json(self, item, _col: int = 0) -> None:
        """Bấm một hội thoại trong cây: hiện toàn bộ nội dung của nó dưới dạng JSON đã
        thoát HTML ở khung chi tiết.
        """
        import html
        import json

        from cowork_local.core.history import load_conversation
        path = item.data(0, Qt.UserRole)
        if not path:
            return
        try:
            conv = load_conversation(path)
            payload = {"title": conv.get("title", ""), "created": conv.get("created", ""),
                       "kind": conv.get("kind", ""), "project_id": conv.get("project_id", ""),
                       "messages": conv.get("messages", [])}
            text = json.dumps(payload, ensure_ascii=False, indent=2)
        except Exception as exc:  # noqa: BLE001
            text = f"(could not read: {exc})"
        self._owner.raw_json_ready.emit(
            f'<pre style="white-space:pre-wrap; font-family:Consolas,monospace; '
            f'font-size:12px;">{html.escape(text)}</pre>')


__all__ = ["GraphMessagesView"]
