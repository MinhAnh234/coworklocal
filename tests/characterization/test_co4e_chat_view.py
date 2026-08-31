"""Characterization test cho khu vực CHAT của ``Co4ETab`` (``ui/co4e_tab.py``).

BỌC HAI PHẦN ĐỘC LẬP (đúng phạm vi được giao cho lượt này — KHÔNG động tới gì
khác):

  (A) ``class _ChatInput(QLineEdit)`` (dòng 139-228) + 3 hàm module-level nó
      dùng: ``_skill_names`` (63-67), ``_agent_names`` (70-73),
      ``_directive_token`` (124-136). Đây là ô chat có autocomplete
      ``/skill:``/``/agent:`` (popup gợi ý, phím mũi tên/Tab/Enter/Escape).
  (B) phần DỰNG WIDGET của ``Co4ETab._build_chat`` (dòng 1030-1093) — header
      "Messages" + ``chat_stack`` + composer (ô chat + routing toggle + nút
      gửi). KHÔNG bao gồm ``_toggle_messages`` (1095-1127) — hàm đó vẫn ở lại
      ``Co4ETab`` và không được test ở đây.

VÌ SAO GHI LẠI CHỨ KHÔNG PHÁN XÉT: đây là lưới an toàn cho đợt tách
``ui/co4e_tab.py`` (2000+ dòng) sang ``presentation/co4e/co4e_chat_view.py``.
Đợt này CHƯA tạo file production đó — chỉ chụp ảnh hành vi hiện tại của khu
vực chat để đợt tách sau có bằng chứng "trước/sau giống nhau". Mọi ``assert``
dưới đây được chốt lại từ giá trị THẬT in ra khi chạy code (quy trình ngược:
chạy trước, in kết quả, dán vào assert) — không phải giá trị suy luận trước.

VÌ SAO CHẠY TRONG TIẾN TRÌNH CON CÔ LẬP HOME: giống hệt kỹ thuật của
``tests/characterization/test_co4e_skills_panel.py``/``test_co4e_agent_panel.py``.
``_ChatInput._maybe_popup`` gọi ``_skill_names()``/``_agent_names()``, và
``_skill_names()`` đọc thật từ ``core/skills.py::SKILLS_DIR`` (hằng số module
tính MỘT LẦN lúc import, từ ``CONFIG_DIR = Path.home() / ".cowork_local"``).
Muốn đổi ``Path.home()`` phải đặt ``USERPROFILE``/``HOME`` TRƯỚC bất kỳ
import ``cowork_local.*`` nào, nên toàn bộ phần dựng ``QApplication`` +
``Co4ETab``/``_ChatInput`` chạy trong MỘT tiến trình con sạch (giống
``tools/capture_screens.py::_isolate_home()``), không phải trong tiến trình
pytest chính (nơi ``cowork_local`` rất có thể đã bị import từ trước bởi một
test khác, khiến việc patch ``os.environ`` sau đó vô nghĩa).

KHÔNG gọi AI/QThread thật: cả (A) và (B) không đụng ``Co4ERunManager``/
``AgentWorker``/``ChatView`` thật đi gửi tin — (B) chỉ dựng widget rồi thay
``_chat_send``/``_toggle_messages`` bằng stub đếm lệnh gọi (Co4ETab thật cần
``self.ctx``, ``self._chat_send``, ``self._toggle_messages`` đã tồn tại vì
``_build_chat`` nối ``.clicked``/``.submit`` tới chúng ngay trong hàm — gọi
``Co4ETab._build_chat(fake_self)`` như một hàm KHÔNG bị ràng buộc (unbound),
với ``fake_self`` là một object tối giản chỉ có ``ctx`` + 2 stub đó, để không
phải dựng toàn bộ ``Co4ETab``/canvas/sidebar nặng nề).

QUIRK ĐÃ ĐÓNG ĐINH (xem case tương ứng bên dưới):
  * ``/agent:<name>`` chèn NGUYÊN TÊN agent (có thể chứa dấu cách, ví dụ
    "Business Analyst") vào ô chat, KHÔNG slugify — trong khi ``/skill:<name>``
    chèn ``co4e.slugify(name)`` (không dấu cách). Hai directive cùng cú pháp
    nhưng xử lý tên khác nhau; một khi đã chèn, chuỗi "/agent:Business Analyst "
    có dấu cách nên ``_directive_token`` không còn coi phần sau dấu cách là
    thuộc token đó nữa (regex partial dùng ``[\\w\\-.]*``, không nhận dấu cách).
  * Autocomplete kích hoạt từ khi gõ mới 2 ký tự ("/a" hoặc "/sk"), TRƯỚC khi
    có dấu ``:`` — nhánh fallback trong ``_directive_token`` khớp theo tiền tố
    của ``"/skill"``/``"/agent"`` với ``partial=""``, nên popup hiện TOÀN BỘ
    danh sách skill/agent ngay từ 2 ký tự, không phải danh sách rỗng.
  * Khi popup ĐANG hiện có ít nhất 1 dòng, phím Enter/Return CHỌN dòng đó
    (``_accept``) và KHÔNG emit ``submit`` — ngược với khi popup ẩn, Enter emit
    ``submit`` để gửi tin. Cùng một phím, hai hành vi khác nhau tuỳ trạng thái
    popup.
  * Phím Down/Up trên popup dùng modulo (``(row + step) % n``) nên vòng lặp:
    từ dòng cuối bấm Down quay về dòng đầu, từ dòng đầu bấm Up quay về dòng
    cuối — không dừng ở biên như nhiều danh sách khác.
  * ``_accept()`` khi popup không có dòng nào được chọn (ẩn, rỗng) là no-op
    tuyệt đối — không đổi text, không đổi con trỏ, không ném lỗi.
  * ``_agent_names()`` không loại trùng theo slug mà theo TÊN HIỂN THỊ: một
    custom agent trùng tên với một agent built-in (ví dụ "Business Analyst")
    "thắng" — built-in cùng tên bị lọc khỏi danh sách (custom agents được đưa
    vào trước, built-in chỉ thêm nếu tên chưa có).
  * ``_skill_names()`` bọc try/except quanh toàn bộ ``list_skills() +
    builtin_skills()`` và trả về ``[]`` một cách im lặng khi lỗi — autocomplete
    ``/skill:`` khi đó chỉ đơn giản không hiện popup, không có thông báo lỗi.

VÒNG ĐỜI: đây là giàn giáo cho đợt tách khu vực CHAT (``ui/co4e_tab.py`` dòng
139-228 + phần dựng widget 1030-1093) sang
``presentation/co4e/co4e_chat_view.py``. Sau khi tách xong, các case ở phần
(A) nên viết lại thành test đặc tả cho ``_ChatInput``/hàm module độc lập
(không cần subprocess/QApplication nặng nếu module mới không còn đọc đĩa lúc
import), còn phần (B) nên viết lại thành test đặc tả cho widget composer mới
(input rõ ràng: ctx giả + 2 callback, không cần dựng qua ``Co4ETab`` gốc).
Quirk "agent không slugify nhưng skill có" và quirk "dedup theo tên hiển thị"
đáng mở issue hỏi ý kiến sản phẩm trước khi ai đó "dọn" chúng trong lúc tách —
rất dễ bị coi là bug và "sửa" nhầm trong khi đây là hành vi đang chạy thật.
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

from PySide6.QtWidgets import QApplication, QListWidget
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QKeyEvent

from cowork_local.config import AppConfig, CONFIG_DIR
from cowork_local.state import AppContext
from cowork_local.core import co4e, skills as skills_mod
from cowork_local.core.co4e_builtins import BUILTIN_AGENTS
from cowork_local.ui.co4e_tab import (
    Co4ETab, _ChatInput, _directive_token, _skill_names, _agent_names,
)
from cowork_local.i18n import tr

sandbox = sys.argv[1]
assert str(CONFIG_DIR).startswith(sandbox), "khong co lap: CONFIG_DIR=" + str(CONFIG_DIR)

app = QApplication([])
ctx = AppContext(AppConfig.load())

# =====================================================================
# PHAN A1: _directive_token (124-136) - ham thuan, khong dung Qt/dia
# =====================================================================
cases = [
    ("/skill:", 7, (0, "skill", "")),
    ("/skill:abc", 11, (0, "skill", "abc")),
    ("/agent", 6, (0, "agent", "")),
    ("/agent:", 7, (0, "agent", "")),
    ("/sk", 3, (0, "skill", "")),
    ("/a", 2, (0, "agent", "")),
    ("/", 1, None),
    ("", 0, None),
    ("hello", 5, None),
    ("hello /agent:bob", 17, (6, "agent", "bob")),
    ("hello /agent:bob", 10, (6, "agent", "")),
    ("/skill:ab cd", 9, (0, "skill", "ab")),
    ("/skill:ab cd", 12, None),
    ("//skill", 7, None),
]
for text, pos, expected in cases:
    got = _directive_token(text, pos)
    assert got == expected, (text, pos, got, expected)
print("CASE_DIRECTIVE_TOKEN_OK")

# =====================================================================
# PHAN A2: _skill_names / _agent_names - doc dia thong qua sandbox
# =====================================================================
assert not skills_mod.SKILLS_DIR.exists(), skills_mod.SKILLS_DIR
assert _skill_names() == []
builtin_only = _agent_names()
assert builtin_only == [a.name for a in BUILTIN_AGENTS], builtin_only
assert len(builtin_only) == 19, len(builtin_only)
print("CASE_EMPTY_DISK_NAMES_OK")

# quirk: custom agent TRUNG TEN voi built-in -> built-in bi loc, khong con 2 ban
co4e.AGENTS_DIR.mkdir(parents=True, exist_ok=True)
(co4e.AGENTS_DIR / "a1.json").write_text(
    json.dumps({"id": "a1", "name": "Business Analyst", "role": "AGENT"}),
    encoding="utf-8")
(co4e.AGENTS_DIR / "a2.json").write_text(
    json.dumps({"id": "a2", "name": "My Custom Agent", "role": "AGENT"}),
    encoding="utf-8")
mixed = _agent_names()
assert mixed[:2] == ["Business Analyst", "My Custom Agent"], mixed[:2]
assert mixed.count("Business Analyst") == 1, mixed
assert len(mixed) == 20, len(mixed)  # 19 built-in - 1 trung ten + 2 custom
print("CASE_AGENT_NAME_DEDUP_QUIRK_OK")

skills_mod.SKILLS_DIR.mkdir(parents=True, exist_ok=True)
(skills_mod.SKILLS_DIR / "s1.json").write_text(json.dumps({
    "name": "Viet Test", "description": "d", "instructions": "content", "enabled": True,
}), encoding="utf-8")
assert _skill_names() == ["Viet Test"], _skill_names()
print("CASE_SKILL_NAMES_AFTER_CREATE_OK")

# =====================================================================
# PHAN A3: _ChatInput - popup autocomplete + phim tat
# =====================================================================
ci = _ChatInput()
assert hasattr(ci, "submit")
assert ci._popup.focusPolicy() == Qt.NoFocus
assert ci._popup.windowFlags() == (
    Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    | Qt.NoDropShadowWindowHint)
print("CASE_CHATINPUT_CTOR_OK")

# go "/skill:vi" -> 1 dong goi y, replacement da slugify + khoang trang cuoi
ci.setText("/skill:vi")
ci.setCursorPosition(len("/skill:vi"))
ci._maybe_popup()
assert ci._popup.count() == 1, ci._popup.count()
row0 = ci._popup.item(0)
assert row0.text() == "Viet Test", row0.text()
assert row0.data(Qt.UserRole) == "/skill:viet-test ", row0.data(Qt.UserRole)
assert row0.toolTip() == "Viet Test", row0.toolTip()
assert ci._popup.isVisible() is True
# quirk: chieu rong popup = max(280, chieu rong o chat) - khong co gia tri co dinh
assert ci._popup.width() == max(280, ci.width()), (ci._popup.width(), ci.width())
assert ci._popup.height() == 8 + 1 * 22, ci._popup.height()  # 1 dong -> 30px
print("CASE_SKILL_POPUP_SLUGIFIED_OK")

# quirk: /agent:<ten> CHEN NGUYEN TEN (co dau cach), KHONG slugify
ci.setText("/agent:business")
ci.setCursorPosition(len("/agent:business"))
ci._maybe_popup()
assert ci._popup.count() == 1, ci._popup.count()
row_a = ci._popup.item(0)
assert row_a.text() == "Business Analyst", row_a.text()
assert row_a.data(Qt.UserRole) == "/agent:Business Analyst ", row_a.data(Qt.UserRole)
print("CASE_AGENT_POPUP_NOT_SLUGIFIED_QUIRK_OK")

# quirk: goi "/a" (2 ky tu, chua co dau :) da kich hoat popup agent VOI partial rong
# -> hien TOAN BO danh sach agent, khong phai danh sach rong
ci.setText("/a")
ci.setCursorPosition(2)
ci._maybe_popup()
assert ci._popup.count() == len(_agent_names()), (ci._popup.count(), len(_agent_names()))
print("CASE_TWO_CHAR_PREFIX_TRIGGERS_FULL_LIST_QUIRK_OK")

# khong khop skill nao -> popup an, count 0
ci.setText("/skill:khongtontai")
ci.setCursorPosition(len("/skill:khongtontai"))
ci._maybe_popup()
assert ci._popup.isVisible() is False, ci._popup.isVisible()
assert ci._popup.count() == 0, ci._popup.count()
print("CASE_NO_MATCH_HIDES_POPUP_OK")

# khong phai directive -> an popup (du popup dang duoc show truoc do)
ci._popup.show()
ci.setText("hello")
ci.setCursorPosition(5)
ci._maybe_popup()
assert ci._popup.isVisible() is False
print("CASE_NON_DIRECTIVE_HIDES_POPUP_OK")

# _accept() thay the token bang replacement + dat lai con tro
ci.setText("/skill:vi")
ci.setCursorPosition(len("/skill:vi"))
ci._maybe_popup()
ci._accept()
assert ci.text() == "/skill:viet-test ", ci.text()
assert ci.cursorPosition() == len("/skill:viet-test "), ci.cursorPosition()
assert ci._popup.isVisible() is False
print("CASE_ACCEPT_REPLACES_TOKEN_OK")

# quirk: _accept() khi khong co dong nao duoc chon -> no-op tuyet doi
ci._popup.clear()
ci._popup.hide()
ci.setText("hello world")
ci.setCursorPosition(5)
ci._accept()
assert ci.text() == "hello world", ci.text()
assert ci.cursorPosition() == 5, ci.cursorPosition()
print("CASE_ACCEPT_NOOP_WHEN_NO_ITEM_QUIRK_OK")

# Enter voi popup AN -> emit submit (gui tin)
submitted = []
ci.submit.connect(lambda: submitted.append(1))
ci._popup.hide()
ci.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier))
assert submitted == [1], submitted
print("CASE_ENTER_SUBMITS_WHEN_POPUP_HIDDEN_OK")

# quirk: Enter voi popup DANG HIEN (co dong) -> accept, KHONG submit
ci.setText("/skill:vi")
ci.setCursorPosition(len("/skill:vi"))
ci._maybe_popup()
assert ci._popup.isVisible() is True and ci._popup.count() == 1
submitted.clear()
ci.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier))
assert ci.text() == "/skill:viet-test ", ci.text()
assert submitted == [], submitted
print("CASE_ENTER_ACCEPTS_INSTEAD_OF_SUBMIT_WHEN_POPUP_VISIBLE_QUIRK_OK")

# quirk: Down/Up dung modulo -> vong lap qua bien
(skills_mod.SKILLS_DIR / "s2.json").write_text(json.dumps({
    "name": "Second Skill", "description": "", "instructions": "x", "enabled": True,
}), encoding="utf-8")
ci.setText("/skill:")
ci.setCursorPosition(len("/skill:"))
ci._maybe_popup()
assert ci._popup.count() == 2, ci._popup.count()
assert ci._popup.currentRow() == 0
ci.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Down, Qt.NoModifier))
assert ci._popup.currentRow() == 1
ci.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Down, Qt.NoModifier))
assert ci._popup.currentRow() == 0, ci._popup.currentRow()  # vong lai dau
ci.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Up, Qt.NoModifier))
assert ci._popup.currentRow() == 1, ci._popup.currentRow()  # vong ve cuoi
print("CASE_UP_DOWN_WRAP_AROUND_QUIRK_OK")

# Escape an popup
ci.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))
assert ci._popup.isVisible() is False
print("CASE_ESCAPE_HIDES_POPUP_OK")

# Tab cung accept (giong Enter khi popup hien)
ci.setText("/skill:vi")
ci.setCursorPosition(len("/skill:vi"))
ci._maybe_popup()
ci.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Tab, Qt.NoModifier))
assert ci.text() == "/skill:viet-test ", ci.text()
print("CASE_TAB_ACCEPTS_OK")

# =====================================================================
# PHAN B: Co4ETab._build_chat (1030-1093) - CHI phan dung widget,
# KHONG bao gom _toggle_messages (o lai Co4ETab, khong test o day)
# =====================================================================
calls = []


class _FakeCo4ETab:
    ctx = ctx

    def _toggle_messages(self):
        calls.append("toggle")

    def _chat_send(self):
        calls.append("send")


fake = _FakeCo4ETab()
w = Co4ETab._build_chat(fake)  # goi nhu ham khong rang buoc, khong dung Co4ETab thuc

# DA CAP NHAT sau khi tach "Chat View" (xem
# presentation/co4e/co4e_chat_view.py): _build_chat gio tra ve mot ChatPanel
# (subclass QWidget dung trong presentation/co4e/co4e_chat_view.py) thay vi
# mot QWidget tran - van la mot QWidget that su (layout/cac widget con van
# nguyen), chi ten class cu the doi (cung khuon mau da dung cho
# RunsPagePanel, xem test_co4e_runs_page.py::test_runs_table_is_parented_into_the_returned_widget).
assert type(w).__name__ == "ChatPanel"
assert w is fake._chat_widget
assert w.layout().contentsMargins().left() == 0
assert w.layout().spacing() == 0
assert w.layout().count() == 3, w.layout().count()
child_types = [w.layout().itemAt(i).widget().objectName() or type(w.layout().itemAt(i).widget()).__name__
               for i in range(w.layout().count())]
assert child_types == ["msgHeader", "QStackedWidget", "QWidget"], child_types
print("CASE_BUILD_CHAT_TOP_LAYOUT_OK")

# ---- header "Messages" ----
assert fake._mhdr.objectName() == "msgHeader"
mh = fake._mhdr.layout()
assert mh.count() == 4, mh.count()
assert mh.itemAt(0).widget() is fake.msgs_icon
assert mh.itemAt(1).widget() is fake.msgs_title
assert mh.itemAt(2).widget() is None  # addStretch(1) - khong phai widget
assert mh.itemAt(3).widget() is fake.chat_toggle_btn
assert mh.contentsMargins().left() == 6 and mh.contentsMargins().top() == 3
assert mh.spacing() == 6
assert fake.msgs_title.text() == tr("co4e.messages"), fake.msgs_title.text()
assert fake.msgs_title.objectName() == "hint"
assert fake.msgs_icon.pixmap().width() == 14 and fake.msgs_icon.pixmap().height() == 14
assert fake.chat_toggle_btn.objectName() == "msgToggle"
assert fake.chat_toggle_btn.isFlat() is True
assert fake.chat_toggle_btn.width() == 22 and fake.chat_toggle_btn.height() == 22
assert fake.chat_toggle_btn.toolTip() == tr("co4e.tt_expand_msgs"), fake.chat_toggle_btn.toolTip()
print("CASE_BUILD_CHAT_HEADER_OK")

# ---- chat_stack + flow_logs ----
assert fake.chat_stack.count() == 0
assert fake._flow_logs == {}
assert fake.chat_stack.isHidden() is True   # mac dinh COLLAPSED
print("CASE_BUILD_CHAT_STACK_OK")

# ---- composer (chat_input_row) ----
crow = fake.chat_input_row.layout()
assert crow.count() == 2, crow.count()
assert crow.itemAt(0).widget() is fake._usage_total_lbl
assert crow.contentsMargins().top() == 4 and crow.spacing() == 3
assert fake._usage_total_lbl.text() == ""
assert fake._usage_total_lbl.objectName() == "hint"
inp_widget = crow.itemAt(1).widget()
row = inp_widget.layout()
assert row.contentsMargins().left() == 0
assert row.count() == 3, row.count()
assert row.itemAt(0).widget() is fake.chat_input
assert row.stretch(0) == 1
assert row.itemAt(1).widget() is fake.co4e_routing_toggle
assert row.stretch(1) == 0
assert row.itemAt(2).widget() is fake.chat_send_btn
assert type(fake.chat_input).__name__ == "_ChatInput"
assert fake.chat_input.placeholderText() == tr("co4e.chat_placeholder"), fake.chat_input.placeholderText()
assert fake.chat_send_btn.text() == tr("co4e.send"), fake.chat_send_btn.text()
assert type(fake.co4e_routing_toggle).__name__ == "RoutingToggle"
assert fake.co4e_routing_toggle.surface == "co4e"
assert fake._co4e_routed_provider is None
assert fake.chat_input_row.isHidden() is True   # mac dinh COLLAPSED
print("CASE_BUILD_CHAT_COMPOSER_OK")

# ---- 1073/1075: submit/click cua composer noi thang toi _chat_send ----
fake.chat_send_btn.click()
assert calls == ["send"], calls
calls.clear()
fake.chat_input.submit.emit()
assert calls == ["send"], calls
calls.clear()
print("CASE_COMPOSER_WIRES_TO_CHAT_SEND_OK")

# ---- 1047: chat_toggle_btn.clicked noi thang toi _toggle_messages ----
fake.chat_toggle_btn.click()
assert calls == ["toggle"], calls
calls.clear()
print("CASE_TOGGLE_BTN_WIRES_TO_TOGGLE_MESSAGES_OK")

# ---- trang thai mac dinh COLLAPSED sau khi _build_chat tra ve ----
assert fake._vsplit_sizes == [540, 220], fake._vsplit_sizes
assert fake._msgs_collapsed is True
assert w.maximumHeight() == fake._mhdr.sizeHint().height() + 6, (
    w.maximumHeight(), fake._mhdr.sizeHint().height())
print("CASE_BUILD_CHAT_DEFAULT_COLLAPSED_STATE_OK")

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


def test_co4e_chat_view_hanh_vi_hien_tai(tmp_path):
    sandbox = tmp_path / "home"
    sandbox.mkdir()

    result = _run_isolated(sandbox)

    assert result.returncode == 0, (
        f"characterization script that bai (exit {result.returncode}):\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    for marker in (
        "CASE_DIRECTIVE_TOKEN_OK",
        "CASE_EMPTY_DISK_NAMES_OK",
        "CASE_AGENT_NAME_DEDUP_QUIRK_OK",
        "CASE_SKILL_NAMES_AFTER_CREATE_OK",
        "CASE_CHATINPUT_CTOR_OK",
        "CASE_SKILL_POPUP_SLUGIFIED_OK",
        "CASE_AGENT_POPUP_NOT_SLUGIFIED_QUIRK_OK",
        "CASE_TWO_CHAR_PREFIX_TRIGGERS_FULL_LIST_QUIRK_OK",
        "CASE_NO_MATCH_HIDES_POPUP_OK",
        "CASE_NON_DIRECTIVE_HIDES_POPUP_OK",
        "CASE_ACCEPT_REPLACES_TOKEN_OK",
        "CASE_ACCEPT_NOOP_WHEN_NO_ITEM_QUIRK_OK",
        "CASE_ENTER_SUBMITS_WHEN_POPUP_HIDDEN_OK",
        "CASE_ENTER_ACCEPTS_INSTEAD_OF_SUBMIT_WHEN_POPUP_VISIBLE_QUIRK_OK",
        "CASE_UP_DOWN_WRAP_AROUND_QUIRK_OK",
        "CASE_ESCAPE_HIDES_POPUP_OK",
        "CASE_TAB_ACCEPTS_OK",
        "CASE_BUILD_CHAT_TOP_LAYOUT_OK",
        "CASE_BUILD_CHAT_HEADER_OK",
        "CASE_BUILD_CHAT_STACK_OK",
        "CASE_BUILD_CHAT_COMPOSER_OK",
        "CASE_COMPOSER_WIRES_TO_CHAT_SEND_OK",
        "CASE_TOGGLE_BTN_WIRES_TO_TOGGLE_MESSAGES_OK",
        "CASE_BUILD_CHAT_DEFAULT_COLLAPSED_STATE_OK",
        "ALL_OK",
    ):
        assert marker in result.stdout, f"thieu marker {marker}\n{result.stdout}"

    # Sandbox chi duoc dung boi cac file skill/agent test tu tao xuong
    # SKILLS_DIR/AGENTS_DIR (khong co du lieu nguoi dung that nao bi cham vao) -
    # CONFIG_DIR nam trong sandbox nhu da assert ngay dau script.
    assert (sandbox / ".cowork_local").exists()
