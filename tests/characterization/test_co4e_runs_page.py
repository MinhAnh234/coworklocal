"""Characterization test cho phần DỰNG WIDGET của trang "Runs" trong Co4E
(``ui/co4e_tab.py``, method ``_build_runs_page``, dòng 869-928).

VÒNG ĐỜI: đây là giàn giáo (scaffolding), KHÔNG phải đặc tả cuối cùng. Mục
đích DUY NHẤT là lưới an toàn cho đợt tách "Run Control" sắp tới (xem
``docs/architecture/co4e-split-map-run-control.md`` — dự kiến ``_build_runs_page``
sẽ dời sang ``presentation/co4e/co4e_run_control_widget.py``). Sau khi việc
tách hoàn tất và ổn định, các test ở đây nên được viết lại thành test đặc tả
(specification test) cho widget/API mới; quirk nào liệt kê dưới đây nên có
issue riêng nếu ai đó muốn "dọn" chúng — ĐỪNG tự sửa code sản phẩm để "dọn"
quirk khi đọc thấy test này.

PHẠM VI: CHỈ ``_build_runs_page`` — phần dựng ``QWidget``/``runs_table`` (5
cột) + 7 widget con (``runs_back_btn``, ``runs_title``, ``ws_folder_btn``,
``run_stop_btn``, ``run_rename_btn``, ``run_del_btn``, ``run_clear_btn``) và
việc NỐI (connect) các signal của chúng tới các method xử lý. CÁC METHOD XỬ LÝ
(``_refresh_runs``, ``_stop_selected_run``, ``_delete_selected_run``,
``_runs_context_menu``, ``_rename_selected_run``, ``_open_run_from_table``,
``_open_workspace_folder``, ``_refresh_ws_folder_btn``) VẪN Ở NGUYÊN trên
``Co4ETab`` và KHÔNG được characterize ở đây (đề bài giao đúng phạm vi
constructor cho lượt này) — test này chỉ xác nhận rằng bấm nút/emit signal
tương ứng CÓ gọi tới đúng method trên ``self`` (qua fake/stub), không xác
nhận method đó làm gì bên trong.

CÁCH DỰNG: ``_build_runs_page`` là instance method cần rất nhiều state của
``Co4ETab`` thật (``self.ctx``, ``self.manager``, hàng chục method khác) để
dựng trọn vẹn — dựng cả ``Co4ETab`` chỉ để test 60 dòng constructor này là
tốn kém và kéo theo rủi ro chạm những phần KHÔNG thuộc phạm vi. Nên ở đây
gọi thẳng ``Co4ETab._build_runs_page(fake_self)`` (unbound, theo đúng gợi ý
của đề bài) trên một ``_FakeTab`` tối giản: chỉ có ``ctx``/``_project_dir``/
``manager`` (để ``_flow_output_root``/``_refresh_ws_folder_btn`` — hai
method DÙNG THẬT của ``Co4ETab``, được gọi ngay TRONG lúc dựng ở dòng 893 —
chạy được) và các method xử lý còn lại được thay bằng stub ghi lại số lần gọi
(KHÔNG gọi ``Co4ERunManager.start()``/dựng ``QThread``/``AgentWorker`` thật —
đúng ràng buộc "không spawn thread/gọi provider thật").

AN TOÀN DỮ LIỆU: dù bước dựng widget này tự nó KHÔNG chạm đĩa, việc gọi
``_flow_output_root()``/``_refresh_ws_folder_btn()`` NGAY trong lúc dựng lại
tính ``CONFIG_DIR`` (qua ``cowork_local.config.CONFIG_DIR = Path.home() /
".cowork_local"``, xuyên qua ``core.co4e.CO4E_DIR``) — nên toàn bộ probe chạy
trong TIẾN TRÌNH CON riêng (tránh xung đột ``QApplication`` singleton với các
test khác trong cùng lượt chạy pytest) với ``HOME``/``USERPROFILE`` trỏ vào
một ``tmp_path`` sandbox ĐẶT TRƯỚC khi script import bất kỳ thứ gì thuộc
``cowork_local`` (đúng kỹ thuật ``tools/capture_screens.py::_isolate_home()``:
đặt ``USERPROFILE``/``HOME``, xoá ``HOMEDRIVE``/``HOMEPATH``), và
``QT_QPA_PLATFORM=offscreen`` được đặt TRƯỚC khi import PySide6 (đúng khuôn
``tools/check_co4e.py`` dòng 22+40-42). Một assert ngay trong tiến trình con
chốt ``CONFIG_DIR`` nằm trong sandbox trước khi làm gì khác (kiểu
``tools/check_co4e.py:47``).

CẦN QApplication: ``_build_runs_page`` dựng ``QWidget``/``QTableWidget`` thật,
đọc ``.text()``/``.toolTip()``/``.icon()``/``.cursor()`` và bấm nút thật qua
``.click()`` — không phải kiểu giá trị thuần, nên bắt buộc ``QApplication``
(``offscreen``), khác các test hình học thuần (``test_co4e_canvas_geometry.py``).

CÁCH CHỐT ASSERT: mọi giá trị dưới đây lấy bằng cách CHẠY code thật (script
``_PROBE_SCRIPT`` bên dưới, qua ``.venv/Scripts/python.exe``, giống hệt lệnh ở
cuối file) rồi dán NGUYÊN VĂN JSON in được vào assert — không suy luận lý
thuyết. Các chuỗi hiển thị phụ thuộc ``tr()`` (tiếng Việt mặc định) được so
sánh bằng cách gọi LẠI ``tr()`` thật ngay trong tiến trình test (không cần
QApplication, ``i18n.py`` là tra bảng thuần) thay vì chép tay chuỗi có dấu —
tránh gõ nhầm ký tự Unicode khi transcribe.

QUIRK ĐÃ ĐÓNG ĐINH (xem case tương ứng bên dưới — ĐỪNG "dọn" các chỗ này khi
tách, chúng trông như bất đối xứng khó hiểu nhưng là hành vi đang chạy thật
hôm nay):
  * ``run_clear_btn`` là nút DUY NHẤT trong 5 nút hàng thao tác KHÔNG có
    ``setIcon(...)`` — icon của nó luôn rỗng (``.icon().isNull() is True``),
    khác hẳn ``run_stop_btn``/``run_rename_btn``/``run_del_btn``/
    ``ws_folder_btn`` đều có icon SVG built-in.
  * ``run_clear_btn.clicked`` nối THẲNG tới
    ``lambda: self.manager.clear_finished()`` — gọi trực tiếp method trên
    ``manager``, KHÔNG đi qua một method riêng trên ``self`` như 3 nút hàng
    xóm (``_stop_selected_run``/``_rename_selected_run``/
    ``_delete_selected_run``) — không có lớp bọc nào để thêm xác nhận
    (confirm dialog) sau này mà không sửa trực tiếp dòng connect này.
  * ``ws_folder_btn`` text được dựng bằng ``"…/" + "/".join(parts[-2:])``
    (đúng 3 ký tự: dấu chấm lửng Unicode U+2026 rồi dấu gạch chéo xuôi) khi
    đường dẫn có hơn 2 phần — dùng ``"/"`` LUÔN LUÔN, kể cả trên Windows
    (khác separator ``\\`` của phần còn lại của path), và không có fallback
    hiển thị full path trừ khi ``len(parts) <= 2``.
  * ``_flow_output_root()`` (được ``_refresh_ws_folder_btn()`` gọi NGAY
    trong lúc dựng, dòng 893) bọc ``ctx.config.cowork_output_dir()`` trong
    ``except Exception`` RỘNG — bất kỳ lỗi nào từ ``ctx.config`` (kể cả
    ``AttributeError`` vì ``ctx`` không có ``.config`` như trong probe này)
    đều rơi vào nhánh fallback ``co4e.CO4E_DIR / "runs"`` một cách im lặng,
    không log, không báo cho người gọi biết đã fallback.
  * ``runs_table`` sau khi dựng xong LUÔN có 0 hàng bất kể ``manager`` đang
    có run nào hay không — ``_build_runs_page`` không tự seed dữ liệu, việc
    đó thuộc về ``_refresh_runs`` (method riêng, KHÔNG thuộc phạm vi test
    này) — ai tách file mà tưởng constructor này "phải" gọi ``_refresh_runs``
    luôn thì sẽ đổi hành vi so với hôm nay.

Lệnh thủ công đã dùng để chốt các con số trên (quy trình ngược, xem cuối file
để chạy lại nếu cần chốt lại sau khi code đổi có chủ đích).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REPO_PARENT = REPO_ROOT.parent

_PROBE_SCRIPT = r"""
import json
import os
import sys
from pathlib import Path

