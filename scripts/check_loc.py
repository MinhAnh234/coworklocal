#!/usr/bin/env python3
"""Lines-of-Code (LOC) Quality Guard (EPIC R10 - CASAN Gate S).

Enforces the Single Responsibility Principle by ensuring that no production
Python file exceeds the configured limit (400 LOC).

Phạm vi quét là TOÀN BỘ cây mã production, không chỉ bốn gói Clean
Architecture: ``ui/``, ``core/``, ``providers/``, ``security/``,
``mcp_servers/`` và các module nằm thẳng ở thư mục gốc đều được tính. Trước
đợt mở rộng này, 18 file dài hơn 400 dòng (dài nhất 944) vẫn qua cổng chỉ vì
chúng nằm ngoài bốn gói kia.

18 file đó không thể sửa hết trong một lần, nên chúng nằm trong
``LEGACY_ALLOWANCE`` với trần riêng bằng đúng số dòng hiện tại — một bánh cóc
chỉ quay một chiều: nợ cũ được giữ nguyên nhưng không được phình thêm, và mỗi
lần file co bớt thì cổng in ra lời nhắc hạ con số xuống.
"""
from __future__ import annotations

import argparse
import ast
import io
import os
import sys
import tokenize
from pathlib import Path
from typing import List, Tuple

# Ensure stdout handles UTF-8 on Windows consoles without codec crash
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Toàn bộ cây mã production. Bốn gói Clean Architecture là phần cổng này canh
# từ đầu; ``ui``/``core``/``providers``/``security``/``mcp_servers`` được đưa
# vào sau đợt đối chiếu AS-IS/TO-BE — trước đó chúng nằm ngoài tầm quét, nên
# một file 944 dòng vẫn qua cổng chỉ vì nó không nằm trong bốn gói kia.
DEFAULT_TARGET_DIRS = [
    "domain", "application", "infrastructure", "presentation",
    "ui", "core", "providers", "security", "mcp_servers",
    # ``i18n/`` và ``theme/`` từng là 13 file rời nằm thẳng ở thư mục gốc nên
    # được quét theo diện "module gốc"; gom vào gói rồi thì phải khai ở đây,
    # không thì chúng lặng lẽ tuột khỏi tầm quét.
    "i18n", "theme",
]
DEFAULT_MAX_LINES = 400

#: Các file ``.py`` nằm thẳng ở thư mục gốc cũng được quét (không đệ quy) —
#: ``app.py``, ``state.py``, ``theme*.py``… đều là mã production.
SCAN_ROOT_MODULES = True

#: Nợ cũ: file đã dài hơn 400 dòng TỪ TRƯỚC khi cổng mở rộng sang ``ui``/
#: ``core``/``providers``. Giá trị là số dòng tại thời điểm ghi nhận và đóng
#: vai trò trần riêng của từng file — đây là bánh cóc CHỈ QUAY MỘT CHIỀU:
#:
#:   * file vượt quá trần riêng  -> cổng đỏ (đang làm nợ cũ tệ thêm)
#:   * file co xuống dưới trần   -> [INFO] nhắc hạ con số xuống
#:   * file co xuống <= 400 dòng -> [INFO] nhắc gỡ hẳn khỏi danh sách
#:
#: Không bao giờ thêm mục mới vào đây để làm cổng xanh trở lại: file mới viết
#: phải dưới 400 dòng ngay từ đầu. Nới một con số cũng vậy — cách duy nhất
#: đúng là tách file.
LEGACY_ALLOWANCE = {
    "ui/workspace_tab.py": 566,
    "ui/widgets.py": 466,
    "ui/task_editor_dialog.py": 627,
    "ui/accounts_tab.py": 559,
    "core/skills.py": 405,
    "core/chat_agent.py": 419,
    "ui/flow_dialog.py": 483,
    "core/tasks.py": 339,
    "core/co4e.py": 330,
    "core/task_executors.py": 347,
    "ui/help_agent_widget.py": 313,
    "core/structure_graph.py": 346,
    "ui/cowork_tab.py": 255,
    "providers/base.py": 224,
    "ui/co4e_tab.py": 180,
    "providers/openai_compat.py": 279,
    "core/doc_extract.py": 283,
    "ui/connectors_panel.py": 281,
}


