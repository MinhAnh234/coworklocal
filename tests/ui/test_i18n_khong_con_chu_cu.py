"""Đổi ngôn ngữ thì MỌI chữ trên màn hình phải đổi theo.

Lỗi mà bộ test này khoá lại: `w.setToolTip(tr("k"))` chỉ đúng ở đúng thời điểm
chạy dòng đó. Không có gì áp lại, nên sau khi người dùng đổi ngôn ngữ thì chữ
đứng nguyên ở ngôn ngữ cũ. Vì `DEFAULT_LANGUAGE = "vi"`, triệu chứng người dùng
báo là "chọn English mà nhiều chỗ vẫn tiếng Việt".

Cách kiểm: KHÔNG so chữ với bảng dịch — làm thế thì một nhãn tiếng Việt trùng
chữ với nhãn khác sẽ báo oan (và ngược lại, "OneDrive" giống nhau ở cả ba ngôn
ngữ sẽ lọt). Thay vào đó thay `tr()` bằng hàm trả về một chuỗi MỐC, rồi gọi
`set_language()`. Chỗ nào được áp lại sẽ mang mốc; chỗ nào không mang mốc là chỗ
không có ai áp lại — đó chính là lỗi, và biết chắc chứ không phải suy đoán.

Hai điểm mà một bản kiểm ngây thơ sẽ sai:

* `from ...i18n import tr` COPY tham chiếu vào namespace của từng module, nên
  sửa `i18n.tr` một mình là không đủ — phải thay ở mọi module đã import nó.
* Lưới vẽ lại bằng `deleteLater()` để lại widget cũ còn sống tới khi vòng lặp sự
  kiện tiêu hoá xong. Không `sendPostedEvents(DeferredDelete)` thì hàng chục
  widget bóng ma mang chữ cũ sẽ bị đếm là lỗi trong khi người dùng không hề thấy.
"""
from __future__ import annotations

import sys

import pytest

pytest.importorskip("PySide6", reason="cần PySide6 để dựng cửa sổ thật")

MOC = "\u2063"   # invisible separator: không chuỗi hiển thị thật nào chứa nó

#: Khoá cố ý giống nhau ở cả ba ngôn ngữ: tên thương hiệu, tên sản phẩm, ký hiệu,
#: placeholder thuần định dạng, và mã mức độ hiển thị nguyên dạng. Thêm khoá mới
#: vào đây phải kèm lý do — đây là chỗ dễ dùng để lặng lẽ bỏ qua việc dịch.
KHOA_KHONG_CAN_DICH = {
    # thương hiệu / tên sản phẩm
    "app.logo", "app.version", "login.header",
    "app.tab.code", "app.tab.cowork", "app.tab.structure",
    "code.title", "code.onedrive_badge", "code.onedrive_btn",
    "cowork.title", "sidebar.filter.code", "sidebar.filter.cowork",
    "workspace.tab_co4e", "workspace.tab_co4e_tooltip", "workspace.tab_cowork",
    "workspace.tab_graphrag", "structure.cmem_ui_open",
    "settings.group.anthropic", "settings.group.cowork", "settings.group.structure",
    "settings.group.teams", "settings.history_onedrive",
    "settings.ms365_connector.onedrive", "settings.ms365_connector.outlook",
    "settings.ms365_connector.sharepoint", "settings.ms365_connector.teams",
    # tên nhóm catalog = danh sách tên sản phẩm, giống hệt ở cả ba ngôn ngữ
    "connectors.cat_cad", "connectors.cat_cae", "connectors.cat_ms365",
    "schedtask.stepexec.co4e", "schedtask.stepexec.cowork",
    "schedtask.type.co4e_code", "schedtask.type.cowork",
    "monitoring.tab_mcp", "ext.mode_rest", "schedtask.f_cron",
    "help_agent.badge", "help_agent.title",   # dùng nguyên dạng trong cả câu tiếng Nhật
    "help_agent.default_user",                # đứng thay cho TÊN người dùng
    # "OK" giữ nguyên dạng ở cả ba ngôn ngữ — bản tiếng Nhật của chính Qt cũng dùng "OK"
    "dialog.ok",
    # viết tắt / ký hiệu / thuần định dạng
    "accounts.ai_search_btn", "monitoring.ai_filter_btn", "monitoring.overview_res_cpu",
    "monitoring.na", "schedtask.add_link_label", "settings.teams_webhook",
    "cowork.project_label", "connectors.jira_fail", "tools_admin.jira_fail",
    # mã mức độ: giữ nguyên dạng ở CẢ BA ngôn ngữ, có chủ ý
    "monitoring.severity_critical", "monitoring.severity_info", "monitoring.severity_medium",
}


