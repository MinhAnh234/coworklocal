"""Characterization test cho khu vực SKILLS trong sidebar của ``Co4ETab``
(``ui/co4e_tab.py``): ``sk_manage_btn``/``skill_list``/``_manage_skills`` (nối
click) và phần "populate skill_list" bên trong ``_reload_sidebar`` — đúng các
đoạn được giao: dòng 569-580 (dựng widget qua ``SkillsListPanel`` + nối
signal), 602 (vòng lặp ``setMinimumHeight(56)`` dùng CHUNG cho
``wf_list``/``agent_list``/``skill_list``/``runs_side_list``), 690-723
(``_reload_sidebar``, CHỈ đoạn skill) và 1370-1374 (``_manage_skills``).

VÌ SAO GHI LẠI CHỨ KHÔNG PHÁN XÉT: đây là lưới an toàn cho đợt tách
``ui/co4e_tab.py`` (2000+ dòng) thành các module con dưới ``presentation/co4e/``
(xem ``docs/architecture/co4e-split-map.md`` — khu vực SKILLS đã dời phần
DỰNG WIDGET sang ``presentation/co4e/skills_list_panel.py::SkillsListPanel``,
còn phần NỐI SIGNAL + populate vẫn ở ``Co4ETab``). Mọi ``assert`` dưới đây
được chốt lại từ giá trị THẬT in ra khi chạy code (quy trình ngược: chạy
trước, in ra, dán vào assert) — không phải giá trị tôi nghĩ nó "nên" là gì.

VÌ SAO CHẠY TRONG TIẾN TRÌNH CON CÔ LẬP HOME: giống hệt kỹ thuật của
``tests/test_build_co4e_tab.py`` (đọc docstring đầu file đó để thấy khuôn gốc)
và ``tests/characterization/test_co4e_agent_panel.py`` — dựng ``Co4ETab`` thật
kéo theo ``AppConfig``/``CONFIG_DIR`` (config.py) và ``SKILLS_DIR``
(core/skills.py) đều là hằng số module tính MỘT LẦN lúc import từ
``Path.home()``. Monkeypatch thuộc tính module SAU khi import không đủ (còn
``AppConfig.load()`` có tham số mặc định đóng băng lúc định nghĩa hàm — xem
``test_build_co4e_tab.py``), nên phải cô lập ``HOME``/``USERPROFILE`` TRƯỚC
bất kỳ import ``cowork_local.*`` nào, trong một tiến trình con sạch hoàn toàn.

AN TOÀN DỮ LIỆU: script con assert ``str(CONFIG_DIR).startswith(sandbox)``
NGAY sau khi import, trước khi ghi bất kỳ file skill nào xuống
``skills_mod.SKILLS_DIR`` (``CONFIG_DIR / "skills"``) — chạy nhầm trên máy
thật sẽ ghi/xoá skill thật của người dùng.

KHÔNG gọi provider AI thật / spawn thread thật: test này không đụng tới
``Co4ERunManager``/``AgentWorker``. ``SkillsDialog.exec()`` (modal, sẽ treo
tiến trình headless) được monkeypatch thành một lớp giả NGAY TRONG tiến trình
con của test — không sửa code sản phẩm; lớp giả chỉ đếm số lần được gọi và trả
về một giá trị falsy (giống bấm Cancel) để lộ ra quirk "luôn reload" bên dưới.

QUIRK ĐÃ ĐÓNG ĐINH (xem case tương ứng bên dưới):
  * ``skill_list`` không lọc theo ``Skill.enabled`` — ``_skill_names()`` gọi
    ``list_skills() + builtin_skills()`` không quan tâm cờ ``enabled``, nên
    một skill được TẠO nhưng chưa được người dùng tick bật (``enabled=False``)
    vẫn xuất hiện trong danh sách kéo-thả của Co4E y hệt một skill đã bật.
    Cờ ``enabled`` chỉ ảnh hưởng nơi khác (``active_skills_text`` cho chat),
    không ảnh hưởng palette này.
  * Payload kéo-thả của một skill KHÔNG chứa ``instructions`` thô của skill,
    mà chứa nguyên khối trả về bởi ``skills_mod.skill_prefix_for(name)`` —
    tức đã có tiền tố ``"## Skill: <tên>\\n"`` dán trước nội dung. Ai "dọn"
    chỗ này để dùng thẳng ``skill.instructions`` sẽ làm mọi flow kéo-thả sẵn
    mất dòng tiêu đề đó.
  * Khi skill có ``instructions`` rỗng, ``skill_prefix_for`` trả về chuỗi rỗng
    (không phải ``None``, không ném lỗi) — payload kéo-thả của skill đó có
    ``instructions == ""`` dù skill vẫn hiện trong danh sách với đúng tên.
  * ``_manage_skills`` LUÔN gọi ``self._reload_sidebar()`` sau
    ``SkillsDialog(...).exec()``, bất kể dialog trả về gì (khác với
    ``_new_agent``/``_edit_agent`` ở khu vực AGENTS, nơi chỉ reload khi
    ``dlg.exec()`` truthy) — đóng Skills manager bằng Cancel/Esc vẫn khiến
    ``skill_list`` bị dựng lại từ đĩa.
  * Thư mục skills không tồn tại (chưa từng tạo skill nào) không ném lỗi:
    ``_skill_names()`` có ``try/except`` bọc quanh, trả về ``[]`` một cách im
    lặng — ``skill_list`` rỗng, không có thông báo lỗi nào cho người dùng.

VÒNG ĐỜI: đây là giàn giáo cho đợt tách phần NỐI SIGNAL + populate của khu vực
Skills sang ``presentation/co4e/`` (dựng widget đã tách xong thành
``SkillsListPanel`` — xem cột "Trạng thái" dòng liên quan trong
``docs/architecture/co4e-split-map.md``). Sau khi phần còn lại được tách (ví
dụ một ``SkillsListController`` biết ``_manage_skills``/populate mà không cần
biết toàn bộ ``Co4ETab``), các case ở đây nên viết lại thành test đặc tả cho
controller mới (input rõ ràng, không cần dựng cả ``Co4ETab``/``QApplication``
nặng nề qua subprocess). Quirk "payload dùng khối có tiền tố thay vì
instructions thô" và quirk "luôn reload dù Cancel" đáng mở issue hỏi ý kiến
sản phẩm trước khi ai đó "dọn" chúng trong lúc tách.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REPO_PARENT = REPO_ROOT.parent

_SCRIPT = r"""
import json
import sys
sys.path.insert(0, REPO_PARENT_PLACEHOLDER)

