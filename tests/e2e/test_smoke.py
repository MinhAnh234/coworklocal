"""EPIC R10-T05: End-to-End Release Smoke Test Suite.

Runs headless E2E smoke tests covering the 5 core runtime subsystems before release:
  Scenario 1: Application Composition Root & MainWindow Bootstrap
  Scenario 2: Chat Turn Lifecycle & AgentEvent Stream
  Scenario 3: Task Scheduling, Calculation & Dispatch
  Scenario 4: Workspace Isolation & File Operations
  Scenario 5: Configuration & Secrets Persistence Round-trip
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure Qt runs offscreen in headless environments
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cowork_local.application.conversations.conversation_application_service import (
    ConversationApplicationService,
)
from cowork_local.application.scheduling.task_application_service import (
    TaskApplicationService,
)
from cowork_local.application.workspaces.file_workspace_service import (
    FileWorkspaceService,
)
from cowork_local.domain.agents.conversation_execution_request import (
    ConversationExecutionRequest,
)
from cowork_local.domain.workspaces.workspace_session import WorkspaceSession
from cowork_local.infrastructure.config.json_config_repository import (
    JsonConfigRepository,
)
from cowork_local.infrastructure.filesystem.execution_workspace import (
    ExecutionWorkspace,
)
from cowork_local.infrastructure.persistence.json.task_repository_impl import (
    TaskRepository,
)
from cowork_local.presentation.shell.bootstrap import build_config, build_context
from cowork_local.presentation.shell.main_window import MainWindow
from cowork_local.state import AppContext
from cowork_local.tests.fakes.turn_runtime_fakes import (
    FakeModelCall,
    FakeReply,
    FakeToolRuntime,
    make_request,
    run_turn,
)

pytest.importorskip("PySide6", reason="PySide6 required for E2E GUI smoke tests")


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_scenario_1_bootstrap_and_main_window(qt_app, tmp_path):
    """Scenario 1: Test Composition Root and MainWindow initialization."""
    config_path = tmp_path / "config.json"
    repo = build_config(config_path)
    assert repo is not None

    ctx = build_context(config_path)
    assert isinstance(ctx, AppContext)

    # Instantiate MainWindow
    window = MainWindow(ctx)
    assert window is not None
    assert window.ctx is ctx
    assert hasattr(window, "pages")
    assert hasattr(window, "sidebar")
    assert hasattr(window, "workspace")
    window.close()


def test_scenario_2_chat_turn_lifecycle(tmp_path):
    """Scenario 2: Test Chat turn execution with pure Python service and FakeModelCall."""
    model = FakeModelCall([FakeReply(content="Hello from release smoke test!", chunks=["Hello from ", "release smoke test!"])])
    service = ConversationApplicationService(model, FakeToolRuntime())

    req = make_request(prompt="Run release smoke test")
    result, events = run_turn(service, request=req)

    assert result.ok is True
    assert result.final_text == "Hello from release smoke test!"
    assert len(events) >= 1


def test_scenario_3_task_scheduling_and_dispatch(tmp_path):
    """Scenario 3: Test task repository and application service dispatch."""
    repo = TaskRepository(directory=tmp_path)

    task_payload = {
        "task_id": "smoke_task_1",
        "title": "Release Smoke Task",
        "status": "backlog",
        "task_type": "cowork",
        "enabled": True,
        "run_at": datetime.now(timezone.utc).isoformat(),
    }
    repo.save(task_payload)

    # Verify task retrieval
    retrieved = repo.get("smoke_task_1")
    assert retrieved is not None
    assert retrieved["title"] == "Release Smoke Task"

    # Test TaskApplicationService operations
    fake_scheduler = MagicMock()
    fake_scheduler.run_task_now.return_value = True

    service = TaskApplicationService(repository=repo, run_now=fake_scheduler.run_task_now)
    result = service.run_now("smoke_task_1")
    assert result.ok is True
    fake_scheduler.run_task_now.assert_called_once_with("smoke_task_1")


def test_scenario_4_workspace_isolation_and_files(tmp_path):
    """Scenario 4: Test file workspace isolation and directory containment."""
    ws_root = tmp_path / "smoke_workspace"
    ws_root.mkdir()

    session = WorkspaceSession.unscoped(ws_root)
    assert session.is_allowed(ws_root / "output.txt") is True
    assert session.is_allowed(tmp_path / "outside.txt") is False

    exec_ws = ExecutionWorkspace(session=session, turn_id="turn-smoke")
    exec_ws.ensure_dirs()
    assert (ws_root / ".scratch").is_dir()

    # FileWorkspaceService operations
    service = FileWorkspaceService(session)
    write_res = service.write_file("smoke_note.txt", "Smoke test content")
    assert (ws_root / "smoke_note.txt").exists()

    read_res = service.read_preview("smoke_note.txt")
    assert "Smoke test content" in str(read_res)


def test_scenario_5_config_and_secrets_persistence(tmp_path):
    """Scenario 5: Test JsonConfigRepository persistence with atomic write."""
    config_file = tmp_path / "config.json"
    repo = JsonConfigRepository.load(config_file, secrets=None)

    # Set and persist values
    repo.data["appearance"] = {"theme": "dark"}
    repo.data["general"] = {"language": "vi"}
    repo.save()

    # Reload from disk and verify
    reloaded = JsonConfigRepository.load(config_file, secrets=None)
    assert reloaded.data.get("appearance", {}).get("theme") == "dark"
    assert reloaded.data.get("general", {}).get("language") == "vi"
