"""Integration test đầu-cuối cho Co4E Studio — dựng THẬT ``Co4ETab`` qua
``build_co4e_tab()`` và lái một luồng người dùng thật xuyên qua NHIỀU panel đã
tách (canvas, chat, agent/skills list, run control) trong CÙNG MỘT instance,
để bắt lỗi mà các characterization test riêng từng panel (test_co4e_canvas_widget,
test_co4e_chat_view, test_co4e_runs_page, test_co4e_agent_panel,
test_co4e_skills_panel) không thể bắt: các panel đó mỗi cái dựng ĐỘC LẬP, không
đi qua ``Co4ETab`` thật nên không lộ lỗi wiring xuyên-panel (ví dụ: alias thiếu,
gọi nhầm panel khác, state canvas mất khi chuyển qua trang Runs rồi quay lại).

PHẠM VI CHỦ ĐỘNG LOẠI TRỪ — KHÔNG bấm nút Run/Stop và KHÔNG gọi bất kỳ
method nào dẫn tới ``Co4ERunManager.start()`` (dòng dẫn tới ``AgentWorker``/
``QThread``/gọi AI thật) — đúng nguyên tắc đã áp dụng xuyên suốt mọi
characterization test của lane N3 (xem ``test_co4e_run_manager_behavior.py``).
Trang "Flow Status"/Runs được kiểm ở trạng thái RỖNG (không có run nào), đủ để
xác nhận panel + wiring không vỡ khi chuyển trang, không cần một run thật.

Vì sao chạy trong tiến trình con cô lập HOME/USERPROFILE (giống
``test_build_co4e_tab.py``, xem docstring đầu file đó để biết đủ cả 2 cái bẫy
CONFIG_DIR/CONFIG_PATH tính lúc import): dựng ``Co4ETab`` thật kéo theo
``Co4ERunManager`` (đọc lịch sử run từ ``CO4E_DIR``/``CONFIG_DIR`` lúc
``__init__``) — không cô lập sẽ đọc/ghi vào ``~/.cowork_local`` thật của người
dùng chạy test.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPO_PARENT = REPO_ROOT.parent

_SCRIPT = """
import sys
sys.path.insert(0, {repo_parent!r})

from PySide6.QtWidgets import QApplication

from cowork_local.config import AppConfig, CONFIG_DIR
from cowork_local.state import AppContext
from cowork_local.core.co4e import Step
from cowork_local.presentation.co4e.co4e_tab import build_co4e_tab

sandbox = sys.argv[1]
assert str(CONFIG_DIR).startswith(sandbox), "khong co lap: CONFIG_DIR=" + str(CONFIG_DIR)

app = QApplication([])
ctx = AppContext(AppConfig.load())


class _FakeWorkflowService:
    \"\"\"build_co4e_tab() hien tai chua dung toi (xem presentation/co4e/co4e_tab.py) -
    chi can mot doi tuong bat ky de kiem factory nhan dung tham so bat buoc thu hai.\"\"\"


tab = build_co4e_tab(ctx, _FakeWorkflowService())

# ---- 1) sidebar: 4 panel da tach deu co mat, danh sach rong luc moi dung ---
assert tab.wf_list.count() == 0, "wf_list phai rong luc moi dung"
assert tab.agent_list.count() >= 0          # AgentListPanel.list_widget qua alias
assert tab.skill_list.count() >= 0          # SkillsListPanel.list_widget qua alias
assert tab.runs_table.rowCount() == 0, "Flow Status phai rong khi chua co run nao"

# ---- 2) "New" workflow (wf_new_btn -> _new_workflow) -----------------------
tab.wf_new_btn.click()
assert tab.canvas.nodes() == [], "flow moi phai la canvas rong"
assert tab._wf.name, "flow moi phai co ten (untitled)"

# ---- 3) them 2 node ket noi tren canvas THAT (khong drag-drop, goi truc tiep
# dung method public da duoc characterization test_co4e_canvas_widget.py khoa
# hanh vi - integration test nay chi kiem NO CHAY DUOC xuyen qua Co4ETab thuc,
# khong lap lai chi tiet hanh vi canvas) --------------------------------------
n1 = tab.canvas.add_node(Step(label="Buoc 1"), x=60, y=60)
n2_id = None
tab.canvas.add_step_below(n1)
assert len(tab.canvas.nodes()) == 2, "canvas phai co 2 node sau add_node + add_step_below"
assert len(tab.canvas.edges()) == 1, "add_step_below phai tu noi edge tu node truoc"

# ---- 4) mo/thu gon khung chat (ChatPanel + _toggle_messages xuyen panel) ---
assert tab.chat_stack.isHidden(), "chat phai COLLAPSED mac dinh (dung dac ta ChatPanel)"
tab.chat_toggle_btn.click()
assert not tab.chat_stack.isHidden(), "bam nut thu/mo phai HIEN khung chat"
tab.chat_toggle_btn.click()
assert tab.chat_stack.isHidden(), "bam lan 2 phai AN lai (toggle dung 2 chieu)"

# ---- 5) chuyen qua trang Flow Status (RunsPagePanel) roi quay lai flow editor,
# xac nhan canvas KHONG mat 2 node da them o buoc 3 (rui ro thuc su cua viec
# tach RunsPagePanel: state flow co song sot qua center_stack.setCurrentIndex?)
tab.runs_btn.setChecked(True)
assert tab.center_stack.currentIndex() == 0, "bam Flow Status phai chuyen sang trang Runs"
assert tab.runs_table.rowCount() == 0, "van chua co run nao, bang phai rong"
tab.runs_btn.setChecked(False)
assert tab.center_stack.currentIndex() == 1, "bo chon Flow Status phai tro lai flow editor"
assert len(tab.canvas.nodes()) == 2, "quay lai flow editor KHONG duoc mat node da them truoc do"

# ---- CHU DINH KHONG lam: khong bam run_stop_btn/bat ky nut Run nao, khong goi
# tab.manager.start(...) - do se tao AgentWorker/QThread thuc va co the goi AI
# thuc (ngoai pham vi integration test nay, xem docstring dau file).

print("INTEGRATION_OK")
"""


def test_co4e_end_to_end_qua_nhieu_panel_da_tach(tmp_path):
    sandbox = tmp_path / "home"
    sandbox.mkdir()

    env = dict(os.environ)
    env["HOME"] = str(sandbox)
    env["USERPROFILE"] = str(sandbox)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env.pop("HOMEDRIVE", None)
    env.pop("HOMEPATH", None)

    script = _SCRIPT.format(repo_parent=str(REPO_PARENT))
    result = subprocess.run(
        [sys.executable, "-c", script, str(sandbox)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, (
        f"integration test that bai (exit {result.returncode}):\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    assert "INTEGRATION_OK" in result.stdout, result.stdout

    # Sandbox khong duoc dung: khong co run nao duoc kich hoat trong luot nay,
    # nen Co4ERunManager khong co gi de ghi xuong dia (_save_history chi ghi khi
    # changed.emit() that su co run/thay doi - _new_workflow khong dung toi
    # manager, add_node/canvas khong dung toi manager).
    assert not (sandbox / ".cowork_local" / "co4e" / "run_history.json").exists(), (
        "chua co run nao thi khong duoc tu ghi lich su run xuong dia"
    )
