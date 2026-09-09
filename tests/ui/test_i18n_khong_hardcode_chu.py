"""Chữ trên giao diện phải đi qua ``tr()`` — kể cả chữ do CHÍNH Qt vẽ.

Bộ ``test_i18n_khong_con_chu_cu.py`` bắt lỗi "có dịch nhưng không ai áp lại".
Nó không bắt được lỗi người dùng báo tháng 9/2026: "đang tiếng Nhật mà nút Save,
Cancel và phần mật khẩu sandbox vẫn tiếng Anh". Lý do là hai lỗ khác hẳn:

* **Chuỗi hardcode.** ``QPushButton("Unlock")`` không hỏi ``tr()`` bao giờ, nên
  phép đo "đổi ngôn ngữ rồi tìm chỗ không mang mốc" thấy nó đứng yên ở cả hai
  lần chụp và coi là bình thường.
* **Nhãn nút của chính Qt.** ``QDialogButtonBox(Save | Cancel)`` và
  ``QMessageBox.question`` lấy chữ từ bảng dịch của Qt. Ứng dụng không cài
  ``QTranslator`` nào nên bảng đó luôn rơi về tiếng Anh — không dòng mã nào của
  dự án sai, mà màn hình vẫn sai.

Ba cổng dưới đây canh cả hai lỗ, và canh ở mức CẤU TRÚC (không ai được dựng lại
kiểu cũ) chứ không chỉ sửa xong từng chỗ.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
#: Chỉ hai tầng này vẽ giao diện.
THU_MUC_UI = ("ui", "presentation")
#: Nơi DUY NHẤT được phép chạm vào nút chuẩn của Qt — chính chỗ gán nhãn lại.
NOI_BOC_QT = "ui/dialog_buttons.py"


def _file_ui():
    """Mọi file .py thuộc tầng giao diện, kèm cây AST đã phân tích."""
    for thu_muc in THU_MUC_UI:
        for path in sorted((REPO / thu_muc).rglob("*.py")):
            rel = path.relative_to(REPO).as_posix()
            yield rel, ast.parse(path.read_text(encoding="utf-8"))


def _ten_ham(func) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


# ---- cấu trúc: không ai được dùng lại nhãn mặc định của Qt ----------------

def test_khong_dung_nut_chuan_qdialogbuttonbox_truc_tiep():
    """``QDialogButtonBox(Save | Cancel)`` phải đi qua ``dialog_buttons()``.

    Dựng thẳng thì Qt tự vẽ chữ, và chữ đó là tiếng Anh ở cả ba ngôn ngữ.
    """
    vi_pham = []
    for rel, tree in _file_ui():
        if rel == NOI_BOC_QT:
            continue
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and _ten_ham(node.func) == "QDialogButtonBox"
                    and node.args):
                # Không tham số = hộp rỗng rồi tự addButton(tr(...)) — vẫn đúng.
                vi_pham.append(f"{rel}:{node.lineno}")

    assert vi_pham == [], (
        "dựng QDialogButtonBox với nút chuẩn thì nhãn do Qt vẽ và luôn là tiếng "
        "Anh — dùng ui.dialog_buttons.dialog_buttons() thay vào:\n  "
        + "\n  ".join(vi_pham))


def test_khong_goi_qinputdialog_tinh_truc_tiep():
    """Hộp nhập liệu phải đi qua ``ask_text`` / ``ask_multiline`` / ``ask_item``.

    ``QInputDialog.getText`` và họ hàng tự dựng hộp thoại bên trong nên không ai
    chạm được vào nút của nó: "Cancel" đứng nguyên tiếng Anh ở cả ja lẫn vi.
    """
    vi_pham = []
    for rel, tree in _file_ui():
        if rel == NOI_BOC_QT:
            continue
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "QInputDialog"
                    and node.func.attr.startswith("get")):
                vi_pham.append(f"{rel}:{node.lineno} QInputDialog.{node.func.attr}")

    assert vi_pham == [], (
        "hàm tĩnh QInputDialog hiện nút Cancel tiếng Anh ở mọi ngôn ngữ — dùng "
        "ask_text / ask_multiline / ask_item của ui.dialog_buttons:\n  "
        + "\n  ".join(vi_pham))


def test_khong_goi_qmessagebox_question_truc_tiep():
    """Hộp hỏi Có/Không phải đi qua ``confirm()``.

    ``QMessageBox.question`` hiện "&Yes" / "&No" tiếng Anh ở mọi ngôn ngữ.
    """
    vi_pham = []
    for rel, tree in _file_ui():
        if rel == NOI_BOC_QT:
            continue
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "question"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "QMessageBox"):
                vi_pham.append(f"{rel}:{node.lineno}")

    assert vi_pham == [], (
        "QMessageBox.question hiện nút Yes/No tiếng Anh ở mọi ngôn ngữ — dùng "
        "ui.dialog_buttons.confirm() thay vào:\n  " + "\n  ".join(vi_pham))


# ---- dữ liệu: không chuỗi hiển thị nào được viết thẳng vào widget ----------

#: Đối số thứ N của các hàm dựng widget này là NHÃN hiển thị.
CTOR_NHAN = {
    "QLabel": 0, "QPushButton": 0, "QGroupBox": 0, "QCheckBox": 0,
    "QRadioButton": 0, "QToolButton": 0, "QAction": 0, "QMenu": 0,
    "QListWidgetItem": 0, "QTreeWidgetItem": 0, "QTableWidgetItem": 0,
    "IconLabel": 1, "ToggleSwitch": 0,
}
#: Đối số thứ N của các setter này là chuỗi hiển thị.
SETTER_NHAN = {
    "setText": 0, "setToolTip": 0, "setPlaceholderText": 0, "setWindowTitle": 0,
    "setTitle": 0, "setStatusTip": 0, "setWhatsThis": 0, "setLabelText": 0,
    "setInformativeText": 0, "setAccessibleName": 0, "addItem": 0,
    "insertItem": 1, "setItemText": 1, "addAction": 0, "addTab": 1,
    "insertTab": 2, "setTabText": 1, "setTabToolTip": 1, "setHeaderLabel": 0,
}
#: Mọi đối số chuỗi đều là nhãn.
SETTER_NHAN_TAT_CA = {
    "setHorizontalHeaderLabels", "setHeaderLabels", "setVerticalHeaderLabels",
}
#: ``QMessageBox.<loai>(parent, title, body)`` — đối số 1 và 2 là chữ hiển thị.
MSGBOX_LOAI = {"information", "warning", "critical", "about"}

#: Chuỗi cố ý viết thẳng, kèm lý do. Thêm mục ở đây là một quyết định, không
#: phải cách làm cổng xanh lại — chữ người dùng ĐỌC ĐƯỢC thì phải dịch.
CHO_PHEP_HARDCODE = {
    # ký hiệu đơn vị và tiền tố phiên bản: giống nhau ở cả ba ngôn ngữ
    ("presentation/monitoring/tabs/overview_tab.py", "/s"),
    ("presentation/settings/about_widget.py", " v"),
    ("presentation/settings/routing_settings_widget.py", " s"),
    ("presentation/settings/routing_settings_widget.py", " h"),
    ("presentation/shell/main_window.py", " v"),
    ("ui/task_editor_dialog.py", " s"),
}


def _chuoi(node) -> str | None:
    """Chữ của một literal chuỗi. Bỏ qua f-string đã có ``tr()`` bên trong."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        if any(isinstance(n, ast.Call) and _ten_ham(n.func) == "tr"
               for n in ast.walk(node)):
            return None
        phan = [v.value for v in node.values
                if isinstance(v, ast.Constant) and isinstance(v.value, str)]
        return "".join(phan) if phan else None
    return None


