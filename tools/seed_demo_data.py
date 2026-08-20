"""Populate a CoworkLocal config dir with realistic demo data, so the audit
screenshots show a working app instead of empty lists.

MUST be imported only AFTER ``USERPROFILE``/``HOME`` have been repointed at a
sandbox — every store below resolves its path from ``CONFIG_DIR``, which is
``Path.home()/".cowork_local"`` evaluated at import time. ``seed()`` asserts this.

Where the app exposes a write API we call it (projects, history, tasks, skills,
workflows, agents). Two stores are written as raw files on purpose:

* **usage** and **audit** — their ``record()`` helpers always stamp
  ``datetime.now()``, so they cannot backdate. A one-day spike makes a useless
  chart, so the day files are written directly.
* **co4e/run_history.json** — the manager only persists from a Qt signal
  handler; there is no public save.
"""
from __future__ import annotations

import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

rnd = random.Random(20260808)      # fixed seed → identical screenshots every run

PROJECTS = [
    ("Trạm sạc EV — Cổng vận hành",
     "Cổng nội bộ theo dõi trạm sạc: bản đồ trạng thái, cảnh báo, báo cáo doanh thu.",
     "Trả lời bằng tiếng Việt. Backend FastAPI + PostgreSQL, frontend React.\n"
     "Luôn viết test trước khi sửa logic thanh toán."),
    ("Báo cáo tài chính Q3",
     "Tự động gom số liệu từ Excel phòng ban, dựng bảng tổng hợp và slide trình bày.",
     "Đơn vị tiền tệ mặc định VND. Làm tròn tới nghìn đồng.\n"
     "Mọi con số phải truy được về file nguồn."),
    ("Cổng tra cứu tài liệu ISO",
     "Tìm kiếm ngữ nghĩa trên kho tài liệu ISO 9001 của công ty.",
     "Ưu tiên trích dẫn đúng số hiệu điều khoản.\nKhông suy diễn ngoài tài liệu."),
]

CONVERSATIONS = [
    (0, "Dựng API trạng thái trạm sạc", True, [
        ("user", "Giúp mình dựng endpoint GET /stations/{id}/status trả về trạng thái realtime."),
        ("assistant", "Mình đã đọc `app/models/station.py` và thấy sẵn bảng `station_heartbeat`.\n\n"
                      "Đề xuất: endpoint đọc heartbeat mới nhất trong 90 giây, quá hạn thì trả `offline`.\n"
                      "Mình tạo `app/api/stations.py` và test đi kèm nhé?"),
        ("user", "Ừ làm đi."),
        ("assistant", "Đã tạo 2 file:\n- `app/api/stations.py` — router + schema phản hồi\n"
                      "- `tests/test_stations.py` — 4 ca: online, offline, không tồn tại, heartbeat lỗi\n\n"
                      "Chạy `pytest tests/test_stations.py` → 4 passed."),
    ]),
    (0, "Sửa lỗi tính tiền sai khi phiên sạc bị ngắt", False, [
        ("user", "Khách báo bị tính dư tiền khi rút sạc đột ngột giữa chừng."),
        ("assistant", "Mình tìm thấy nguyên nhân ở `billing/session.py:142`: khi phiên kết thúc bất thường, "
                      "`ended_at` vẫn để `None` nên hàm tính giờ lấy `now()` — tiền chạy tiếp tới lúc job dọn chạy.\n\n"
                      "Sửa: lấy mốc heartbeat cuối cùng làm `ended_at`. Mình chuẩn bị diff nhé?"),
    ]),
    (1, "Gom số liệu doanh thu từ 6 file phòng ban", True, [
        ("user", "Có 6 file Excel trong thư mục input, gom lại thành 1 bảng tổng hợp giúp mình."),
        ("assistant", "Đã đọc cả 6 file. Lưu ý: `PB_Marketing.xlsx` để cột “Doanh thu” ở vị trí khác "
                      "(cột F thay vì D) và có 3 dòng trống ở cuối.\n\n"
                      "Mình đã chuẩn hoá và xuất `tonghop_q3.xlsx` — 1.284 dòng, tổng 42.7 tỷ VND."),
    ]),
    (1, "Dựng slide trình bày kết quả Q3", False, [
        ("user", "Từ file tổng hợp, làm giúp bộ slide 8 trang."),
        ("assistant", "Đã tạo `BaoCao_Q3.pptx`: tổng quan → doanh thu theo phòng ban → so sánh Q2 → "
                      "top 5 tăng trưởng → rủi ro → kế hoạch Q4."),
    ]),
    (2, "Đánh chỉ mục kho tài liệu ISO", False, [
        ("user", "Quét thư mục docs/iso và dựng đồ thị tri thức."),
        ("assistant", "Đã quét 148 tài liệu, dựng 1.902 node và 3.418 cạnh. "
                      "Có 12 tài liệu bị trùng số hiệu điều khoản, mình liệt kê ở `trung_lap.md`."),
    ]),
    (0, "Rà soát bảo mật trước khi lên production", False, [
        ("user", "Kiểm tra giúp mình các chỗ có rủi ro bảo mật."),
        ("assistant", "Tìm thấy 3 điểm cần xử lý:\n1. API key Stripe hard-code ở `config/payment.py:31`\n"
                      "2. Endpoint `/admin/export` không kiểm tra quyền\n"
                      "3. CORS đang để `allow_origins=[\"*\"]`"),
    ]),
]