from PySide6.QtWidgets import QAbstractItemView, QApplication
from PySide6.QtCore import Qt

from cowork_local.config import AppConfig, CONFIG_DIR
from cowork_local.state import AppContext
from cowork_local.core import skills as skills_mod
from cowork_local.ui.co4e_tab import Co4ETab, _PaletteList, _skill_names
from cowork_local.ui.icons import icon as _icon
from cowork_local.i18n import tr

sandbox = sys.argv[1]
assert str(CONFIG_DIR).startswith(sandbox), "khong co lap: CONFIG_DIR=" + str(CONFIG_DIR)

app = QApplication([])
ctx = AppContext(AppConfig.load())
tab = Co4ETab(ctx)

# ---- 569-580: widget cua khu vuc SKILLS duoc dung qua SkillsListPanel ------
assert tab.sk_manage_btn.text() == tr("co4e.manage_skills"), tab.sk_manage_btn.text()
assert tab.sk_manage_btn.toolTip() == tr("co4e.tt_manage_skills"), tab.sk_manage_btn.toolTip()
assert tab.sk_manage_btn.objectName() == "co4eSectionAction"
assert tab.sk_manage_btn.isFlat() is True
assert tab.sk_manage_btn.cursor().shape() == Qt.PointingHandCursor
assert isinstance(tab.skill_list, _PaletteList), type(tab.skill_list)
assert tab.skill_list.dragEnabled() is True
assert tab.skill_list.dragDropMode() == QAbstractItemView.DragOnly
print("CASE_WIDGETS_OK")

