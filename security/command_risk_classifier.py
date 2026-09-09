"""Command risk classifier — scores commands 0-100 and assigns risk level.

This is the first gate in the security validation pipeline. It classifies every
command/tool-call/prompt into a risk bucket so SandboxManager can select the
right isolation backend.

Risk levels:
  safe       (0-30)   Business-safe, read-only, no system impact
  moderate   (31-60)  File writes, trusted internal tools, report generation
  high       (61-85)  Interpreters, untrusted commands, external file access
  critical   (86-100) Unknown binaries, privilege changes, shell expansion,
                      system discovery, source-code access, secret access
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class RiskLevel(str, Enum):
    """Bậc rủi ro của một lệnh, prompt hay tệp đính kèm.

    Kế thừa ``str`` để so sánh và ghi log thẳng bằng chuỗi mà không phải
    ``.value`` ở từng chỗ dùng.
    """
    SAFE = "safe"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"
    BLOCKED = "blocked"


@dataclass
class RiskResult:
    """Kết quả một lần phân loại: điểm, bậc, lý do, và có chặn hẳn không.

    ``reasons`` giữ lại đúng mẫu regex đã khớp — nhật ký kiểm toán phải trả
    lời được "vì sao lệnh này bị chặn", không chỉ "bị chặn".
    """
    score: int           # 0-100
    level: RiskLevel     # categorized bucket
    reasons: List[str]   # why this score was assigned
    blocked: bool = False


# Patterns that immediately block (score=100, blocked=True)
_BLOCK_PATTERNS = [
    r'\bwhoami\b', r'\bgetent\b', r'\bw\b', r'\buname\b', r'\bhostname\b',
    r'\bnmap\b', r'\bnetstat\b', r'\bir\b', r'\bpip\s+list\b', r'\bnpm\s+list\b',
    r'\bsecret\b', r'\bpassword\b', r'\bapi[_-]?key\b', r'\btoken\b',
    r'\b\.env\b', r'\bcredentials?\b', r'\bprivate[_-]?key\b',
    r'\bsudo\b', r'\brunsas\b', r'\bpowershell\s+-ep\s+bypass',
    r'\bexploit\b', r'\bpayload\b', r'\bshellcode\b',
    r'ignore\s+previous\s+instructions?',
    r'you\s+are\s+now\s+(\w+)',
    r'disabl(e|ed?)\s+(sandbox|security|guardrail|filter)',
    r'bypass\s+(security|sandbox|policy)',
]

_HIGH_PATTERNS = [
    r'\b(python|node|ruby|perl|php|bash|sh|pwsh|powershell)\b',
    r'\bexec\b', r'\beval\b', r'\bsystem\b', r'\bpopen\b',
    r'\bcurl\s+.*\|\s*(bash|sh|python|node)',
    r'\brm\s+-rf\b', r'\bdeltree\b',
]

_MODERATE_PATTERNS = [
    r'\b(touch|mkdir|cp|mv|rename)\b',
    r'\b(pip|npm|pnpm|yarn)\s+install\b',
    r'\b(make|cmake|gradle|mvn)\b',
    r'\b(test|pytest|jest|mocha)\b',
]

# Tools that reach the network over ICMP/raw sockets/direct DNS instead of an
# HTTP(S) connection — none of them read HTTP_PROXY/HTTPS_PROXY, so
# core/deps.py::network_blocked_env()'s proxy-env-var block (the only network
# control this sandbox actually enforces) has no effect on them at all. Used
# by command_bypasses_network_proxy() to deny these BY NAME when the user has
# "Chặn mạng cho lệnh do agent chạy" on, since the proxy trick alone silently
# lets them through (see DF-005 in Defect Management).
_NETWORK_PROXY_BYPASS_PATTERNS = [
    r'\bping\b', r'\btracert\b', r'\btraceroute\b', r'\bnslookup\b', r'\bdig\b',
    r'\btelnet\b', r'\bftp\b', r'\bsftp\b', r'\bscp\b', r'\bssh\b',
    r'\bnc\b', r'\bncat\b', r'\bnetcat\b', r'\barp\b',
    r'\btest-netconnection\b', r'\btest-connection\b', r'\bresolve-dnsname\b',
]


def command_bypasses_network_proxy(command: str) -> Optional[str]:
    """Tên công cụ mạng đầu tiên khớp trong ``command`` mà không tôn trọng
    HTTP_PROXY/HTTPS_PROXY — None nếu không có công cụ nào như vậy.

    ``network_blocked_env()`` chỉ set biến proxy, nên chỉ chặn được các công
    cụ có ĐỌC biến đó (curl/pip/requests...). ``ping`` (ICMP), ``nslookup``
    (DNS trực tiếp), ``ssh``/``ftp`` (TCP thô)... đều đi qua giao thức khác,
    biến proxy không có tác dụng gì với chúng — phải chặn riêng theo tên lệnh
    khi ``block_network`` đang bật.
    """
    cmd_lower = command.lower()
    for pattern in _NETWORK_PROXY_BYPASS_PATTERNS:
        m = re.search(pattern, cmd_lower, re.IGNORECASE)
        if m:
            return m.group()
    return None


def classify_command(command: str, is_cowork_mode: bool = True) -> RiskResult:
    """Chấm điểm rủi ro một lệnh shell.

    Ba tầng mẫu: ``_BLOCK_PATTERNS`` chặn thẳng (100 điểm, dừng ngay khi
    khớp mẫu đầu tiên), ``_HIGH_PATTERNS`` và ``_MODERATE_PATTERNS`` cộng
    dồn điểm. ``is_cowork_mode`` nới tay hơn cho màn Cowork, nơi người dùng
    đang chủ động ngồi xem từng bước.
    """
    score = 0
    reasons: List[str] = []
    blocked = False
    cmd_lower = command.lower()

    for pattern in _BLOCK_PATTERNS:
        m = re.search(pattern, cmd_lower, re.IGNORECASE)
        if m:
            reasons.append(f"blocked: matched '{m.group()[:50]}'")
            score = 100
            blocked = True
            break

    if not blocked:
        high_hits = 0
        for pattern in _HIGH_PATTERNS:
            m = re.search(pattern, cmd_lower, re.IGNORECASE)
            if m:
                high_hits += 1
                reasons.append(f"high: matched '{m.group()[:50]}'")
        score = max(score, min(85, 50 + high_hits * 10))

        mod_hits = 0
        for pattern in _MODERATE_PATTERNS:
            m = re.search(pattern, cmd_lower, re.IGNORECASE)
            if m:
                mod_hits += 1
                reasons.append(f"moderate: matched '{m.group()[:50]}'")
        score = max(score, min(60, 20 + mod_hits * 10))

        if not reasons:
            score = 10
            reasons.append("safe: no risky patterns detected")

    if blocked:
        level = RiskLevel.BLOCKED
    elif score >= 86:
        level = RiskLevel.CRITICAL
    elif score >= 61:
        level = RiskLevel.HIGH
    elif score >= 31:
        level = RiskLevel.MODERATE
    else:
        level = RiskLevel.SAFE

    return RiskResult(score=score, level=level, reasons=reasons, blocked=blocked)


def classify_prompt(prompt: str, is_cowork_mode: bool = True) -> RiskResult:
    """Chấm điểm rủi ro một prompt — dùng chung bộ mẫu với lệnh shell.

    Cố ý dùng chung: tấn công tiêm lệnh viết bằng văn xuôi ("ignore previous
    instructions") và lệnh shell nguy hiểm đều nằm trong cùng danh sách mẫu.
    """
    return classify_command(prompt, is_cowork_mode=is_cowork_mode)


def classify_attachment(path: str, mime_type: Optional[str] = None) -> RiskResult:
    """Chặn tệp đính kèm chạy được, theo đuôi tệp rồi tới kiểu MIME.

    Chặn theo danh sách đen — mã nguồn và tệp thực thi không được đưa vào
    ngữ cảnh chat. Tệp ngoài danh sách được coi là an toàn (30 điểm).
    """
    import os
    _, ext = os.path.splitext(path.lower())
    blocked_ext = {
        '.py', '.js', '.ts', '.java', '.cs', '.cpp', '.c', '.go', '.rs',
        '.php', '.vb', '.sql', '.ps1', '.sh', '.bat', '.cmd', '.vbs',
        '.vba', '.exe', '.dll', '.jar',
    }
    if ext in blocked_ext:
        return RiskResult(100, RiskLevel.BLOCKED,
                          [f"blocked: extension '{ext}'"], blocked=True)
    if mime_type:
        blocked_mimes = {
            'application/x-executable', 'application/x-dosexec',
            'application/x-pie-executable', 'application/x-sharedlib',
            'application/java-archive', 'application/x-msdownload',
        }
        if mime_type.lower() in blocked_mimes:
            return RiskResult(100, RiskLevel.BLOCKED,
                              [f"blocked: MIME '{mime_type}'"], blocked=True)
    return RiskResult(30, RiskLevel.SAFE, ["safe: allowed file type"], blocked=False)


def classify_action(action_type: str, action_details: Optional[dict] = None) -> RiskResult:
    """Chấm điểm rủi ro một loại hành động theo từ khoá trong tên.

    Hành động lạ nhận 50 điểm (mức trung bình) chứ không phải 0 — thứ chưa
    biết thì không được mặc định là an toàn.
    """
    a = action_type.lower()
    if any(kw in a for kw in ('execute', 'run', 'shell', 'system')):
        return RiskResult(70, RiskLevel.HIGH, [f"high: action '{action_type}'"])
    if any(kw in a for kw in ('write', 'create', 'modify', 'delete', 'install')):
        return RiskResult(40, RiskLevel.MODERATE, [f"moderate: action '{action_type}'"])
    if any(kw in a for kw in ('read', 'list', 'get', 'search', 'query')):
        return RiskResult(10, RiskLevel.SAFE, [f"safe: action '{action_type}'"])
    return RiskResult(50, RiskLevel.MODERATE, [f"unknown: action '{action_type}'"])