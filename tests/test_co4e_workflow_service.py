"""Test đặc tả cho phần vừa tách khỏi ``core/co4e_run_manager.py``:

  * ``domain/workflows/run_record.py::RunRecord`` — DTO thuần domain.
  * ``application/workflows/co4e_workflow_service.py::Co4EWorkflowService`` —
    phần hành vi (hook + lifecycle + lưu lịch sử), thuần Python.

Khác với ``tests/characterization/test_co4e_run_manager_behavior.py`` (bọc lớp
CŨ, không được sửa), file này bọc lớp MỚI, và có thêm một test bắt buộc theo
yêu cầu tách: ``test_new_service_produces_same_json_record_as_old_manager`` —
chạy CÙNG một chuỗi thao tác trên CẢ HAI lớp (cũ và mới) với cùng input, rồi so
JSON ghi ra đĩa của chúng bằng nhau. Đây là bằng chứng "hành vi không lệch"
chạy được, không phải suy luận bằng mắt.

Không gọi ``Co4EWorkflowService.start()`` với ``runner=None`` bỏ qua — luôn
truyền ``runner`` fake không thực thi job thật (không gọi AI thật), giống lý do
``test_co4e_run_manager_behavior.py`` không bao giờ gọi ``Co4ERunManager.start()``
thật.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cowork_local.application.workflows.co4e_workflow_service import Co4EWorkflowService
from cowork_local.core.co4e import Node, Step, Workflow
from cowork_local.domain.workflows.run_record import RunRecord


class _FakeConfig:
    def __init__(self, output_dir: Path):
        self._output_dir = output_dir

    def cowork_output_dir(self) -> Path:
        return self._output_dir


class _Ctx:
    """Stub ctx: chỉ ``start()``/``_out_dir()`` mới đụng ``ctx.config``."""

    def __init__(self, output_dir: Path):
        self.config = _FakeConfig(output_dir)


class _RecordingRunner:
    """Fake ``WorkflowRunner`` — ghi lại lời gọi ``start()``, KHÔNG thực thi
    ``job`` (job thật gọi ``core.co4e_runner.run_workflow`` -> AI thật, tốn
    tiền/ghi file thật, đúng lý do old characterization test tránh gọi
    ``Co4ERunManager.start()``). Trả một handle giả để test ``stop()``."""

    def __init__(self):
        self.calls = []

    def start(self, run_id, job, on_event, on_finished, on_failed):
        handle = _FakeWorkerHandle()
        self.calls.append((run_id, job, on_event, on_finished, on_failed, handle))
        return handle


class _FakeWorkerHandle:
    def __init__(self):
        self.stop_requested = False

    def request_stop(self):
        self.stop_requested = True


def _make_workflow(node_count: int = 3, wf_id: str = "wf1", name: str = "Flow") -> Workflow:
    # Dung dung dataclass that (core/co4e.py) thay vi stub -- workflow_to_dict()
    # trong Co4EWorkflowService.start() doc n.id/n.x/n.y/n.data tren tung node
    # va wf.is_template tren workflow, khong the gia lap bang string/duck-type
    # thieu thuoc tinh.
    nodes = [Node(id=f"n{i}", x=0.0, y=0.0, data=Step(label=f"Step{i}")) for i in range(1, node_count + 1)]
    return Workflow(id=wf_id, name=name, nodes=nodes, edges=[])


@pytest.fixture
def service(tmp_path):
    return Co4EWorkflowService(_Ctx(tmp_path), history_path=tmp_path / "run_history.json")


def _seed(service: Co4EWorkflowService, run_id: str, **kw) -> RunRecord:
    defaults = dict(wf_id="wf1", name="Flow", total=3, plan_mode=False, manual=False)
    defaults.update(kw)
    r = RunRecord(run_id, **defaults)
    service._runs[run_id] = r
    return r


# ---------------------------------------------------------------------------
# RunRecord: gia tri mac dinh / kep bien / round trip (khop ban cu)
# ---------------------------------------------------------------------------

def test_run_record_defaults_on_construction():
    r = RunRecord("run1", "wf1", "My Flow", 3, False, False)
    assert r.status == "running"
    assert r.done == 0
    assert r.progress_text() == "0/3"
    assert r.running is True


def test_run_record_negative_total_clamped_to_zero():
    r = RunRecord("run2", "wf2", "Flow2", -5, False, False)
    assert r.total == 0


def test_run_record_zero_total_progress_text_falls_back_to_status():
    r = RunRecord("run3", "wf3", "Flow3", 0, False, False)
    assert r.progress_text() == "running"


def test_to_dict_contains_expected_keys_and_values():
    r = RunRecord("run1", "wf1", "My Flow", 3, False, False,
                  created_by="alice", created_at="2026-08-23 10:00", project_id="p1")
    rec = r.to_dict()
    assert sorted(rec.keys()) == [
        "created_at", "created_by", "done", "error", "id", "manual", "name",
        "node_status", "out_dir", "plan_mode", "project_id", "status", "total",
        "wf", "wf_id",
    ]
    assert rec["id"] == "run1"
    assert rec["status"] == "running"
    assert rec["wf"] is None


def test_round_trip_status_running_becomes_stopped():
    r = RunRecord("run1", "wf1", "My Flow", 3, False, False)
    rec = r.to_dict()
    assert rec["status"] == "running"
    back = RunRecord.from_dict(rec)
    assert back.status == "stopped"


@pytest.mark.parametrize("status", ["done", "error", "stopped"])
def test_round_trip_non_running_statuses_are_preserved(status):
    r = RunRecord("run1", "wf1", "My Flow", 3, False, False)
    r.status = status
    back = RunRecord.from_dict(r.to_dict())
    assert back.status == status


def test_from_dict_empty_dict_uses_documented_defaults():
    r = RunRecord.from_dict({})
    assert r.id == ""
    assert r.status == "done"
    assert r.wf is None
    assert r.node_status == {}


def test_from_dict_none_treated_same_as_empty_dict():
    assert RunRecord.from_dict(None).id == RunRecord.from_dict({}).id
    assert RunRecord.from_dict(None).status == RunRecord.from_dict({}).status


def test_round_trip_preserves_raw_workflow_snapshot_dict():
    # domain khong parse "wf" thanh doi tuong -- giu nguyen dict tho (khac
    # RunHandle cu, xem docstring domain/workflows/run_record.py).
    r = RunRecord("run4", "wf-x", "Flow X run", 1, False, False)
    r.wf = {"id": "wf-x", "name": "Flow X", "nodes": [{"id": "n1"}], "edges": []}
    back = RunRecord.from_dict(r.to_dict())
    assert back.wf == r.wf
    assert isinstance(back.wf, dict)


# ---------------------------------------------------------------------------
# _on_event / _on_finished / _on_failed (hanh vi khop ban cu, callback thay Signal)
# ---------------------------------------------------------------------------

def test_on_event_node_status_done_increments_progress_and_emits_changed(service):
    r = _seed(service, "run1")
    changed = []
    service.on_changed(lambda: changed.append(1))
    service._on_event("run1", {"type": "node_status", "node_id": "n1", "status": "done"})
    assert r.node_status == {"n1": "done"}
    assert r.done == 1
    assert len(changed) == 1


def test_on_event_node_status_planned_counts_as_terminal_too(service):
    r = _seed(service, "run1")
    service._on_event("run1", {"type": "node_status", "node_id": "n1", "status": "planned"})
    assert r.done == 1


def test_on_event_node_status_running_is_not_terminal(service):
    r = _seed(service, "run1")
    service._on_event("run1", {"type": "node_status", "node_id": "n1", "status": "running"})
    assert r.done == 0


def test_on_event_node_status_missing_keys_stores_none_key(service):
    r = _seed(service, "run1")
    service._on_event("run1", {"type": "node_status"})
    assert r.node_status == {None: None}


def test_on_event_run_done_default_ok_marks_done(service):
    r = _seed(service, "run1")
    service._on_event("run1", {"type": "run_done"})
    assert r.status == "done"


def test_on_event_run_done_ok_false_marks_error(service):
    r = _seed(service, "run1")
    service._on_event("run1", {"type": "run_done", "ok": False})
    assert r.status == "error"


def test_on_event_run_done_ignored_when_not_running(service):
    r = _seed(service, "run1")
    r.status = "stopped"
    service._on_event("run1", {"type": "run_done", "ok": False})
    assert r.status == "stopped"


def test_on_event_unknown_run_id_does_not_raise_and_still_reemits_event(service):
    received = []
    service.on_event(lambda rid, ev: received.append((rid, ev)))
    service._on_event("no-such-run", {"type": "node_status", "node_id": "n1", "status": "done"})
    assert received == [("no-such-run", {"type": "node_status", "node_id": "n1", "status": "done"})]


def test_on_event_none_payload_does_not_raise_and_reemits_none(service):
    # Khac ban cu (Qt ep None -> {} do Signal(str, dict)): o day khong con
    # Signal nen callback nhan DUNG gia tri goc None. Xem comment trong
    # co4e_workflow_service.py::_on_event ve ly do khong gia lap lai viec ep
    # kieu do.
    _seed(service, "run1")
    received = []
    service.on_event(lambda rid, ev: received.append((rid, ev)))
    service._on_event("run1", None)
    assert received == [("run1", None)]


def test_on_finished_while_running_settles_to_done(service):
    r = _seed(service, "run1")
    changed = []
    service.on_changed(lambda: changed.append(1))
    service._on_finished("run1")
    assert r.status == "done"
    assert len(changed) == 1


def test_on_finished_when_already_settled_is_a_noop(service):
    r = _seed(service, "run1")
    r.status = "error"
    changed = []
    service.on_changed(lambda: changed.append(1))
    service._on_finished("run1")
    assert r.status == "error"
    assert len(changed) == 0


def test_on_finished_unknown_run_id_is_a_total_noop(service):
    changed = []
    service.on_changed(lambda: changed.append(1))
    service._on_finished("no-such-run")
    assert service._runs == {}
    assert changed == []


def test_on_failed_marks_error_with_message_and_emits_run_error_event(service):
    r = _seed(service, "run1")
    events = []
    changed = []
    service.on_event(lambda rid, ev: events.append((rid, ev)))
    service.on_changed(lambda: changed.append(1))
    service._on_failed("run1", "boom")
    assert r.status == "error"
    assert r.error == "boom"
    assert events == [("run1", {"type": "run_error", "error": "boom"})]
    assert len(changed) == 1


def test_on_failed_overrides_status_even_when_already_settled(service):
    r = _seed(service, "run1")
    r.status = "done"
    service._on_failed("run1", "late failure")
    assert r.status == "error"


def test_on_failed_unknown_run_id_is_a_total_noop(service):
    events = []
    changed = []
    service.on_event(lambda rid, ev: events.append((rid, ev)))
    service.on_changed(lambda: changed.append(1))
    service._on_failed("no-such-run", "err")
    assert events == []
    assert changed == []


# ---------------------------------------------------------------------------
# persistence: hook -> dia -> from_dict round trip
# ---------------------------------------------------------------------------

def test_changed_hook_persists_to_history_file(service, tmp_path):
    _seed(service, "run1")
    service._on_event("run1", {"type": "node_status", "node_id": "n1", "status": "done"})
    path = tmp_path / "run_history.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["runs"]) == 1
    assert data["runs"][0]["id"] == "run1"
    assert data["runs"][0]["status"] == "running"


def test_reloading_service_after_hook_settles_running_to_stopped(tmp_path):
    history_path = tmp_path / "run_history.json"
    s1 = Co4EWorkflowService(_Ctx(tmp_path), history_path=history_path)
    _seed(s1, "run1")
    s1._on_event("run1", {"type": "node_status", "node_id": "n1", "status": "done"})

    s2 = Co4EWorkflowService(_Ctx(tmp_path), history_path=history_path)
    assert "run1" in s2._runs
    assert s2._runs["run1"].status == "stopped"
    assert s2._seq == 1


def test_reloaded_seq_avoids_colliding_with_history_ids(tmp_path):
    history_path = tmp_path / "run_history.json"
    s1 = Co4EWorkflowService(_Ctx(tmp_path), history_path=history_path)
    _seed(s1, "run7")
    s1._on_event("run7", {"type": "node_status", "node_id": "n1", "status": "done"})

    s2 = Co4EWorkflowService(_Ctx(tmp_path), history_path=history_path)
    assert s2._seq == 7
    assert s2._next_id() == "run8"


def test_load_history_missing_file_is_silent_noop(tmp_path):
    s = Co4EWorkflowService(_Ctx(tmp_path), history_path=tmp_path / "does-not-exist.json")
    assert s._runs == {}
    assert s._seq == 0


# ---------------------------------------------------------------------------
# start() qua WorkflowRunner Protocol (khong QThread, khong AI that)
# ---------------------------------------------------------------------------

def test_start_registers_run_and_delegates_to_injected_runner(tmp_path):
    runner = _RecordingRunner()
    s = Co4EWorkflowService(_Ctx(tmp_path), history_path=tmp_path / "h.json", runner=runner)
    changed = []
    s.on_changed(lambda: changed.append(1))

    run_id = s.start(_make_workflow(node_count=2))

    assert run_id == "run1"
    record = s.get(run_id)
    assert record is not None
    assert record.status == "running"
    assert record.total == 2
    assert record.wf["id"] == "wf1"
    assert record.wf["name"] == "Flow"
    assert len(record.wf["nodes"]) == 2
    assert len(runner.calls) == 1
    assert runner.calls[0][0] == run_id
    assert len(changed) == 1


def test_start_with_only_nodes_uses_its_length_as_total(tmp_path):
    runner = _RecordingRunner()
    s = Co4EWorkflowService(_Ctx(tmp_path), history_path=tmp_path / "h.json", runner=runner)
    run_id = s.start(_make_workflow(node_count=3), only_nodes={"n1", "n2"})
    assert s.get(run_id).total == 2


def test_start_without_runner_still_registers_run_but_no_job_delegated(tmp_path):
    s = Co4EWorkflowService(_Ctx(tmp_path), history_path=tmp_path / "h.json")  # runner=None mac dinh
    run_id = s.start(_make_workflow())
    assert s.get(run_id) is not None
    assert s.get(run_id).status == "running"


def test_stop_calls_runner_handle_request_stop(tmp_path):
    runner = _RecordingRunner()
    s = Co4EWorkflowService(_Ctx(tmp_path), history_path=tmp_path / "h.json", runner=runner)
    run_id = s.start(_make_workflow())
    handle = runner.calls[0][5]
    s.stop(run_id)
    assert handle.stop_requested is True
    assert s.get(run_id).status == "stopped"


def test_stop_running_run_emits_changed(tmp_path):
    # Bite-test: neu ai xoa self._emit_changed() ben trong stop(), test nay
    # phai do (khac assertion ve status/stop_requested o test ben tren, von
    # khong dung toi len goi on_changed()).
    runner = _RecordingRunner()
    s = Co4EWorkflowService(_Ctx(tmp_path), history_path=tmp_path / "h.json", runner=runner)
    run_id = s.start(_make_workflow())
    changed = []
    s.on_changed(lambda: changed.append(1))
    s.stop(run_id)
    assert len(changed) == 1


def test_stop_non_running_run_is_noop_and_does_not_emit_changed(tmp_path):
    runner = _RecordingRunner()
    s = Co4EWorkflowService(_Ctx(tmp_path), history_path=tmp_path / "h.json", runner=runner)
    run_id = s.start(_make_workflow())
    s.get(run_id).status = "done"
    changed = []
    s.on_changed(lambda: changed.append(1))
    s.stop(run_id)
    assert changed == []


def test_rename_updates_name_and_wf_dict_and_emits_changed(service):
    r = _seed(service, "run1")
    r.wf = {"id": "wf1", "name": "Old", "nodes": [], "edges": []}
    changed = []
    service.on_changed(lambda: changed.append(1))
    service.rename("run1", "New Name")
    assert r.name == "New Name"
    assert r.wf["name"] == "New Name"
    assert len(changed) == 1


def test_rename_blank_name_is_noop_and_does_not_emit_changed(service):
    r = _seed(service, "run1", name="Flow")
    changed = []
    service.on_changed(lambda: changed.append(1))
    service.rename("run1", "   ")
    assert r.name == "Flow"
    assert changed == []


def test_rename_same_name_is_noop_and_does_not_emit_changed(service):
    _seed(service, "run1", name="Flow")
    changed = []
    service.on_changed(lambda: changed.append(1))
    service.rename("run1", "Flow")
    assert changed == []


def test_rename_unknown_run_id_is_noop_and_does_not_emit_changed(service):
    changed = []
    service.on_changed(lambda: changed.append(1))
    service.rename("no-such-run", "New Name")
    assert changed == []


def test_remove_running_run_stops_it_then_removes_and_emits_changed_twice(tmp_path):
    # remove() goi stop() (rieng no da emit mot lan) roi tu emit them mot lan
    # sau khi pop -- 2 la con so dung khop ban cu (core/co4e_run_manager.py::
    # remove), khong phai 1.
    runner = _RecordingRunner()
    s = Co4EWorkflowService(_Ctx(tmp_path), history_path=tmp_path / "h.json", runner=runner)
    run_id = s.start(_make_workflow())
    handle = runner.calls[0][5]
    changed = []
    s.on_changed(lambda: changed.append(1))
    s.remove(run_id)
    assert handle.stop_requested is True
    assert s.get(run_id) is None
    assert len(changed) == 2


def test_remove_non_running_run_emits_changed_once(service):
    r = _seed(service, "run1")
    r.status = "done"
    changed = []
    service.on_changed(lambda: changed.append(1))
    service.remove("run1")
    assert service.get("run1") is None
    assert len(changed) == 1


def test_clear_finished_emits_changed_even_with_no_matching_runs(service):
    # Ban cu luon emit sau vong lap, ke ca khi khong xoa gi -- giu quirk nay.
    changed = []
    service.on_changed(lambda: changed.append(1))
    service.clear_finished()
    assert len(changed) == 1


def test_clear_finished_removes_only_finished_runs_of_current_project(service):
    r1 = _seed(service, "run1")
    r1.status = "done"
    r2 = _seed(service, "run2")
    r2.status = "running"
    changed = []
    service.on_changed(lambda: changed.append(1))
    service.clear_finished()
    assert "run1" not in service._runs
    assert "run2" in service._runs
    assert len(changed) == 1


def test_set_current_project_changes_pid_and_emits_changed(service):
    changed = []
    service.on_changed(lambda: changed.append(1))
    service.set_current_project("proj1")
    assert service._project_id == "proj1"
    assert len(changed) == 1


def test_set_current_project_same_pid_is_noop_and_does_not_emit_changed(service):
    service.set_current_project("proj1")
    changed = []
    service.on_changed(lambda: changed.append(1))
    service.set_current_project("proj1")
    assert changed == []


# ---------------------------------------------------------------------------
# Bang chung "hanh vi khong lech": cung input -> cung JSON tren dia, ca lop
# cu (core/co4e_run_manager.py) lan lop moi (application/workflows/...).
# ---------------------------------------------------------------------------

def test_new_service_produces_same_json_record_as_old_manager(tmp_path, monkeypatch):
    from cowork_local.core import co4e as _co4e_module
    from cowork_local.core.co4e_run_manager import Co4ERunManager, RunHandle as OldRunHandle

    # Co lap CO4E_DIR cho manager cu bang cach patch THUOC TINH MODULE (dung ky
    # thuat cua tests/characterization/test_co4e_run_manager_behavior.py, xem
    # docstring dau file do ve ly do KHONG dung bien moi truong truoc luc
    # import: _history_path() doc lai CO4E_DIR tuoi ngay luc goi ham).
    monkeypatch.setattr(_co4e_module, "CO4E_DIR", tmp_path / "old_home" / ".cowork_local" / "co4e")
    old_history = tmp_path / "old_history.json"
    monkeypatch.setattr(Co4ERunManager, "_history_path", lambda self: old_history)

    class _OldCtx:
        pass

    old_mgr = Co4ERunManager(_OldCtx())
    old_mgr._runs["run1"] = OldRunHandle(
        "run1", "wf1", "Flow", 3, False, False,
        created_by="alice", created_at="2026-08-23 10:00", project_id="p1",
    )
    old_mgr._on_event("run1", {"type": "node_status", "node_id": "n1", "status": "done"})
    old_mgr._on_event("run1", {"type": "node_status", "node_id": "n2", "status": "running"})
    old_mgr._on_event("run1", {"type": "run_done", "ok": True})
    old_record = json.loads(old_history.read_text(encoding="utf-8"))["runs"][0]

    new_history = tmp_path / "new_history.json"
    new_svc = Co4EWorkflowService(_Ctx(tmp_path), history_path=new_history)
    new_svc._runs["run1"] = RunRecord(
        "run1", "wf1", "Flow", 3, False, False,
        created_by="alice", created_at="2026-08-23 10:00", project_id="p1",
    )
    new_svc._on_event("run1", {"type": "node_status", "node_id": "n1", "status": "done"})
    new_svc._on_event("run1", {"type": "node_status", "node_id": "n2", "status": "running"})
    new_svc._on_event("run1", {"type": "run_done", "ok": True})
    new_record = json.loads(new_history.read_text(encoding="utf-8"))["runs"][0]

    assert new_record == old_record


def test_new_service_reload_quirk_matches_old_manager_reload_quirk(tmp_path, monkeypatch):
    """Cung quirk round-trip khong doi xung ('running' -> 'stopped' sau khi
    doc lai tu dia) phai xay ra giong het nhau tren ca hai lop."""
    from cowork_local.core import co4e as _co4e_module
    from cowork_local.core.co4e_run_manager import Co4ERunManager, RunHandle as OldRunHandle

    monkeypatch.setattr(_co4e_module, "CO4E_DIR", tmp_path / "old_home2" / ".cowork_local" / "co4e")
    old_history = tmp_path / "old_history2.json"
    monkeypatch.setattr(Co4ERunManager, "_history_path", lambda self: old_history)

    class _OldCtx:
        pass

    old_mgr = Co4ERunManager(_OldCtx())
    old_mgr._runs["run7"] = OldRunHandle("run7", "wf1", "Flow", 2, False, False)
    old_mgr._on_event("run7", {"type": "node_status", "node_id": "n1", "status": "done"})
    old_mgr2 = Co4ERunManager(_OldCtx())

    new_history = tmp_path / "new_history2.json"
    new_svc = Co4EWorkflowService(_Ctx(tmp_path), history_path=new_history)
    new_svc._runs["run7"] = RunRecord("run7", "wf1", "Flow", 2, False, False)
    new_svc._on_event("run7", {"type": "node_status", "node_id": "n1", "status": "done"})
    new_svc2 = Co4EWorkflowService(_Ctx(tmp_path), history_path=new_history)

    assert old_mgr2._runs["run7"].status == new_svc2._runs["run7"].status == "stopped"
    assert old_mgr2._seq == new_svc2._seq == 7
