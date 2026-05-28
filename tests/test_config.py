import pytest

from app.core.config import Settings


def test_settings_reads_calculator_max_power_exponent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CALCULATOR_MAX_POWER_EXPONENT", "3")

    settings = Settings.from_env()

    assert settings.calculator_settings.max_power_exponent == 3


def test_settings_uses_default_calculator_max_power_exponent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CALCULATOR_MAX_POWER_EXPONENT", raising=False)

    settings = Settings.from_env()

    assert settings.calculator_settings.max_power_exponent == 8


def test_settings_rejects_invalid_calculator_max_power_exponent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CALCULATOR_MAX_POWER_EXPONENT", "not-an-int")

    with pytest.raises(ValueError, match="CALCULATOR_MAX_POWER_EXPONENT"):
        Settings.from_env()


def test_settings_reads_agent_planner_mode_and_llm_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_PLANNER_MODE", "llm")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")

    settings = Settings.from_env()

    assert settings.agent_planner_mode == "llm"
    assert settings.llm_api_key == "test-key"
    assert settings.llm_model == "test-model"
