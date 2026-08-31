"""Không thư mục nào ở gốc repo được trùng tên module thư viện chuẩn.

Bài này sinh ra từ một lỗi thật: kế hoạch refactor đặt tên một tầng là
``platform/``, và ngay khi tạo thư mục đó thì mọi script chạy từ gốc repo —
``python tools/check_*.py``, ``python scripts/audit_security.py``, 26 file tất
cả — đều nạp nhầm ``platform/`` thay cho ``platform`` của Python. ``keyring``
chết ngay với ``AttributeError: module 'platform' has no attribute 'system'``.

Kiểm bằng tên chứ không phải bằng cách thử import: import chỉ hỏng khi có ai
đó thật sự dùng module bị che, nên nó im lặng cho tới lúc muộn.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: Không tính: đây là thư mục dữ liệu/tài liệu, không phải package Python.
NOT_PACKAGES = {".git", ".gitea", ".vibeflow-preview", "docs", "assets",
                "__pycache__", ".pytest_cache", "cowork-local-gitea",
                ".cowork_history", ".cowork_local"}


def _top_level_packages() -> list[str]:
    return [d.name for d in REPO.iterdir()
            if d.is_dir() and d.name not in NOT_PACKAGES
            and (d / "__init__.py").exists()]


def test_khong_package_nao_che_khuat_thu_vien_chuan():
    stdlib = set(sys.stdlib_module_names)
    clashes = [name for name in _top_level_packages() if name in stdlib]
    assert not clashes, (
        "Thư mục ở gốc repo trùng tên module thư viện chuẩn: "
        + ", ".join(sorted(clashes))
        + ". Chạy script từ gốc repo sẽ nạp nhầm thư mục này. Đổi tên thư mục."
    )


def test_import_duoc_stdlib_khi_chay_tu_goc_repo():
    """Bài trên bắt bằng tên; bài này bắt bằng hành vi thật.

    Chạy tiến trình con với thư mục làm việc là gốc repo — đúng cách 26 script
    trong ``tools/`` và ``scripts/`` được gọi.
    """
    import subprocess

    snippet = (
        "import platform, json, types, io\n"
        "assert 'site-packages' not in platform.__file__\n"
        "assert platform.system(), 'platform.system() phải trả về tên hệ điều hành'\n"
        "import keyring\n"
        "print('OK')\n"
    )
    out = subprocess.run([sys.executable, "-c", snippet], cwd=REPO,
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert "OK" in out.stdout