def _la_chu_nguoi_doc(s: str) -> bool:
    """Chuỗi có phải chữ người dùng ĐỌC, chứ không phải mã/ký hiệu/định dạng.

    Mốc "ít nhất ba chữ cái" loại được đơn vị (``/s``, `` h``) và tiền tố phiên
    bản (`` v``) mà vẫn giữ lại mọi nhãn thật — nhãn ngắn nhất trên màn này là
    "Unlock".
    """
    import re

    if len(s.strip()) < 2 or re.fullmatch(r"[\W\d_]+", s):
        return False
    if re.fullmatch(r"[a-z][a-zA-Z0-9]*|[a-z0-9_.]+", s):
        return False          # objectName / khoá dạng định danh
    if s.startswith(("http://", "https://", "#", "<")):
        return False
    return len(re.findall(r"[A-Za-zÀ-ỹ぀-ヿ一-鿿]", s)) >= 3


def test_khong_con_chuoi_hien_thi_viet_thang_vao_widget():
    """Không nhãn/tooltip/placeholder nào được viết thẳng bằng một ngôn ngữ.

    Đây là nửa còn lại của lỗi tháng 9/2026: nhóm mật khẩu Sandbox Security
    dựng bằng ``QPushButton("Unlock")`` và ``IconLabel(..., "Locked ...")``, nên
    đổi sang tiếng Nhật thì cả cụm vẫn nguyên tiếng Anh.
    """
    vi_pham = []
    for rel, tree in _file_ui():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn, args = _ten_ham(node.func), node.args

            def bao(i: int) -> None:
                if i >= len(args):
                    return
                s = _chuoi(args[i])
                if s and _la_chu_nguoi_doc(s) and (rel, s) not in CHO_PHEP_HARDCODE:
                    vi_pham.append(f"{rel}:{args[i].lineno} {fn}({s!r})")

            if fn in CTOR_NHAN:
                bao(CTOR_NHAN[fn])
            if fn in SETTER_NHAN:
                bao(SETTER_NHAN[fn])
            if fn in SETTER_NHAN_TAT_CA:
                for i in range(len(args)):
                    bao(i)
            if (fn in MSGBOX_LOAI and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "QMessageBox"):
                bao(1)
                bao(2)

    assert vi_pham == [], (
        "chữ hiển thị viết thẳng, không đi qua tr() nên không đổi theo ngôn "
        "ngữ:\n  " + "\n  ".join(sorted(vi_pham)))


