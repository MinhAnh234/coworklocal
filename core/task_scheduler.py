"""Schedule Task module — the background scheduler engine (Qt layer).

A QTimer ticks every 30s; due tasks (status=Scheduled, schedule enabled,
run_at reached) start on an ``AgentWorker`` thread each, so the UI never
blocks and several tasks can run at once. Pure decisions (what's due, what
happens after a run, chain rules) live in ``tasks.py`` where they're unit
tested; this class applies them and persists the results.

Safety (spec §13): a task with ``requires_approval`` is NEVER auto-run — the
scheduler parks it in Waiting Input; only an explicit "Run now" from the user
counts as the manual confirmation that lets it execute.
"""
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import QObject, Signal

from .tasks import (
    advance_after_run, chain_action, dependencies_met, due_tasks, format_run_at,
    list_tasks, load_task, previous_output_ready, record_interrupted_run, save_task,
)
from .task_executors import execute_task, new_run_id
from .worker import AgentWorker

TICK_MS = 30_000
STOP_WAIT_SECS = 10.0


class TaskScheduler(QObject):
    """Bộ chạy task theo lịch: cứ mỗi nhịp lại tìm task tới hạn và chạy chúng ở
    luồng nền.

    Đồng hồ được tiêm qua ``clock=`` (R07-T03) nên test chạy được mà không cần
    ``QTimer`` thật, và các checker UI vô hiệu hoá được nó để việc dựng cửa sổ
    không vô tình chạy task thật của người dùng.
    """
    tasks_changed = Signal()           # any status/log change → UI refresh
    task_started = Signal(str)         # task_id
    task_finished = Signal(str, bool)  # task_id, ok
    # A running task's conversation session actually EXISTS in History now —
    # safe to refresh the sidebar and expect to see it (unlike task_started,
    # which fires before the worker thread has even begun).
    history_ready = Signal(str)        # task_id

    def __init__(self, ctx, tasks_dir: Optional[Path] = None, parent=None, clock=None):
        """``clock`` để None thì tự dựng ``QtSchedulerClock`` thật, nên mọi chỗ gọi cũ
        không phải sửa; test tiêm ``FakeClock`` để điều khiển nhịp bằng tay.
        """
        super().__init__(parent)
        self.ctx = ctx
        self.tasks_dir = tasks_dir            # None → default TASKS_DIR
        self._workers: Dict[str, AgentWorker] = {}   # task_id → running worker
        self._retries: Dict[str, int] = {}
        self._session_ids: Dict[str, str] = {}       # task_id → its run's History session id
        # R07-T03: the QTimer this class used to own directly is now behind a
        # small clock interface (start/stop/pump) — see
        # infrastructure/qt/qt_scheduler_clock.py::QtSchedulerClock. Defaulting to a
        # real one here keeps every existing production call site (which
        # never passes `clock=`) unchanged; tests inject
        # tests/fakes/fake_clock.py::FakeClock to control ticks by hand with
        # no Qt event loop running. Imported lazily so importing core.tasks/
        # core.task_scheduler for the Qt-free logic doesn't require the Qt
        # adapter module to even exist in a headless test context.
        if clock is None:
            from ..infrastructure.qt.qt_scheduler_clock import QtSchedulerClock
            clock = QtSchedulerClock(self)
        self._clock = clock

    # ---- lifecycle ----------------------------------------------------
    def start(self) -> None:
        """Bắt đầu chạy: thu dọn task còn kẹt từ lần chạy trước, đuổi kịp task đã quá
        hạn, rồi bật nhịp đếm.
        """
        self._recover_orphans()
        self.tick()          # catch up overdue tasks right at app start
        self._clock.start(TICK_MS, self.tick)

    def stop(self) -> None:
        """Request every running worker to stop, then WAIT (bounded) for them
        to actually exit, pumping the event loop while we do.

        Without this, a worker still mid-run when the window closes finishes
        its job on its own OS thread and tries to deliver its
        ``finished_ok``/``failed`` signal as a queued cross-thread call — but
        nothing is left processing this object's event loop by then, so
        ``_on_done`` (the only place that writes the run into the task's
        history) never runs. The task's real output can already be sitting on
        disk while its history stays stuck on "running" forever. Pumping
        the clock here lets that queued signal actually get delivered before
        the app finishes quitting.
        """
        self._clock.stop()
        deadline = time.monotonic() + STOP_WAIT_SECS
        while self._workers and time.monotonic() < deadline:
            for w in list(self._workers.values()):
                w.request_stop()
            self._clock.pump()
            for w in list(self._workers.values()):
                w.wait(50)
        # Anything still alive past the deadline is abandoned here;
        # _recover_orphans() records it as interrupted on the next launch.

    def _recover_orphans(self) -> None:
        """Tasks left 'running' by a previous session (app closed mid-run,
        or killed outright before stop()'s wait loop above could finish):
        record the interruption as a real run entry — via the same
        ``advance_after_run`` a normal completion uses — instead of silently
        dropping it, so the task's history always shows that a run happened
        and points the user at the output folder to check what it produced."""
        for task in list_tasks(self.tasks_dir):
            if task.get("status") != "running":
                continue
            record_interrupted_run(
                task, new_run_id(),
                error=("Interrupted: app closed while this run was still in "
                       "progress. Check the task's output folder — the run "
                       "may have already produced output before it was cut off."),
            )
            save_task(task, self.tasks_dir)

    # ---- tick / dispatch ----------------------------------------------
    def tick(self) -> None:
        """Một nhịp: chạy mọi task đã tới hạn tại thời điểm này."""
        now = datetime.now()
        changed = False
        for task in due_tasks(list_tasks(self.tasks_dir), now):
            tid = task["task_id"]
            if tid in self._workers:
                continue   # already running
            if task["execution"].get("requires_approval"):
                task["status"] = "waiting_input"   # waits for a manual Run now
                save_task(task, self.tasks_dir)
                changed = True
                continue
            if (not dependencies_met(task, self.tasks_dir)
                    or not previous_output_ready(task, self.tasks_dir)):
                # A prerequisite hasn't finished (fan-in) / chained input
                # isn't there yet — the task doesn't have its input, park it.
                # _release_dependents re-enqueues it the moment the last
                # prerequisite completes.
                task["status"] = "waiting_input"
                save_task(task, self.tasks_dir)
                changed = True
                continue
            self._start(task)
            changed = True
        if changed:
            self.tasks_changed.emit()

    def run_now(self, task_id: str) -> bool:
        """Explicit user action — counts as manual approval (spec §13)."""
        task = load_task(task_id, self.tasks_dir)
        if not task or task_id in self._workers:
            return False
        self._start(task)
        self.tasks_changed.emit()
        return True

    def is_running(self, task_id: str) -> bool:
        """Task này có đang chạy không."""
        return task_id in self._workers

    def running_count(self) -> int:
        """Number of tasks currently executing — Monitoring Dashboard's
        Agent Status panel reads this rather than tracking its own state."""
        return len(self._workers)

    def running_session_ids(self) -> set:
        """History session ids for currently-running task runs — merged into
        the sidebar's own "mark as running" set (``app.py::_running_session_ids``)
        so a Schedule Task's run shows the same live "running" indicator an
        interactive Cowork/Code chat gets."""
        return set(self._session_ids.values())

    # ---- internals -----------------------------------------------------
    def _start(self, task: dict) -> None:
        """Khởi động một task ở luồng nền và đánh dấu trạng thái 'running'."""
        tid = task["task_id"]
        run_id = new_run_id()
        task["status"] = "running"
        save_task(task, self.tasks_dir)
        self.task_started.emit(tid)

        def job(worker: AgentWorker):
            """Chạy nền: thực thi task, chuyển tiếp sự kiện tiến độ và cờ huỷ."""
            return execute_task(self.ctx, task, run_id,
                                emit=worker.emit_event, cancel=worker.is_cancelled,
                                tasks_dir=self.tasks_dir)

        worker = AgentWorker(job)
        worker.event.connect(lambda ev, t=tid: self._on_worker_event(t, ev))
        worker.finished_ok.connect(lambda res, t=tid, r=run_id: self._on_done(t, r, res))
        worker.failed.connect(lambda err, t=tid, r=run_id: self._on_done(
            t, r, {"ok": False, "error": err, "output": "", "artifact": ""}))
        self._workers[tid] = worker
        worker.start()

    def _on_worker_event(self, task_id: str, ev: dict) -> None:
        """``_run_agent`` (task_executors.py) emits ``history_ready`` the
        MOMENT its run's session is actually written to History (right at
        the start of the run, then again after each turn) — listening for it
        here, instead of refreshing on ``task_started`` (which fires before
        the worker thread even begins), is what lets the UI actually show a
        Running task's session in Cowork/Code History while it's running."""
        if not isinstance(ev, dict) or ev.get("type") != "history_ready":
            return
        session_id = ev.get("session_id") or ""
        if session_id:
            self._session_ids[task_id] = session_id
        self.history_ready.emit(task_id)

    def _on_done(self, task_id: str, run_id: str, result: dict) -> None:
        """Task chạy xong: ghi kết quả, tính lần chạy kế tiếp, và kích hoạt task nối tiếp."""
        self._workers.pop(task_id, None)
        self._session_ids.pop(task_id, None)
        task = load_task(task_id, self.tasks_dir)
        if not task:
            return
        ok = bool(result.get("ok"))
        error = result.get("error", "")

        # Retry (before advancing state), capped by execution.max_retry.
        if not ok:
            tried = self._retries.get(task_id, 0)
            if tried < int(task["execution"].get("max_retry", 0) or 0):
                self._retries[task_id] = tried + 1
                self._start(task)
                return
        self._retries.pop(task_id, None)

        advance_after_run(task, ok, run_id, error)
        save_task(task, self.tasks_dir)
        self._notify(task, ok, error)
        self.task_finished.emit(task_id, ok)

        action = chain_action(task, ok)
        if action:
            self._apply_chain(task, *action)
        if ok:
            self._release_dependents(task["task_id"])
        self.tasks_changed.emit()

    def _release_dependents(self, finished_id: str) -> None:
        """Fan-in trigger: a task just completed successfully — any task
        parked in Waiting Input because it was waiting for this one (among
        possibly several parallel prerequisites) starts IMMEDIATELY once ALL
        of its prerequisites are done (no waiting for the next 30s tick)."""
        from .tasks import _all_prerequisites

        for task in list_tasks(self.tasks_dir):
            if task.get("status") != "waiting_input":
                continue
            if task["execution"].get("requires_approval"):
                continue   # still needs the user's explicit Run now
            if finished_id not in _all_prerequisites(task):
                continue
            if task["task_id"] in self._workers:
                continue   # already running
            if not dependencies_met(task, self.tasks_dir):
                continue   # some other prerequisite still pending
            if not previous_output_ready(task, self.tasks_dir):
                continue
            self._start(task)

    def _apply_chain(self, task: dict, verb: str, next_id: str) -> None:
        """Kích hoạt task nối tiếp theo luật ``run_next``.

        Task kế đang tạm dừng thì BỎ QUA — trình sửa task có cảnh báo trước về
        điều này.
        """
        nxt = load_task(next_id, self.tasks_dir)
        if not nxt or nxt.get("status") == "paused":
            return   # paused next task is skipped (warned about in the editor)
        if task["dependency"].get("pass_output_to_next"):
            nxt["input"]["mode"] = "previous_task_output"
            nxt["input"]["previous_task_id"] = task["task_id"]
            nxt["dependency"]["previous_task_id"] = task["task_id"]
        if verb == "enqueue":
            nxt["status"] = "scheduled"
            nxt["schedule"]["enabled"] = True
            nxt["schedule"]["run_at"] = format_run_at(datetime.now())
        else:   # await_confirm — parked until the user runs it
            nxt["status"] = "waiting_input"
        save_task(nxt, self.tasks_dir)

    def _notify(self, task: dict, ok: bool, error: str) -> None:
        """Gửi nhắc việc qua Teams hoặc Outlook khi task kết thúc.

        Đã chọn kênh thì báo cả khi chạy xong LẪN khi lỗi — im lặng lúc lỗi là
        kiểu hỏng tệ nhất của một tác vụ chạy nền.
        """
        ex = task["execution"]
        channel = ex.get("notify_channel", "none")
        # A chosen channel notifies on BOTH completion and error; the legacy
        # per-outcome flags still work (they route to Teams) when no channel set.
        if channel == "none":
            wants = ex.get("notify_on_complete") if ok else ex.get("notify_on_error")
            if not wants:
                return
            channel = "teams"
        title = task.get("title", "")
        status = "✅ done" if ok else "❌ failed"
        subject = f"[CoworkLocal] Task {status}: {title}"
        body = (error or "Completed.")[:2000]
        try:
            if channel == "outlook":
                from . import outlook_notify
                outlook_notify.send_via_outlook(ex.get("notify_email", ""), subject, body)
            else:  # "teams"
                notifier = self.ctx.teams_notifier()
                if notifier and notifier.configured():
                    notifier.send(subject, body,
                                  {"Task": title, "Type": task.get("task_type", "")})
        except Exception:  # noqa: BLE001 — notification must never break the run
            pass
