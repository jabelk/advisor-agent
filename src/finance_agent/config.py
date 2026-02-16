"""Configuration management: loads settings from environment variables."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

# Valid Python logging level names
_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    alpaca_paper_api_key: str = ""
    alpaca_paper_secret_key: str = ""
    alpaca_live_api_key: str = ""
    alpaca_live_secret_key: str = ""
    trading_mode: str = "paper"
    db_path: str = "data/finance_agent.db"
    log_level: str = "INFO"
    # Derived
    is_live: bool = field(init=False, default=False)
    warnings: list[str] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        self.trading_mode = self.trading_mode.lower()
        self.log_level = self.log_level.upper()
        self._detect_mode()

    def _detect_mode(self) -> None:
        """Apply mode detection logic from data-model.md."""
        has_live = bool(self.alpaca_live_api_key and self.alpaca_live_secret_key)

        if self.trading_mode == "live":
            if has_live:
                self.is_live = True
            else:
                raise ConfigError(
                    "TRADING_MODE=live but live API keys are missing. "
                    "Set ALPACA_LIVE_API_KEY and ALPACA_LIVE_SECRET_KEY."
                )
        else:
            # Paper mode (default)
            self.is_live = False
            if has_live:
                self.warnings.append(
                    "Live trading keys detected but TRADING_MODE is 'paper'. "
                    "Using paper mode. Set TRADING_MODE=live to enable live trading."
                )

    @property
    def active_api_key(self) -> str:
        if self.is_live:
            return self.alpaca_live_api_key
        return self.alpaca_paper_api_key

    @property
    def active_secret_key(self) -> str:
        if self.is_live:
            return self.alpaca_live_secret_key
        return self.alpaca_paper_secret_key

    @property
    def mode_label(self) -> str:
        return "LIVE MODE" if self.is_live else "PAPER MODE"


class ConfigError(Exception):
    """Raised when configuration is invalid or incomplete."""


def load_settings() -> Settings:
    """Load settings from environment variables (and .env file if present).

    Loading order per contracts/cli.md:
    1. Read .env file if present (via python-dotenv)
    2. Read environment variables (override .env)
    3. Apply defaults for optional settings
    4. Validate required settings
    """
    # Try to load .env file (python-dotenv is a dev dependency, may not be present)
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    settings = Settings(
        alpaca_paper_api_key=os.environ.get("ALPACA_PAPER_API_KEY", ""),
        alpaca_paper_secret_key=os.environ.get("ALPACA_PAPER_SECRET_KEY", ""),
        alpaca_live_api_key=os.environ.get("ALPACA_LIVE_API_KEY", ""),
        alpaca_live_secret_key=os.environ.get("ALPACA_LIVE_SECRET_KEY", ""),
        trading_mode=os.environ.get("TRADING_MODE", "paper"),
        db_path=os.environ.get("DB_PATH", "data/finance_agent.db"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )

    return settings


def validate_settings(settings: Settings) -> list[str]:
    """Validate settings and return list of errors (empty if valid)."""
    errors: list[str] = []

    # Check required keys for the active mode
    if settings.is_live:
        if not settings.alpaca_live_api_key:
            errors.append("Missing: ALPACA_LIVE_API_KEY")
        if not settings.alpaca_live_secret_key:
            errors.append("Missing: ALPACA_LIVE_SECRET_KEY")
    else:
        if not settings.alpaca_paper_api_key:
            errors.append("Missing: ALPACA_PAPER_API_KEY")
        if not settings.alpaca_paper_secret_key:
            errors.append("Missing: ALPACA_PAPER_SECRET_KEY")

    # Validate TRADING_MODE
    if settings.trading_mode not in ("paper", "live"):
        errors.append(
            f"Invalid TRADING_MODE: '{settings.trading_mode}' (must be 'paper' or 'live')"
        )

    # Validate LOG_LEVEL
    if settings.log_level not in _VALID_LOG_LEVELS:
        errors.append(
            f"Invalid LOG_LEVEL: '{settings.log_level}' "
            f"(must be one of: {', '.join(sorted(_VALID_LOG_LEVELS))})"
        )

    # Validate DB_PATH parent directory is writable
    db_parent = Path(settings.db_path).parent
    if db_parent.exists() and not os.access(db_parent, os.W_OK):
        errors.append(f"DB_PATH parent directory is not writable: {db_parent}")

    return errors


def configure_logging(settings: Settings) -> None:
    """Set up logging based on settings."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
