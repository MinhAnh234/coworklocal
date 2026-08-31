"""Characterization test cho khu vực AGENTS trong sidebar của ``Co4ETab``
(``ui/co4e_tab.py``): ``ag_new_btn``/``ag_edit_btn``/``ag_del_btn``/``agent_list``
và phần "populate agent_list" bên trong ``_reload_sidebar`` — đúng các đoạn được
giao: dòng 549-568 (dựng widget + nối signal), 689-713 (``_reload_sidebar``, CHỈ
đoạn agent: item "Parallel" cố định rồi tới danh sách custom agent) và
1339-1367 (``_new_agent``/``_edit_agent``/``_edit_agent_dialog``/``_delete_agent``).

VÌ SAO GHI LẠI CHỨ KHÔNG PHÁN XÉT: đây là lưới an toàn cho đợt tách
``ui/co4e_tab.py`` (2000+ dòng) thành các module con dưới ``presentation/co4e/``
(xem ``docs/architecture/co4e-split-map.md``). Mọi ``assert`` dưới đây được chốt
lại từ giá trị THẬT in ra khi chạy code (quy trình ngược: chạy trước, in ra,
dán vào assert), không phải giá trị tôi nghĩ nó "nên" là gì.

VÌ SAO CHẠY TRONG TIẾN TRÌNH CON CÔ LẬP HOME: y hệt kỹ thuật của
``test_co4e_skills_panel.py`` (đọc file đó để thấy khuôn subprocess gốc) —
dựng ``Co4ETab`` thật kéo theo ``AppConfig``/``CONFIG_DIR`` là hằng số module
tính MỘT LẦN lúc import từ ``Path.home()``, nên phải cô lập ``HOME``/
``USERPROFILE`` TRƯỚC bất kỳ import ``cowork_local.*`` nào, trong một tiến
trình con sạch — patch thuộc tính module sau khi import là không đủ.

AN TOÀN DỮ LIỆU — agent_list NGUY HIỂM HƠN skill_list: ``_reload_sidebar``/
``_new_agent``/``_edit_agent``/``_delete_agent`` gọi thẳng
``core.co4e.list_custom_agents``/``save_custom_agent``/``delete_custom_agent``,
và ``delete_custom_agent`` THỰC SỰ XOÁ file JSON dưới ``CO4E_DIR``. Script con
assert ``str(CONFIG_DIR).startswith(sandbox)`` NGAY sau khi import, trước khi
gọi bất kỳ hàm co4e nào — chạy nhầm trên máy thật sẽ xoá agent thật của người
dùng.

KHÔNG gọi provider AI thật / spawn thread thật: không đụng tới
``Co4ERunManager.start()`` hay ``AgentWorker`` được start thật. ``gen_btn``
("AI-assist" trong ``Co4EAgentDialog``) không được click ở bất kỳ case nào.
``Co4EAgentDialog.exec`` (modal, sẽ treo tiến trình headless) được monkeypatch
thành một hàm giả NGAY TRONG tiến trình con của test — không sửa code sản
phẩm; hàm giả chỉ gõ vào các ô nhập liệu thật (``name_edit``/``role_edit``)
rồi trả về "Accepted" để đường xử lý thật (``dlg.result_agent()`` +
``save_custom_agent``) chạy nguyên vẹn.

QUIRK ĐÃ ĐÓNG ĐINH (xem case tương ứng bên dưới):
  * ``_mint_id`` (``core/co4e.py``) dùng MỘT bộ đếm ``_counter["n"]`` DÙNG
    CHUNG cho mọi loại id (workflow/node/agent...), không tách theo tiền tố.
    ``Co4ETab.__init__`` mint ``wf_000001`` cho luồng rỗng ban đầu TRƯỚC khi
    bất kỳ agent nào được tạo, nên agent custom đầu tiên trong cả tiến trình
    mang id ``agent_000002`` chứ không phải ``agent_000001`` — id "nhảy số"
    không phải bug ghi riêng cho agent, mà là hệ quả của một bộ đếm toàn cục.
  * Dòng 706 dùng ``role=ca.role or "AGENT"`` khi dựng payload kéo-thả, nhưng
    nhãn hiển thị trên dòng 711 dùng THẲNG ``ca.role`` (không fallback) — một
    agent lưu với ``role=""`` hiện dòng tiêu đề rỗng ("  ·   ·  tùy chỉnh")
    nhưng payload kéo lên canvas lại có ``role="AGENT"``. Hai chỗ đọc cùng một
    field nhưng ứng xử khác nhau với chuỗi rỗng.
  * ``_edit_agent``/``_delete_agent`` đọc ``cid`` từ item đang chọn rồi tra
    lại trong ``list_custom_agents()`` MỚI (không dùng payload đã cache) — nếu
    file bị xoá ở "phía sau" (script khác, hoặc do một _delete_agent khác) mà
    ``agent_list`` chưa được ``_reload_sidebar()`` lại, thao tác Sửa trên dòng
    đó là NO-OP thầm lặng (không báo lỗi, không mở dialog) vì
    ``agent is not None`` chặn ở nhánh fallback.
  * Chọn dòng "Parallel" (cố định, không phải custom agent) rồi bấm Sửa/Xoá
    tạo ra CÙNG MỘT thông báo với việc không chọn gì cả
    (``tr("co4e.select_custom_agent")``) — ``cid`` là ``None`` trong cả hai
    trường hợp vì item Parallel không set ``Qt.UserRole + 1``.

VÒNG ĐỜI: đây là giàn giáo cho đợt tách khu vực Agents sang
``presentation/co4e/`` (xem cột "Trạng thái" của dòng liên quan trong
``docs/architecture/co4e-split-map.md``). Sau khi tách xong thành một
``AgentsListPanel``/tương đương với hợp đồng rõ ràng (giống
``SkillsListPanel`` đã làm), các case ở đây nên được viết lại thành test đặc
tả cho panel mới (input rõ ràng, không cần dựng cả ``Co4ETab``/``QApplication``
nặng nề qua subprocess). Ba quirk "bộ đếm id dùng chung", "role rỗng hiển thị
khác payload" và "sửa trên cid đã xoá là no-op thầm lặng" đáng mở issue hỏi ý
kiến sản phẩm trước khi ai đó "dọn" chúng trong lúc tách — đặc biệt quirk thứ
hai, vì nó rất dễ bị "sửa cho gọn" thành dùng cùng một biểu thức fallback ở cả
hai chỗ, và như vậy vô tình đổi cả nhãn hiển thị lẫn dữ liệu kéo-thả.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REPO_PARENT = REPO_ROOT.parent

_SCRIPT = r"""
import sys
sys.path.insert(0, REPO_PARENT_PLACEHOLDER)