sandbox = sys.argv[1]
repo_parent = sys.argv[2]
sys.path.insert(0, repo_parent)

os.environ["QT_QPA_PLATFORM"] = "offscreen"
for var in ("USERPROFILE", "HOME"):
    os.environ[var] = sandbox
os.environ.pop("HOMEDRIVE", None)
os.environ.pop("HOMEPATH", None)

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QApplication, QHeaderView, QTableWidget, QTableWidgetItem,
)

app = QApplication([])

from cowork_local.config import CONFIG_DIR
assert str(Path(sandbox).resolve()) in str(CONFIG_DIR.resolve()), (
    "khong co lap: CONFIG_DIR=" + str(CONFIG_DIR))

from cowork_local.ui.co4e_tab import Co4ETab

result = {}
calls = {"show_runs": [], "stop": 0, "rename": 0, "delete": 0, "open_run": 0,
         "ws_open": 0, "ctx_menu": 0}


class _Manager:
    # Stand-in cho Co4ERunManager - KHONG dung QThread/AgentWorker that.

    def __init__(self):
        self.clear_finished_calls = 0

    def clear_finished(self):
        self.clear_finished_calls += 1


class _Config:
    def cowork_output_dir(self):
        # co tinh nem loi de _flow_output_root roi vao nhanh fallback
        # (quirk duoc dong dinh trong docstring cua file test).
        raise RuntimeError("no config in probe")