TASKS = [
    # (title, status, priority, ai, enabled, offset_days, last_status)
    ("Đồng bộ heartbeat trạm sạc mỗi 5 phút", "running", "high", False, True, 0, "success"),
    ("Gửi báo cáo doanh thu hằng ngày 08:00", "scheduled", "medium", False, True, 1, "success"),
    ("Quét lại chỉ mục ISO cuối tuần", "scheduled", "low", False, True, 3, "success"),
    ("Dựng slide tổng kết Q3", "done", "high", True, False, -2, "success"),
    ("Kiểm tra chứng chỉ TLS sắp hết hạn", "failed", "critical", False, True, -1, "failed"),
    ("Chờ kế toán duyệt số liệu tháng 7", "waiting_input", "medium", False, False, -3, None),
    ("Dọn log cũ hơn 90 ngày", "paused", "low", False, False, 7, "success"),
    ("Xuất danh sách khách hàng B2B", "backlog", "low", True, False, 5, None),
    ("Rà soát bảo mật trước release", "backlog", "high", False, False, 2, None),
    ("Sao lưu cơ sở dữ liệu hằng đêm", "done", "critical", False, True, -1, "success"),
]

SKILLS = [
    ("Rà soát bảo mật", "Quét mã tìm lộ khoá, thiếu kiểm tra quyền, cấu hình CORS lỏng.",
     "Khi được gọi, hãy rà soát theo thứ tự:\n1. Bí mật hard-code (API key, mật khẩu, token)\n"
     "2. Endpoint thiếu kiểm tra xác thực/phân quyền\n3. Cấu hình CORS, CSP, cookie\n"
     "4. Truy vấn SQL ghép chuỗi\nMỗi phát hiện phải kèm file:dòng và cách sửa cụ thể."),
    ("Chuẩn hoá bảng Excel", "Gom nhiều file Excel lệch cấu trúc về một bảng thống nhất.",
     "Đọc từng file, dò vị trí cột theo tiêu đề chứ không theo chỉ số cột.\n"
     "Bỏ dòng trống ở cuối. Báo rõ file nào lệch cấu trúc và lệch ra sao."),
    ("Viết test trước", "Sinh test cho hành vi mong muốn trước khi sửa mã.",
     "Trước khi sửa logic, viết test mô tả hành vi đúng.\n"
     "Chạy test để xác nhận nó FAIL, rồi mới sửa mã cho nó PASS."),
    ("Tóm tắt tài liệu ISO", "Tóm tắt điều khoản ISO kèm trích dẫn số hiệu.",
     "Luôn trích dẫn số hiệu điều khoản. Không suy diễn ngoài văn bản.\n"
     "Nếu tài liệu mâu thuẫn nhau, nêu rõ cả hai và chỉ ra chỗ mâu thuẫn."),
    ("Dựng slide từ số liệu", "Chuyển bảng số liệu thành bộ slide trình bày.",
     "Mỗi slide một thông điệp. Biểu đồ phải có nhãn trục và đơn vị.\n"
     "Slide cuối luôn là hành động tiếp theo."),
]