from PySide6.QtWidgets import QAbstractItemView, QApplication
from PySide6.QtCore import Qt

from cowork_local.config import AppConfig, CONFIG_DIR
from cowork_local.state import AppContext
from cowork_local.core import co4e as co4e_mod
from cowork_local.ui.co4e_tab import Co4ETab
from cowork_local.ui.co4e_agent_dialog import Co4EAgentDialog
from cowork_local.i18n import tr

sandbox = sys.argv[1]
assert str(CONFIG_DIR).startswith(sandbox), "khong co lap: CONFIG_DIR=" + str(CONFIG_DIR)

app = QApplication([])
ctx = AppContext(AppConfig.load())
tab = Co4ETab(ctx)

# ---- 549-568: widget cua khu vuc AGENTS duoc dung dung nhu quan sat -------
assert tab.ag_new_btn.text() == tr("co4e.new"), tab.ag_new_btn.text()
assert tab.ag_new_btn.toolTip() == tr("co4e.tt_new_agent"), tab.ag_new_btn.toolTip()
assert tab.ag_new_btn.objectName() == "co4eSectionAction"
assert tab.ag_new_btn.isFlat() is True
assert tab.ag_new_btn.cursor().shape() == Qt.PointingHandCursor
assert tab.ag_edit_btn.toolTip() == tr("co4e.tt_edit_agent"), tab.ag_edit_btn.toolTip()
assert tab.ag_edit_btn.width() == 34, tab.ag_edit_btn.width()
assert tab.ag_del_btn.toolTip() == tr("co4e.tt_del_agent"), tab.ag_del_btn.toolTip()
assert tab.ag_del_btn.width() == 34, tab.ag_del_btn.width()
assert tab.agent_list.dragEnabled() is True
assert tab.agent_list.dragDropMode() == QAbstractItemView.DragOnly
print("CASE_WIDGETS_OK")

# ---- 689-713: _reload_sidebar voi thu muc agents RONG ---------------------
# Chi con dong "Parallel" co dinh, khong co custom agent nao.
tab._reload_sidebar()
assert tab.agent_list.count() == 1, tab.agent_list.count()
it0 = tab.agent_list.item(0)
assert it0.text() == tr("co4e.parallel_node"), it0.text()
payload0 = it0.data(Qt.UserRole)
assert payload0 == {
    "variant": "parallel", "label": "Parallel", "role": "PARALLEL",
    "icon": "server", "sub_agents": [],
}, payload0
assert it0.data(Qt.UserRole + 1) is None
print("CASE_EMPTY_OK")

