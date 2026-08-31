"""Audit logger — records every sandbox execution attempt.

Logs: allow, deny, execution events with timestamp, user, project, workspace,
prompt category, risk score, action type, backend selected, command hash,
working directory scope, network blocked, result status, return code, denial reason.

Does NOT log secrets or raw sensitive content.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("cowork_local.security.audit")


@dataclass
class AuditEntry:
    """Một dòng nhật ký kiểm toán, đủ trường để dựng lại bối cảnh sau này.

    Cố ý KHÔNG lưu nguyên văn lệnh: chỉ giữ ``command_hash`` (SHA-256, 16
    ký tự đầu) để đối chiếu hai lần chạy có giống nhau không, mà không đưa
    nội dung nhạy cảm vào file log.
    """
    timestamp: str = ""
    user: str = ""
    project: str = ""
    workspace: str = ""
    prompt_category: str = ""
    risk_score: int = 0
    action_type: str = ""
    backend_selected: str = ""
    command_hash: str = ""
    working_directory_scope: str = ""
    network_blocked: bool = False
    result_status: str = ""  # allowed, denied, executed, error
    return_code: int = 0
    denial_reason: str = ""
    approval_status: str = ""  # auto, approved, rejected

    def __post_init__(self):
        """Điền mốc thời gian và mã băm lệnh nếu bên gọi chưa đặt.

        Mã băm thay cho nội dung lệnh gốc: nhật ký cần truy được về sau nhưng không
        nên chứa nguyên văn thứ đã chạy.
        """
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.command_hash and self.action_type:
            self.command_hash = hashlib.sha256(
                self.action_type.encode()
            ).hexdigest()[:16]


def _audit_dir() -> Path:
    """Thư mục chứa nhật ký kiểm toán. Import muộn để tránh vòng import với ``config``."""
    from ..config import CONFIG_DIR
    return CONFIG_DIR / "audit"


def record(
    action_type: str,
    result_status: str,
    *,
    user: str = "",
    project: str = "",
    workspace: str = "",
    prompt_category: str = "",
    risk_score: int = 0,
    backend_selected: str = "",
    command: str = "",
    working_directory: str = "",
    network_blocked: bool = False,
    return_code: int = 0,
    denial_reason: str = "",
    approval_status: str = "",
) -> AuditEntry:
    """Create and persist an audit log entry."""
    cmd_hash = hashlib.sha256(command.encode()).hexdigest()[:16] if command else ""
    entry = AuditEntry(
        user=user,
        project=project,
        workspace=workspace,
        prompt_category=prompt_category,
        risk_score=risk_score,
        action_type=action_type,
        backend_selected=backend_selected,
        command_hash=cmd_hash,
        working_directory_scope=working_directory,
        network_blocked=network_blocked,
        result_status=result_status,
        return_code=return_code,
        denial_reason=denial_reason,
        approval_status=approval_status,
    )

    # Write to JSONL file
    audit_dir = _audit_dir()
    audit_dir.mkdir(parents=True, exist_ok=True)
    log_file = audit_dir / "sandbox_audit.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entry)) + "\n")

    logger.info(
        "AUDIT: action=%s status=%s user=%s risk=%d backend=%s",
        action_type, result_status, user, risk_score, backend_selected,
    )
    return entry