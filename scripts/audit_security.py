"""CASAN Check 1 — không được có credential nào nằm phơi trong repo.

Team Gamma chủ trì check này (hạn: 30/08). Viết sẵn từ 21/08 để chạy được liên
tục trong lúc chuyển API key sang Keyring (R02-T05), thay vì tới ngày cổng mới
chạy lần đầu rồi mới biết còn sót.

Quét gì:
  * file cấu hình đã commit: ``*.json`` ``*.jsonl`` ``*.yaml`` ``*.yml`` ``*.env``
  * mã nguồn Python — chỗ gán chuỗi cho biến tên như api_key / token / secret

Tìm hai loại:
  1. Chuỗi có hình dạng credential thật (sk-…, ghp_…, xoxb-…, AKIA…, JWT…)
  2. Trường tên nhạy cảm mà giá trị không rỗng và không phải placeholder

Bỏ qua: chuỗi rỗng, placeholder ("your-key-here", "changeme"…), giá trị hằng
không phải bí mật (Ollama đòi có api_key nhưng bỏ qua nội dung).

Chạy:  python scripts/audit_security.py [--json]
Mã thoát: 0 = sạch, 1 = có phát hiện.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

# console Windows hay là cp932/cp1258; ép UTF-8 để không chết giữa báo cáo
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "build",
             "dist", ".pytest_cache", ".mypy_cache", "cowork-local-gitea"}
CONFIG_SUFFIX = {".json", ".jsonl", ".yaml", ".yml", ".env"}

# tên trường coi là nhạy cảm
SENSITIVE = re.compile(
    r"(api[_-]?key|secret|token|password|passwd|client[_-]?secret|"
    r"access[_-]?key|private[_-]?key|credential)", re.I)

# hình dạng credential thật — bắt được kể cả khi tên trường vô hại
SHAPES = [
    ("OpenAI",      re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}")),
    ("Anthropic",   re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}")),
    ("GitHub",      re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("Slack",       re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}")),
    ("AWS",         re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google",      re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("JWT",         re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.")),
    ("Private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]

#: Dòng có dấu này được bỏ qua — lối thoát chuẩn cho mẫu thử, tài liệu, hằng
#: đặt tên chứa "secret". Bắt buộc ghi lý do sau dấu hai chấm.
ALLOW_MARK = re.compile(r"#\s*casan:\s*allow")

#: Giá trị là KHOÁ i18n / tên hằng, không phải bí mật. Bắt bằng hình dạng
#: "a.b.c" hoặc "a_b_c" chứ không phải bằng danh sách đen từng chữ.
LOOKS_LIKE_KEY = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")

#: Credential thật gần như luôn dài hơn thế này. Ngưỡng để loại dữ liệu test
#: kiểu api_key="x" — báo động giả làm cả đội thôi đọc báo cáo.
MIN_SECRET_LEN = 12

#: Giá trị là hằng liệt kê, không phải bí mật: mức độ cảnh báo, bật/tắt…
ENUMISH = {"warning", "warn", "error", "info", "debug", "critical", "on", "off",
           "true", "false", "yes", "no", "allow", "deny", "block", "ask",
           "always", "never", "auto", "default", "disabled", "enabled"}

# giá trị vô hại — không tính là phát hiện
PLACEHOLDER = re.compile(
    r"^(|ollama|none|null|changeme|your[_\- ]?(api[_\- ]?)?key([_\- ]?here)?|"
    r"<[^>]*>|\{\{.*\}\}|\$\{.*\}|xxx+|\*+|placeholder|todo|example|test|dummy|"
    r"sk-\.\.\.|\.\.\.)$", re.I)

# gán chuỗi trong Python: api_key = "..."
PY_ASSIGN = re.compile(
    r"""["']?(\w*(?:api[_-]?key|secret|token|password|credential)\w*)["']?\s*[:=]\s*"""
    r"""["']([^"']*)["']""", re.I)


