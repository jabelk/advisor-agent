"""Unit tests for finance_agent.config module."""

from __future__ import annotations

import pytest

from finance_agent.config import ConfigError, Settings, load_settings, validate_settings


class TestSettings:
    """Test Settings dataclass creation and mode detection."""

    def test_paper_mode_default(self) -> None:
        s = Settings(
            alpaca_paper_api_key="PK123",
            alpaca_paper_secret_key="SK123",
        )
        assert s.is_live is False
        assert s.mode_label == "PAPER MODE"
        assert s.active_api_key == "PK123"
        assert s.active_secret_key == "SK123"
        assert s.warnings == []

    def test_paper_mode_explicit(self) -> None:
        s = Settings(
            alpaca_paper_api_key="PK123",
            alpaca_paper_secret_key="SK123",
            trading_mode="paper",
        )
        assert s.is_live is False
        assert s.mode_label == "PAPER MODE"

    def test_trading_mode_case_insensitive(self) -> None:
        s = Settings(
            alpaca_paper_api_key="PK123",
            alpaca_paper_secret_key="SK123",
            trading_mode="PAPER",
        )
        assert s.trading_mode == "paper"
        assert s.is_live is False

    def test_live_mode_with_keys(self) -> None:
        s = Settings(
            alpaca_live_api_key="LK123",
            alpaca_live_secret_key="LS123",
            trading_mode="live",
        )
        assert s.is_live is True
        assert s.mode_label == "LIVE MODE"
        assert s.active_api_key == "LK123"
        assert s.active_secret_key == "LS123"

    def test_live_mode_missing_keys_raises(self) -> None:
        with pytest.raises(ConfigError, match="live API keys are missing"):
            Settings(trading_mode="live")

    def test_dual_keys_defaults_to_paper_with_warning(self) -> None:
        s = Settings(
            alpaca_paper_api_key="PK123",
            alpaca_paper_secret_key="SK123",
            alpaca_live_api_key="LK123",
            alpaca_live_secret_key="LS123",
        )
        assert s.is_live is False
        assert len(s.warnings) == 1
        assert "Live trading keys detected" in s.warnings[0]

    def test_defaults(self) -> None:
        s = Settings(
            alpaca_paper_api_key="PK123",
            alpaca_paper_secret_key="SK123",
        )
        assert s.trading_mode == "paper"
        assert s.db_path == "data/finance_agent.db"
        assert s.log_level == "INFO"


class TestValidateSettings:
    """Test configuration validation."""

    def test_valid_paper_settings(self) -> None:
        s = Settings(
            alpaca_paper_api_key="PK123",
            alpaca_paper_secret_key="SK123",
        )
        errors = validate_settings(s)
        assert errors == []

    def test_missing_paper_api_key(self) -> None:
        s = Settings(alpaca_paper_secret_key="SK123")
        errors = validate_settings(s)
        assert any("ALPACA_PAPER_API_KEY" in e for e in errors)

    def test_missing_paper_secret_key(self) -> None:
        s = Settings(alpaca_paper_api_key="PK123")
        errors = validate_settings(s)
        assert any("ALPACA_PAPER_SECRET_KEY" in e for e in errors)

    def test_missing_both_paper_keys(self) -> None:
        s = Settings()
        errors = validate_settings(s)
        assert len(errors) == 2

    def test_invalid_trading_mode(self) -> None:
        s = Settings(
            alpaca_paper_api_key="PK123",
            alpaca_paper_secret_key="SK123",
            trading_mode="demo",
        )
        errors = validate_settings(s)
        assert any("TRADING_MODE" in e for e in errors)

    def test_invalid_log_level(self) -> None:
        s = Settings(
            alpaca_paper_api_key="PK123",
            alpaca_paper_secret_key="SK123",
            log_level="VERBOSE",
        )
        errors = validate_settings(s)
        assert any("LOG_LEVEL" in e for e in errors)

    def test_valid_log_levels(self) -> None:
        for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            s = Settings(
                alpaca_paper_api_key="PK123",
                alpaca_paper_secret_key="SK123",
                log_level=level,
            )
            assert validate_settings(s) == []


class TestLoadSettings:
    """Test loading settings from environment."""

    def test_loads_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ALPACA_PAPER_API_KEY", "PK_ENV")
        monkeypatch.setenv("ALPACA_PAPER_SECRET_KEY", "SK_ENV")
        monkeypatch.setenv("TRADING_MODE", "paper")
        s = load_settings()
        assert s.alpaca_paper_api_key == "PK_ENV"
        assert s.alpaca_paper_secret_key == "SK_ENV"

    def test_defaults_when_env_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ALPACA_PAPER_API_KEY", raising=False)
        monkeypatch.delenv("ALPACA_PAPER_SECRET_KEY", raising=False)
        monkeypatch.delenv("TRADING_MODE", raising=False)
        monkeypatch.delenv("DB_PATH", raising=False)
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        s = load_settings()
        assert s.trading_mode == "paper"
        assert s.db_path == "data/finance_agent.db"
        assert s.log_level == "INFO"