class _Ctx:
    def __init__(self):
        self.config = _Config()


class _FakeTab:
    # Chi mang du state de goi duoc Co4ETab._build_runs_page(self) unbound -
    # KHONG dung ca Co4ETab that (tranh keo theo sidebar/canvas/config panel
    # ngoai pham vi).

    # Hai method NAY la method THAT cua Co4ETab, duoc _build_runs_page goi
    # NGAY trong luc dung (dong 893) - phai la ban that, khong stub.
    _flow_output_root = Co4ETab._flow_output_root
    _refresh_ws_folder_btn = Co4ETab._refresh_ws_folder_btn
    _build_runs_page = Co4ETab._build_runs_page

    def __init__(self):
        self.ctx = _Ctx()
        self._project_dir = None
        self.manager = _Manager()

    def _show_runs(self, on):
        calls["show_runs"].append(on)

    def _stop_selected_run(self):
        calls["stop"] += 1

    def _rename_selected_run(self):
        calls["rename"] += 1

    def _delete_selected_run(self):
        calls["delete"] += 1

    def _open_run_from_table(self, item):
        calls["open_run"] += 1

    def _open_workspace_folder(self):
        calls["ws_open"] += 1

    def _runs_context_menu(self, pos):
        calls["ctx_menu"] += 1


fake = _FakeTab()
w = fake._build_runs_page()

result["w_type"] = type(w).__name__
result["layout_type"] = type(w.layout()).__name__
result["table_is_child_of_w"] = w.findChild(type(fake.runs_table)) is fake.runs_table

result["col_count"] = fake.runs_table.columnCount()
result["row_count"] = fake.runs_table.rowCount()
result["header_resize_mode_is_stretch"] = (
    fake.runs_table.horizontalHeader().sectionResizeMode(0) == QHeaderView.Stretch
)
result["vheader_visible"] = fake.runs_table.verticalHeader().isVisible()
# isVisible() luon False vi 'w' khong bao gio duoc .show() trong probe nay
# (widget khong nam trong mot top-level dang hien thi that) - dung
# isVisibleTo(ancestor) de bat dung co hidden explicit da duoc setVisible(...)
# dat tren verticalHeader, khong phu thuoc chuoi ancestor co duoc show hay
# khong. Xem PySide6 doc QWidget.isVisibleTo(): tra ve True/False dua tren co
# WA_WState_Hidden explicit cua chinh widget do (va cac ancestor tinh den
# truoc 'ancestor'), bat ke ancestor da .show() hay chua.
result["vheader_visible_to_table"] = (
    fake.runs_table.verticalHeader().isVisibleTo(fake.runs_table)
)
result["edit_triggers_is_no_edit"] = (
    fake.runs_table.editTriggers() == QTableWidget.NoEditTriggers
)
result["selection_behavior_is_select_rows"] = (
    fake.runs_table.selectionBehavior() == QTableWidget.SelectRows
)
result["context_menu_policy_is_custom"] = (
    fake.runs_table.contextMenuPolicy() == Qt.CustomContextMenu
)
result["table_tooltip"] = fake.runs_table.toolTip()