# ---- 602: bon danh sach dung CHUNG mot vong lap setMinimumHeight(56) -------
heights = {
    "wf_list": tab.wf_list.minimumHeight(),
    "agent_list": tab.agent_list.minimumHeight(),
    "skill_list": tab.skill_list.minimumHeight(),
    "runs_side_list": tab.runs_side_list.minimumHeight(),
}
assert heights == {
    "wf_list": 56, "agent_list": 56, "skill_list": 56, "runs_side_list": 56,
}, heights
print("CASE_MIN_HEIGHT_SHARED_OK")

# ---- quirk: chua tao skill nao -> thu muc SKILLS_DIR khong ton tai ---------
# _skill_names() boc try/except quanh list_skills()/builtin_skills(); thu muc
# chua ton tai (Co4ETab.__init__ khong tu tao no) khong nem loi, tra ve rong.
assert not skills_mod.SKILLS_DIR.exists(), skills_mod.SKILLS_DIR
assert _skill_names() == []
tab._reload_sidebar()
assert tab.skill_list.count() == 0, tab.skill_list.count()
print("CASE_EMPTY_DIR_OK")

# ---- 690-723 (doan skill): mot skill co instructions, da bat enabled -------
skills_mod.SKILLS_DIR.mkdir(parents=True, exist_ok=True)
(skills_mod.SKILLS_DIR / "s1.json").write_text(json.dumps({
    "name": "Viet test",
    "description": "desc 1",
    "instructions": "Luon viet test",
    "enabled": True,
}), encoding="utf-8")
tab._reload_sidebar()
assert tab.skill_list.count() == 1, tab.skill_list.count()
it0 = tab.skill_list.item(0)
assert it0.text() == "Viet test", it0.text()
assert it0.icon().isNull() is False
# Dong lo hong da bi mutation test bat duoc (xem docs/architecture/
# co4e-refactor-run-report.md muc 4, luot 3): doi icon_name truyen vao
# _palette_item(name, "sparkle", payload) tu "sparkle" sang "robot" o
# ui/co4e_tab.py (dong _reload_sidebar, khu vuc SKILLS) truoc day KHONG bi bat,
# vi assert cu chi kiem "co icon" (isNull() is False) ma khong kiem la icon NAO.
# So sanh pixmap that (icon() la ham thuan, cung name/size/color -> cung anh)
# thay vi so QIcon truc tiep (QIcon khong dinh nghia __eq__ theo noi dung).
assert it0.icon().pixmap(16, 16).toImage() == _icon("sparkle").pixmap(16, 16).toImage(), (
    "icon cua skill trong palette phai dung 'sparkle' (_palette_item(name, 'sparkle', payload))"
)
payload0 = it0.data(Qt.UserRole)
assert payload0 == {
    "variant": "step", "label": "Viet test", "agent_slug": "viet-test",
    "role": "SKILL", "icon": "sparkle",
    "instructions": "## Skill: Viet test\nLuon viet test",
    "context": "", "model": "", "self_verify": True, "max_verify_rounds": 1,
    "permission_preset": "full", "skills": ["Viet test"], "attachments": [],
    "sub_agents": [],
}, payload0
assert it0.data(Qt.UserRole + 1) is None
print("CASE_ONE_SKILL_OK")

# ---- quirk: skill CHUA duoc bat (enabled=False) van hien trong palette -----
# list_skills()/builtin_skills() khong loc theo enabled - _skill_names() lay
# ca hai, nen mot skill "tat" van keo-tha duoc tu Co4E y het skill "bat".
(skills_mod.SKILLS_DIR / "s2-disabled.json").write_text(json.dumps({
    "name": "Chua bat",
    "description": "",
    "instructions": "Noi dung chua bat",
    "enabled": False,
}), encoding="utf-8")
tab._reload_sidebar()
assert tab.skill_list.count() == 2, tab.skill_list.count()
names = [tab.skill_list.item(i).text() for i in range(tab.skill_list.count())]
assert names == ["Viet test", "Chua bat"], names
it1 = tab.skill_list.item(1)
payload1 = it1.data(Qt.UserRole)
assert payload1["instructions"] == "## Skill: Chua bat\nNoi dung chua bat", payload1
print("CASE_DISABLED_SKILL_STILL_SHOWN_QUIRK_OK")

