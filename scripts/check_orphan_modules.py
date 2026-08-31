#!/usr/bin/env python3
"""Cổng chất lượng: không để module production nào không ai import (CASAN Gate O).

Vì sao cần cổng này
-------------------
Ba cổng đang có (Clean Architecture / Secrets / LOC) đều **không bắt được mã
chết**: một file không ai import vẫn qua cả ba, vì nó đúng chiều phụ thuộc,
không chứa credential, và ngắn hơn 400 dòng. Đợt kiểm chứng ngày 29/08 tìm ra
**1.400 dòng mã trùng lặp chết** lọt qua đúng theo cách đó — hai bản tách song
song của cùng một god-file cùng được giữ lại sau một lần merge, trong đó hai
file còn không import nổi (``GraphQaMixin`` không tồn tại,
``ui.calendar_view`` đã bị xoá). Không ai phát hiện vì không có gì đi tìm.

Cách làm
--------
Dựng đồ thị import tĩnh bằng AST, bắt đầu từ ``__init__`` / ``__main__`` /
``app``, đi theo cả import tuyệt đối lẫn tương đối, kể cả import nằm trong thân
hàm (mã này dùng import muộn rất nhiều). Import một module con cũng chạy
``__init__.py`` của mọi gói cha, nên các gói cha đó cũng được coi là tới được.

Module không tới được mà KHÔNG nằm trong ``ALLOWLIST`` thì cổng đỏ. Hai
ngoại lệ tự động, để danh sách miễn trừ không phải chép lại cùng một lý do
nhiều lần: ``__init__.py`` của một gói mà mọi thành viên đều dormant, và
module chỉ được chính mã dormant đã miễn trừ import.

Seam chưa nối dây
------------------
Một phần ``ALLOWLIST`` là *seam*: hợp đồng dựng trước để hai nhóm làm song
song, chờ bên kia nối vào. Những file đó mang nhãn ``SEAM · dựng <ngày>``
trong docstring đầu file, và cổng này đếm tuổi của chúng. Quá
``SEAM_MAX_AGE_DAYS`` thì in [WARN] — chỉ nhắc, không làm cổng đỏ.

Danh sách miễn trừ
------------------
``ALLOWLIST`` là mã dormant đã có TỪ TRƯỚC đợt refactor (xem
``docs/architecture/dormant-code.md``) cộng các seam đã dựng nhưng chưa nối
dây. Đây là danh sách **chỉ được co lại**: xoá hoặc nối dây một mục thì gỡ nó
khỏi đây, đừng bao giờ thêm mục mới để làm cổng xanh trở lại.

Chạy:  python scripts/check_orphan_modules.py
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE = "cowork_local"

#: Không phải mã production — không quét.
SKIP_TOP = {
    ".git", ".gitea", ".vibeflow-preview", "__pycache__", "assets", "config",
    "docs", "scripts", "skill_library", "slides", "tests", "tools",
}

#: Điểm bắt đầu: mọi thứ tới được từ đây là mã đang sống.
ROOTS = (PACKAGE, f"{PACKAGE}.__main__", f"{PACKAGE}.app")

#: Bao nhiêu ngày thì một seam chưa nối dây đáng được nhắc lại.
#:
#: Seam là hợp đồng dựng trước để hai nhóm làm song song — hợp lý trong vài
#: tuần, nhưng quá lâu thì nó không còn là hợp đồng nữa mà thành mã chết có lời
#: biện hộ. 30 ngày là một chu kỳ epic của dự án này: qua một chu kỳ mà vẫn
#: chưa ai nối thì phải quyết — nối, hoặc xoá.
#:
#: Chỉ nhắc, KHÔNG làm cổng đỏ: để nó đỏ thì CI sẽ đỏ vào một buổi sáng mà
#: không ai sửa gì cả, và cách nhanh nhất để xanh lại là sửa ngày.
SEAM_MAX_AGE_DAYS = 30

#: Nhận dạng nhãn seam trong docstring đầu file.
_SEAM_RE = re.compile(r"SEAM \u00b7 d\u1ef1ng (\d{4})-(\d{2})-(\d{2})")

#: Mã dormant được chấp nhận, kèm lý do. CHỈ ĐƯỢC CO LẠI.
ALLOWLIST: Dict[str, str] = {
    # --- dormant từ trước refactor (docs/architecture/dormant-code.md) -----
    "core/account_excel.py": "quản lý tài khoản — chưa bật, dormant từ trước R01",
    "core/accounts.py": "quản lý tài khoản — chưa bật, dormant từ trước R01",
    "core/codebase_memory_ui.py": "phần UI của codebase-memory — chưa bật",
    "core/custom_agents.py": "bản agent tự tạo cũ, đã thay bằng core/co4e.py",
    "core/graph_server.py": "máy chủ HTTP phục vụ đồ thị D3 — chỉ dùng khi bật cờ",
    "core/groups.py": "nhóm người dùng — chưa bật, dormant từ trước R01",
    "security/action_validator.py": "lớp bọc mỏng quanh command_risk_classifier",
    "security/attachment_validator.py": "lớp bọc mỏng quanh command_risk_classifier",
    "security/prompt_validator.py": "lớp bọc mỏng quanh command_risk_classifier",
    "ui/accounts_tab.py": "màn quản lý tài khoản — chưa bật",
    "ui/agent_manager_tab.py": "đã thay bằng presentation/monitoring/tabs/agents_admin_tab.py",
    "ui/flow_dialog.py": "trình sửa luồng cũ, đã thay bằng Co4E Studio",
    "ui/login_dialog.py": "bản này không có lớp đăng nhập",
    "ui/mcp_servers_dialog.py": "đã thay bằng ui/connectors_panel.py",
    "ui/skill_manager_tab.py": "đã thay bằng ui/skills_dialog.py",
    # --- chạy bằng tiến trình con, không ai import ------------------------
    "mcp_servers/ms365_server.py": "chạy bằng subprocess (state.py)",
    "mcp_servers/project_context_server.py": "chạy bằng subprocess",
    "mcp_servers/project_context/server.py": "chạy bằng subprocess",
    "mcp_servers/project_context/foundation.py": "gói MCP chạy bằng subprocess",
    "mcp_servers/project_context/registry.py": "gói MCP chạy bằng subprocess",
    "mcp_servers/project_context/runtime.py": "gói MCP chạy bằng subprocess",
    "mcp_servers/project_context/providers/change.py": "gói MCP chạy bằng subprocess",
    "mcp_servers/project_context/providers/issue.py": "gói MCP chạy bằng subprocess",
    "mcp_servers/project_context/providers/knowledge.py": "gói MCP chạy bằng subprocess",
    "mcp_servers/project_context/tools/change_context.py": "gói MCP chạy bằng subprocess",
    "mcp_servers/project_context/tools/issue_context.py": "gói MCP chạy bằng subprocess",
    "mcp_servers/project_context/tools/knowledge_search.py": "gói MCP chạy bằng subprocess",
    # --- seam đã dựng, chưa nối dây (xem F-05 trong báo cáo đối chiếu) ----
    "application/workflows/co4e_workflow_service.py": "R07-T06 — bootstrap chưa gọi build_co4e_tab",
    "presentation/co4e/co4e_tab.py": "factory chờ bootstrap.py nối, hạn đã ghi trong file",
    "domain/security/tool_policy.py": "hình dạng dữ liệu, chờ nối vào ToolPolicyGateway",
    "domain/workflows/run_record.py": "DTO, dùng khi Co4EWorkflowService được nối dây",
    "domain/agents/agent_event_codec.py": "shim tạm, bỏ khi chat_panel dùng event có kiểu",
    "infrastructure/filesystem/execution_workspace.py": "R06-T03 — chưa có call site",
    "infrastructure/sandbox/sandbox_capabilities.py": "ma trận năng lực sandbox, chưa nối",
    "infrastructure/config/settings_facade.py": "R02-T03 — chưa có call site",
    "infrastructure/config/config_repository.py": "Protocol, chỉ dùng làm chú thích kiểu",
    # --- vỏ chuyển tiếp (strangler-fig) ------------------------------------
    # Vỏ chuyển tiếp tồn tại để giữ ĐƯỜNG IMPORT CŨ chạy được, nên việc mã mới
    # không import nó là trạng thái ĐÚNG chứ không phải thiếu sót. Ba vỏ còn
    # lại (ui/chat_panel.py, ui/monitoring_tab.py, core/tools.py) hiện vẫn tới
    # được vì presentation/ đang nhập ngược qua chúng — đi vòng như thế tạo chu
    # trình import, và khi nào gỡ nốt thì chúng cũng xuống đây.
    "ui/composer.py": "vỏ chuyển tiếp R08-T02, giữ đường import cũ",
    # --- hạ tầng test / công cụ -------------------------------------------
    "conftest.py": "pytest tự nạp, không ai import",
}


def _discover() -> Dict[str, str]:
    """{tên module đầy đủ: đường dẫn tương đối} cho mọi file production."""
    out: Dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        rel_dir = os.path.relpath(dirpath, REPO_ROOT).replace("\\", "/")
        if rel_dir == ".":
            rel_dir = ""
            dirnames[:] = [d for d in dirnames if d not in SKIP_TOP]
        else:
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in filenames:
            if not name.endswith(".py"):
                continue
            rel = f"{rel_dir}/{name}" if rel_dir else name
            parts = rel[:-3].split("/")
            if parts[-1] == "__init__":
                parts = parts[:-1]
            out[".".join([PACKAGE] + parts) if parts else PACKAGE] = rel
    return out


def _targets(module: str, node: ast.AST, modules: Dict[str, str]) -> List[str]:
    """Các module trong gói mà một câu lệnh import trỏ tới."""
    names: List[str] = []
    if isinstance(node, ast.Import):
        names = [a.name for a in node.names]
    elif isinstance(node, ast.ImportFrom):
        if node.level:
            parts = module.split(".")
            # gói (__init__) tự nó là tiền tố; module thường thì lấy gói cha
            if modules.get(module, "").endswith("__init__.py"):
                pkg = parts
            else:
                pkg = parts[:-1]
            up = node.level - 1
            if up:
                pkg = pkg[: len(pkg) - up]
            base = ".".join(pkg)
            head = f"{base}.{node.module}" if node.module else base
            names = [head] + [f"{head}.{a.name}" for a in node.names]
        elif node.module:
            names = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
    resolved = []
    for n in names:
        if n in modules:
            resolved.append(n)
        elif n.rsplit(".", 1)[0] in modules:
            resolved.append(n.rsplit(".", 1)[0])
    return resolved


def _reach(modules: Dict[str, str], edges: Dict[str, Set[str]],
           roots) -> Set[str]:
    """Tập module tới được từ ``roots`` theo đồ thị import."""
    seen: Set[str] = set()
    stack = [r for r in roots if r in modules]
    while stack:
        module = stack.pop()
        if module in seen:
            continue
        seen.add(module)
        stack.extend(edges.get(module, ()))
        # Import một module con cũng chạy __init__.py của mọi gói cha.
        parts = module.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[:i])
            if parent in modules and parent not in seen:
                stack.append(parent)
    return seen


def find_orphans() -> List[str]:
    """Đường dẫn các module production không tới được từ điểm bắt đầu."""
    modules = _discover()
    edges: Dict[str, Set[str]] = {}
    for module, rel in modules.items():
        try:
            tree = ast.parse((REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            edges[module] = set()
            continue
        found: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                found.update(_targets(module, node, modules))
        edges[module] = found

    seen = _reach(modules, edges, ROOTS)
    return sorted(modules[m] for m in set(modules) - seen)


def find_dormant_reachable() -> Set[str]:
    """Module chỉ tới được từ một mục trong ``ALLOWLIST``.

    Một module mà người import duy nhất là mã dormant đã được miễn trừ thì
    dormant vì ĐÚNG LÝ DO ẤY — bắt nó phải có dòng miễn trừ riêng chỉ nhân đôi
    cùng một thông tin, và tệ hơn là khiến người ta ngại tách file trong vùng
    dormant. Đổi lại, khi mục dormant kia được nối dây hoặc bị xoá, cả nhánh
    này tự động theo — sống theo hoặc bị báo lên, không có dòng miễn trừ cũ
    nào ở lại che mắt.
    """
    modules = _discover()
    rel_to_mod = {rel: mod for mod, rel in modules.items()}
    edges: Dict[str, Set[str]] = {}
    for module, rel in modules.items():
        try:
            tree = ast.parse((REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            edges[module] = set()
            continue
        found: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                found.update(_targets(module, node, modules))
        edges[module] = found

    dormant_roots = [rel_to_mod[rel] for rel in ALLOWLIST if rel in rel_to_mod]
    from_real = _reach(modules, edges, ROOTS)
    from_dormant = _reach(modules, edges, dormant_roots)
    # Bỏ chính các mục ALLOWLIST — chúng đã có dòng miễn trừ riêng, kể lại
    # ở đây chỉ làm nhiễu.
    return {modules[m] for m in from_dormant - from_real} - set(ALLOWLIST)


def seam_ages(today: Optional[date] = None) -> List[Tuple[str, int, bool]]:
    """(đường dẫn, số ngày dormant, có nhãn không) cho mọi seam trong ALLOWLIST.

    Seam được nhận ra bằng chính nhãn ``SEAM · dựng <ngày>`` trong docstring
    đầu file chứ không bằng một danh sách thứ hai ở đây: hai danh sách là hai
    chỗ phải nhớ cập nhật, và chỗ thứ hai bao giờ cũng là chỗ bị quên.

    Ngày trong nhãn là ngày file được thêm vào repo (lấy từ git lúc đặt nhãn),
    không phải một hạn ai đó tự đặt.
    """
    today = today or date.today()
    out: List[Tuple[str, int, bool]] = []
    for rel in sorted(ALLOWLIST):
        path = REPO_ROOT / rel
        if not path.is_file():
            continue
        head = path.read_text(encoding="utf-8", errors="replace")[:4000]
        m = _SEAM_RE.search(head)
        if m is None:
            continue
        made = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        age = (today - made).days
        out.append((rel, age, age > SEAM_MAX_AGE_DAYS))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-allowed", action="store_true",
                        help="In danh sách miễn trừ rồi thoát")
    args = parser.parse_args()

    if args.list_allowed:
        for rel, why in sorted(ALLOWLIST.items()):
            print(f"  {rel:62} {why}")
        return 0

    print("=" * 70)
    print("CASAN Guard 'O' (Orphan): module production phải có ít nhất 1 nơi import")
    print("=" * 70)

    orphans = find_orphans()
    orphan_set = set(orphans)

    def _dormant_package(rel: str) -> bool:
        """``__init__.py`` của một gói mà KHÔNG module nào bên trong tới được.

        Gói kiểu đó dormant vì thành viên của nó dormant — báo riêng nó ra chỉ
        nhân đôi cùng một phát hiện. Gói còn dù chỉ một module đang sống thì
        ``__init__.py`` cũng phải sống theo (import module con chạy nó), nên
        luật này không che được mã chết thật.
        """
        if not rel.endswith("__init__.py"):
            return False
        pkg = rel[: -len("__init__.py")]
        members = [m for m in _discover().values()
                   if m.startswith(pkg) and m != rel]
        return bool(members) and all(
            m in orphan_set or m in ALLOWLIST for m in members)

    via_dormant = find_dormant_reachable()
    unexpected = [o for o in orphans
                  if o not in ALLOWLIST
                  and o not in via_dormant
                  and not _dormant_package(o)]
    stale = sorted(set(ALLOWLIST) - orphan_set)

    if stale:
        print(f"\n[INFO] {len(stale)} mục trong ALLOWLIST nay đã có nơi import — gỡ khỏi danh sách:")
        for rel in stale:
            print(f"  - {rel}")

    if unexpected:
        print(f"\n[FAIL] {len(unexpected)} module production không ai import:")
        for rel in unexpected:
            print(f"  x {rel}")
        print("\nXoá chúng, hoặc nối dây, hoặc thêm vào ALLOWLIST kèm lý do")
        print("(scripts/check_orphan_modules.py) nếu đó là mã dormant có chủ ý.")
        return 1

    seams = seam_ages()
    overdue = [(rel, age) for rel, age, late in seams if late]
    if overdue:
        print(f"\n[WARN] {len(overdue)}/{len(seams)} seam đã dựng quá {SEAM_MAX_AGE_DAYS} "
              f"ngày mà chưa nối dây — nối, hoặc xoá:")
        for rel, age in sorted(overdue, key=lambda x: -x[1]):
            print(f"  ! {rel}: {age} ngày")
    elif seams:
        oldest = max(age for _, age, _ in seams)
        print(f"\n[INFO] {len(seams)} seam chưa nối dây, cái lâu nhất {oldest} ngày "
              f"(nhắc khi quá {SEAM_MAX_AGE_DAYS}).")

    total = len(_discover())
    # __init__.py của gói toàn thành viên dormant đã có luật riêng ở trên —
    # không kể lại lần nữa.
    implicit = sorted(r for r in via_dormant if not _dormant_package(r))
    if implicit:
        print(f"\n[INFO] {len(implicit)} module chỉ được mã dormant import — "
              f"dormant theo cùng lý do, không cần dòng miễn trừ riêng:")
        for rel in implicit:
            print(f"  - {rel}")
    print(f"\n[PASS] {total - len(orphans)}/{total} module production đều có nơi import "
          f"({len(orphans)} mục dormant đã được miễn trừ).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