def test_moi_tool_co_mo_ta_hien_thi_rieng():
    """Mỗi tool trong ``TOOL_SPECS`` phải có khoá mô tả để hiển thị.

    Thẻ tool ở Giám sát ▸ Công cụ từng hiện thẳng ``spec.description`` — chuỗi
    gửi cho MÔ HÌNH trong schema function-calling, nên luôn tiếng Anh. Thiếu
    khoá thì ``tr()`` trả về chính khoá, và người dùng đọc được
    ``tools_admin.desc.<tên>`` ngay trên thẻ.
    """
    from cowork_local.core.tools import TOOL_SPECS
    from cowork_local.i18n import STRINGS

    thieu = [s.name for s in TOOL_SPECS
             if f"tools_admin.desc.{s.name}" not in STRINGS]

    assert thieu == [], (
        "tool chưa có khoá mô tả hiển thị (thêm tools_admin.desc.<tên> vào "
        f"i18n/libreoffice_view.py): {thieu}")


def test_add_section_nhan_khoa_chu_khong_nhan_chuoi_da_dich():
    """``_add_section`` tự dựng nhãn mục, nên phải nhận KHOÁ.

    Truyền ``tr(...)`` vào đây hỏng ÂM THẦM: khoá thiếu thì ``tr()`` trả về
    chính chuỗi đưa vào, nên tiêu đề hiện đúng ở ngôn ngữ lúc dựng panel rồi
    đứng nguyên mãi. Đúng lỗi người dùng báo: mở Co4E ▸ Step config ở tiếng
    Nhật thì đổi sang tiếng Anh vẫn còn tiếng Nhật.
    """
    vi_pham = []
    for rel, tree in _file_ui():
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and _ten_ham(node.func) == "_add_section"
                    and len(node.args) >= 2
                    and isinstance(node.args[1], ast.Call)
                    and _ten_ham(node.args[1].func) == "tr"):
                vi_pham.append(f"{rel}:{node.lineno}")

    assert vi_pham == [], (
        "_add_section nhận khoá dịch, không nhận tr(...) — truyền chuỗi đã dịch "
        "thì tiêu đề mục không bao giờ đổi lại:\n  " + "\n  ".join(vi_pham))