def count_file_lines(file_path: Path) -> int:
    """Read a python file and return total physical line count."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        return len(content.splitlines())
    except Exception as exc:
        print(f"[WARN] Failed to read {file_path}: {exc}", file=sys.stderr)
        return 0


def iter_source_files(root_dir: Path, target_dirs: List[str]):
    """Sinh (đường dẫn tương đối, số dòng) cho mọi file production cần quét.

    Ngoài các gói trong ``target_dirs``, quét thêm các ``.py`` nằm thẳng ở thư
    mục gốc (``app.py``, ``state.py``, ``theme*.py``…) — chúng cũng là mã chạy
    thật nhưng không thuộc gói nào, nên trước đây không ai canh.
    """
    for target in target_dirs:
        dir_path = root_dir / target
        if not dir_path.is_dir():
            continue
        for current_root, dirnames, files in os.walk(dir_path):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for file_name in sorted(files):
                if file_name.endswith(".py"):
                    full = Path(current_root) / file_name
                    yield full.relative_to(root_dir).as_posix(), count_file_lines(full)

    if SCAN_ROOT_MODULES:
        for full in sorted(root_dir.glob("*.py")):
            yield full.name, count_file_lines(full)


def iter_code_sizes(root_dir: Path, target_dirs: List[str]):
    """Như :func:`iter_source_files` nhưng đếm DÒNG MÃ — dành cho bánh cóc."""
    for target in target_dirs:
        dir_path = root_dir / target
        if not dir_path.is_dir():
            continue
        for current_root, dirnames, files in os.walk(dir_path):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for file_name in sorted(files):
                if file_name.endswith(".py"):
                    full = Path(current_root) / file_name
                    yield full.relative_to(root_dir).as_posix(), count_code_lines(full)

    if SCAN_ROOT_MODULES:
        for full in sorted(root_dir.glob("*.py")):
            yield full.name, count_code_lines(full)


def count_code_lines(file_path: Path) -> int:
    """Số dòng MÃ của một file: bỏ docstring, chú thích và dòng trống.

    Dùng riêng cho bánh cóc ``LEGACY_ALLOWANCE``, không dùng cho trần 400 dòng.
    Lý do: bánh cóc có một câu hỏi duy nhất — "file này có đang ĐỂ THÊM
    VIỆC vào không?" — mà viết thêm một docstring thì không. Đếm dòng vật lý
    ở đây biến cổng thành thứ phạt người viết tài liệu, và cách dễ nhất để làm
    nó xanh lại sẽ là xoá bớt chú thích — đúng thứ không ai muốn.

    Trần 400 dòng thì VẪN đếm dòng vật lý: đó là hợp đồng đã chốt của cổng
    S từ đầu, đổi cách đo là âm thầm nới nó ra cho mọi file.
    """
    try:
        src = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        print(f"[WARN] Failed to read {file_path}: {exc}", file=sys.stderr)
        return 0

    skip: set = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return len(src.splitlines())
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", None)
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            skip.update(range(body[0].lineno, body[0].end_lineno + 1))

    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                skip.add(tok.start[0])
    except (tokenize.TokenError, IndentationError):
        pass

    return sum(1 for i, line in enumerate(src.splitlines(), 1)
               if i not in skip and line.strip())


def scan_directories(
    root_dir: Path, target_dirs: List[str], max_lines: int, verbose: bool = False
) -> Tuple[int, List[Tuple[str, int]]]:
    """Quét cây mã production, đối chiếu với trần chung và trần riêng của nợ cũ.

    Trả về ``(số file đã quét, danh sách vi phạm)``. Một file bị tính là vi
    phạm khi nó vượt trần chung VÀ không có trong ``LEGACY_ALLOWANCE``, hoặc
    khi nó có trong danh sách nợ cũ nhưng đã phình quá con số ghi ở đó.
    """
    total_files = 0
    violations: List[Tuple[str, int]] = []
    code_sizes = dict(iter_code_sizes(root_dir, target_dirs))

    for rel_path, lines in iter_source_files(root_dir, target_dirs):
        total_files += 1
        if verbose:
            print(f"  {rel_path}: {lines} lines")

        allowance = LEGACY_ALLOWANCE.get(rel_path)
        if allowance is None:
            if lines > max_lines:
                violations.append((rel_path, lines))
        else:
            # Nợ cũ: đo bằng dòng mã, không đo bằng dòng vật lý.
            code = code_sizes.get(rel_path, lines)
            if code > allowance:
                violations.append((rel_path, code))

    return total_files, violations


def audit_legacy(root_dir: Path, target_dirs: List[str], max_lines: int) -> List[str]:
    """Các dòng nhắc về ``LEGACY_ALLOWANCE`` — chỉ để báo, không làm cổng đỏ.

    Bánh cóc chỉ có nghĩa khi con số được siết lại mỗi lần file co bớt; nếu
    không ai nhắc thì nó đứng yên mãi ở mức của lần ghi đầu tiên.

    Hai thước đo, mỗi thước trả lời một câu khác nhau:

    * **Gỡ hẳn khỏi danh sách** chỉ đúng khi file đã xuống dưới trần đo bằng
      DÒNG VẬT LÝ — vì đó mới là thước của trần 400. Nhắc gỡ một file 950
      dòng chỉ vì phần mã của nó dưới 400 là lời khuyên sai: gỡ xong cổng đỏ
      ngay.
    * **Hạ con số xuống** đo bằng DÒNG MÃ, cùng thước với chính bánh cóc.
    """
    code = dict(iter_code_sizes(root_dir, target_dirs))
    physical = dict(iter_source_files(root_dir, target_dirs))
    notes: List[str] = []
    for rel_path, allowance in sorted(LEGACY_ALLOWANCE.items()):
        lines = code.get(rel_path)
        if lines is None:
            notes.append(f"{rel_path}: file khong con ton tai - go khoi LEGACY_ALLOWANCE")
        elif physical.get(rel_path, lines) <= max_lines:
            notes.append(f"{rel_path}: nay chi {physical[rel_path]} dong - go khoi LEGACY_ALLOWANCE")
        elif lines < allowance:
            notes.append(f"{rel_path}: {lines} dong ma (tran dang ghi {allowance}) - ha con so xuong {lines}")
    return notes


def main() -> int:
    """CLI entry point for the LOC guard script."""
    parser = argparse.ArgumentParser(
        description="Verify that production source files do not exceed the LOC ceiling."
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=DEFAULT_MAX_LINES,
        help=f"Maximum allowed lines per file (default: {DEFAULT_MAX_LINES})",
    )
    parser.add_argument(
        "--dirs",
        nargs="+",
        default=DEFAULT_TARGET_DIRS,
        help=f"Target directories to scan (default: {' '.join(DEFAULT_TARGET_DIRS)})",
    )
    parser.add_argument(
        "--root",
        type=str,
        default=str(Path(__file__).resolve().parent.parent),
        help="Root repository directory",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output listing all scanned files",
    )

    args = parser.parse_args()
    root_dir = Path(args.root).resolve()

    print("=" * 70)
    print(f"CASAN Guard 'S' (Single Responsibility): Checking file length <= {args.max_lines} LOC")
    print(f"Scanning target directories: {args.dirs}")
    print("=" * 70)

    total_files, violations = scan_directories(
        root_dir=root_dir,
        target_dirs=args.dirs,
        max_lines=args.max_lines,
        verbose=args.verbose,
    )

    notes = audit_legacy(root_dir, args.dirs, args.max_lines)
    if notes:
        print(f"\n[INFO] {len(notes)} muc trong LEGACY_ALLOWANCE co the siet lai:")
        for note in notes:
            print(f"  - {note}")

    if violations:
        print(f"\n[FAIL] Found {len(violations)} oversized file(s) (> {args.max_lines} LOC):")
        for file_path, lines in sorted(violations, key=lambda x: x[1], reverse=True):
            allowance = LEGACY_ALLOWANCE.get(file_path)
            if allowance:
                print(f"  ❌ {file_path}: {lines} dong ma - no cu ghi la {allowance}, "
                      f"nay phinh them {lines - allowance}. Tach bot, dung noi con so.")
            else:
                print(f"  ❌ {file_path}: {lines} lines (exceeds limit by {lines - args.max_lines})")
        print("\nAction Required: Refactor oversized files into smaller single-responsibility modules.")
        return 1

    legacy = len(LEGACY_ALLOWANCE)
    print(f"\n[PASS] All {total_files} production files in {args.dirs} satisfy <= {args.max_lines} LOC limit "
          f"({legacy} file no cu duoc mien tru, khong file nao phinh them).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