# ---- dữ liệu: bảng dịch không được thiếu tiếng Nhật ----------------------

def test_moi_khoa_co_du_ba_ngon_ngu():
    from cowork_local.i18n import STRINGS

    thieu = {k: sorted({"en", "ja", "vi"} - {x for x in v if v.get(x)})
             for k, v in STRINGS.items()
             if not all(v.get(x) for x in ("en", "ja", "vi"))}

    assert thieu == {}, f"khoá thiếu bản dịch: {thieu}"


def test_ban_dich_nhat_khong_phai_chuoi_tieng_anh():
    """`ja` bằng đúng `en` nghĩa là khoá đó chưa được dịch — trừ danh sách miễn.

    Đây là nửa còn lại của lỗi người dùng báo: "chọn tiếng Nhật thì vài chỗ hiển
    thị tiếng Anh". Nó KHÔNG phải lỗi dây nối (widget vẫn áp lại `tr()` đúng),
    mà là lỗ trong dữ liệu dịch — nên phải có cổng riêng canh.
    """
    from cowork_local.i18n import STRINGS

    chua_dich = sorted(k for k, v in STRINGS.items()
                       if v.get("en") == v.get("ja") and k not in KHOA_KHONG_CAN_DICH)

    assert chua_dich == [], (
        "khoá chưa có bản dịch tiếng Nhật (thêm bản dịch, hoặc khai vào "
        f"KHOA_KHONG_CAN_DICH kèm lý do): {chua_dich}")


def test_danh_sach_mien_khong_phinh_len_am_tham():
    """Danh sách miễn chỉ được chứa khoá THẬT SỰ giống nhau ở en/ja.

    Không có test này thì cách dễ nhất để làm cổng trên xanh lại là nhét khoá
    vào danh sách miễn rồi để nguyên đó sau khi đã dịch.
    """
    from cowork_local.i18n import STRINGS

    thua = sorted(k for k in KHOA_KHONG_CAN_DICH
                  if k in STRINGS and STRINGS[k].get("en") != STRINGS[k].get("ja"))

    assert thua == [], f"khoá đã có bản dịch nhưng vẫn nằm trong danh sách miễn: {thua}"


# ---- lúc chạy: đổi ngôn ngữ thì chữ trên màn hình phải đổi --------------

def _chu_cua(w):
    """Mọi chỗ chữ hiện ra từ một widget, kèm tên thuộc tính."""
    from PySide6.QtWidgets import (
        QComboBox, QLineEdit, QListWidget, QPlainTextEdit, QTabWidget,
        QTableWidget, QTextEdit, QTreeWidget,
    )
    ra = []

    def them(ten, s):
        if isinstance(s, str) and s.strip():
            ra.append((ten, s))

    # QLineEdit.text() là NỘI DUNG người dùng gõ, không phải nhãn giao diện.
    if hasattr(w, "text") and not isinstance(w, (QLineEdit, QTextEdit, QPlainTextEdit)):
        try:
            them("text", w.text())
        except RuntimeError:
            return ra
    for ten in ("windowTitle", "placeholderText", "toolTip", "title", "accessibleName"):
        f = getattr(w, ten, None)
        if callable(f):
            try:
                them(ten, f())
            except (RuntimeError, TypeError):
                pass
    if isinstance(w, QTabWidget):
        for i in range(w.count()):
            them(f"tabText[{i}]", w.tabText(i))
            them(f"tabToolTip[{i}]", w.tabToolTip(i))
    if isinstance(w, QComboBox):
        for i in range(w.count()):
            them(f"itemText[{i}]", w.itemText(i))
    if isinstance(w, QListWidget):
        for i in range(w.count()):
            it = w.item(i)
            if it is not None:
                them(f"item[{i}]", it.text())
                them(f"itemTip[{i}]", it.toolTip())
    if isinstance(w, QTableWidget):
        for c in range(w.columnCount()):
            h = w.horizontalHeaderItem(c)
            if h is not None:
                them(f"hheader[{c}]", h.text())
    if isinstance(w, QTreeWidget):
        hi = w.headerItem()
        if hi is not None:
            for c in range(w.columnCount()):
                them(f"hheader[{c}]", hi.text(c))
    return ra