result["back_btn_text"] = fake.runs_back_btn.text()
result["back_btn_tooltip"] = fake.runs_back_btn.toolTip()
result["back_icon_isnull"] = fake.runs_back_btn.icon().isNull()

result["title_text"] = fake.runs_title.text()
result["title_object_name"] = fake.runs_title.objectName()

result["ws_folder_flat"] = fake.ws_folder_btn.isFlat()
result["ws_folder_cursor_is_pointing_hand"] = (
    fake.ws_folder_btn.cursor().shape() == Qt.PointingHandCursor
)
result["ws_folder_text"] = fake.ws_folder_btn.text()
result["ws_folder_tooltip"] = fake.ws_folder_btn.toolTip()
result["ws_folder_icon_isnull"] = fake.ws_folder_btn.icon().isNull()

result["stop_btn_text"] = fake.run_stop_btn.text()
result["stop_btn_object_name"] = fake.run_stop_btn.objectName()
result["stop_btn_tooltip"] = fake.run_stop_btn.toolTip()
result["stop_btn_icon_isnull"] = fake.run_stop_btn.icon().isNull()

result["rename_btn_text"] = fake.run_rename_btn.text()
result["rename_btn_tooltip"] = fake.run_rename_btn.toolTip()
result["rename_btn_icon_isnull"] = fake.run_rename_btn.icon().isNull()

result["del_btn_text"] = fake.run_del_btn.text()
result["del_btn_tooltip"] = fake.run_del_btn.toolTip()
result["del_btn_icon_isnull"] = fake.run_del_btn.icon().isNull()

result["clear_btn_text"] = fake.run_clear_btn.text()
result["clear_btn_tooltip"] = fake.run_clear_btn.toolTip()
result["clear_btn_object_name"] = fake.run_clear_btn.objectName()
result["clear_btn_icon_isnull"] = fake.run_clear_btn.icon().isNull()

# --- bam nut / emit signal that -> xac nhan CO goi dung method tren self ----
fake.runs_back_btn.click()
result["calls_after_back_click"] = list(calls["show_runs"])

fake.ws_folder_btn.click()
result["ws_open_calls_after_click"] = calls["ws_open"]

fake.run_stop_btn.click()
result["stop_calls_after_click"] = calls["stop"]

fake.run_rename_btn.click()
result["rename_calls_after_click"] = calls["rename"]

fake.run_del_btn.click()
result["delete_calls_after_click"] = calls["delete"]

fake.run_clear_btn.click()
result["manager_clear_finished_calls_after_click"] = fake.manager.clear_finished_calls

item = QTableWidgetItem("row0")
fake.runs_table.setRowCount(1)
fake.runs_table.setItem(0, 0, item)
fake.runs_table.itemDoubleClicked.emit(item)
result["open_run_calls_after_dbl_click"] = calls["open_run"]

fake.runs_table.customContextMenuRequested.emit(QPoint(5, 5))
result["ctx_menu_calls_after_signal"] = calls["ctx_menu"]

result["flow_output_root_fallback"] = str(fake._flow_output_root())
result["config_dir"] = str(CONFIG_DIR)