# ---- lúc chạy: nhãn nút thật sự đổi theo ngôn ngữ -------------------------

def test_tieu_de_muc_step_config_doi_theo_ngon_ngu(qapp):
    """Bốn tiêu đề mục của Step config phải đổi theo ngôn ngữ.

    Panel này dựng LƯỜI (chỉ khi người dùng chọn một bước trên canvas Co4E) nên
    nó không nằm trong cây widget mà ``test_i18n_khong_con_chu_cu`` quét — phải
    dựng thẳng ở đây thì mới canh được.
    """
    pytest.importorskip("PySide6")

    from cowork_local import i18n
    from cowork_local.presentation.co4e.node_property_panel import StepConfigPanel
    from cowork_local.presentation.co4e.step_config_section import _SectionHeader

    cu = i18n.get_language()
    try:
        i18n.set_language("ja")
        panel = StepConfigPanel()          # dựng TRONG lúc đang tiếng Nhật
        nhat = [h.text() for h in panel.findChildren(_SectionHeader)]
        assert nhat, "không tìm thấy tiêu đề mục nào"

        i18n.set_language("en")
        anh = [h.text() for h in panel.findChildren(_SectionHeader)]

        assert all(a != n for a, n in zip(anh, nhat)), (
            f"tiêu đề mục giữ nguyên ngôn ngữ lúc dựng panel: {anh}")
        assert anh == [f"▶ {i18n.tr(k)}" for k in
                       ("co4e.tab_basic", "co4e.tab_model_perm",
                        "co4e.tab_skills_files", "co4e.f_subagents")]
    finally:
        i18n.set_language(cu)


def test_doi_ngon_ngu_khong_lam_mat_trang_thai_gap_mo(qapp):
    """Mục đang MỞ vẫn phải mang dấu ▼ sau khi đổi ngôn ngữ.

    Đây là lý do nhãn này dùng ``bind_dynamic`` chứ không ``bind_text``: bind
    cứng một khoá sẽ ghi đè cả dấu gập/mở, trả mục đang mở về ▶ trong khi phần
    thân của nó vẫn đang hiện.
    """
    pytest.importorskip("PySide6")

    from cowork_local import i18n
    from cowork_local.presentation.co4e.node_property_panel import StepConfigPanel
    from cowork_local.presentation.co4e.step_config_section import _SectionHeader

    cu = i18n.get_language()
    try:
        i18n.set_language("en")
        panel = StepConfigPanel()
        header = panel.findChildren(_SectionHeader)[0]
        header.clicked.emit()                      # mở mục đầu tiên
        assert header.text().startswith("▼")

        i18n.set_language("ja")

        assert header.text().startswith("▼"), (
            f"đổi ngôn ngữ làm mất trạng thái đang mở: {header.text()!r}")
    finally:
        i18n.set_language(cu)

def test_nhan_nut_hop_thoai_doi_theo_ngon_ngu(qapp):
    """Nút Save/Cancel mang chữ của dự án ở cả ba ngôn ngữ.

    Chốt luôn cái bẫy vòng đời: ràng buộc giữ widget bằng ``weakref``, mà nút
    chuẩn do C++ dựng nên wrapper Python của nó có thể bị thu hồi. Hộp thoại ở
    đây thả hết tham chiếu cục bộ, đúng như mọi call site thật.
    """
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

    from cowork_local import i18n
    from cowork_local.ui.dialog_buttons import dialog_buttons

    dlg = QDialog()
    QVBoxLayout(dlg).addWidget(
        dialog_buttons(QDialogButtonBox.Save | QDialogButtonBox.Cancel))
    hop = dlg.findChild(QDialogButtonBox)

    cu = i18n.get_language()
    try:
        for lang in ("en", "ja", "vi"):
            i18n.set_language(lang)
            mong_doi = [i18n.STRINGS["dialog.save"][lang],
                        i18n.STRINGS["dialog.cancel"][lang]]
            assert [b.text() for b in hop.buttons()] == mong_doi, (
                f"nhãn nút không theo ngôn ngữ {lang}")
    finally:
        i18n.set_language(cu)
        dlg.close()