# ---- quirk: skill co instructions RONG -> payload instructions == "" ------
# skill_prefix_for() tra ve "" khi instructions rong (khong None, khong loi);
# skill van hien dung ten trong danh sach.
(skills_mod.SKILLS_DIR / "s3-empty-instr.json").write_text(json.dumps({
    "name": "Rong noi dung",
    "description": "",
    "instructions": "",
    "enabled": True,
}), encoding="utf-8")
tab._reload_sidebar()
assert tab.skill_list.count() == 3, tab.skill_list.count()
it2 = tab.skill_list.item(2)
assert it2.text() == "Rong noi dung", it2.text()
payload2 = it2.data(Qt.UserRole)
assert payload2["instructions"] == "", payload2
assert payload2["skills"] == ["Rong noi dung"], payload2
print("CASE_EMPTY_INSTRUCTIONS_QUIRK_OK")

# ---- xoa het skill roi reload lai -> khong con dong nao (khong con sot) ----
for p in skills_mod.SKILLS_DIR.glob("*.json"):
    p.unlink()
tab._reload_sidebar()
assert tab.skill_list.count() == 0, tab.skill_list.count()
print("CASE_CLEAR_ON_RELOAD_OK")

# ---- 1370-1374: _manage_skills() mo SkillsDialog(self, self.ctx) -----------
import cowork_local.ui.skills_dialog as skills_dialog_mod

dialog_calls = []


class _FakeSkillsDialog:
    def __init__(self, parent, ctx_arg):
        dialog_calls.append((parent is tab, ctx_arg is ctx))

    def exec(self):
        return 0  # falsy, gia lap bam Cancel/Esc


orig_dialog_cls = skills_dialog_mod.SkillsDialog
skills_dialog_mod.SkillsDialog = _FakeSkillsDialog

reload_calls = {"n": 0}
orig_reload = tab._reload_sidebar


def _counting_reload():
    reload_calls["n"] += 1
    return orig_reload()


tab._reload_sidebar = _counting_reload
tab._manage_skills()
skills_dialog_mod.SkillsDialog = orig_dialog_cls
tab._reload_sidebar = orig_reload

assert dialog_calls == [(True, True)], dialog_calls
# quirk: dialog tra ve gia tri falsy (Cancel) nhung sidebar VAN duoc reload.
assert reload_calls["n"] == 1, reload_calls
print("CASE_MANAGE_SKILLS_ALWAYS_RELOADS_QUIRK_OK")

# ---- 573: sk_manage_btn.clicked noi thang toi _manage_skills ---------------
recorded = []
tab._manage_skills = lambda: recorded.append(1)
tab.sk_manage_btn.click()
assert recorded == [1], recorded
print("CASE_CLICK_WIRES_TO_MANAGE_SKILLS_OK")

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


def test_co4e_skills_panel_hanh_vi_hien_tai(tmp_path):
    sandbox = tmp_path / "home"
    sandbox.mkdir()

    result = _run_isolated(sandbox)

    assert result.returncode == 0, (
        f"characterization script that bai (exit {result.returncode}):\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    for marker in (
        "CASE_WIDGETS_OK",
        "CASE_MIN_HEIGHT_SHARED_OK",
        "CASE_EMPTY_DIR_OK",
        "CASE_ONE_SKILL_OK",
        "CASE_DISABLED_SKILL_STILL_SHOWN_QUIRK_OK",
        "CASE_EMPTY_INSTRUCTIONS_QUIRK_OK",
        "CASE_CLEAR_ON_RELOAD_OK",
        "CASE_MANAGE_SKILLS_ALWAYS_RELOADS_QUIRK_OK",
        "CASE_CLICK_WIRES_TO_MANAGE_SKILLS_OK",
        "ALL_OK",
    ):
        assert marker in result.stdout, f"thieu marker {marker}\n{result.stdout}"

    # Sandbox chi duoc dung boi cac file skill test tu tao xuong SKILLS_DIR
    # (khong co du lieu nguoi dung that nao bi cham vao) - CONFIG_DIR nam
    # trong sandbox nhu da assert ngay dau script.
    assert (sandbox / ".cowork_local").exists()