# ---- quirk: bo dem id dung chung cho moi loai (xem docstring dau file) ----
# Co4ETab.__init__ da mint "wf_000001" cho luong rong ban dau -> agent CUSTOM
# dau tien trong ca tien trinh mang id "agent_000002", khong phai "..._000001".
agent1 = co4e_mod.new_custom_agent("Reviewer Bot")
assert agent1.id == "agent_000002", agent1.id
print("CASE_ID_COUNTER_QUIRK_OK")

agent1.role = "REVIEWER"
agent1.icon = "eye"
agent1.instructions = "Review the diff."
agent1.skills = ["Test Skill"]
co4e_mod.save_custom_agent(agent1)
tab._reload_sidebar()
assert tab.agent_list.count() == 2, tab.agent_list.count()
it1 = tab.agent_list.item(1)
assert it1.text() == "Reviewer Bot  ·  REVIEWER ·  " + tr("co4e.custom"), it1.text()
payload1 = it1.data(Qt.UserRole)
assert payload1 == {
    "variant": "step", "label": "Reviewer Bot", "agent_slug": "reviewer-bot",
    "role": "REVIEWER", "icon": "eye", "instructions": "Review the diff.",
    "context": "", "model": "", "self_verify": True, "max_verify_rounds": 1,
    "permission_preset": "full", "skills": ["Test Skill"], "attachments": [],
    "sub_agents": [],
}, payload1
assert it1.data(Qt.UserRole + 1) == agent1.id
assert it1.icon().isNull() is False
print("CASE_ONE_AGENT_OK")

# ---- quirk: agent luu voi name="" va role="" -------------------------------
# Nhan hien thi (dong 711) dung THANG ca.role -> rong; nhung payload keo-tha
# (dong 706) dung "ca.role or 'AGENT'" -> fallback ve "AGENT". Cung mot field,
# hai cach doc khac nhau khi gap chuoi rong.
agent2 = co4e_mod.new_custom_agent("")
agent2.role = ""
co4e_mod.save_custom_agent(agent2)
tab._reload_sidebar()
assert tab.agent_list.count() == 3, tab.agent_list.count()
it2 = tab.agent_list.item(2)
assert it2.text() == "  ·   ·  " + tr("co4e.custom"), repr(it2.text())
payload2 = it2.data(Qt.UserRole)
assert payload2["role"] == "AGENT", payload2["role"]
print("CASE_EMPTY_NAME_ROLE_QUIRK_OK")

# ---- 1339-1340: _new_agent() mo dialog cho MOT agent moi tinh --------------
# Gia lap Co4EAgentDialog.exec() ngay trong tien trinh con nay (khong sua code
# san pham): go vao chinh cac o nhap that (name_edit/role_edit) roi tra ve
# Accepted, de duong xu ly that (result_agent() + save_custom_agent) chay
# nguyen ven.
calls = {"n": 0}


def _fake_exec(self):
    calls["n"] += 1
    self.name_edit.setText(f"Fresh-{calls['n']}")
    self.role_edit.setText("Scout")
    return 1  # QDialog.Accepted


Co4EAgentDialog.exec = _fake_exec

before = tab.agent_list.count()
tab.ag_new_btn.click()  # 555: noi that toi _new_agent
assert calls["n"] == 1
assert tab.agent_list.count() == before + 1, tab.agent_list.count()
names = [tab.agent_list.item(i).text() for i in range(tab.agent_list.count())]
assert names[-1] == "Fresh-1  ·  SCOUT ·  " + tr("co4e.custom"), names
print("CASE_NEW_AGENT_VIA_CLICK_OK")

# ---- 1342-1350: _edit_agent() khong co dong nao dang chon ------------------
msgs = []
tab.status_message.connect(lambda m: msgs.append(m))
tab.agent_list.setCurrentRow(-1)
assert tab.agent_list.currentItem() is None
tab._edit_agent()
assert msgs == [tr("co4e.select_custom_agent")], msgs
print("CASE_EDIT_NO_SELECTION_OK")

# ---- quirk: chon dong "Parallel" (khong phai custom agent) -> CUNG thong
# bao nhu khong chon gi, vi Qt.UserRole + 1 la None o dong nay -----------
tab.agent_list.setCurrentRow(0)
tab._edit_agent()
assert msgs == [tr("co4e.select_custom_agent")] * 2, msgs
tab._delete_agent()
assert msgs == [tr("co4e.select_custom_agent")] * 3, msgs
assert tab.agent_list.count() == before + 1, "chon Parallel roi Xoa khong lam mat dong nao"
print("CASE_PARALLEL_ROW_NOOP_QUIRK_OK")

