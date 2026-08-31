"""Characterization test cho lớp CŨ ``core/co4e_run_manager.py``
(``Co4ERunManager`` + ``RunHandle``) — hook ``_on_event``/``_on_finished``/
``_on_failed`` và round-trip ``RunHandle.to_record``/``RunHandle.from_record``.

VÒNG ĐỜI: đây là giàn giáo (scaffolding), không phải công trình cuối cùng.
Mục đích DUY NHẤT là làm lưới an toàn cho đợt tách ``Co4ERunManager`` thành
``domain/workflows/run_record.py::RunRecord`` (DTO thuần) +
``application/workflows/co4e_workflow_service.py::Co4EWorkflowService``
(hành vi + lifecycle + lưu đĩa) — xem ``tests/test_co4e_workflow_service.py``,
nơi lớp MỚI được bọc lại bằng test đặc tả tử tế, và nơi có
``test_new_service_produces_same_json_record_as_old_manager`` chạy CÙNG một
chuỗi thao tác trên cả hai lớp rồi so JSON ghi ra đĩa — bằng chứng "hành vi
không lệch" chạy được. File NÀY chỉ ghi lại hành vi của lớp CŨ, KHÔNG được sửa
lớp cũ để "cho khớp" test — nếu một assert dưới đây đỏ mà code cũ trông "sai",
sửa assert, không sửa ``core/co4e_run_manager.py``. Sau khi đợt tách hoàn tất
và ``core/co4e_run_manager.py`` bị xoá/deprecate hẳn, file này hết nhiệm vụ và
nên được xoá theo (không viết lại thành spec — spec test đã có sẵn ở
``tests/test_co4e_workflow_service.py``).

CÁCH CHỐT ASSERT: mọi giá trị dưới đây được lấy bằng cách CHẠY code thật qua
``.venv/Scripts/python.exe -c "..."`` rồi dán nguyên kết quả in được vào
assert (đúng quy trình ngược yêu cầu), không suy luận lý thuyết.

AN TOÀN DỮ LIỆU (BẮT BUỘC — lý do có 2 lớp phòng thủ dưới đây):
  1. ``Co4ERunManager.__init__`` gọi ``_load_history()`` đọc
     ``~/.cowork_local/co4e/run_history.json`` THẬT (``CONFIG_DIR`` là
     ``Path.home() / ".cowork_local"``, hằng số module tính MỘT LẦN lúc
     ``cowork_local.config`` được import), rồi mọi ``changed.emit()`` (từ mọi
     hook mà test này gọi) kéo theo ``_save_history()`` ghi ĐÈ file đó. Vì
     vậy, TRƯỚC khi import bất kỳ thứ gì thuộc ``cowork_local``, module này tự
     dựng một HOME giả (``_isolate_home()``, cùng kỹ thuật
     ``tools/capture_screens.py::_isolate_home()``: đặt ``USERPROFILE``/
     ``HOME`` trỏ vào một thư mục tạm, xoá ``HOMEDRIVE``/``HOMEPATH``) rồi mới
     import ``cowork_local.config``/``cowork_local.core.co4e_run_manager`` —
     một assert ngay sau import chốt rằng ``CONFIG_DIR`` thật sự nằm trong
     sandbox đó (kiểu ``tools/check_co4e.py:47``).
  2. Phòng thủ thứ hai, độc lập với (1): mỗi test còn monkeypatch
     ``Co4ERunManager._history_path`` trỏ về một file trong ``tmp_path`` CỦA
     RIÊNG NÓ. Lý do cần thêm lớp này dù đã có (1): nếu file test này được
     chạy CÙNG bộ với các file khác đã import ``cowork_local.config`` với HOME
     thật trước đó (thứ tự collect của pytest), hằng số module ``CONFIG_DIR``/
     ``CO4E_DIR`` đã bị đóng băng theo HOME thật mất rồi — xem đúng cái bẫy
     này được ghi lại trong docstring đầu
     ``tests/characterization/test_co4e_skills_panel.py``. Vá thẳng
     ``_history_path`` (đọc lại lúc GỌI, không đọc lúc import) không phụ
     thuộc thời điểm import nên luôn đúng bất kể thứ tự collect.

KHÔNG gọi ``Co4ERunManager.start()`` (spawn ``AgentWorker``/``QThread`` thật,
gọi provider AI thật, tốn tiền, ghi file thật). Mọi test dưới đây seed thẳng
vào ``manager._runs[...]`` bằng ``RunHandle`` rồi gọi ``_on_event``/
``_on_finished``/``_on_failed`` trực tiếp — đúng route hook thật mà
``start()`` nối qua ``worker.event.connect(...)`` v.v., chỉ bỏ qua phần
spawn/chạy job.

KHÔNG CẦN QApplication: ``Co4ERunManager``/``RunHandle`` chỉ dùng
``QObject``+``Signal`` đồng luồng (kết nối rồi ``emit()`` ngay trong test,
không dựng widget, không đọc kích thước, không cần app instance).

QUIRK ĐÃ ĐÓNG ĐINH (xem case tương ứng bên dưới — ĐỪNG "dọn" các chỗ này khi
tách, chúng trông như bug nhưng là hành vi đang chạy thật hôm nay):
  * ``event = Signal(str, dict)`` khai báo kiểu cứng cho tham số thứ hai. Khi
    ``_on_event(run_id, ev)`` được gọi với ``ev=None`` và ``run_id`` KHÔNG có
    trong ``_runs`` (nên nhánh xử lý dict bị bỏ qua, đi thẳng xuống
    ``self.event.emit(run_id, ev)``), Qt/Shiboken ép kiểu ``None`` thành
    ``dict`` RỖNG (``{}``) ngay tại điểm ``emit`` — listener nhận được
    ``{}`` chứ KHÔNG PHẢI ``None``. (Shiboken có in một dòng cảnh báo
    "Cannot copy-convert ... (NoneType) to C++" ra stderr, nhưng KHÔNG ném
    lỗi.) Đây là khác biệt cố ý với lớp MỚI
    (``Co4EWorkflowService``/``domain/workflows/run_record.py``), nơi không
    còn ``Signal`` nữa nên callback nhận đúng ``None`` gốc — xem
    ``tests/test_co4e_workflow_service.py::test_on_event_none_payload_does_not_raise_and_reemits_none``.
  * Khi ``ev["type"] == "run_done"`` mà ``handle.status`` KHÔNG phải
    ``"running"`` (ví dụ đã ``"stopped"``), nhánh ``if handle.status ==
    "running":`` không đổi ``status``, nhưng ``self.changed.emit()`` vẫn được
    gọi VÔ ĐIỀU KIỆN ngay sau đó (nằm ngoài ``if``) — run "đã xong" vẫn kích
    một lần refresh + một lần ghi lịch sử xuống đĩa, dù không có gì thay đổi
    trên ``handle`` đó.
  * ``RunHandle.to_record()``/``from_record()`` đổi trường ``wf`` qua lại
    thành ĐỐI TƯỢNG ``Workflow`` thật (``workflow_to_dict``/
    ``workflow_from_dict`` từ ``core/co4e.py``) — khác hẳn ``RunRecord`` mới
    (``domain/workflows/run_record.py``), nơi ``wf`` CỐ Ý được giữ nguyên là
    dict thô vì domain không được phép import ``core.co4e.Workflow``. Đây là
    một khác biệt thiết kế có chủ đích giữa bản cũ và bản mới, không phải lỗi
    port thiếu.
  * Round-trip KHÔNG đối xứng: ``status == "running"`` đọc lại từ
    ``from_record()`` bị chốt thành ``"stopped"`` (worker của nó đã mất theo
    khi app tắt giữa run), nhưng ``to_record()`` vẫn ghi đúng "running" xuống
    đĩa tại thời điểm lưu. ``from_record({})``/``from_record(None)`` mặc định
    ``status="done"`` (không phải "running") nên KHÔNG rơi vào nhánh đổi
    thành "stopped".
  * ``total`` âm bị ``max(0, total)`` kẹp về 0 ngay lúc khởi tạo
    ``RunHandle``, không giữ nguyên giá trị âm.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def _isolate_home() -> Path:
    """Trỏ USERPROFILE/HOME sang một thư mục tạm TRƯỚC khi import
    ``cowork_local`` — cùng kỹ thuật ``tools/capture_screens.py::_isolate_home()``.
    Không có dữ liệu thật nào được sao chép vào đây (khác capture_screens):
    test này không cần đọc lịch sử run thật, chỉ cần KHÔNG BAO GIỜ chạm vào nó.
    """
    sandbox = Path(tempfile.mkdtemp(prefix="co4e-run-manager-test-home-"))
    (sandbox / ".cowork_local").mkdir(parents=True, exist_ok=True)
    for var in ("USERPROFILE", "HOME"):
        os.environ[var] = str(sandbox)
    os.environ.pop("HOMEDRIVE", None)
    os.environ.pop("HOMEPATH", None)
    return sandbox


_SANDBOX_HOME = _isolate_home()

import pytest  # noqa: E402

from cowork_local.config import CONFIG_DIR  # noqa: E402
from cowork_local.core.co4e import Node, Step, Workflow  # noqa: E402
from cowork_local.core.co4e_run_manager import Co4ERunManager, RunHandle  # noqa: E402

# GIỚI HẠN ĐÃ BIẾT (không phải lỗ hổng an toàn dữ liệu — xem lớp phòng thủ #2
# ở docstring đầu file, mọi test dưới đây đều tự vá ``_history_path`` bất kể
# kết quả kiểm tra này): ``CONFIG_DIR`` là hằng số module tính MỘT LẦN lúc
# ``cowork_local.config`` được import. Khi chạy CHỈ file này (đúng lệnh VERIFY
# ở đầu task), ``_isolate_home()`` ở trên chạy trước import đầu tiên nên chốt
# đúng. Khi chạy CẢ BỘ, một file khác được pytest collect trước có thể đã
# import ``cowork_local.config`` với HOME thật rồi — ``CONFIG_DIR`` khi đó đã
# đóng băng theo giá trị thật, không cách nào isolate lại được nữa từ file này
# (cùng giới hạn được ghi trong docstring đầu
# ``tests/characterization/test_co4e_skills_panel.py``). Vì vậy test dưới đây
# CHỦ ĐỘNG bỏ qua (không fail cả file, không làm mất 30 test còn lại) khi phát
# hiện giới hạn này, thay vì assert cứng ở cấp module (từng thử — gây lỗi
# collection cho TOÀN BỘ file khi chạy chung với các file khác đã import
# ``cowork_local.config`` trước).
def test_home_isolation_pins_config_dir_into_sandbox_when_first_to_import():
    if str(_SANDBOX_HOME) not in str(CONFIG_DIR):
        pytest.skip(
            "cowork_local.config da bi mot file test khac import voi HOME "
            "that TRUOC file nay trong cung phien pytest (thu tu collect) -- "
            f"CONFIG_DIR={CONFIG_DIR!r} khong con nam trong sandbox cua file "
            "nay. Day la gioi han da biet (xem docstring dau file), KHONG "
            "phai mat an toan du lieu: moi test hook trong file nay tu va "
            "thang Co4ERunManager._history_path (doc lap voi CONFIG_DIR) nen "
            "khong test nao trong file thuc su cham vao lich su run that."
        )
    assert str(_SANDBOX_HOME) in str(CONFIG_DIR)


class _Ctx:
    """Stub ``ctx``: không hook/round-trip nào trong file này đụng tới
    ``ctx.config`` (chỉ ``start()``/``_out_dir()`` — không thuộc phạm vi bọc
    của file này — mới cần nó thật)."""


@pytest.fixture
def manager(tmp_path, monkeypatch):
    # Lớp phòng thủ thứ hai (xem docstring đầu file): mỗi test có lịch sử
    # riêng trong tmp_path của chính nó, độc lập với CONFIG_DIR.
    history_path = tmp_path / "run_history.json"
    monkeypatch.setattr(Co4ERunManager, "_history_path", lambda self: history_path)
    return Co4ERunManager(_Ctx())


def _seed(manager: Co4ERunManager, run_id: str, **kw) -> RunHandle:
    defaults = dict(wf_id="wf1", name="Flow", total=3, plan_mode=False, manual=False)
    defaults.update(kw)
    h = RunHandle(run_id, **defaults)
    manager._runs[run_id] = h
    return h


def _make_workflow(node_count: int = 1, wf_id: str = "wf-x", name: str = "Flow X") -> Workflow:
    nodes = [Node(id=f"n{i}", x=0.0, y=0.0, data=Step(label=f"Step{i}")) for i in range(1, node_count + 1)]
    return Workflow(id=wf_id, name=name, nodes=nodes, edges=[])


# ---------------------------------------------------------------------------
# RunHandle: gia tri mac dinh / kep bien
# ---------------------------------------------------------------------------

def test_run_handle_defaults_on_construction():
    h = RunHandle("run1", "wf1", "My Flow", 3, False, False)
    assert h.status == "running"
    assert h.done == 0
    assert h.progress_text() == "0/3"
    assert h.running is True


def test_run_handle_negative_total_clamped_to_zero():
    h = RunHandle("run2", "wf2", "Flow2", -5, False, False)
    assert h.total == 0


def test_run_handle_zero_total_progress_text_falls_back_to_status():
    h = RunHandle("run3", "wf3", "Flow3", 0, False, False)
    assert h.progress_text() == "running"


# ---------------------------------------------------------------------------
# to_record / from_record
# ---------------------------------------------------------------------------

def test_to_record_contains_expected_keys_and_values():
    h = RunHandle("run1", "wf1", "My Flow", 3, False, False,
                  created_by="alice", created_at="2026-08-23 10:00", project_id="p1")
    rec = h.to_record()
    assert sorted(rec.keys()) == [
        "created_at", "created_by", "done", "error", "id", "manual", "name",
        "node_status", "out_dir", "plan_mode", "project_id", "status", "total",
        "wf", "wf_id",
    ]
    assert rec["id"] == "run1"
    assert rec["status"] == "running"
    assert rec["wf"] is None


def test_round_trip_status_running_becomes_stopped():
    h = RunHandle("run1", "wf1", "My Flow", 3, False, False)
    rec = h.to_record()
    assert rec["status"] == "running"          # to_record ghi dung "running"
    back = RunHandle.from_record(rec)
    assert back.status == "stopped"            # nhung from_record chot lai thanh "stopped"


@pytest.mark.parametrize("status", ["done", "error", "stopped"])
def test_round_trip_non_running_statuses_are_preserved(status):
    h = RunHandle("run1", "wf1", "My Flow", 3, False, False)
    h.status = status
    back = RunHandle.from_record(h.to_record())
    assert back.status == status


def test_from_record_empty_dict_uses_documented_defaults():
    h = RunHandle.from_record({})
    assert h.id == ""
    assert h.status == "done"      # quirk: khong roi vao nhanh doi thanh "stopped"
    assert h.wf is None
    assert h.node_status == {}


def test_from_record_none_treated_same_as_empty_dict():
    assert RunHandle.from_record(None).id == RunHandle.from_record({}).id
    assert RunHandle.from_record(None).status == RunHandle.from_record({}).status


def test_round_trip_workflow_snapshot_becomes_real_workflow_object():
    # quirk: khac RunRecord moi (giu wf la dict tho), RunHandle CU doi wf qua
    # lai thanh doi tuong Workflow that qua workflow_to_dict/workflow_from_dict.
    h = RunHandle("run4", "wf-x", "Flow X run", 1, False, False)
    h.wf = _make_workflow()
    rec = h.to_record()
    assert isinstance(rec["wf"], dict)         # tren dia luon la dict (JSON-able)
    assert rec["wf"]["id"] == "wf-x"
    assert rec["wf"]["name"] == "Flow X"

    back = RunHandle.from_record(rec)
    assert isinstance(back.wf, Workflow)       # nhung doc lai thanh doi tuong that
    assert back.wf.id == "wf-x"
    assert back.wf.name == "Flow X"
    assert len(back.wf.nodes) == 1
    assert back.wf.nodes[0].id == "n1"


# ---------------------------------------------------------------------------
# _on_event
# ---------------------------------------------------------------------------

def test_on_event_node_status_done_increments_progress_and_emits_changed(manager):
    h = _seed(manager, "run1")
    changed = []
    manager.changed.connect(lambda: changed.append(1))
    manager._on_event("run1", {"type": "node_status", "node_id": "n1", "status": "done"})
    assert h.node_status == {"n1": "done"}
    assert h.done == 1
    assert len(changed) == 1


def test_on_event_node_status_planned_counts_as_terminal_too(manager):
    h = _seed(manager, "run1")
    manager._on_event("run1", {"type": "node_status", "node_id": "n1", "status": "planned"})
    assert h.done == 1


def test_on_event_node_status_running_is_not_terminal(manager):
    h = _seed(manager, "run1")
    manager._on_event("run1", {"type": "node_status", "node_id": "n1", "status": "running"})
    assert h.done == 0


def test_on_event_node_status_missing_keys_stores_none_key(manager):
    h = _seed(manager, "run1")
    manager._on_event("run1", {"type": "node_status"})
    assert h.node_status == {None: None}


def test_on_event_run_done_default_ok_marks_done(manager):
    h = _seed(manager, "run1")
    manager._on_event("run1", {"type": "run_done"})
    assert h.status == "done"


def test_on_event_run_done_ok_false_marks_error(manager):
    h = _seed(manager, "run1")
    manager._on_event("run1", {"type": "run_done", "ok": False})
    assert h.status == "error"


def test_on_event_run_done_when_not_running_leaves_status_but_still_emits_changed(manager):
    # quirk (xem docstring dau file): "if status == running" khong doi status,
    # nhung changed.emit() nam NGOAI if nen van chay du khong co gi doi tren
    # handle nay.
    h = _seed(manager, "run1")
    h.status = "stopped"
    changed = []
    manager.changed.connect(lambda: changed.append(1))
    manager._on_event("run1", {"type": "run_done", "ok": False})
    assert h.status == "stopped"
    assert len(changed) == 1


def test_on_event_unknown_run_id_does_not_raise_and_still_reemits_event(manager):
    received = []
    manager.event.connect(lambda rid, ev: received.append((rid, ev)))
    manager._on_event("no-such-run", {"type": "node_status", "node_id": "n1", "status": "done"})
    assert received == [("no-such-run", {"type": "node_status", "node_id": "n1", "status": "done"})]


def test_on_event_none_payload_on_unknown_run_id_is_coerced_to_empty_dict_by_qt(manager):
    # quirk (xem docstring dau file): event = Signal(str, dict) ep None thanh
    # {} ngay tai diem emit -- khac han lop MOI (khong con Signal) nhan dung
    # None goc. Day la khac biet CO CHU Y giua ban cu va ban moi, khong phai
    # bug can sua.
    received = []
    manager.event.connect(lambda rid, ev: received.append((rid, ev)))
    manager._on_event("no-such-run", None)
    assert received == [("no-such-run", {})]


def test_on_event_none_payload_on_known_run_id_does_not_mutate_handle(manager):
    h = _seed(manager, "run1")
    received = []
    manager.event.connect(lambda rid, ev: received.append((rid, ev)))
    manager._on_event("run1", None)
    assert h.status == "running"
    assert h.node_status == {}
    assert received == [("run1", {})]      # cung bi Qt ep thanh {} nhu tren


# ---------------------------------------------------------------------------
# _on_finished
# ---------------------------------------------------------------------------

def test_on_finished_while_running_settles_to_done(manager):
    h = _seed(manager, "run1")
    changed = []
    manager.changed.connect(lambda: changed.append(1))
    manager._on_finished("run1")
    assert h.status == "done"
    assert len(changed) == 1


def test_on_finished_when_already_settled_is_a_noop(manager):
    h = _seed(manager, "run1")
    h.status = "error"
    changed = []
    manager.changed.connect(lambda: changed.append(1))
    manager._on_finished("run1")
    assert h.status == "error"
    assert len(changed) == 0


def test_on_finished_unknown_run_id_is_a_total_noop(manager):
    changed = []
    manager.changed.connect(lambda: changed.append(1))
    manager._on_finished("no-such-run")
    assert manager._runs == {}
    assert changed == []


# ---------------------------------------------------------------------------
# _on_failed
# ---------------------------------------------------------------------------

def test_on_failed_marks_error_with_message_and_emits_run_error_event(manager):
    h = _seed(manager, "run1")
    events = []
    changed = []
    manager.event.connect(lambda rid, ev: events.append((rid, ev)))
    manager.changed.connect(lambda: changed.append(1))
    manager._on_failed("run1", "boom")
    assert h.status == "error"
    assert h.error == "boom"
    assert events == [("run1", {"type": "run_error", "error": "boom"})]
    assert len(changed) == 1


def test_on_failed_overrides_status_even_when_already_settled(manager):
    h = _seed(manager, "run1")
    h.status = "done"
    manager._on_failed("run1", "late failure")
    assert h.status == "error"


def test_on_failed_unknown_run_id_is_a_total_noop(manager):
    events = []
    changed = []
    manager.event.connect(lambda rid, ev: events.append((rid, ev)))
    manager.changed.connect(lambda: changed.append(1))
    manager._on_failed("no-such-run", "err")
    assert events == []
    assert changed == []


# ---------------------------------------------------------------------------
# persistence: hook -> dia THAT (trong sandbox cua rieng tung test) -> reload
# ---------------------------------------------------------------------------

def test_changed_hook_persists_to_history_file(manager, tmp_path):
    _seed(manager, "run1")
    manager._on_event("run1", {"type": "node_status", "node_id": "n1", "status": "done"})
    path = tmp_path / "run_history.json"
    assert path.exists()
    import json
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["runs"]) == 1
    assert data["runs"][0]["id"] == "run1"
    assert data["runs"][0]["status"] == "running"


def test_reloading_manager_after_hook_settles_running_to_stopped(tmp_path, monkeypatch):
    history_path = tmp_path / "run_history.json"
    monkeypatch.setattr(Co4ERunManager, "_history_path", lambda self: history_path)

    mgr1 = Co4ERunManager(_Ctx())
    _seed(mgr1, "run1")
    mgr1._on_event("run1", {"type": "node_status", "node_id": "n1", "status": "done"})

    mgr2 = Co4ERunManager(_Ctx())
    assert "run1" in mgr2._runs
    assert mgr2._runs["run1"].status == "stopped"
    assert mgr2._seq == 1


def test_reloaded_seq_avoids_colliding_with_history_ids(tmp_path, monkeypatch):
    history_path = tmp_path / "run_history.json"
    monkeypatch.setattr(Co4ERunManager, "_history_path", lambda self: history_path)

    mgr1 = Co4ERunManager(_Ctx())
    _seed(mgr1, "run7")
    mgr1._on_event("run7", {"type": "node_status", "node_id": "n1", "status": "done"})

    mgr2 = Co4ERunManager(_Ctx())
    assert mgr2._seq == 7
    assert mgr2._next_id() == "run8"


def test_load_history_missing_file_is_silent_noop(tmp_path, monkeypatch):
    monkeypatch.setattr(Co4ERunManager, "_history_path", lambda self: tmp_path / "does-not-exist.json")
    mgr = Co4ERunManager(_Ctx())
    assert mgr._runs == {}
    assert mgr._seq == 0
