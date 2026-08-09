from __future__ import annotations

from cowork_local.config import AppConfig, DEFAULT_CONFIG


def test_unlock_codes_have_no_shared_default() -> None:
    assert DEFAULT_CONFIG["agent_security"]["sandbox_pw"] == ""
    assert DEFAULT_CONFIG["ms365"]["unlock_code"] == ""


def test_unlock_codes_can_be_supplied_by_environment(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("COWORK_SANDBOX_PASSWORD", "sandbox-test-only")
    monkeypatch.setenv("COWORK_MS365_UNLOCK_CODE", "ms365-test-only")

    config = AppConfig.load(tmp_path / "missing.json")

    assert config.agent_security["sandbox_pw"] == "sandbox-test-only"
    assert config.ms365["unlock_code"] == "ms365-test-only"