def _chu_so_huu(w):
    """Lớp widget của chính dự án gần nhất trên đường đi lên.

    Một `QPushButton` trần không cho biết nó thuộc màn nào; tổ tiên gần nhất do
    dự án định nghĩa thì cho biết, và đó là file cần sửa.
    """
    cur = w
    while cur is not None:
        mod = type(cur).__module__ or ""
        if mod.startswith("cowork_local"):
            return f"{mod}.{type(cur).__name__}"
        cur = cur.parent()
    return "?"


def _chup(root, giu):
    """Ảnh chụp mọi chỗ chữ trong cây widget.

    ``giu`` nhận thêm tham chiếu tới từng widget đã đi qua: wrapper PySide6 bị
    thu hồi thì `id()` được cấp lại cho wrapper sau, và vòng quét sẽ tưởng đã
    thăm rồi mà dừng sớm — mất phần lớn cây.
    """
    from PySide6.QtWidgets import QMenu, QWidget

    anh, ngan, da_tham = {}, [root], set()
    while ngan:
        w = ngan.pop()
        if id(w) in da_tham:
            continue
        da_tham.add(id(w))
        giu.append(w)
        so_huu = _chu_so_huu(w)
        for ten, s in _chu_cua(w):
            anh[(id(w), type(w).__name__, so_huu, ten)] = s
        try:
            ngan.extend([c for c in w.children() if isinstance(c, (QWidget, QMenu))])
        except RuntimeError:
            pass
    return anh


def _thay_tr(moi, cu):
    """Thay `tr` ở MỌI module của dự án đang trỏ tới ``cu``. Trả về số module."""
    from cowork_local import i18n as i18n_mod

    n = 0
    for ten, m in list(sys.modules.items()):
        if ten.startswith("cowork_local") and getattr(m, "tr", None) is cu:
            setattr(m, "tr", moi)
            n += 1
    i18n_mod.tr = moi
    return n


def _tieu_hoa(qapp):
    """Cho Qt xử lý hết `deleteLater()` để không đếm widget bóng ma."""
    from PySide6.QtCore import QEvent

    for _ in range(3):
        qapp.processEvents()
        qapp.sendPostedEvents(None, QEvent.DeferredDelete)


@pytest.fixture
def cua_so(qapp, tmp_path):
    """`MainWindow` thật, đã dựng cả bốn trang dựng-lười.

    Trang chưa dựng thì không có chữ nào để kiểm, mà đó lại đúng là nơi lỗi hay
    nằm — nên phải gọi `_ensure_page` cho hết.
    """
    from cowork_local.presentation.shell.bootstrap import build_config, build_context
    from cowork_local.presentation.shell.main_window import MainWindow

    duong_dan = tmp_path / "config.json"
    build_config(duong_dan)
    win = MainWindow(build_context(duong_dan))
    win.resize(1500, 950)
    for row in range(len(win._page_widgets)):
        win._ensure_page(row)
    yield win
    win.close()


