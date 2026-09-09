"""Characterization test cho ``StepConfigPanel`` (``ui/co4e_config_panel.py``,
dong 133-528) — KHONG bao gom ``_SectionHeader``/``_add_section`` (khung UI
chung, khong co hanh vi nghiep vu rieng dang characterize).

VI SAO GHI LAI CHU KHONG PHAN XET: day la luoi an toan cho dot tach
``StepConfigPanel`` ra khoi ``ui/co4e_config_panel.py`` sang cac module con
duoi ``presentation/co4e/`` (vi du ``node_property_panel.py``,
``node_property_actions_mixin.py``, ``step_config_section.py`` — xem
``docs/architecture/co4e-split-map-node-property.md``). Moi ``assert`` duoi
day duoc chot lai tu gia tri THAT in ra khi chay code that (quy trinh nguoc:
chay truoc, in ra, dan vao assert) — khong phai gia tri "nen" la gi theo suy
doan.

VI SAO CAN TIEN TRINH CON + CO LAP HOME: ban than ``StepConfigPanel.__init__``/
``load_step`` KHONG cham dia/mang, nhung ``_available_agent_names()`` (goi tu
``_add_subagent``/``_edit_subagent``) doc THAT tu
``core.co4e.list_custom_agents()`` duoi ``CONFIG_DIR/co4e/agents`` — mot
hang so module tinh MOT LAN tu ``Path.home()`` luc import. Vi vay HOME/
USERPROFILE phai duoc tro sang thu muc tam TRUOC BAT KY import
``cowork_local.*`` nao, trong mot tien trinh con sach (patch thuoc tinh sau
khi import la khong du) — dung khuon ``tools/capture_screens.py::_isolate_home``
va ``tests/characterization/test_co4e_agent_panel.py``. Tien trinh con rieng
cung tranh xung dot QApplication singleton neu mot tien trinh pytest khac da
tao QApplication trong cung luot chay. ``QT_QPA_PLATFORM=offscreen`` duoc dat
TRUOC khi import PySide6 (dung khuon ``tools/check_co4e.py`` dong 22+40-42);
script con assert ngay ``str(CONFIG_DIR).startswith(sandbox)`` truoc khi goi
bat ky ham co4e nao (giong ``tools/check_co4e.py:47``) — khong co lap la doc
(va co the ghi) du lieu that cua nguoi dung qua ``list_custom_agents()``/
``save_custom_agent()``.

KHONG goi provider AI that / spawn thread that: ``_ai_draft()`` va
``_load_models()`` (dung ``AgentWorker``/``QThread`` that) KHONG duoc goi o
bat ky case nao trong file nay — hai ham do nam NGOAI pham vi duoc giao
(139-462) va can duoc characterize rieng, tach biet, voi worker/thread duoc
gia lap chu khong start that.

QUIRK DA DONG DINH (xem case tuong ung ben duoi):
  * ``gen_btn``/``load_models_btn`` duoc set ``setEnabled(ctx is not None)``
    ngay trong ``__init__`` (dong 181, 208), NHUNG dong 313 goi
    ``self.setEnabled(False)`` cho CA PANEL o cuoi ``__init__`` — vi Qt tinh
    ``isEnabled()`` hieu qua tu ca chuoi ancestor, ca hai nut deu tra ve
    ``False`` NGAY SAU KHI DUNG XONG bat ke ``ctx`` la gi, cho toi khi
    ``load_step()`` (hoac ``setEnabled(True)`` truc tiep) bat lai ca panel.
    Doc rieng dong 181/208 se de tuong "ctx=None thi nut luon tat, ctx khac
    None thi nut luon bat" — sai, ca hai deu tat cho den khi co step duoc nap.
  * ``rounds_spin`` = ``QSpinBox(range=1..5)`` nhung code goi
    ``setValue(max(1, step.max_verify_rounds))`` (dong 330) — voi
    ``max_verify_rounds=10``, ``max(1, 10) == 10`` nhung ``QSpinBox`` tu kep
    ve tran cua no nen gia tri hien thi la ``5``, khong phai ``10``. Doc code
    ma khong chay se tuong gia tri duoc giu nguyen.
  * ``perm_combo`` voi ``step.permission_preset`` khong nam trong
    ``PERMISSION_PRESETS`` (nhanh fallback cua ``findData`` tra ve -1) roi ve
    index 0 == ``"inherit"`` — im lang, khong bao loi.
  * ``load_step`` chi dung skill_names de dung skills_list; mot skill trong
    ``step.skills`` khong con trong ``skill_names`` (skill da bi xoa khoi
    registry) don gian BIEN MAT khoi checklist — va khi ``_on_edit`` chay lan
    ke tiep (do BAT KY thay doi field nao khac, khong can dung vao
    skills_list), ``s.skills`` duoc GHI DE lai chi bang cac item dang hien
    trong checklist, nen ten skill "mo coi" do bi RUNG VINH VIEN khoi
    ``step.skills`` — mot edit khong lien quan (vi du sua role) am tham xoa
    du lieu skill cu.
  * ``variant != "parallel"``: ``_parallel_card`` bi an VA ``sub_list.clear()``
    duoc goi, nhung ``step.sub_agents`` KHONG bi dung vao neu ``is_par`` False
    — du liệu van con trong step, chi khong hien tren UI.
  * ``_add_subagent``: khi ``_available_agent_names()`` tra ve danh sach RONG,
    code chuyen sang ``ask_text`` thay vi ``ask_item`` (dong
    401-402) — nhanh fallback nay chi cham toi khi khong con agent nao (builtin
    + custom) de chon, hiem khi xay ra tren du lieu that nhung van la mot
    nhanh code song.
  * ``_edit_subagent``: neu agent hien tai cua sub-agent khong con trong danh
    sach ten kha dung (``cur not in names``), dialog mo tai index 0 thay vi
    bao loi hay giu nguyen lua chon cu.

VONG DOI: day la gian giao cho dot tach ``StepConfigPanel`` sang
``presentation/co4e/`` (xem ``docs/architecture/co4e-split-map-node-property.md``
cho ke hoach tach cu the). Sau khi tach xong thanh cac lop/mixin voi hop dong
ro rang, cac case o day nen duoc viet lai thanh test dac ta cho tung phan
(khong can dung ca ``QApplication``/tien trinh con neu phan tach ra la logic
thuan). Ba quirk "panel disabled de len enable cua nut", "orphan skill bi xoa
qua mot edit khong lien quan" va "sub_agents khong dong bo voi sub_list khi
doi variant" dang mo issue hoi y kien san pham truoc khi ai do "don" chung
trong luc tach — dac biet quirk orphan-skill, vi day la mot dang mat du lieu
tham lang de bi coi la bug can sua ngay khi gap lai, nhung sua no thay doi
hanh vi luu tru hien co ma khong ai ro co ai dang phu thuoc vao khong.
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

from pathlib import Path as _PP
from PySide6.QtWidgets import QApplication, QFileDialog, QListWidgetItem
from PySide6.QtCore import Qt

from cowork_local.config import CONFIG_DIR

sandbox = sys.argv[1]
assert str(CONFIG_DIR).startswith(str(_PP(sandbox))), "khong co lap: CONFIG_DIR=" + str(CONFIG_DIR)

app = QApplication([])

from cowork_local.ui.co4e_config_panel import StepConfigPanel
from cowork_local.core.co4e import Step, SubAgent, PERMISSION_PRESETS
from cowork_local.core import co4e as co4e_mod
from cowork_local.core.co4e_builtins import BUILTIN_AGENTS

# ---- __init__ (139-313) ----------------------------------------------------
p = StepConfigPanel()
assert p.gen_btn.isEnabled() is False
assert p.load_models_btn.isEnabled() is False
assert p.isEnabled() is False, "panel bat dau bi setEnabled(False) o dong 313"
assert p.perm_combo.count() == len(PERMISSION_PRESETS) == 4
assert [p.perm_combo.itemData(i) for i in range(4)] == list(PERMISSION_PRESETS)
assert (p.rounds_spin.minimum(), p.rounds_spin.maximum()) == (1, 5)
print("CASE_INIT_DEFAULT_CTX_NONE_OK")

# quirk: gen_btn/load_models_btn duoc set theo ctx, nhung setEnabled(False)
# cho CA PANEL o cuoi __init__ de len tren ca hai -> ca hai deu False cho den
# khi mot cai gi do bat lai ca panel (vd load_step() goi setEnabled(True)).
p_ctx = StepConfigPanel(ctx=object())
assert p_ctx.gen_btn.isEnabled() is False, "quirk: panel disabled de len len ctx!=None"
assert p_ctx.load_models_btn.isEnabled() is False
p_ctx.setEnabled(True)  # mo phong dieu load_step() lam
assert p_ctx.gen_btn.isEnabled() is True
assert p_ctx.load_models_btn.isEnabled() is True

p_none = StepConfigPanel(ctx=None)
p_none.setEnabled(True)
assert p_none.gen_btn.isEnabled() is False, "ctx=None -> nut van tat sau khi panel duoc bat"
assert p_none.load_models_btn.isEnabled() is False
print("CASE_INIT_CTX_ENABLE_QUIRK_OK")

p.show()
app.processEvents()
assert p._parallel_card.isVisible() is True, "form4/_parallel_card khong tu an luc dung"
print("CASE_INIT_PARALLEL_CARD_DEFAULT_VISIBLE_OK")

# ---- load_step (316-354): step "step" thuong -------------------------------
step = Step(
    variant="step", label="My Step", role="worker", icon="file",
    instructions="Do X", context="bg info", model="gpt-4",
    permission_preset="standard", self_verify=False, max_verify_rounds=3,
    skills=["Test Skill", "OrphanSkill"], attachments=["C:/foo/bar/baz.txt", "note.md"],
    sub_agents=[SubAgent(agent="Ghost")],
)
p.load_step("n1", step, ["Test Skill", "Other Skill"])
assert p.label_edit.text() == "My Step"
assert p.role_edit.text() == "worker"
assert p.icon_edit.currentText() == "file"
assert p.instructions_edit.toPlainText() == "Do X"
assert p.context_edit.toPlainText() == "bg info"
assert p.model_combo.currentText() == "gpt-4"
assert (p.perm_combo.currentIndex(), p.perm_combo.currentData()) == (2, "standard")
assert p.verify_chk.isChecked() is False
assert p.rounds_spin.value() == 3
assert p.skills_list.count() == 2, "chi 2 muc trong skill_names duoc ve, OrphanSkill khong co hang"
assert [p.skills_list.item(i).text() for i in range(2)] == ["Test Skill", "Other Skill"]
assert p.skills_list.item(0).checkState() == Qt.Checked
assert p.skills_list.item(1).checkState() == Qt.Unchecked
assert p.attach_list.count() == 2
assert p.attach_list.item(0).text() == "baz.txt"
assert p.attach_list.item(0).toolTip() == "C:/foo/bar/baz.txt"
assert p.attach_list.item(1).text() == "note.md"
app.processEvents()
assert p._parallel_card.isVisible() is False, "variant='step' -> card an"
assert p.sub_list.count() == 0, "quirk: sub_agents khong rong nhung khong dong bo vao UI khi khong phai parallel"
assert step.sub_agents == [SubAgent(agent="Ghost")], "du lieu step khong bi dong cham, chi UI khong ve"
print("CASE_LOAD_STEP_BASIC_OK")

# quirk: rounds_spin.setValue(max(1, n)) nhung QSpinBox tu kep tran o 5.
p.load_step("n0", Step(max_verify_rounds=0), [])
assert p.rounds_spin.value() == 1
p.load_step("nneg", Step(max_verify_rounds=-5), [])
assert p.rounds_spin.value() == 1
p.load_step("n10", Step(max_verify_rounds=10), [])
assert p.rounds_spin.value() == 5, "quirk: max(1,10)=10 nhung QSpinBox kep ve tran 5"
print("CASE_LOAD_STEP_ROUNDS_CLAMP_QUIRK_OK")

# quirk: permission_preset la khoa khong ton tai -> fallback ve index 0 (inherit)
p.load_step("nbad", Step(permission_preset="does-not-exist"), [])
assert (p.perm_combo.currentIndex(), p.perm_combo.currentData()) == (0, "inherit")
print("CASE_LOAD_STEP_UNKNOWN_PRESET_FALLBACK_OK")

# variant="parallel" -> card hien, sub_list duoc ve tu sub_agents
steppar = Step(variant="parallel", sub_agents=[SubAgent(agent="A1"), SubAgent(agent="A2")])
p.load_step("npar", steppar, [])
app.processEvents()
assert p._parallel_card.isVisible() is True
assert [p.sub_list.item(i).text() for i in range(p.sub_list.count())] == ["A1", "A2"]
print("CASE_LOAD_STEP_PARALLEL_OK")

# rong: skills/attachments rong -> list rong, khong loi
p.load_step("nempty", Step(), [])
assert p.skills_list.count() == 0
assert p.attach_list.count() == 0
print("CASE_LOAD_STEP_EMPTY_OK")

# ---- clear_step (356-359) ---------------------------------------------------
p.clear_step()
assert p._step is None
assert p._node_id == ""
assert p.isEnabled() is False
print("CASE_CLEAR_STEP_OK")

# _on_edit voi _step None -> khong loi, khong lam gi
p._on_edit()
print("CASE_ON_EDIT_NO_STEP_NOOP_OK")

# ---- _on_edit (362-378): guard _loading, fallback role, quirk orphan-skill --
p.load_step("npar2", step, ["Test Skill", "Other Skill"])
assert step.skills == ["Test Skill", "OrphanSkill"], "chua edit gi thi step chua bi dong den"
p.role_edit.setText("")  # -> _on_edit tu dong chay qua signal that, khong mock
assert step.role == "AGENT", "role rong -> fallback 'AGENT' (dong 367)"
assert step.skills == ["Test Skill"], (
    "quirk: mot edit KHONG LIEN QUAN (sua role) cung ghi de s.skills bang "
    "danh sach dang checked trong UI -> OrphanSkill bi rung vinh vien"
)
print("CASE_ON_EDIT_ROLE_FALLBACK_AND_ORPHAN_SKILL_QUIRK_OK")

p._loading = True
step.role = "UNTOUCHED"
p.role_edit.setText("Something Else")
assert step.role == "UNTOUCHED", "guard _loading chan _on_edit khong ghi lai step"
p._loading = False
print("CASE_ON_EDIT_LOADING_GUARD_OK")

p.role_edit.setText("scout")
assert step.role == "SCOUT", "role duoc upper() hoa (dong 367)"
print("CASE_ON_EDIT_ROLE_UPPERCASE_OK")

# ---- _available_agent_names (380-390, static) ------------------------------
names0 = StepConfigPanel._available_agent_names()
assert names0 == [a.name for a in BUILTIN_AGENTS], "khong co custom agent -> chi builtin, dung thu tu"
assert names0[0] == "Business Analyst"
assert len(names0) == len(BUILTIN_AGENTS) == 19
print("CASE_AVAILABLE_NAMES_NO_CUSTOM_OK")

custom = co4e_mod.new_custom_agent("Zed Custom")
co4e_mod.save_custom_agent(custom)
names1 = StepConfigPanel._available_agent_names()
assert names1[0] == "Zed Custom", "custom agent dung TRUOC builtin"
assert len(names1) == len(BUILTIN_AGENTS) + 1
print("CASE_AVAILABLE_NAMES_ONE_CUSTOM_OK")

# quirk: custom trung ten voi mot builtin -> chi giu 1 lan (dong 389: "not in names")
dup = co4e_mod.new_custom_agent(BUILTIN_AGENTS[0].name)
co4e_mod.save_custom_agent(dup)
names2 = StepConfigPanel._available_agent_names()
assert names2.count(BUILTIN_AGENTS[0].name) == 1, "trung ten voi builtin bi loai bo, khong nhan doi"
assert names2[0] == "Zed Custom"
print("CASE_AVAILABLE_NAMES_DEDUPE_WITH_BUILTIN_OK")

# ---- _add_subagent (392-408) ------------------------------------------------
pstep = Step(variant="parallel")
p.load_step("nsub", pstep, [])
p._step = None
before_n = p.sub_list.count()
p._add_subagent()
assert p.sub_list.count() == before_n, "_step None -> _add_subagent la no-op"
print("CASE_ADD_SUBAGENT_NO_STEP_NOOP_OK")

p._step = pstep
# Panel goi ask_item/ask_text cua ui/dialog_buttons (khong con goi thang ham
# tinh QInputDialog.get*: ham tinh tu dung hop thoai ben trong nen nut "Cancel"
# cua no luon tieng Anh). Patch dung namespace cua mixin dang goi — patch vao
# QInputDialog nhu truoc se KHONG chan duoc gi va hop thoai that se mo ra treo.
from cowork_local.presentation.co4e import node_property_actions_mixin as _acts

orig_getItem = _acts.ask_item
orig_getText = _acts.ask_text
changed_n = {"n": 0}
p.changed.connect(lambda: changed_n.__setitem__("n", changed_n["n"] + 1))

_acts.ask_item = lambda *a, **k: ("Picked Agent", True)
p._add_subagent()
assert [s.agent for s in pstep.sub_agents] == ["Picked Agent"]
assert [p.sub_list.item(i).text() for i in range(p.sub_list.count())] == ["Picked Agent"]
assert changed_n["n"] == 1
print("CASE_ADD_SUBAGENT_PICKED_OK")

_acts.ask_item = lambda *a, **k: ("", True)
p._add_subagent()
assert [s.agent for s in pstep.sub_agents] == ["Picked Agent"], "ten rong (sau strip) -> khong them"
assert changed_n["n"] == 1, "khong them thi khong emit changed"
print("CASE_ADD_SUBAGENT_EMPTY_NAME_NOOP_OK")

_acts.ask_item = lambda *a, **k: ("Should Not Add", False)
p._add_subagent()
assert [s.agent for s in pstep.sub_agents] == ["Picked Agent"], "ok=False -> khong them"
print("CASE_ADD_SUBAGENT_CANCELLED_NOOP_OK")

# quirk: khi _available_agent_names() rong -> dung getText thay vi getItem (dong 401-402)
# GHI CHU DOT TACH mixin (khong doi hanh vi, chi doi CACH patch/restore trong
# test): sau khi StepConfigPanel._available_agent_names duoc dua vao mixin
# rieng (_StepConfigActionsMixin), no khong con nam trong
# StepConfigPanel.__dict__ nua (ma nam trong __dict__ cua mixin, StepConfigPanel
# chi ke thua qua MRO) nen "StepConfigPanel.__dict__['_available_agent_names']"
# nem KeyError. Gan de ghi de truc tiep len StepConfigPanel (nhu dong duoi) van
# shadow dung nhu truoc; khi xong chi can `del` thuoc tinh do khoi
# StepConfigPanel de no roi ve lai dung method ke thua tu mixin - tuong duong
# hanh vi voi cach "luu roi gan lai" cu, khong lam yeu di assert nao.
StepConfigPanel._available_agent_names = staticmethod(lambda: [])
_acts.ask_text = lambda *a, **k: ("Typed Agent", True)
p._add_subagent()
assert [s.agent for s in pstep.sub_agents] == ["Picked Agent", "Typed Agent"]
del StepConfigPanel._available_agent_names
_acts.ask_item = orig_getItem
_acts.ask_text = orig_getText
print("CASE_ADD_SUBAGENT_EMPTY_NAMES_USES_GETTEXT_QUIRK_OK")

# ---- _edit_subagent (410-428) -----------------------------------------------
pstep2 = Step(variant="parallel", sub_agents=[SubAgent(agent="Unknown Agent XYZ")])
p.load_step("nedit", pstep2, [])
captured = {}


def _fake_get_item(*a, **k):
    captured["items"] = a[3]
    captured["current_index"] = a[4]
    return ("Renamed", True)


_acts.ask_item = _fake_get_item
item0 = p.sub_list.item(0)
p._edit_subagent(item0)
assert captured["current_index"] == 0, "quirk: cur khong nam trong names -> mo dialog tai index 0"
assert pstep2.sub_agents[0].agent == "Renamed"
assert item0.text() == "Renamed"
print("CASE_EDIT_SUBAGENT_UNKNOWN_CUR_STARTS_AT_0_OK")

foreign_item = QListWidgetItem("not in list")
snapshot = dict(captured)
p._edit_subagent(foreign_item)
assert captured == snapshot, "item khong thuoc sub_list (row=-1) -> no-op"
_acts.ask_item = orig_getItem
print("CASE_EDIT_SUBAGENT_FOREIGN_ITEM_NOOP_OK")

# ---- _del_subagent (430-437) -------------------------------------------------
pstep3 = Step(variant="parallel", sub_agents=[SubAgent(agent="A"), SubAgent(agent="B")])
p.load_step("ndel", pstep3, [])
p.sub_list.setCurrentRow(-1)
p._del_subagent()
assert [s.agent for s in pstep3.sub_agents] == ["A", "B"], "khong chon dong nao -> no-op"
p.sub_list.setCurrentRow(0)
p._del_subagent()
assert [s.agent for s in pstep3.sub_agents] == ["B"]
assert [p.sub_list.item(i).text() for i in range(p.sub_list.count())] == ["B"]
print("CASE_DEL_SUBAGENT_OK")

# ---- _add_attachment (439-453) -----------------------------------------------
astep = Step(attachments=["already/here.txt"])
p.load_step("natt", astep, [])
orig_getOpenFileNames = QFileDialog.getOpenFileNames
QFileDialog.getOpenFileNames = staticmethod(
    lambda *a, **k: (["already/here.txt", "new/one.txt", ""], "")
)
att_changed = {"n": 0}
p.changed.connect(lambda: att_changed.__setitem__("n", att_changed["n"] + 1))
p._add_attachment()
assert astep.attachments == ["already/here.txt", "new/one.txt"], (
    "duplicate bi loai (dong 447), chuoi rong bi loai boi 'if f and ...'"
)
assert p.attach_list.count() == 2
print("CASE_ADD_ATTACHMENT_DEDUPE_AND_SKIP_EMPTY_OK")

before_att_changed = att_changed["n"]
QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: ([], ""))
p._add_attachment()
assert att_changed["n"] == before_att_changed, "files rong -> khong emit changed (dong 452-453)"
QFileDialog.getOpenFileNames = orig_getOpenFileNames
print("CASE_ADD_ATTACHMENT_EMPTY_FILES_NO_CHANGED_OK")

p._step = None
before_att_count = p.attach_list.count()
p._add_attachment()
assert p.attach_list.count() == before_att_count, "_step None -> no-op"
p._step = astep
print("CASE_ADD_ATTACHMENT_NO_STEP_NOOP_OK")

# ---- _del_attachment (455-462) -----------------------------------------------
p.attach_list.setCurrentRow(-1)
p._del_attachment()
assert astep.attachments == ["already/here.txt", "new/one.txt"], "khong chon dong -> no-op"
p.attach_list.setCurrentRow(0)
p._del_attachment()
assert astep.attachments == ["new/one.txt"]
assert p.attach_list.count() == 1
print("CASE_DEL_ATTACHMENT_OK")

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


def test_step_config_panel_hanh_vi_hien_tai(tmp_path):
    sandbox = tmp_path / "home"
    sandbox.mkdir()

    result = _run_isolated(sandbox)

    assert result.returncode == 0, (
        f"characterization script that bai (exit {result.returncode}):\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    for marker in (
        "CASE_INIT_DEFAULT_CTX_NONE_OK",
        "CASE_INIT_CTX_ENABLE_QUIRK_OK",
        "CASE_INIT_PARALLEL_CARD_DEFAULT_VISIBLE_OK",
        "CASE_LOAD_STEP_BASIC_OK",
        "CASE_LOAD_STEP_ROUNDS_CLAMP_QUIRK_OK",
        "CASE_LOAD_STEP_UNKNOWN_PRESET_FALLBACK_OK",
        "CASE_LOAD_STEP_PARALLEL_OK",
        "CASE_LOAD_STEP_EMPTY_OK",
        "CASE_CLEAR_STEP_OK",
        "CASE_ON_EDIT_NO_STEP_NOOP_OK",
        "CASE_ON_EDIT_ROLE_FALLBACK_AND_ORPHAN_SKILL_QUIRK_OK",
        "CASE_ON_EDIT_LOADING_GUARD_OK",
        "CASE_ON_EDIT_ROLE_UPPERCASE_OK",
        "CASE_AVAILABLE_NAMES_NO_CUSTOM_OK",
        "CASE_AVAILABLE_NAMES_ONE_CUSTOM_OK",
        "CASE_AVAILABLE_NAMES_DEDUPE_WITH_BUILTIN_OK",
        "CASE_ADD_SUBAGENT_NO_STEP_NOOP_OK",
        "CASE_ADD_SUBAGENT_PICKED_OK",
        "CASE_ADD_SUBAGENT_EMPTY_NAME_NOOP_OK",
        "CASE_ADD_SUBAGENT_CANCELLED_NOOP_OK",
        "CASE_ADD_SUBAGENT_EMPTY_NAMES_USES_GETTEXT_QUIRK_OK",
        "CASE_EDIT_SUBAGENT_UNKNOWN_CUR_STARTS_AT_0_OK",
        "CASE_EDIT_SUBAGENT_FOREIGN_ITEM_NOOP_OK",
        "CASE_DEL_SUBAGENT_OK",
        "CASE_ADD_ATTACHMENT_DEDUPE_AND_SKIP_EMPTY_OK",
        "CASE_ADD_ATTACHMENT_EMPTY_FILES_NO_CHANGED_OK",
        "CASE_ADD_ATTACHMENT_NO_STEP_NOOP_OK",
        "CASE_DEL_ATTACHMENT_OK",
        "ALL_OK",
    ):
        assert marker in result.stdout, f"thieu marker {marker}\n{result.stdout}"

    # Sandbox chi duoc dung boi save_custom_agent() cua chinh test (khong co
    # du lieu nguoi dung that nao bi cham vao) - CONFIG_DIR nam trong sandbox
    # nhu da assert ngay dau script.
    assert (sandbox / ".cowork_local" / "co4e").exists()