CO4E_AGENTS = [
    ("Phân tích yêu cầu", "ANALYST", "search",
     "Đọc mô tả yêu cầu, bóc tách thành danh sách hạng mục rõ ràng, đánh dấu chỗ còn mơ hồ.",
     ["Rà soát bảo mật"]),
    ("Thiết kế giải pháp", "ARCHITECT", "flow",
     "Từ danh sách hạng mục, đề xuất kiến trúc và các bước triển khai, nêu rõ đánh đổi.", []),
    ("Lập trình viên", "CODER", "code",
     "Hiện thực theo thiết kế. Viết test trước khi sửa logic nghiệp vụ.", ["Viết test trước"]),
    ("Kiểm thử", "TESTER", "shield",
     "Chạy test, đọc log lỗi, báo cáo ca nào hỏng và vì sao.", ["Rà soát bảo mật"]),
    ("Soạn tài liệu", "WRITER", "book",
     "Viết tài liệu hướng dẫn sử dụng từ mã nguồn và test.", ["Tóm tắt tài liệu ISO"]),
]

WORKFLOWS = [
    ("Quy trình phát triển tính năng",
     ["Phân tích yêu cầu", "Thiết kế giải pháp", "Lập trình viên", "Kiểm thử", "Soạn tài liệu"]),
    ("Rà soát bảo mật định kỳ", ["Phân tích yêu cầu", "Kiểm thử"]),
    ("Dựng báo cáo từ Excel", ["Phân tích yêu cầu", "Lập trình viên", "Soạn tài liệu"]),
]

AUDIT_EVENTS = [
    ("tool_call", "read_file", True, "app/models/station.py (2.1 KB)"),
    ("tool_call", "write_file", True, "app/api/stations.py — tạo mới, 84 dòng"),
    ("tool_call", "run_command", True, "pytest tests/test_stations.py → 4 passed"),
    ("tool_call", "fetch_url", True, "https://docs.python.org/3/library/asyncio.html"),
    ("permission", "run_command", True, "Người dùng duyệt: npm install --save-dev vitest"),
    ("permission", "write_file", False, "Người dùng từ chối: ghi đè .env"),
    ("security_block", "path_outside_sandbox", False, "Chặn đọc C:\\Users\\NamPDT\\Documents\\personal.xlsx"),
    ("security_block", "network_blocked", False, "Chặn kết nối ra 203.0.113.44:8080 (không trong danh sách cho phép)"),
    ("security_block", "dangerous_command", False, "Chặn lệnh: rm -rf / --no-preserve-root"),
    ("security_block", "secret_in_output", False, "Phát hiện chuỗi giống API key trong đầu ra, đã che"),
    ("mcp_call", "filesystem.list_directory", True, "docs/iso → 148 mục"),
    ("mcp_call", "jira.search_issues", True, "project=EV AND status=Open → 23 issue"),
    ("mcp_call", "postgres.query", True, "SELECT count(*) FROM station_heartbeat → 1.284.902"),
    ("mcp_call", "jira.create_issue", False, "401 Unauthorized — API token hết hạn"),
    ("mcp_call", "filesystem.read_file", True, "docs/iso/9001-2015.pdf (4.2 MB)"),
]

