"""Shared test fixtures for finance_agent tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from finance_agent.config import Settings
from finance_agent.data.watchlist import add_company
from finance_agent.db import get_connection, run_migrations


@pytest.fixture
def tmp_db(tmp_path: Path) -> sqlite3.Connection:
    """Provide a temporary SQLite database with all migrations applied."""
    db_path = str(tmp_path / "test.db")
    conn = get_connection(db_path)
    migrations_dir = str(Path(__file__).resolve().parent.parent / "migrations")
    run_migrations(conn, migrations_dir)
    yield conn
    conn.close()


@pytest.fixture
def mock_settings(tmp_path: Path) -> Settings:
    """Provide a Settings instance with test values (paper mode)."""
    return Settings(
        alpaca_paper_api_key="PKTEST1234567890",
        alpaca_paper_secret_key="secret_test_1234567890abcdef",
        trading_mode="paper",
        db_path=str(tmp_path / "test.db"),
        log_level="DEBUG",
    )


@pytest.fixture
def sample_company(tmp_db: sqlite3.Connection) -> dict[str, str | int | None]:
    """Add NVDA to the watchlist and return the company dict."""
    company_id = add_company(
        tmp_db,
        ticker="NVDA",
        name="NVIDIA Corporation",
        cik="0001045810",
        sector="Technology",
    )
    return {
        "id": company_id,
        "ticker": "NVDA",
        "name": "NVIDIA Corporation",
        "cik": "0001045810",
        "sector": "Technology",
    }


@pytest.fixture
def mock_anthropic_client() -> MagicMock:
    """Provide a mocked Anthropic client."""
    client = MagicMock()
    client.messages = MagicMock()
    return client
