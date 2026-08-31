"""Smoke test cho ``presentation.co4e.co4e_tab.build_co4e_tab`` — gọi thật
factory, dựng thật ``Co4ETab``, xác nhận nó không vỡ.

Vì sao chạy trong tiến trình con thay vì import thẳng trong tiến trình pytest
chính: ``CONFIG_DIR`` (config.py) và ``CO4E_DIR`` (core/co4e.py) đều là hằng số
module tính MỘT LẦN lúc import từ ``Path.home()``. Nhiều file test khác trong
bộ này (chạy trước theo thứ tự collect) đã import ``cowork_local.config``/
``cowork_local.core.co4e`` với HOME thật rồi — monkeypatch thuộc tính module
(cách ``tests/characterization/test_co4e_run_manager_behavior.py`` dùng cho
``CO4E_DIR``) chỉ vá được đúng chỗ đó, còn ``AppConfig.load()`` có thêm một bẫy
riêng: tham số mặc định ``path: Path = CONFIG_PATH`` được gán MỘT LẦN lúc định
nghĩa hàm, nên monkeypatch ``CONFIG_PATH`` sau đó không đổi được giá trị mặc
định đã đóng băng — gọi ``AppConfig.load()`` không tham số vẫn đọc file thật
dù đã vá module. Dựng ``Co4ETab`` thật kéo theo cả hai đường trên (và có thể
còn đường khác chưa biết, vì lớp này 2000+ dòng). Cô lập bằng biến môi trường
``HOME``/``USERPROFILE`` TRƯỚC bất kỳ import nào, trong một tiến trình con
sạch hoàn toàn, né được toàn bộ lớp bẫy này một lần — không cần biết hết mọi
hằng số tính lúc import ở đâu trong file 2000+ dòng đó.

Bắt được gì: đổi sai độ sâu dấu chấm ở import tương đối trong
``presentation/co4e/co4e_tab.py`` (``from ...ui.co4e_tab import Co4ETab``),
đổi chữ ký ``Co4ETab.__init__`` mà quên sửa lệnh gọi trong factory, hoặc
factory trả sai kiểu/sai ``ctx`` — không có test nào khác trong bộ này gọi
``build_co4e_tab()``, nên đây là lưới an toàn DUY NHẤT cho hàm này.

KHÔNG chạm dữ liệu thật: sandbox trống hoàn toàn, không copy
``~/.cowork_local`` thật (khác ``tools/capture_screens.py::_isolate_home()`` —
ở đó cố tình copy để chụp ảnh có dữ liệu mẫu; ở đây không cần, càng sạch càng
tốt cho một smoke test).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPO_PARENT = REPO_ROOT.parent

_SMOKE_SCRIPT = """
import sys
sys.path.insert(0, {repo_parent!r})

from PySide6.QtWidgets import QApplication, QWidget

from cowork_local.config import AppConfig, CONFIG_DIR
from cowork_local.state import AppContext
from cowork_local.presentation.co4e.co4e_tab import build_co4e_tab

sandbox = sys.argv[1]
assert str(CONFIG_DIR).startswith(sandbox), "khong co lap: CONFIG_DIR=" + str(CONFIG_DIR)

app = QApplication([])
ctx = AppContext(AppConfig.load())


class _FakeWorkflowService:
    \"\"\"Chua dung toi trong than ham build_co4e_tab hien tai (xem docstring
    cua factory) - chi can mot doi tuong bat ky de kiem factory nhan dung
    tham so bat buoc thu hai.\"\"\"


widget = build_co4e_tab(ctx, _FakeWorkflowService())
assert isinstance(widget, QWidget), "khong phai QWidget: " + repr(type(widget))
assert widget.ctx is ctx, "factory khong gan dung ctx cho widget tra ve"
print("SMOKE_OK")
"""


def test_build_co4e_tab_dung_that_va_gan_dung_ctx(tmp_path):
    sandbox = tmp_path / "home"
    sandbox.mkdir()

    env = dict(os.environ)
    env["HOME"] = str(sandbox)
    env["USERPROFILE"] = str(sandbox)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env.pop("HOMEDRIVE", None)
    env.pop("HOMEPATH", None)

    script = _SMOKE_SCRIPT.format(repo_parent=str(REPO_PARENT))
    result = subprocess.run(
        [sys.executable, "-c", script, str(sandbox)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, (
        f"smoke build_co4e_tab that bai (exit {result.returncode}):\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    assert "SMOKE_OK" in result.stdout, result.stdout

    # Sandbox khong duoc dung: chua co gi ghi vao no truoc khi tien trinh con
    # chay (con AppConfig.load() khong ghi gi ca - chi save() moi ghi).
    assert not (sandbox / ".cowork_local").exists(), (
        "AppConfig.load() khong duoc tu tao thu muc config that trong sandbox"
    )