def test_doi_ngon_ngu_thi_khong_con_chu_ngon_ngu_cu(qapp, cua_so):
    """Không chỗ nào giữ lại chữ của ngôn ngữ cũ sau khi đổi ngôn ngữ."""
    from cowork_local import i18n as i18n_mod

    giu = []          # chống cấp lại id() cho wrapper mới
    goc = i18n_mod.tr
    ngon_ngu_cu = i18n_mod.get_language()
    i18n_mod.set_language("vi")
    _tieu_hoa(qapp)
    truoc = _chup(cua_so, giu)

    def moc(key, **kw):
        return MOC + key

    try:
        assert _thay_tr(moc, goc) > 0, "không thay được tr() ở module nào"
        i18n_mod.set_language("en")
        _tieu_hoa(qapp)
        sau = _chup(cua_so, giu)
    finally:
        _thay_tr(goc, moc)
        i18n_mod.set_language(ngon_ngu_cu)

    # Chỉ tính chỗ mà chữ CÓ phụ thuộc ngôn ngữ: "OneDrive" giống nhau ở cả ba
    # ngôn ngữ nên không áp lại cũng không ai thấy khác.
    phu_thuoc_ngon_ngu = set()
    for v in i18n_mod.STRINGS.values():
        gia_tri = {v.get("en"), v.get("ja"), v.get("vi")}
        if len(gia_tri) > 1:
            phu_thuoc_ngon_ngu.update(x for x in gia_tri if x)

    # Nhãn nhà cung cấp là DANH TÍNH lấy từ ``config.PROVIDER_LABELS``, không đi
    # qua ``tr()`` ở bất kỳ đâu (Agents Admin, model resolver, preview_ai đều
    # hiện nguyên dạng như nhau). Một trong số chúng tình cờ trùng chữ với bản
    # tiếng Anh của ``settings.group.openai`` — là tiêu đề mục trong Cài đặt,
    # một khoá khác hẳn. Không trừ ra thì phép đo báo oan chỗ này mãi mãi.
    # Muốn dịch tên nhà cung cấp thì phải sửa ``config.py`` và sửa đồng loạt cả
    # năm nơi đang đọc nó — đó là một quyết định sản phẩm, không phải lỗi dây nối.
    from cowork_local.config import PROVIDER_LABELS
    phu_thuoc_ngon_ngu -= set(PROVIDER_LABELS.values())

    con_chu_cu = sorted(
        f"{cho[2]} :: {cho[1]}.{cho[3]} = {chu!r}"
        for cho, chu in sau.items()
        if cho in truoc and not chu.startswith(MOC) and chu in phu_thuoc_ngon_ngu
    )

    assert con_chu_cu == [], (
        "những chỗ này không được áp lại khi đổi ngôn ngữ — dùng bind_text / "
        "bind_tip / bind_placeholder / bind_items / bind_dynamic của i18n thay "
        "cho setText(tr(...)) một lần:\n  " + "\n  ".join(con_chu_cu))


def test_phep_do_thuc_su_quet_duoc_man_hinh(qapp, cua_so):
    """Chốt độ phủ của chính phép đo trên.

    Một hôm nào đó `_chup` đi sai (đúng lỗi `id()` bị cấp lại đã gặp) thì nó vẫn
    trả về một dict rỗng và test trên vẫn xanh — xanh vì không kiểm gì cả.
    """
    giu = []
    anh = _chup(cua_so, giu)

    assert len(anh) > 500, f"chỉ quét được {len(anh)} chỗ chữ — phép đo đang bị cắt"


def test_binding_tu_don_khi_widget_bi_xoa(qapp):
    """Ràng buộc không được giữ widget sống, và không được ném khi widget chết.

    Đây là điều kiện để `bind_*` dùng được cho widget dựng lại liên tục (hàng
    Kanban, ô lịch) mà không tích thành rác.
    """
    from PySide6.QtWidgets import QLabel

    from cowork_local import i18n as i18n_mod

    lbl = QLabel()
    i18n_mod.bind_text(lbl, "app.settings")
    truoc = len(i18n_mod._bindings)
    assert truoc > 0

    lbl.deleteLater()
    del lbl
    _tieu_hoa(qapp)
    i18n_mod._apply_bindings()          # không được ném

    assert len(i18n_mod._bindings) < truoc, "ràng buộc của widget đã xoá vẫn còn"
