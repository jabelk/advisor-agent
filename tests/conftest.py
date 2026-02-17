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


@pytest.fixture
def mcp_db(tmp_path: Path) -> sqlite3.Connection:
    """Provide a populated test database for MCP server tool tests.

    Includes: 2 companies, 2 source documents, 2 research signals,
    safety_state rows, audit_log entries, and an ingestion_run record.
    """

    db_path = str(tmp_path / "mcp_test.db")
    conn = get_connection(db_path)
    migrations_dir = str(Path(__file__).resolve().parent.parent / "migrations")
    run_migrations(conn, migrations_dir)

    # Companies
    conn.execute(
        "INSERT INTO company (id, ticker, name, cik, sector, active) "
        "VALUES (1, 'AAPL', 'Apple Inc.', '0000320193', 'Technology', 1)"
    )
    conn.execute(
        "INSERT INTO company (id, ticker, name, cik, sector, active) "
        "VALUES (2, 'MSFT', 'Microsoft Corporation', '0000789019', 'Technology', 1)"
    )

    # Source documents
    conn.execute(
        "INSERT INTO source_document "
        "(id, company_id, source_type, content_type, source_id, title, "
        "published_at, content_hash, local_path, file_size_bytes, analysis_status) "
        "VALUES (1, 1, 'sec_edgar', '10-K', 'edgar:AAPL:10-K:2025', "
        "'Apple Inc. 10-K (2025)', '2025-11-01T00:00:00Z', 'abc123', "
        "'sec_filings/AAPL/10-K_2025.md', 24500, 'complete')"
    )
    conn.execute(
        "INSERT INTO source_document "
        "(id, company_id, source_type, content_type, source_id, title, "
        "published_at, content_hash, local_path, file_size_bytes, analysis_status) "
        "VALUES (2, 2, 'finnhub', 'analyst_ratings', 'finnhub:MSFT:recommendation_trends:2026-02', "
        "'MSFT Analyst Ratings (Feb 2026)', '2026-02-01T00:00:00Z', 'def456', "
        "'market_data/finnhub/MSFT/analyst_ratings_2026-02.md', 5000, 'complete')"
    )

    # Research signals
    conn.execute(
        "INSERT INTO research_signal "
        "(id, company_id, document_id, signal_type, evidence_type, confidence, "
        "summary, details, created_at) "
        "VALUES (1, 1, 1, 'revenue_growth', 'quantitative', 'high', "
        "'Q4 revenue grew 8% YoY driven by Services', 'Detailed analysis...', "
        "datetime('now', '-1 day'))"
    )
    conn.execute(
        "INSERT INTO research_signal "
        "(id, company_id, document_id, signal_type, evidence_type, confidence, "
        "summary, details, created_at) "
        "VALUES (2, 1, 1, 'management_concern', 'qualitative', 'medium', "
        "'CEO noted supply chain risks in China', NULL, "
        "datetime('now', '-2 days'))"
    )

    # Audit log entries
    conn.execute(
        "INSERT INTO audit_log (event_type, source, payload) "
        "VALUES ('pipeline_started', 'research.orchestrator', "
        "'{\"sources\": [\"sec_edgar\"]}')"
    )
    conn.execute(
        "INSERT INTO audit_log (event_type, source, payload) "
        "VALUES ('signal_created', 'research.analyzer', "
        "'{\"signal_id\": 1, \"ticker\": \"AAPL\"}')"
    )

    # Ingestion run
    conn.execute(
        "INSERT INTO ingestion_run "
        "(id, started_at, completed_at, status, documents_ingested, signals_generated, "
        "errors_json, sources_json) "
        "VALUES (1, datetime('now', '-1 hour'), datetime('now', '-50 minutes'), "
        "'completed', 2, 2, '[]', '[\"sec_edgar\", \"finnhub\"]')"
    )

    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def mcp_db_path(mcp_db: sqlite3.Connection, tmp_path: Path) -> str:
    """Return the file path to the MCP test database."""
    return str(tmp_path / "mcp_test.db")