print(json.dumps(result, sort_keys=True, ensure_ascii=True))
print("PROBE_OK")
"""


@pytest.fixture(scope="module")
def probe_result(tmp_path_factory):
    """Chạy ``_PROBE_SCRIPT`` một lần cho cả module trong TIẾN TRÌNH CON, trả
    về dict JSON đã in được cùng ``sandbox`` đã dùng (để test tính lại các giá
    trị phụ thuộc đường dẫn, thay vì chép tay chuỗi tuyệt đối)."""
    sandbox = tmp_path_factory.mktemp("co4e-runs-page-home")

    env = dict(os.environ)
    env["HOME"] = str(sandbox)
    env["USERPROFILE"] = str(sandbox)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env.pop("HOMEDRIVE", None)
    env.pop("HOMEPATH", None)

    result = subprocess.run(
        [sys.executable, "-c", _PROBE_SCRIPT, str(sandbox), str(REPO_PARENT)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"probe co4e runs page that bai (exit {result.returncode}):\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    assert "PROBE_OK" in result.stdout, result.stdout

    json_line = result.stdout.strip().splitlines()[-2]
    data = json.loads(json_line)
    data["_sandbox"] = str(sandbox)
    return data


# ---------------------------------------------------------------------------
# runs_table: cau truc/co so mac dinh
# ---------------------------------------------------------------------------

def test_runs_table_has_5_columns_and_starts_empty(probe_result):
    assert probe_result["col_count"] == 5
    # quirk: _build_runs_page KHONG tu seed hang nao, du manager co run hay
    # khong - seed la viec cua _refresh_runs (ngoai pham vi test nay).
    assert probe_result["row_count"] == 0


def test_runs_table_is_parented_into_the_returned_widget(probe_result):
    # DA CAP NHAT sau khi tach "Run Control" (xem
    # docs/architecture/co4e-split-map-run-control.md): _build_runs_page gio
    # tra ve mot RunsPagePanel (subclass QWidget dung trong presentation/co4e/
    # co4e_run_control_widget.py) thay vi mot QWidget tran - van la mot QWidget
    # that su (layout/table van nguyen), chi ten class cu the doi.
    assert probe_result["w_type"] == "RunsPagePanel"
    assert probe_result["layout_type"] == "QVBoxLayout"
    assert probe_result["table_is_child_of_w"] is True


def test_runs_table_display_settings(probe_result):
    assert probe_result["header_resize_mode_is_stretch"] is True
    # KHONG dung "vheader_visible" (QWidget.isVisible()) o day: gia tri do
    # luon False bat ke setVisible(True/False) trong code san pham, vi
    # runs_table/verticalHeader khong bao gio duoc .show() thuc su trong luc
    # probe (isVisible() phu thuoc CA chuoi ancestor co dang hien tren man
    # hinh hay khong). Dung "vheader_visible_to_table" (isVisibleTo(ancestor))
    # de bat dung co explicit hidden ma setVisible(False) dat len
    # verticalHeader, khong phu thuoc runs_table co duoc show hay khong -
    # mutation setVisible(False) -> True lam gia tri nay lat tu False len True.
    assert probe_result["vheader_visible_to_table"] is False
    assert probe_result["edit_triggers_is_no_edit"] is True
    assert probe_result["selection_behavior_is_select_rows"] is True
    assert probe_result["context_menu_policy_is_custom"] is True


def test_runs_table_tooltip_matches_tr_key(probe_result):
    from cowork_local.i18n import tr
    assert probe_result["table_tooltip"] == tr("co4e.tt_runs_list")


# ---------------------------------------------------------------------------
# runs_back_btn
# ---------------------------------------------------------------------------

def test_back_button_text_tooltip_and_icon(probe_result):
    from cowork_local.i18n import tr
    assert probe_result["back_btn_text"] == tr("co4e.back_to_flow")
    assert probe_result["back_btn_tooltip"] == tr("co4e.tt_back_to_flow")
    assert probe_result["back_icon_isnull"] is False


def test_back_button_click_calls_show_runs_with_false(probe_result):
    # _build_runs_page noi runs_back_btn.clicked -> lambda: self._show_runs(False)
    assert probe_result["calls_after_back_click"] == [False]


# ---------------------------------------------------------------------------
# runs_title
# ---------------------------------------------------------------------------

def test_runs_title_text_and_object_name(probe_result):
    from cowork_local.i18n import tr
    assert probe_result["title_text"] == tr("co4e.running_flows")
    assert probe_result["title_object_name"] == "hint"


# ---------------------------------------------------------------------------
# ws_folder_btn
# ---------------------------------------------------------------------------

def test_ws_folder_button_is_flat_with_pointing_hand_cursor(probe_result):
    assert probe_result["ws_folder_flat"] is True
    assert probe_result["ws_folder_cursor_is_pointing_hand"] is True
    assert probe_result["ws_folder_icon_isnull"] is False


def test_ws_folder_button_text_uses_ellipsis_and_forward_slash_regardless_of_os(
    probe_result,
):
    # quirk: "…/" (dau cham lung That, KHONG phai 3 dau cham thuong) roi
    # noi 2 phan cuoi cua path bang "/" luon luon - kha nang fallback rong day
    # du duoc kich hoat boi ctx.config gia lap khong co .config that.
    assert probe_result["ws_folder_text"] == "…/runs/co4e"


def test_ws_folder_button_tooltip_embeds_the_fallback_root_path(probe_result):
    from cowork_local.i18n import tr
    root = str(Path(probe_result["config_dir"]) / "co4e" / "runs" / "co4e")
    assert probe_result["ws_folder_tooltip"] == tr(
        "co4e.tt_open_workspace", path=root
    )
    assert probe_result["flow_output_root_fallback"] == root


def test_ws_folder_button_click_calls_open_workspace_folder(probe_result):
    assert probe_result["ws_open_calls_after_click"] == 1


def test_config_dir_is_isolated_inside_the_sandbox(probe_result):
    # chot lai rang qua trinh dung widget khong lam chuyen sang HOME that.
    assert probe_result["_sandbox"] in probe_result["config_dir"]


# ---------------------------------------------------------------------------
# run_stop_btn / run_rename_btn / run_del_btn / run_clear_btn
# ---------------------------------------------------------------------------

def test_stop_button_text_object_name_tooltip_icon(probe_result):
    from cowork_local.i18n import tr
    assert probe_result["stop_btn_text"] == tr("co4e.stop")
    assert probe_result["stop_btn_object_name"] == "danger"
    assert probe_result["stop_btn_tooltip"] == tr("co4e.tt_stop_run")
    assert probe_result["stop_btn_icon_isnull"] is False


def test_stop_button_click_calls_stop_selected_run(probe_result):
    assert probe_result["stop_calls_after_click"] == 1


def test_rename_button_text_tooltip_icon(probe_result):
    from cowork_local.i18n import tr
    assert probe_result["rename_btn_text"] == tr("co4e.rename_run")
    assert probe_result["rename_btn_tooltip"] == tr("co4e.tt_rename_run")
    assert probe_result["rename_btn_icon_isnull"] is False


def test_rename_button_click_calls_rename_selected_run(probe_result):
    assert probe_result["rename_calls_after_click"] == 1


def test_delete_button_text_tooltip_icon(probe_result):
    from cowork_local.i18n import tr
    assert probe_result["del_btn_text"] == tr("co4e.delete_run")
    assert probe_result["del_btn_tooltip"] == tr("co4e.tt_delete_run")
    assert probe_result["del_btn_icon_isnull"] is False


def test_delete_button_click_calls_delete_selected_run(probe_result):
    assert probe_result["delete_calls_after_click"] == 1


def test_clear_button_text_tooltip_and_no_object_name(probe_result):
    from cowork_local.i18n import tr
    assert probe_result["clear_btn_text"] == tr("co4e.clear_done")
    assert probe_result["clear_btn_tooltip"] == tr("co4e.tt_clear_runs")
    # quirk: khac 4 nut hang xom, run_clear_btn khong setObjectName.
    assert probe_result["clear_btn_object_name"] == ""


def test_clear_button_has_no_icon_unlike_its_siblings(probe_result):
    # quirk: run_clear_btn la nut DUY NHAT trong hang khong co setIcon(...).
    assert probe_result["clear_btn_icon_isnull"] is True


def test_clear_button_click_calls_manager_clear_finished_directly(probe_result):
    # quirk: noi THANG toi lambda: self.manager.clear_finished() - khong di
    # qua mot method rieng tren self nhu 3 nut hang xom (stop/rename/delete).
    assert probe_result["manager_clear_finished_calls_after_click"] == 1


# ---------------------------------------------------------------------------
# runs_table: double-click / context-menu signals
# ---------------------------------------------------------------------------

def test_double_click_on_a_row_calls_open_run_from_table(probe_result):
    assert probe_result["open_run_calls_after_dbl_click"] == 1


def test_context_menu_request_calls_runs_context_menu(probe_result):
    assert probe_result["ctx_menu_calls_after_signal"] == 1


# ---------------------------------------------------------------------------
# Lenh thu cong da dung de chot cac gia tri JSON o tren (quy trinh nguoc):
#
#   .venv/Scripts/python.exe -c "<noi dung _PROBE_SCRIPT>" <sandbox> <repo_parent>
#
# voi <sandbox> la mot thu muc rong duoc gan vao HOME/USERPROFILE TRUOC khi
# script import bat ky thu gi thuoc cowork_local, va <repo_parent> la thu muc
# cha cua repo (de "import cowork_local" hoat dong dung nhu conftest.py lam).
# ---------------------------------------------------------------------------
