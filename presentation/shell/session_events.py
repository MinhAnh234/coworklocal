"""Lịch sử hội thoại và thông báo khi task chạy xong — R08-T10.

Gom những gì phản ứng với việc **có chuyện xảy ra ở nơi khác**: một task đã lên
lịch chạy xong, một phiên được lưu, danh sách project đổi.

Điểm dễ sai đã ghi lại trong ``_on_scheduled_task_done``: tín hiệu
``task_started`` bắn TRƯỚC khi luồng chạy bắt đầu, lúc đó phiên chưa có trên
đĩa — làm mới Lịch sử ở đó thì không thấy gì. Phải bám ``history_ready``.

Cùng kiểu mixin, xem ghi chú ở đầu ``nav_rail.py``.
"""
from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from ... import DISPLAY_NAME
from ...i18n import tr
from ...ui.workspace_tab import WorkspaceTab


class SessionEventsMixin:
    """Nối các sự kiện phiên chat vào vỏ cửa sổ: làm mới cột lịch sử, chấm trạng thái
    và nhãn thư mục khi project đổi tên.
    """
    def _running_session_ids(self):
        """All conversation ids currently running — interactive Cowork/Code
        chat tab AgentWorkers, plus Schedule Task runs (their own session,
        tracked by the scheduler), so a task's live run gets the same
        "running" marker in History an interactive chat gets."""
        return set(self.cowork.running_session_ids()) | self.task_scheduler.running_session_ids()
    def _refresh_history(self) -> None:
        """Rebuild the History list with the current conversation highlighted and
        the running ones marked. Deferred to the next event-loop tick: this is often
        triggered (via load_conversation) from inside the sidebar's own item-click
        handler, and clearing the tree there would delete the item mid-click."""
        from PySide6.QtCore import QTimer

        def _do() -> None:
            """Đồng bộ cột lịch sử với hội thoại đang mở và các hội thoại đang chạy."""
            current = self.cowork.session_id
            self.sidebar.set_view_state(current, self._running_session_ids())
            self.sidebar.refresh()
            self._refresh_rail_recents()   # the rail shortcut follows the panel

        # Coalesce bursts from turn/tool/history signals into one sidebar read.
        timer = getattr(self, "_history_refresh_timer", None)
        if timer is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(_do)
            self._history_refresh_timer = timer
        timer.start(0)
    def _on_scheduled_task_done(self, task_id: str, ok: bool) -> None:
        """Desktop notification for a finished scheduled task (toast always,
        tray balloon when the window isn't focused), then refresh History —
        cowork/co4e task runs just saved themselves as new sessions there."""
        from ...core.tasks import load_task

        task = load_task(task_id) or {}
        title = task.get("title", "")
        msg = (tr("app.toast.task_done", title=title) if ok
               else tr("app.toast.task_failed", title=title))
        self.toast.show_message(msg, ok=ok)
        if (self.tray is not None
                and self.ctx.config.data.get("tray", {}).get("notify_on_done", True)
                and not self.isActiveWindow()):
            self._tray.show_message(DISPLAY_NAME, msg, error=not ok)
        self._refresh_history()
    def _notify_task(self, tab, kind: str, result: dict) -> None:
        """Notify when a task finishes/fails (skip if more stages queued)."""
        if tab.composer.has_queue():
            return  # a flow / queue is still running — notify only at the end
        name = tr(f"app.tab.{kind}")
        err = (result or {}).get("error")
        # In-app popup at the top-left (shown whether or not the window is focused).
        self.toast.show_message(
            tr("app.toast.error", name=name) if err else tr("app.toast.done", name=name), ok=not err)
        # System-tray balloon only when the window isn't the active one.
        if self.tray is None:
            return
        if not self.ctx.config.data.get("tray", {}).get("notify_on_done", True):
            return
        if self.isActiveWindow():
            return  # user is looking at the window already
        err = (result or {}).get("error")
        title = tr("app.toast.error", name=name) if err else tr("app.toast.done", name=name)
        body = (err if err else (tab._last_assistant_text() or "Task completed."))[:140]
        self._tray.show_message(title, body, error=bool(err))
    def _restore_sessions(self) -> None:
        """Reopen the last conversation per tab (recover after a crash/abrupt exit)."""
        from pathlib import Path

        from ...core.history import load_conversation

        last = self.ctx.config.data.get("last_session", {})
        path = last.get("cowork", "")
        if path and Path(path).exists():
            try:
                self.cowork.load_conversation(load_conversation(path))
                # Reflect the restored thread's project in the Workspace home
                # (selecting the matching row won't wipe it — the project id
                # already matches, so _bind_project starts no new session).
                # Skip forcing the Cowork tab open for a project that no
                # longer exists (deleted since this session was saved) — that
                # would show the Cowork page while the tab strip still says
                # "no project selected" (see WorkspaceTab._on_sidebar_open).
                pid = self.cowork.project_id
                if pid in ("", "default") or self.workspace._select_project_row(pid):
                    self.workspace._show_cowork_tab()
            except Exception:
                pass
    def _on_projects_changed(self) -> None:
        """Project được tạo/sửa/xoá: gom nhóm lại cột lịch sử và cập nhật nhãn thư mục."""
        self.sidebar.refresh()                 # History regroups by project
        self.cowork._apply_output_folder_label()  # project may have been renamed
        if getattr(self, "structure", None) is not None:
            self.structure._refresh_project_combo()   # GraphRAG's project lock list follows too
