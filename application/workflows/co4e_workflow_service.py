"""``Co4EWorkflowService`` — nửa "hành vi" tách ra từ ``Co4ERunManager`` cũ.

Bối cảnh: ``core/co4e_run_manager.py::Co4ERunManager`` là một ``QObject`` gộp
chung dữ liệu run (nay là ``domain/workflows/run_record.py::RunRecord``), logic
chạy job trên ``AgentWorker``/``QThread``, và logic đọc/ghi lịch sử ra đĩa. File
này là phần còn lại sau khi tách DTO: quản lý vòng đời nhiều run cùng lúc, các
hook nhận sự kiện từ worker, và lưu/nạp lịch sử — nhưng THUẦN PYTHON, không kế
thừa ``QObject`` và không tự dựng ``QThread`` (``application/`` cấm PySide6).

Hai điều thay ``Signal`` cũ:
  * ``changed = Signal()`` -> danh sách callback ``self._changed_callbacks`` +
    ``on_changed(cb)`` để đăng ký; mọi chỗ code cũ gọi ``self.changed.emit()``
    nay gọi ``self._emit_changed()``, gọi callback theo ĐÚNG thứ tự đã đăng ký.
  * ``event = Signal(str, dict)`` -> ``self._event_callbacks`` + ``on_event(cb)``,
    tương tự, thay ``self.event.emit(rid, ev)`` bằng ``self._emit_event(rid, ev)``.
  * ``self.changed.connect(self._save_history)`` (lớp cũ tự nối signal của
    chính nó vào slot riêng, trong ``__init__``) -> ở đây gọi thẳng
    ``self._save_history()`` làm bước ĐẦU TIÊN bên trong ``_emit_changed()``,
    trước khi chạy các callback đã đăng ký từ bên ngoài. Chọn cách "gọi thẳng"
    (thay vì "đăng ký như callback đầu tiên") vì nó khớp với thứ tự nối cũ
    (``_save_history`` luôn được nối sớm nhất trong ``__init__`` nên luôn chạy
    trước mọi slot ngoài nối sau) mà không cần một danh sách callback nội bộ
    riêng chỉ để chứa đúng một phần tử cố định.

``start()`` KHÔNG tự tạo ``AgentWorker``/``QThread`` — nó nhận một ``runner``
(``WorkflowRunner`` Protocol, mặc định ``None``) tiêm qua constructor. Adapter
Qt thật (bọc ``AgentWorker`` — xem ``core/worker.py``) là việc của widget ở
``presentation/``, không viết ở đây; test dùng fake chạy đồng bộ
(``tests/fakes/fake_co4e_workflow_service.py`` hoặc fake cục bộ trong
``tests/test_co4e_workflow_service.py``).

KHÔNG xoá/sửa ``core/co4e_run_manager.py`` — lớp cũ tiếp tục chạy song song
cho tới khi widget Co4E Studio thật (``ui/co4e_tab.py``) chuyển hẳn sang dùng
service này.

SEAM · dựng 2026-08-25 · chưa nối dây (F-05)
------------------------------------------------------------
Được nối khi: ``ui/co4e_tab.py`` bỏ ``Co4ERunManager`` và nhận service này qua ``build_co4e_tab(ctx, workflow_service)``.
Để dormant thì sao: Hai bản cùng giữ vòng đời run đang chạy song song. Càng
để lâu thì sửa một lỗi lại phải sửa hai nơi — và đến một lúc sẽ có người
quên nơi thứ hai.

Cổng ``scripts/check_orphan_modules.py`` đếm tuổi seam từ ngày trên
và nhắc khi quá ``SEAM_MAX_AGE_DAYS``. Đổi nội dung dòng đó thì cổng
đọc theo — đừng sửa ngày để làm im lời nhắc.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Protocol, Set

from ...core.co4e import CO4E_DIR, STEP_DONE, STEP_ERROR, STEP_PLANNED, Workflow, slugify, workflow_to_dict
from ...domain.workflows.run_record import RunRecord
from .co4e_run_history import RunHistoryStore

_TERMINAL_NODE = {STEP_DONE, STEP_ERROR, STEP_PLANNED}


def _now_str() -> str:
    """Mốc thời gian hiện tại dạng 'YYYY-MM-DD HH:MM' — đúng định dạng lịch sử run đang lưu."""
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _current_user() -> str:
    """Best-effort creator name for a run (signed-in MS365 identity -> OS user)."""
    return os.environ.get("USERNAME") or os.environ.get("USER") or "you"


# ---- ports (Protocol) — thay QThread thật bằng thứ tiêm được ---------------
class RunnerJob(Protocol):
    """Bề mặt tối thiểu mà job workflow cần từ 'worker' của nó.

    Tương ứng ``AgentWorker.emit_event``/``AgentWorker.is_cancelled`` cũ
    (``core/worker.py``) — giữ nguyên chữ ký đó để hàm job bên trong
    ``co4e_runner.run_workflow`` không phải đổi khi runner đứng sau là
    ``AgentWorker``/``QThread`` thật (adapter ở presentation/) hay là fake
    đồng bộ trong test.
    """

    def emit_event(self, ev: dict) -> None:
        """Đẩy một sự kiện tiến độ từ luồng nền về service."""
        ...

    def is_cancelled(self) -> bool:
        """``True`` khi người dùng đã bấm dừng — thân job phải tự kiểm để thoát sớm."""
        ...


class RunWorkerHandle(Protocol):
    """Điều khiển một job đang chạy nền — tương ứng phần
    ``AgentWorker.request_stop()`` cũ mà ``Co4ERunManager.stop()`` gọi."""

    def request_stop(self) -> None:
        """Xin dừng run. Chỉ là yêu cầu: job đang chạy phải tự thấy qua
        ``is_cancelled()`` rồi thoát, không ai giết luồng giữa chừng.
        """
        ...


class WorkflowRunner(Protocol):
    """Cổng chạy một job nền, tiêm qua constructor ``Co4EWorkflowService``.

    Thay cho việc service tự ``AgentWorker(job); worker.start()`` (cần
    ``QThread`` -> cấm ở ``application/``). Bên gọi ``start()`` truyền vào
    ``job`` với đúng chữ ký cũ (``job(worker) -> Optional[dict]``); runner chịu
    trách nhiệm chạy nó (nền thật hay đồng bộ) và gọi lại ba callback tương ứng
    ba signal cũ của ``AgentWorker`` (``event``/``finished_ok``/``failed``).
    """

    def start(self, run_id: str, job: Callable[[RunnerJob], Optional[dict]],
              on_event: Callable[[dict], None],
              on_finished: Callable[[Optional[dict]], None],
              on_failed: Callable[[str], None]) -> RunWorkerHandle:
        """Chạy ``job`` và trả về tay cầm để dừng nó."""
        ...


class Co4EWorkflowService:
    """Tầng application: vòng đời nhiều run Co4E cùng lúc, thuần Python.

    Vai trò: đây là nơi ``build_co4e_tab(ctx, workflow_service)``
    (``presentation/co4e/co4e_tab.py``) sẽ lấy ``workflow_service`` thật một
    khi widget Co4E Studio được lắp lại để dùng nó — hiện widget thật
    (``ui/co4e_tab.py``) vẫn dùng ``Co4ERunManager`` cũ song song.
    """

    def __init__(self, ctx, *, history_path: Optional[Path] = None,
                 runner: Optional[WorkflowRunner] = None):
        """Dựng service.

        ``runner`` để None nghĩa là chưa có ai chạy được run — đúng trạng thái hiện
        nay, vì adapter Qt thật thuộc về tầng ``presentation/`` và chưa được nối.
        Test tiêm runner chạy đồng bộ vào đây.
        """
        self.ctx = ctx
        self._runs: Dict[str, RunRecord] = {}
        self._worker_handles: Dict[str, RunWorkerHandle] = {}
        self._seq = 0
        self._output_root: Optional[Path] = None   # thư mục output co4e của workspace đang chọn
        self._project_id: str = ""                 # workspace đang chọn — Flow Status lọc theo no
        self._runner = runner
        # DTO domain khong duoc cham dia (xem domain/workflows/run_record.py),
        # nen viec doc/ghi file lich su nam o tang application — cu the la
        # co4e_run_history.py::RunHistoryStore.
        self._history_path_value = (
            Path(history_path) if history_path is not None else (CO4E_DIR / "run_history.json")
        )
        self._history = RunHistoryStore(self._history_path_value)
        self._changed_callbacks: List[Callable[[], None]] = []
        self._event_callbacks: List[Callable[[str, dict], None]] = []
        self._load_history()          # khoi phuc lich su cu de Flow Status
                                       # giu du lich su qua cac lan restart

    # ---- callback thay Signal ---------------------------------------------
    def on_changed(self, cb: Callable[[], None]) -> None:
        """Đăng ký callback gọi mỗi khi danh sách run đổi — thay cho signal Qt cũ."""
        self._changed_callbacks.append(cb)

    def on_event(self, cb: Callable[[str, dict], None]) -> None:
        """Đăng ký callback nhận sự kiện tiến độ của từng run — thay cho signal Qt cũ."""
        self._event_callbacks.append(cb)

    def _emit_changed(self) -> None:
        """Lưu lịch sử rồi báo mọi người đăng ký."""
        self._save_history()          # xem docstring dau file: giu dung thu tu ban Qt cu
        for cb in self._changed_callbacks:
            cb()

    def _emit_event(self, run_id: str, ev) -> None:
        """Chuyển một sự kiện tiến độ tới mọi callback đã đăng ký."""
        for cb in self._event_callbacks:
            cb(run_id, ev)

    # ---- persistence --------------------------------------------------
    def _load_history(self) -> None:
        """Khôi phục lịch sử run từ đĩa lúc khởi động.

        Lấy luôn số thứ tự lớn nhất đã dùng để ``_next_id()`` không sinh trùng
        id với run cũ.
        """
        self._runs, self._seq = self._history.load()

    def _save_history(self) -> None:
        """Ghi lịch sử xuống đĩa. Lỗi ghi bị nuốt có chủ ý — xem
        ``co4e_run_history.py::RunHistoryStore``.
        """
        self._history.save(list(self._runs.values()))

    # ---- lifecycle ----------------------------------------------------
    def _next_id(self) -> str:
        """Sinh id run kế tiếp ('run1', 'run2', ...), không đụng id đã có trong lịch sử."""
        self._seq += 1
        return f"run{self._seq}"

    def start(self, wf: Workflow, *, skill_map: Optional[Dict[str, str]] = None,
              plan_mode: bool = False, only_nodes: Optional[set] = None,
              seed_outputs: Optional[Dict[str, str]] = None,
              manual: bool = False, label: Optional[str] = None) -> str:
        """Đăng ký một run mới và giao job cho ``self._runner`` (nếu có).

        Không tự thực thi AI thật ở đây: khi ``self._runner`` là ``None``
        (mặc định), run được ghi nhận nhưng không job nào được giao đi — dùng
        cho test/khi chưa lắp adapter Qt thật.
        """
        run_id = self._next_id()
        total = len(only_nodes) if only_nodes else len(wf.nodes)
        record = RunRecord(run_id, wf.id, label or wf.name, total, plan_mode, manual,
                            created_by=_current_user(), created_at=_now_str(),
                            project_id=self._project_id)
        # workflow_to_dict() tu dung dataclasses.asdict() de dung ca cay (node,
        # step, sub-agent) -> ban than no da la mot "deep copy" sang dict moi,
        # khong con giu tham chieu toi wf.nodes/wf.edges song. Vi vay KHONG can
        # deepcopy(wf) truoc nhu ban Qt cu (RunHandle.wf giu nguyen doi tuong
        # Workflow) -- xem doc string dau file domain/workflows/run_record.py
        # ve ly do snapshot o day la dict tho chu khong phai doi tuong.
        record.wf = workflow_to_dict(wf)
        nodes = list(wf.nodes)
        edges = list(wf.edges)
        out_dir = self._out_dir(wf)
        record.out_dir = str(out_dir)
        ctx = self.ctx
        sk = dict(skill_map or {})
        only: Optional[Set[str]] = set(only_nodes) if only_nodes else None
        seed = dict(seed_outputs or {})
        run_label = record.name
        self._runs[run_id] = record

        if self._runner is not None:
            def job(worker: RunnerJob):
                from ...core import co4e_runner
                return co4e_runner.run_workflow(
                    ctx, nodes, edges, out_dir, worker.emit_event, worker.is_cancelled,
                    plan_mode=plan_mode, skill_map=sk, only_nodes=only, seed_outputs=seed,
                    usage_label=run_label)

            self._worker_handles[run_id] = self._runner.start(
                run_id, job,
                on_event=lambda ev, rid=run_id: self._on_event(rid, ev),
                on_finished=lambda _r=None, rid=run_id: self._on_finished(rid),
                on_failed=lambda e, rid=run_id: self._on_failed(rid, e),
            )
        self._emit_changed()
        return run_id

    # ---- worker callbacks (goi tu runner, thay slot Qt cu) -----------------
    def _on_event(self, run_id: str, ev) -> None:
        """Nhận sự kiện từ job đang chạy và cập nhật bản ghi run."""
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
        # quirk co y giu nguyen (xem test_on_event_unknown_run_id... trong ca
        # test cu lan test moi): re-emit VO DIEU KIEN, ke ca run_id la hoac ev
        # khong phai dict/None -- khac _on_finished/_on_failed la no-op hoan
        # toan khi run_id la.
        #
        # Khac biet CO CHU Y so voi ban Qt cu: Signal(str, dict) cua PySide6 ep
        # ev=None thanh {} khi giao cho slot (tac dung phu cua kieu Signal khai
        # bao cung). O day khong con Signal nen callback nhan DUNG gia tri ev
        # goc (None neu goi voi None) -- khong gia lap lai viec ep kieu do vi
        # no la tac dung phu cua Qt, khong phai quy tac nghiep vu can giu.
        self._emit_event(run_id, ev)

    def _on_finished(self, run_id: str) -> None:
        """Job kết thúc mà không phát ``run_done``: chốt trạng thái về 'done'."""
        record = self._runs.get(run_id)
        if record is not None and record.status == "running":
            # job returned without a run_done event (shouldn't happen) — settle it
            record.status = "done"
            self._emit_changed()

    def _on_failed(self, run_id: str, err: str) -> None:
        """Job ném lỗi: ghi lỗi vào bản ghi và báo ra ngoài một sự kiện ``run_error``."""
        record = self._runs.get(run_id)
        if record is not None:
            record.status = "error"
            record.error = str(err)
            self._emit_event(run_id, {"type": "run_error", "error": str(err)})
            self._emit_changed()

    # ---- control --------------------------------------------------------
    def stop(self, run_id: str) -> None:
        """Yêu cầu dừng một run đang chạy và đánh dấu 'stopped'."""
        record = self._runs.get(run_id)
        worker = self._worker_handles.get(run_id)
        if record is not None and worker is not None and record.running:
            worker.request_stop()
            record.status = "stopped"
            self._emit_changed()

    def stop_all(self) -> None:
        """Dừng mọi run của workspace đang chọn (Flow Status vốn lọc theo project)."""
        # Only the CURRENT workspace's runs (Flow Status is per-project).
        for run_id in [r for r, rec in self._runs.items() if self._belongs(rec)]:
            self.stop(run_id)

    def rename(self, run_id: str, new_name: str) -> None:
        """Rename a run in the Flow Status history (and its kept workflow snapshot),
        then persist + refresh views. No-op on a blank name / unknown run."""
        record = self._runs.get(run_id)
        new_name = (new_name or "").strip()
        if record is None or not new_name or new_name == record.name:
            return
        record.name = new_name
        # DTO doi: RunHandle.wf cu la doi tuong Workflow (gan record.wf.name),
        # RunRecord.wf o day la dict tho (xem domain/workflows/run_record.py)
        # nen doi truc tiep khoa "name" cua dict thay vi thuoc tinh doi tuong.
        if record.wf is not None:
            record.wf["name"] = new_name
        self._emit_changed()

    def remove(self, run_id: str) -> None:
        """Xoá một run khỏi lịch sử; đang chạy thì dừng trước."""
        record = self._runs.get(run_id)
        if record is not None and record.running:
            self.stop(run_id)
        self._runs.pop(run_id, None)
        self._worker_handles.pop(run_id, None)
        self._emit_changed()

    def clear_finished(self) -> None:
        """Xoá mọi run đã kết thúc của workspace đang chọn, giữ nguyên run đang chạy."""
        # Only clear finished runs of the CURRENT workspace.
        for run_id in [r for r, rec in self._runs.items() if not rec.running and self._belongs(rec)]:
            self._runs.pop(run_id, None)
            self._worker_handles.pop(run_id, None)
        self._emit_changed()

    # ---- queries ----------------------------------------------------------
    def _belongs(self, r: RunRecord) -> bool:
        """Whether a run belongs to the currently-selected workspace."""
        return getattr(r, "project_id", "") == self._project_id

    def runs(self) -> List[RunRecord]:
        """Runs of the CURRENT workspace only — Flow Status is per-project."""
        return [r for r in self._runs.values() if self._belongs(r)]

    def all_runs(self) -> List[RunRecord]:
        """Every tracked run across all workspaces (background tracking)."""
        return list(self._runs.values())

    def get(self, run_id: str) -> Optional[RunRecord]:
        """Lấy một run theo id; ``None`` nếu không có."""
        return self._runs.get(run_id)

    def active_count(self) -> int:
        """Số run đang chạy của workspace đang chọn — dùng cho huy hiệu trên tab."""
        return sum(1 for r in self._runs.values() if r.running and self._belongs(r))

    def set_current_project(self, project_id: str) -> None:
        """Filter Flow Status (and new runs) to this workspace. Runs started while
        this is set are tagged with it; the Runs view shows only matching runs."""
        pid = project_id or ""
        if pid != self._project_id:
            self._project_id = pid
            self._emit_changed()          # re-render Flow Status for the new workspace

    def set_output_root(self, root: Optional[Path]) -> None:
        """Point flow outputs at the SELECTED workspace's co4e folder (set by the
        Co4E tab when a project is chosen). ``None`` → fall back to the global
        Cowork output dir."""
        self._output_root = Path(root) if root else None

    def _out_dir(self, wf: Workflow) -> Path:
        """Thư mục ghi kết quả của một luồng, tạo sẵn nếu chưa có."""
        # Flow deliverables are written into the SELECTED workspace (the active
        # project's folder) so they land where the user works with files (Folder
        # tab), not in the config/install folder. One subfolder per flow keeps
        # runs tidy. Falls back to the global Cowork output dir when no workspace
        # is selected.
        base = self._output_root
        if base is None:
            try:
                base = self.ctx.config.cowork_output_dir() / "co4e"
            except Exception:  # noqa: BLE001 - fall back to the config dir if unavailable
                base = CO4E_DIR / "runs" / "co4e"
        d = Path(base) / slugify(wf.name or "flow")
        d.mkdir(parents=True, exist_ok=True)
        return d
