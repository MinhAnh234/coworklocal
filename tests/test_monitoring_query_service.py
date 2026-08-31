"""Task 3 — MonitoringQueryService: read-only filter/sort/pagination over
audit events, fully testable without file I/O (InMemoryAuditEventRepository)
and with a real CanonicalAuditLogger wired through CanonicalAuditEventRepository.
"""
from __future__ import annotations

from cowork_local.application.monitoring.dto.audit_event_dto import AuditEventDTO
from cowork_local.application.monitoring.monitoring_query_service import (
    MonitoringQueryService,
)
from cowork_local.application.monitoring.repository.audit_event_repository import (
    CanonicalAuditEventRepository,
    InMemoryAuditEventRepository,
)
from cowork_local.infrastructure.telemetry.audit_logger import CanonicalAuditLogger


def _event(ts, kind="tool_call", name="x", ok=True, detail="") -> AuditEventDTO:
    return AuditEventDTO(ts=ts, kind=kind, name=name, ok=ok, detail=detail)


def test_query_filters_by_kind() -> None:
    repo = InMemoryAuditEventRepository([
        _event("2026-01-01T00:00:00", kind="mcp_call", name="a"),
        _event("2026-01-01T00:00:01", kind="security_block", name="b"),
    ])
    service = MonitoringQueryService(repo)
    page = service.query(kind="mcp_call")
    assert [e.name for e in page.items] == ["a"]


def test_query_filters_by_ok_and_text() -> None:
    repo = InMemoryAuditEventRepository([
        _event("2026-01-01T00:00:00", name="run_command", ok=False, detail="blocked"),
        _event("2026-01-01T00:00:01", name="run_command", ok=True, detail="fine"),
        _event("2026-01-01T00:00:02", name="fetch_url", ok=False, detail="blocked"),
    ])
    service = MonitoringQueryService(repo)
    page = service.query(ok=False, text="run_command")
    assert len(page.items) == 1
    assert page.items[0].detail == "blocked"


def test_query_sorts_newest_first_by_default() -> None:
    repo = InMemoryAuditEventRepository([
        _event("2026-01-01T00:00:00", name="first"),
        _event("2026-01-02T00:00:00", name="second"),
    ])
    service = MonitoringQueryService(repo)
    page = service.query()
    assert [e.name for e in page.items] == ["second", "first"]


def test_query_paginates() -> None:
    events = [_event(f"2026-01-{i:02d}T00:00:00", name=str(i)) for i in range(1, 11)]
    repo = InMemoryAuditEventRepository(events)
    service = MonitoringQueryService(repo)

    page1 = service.query(sort_by="ts", descending=False, page=1, page_size=4)
    page2 = service.query(sort_by="ts", descending=False, page=2, page_size=4)

    assert page1.total == 10
    assert [e.name for e in page1.items] == ["1", "2", "3", "4"]
    assert [e.name for e in page2.items] == ["5", "6", "7", "8"]
    assert page1.has_more is True


def test_large_page_size_returns_everything_matching_current_ui_behaviour() -> None:
    events = [_event(f"2026-01-{i:02d}T00:00:00", name=str(i)) for i in range(1, 6)]
    repo = InMemoryAuditEventRepository(events)
    service = MonitoringQueryService(repo)
    page = service.query(page_size=10_000)
    assert len(page.items) == 5
    assert page.has_more is False


def test_repository_is_read_only_no_pyside6_import() -> None:
    import cowork_local.application.monitoring.monitoring_query_service as mod
    import cowork_local.application.monitoring.repository.audit_event_repository as repo_mod
    assert "PySide6" not in mod.__dict__
    assert "PySide6" not in repo_mod.__dict__
    assert not hasattr(mod.MonitoringQueryService, "record")


def test_canonical_repository_wires_to_real_logger(tmp_path) -> None:
    logger = CanonicalAuditLogger(tmp_path)
    logger.record("security_block", "run_command", False, detail="nope")
    logger.record("mcp_call", "search", True)

    repo = CanonicalAuditEventRepository(logger)
    service = MonitoringQueryService(repo)

    page = service.query(kind="security_block")
    assert len(page.items) == 1
    assert page.items[0].name == "run_command"
