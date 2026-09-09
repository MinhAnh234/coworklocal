"""Sandbox Security unlock — chốt các đường KHÔNG được mở khoá (SEC-20260907-01).

``DEFAULT_CONFIG`` ship ``agent_security.sandbox_pw = ""`` kể từ commit
``3827552 fix(security): remove shared unlock defaults``, và cấu hình đưa tới
dialog LUÔN được deep-merge với defaults đó
(``infrastructure/config/json_config_repository.py``). Nghĩa là trên mọi bản cài
không đặt ``COWORK_SANDBOX_PASSWORD``, mật khẩu đã lưu là chuỗi rỗng — và phép so
sánh ``pw == self._sandbox_pw`` nhận luôn ô nhập trống.

Ba nhóm bài ở đây:

* **đường tấn công** — chốt đúng lỗ trên;
* **đường đi đúng** — bản vá không được phá, kể cả với mật khẩu có dấu;
* **chặn cả lớp lỗi** — commit ``3827552`` sửa ``config.py`` nhưng bỏ sót bản sao
  thứ hai của literal trong ``ui/settings_dialog.py``. Bài cuối quét chéo mọi thư
  mục nguồn để lần sau không sót kiểu đó nữa.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# Fake ctx dùng chung với đặc tả SettingsDialog: nó đã là "đủ cho SettingsDialog,
# không hơn". Dựng bản thứ hai ở đây chỉ tạo thêm một chỗ để lệch nhau.
from .test_settings_dialog_dac_ta import _Ctx


@pytest.fixture
def shown(monkeypatch):
    """Ghi lại mọi QMessageBox thay vì bật modal thật (modal sẽ treo test).

    Trả về list các ``(loại, tiêu_đề, nội_dung)`` — cần thiết để phân biệt
    "chưa cấu hình mật khẩu" với "sai mật khẩu"; nếu chỉ nuốt hộp thoại đi thì
    hai nhánh gộp lại làm một mà test vẫn xanh.
    """
    from PySide6.QtWidgets import QMessageBox
    calls: list[tuple[str, str, str]] = []

    def _record(kind):
        def _fn(_parent, title, text, *a, **k):
            calls.append((kind, title, text))
        return staticmethod(_fn)

    monkeypatch.setattr(QMessageBox, "warning", _record("warning"))
    monkeypatch.setattr(QMessageBox, "information", _record("information"))
    return calls


def _dialog(stored_pw: str):
    """SettingsDialog với ``sandbox_pw`` đúng như bản cài thật: key CÓ mặt."""
    from cowork_local.ui.settings_dialog import SettingsDialog
    ctx = _Ctx()
    ctx.config.data["agent_security"]["sandbox_pw"] = stored_pw
    return SettingsDialog(ctx)


# ---- đường tấn công ------------------------------------------------------

def test_o_trong_khong_mo_duoc_khoa(qapp, shown):
    """Chưa đặt mật khẩu (sandbox_pw == "") thì ô nhập trống KHÔNG được mở khoá."""
    dlg = _dialog("")
    dlg.sandbox_pw_edit.setText("")

    dlg._sandbox_unlock()

    assert dlg._sandbox_unlocked is False
    dlg.deleteLater()


def test_go_bua_khi_chua_dat_mat_khau_cung_khong_mo_duoc(qapp, shown):
    """Mật khẩu lưu rỗng thì KHÔNG chuỗi nào mở được, kể cả chuỗi khác rỗng."""
    dlg = _dialog("")
    dlg.sandbox_pw_edit.setText("bat ky")

    dlg._sandbox_unlock()

    assert dlg._sandbox_unlocked is False
    dlg.deleteLater()


def test_mat_khau_sai_khong_mo_duoc(qapp, shown):
    """Đã đặt mật khẩu thì gõ sai vẫn khoá."""
    dlg = _dialog("K7MNP2QRSTVW")
    dlg.sandbox_pw_edit.setText("K7MNP2QRSTVX")

    dlg._sandbox_unlock()

    assert dlg._sandbox_unlocked is False
    dlg.deleteLater()


# ---- thông báo phải phân biệt được hai tình huống -------------------------

def test_chua_cau_hinh_bao_khac_voi_sai_mat_khau(qapp, shown):
    """Hai nhánh phải nói hai chuyện khác nhau.

    Người chưa từng đặt mật khẩu mà nhận "Password incorrect" sẽ gõ lại mãi một
    thứ không tồn tại. Không có bài này thì gộp hai nhánh về một thông báo chung
    vẫn xanh hết.
    """
    from cowork_local.i18n import tr

    dlg = _dialog("")
    dlg.sandbox_pw_edit.setText("")
    dlg._sandbox_unlock()
    chua_cau_hinh = list(shown)
    dlg.deleteLater()

    shown.clear()
    dlg2 = _dialog("K7MNP2QRSTVW")
    dlg2.sandbox_pw_edit.setText("sai roi")
    dlg2._sandbox_unlock()
    sai_mat_khau = list(shown)
    dlg2.deleteLater()

    assert len(chua_cau_hinh) == 1, "phải hiện đúng một thông báo"
    assert len(sai_mat_khau) == 1
    assert chua_cau_hinh[0][2] == tr("settings.sandbox_pw_unset_body")
    assert chua_cau_hinh[0][2] != sai_mat_khau[0][2], (
        "chưa cấu hình mật khẩu và sai mật khẩu phải là hai thông báo khác nhau")


# ---- đường đi đúng vẫn phải chạy ----------------------------------------

def test_mat_khau_dung_van_mo_duoc(qapp, shown):
    """Bản vá không được phá đường đi hợp lệ."""
    dlg = _dialog("K7MNP2QRSTVW")
    dlg.sandbox_pw_edit.setText("K7MNP2QRSTVW")

    dlg._sandbox_unlock()

    assert dlg._sandbox_unlocked is True
    dlg.deleteLater()


@pytest.mark.parametrize("pw", ["mật khẩu", "パスワード", "sénhà-2026"])
def test_mat_khau_co_dau_khong_lam_crash(qapp, shown, pw):
    """``secrets.compare_digest`` ném TypeError nếu str có ký tự ngoài ASCII.

    App mặc định tiếng Việt và phục vụ khách Nhật, nên chữ có dấu trong ô mật
    khẩu là input bình thường. Phải so sánh trên bytes.
    """
    dlg = _dialog(pw)
    dlg.sandbox_pw_edit.setText(pw)

    dlg._sandbox_unlock()          # không được ném TypeError

    assert dlg._sandbox_unlocked is True
    dlg.deleteLater()


def test_mat_khau_co_dau_sai_thi_van_khoa(qapp, shown):
    """Chữ có dấu không được biến thành đường mở khoá dễ dãi."""
    dlg = _dialog("mật khẩu")
    dlg.sandbox_pw_edit.setText("mat khau")

    dlg._sandbox_unlock()

    assert dlg._sandbox_unlocked is False
    dlg.deleteLater()


# ---- hàm so khớp, gọi thẳng ----------------------------------------------

@pytest.mark.parametrize("entered,stored,expected", [
    ("", "", False),                       # cả hai rỗng
    ("", "K7MNP2QRSTVW", False),           # ô nhập rỗng
    ("K7MNP2QRSTVW", "", False),           # chưa đặt mật khẩu — nhánh phòng thủ
    ("K7MNP2QRSTVW", "K7MNP2QRSTVW", True),
    ("mật khẩu", "mật khẩu", True),        # ngoài ASCII
    ("mật khẩu", "mat khau", False),
])
def test_ham_so_khop(entered, stored, expected):
    """Gọi thẳng ``_sandbox_password_matches`` — phủ cả nhánh mà call site đã
    chặn trước bằng return sớm."""
    from cowork_local.ui.settings_dialog import _sandbox_password_matches
    assert _sandbox_password_matches(entered, stored) is expected


# ---- chặn cả lớp lỗi -----------------------------------------------------

#: ``.get("<khoá kiểu credential>", "<literal khác rỗng>")`` — mặc định trông có
#: vẻ an toàn nhưng thực ra là credential nằm trong mã nguồn. Nó cũng là code
#: chết: cấu hình đã deep-merge với DEFAULT_CONFIG nên key luôn tồn tại.
#:
#: Cố ý KHÔNG bắt ``key`` và ``code`` trần: ``it.get("key", "?")`` của Jira
#: (``core/jira_tool.py``) là mã issue, không phải credential. Danh sách dưới đây
#: chỉ gồm tên đã mang nghĩa bí mật.
_CREDENTIAL_FALLBACK = re.compile(
    r'\.get\(\s*["\'][a-z_]*'
    r'(?:pw|passwd|password|secret|token|api_key|unlock_code|access_code)'
    r'[a-z_]*["\']\s*,\s*["\'][^"\']+["\']'
)

#: Quét CHÉO mọi thư mục nguồn, không chỉ tầng giao diện. Sai sót gốc của commit
#: ``3827552`` là sửa ``config.py`` mà quên bản sao trong ``ui/`` — tức là lỗi đi
#: xuyên thư mục, nên phép quét cũng phải đi xuyên thư mục.
_SCANNED = (
    "ui", "presentation", "core", "infrastructure", "application", "domain",
    "mcp_servers", "providers", "security", "theme", "config.py", "state.py",
)


def test_khong_con_fallback_credential_trong_ma_nguon():
    """Không file nguồn nào được đặt credential làm giá trị mặc định của ``.get()``."""
    root = Path(__file__).resolve().parents[2]
    offenders = []
    for name in _SCANNED:
        target = root / name
        if target.is_file():
            files = [target]
        elif target.is_dir():
            files = [p for p in target.rglob("*.py") if "__pycache__" not in p.parts]
        else:                                   # thư mục bị đổi tên/xoá
            continue
        for path in files:
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if _CREDENTIAL_FALLBACK.search(line):
                    offenders.append(
                        f"{path.relative_to(root).as_posix()}:{lineno}: {line.strip()}")

    assert not offenders, "credential nằm trong mã nguồn:\n  " + "\n  ".join(offenders)


def test_phep_quet_thuc_su_nhin_thay_file():
    """Lưới an toàn cho bài trên: đổi tên thư mục làm nó quét rỗng mà vẫn xanh."""
    root = Path(__file__).resolve().parents[2]
    seen = sum(
        1 for name in _SCANNED
        for _ in ([root / name] if (root / name).is_file()
                  else (root / name).rglob("*.py") if (root / name).is_dir() else [])
    )
    assert seen > 200, f"chỉ quét được {seen} file — phạm vi quét đã hỏng"
