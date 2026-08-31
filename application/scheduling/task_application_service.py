"""TaskApplicationService - task CRUD + dispatch, outside the widget (R07-T04).

``ui/schedule_task_tab.py`` currently does all of this by importing
``core/tasks.py`` module functions directly and calling
``self.scheduler.run_now(...)`` inline inside Qt slot methods
(``_run_now``, ``_context_menu``'s duplicate/pause/delete branches,
``_on_task_dropped``'s per-lane business rules). None of it is Qt — it's
plain CRUD plus a few small rules ("a manual task never auto-runs",
"dropping a card on Done disables its schedule so it won't re-fire",
"dropping on Scheduled with no time set needs the editor, not a silent
no-op") — but it can only be exercised today by driving the real widget.

This service is the seam ``presentation/scheduling/kanban_board_widget.py``
(R08-T11) calls instead: same rules, same
:class:`~infrastructure.persistence.json.task_repository_impl.TaskRepository`
underneath, testable with no Qt at all.

Pure Python: no Qt import. ``run_now`` dispatch is a plain injected callable
(production wires ``TaskScheduler.run_now``; tests inject a stub), the same
constructor-injection shape ``application/conversations/conversation_
application_service.py`` (R04-T03) uses for its provider factory.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

# "TaskRepository" here is a Protocol-shaped name, not an import: this module
# only calls .get/.save/.delete/.duplicate, so any object with that shape
# (the real infrastructure.persistence.json.task_repository_impl.TaskRepository,
# or a test double) works without this file importing infrastructure/ at
# module scope.
RunNowFn = Callable[[str], bool]


@dataclass
class RunNowResult:
    """Outcome of asking a task to run immediately.

    ``reason`` is one of ``""`` (ok), ``"not_found"``, ``"manual_task"``
    (manual tasks never auto-run — spec: they exist to be run by a human),
    ``"no_scheduler"`` (no ``run_now`` callable was wired in), or
    ``"already_running"`` (the scheduler's own dedupe rejected it).
    """

    ok: bool
    reason: str = ""


@dataclass
class MoveResult:
    """Outcome of dropping a task card onto a Kanban lane
    (``move_to_status``). The caller (kanban widget) uses the flags to decide
    what to show — a full re-render, a "task is running" toast, or opening
    the task editor — without re-deriving the business rule itself."""

    task: Optional[Dict[str, Any]]
    blocked: bool = False          # dropped while already running — ignored
    ran_now: bool = False          # dropped on the Running lane — dispatched
    run_now_result: Optional[RunNowResult] = None
    needs_schedule: bool = False   # dropped on Scheduled with no run_at set — needs editing


class TaskApplicationService:
    """CRUD + dispatch for Schedule Task, backed by a ``TaskRepository``.

    Args:
        repository: a ``TaskRepository``-shaped object (``.get``, ``.save``,
            ``.delete``, ``.duplicate``). Production passes
            ``infrastructure.persistence.json.task_repository_impl.
            TaskRepository()``; tests pass one scoped to a ``tmp_path``.
        run_now: ``(task_id) -> bool``. Production passes
            ``TaskScheduler.run_now``; ``None`` means no scheduler is wired
            (matches the widget's own "no scheduler" guard today).
    """

    def __init__(self, repository: Any, run_now: Optional[RunNowFn] = None) -> None:
        """``run_now`` để None thì service chỉ đọc/ghi task, không chạy được cái nào —
        đúng cho ngữ cảnh không có scheduler (test, hay màn chỉ xem).
        """
        self._repository = repository
        self._run_now = run_now

    # -- single-task actions ------------------------------------------------ #
    def run_now(self, task_id: str) -> RunNowResult:
        """Dispatch ``task_id`` immediately. A "Run now" always counts as
        manual approval (spec §13) — this is the ONE path that bypasses
        ``execution.requires_approval``, same as the scheduler's own
        ``run_now`` already does."""
        task = self._repository.get(task_id)
        if task is None:
            return RunNowResult(False, "not_found")
        if task.get("task_type") == "manual":
            return RunNowResult(False, "manual_task")
        if self._run_now is None:
            return RunNowResult(False, "no_scheduler")
        ok = self._run_now(task_id)
        return RunNowResult(ok, "" if ok else "already_running")

    def duplicate(self, task_id: str) -> Optional[Dict[str, Any]]:
        """A saved copy with a fresh identity — see
        ``core/tasks.py::duplicate_task`` for what's preserved/reset."""
        task = self._repository.get(task_id)
        if task is None:
            return None
        dup = self._repository.duplicate(task)
        self._repository.save(dup)
        return dup

    def toggle_pause(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Pause a task, or resume a paused one back to Backlog (matches
        ``ui/schedule_task_tab.py``'s context-menu action exactly — resuming
        does NOT restore whatever status the task had before pausing, only
        Backlog, so the user re-schedules explicitly rather than a stale
        schedule silently re-firing)."""
        task = self._repository.get(task_id)
        if task is None:
            return None
        task["status"] = "backlog" if task.get("status") == "paused" else "paused"
        self._repository.save(task)
        return task

    def delete(self, task_id: str) -> bool:
        """Xoá một task; trả về ``False`` nếu id không tồn tại."""
        if self._repository.get(task_id) is None:
            return False
        self._repository.delete(task_id)
        return True

    def bulk_delete(self, task_ids: List[str]) -> int:
        """Delete every id in ``task_ids``; returns how many actually
        existed (mirrors ``_confirm_and_delete_selected``'s best-effort
        loop — a stale id in the selection doesn't abort the rest)."""
        return sum(1 for tid in task_ids if self.delete(tid))

    # -- Kanban drag/drop ----------------------------------------------------- #
    def move_to_status(self, task_id: str, new_status: str) -> Optional[MoveResult]:
        """Apply the business rule behind dropping a card into a lane
        (``ui/schedule_task_tab.py::_on_task_dropped``, moved here so it's
        testable without a real ``QListWidget`` drag gesture):

        * already running -> the drop is ignored (a running task can't be
          re-filed by dragging it).
        * dropped on Running -> runs it now (counts as manual approval).
        * dropped on Done -> marks it done AND disables its schedule, so a
          repeating task marked done by hand doesn't quietly re-fire later.
        * dropped on Scheduled with no ``run_at`` set yet -> saved as-is but
          flagged ``needs_schedule`` — the caller should open the editor
          rather than leave a Scheduled card that will never actually run.
        * anything else -> plain status change.
        """
        task = self._repository.get(task_id)
        if task is None:
            return None
        if task.get("status") == "running":
            return MoveResult(task=task, blocked=True)
        if new_status == "running":
            result = self.run_now(task_id)
            return MoveResult(task=self._repository.get(task_id), ran_now=True, run_now_result=result)
        if new_status == "done":
            task["status"] = "done"
            task["schedule"]["enabled"] = False
            self._repository.save(task)
            return MoveResult(task=task)
        task["status"] = new_status
        if new_status == "scheduled" and not task["schedule"].get("enabled"):
            if task["schedule"].get("run_at"):
                task["schedule"]["enabled"] = True
            else:
                self._repository.save(task)
                return MoveResult(task=task, needs_schedule=True)
        self._repository.save(task)
        return MoveResult(task=task)


__all__ = ["TaskApplicationService", "RunNowResult", "MoveResult"]
