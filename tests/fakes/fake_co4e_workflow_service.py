"""``Co4EWorkflowService`` giả — cho widget Co4E Studio (presentation/) và cho
test khác dùng khi service thật
(``application/workflows/co4e_workflow_service.py``) chưa được ``bootstrap.py``
lắp vào, hoặc khi test không muốn chạm đĩa/AI thật.

Chạy hoàn toàn trong bộ nhớ, đồng bộ, không cần ``runner`` thật (không
``AgentWorker``/``QThread`` nào được tạo): ``start()`` ghi nhận run ở trạng
thái "running" rồi đứng yên — muốn mô phỏng tiến trình thì test tự gọi
``deliver_event``/``mark_finished``/``mark_failed``, giống hệt cách
``tests/characterization/test_co4e_run_manager_behavior.py`` seed tay vào
``Co4ERunManager`` thật rồi gọi ``_on_event``/``_on_finished``/``_on_failed``.

Ví dụ dùng::

    >>> from tests.fakes.fake_co4e_workflow_service import FakeCo4EWorkflowService
    >>> class _Wf:
    ...     id = "wf1"; name = "Flow"; nodes = []; edges = []
    >>> svc = FakeCo4EWorkflowService()
    >>> run_id = svc.start(_Wf())
    >>> svc.started_workflows[0].id
    'wf1'
    >>> svc.runs()[0].status
    'running'
    >>> svc.mark_finished(run_id)
    >>> svc.runs()[0].status
    'done'
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional

from cowork_local.domain.workflows.run_record import RunRecord

# Mirror dung gia tri cua STEP_DONE/STEP_ERROR/STEP_PLANNED (core/co4e.py) ma
# khong import core/ o day -- fake nay chi phu thuoc domain/, giu no nhe va
# nhanh de import trong test cua team khac.
_TERMINAL_NODE = {"done", "error", "planned"}


class FakeCo4EWorkflowService:
    """Bản giả của ``Co4EWorkflowService`` — cùng API công khai, ghi lại mọi
    lời gọi để test khẳng định được "có gọi service không" và "gọi với gì"."""

    def __init__(self):
        self._runs: Dict[str, RunRecord] = {}
        self._seq = 0
        self._project_id: str = ""
        self._output_root: Optional[Path] = None
        self._changed_callbacks: List[Callable[[], None]] = []
        self._event_callbacks: List[Callable[[str, dict], None]] = []
        #: moi workflow da duoc start(), dung thu tu goi -- test khang dinh
        #: "co goi service.start() khong" ma khong can thuc thi that.
        self.started_workflows: list = []
        self.stopped_run_ids: List[str] = []
        self.removed_run_ids: List[str] = []
        self.renamed: List[tuple] = []

    # ---- callback thay Signal (giong Co4EWorkflowService that) -------------
    def on_changed(self, cb: Callable[[], None]) -> None:
        self._changed_callbacks.append(cb)

    def on_event(self, cb: Callable[[str, dict], None]) -> None:
        self._event_callbacks.append(cb)

    def _emit_changed(self) -> None:
        for cb in self._changed_callbacks:
            cb()

    def _emit_event(self, run_id: str, ev: dict) -> None:
        for cb in self._event_callbacks:
            cb(run_id, ev)

    # ---- lifecycle ----------------------------------------------------
    def start(self, wf, *, skill_map=None, plan_mode: bool = False, only_nodes=None,
              seed_outputs=None, manual: bool = False, label: Optional[str] = None) -> str:
        self._seq += 1
        run_id = f"run{self._seq}"
        nodes = getattr(wf, "nodes", None) or []
        total = len(only_nodes) if only_nodes else len(nodes)
        record = RunRecord(run_id, getattr(wf, "id", ""), label or getattr(wf, "name", ""),
                            total, plan_mode, manual, project_id=self._project_id)
        self._runs[run_id] = record
        self.started_workflows.append(wf)
        self._emit_changed()
        return run_id

    # ---- hook gia lap tien trinh (goi TU TEST, khong phai tu runner that) --
    def deliver_event(self, run_id: str, ev: dict) -> None:
        """Mo phong dung ``Co4EWorkflowService._on_event`` that."""
        record = self._runs.get(run_id)
        if record is not None and isinstance(ev, dict):
            t = ev.get("type")
            if t == "node_status":
                record.node_status[ev.get("node_id")] = ev.get("status")
                record.done = sum(1 for s in record.node_status.values() if s in _TERMINAL_NODE)
                self._emit_changed()
            elif t == "run_done":
                if record.status == "running":
                    record.status = "done" if ev.get("ok", True) else "error"
                self._emit_changed()
        self._emit_event(run_id, ev)

    def mark_finished(self, run_id: str) -> None:
        record = self._runs.get(run_id)
        if record is not None and record.status == "running":
            record.status = "done"
            self._emit_changed()

    def mark_failed(self, run_id: str, err: str) -> None:
        record = self._runs.get(run_id)
        if record is not None:
            record.status = "error"
            record.error = str(err)
            self._emit_event(run_id, {"type": "run_error", "error": str(err)})
            self._emit_changed()

    # ---- control --------------------------------------------------------
    def stop(self, run_id: str) -> None:
        record = self._runs.get(run_id)
        if record is not None and record.running:
            record.status = "stopped"
            self.stopped_run_ids.append(run_id)
            self._emit_changed()

    def stop_all(self) -> None:
        for run_id in [r for r, rec in self._runs.items() if self._belongs(rec)]:
            self.stop(run_id)

    def rename(self, run_id: str, new_name: str) -> None:
        record = self._runs.get(run_id)
        new_name = (new_name or "").strip()
        if record is None or not new_name or new_name == record.name:
            return
        record.name = new_name
        if record.wf is not None:
            record.wf["name"] = new_name
        self.renamed.append((run_id, new_name))
        self._emit_changed()

    def remove(self, run_id: str) -> None:
        self._runs.pop(run_id, None)
        self.removed_run_ids.append(run_id)
        self._emit_changed()

    def clear_finished(self) -> None:
        for run_id in [r for r, rec in self._runs.items() if not rec.running and self._belongs(rec)]:
            self._runs.pop(run_id, None)
        self._emit_changed()

    # ---- queries ----------------------------------------------------------
    def _belongs(self, r: RunRecord) -> bool:
        return getattr(r, "project_id", "") == self._project_id

    def runs(self) -> List[RunRecord]:
        return [r for r in self._runs.values() if self._belongs(r)]

    def all_runs(self) -> List[RunRecord]:
        return list(self._runs.values())

    def get(self, run_id: str) -> Optional[RunRecord]:
        return self._runs.get(run_id)

    def active_count(self) -> int:
        return sum(1 for r in self._runs.values() if r.running and self._belongs(r))

    def set_current_project(self, project_id: str) -> None:
        pid = project_id or ""
        if pid != self._project_id:
            self._project_id = pid
            self._emit_changed()

    def set_output_root(self, root) -> None:
        self._output_root = Path(root) if root else None
