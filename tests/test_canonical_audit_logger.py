"""Task 2 — CanonicalAuditLogger.

Verifies: (1) the infrastructure class itself round-trips events correctly
and mirrors to a shared dir, (2) ``core/audit_log.py``'s wrapper functions
still behave exactly as before (same signatures, same dict schema, same
never-raise guarantee), and (3) old-format raw dicts (as written by the
pre-refactor ``core/audit_log.py``) still load correctly for backward
compatibility.
"""
from __future__ import annotations

import json

from cowork_local.core import audit_log
from cowork_local.infrastructure.telemetry.audit_logger import (
    KIND_MCP_CALL,
    KIND_SECURITY_BLOCK,
    CanonicalAuditEvent,
    CanonicalAuditLogger,
)


def test_record_and_load_round_trip(tmp_path) -> None:
    logger = CanonicalAuditLogger(tmp_path)
    logger.set_identity("alice", "machine-1", role="admin")
    logger.record(KIND_SECURITY_BLOCK, "run_command", False, detail="blocked it")

    events = logger.load_events()
    assert len(events) == 1
    e = events[0]
    assert e.kind == KIND_SECURITY_BLOCK
    assert e.name == "run_command"
    assert e.ok is False
    assert e.detail == "blocked it"
    assert e.account == "alice"
    assert e.machine == "machine-1"
    assert e.role == "admin"


def test_load_events_filters_by_kind(tmp_path) -> None:
    logger = CanonicalAuditLogger(tmp_path)
    logger.record(KIND_SECURITY_BLOCK, "a", False)
    logger.record(KIND_MCP_CALL, "b", True)

    only_mcp = logger.load_events(kind=KIND_MCP_CALL)
    assert [e.name for e in only_mcp] == ["b"]


def test_shared_dir_mirroring(tmp_path) -> None:
    shared = tmp_path / "shared"
    logger = CanonicalAuditLogger(tmp_path / "audit")
    logger.set_identity("bob", "machine-2", shared_dir=str(shared))
    logger.record(KIND_MCP_CALL, "tool_x", True)

    mirrored_files = list((shared / "telemetry" / "audit").glob("machine-2-*.jsonl"))
    assert len(mirrored_files) == 1


def test_from_dict_is_tolerant_of_old_partial_rows() -> None:
    old_row = {"ts": "2024-01-01T00:00:00", "kind": "tool_call", "name": "x", "ok": True}
    event = CanonicalAuditEvent.from_dict(old_row)
    assert event.detail == ""
    assert event.account == ""


def test_record_never_raises_on_bad_directory(tmp_path) -> None:
    bad_dir = tmp_path / "some_file.txt"
    bad_dir.write_text("not a directory")
    logger = CanonicalAuditLogger(bad_dir / "audit")
    logger.record(KIND_SECURITY_BLOCK, "x", False)  # must not raise


def test_core_audit_log_wrapper_same_schema_as_before(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(audit_log, "AUDIT_DIR", tmp_path)
    monkeypatch.setattr(audit_log, "_logger",
                        audit_log.CanonicalAuditLogger(tmp_path))
    audit_log.set_identity("carol", "machine-3", role="user")
    audit_log.record("permission", "install_package", True, detail="ok", agent_role="cowork")

    events = audit_log.load_events()
    assert len(events) == 1
    e = events[0]
    assert set(e.keys()) == {"ts", "kind", "agent_role", "name", "ok", "detail",
                             "account", "role", "machine"}
    assert e["kind"] == "permission"
    assert e["name"] == "install_package"
    assert e["ok"] is True
    assert e["agent_role"] == "cowork"
    assert e["account"] == "carol"

    # Raw file on disk still uses the exact pre-refactor schema/keys.
    raw_line = next((tmp_path).glob("*.jsonl")).read_text(encoding="utf-8").splitlines()[0]
    raw = json.loads(raw_line)
    assert list(raw.keys()) == ["ts", "kind", "agent_role", "name", "ok", "detail",
                                "account", "role", "machine"]