# ---- 1342-1358: _edit_agent() tren mot custom agent that -------------------
target_row = next(
    i for i in range(tab.agent_list.count())
    if tab.agent_list.item(i).data(Qt.UserRole + 1) == agent1.id
)
tab.agent_list.setCurrentRow(target_row)
tab.ag_edit_btn.click()  # 562: noi that toi _edit_agent
assert calls["n"] == 2
names = [tab.agent_list.item(i).text() for i in range(tab.agent_list.count())]
assert names[target_row] == "Fresh-2  ·  SCOUT ·  " + tr("co4e.custom"), names
# id giu nguyen qua lan sua (chi noi dung doi, khong mint id moi)
assert tab.agent_list.item(target_row).data(Qt.UserRole + 1) == agent1.id
print("CASE_EDIT_EXISTING_OK")

# ---- quirk: sua tren mot cid da bi xoa "phia sau" -> no-op tham lang -------
# _edit_agent tra cuu lai list_custom_agents() MOI, khong dung payload da cache
# trong item; neu file da mat va agent_list CHUA duoc _reload_sidebar(), thao
# tac Sua tren dong do khong lam gi (khong mo dialog, khong loi).
co4e_mod.delete_custom_agent(agent1.id)
stale_item = tab.agent_list.item(target_row)
assert stale_item.data(Qt.UserRole + 1) == agent1.id  # item van con cid cu
tab.agent_list.setCurrentRow(target_row)
tab._edit_agent()
assert calls["n"] == 2, "khong duoc mo dialog voi cid da bi xoa"
print("CASE_EDIT_STALE_CID_QUIRK_OK")

# ---- 1360-1367: _delete_agent() tren mot custom agent that -----------------
tab._reload_sidebar()
count_before_delete = tab.agent_list.count()
del_row, del_cid = next(
    (i, tab.agent_list.item(i).data(Qt.UserRole + 1))
    for i in range(tab.agent_list.count())
    if tab.agent_list.item(i).data(Qt.UserRole + 1)
)
tab.agent_list.setCurrentRow(del_row)
tab.ag_del_btn.click()  # 563: noi that toi _delete_agent
assert tab.agent_list.count() == count_before_delete - 1
assert not (co4e_mod.agents_dir() / f"{del_cid}.json").exists()
print("CASE_DELETE_REAL_OK")

# ---- fallback: xoa lai mot id da khong con file -> khong nem loi -----------
co4e_mod.delete_custom_agent(del_cid)
print("CASE_DELETE_ALREADY_GONE_OK")

print("ALL_OK")
"""


def _run_isolated(sandbox: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["HOME"] = str(sandbox)
    env["USERPROFILE"] = str(sandbox)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("HOMEDRIVE", None)
    env.pop("HOMEPATH", None)

    script = _SCRIPT.replace("REPO_PARENT_PLACEHOLDER", repr(str(REPO_PARENT)))
    return subprocess.run(
        [sys.executable, "-c", script, str(sandbox)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_co4e_agent_panel_hanh_vi_hien_tai(tmp_path):
    sandbox = tmp_path / "home"
    sandbox.mkdir()

    result = _run_isolated(sandbox)

    assert result.returncode == 0, (
        f"characterization script that bai (exit {result.returncode}):\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    for marker in (
        "CASE_WIDGETS_OK",
        "CASE_EMPTY_OK",
        "CASE_ID_COUNTER_QUIRK_OK",
        "CASE_ONE_AGENT_OK",
        "CASE_EMPTY_NAME_ROLE_QUIRK_OK",
        "CASE_NEW_AGENT_VIA_CLICK_OK",
        "CASE_EDIT_NO_SELECTION_OK",
        "CASE_PARALLEL_ROW_NOOP_QUIRK_OK",
        "CASE_EDIT_EXISTING_OK",
        "CASE_EDIT_STALE_CID_QUIRK_OK",
        "CASE_DELETE_REAL_OK",
        "CASE_DELETE_ALREADY_GONE_OK",
        "ALL_OK",
    ):
        assert marker in result.stdout, f"thieu marker {marker}\n{result.stdout}"

    # Sandbox chi duoc dung boi save_custom_agent()/delete_custom_agent() cua
    # chinh test (khong co du lieu nguoi dung that nao bi cham vao) -
    # CONFIG_DIR nam trong sandbox nhu da assert ngay dau script.
    assert (sandbox / ".cowork_local" / "co4e").exists()