MODELS = [("ollama", "qwen2.5-coder:7b"), ("ollama", "llama3.1:8b"), ("openai", "gpt-4o-mini")]
LABELS = ["Dựng API trạng thái trạm sạc", "Sửa lỗi tính tiền sai", "Gom số liệu doanh thu",
          "Dựng slide trình bày", "Đánh chỉ mục ISO", "Rà soát bảo mật"]


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def seed(days: int = 45) -> dict:
    """Fill the (sandboxed) config dir. Returns a per-store count summary."""
    from cowork_local.config import CONFIG_DIR
    home = str(Path.home())
    assert str(CONFIG_DIR).startswith(home), "refusing to seed outside the sandboxed HOME"
    assert "cowork-capture-" in home or "cowork-seed-" in home, (
        f"HOME ({home}) does not look like a capture sandbox — refusing to seed")

    from cowork_local.core import admin_agents, co4e, history, projects, skills, tasks

    out: dict[str, int] = {}
    now = datetime.now().replace(hour=14, minute=32, second=0, microsecond=0)

    # ---- projects ---------------------------------------------------------
    made = []
    for name, desc, instr in PROJECTS:
        p = projects.new_project(name, description=desc, instructions=instr)
        p.workspace_dir().mkdir(parents=True, exist_ok=True)
        # a few files so the Folder tab's tree isn't bare
        for rel in ("README.md", "src/main.py", "src/billing/session.py",
                    "tests/test_stations.py", "docs/ghi-chu.md"):
            f = p.workspace_dir() / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            if not f.exists():
                f.write_text(f"# {rel}\n\n(nội dung mẫu cho ảnh chụp)\n", encoding="utf-8")
        made.append(p)
    out["projects"] = len(made)

    # ---- conversations ----------------------------------------------------
    hist_root = CONFIG_DIR / "history"
    hist_root.mkdir(parents=True, exist_ok=True)
    n_conv = 0
    for i, (pi, title, pinned, msgs) in enumerate(CONVERSATIONS):
        proj = made[pi]
        created = _iso(now - timedelta(days=i * 2 + 1, hours=i * 3))
        sid = (now - timedelta(days=i * 2 + 1)).strftime("%Y%m%d-%H%M%S-") + f"{i:03d}"
        payload = [{"role": r, "content": c} for r, c in msgs]
        for directory in (hist_root, proj.workspace_dir() / ".cowork_history"):
            directory.mkdir(parents=True, exist_ok=True)
            path = history.save_conversation(
                directory, "cowork", sid, payload, title=title,
                created=created, project_id=proj.project_id)
            if pinned:
                history.set_pinned(path, True)
            # stagger mtime so the sidebar's newest-first order looks real
            ts = (now - timedelta(days=i * 2 + 1)).timestamp()
            os.utime(path, (ts, ts))
        n_conv += 1
    out["conversations"] = n_conv

    # ---- scheduled tasks --------------------------------------------------
    for title, status, prio, ai, enabled, off, last in TASKS:
        t = tasks.new_task(
            title=title, status=status, priority=prio, is_ai_generated=ai,
            project_id=made[0].project_id, provider="ollama", model="qwen2.5-coder:7b",
            description=f"Tác vụ tự động: {title.lower()}.",
            schedule={"enabled": enabled,
                      "run_at": (now + timedelta(days=off)).strftime("%Y-%m-%d %H:%M"),
                      "repeat_type": "daily" if enabled else "none"},
            logs={"last_status": last or "", "last_run_id": "run-demo" if last else "",
                  "last_error": "Chứng chỉ hết hạn 2026-08-06" if last == "failed" else ""},
        )
        if last:
            t["runs"] = [{"run_id": f"r{n}", "status": last,
                          "finished_at": (now - timedelta(days=n)).strftime("%Y-%m-%d %H:%M"),
                          "error": "Chứng chỉ hết hạn" if last == "failed" else None}
                         for n in range(1, 4)]
        tasks.save_task(t)
    out["tasks"] = len(TASKS)

    # ---- skills -----------------------------------------------------------
    for name, desc, instr in SKILLS:
        skills.save_skill(skills.Skill(name=name, description=desc,
                                       instructions=instr, enabled=True))
    out["skills"] = len(SKILLS)

    # ---- Co4E agents ------------------------------------------------------
    for name, role, icon, instr, sk in CO4E_AGENTS:
        a = co4e.new_custom_agent(name)
        a.role, a.icon, a.instructions, a.skills = role, icon, instr, sk
        a.model = "qwen2.5-coder:7b"
        co4e.save_custom_agent(a)
    out["co4e_agents"] = len(CO4E_AGENTS)

    # ---- Co4E workflows ---------------------------------------------------
    wfs = []
    for name, steps in WORKFLOWS:
        wf = co4e.new_workflow(name)
        prev = None
        for j, label in enumerate(steps):
            node = co4e.Node(id=co4e.new_node_id(), x=60.0 + j * 250, y=140.0 + (j % 2) * 120,
                             data=co4e.Step(label=label, role="AGENT",
                                            instructions=f"{label}: thực hiện phần việc của mình "
                                                         f"rồi chuyển kết quả cho bước sau.",
                                            model="qwen2.5-coder:7b"))
            wf.nodes.append(node)
            if prev:
                wf.edges.append(co4e.Edge(id=co4e.new_edge_id(prev, node.id),
                                          source=prev, target=node.id))
            prev = node.id
        co4e.save_workflow(wf)
        wfs.append(wf)
    out["workflows"] = len(wfs)

    # ---- Co4E run history (no public save — written directly) -------------
    runs = []
    specs = [("done", 5, 5, 0), ("done", 2, 2, 1), ("error", 3, 5, 2),
             ("done", 3, 3, 3), ("stopped", 1, 5, 4), ("done", 5, 5, 6)]
    for k, (status, done, total, ago) in enumerate(specs, 1):
        wf = wfs[k % len(wfs)]
        runs.append({
            "id": f"run{k}", "wf_id": wf.id, "name": wf.name,
            "total": total, "done": done, "status": status,
            "plan_mode": False, "manual": False, "created_by": "local",
            "created_at": (now - timedelta(days=ago, hours=k)).strftime("%Y-%m-%d %H:%M"),
            "error": "Bước “Kiểm thử” trả về mã lỗi 1" if status == "error" else "",
            "node_status": {n.id: ("done" if i < done else
                                   ("error" if status == "error" and i == done else "idle"))
                            for i, n in enumerate(wf.nodes)},
            "wf": co4e.workflow_to_dict(wf),
            "out_dir": str(made[0].workspace_dir()),
            "project_id": made[0].project_id,
        })
    hp = CONFIG_DIR / "co4e" / "run_history.json"
    hp.parent.mkdir(parents=True, exist_ok=True)
    hp.write_text(json.dumps({"runs": runs}, ensure_ascii=False, indent=2), encoding="utf-8")
    out["co4e_runs"] = len(runs)

    # ---- usage day files (record() cannot backdate) -----------------------
    usage_dir = CONFIG_DIR / "usage"
    usage_dir.mkdir(parents=True, exist_ok=True)
    n_usage = 0
    for d in range(days):
        day = now - timedelta(days=days - 1 - d)
        # a workday rhythm: quiet weekends, a gentle upward trend
        weekend = day.weekday() >= 5
        turns = rnd.randint(1, 3) if weekend else rnd.randint(4, 11) + d // 12
        lines = []
        for _ in range(turns):
            prov, model = rnd.choice(MODELS)
            lines.append(json.dumps({
                "ts": _iso(day.replace(hour=rnd.randint(8, 18), minute=rnd.randint(0, 59))),
                "source": rnd.choice(["cowork", "cowork", "task", "co4e"]),
                "label": rnd.choice(LABELS), "provider": prov, "model": model,
                "in": rnd.randint(1200, 9000), "out": rnd.randint(300, 3200),
                "cache": rnd.randint(0, 4200), "estimated": False,
                "account": "local", "machine": "DESKTOP-DEMO",
            }, ensure_ascii=False))
            n_usage += 1
        (usage_dir / f"{day:%Y-%m-%d}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    out["usage_events"] = n_usage

    # ---- audit day files (drives Security / MCP / Action tables) ----------
    audit_dir = CONFIG_DIR / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    n_audit = 0
    roles = ["cowork", "code", "schedule", "graphrag", "security"]
    for d in range(14):
        day = now - timedelta(days=13 - d)
        lines = []
        for _ in range(rnd.randint(4, 9)):
            kind, name, ok, detail = rnd.choice(AUDIT_EVENTS)
            lines.append(json.dumps({
                "ts": _iso(day.replace(hour=rnd.randint(8, 19), minute=rnd.randint(0, 59))),
                "kind": kind, "agent_role": rnd.choice(roles), "name": name,
                "ok": ok, "detail": detail,
                "account": "local", "role": "admin", "machine": "DESKTOP-DEMO",
            }, ensure_ascii=False))
            n_audit += 1
        (audit_dir / f"{day:%Y-%m-%d}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    out["audit_events"] = n_audit

    # ---- admin agents -----------------------------------------------------
    admin_dir = admin_agents.agents_admin_dir("")
    admin_dir.mkdir(parents=True, exist_ok=True)
    for name, kind in [("Trợ giúp trong app", "help"), ("Tìm kiếm tài khoản", "search"),
                       ("Phân tích giám sát", "monitor"), ("Cowork mặc định", "cowork"),
                       ("Hỏi đáp GraphRAG", "graphrag"), ("Lập lịch thông minh", "schedule"),
                       ("Kiểm tra lệnh nguy hiểm", "security")]:
        a = admin_agents.new_agent(name, task_kind=kind, provider="ollama",
                                   model="qwen2.5-coder:7b", updated_by="local",
                                   prompt=f"Bạn phụ trách chức năng “{kind}” của ứng dụng.")
        admin_agents.save_agent(a, admin_dir)
    out["admin_agents"] = 7

    return out


if __name__ == "__main__":
    raise SystemExit("Import and call seed() from capture_screens.py — it needs the sandboxed HOME.")
