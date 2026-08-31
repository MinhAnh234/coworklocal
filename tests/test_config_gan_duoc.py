"""Mọi chỗ trong repo gán ``config.X = ...`` thì repository phải nhận được.

Bài này sinh ra từ một lỗi thật ngày 26/08.

R02 tráo ``config.py::AppConfig`` bằng ``JsonConfigRepository``. Trước khi
tráo tôi có đối chiếu API: đếm đủ 34/34 thành viên công khai, không thiếu cái
nào, nên kết luận là thay được. Đối chiếu đó **chỉ so tên**, không so việc một
``property`` có setter hay không.

``AppConfig`` cũ là dataclass, ``config.language = "vi"`` chạy bình thường.
Repository để ``language`` là property chỉ đọc, gán vào là ``AttributeError``.
Ba chỗ trong ``app.py`` đang gán như thế: đổi ngôn ngữ, đổi giao diện, đổi
provider trên thanh bên.

Điều làm nó khó thấy: cả ba đều nằm trong slot của Qt, mà Qt **nuốt ngoại lệ
trong slot**. Không có traceback, không có thông báo — người dùng bấm đổi ngôn
ngữ thì không có gì xảy ra. Bộ test đơn vị vẫn 709 xanh; chỉ ``check_nav`` bắt
được vì nó bấm thật vào combo rồi kiểm ngôn ngữ có đổi không.

Nên bài này đi ngược từ mã nguồn: tìm mọi chỗ gán, rồi thử gán thật.
"""
from __future__ import annotations

import copy
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

#: ``config.X = ...`` nhưng không phải ``==``.
GAN = re.compile(r"\bconfig\.([a-z_][a-z_0-9]*)\s*=(?!=)")

#: Không phải thuộc tính cấu hình — là chỗ chứa chính đối tượng config.
BO_QUA = {"data", "config"}


def _cho_gan() -> set[str]:
    out = subprocess.run(["git", "ls-files", "*.py"], cwd=REPO,
                         capture_output=True, text=True, encoding="utf-8",
                         errors="replace").stdout.split()
    ten: set[str] = set()
    for f in out:
        p = REPO / f
        if not p.is_file():
            continue
        for m in GAN.finditer(p.read_text(encoding="utf-8", errors="replace")):
            if m.group(1) not in BO_QUA and not m.group(1).startswith("_"):
                ten.add(m.group(1))
    return ten


def _repo(tmp_path):
    from cowork_local.config import DEFAULT_CONFIG
    from cowork_local.infrastructure.config.json_config_repository import (
        JsonConfigRepository,
    )
    return JsonConfigRepository.from_data(copy.deepcopy(DEFAULT_CONFIG),
                                          tmp_path / "config.json")


def test_tim_duoc_cho_gan():
    """Bảo vệ chính bài test: biểu thức tìm kiếm hỏng thì nó lặng lẽ xanh."""
    ten = _cho_gan()
    assert ten, "không tìm thấy chỗ nào gán config.X — kiểm lại GAN"
    assert "language" in ten, f"phải thấy config.language (thấy: {sorted(ten)})"


def test_moi_thuoc_tinh_bi_gan_deu_gan_duoc(tmp_path):
    cfg = _repo(tmp_path)
    hong = []
    for ten in sorted(_cho_gan()):
        if not hasattr(type(cfg), ten) and not hasattr(cfg, ten):
            continue          # thuộc tính của lớp khác, không phải config
        cu = getattr(cfg, ten, None)
        try:
            setattr(cfg, ten, cu)
        except AttributeError:
            hong.append(ten)

    assert not hong, (
        "Repository không nhận gán, nhưng trong mã nguồn có chỗ gán:\n  "
        + "\n  ".join("config.%s = ..." % t for t in hong)
        + "\nQt nuốt AttributeError trong slot, nên chỗ đó sẽ im lặng không "
          "làm gì. Thêm @<tên>.setter vào JsonConfigRepository."
    )


@pytest.mark.parametrize("ten,gia_tri", [("language", "ja"), ("theme", "light"),
                                         ("active_provider", "ollama")])
def test_ba_cho_app_py_dang_gan(tmp_path, ten, gia_tri):
    """Chốt riêng ba cái app.py gán, để bài trên có hỏng thì vẫn còn lưới."""
    cfg = _repo(tmp_path)
    setattr(cfg, ten, gia_tri)
    assert getattr(cfg, ten) == gia_tri