def _is_placeholder(value: str) -> bool:
    v = value.strip()
    if PLACEHOLDER.match(v) or v.lower() in ENUMISH:
        return True
    if LOOKS_LIKE_KEY.match(v):        # "monitoring.action_secret_in_output"
        return True
    # quá ngắn để là credential thật
    return len(v) < MIN_SECRET_LEN


def _walk():
    for path in REPO.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix in CONFIG_SUFFIX or path.suffix == ".py":
            yield path


def scan() -> list[dict]:
    findings: list[dict] = []
    for path in _walk():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = path.relative_to(REPO).as_posix()

        for lineno, line in enumerate(text.splitlines(), 1):
            if ALLOW_MARK.search(line):
                continue
            # 1. hình dạng credential thật
            for label, pattern in SHAPES:
                m = pattern.search(line)
                if m:
                    findings.append({
                        "file": rel, "line": lineno, "kind": f"{label} credential",
                        "evidence": m.group(0)[:12] + "…",
                    })

            # 2. trường nhạy cảm có giá trị
            for m in PY_ASSIGN.finditer(line):
                field, value = m.group(1), m.group(2)
                if not SENSITIVE.search(field) or _is_placeholder(value):
                    continue
                findings.append({
                    "file": rel, "line": lineno,
                    "kind": f"trường '{field}' có giá trị",
                    "evidence": value[:6] + "…" if len(value) > 6 else value,
                })
    return findings


def _self_test() -> int:
    """Một máy quét không tìm thấy gì chỉ có giá trị nếu chứng minh được nó
    biết tìm. Cắm mẫu xấu và mẫu vô hại, xem có phân biệt đúng không."""
    import tempfile

    bad = {
        "OpenAI":   '"api_key": "sk-proj-abc123def456ghi789jkl012mno"',  # casan: allow - mau thu cua chinh script
        "GitHub":   'token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"',  # casan: allow - mau thu cua chinh script
        "AWS":      'aws = "AKIAIOSFODNN7EXAMPLE"',  # casan: allow - mau thu cua chinh script
        "Anthropic": '"api_key": "sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxx"',  # casan: allow - mau thu cua chinh script
    }
    ok = {
        "rỗng":        '"api_key": ""',
        "placeholder": '"api_key": "your-key-here"',
        "ollama":      '"api_key": "ollama"',
        "test ngắn":   'api_key = "x"',
        "hằng liệt kê": '"secret_in_output": "warning"',
    }
    global REPO
    keep = REPO
    passed = True
    with tempfile.TemporaryDirectory() as tmp:
        REPO = Path(tmp)
        for label, line in {**bad, **ok}.items():
            (REPO / "probe.py").write_text(line + "\n", encoding="utf-8")
            found = bool(scan())
            want = label in bad
            mark = "OK " if found == want else "SAI"
            if found != want:
                passed = False
            verb = "bắt được" if found else "bỏ qua"
            print(f"  [{mark}] {label:14} -> {verb}")
    REPO = keep
    print()
    print("Tự kiểm: " + ("script phân biệt đúng." if passed
                         else "*** script phân biệt SAI ***"))
    return 0 if passed else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="CASAN Check 1 — quét credential lộ")
    ap.add_argument("--json", action="store_true", help="in kết quả dạng JSON")
    ap.add_argument("--self-test", action="store_true",
                    help="cắm credential giả vào file tạm, kiểm script có bắt được")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()

    findings = scan()
    if args.json:
        print(json.dumps(findings, ensure_ascii=False, indent=2))
    else:
        n_files = sum(1 for _ in _walk())
        print(f"CASAN Check 1 — quét {n_files} file trong {REPO.name}/")
        if not findings:
            print("\n0 credential lưu plaintext. PASS.")
        else:
            print(f"\n*** {len(findings)} phát hiện ***\n")
            for f in findings:
                print(f"  {f['file']}:{f['line']}")
                print(f"      {f['kind']} — {f['evidence']}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
