"""Không file mã nguồn nào được nằm ngoài repo vì `.gitignore`.

Bài này sinh ra từ một lỗi thật, mất hai ngày mới lộ:

``.gitignore`` dòng 31 ghi ``secrets/`` — mẫu **không neo**, nên git bỏ qua
mọi thư mục tên ``secrets`` ở mọi độ sâu, kể cả ``infrastructure/secrets/``
vốn là **mã nguồn**. Ba file trong đó chưa bao giờ lên repo. Máy người viết
vẫn chạy 150 test xanh, nhưng ai clone sạch về thì 4 file test đỏ ngay lúc
thu thập.

Trên máy đã có file thì không cách nào nhận ra: ``pytest`` đọc đĩa, không đọc
git. Nên phải hỏi thẳng git.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: Thư mục chứa mã nguồn của ứng dụng — file .py ở đây bắt buộc phải vào repo.
SOURCE_DIRS = ["domain", "application", "infrastructure", "presentation",
               "adapters", "core", "ui", "providers", "scripts", "tools", "tests"]


def _git(*args: str) -> str:
    out = subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                         text=True, encoding="utf-8", errors="replace")
    return out.stdout


def test_khong_file_py_nao_bi_gitignore_nuot():
    """File .py có trên đĩa nhưng git không thấy — vừa chưa theo dõi, vừa bị
    bỏ qua. Đó chính là hình dạng của lỗi ``secrets/``."""
    existing = []
    for d in SOURCE_DIRS:
        root = REPO / d
        if root.is_dir():
            existing.append(d)
    assert existing, "không thấy thư mục mã nguồn nào — kiểm lại SOURCE_DIRS"

    ignored = _git("ls-files", "--others", "--ignored", "--exclude-standard",
                   "--", *existing).splitlines()
    ignored_py = [p for p in ignored
                  if p.endswith(".py") and "__pycache__" not in p]

    assert not ignored_py, (
        "File mã nguồn bị .gitignore nuốt — clone sạch sẽ thiếu:\n  "
        + "\n  ".join(ignored_py)
        + "\nChạy `git check-ignore -v <file>` để biết dòng nào gây ra."
    )


def test_khong_file_py_nao_bi_bo_quen_chua_theo_doi():
    """Chưa bị ignore nhưng cũng chưa `git add` — quên, không phải cố ý."""
    untracked = _git("ls-files", "--others", "--exclude-standard").splitlines()
    forgotten = [p for p in untracked
                 if p.endswith(".py")
                 and p.split("/")[0] in SOURCE_DIRS
                 and "__pycache__" not in p]

    assert not forgotten, (
        "File mã nguồn chưa được git add — clone sạch sẽ thiếu:\n  "
        + "\n  ".join(forgotten)
    )


def test_moi_module_duoc_import_deu_co_trong_repo():
    """Bắt theo hướng ngược: đi từ những gì code THỰC SỰ import.

    Hai bài trên quét theo thư mục; bài này bắt cả trường hợp file nằm ngoài
    danh sách đó mà vẫn được import.
    """
    tracked = set(_git("ls-files").splitlines())
    missing = []
    for d in ("domain", "application", "infrastructure", "adapters"):
        root = REPO / d
        if not root.is_dir():
            continue
        for f in root.rglob("*.py"):
            rel = f.relative_to(REPO).as_posix()
            if "__pycache__" in rel:
                continue
            if rel not in tracked:
                missing.append(rel)

    assert not missing, (
        "Module thuộc kiến trúc mới nhưng không có trong repo:\n  "
        + "\n  ".join(missing)
    )
