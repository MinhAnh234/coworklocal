"""Task 4b — agent_security <-> agent_security_alert circular dependency is gone.

Before this fix, ``agent_security_alert.py`` imported ``SecurityVerdict`` from
``agent_security.py`` at module level (for the ``notify_admin`` type
annotation), while ``agent_security.py`` deferred-imported
``agent_security_alert.notify_admin`` inside ``enforce_prompt``/
``enforce_command`` — an architectural cycle only avoided at runtime by
pushing that second import inside a function body.

``SecurityVerdict``/``SecurityBlocked`` now live in the dependency-free leaf
module ``agent_security_types.py``. ``agent_security_alert.py`` imports the
type from there instead of from ``agent_security.py``, which lets
``agent_security.py`` import ``agent_security_alert.notify_admin`` at module
top level with no cycle.
"""
from __future__ import annotations

from cowork_local.core import (
    agent_security,
    agent_security_alert,
    agent_security_types,
)


def test_shared_types_live_in_the_leaf_module() -> None:
    assert agent_security.SecurityVerdict is agent_security_types.SecurityVerdict
    assert agent_security.SecurityBlocked is agent_security_types.SecurityBlocked
    assert agent_security_alert.SecurityVerdict is agent_security_types.SecurityVerdict


def test_agent_security_alert_no_longer_imports_agent_security() -> None:
    assert "agent_security" not in agent_security_alert.__dict__


def test_notify_admin_imported_at_module_top_level_in_agent_security() -> None:
    assert agent_security.notify_admin is agent_security_alert.notify_admin


def test_enforce_command_still_blocks_and_alerts_like_before(monkeypatch) -> None:
    class _FakeProvider:
        def chat(self, messages, tools=None):
            return {"content": '{"allowed": false, "reason": "destructive"}'}

    class _Config:
        data = {"agent_security": {"enabled": True, "validate_commands": True,
                                    "command_ai_check": True}}
        ms365 = {}

        @property
        def agent_security(self):
            return self.data["agent_security"]

    notify_calls = []
    record_calls = []
    monkeypatch.setattr(agent_security, "notify_admin",
                        lambda config, verdict, detail="": notify_calls.append((verdict, detail)))
    from cowork_local.core import audit_log
    monkeypatch.setattr(audit_log, "record",
                        lambda *a, **k: record_calls.append((a, k)))

    emitted = []
    raised = False
    try:
        agent_security.enforce_command(
            _FakeProvider(), "run_command", {"command": "rm -rf /"}, _Config(),
            emit=emitted.append,
        )
    except agent_security.SecurityBlocked as exc:
        raised = True
        assert exc.verdict.layer == "command"

    assert raised is True
    assert notify_calls
    assert record_calls
    assert emitted and emitted[0]["type"] == "notice"
