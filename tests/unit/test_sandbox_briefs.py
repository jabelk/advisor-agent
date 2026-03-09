"""Unit tests for meeting brief and market commentary generation."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from finance_agent.db import get_connection, run_migrations
from finance_agent.sandbox.commentary import generate_commentary
from finance_agent.sandbox.meeting_prep import generate_meeting_brief

MIGRATIONS_DIR = str(Path(__file__).resolve().parent.parent.parent / "migrations")


@pytest.fixture
def db(tmp_path: Path) -> sqlite3.Connection:
    """Create a fresh DB with all migrations applied (for research signals)."""
    db_path = str(tmp_path / "test.db")
    conn = get_connection(db_path)
    run_migrations(conn, MIGRATIONS_DIR)
    return conn


@pytest.fixture
def mock_sf():
    """Create a mock Salesforce client with a test client preloaded."""
    sf = MagicMock()
    # Default: get_client returns a test contact via Contact.get + query for Tasks
    sf.Contact.get.return_value = {
        "Id": "003xxTEST001",
        "FirstName": "Test",
        "LastName": "Client",
        "Email": "test@example.com",
        "Phone": "555-000-0000",
        "Title": "Engineer",
        "Description": "Test client for briefs",
        "Age__c": 45,
        "Account_Value__c": 500000.0,
        "Risk_Tolerance__c": "growth",
        "Life_Stage__c": "accumulation",
        "Investment_Goals__c": "Long-term growth",
        "Household_Members__c": None,
        "CreatedDate": "2025-01-01T00:00:00.000+0000",
        "LastModifiedDate": "2025-06-01T00:00:00.000+0000",
    }
    sf.query.return_value = {"records": []}  # No tasks by default
    return sf


def _mock_anthropic_response(data: dict) -> MagicMock:
    """Create a mock Anthropic message response."""
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_content = MagicMock()
    mock_content.text = json.dumps(data)
    mock_message.content = [mock_content]
    mock_client.messages.create.return_value = mock_message
    return mock_client


class TestGenerateMeetingBrief:
    def test_returns_expected_structure(self, mock_sf):
        mock_data = {
            "client_summary": "Test Client is a 45-year-old engineer.",
            "portfolio_context": "Growth-oriented portfolio with $500K.",
            "market_conditions": "Markets are stable.",
            "talking_points": ["Review allocation", "Discuss goals", "Market update"],
        }
        mock_client = _mock_anthropic_response(mock_data)

        result = generate_meeting_brief(mock_sf, "003xxTEST001", anthropic_client=mock_client)

        assert result["client_id"] == "003xxTEST001"
        assert result["client_name"] == "Test Client"
        assert "generated_at" in result
        assert result["client_summary"] == mock_data["client_summary"]
        assert result["portfolio_context"] == mock_data["portfolio_context"]
        assert result["market_conditions"] == mock_data["market_conditions"]
        assert isinstance(result["talking_points"], list)
        assert len(result["talking_points"]) == 3
        assert isinstance(result["market_data_available"], bool)

    def test_nonexistent_client_raises(self, mock_sf):
        mock_sf.Contact.get.side_effect = Exception("NOT_FOUND")
        mock_client = _mock_anthropic_response({})
        with pytest.raises(ValueError, match="not found"):
            generate_meeting_brief(mock_sf, "003xxBAD", anthropic_client=mock_client)

    def test_no_research_signals(self, mock_sf):
        """No db_conn means no signals → market_data_available=False."""
        mock_data = {
            "client_summary": "Summary.",
            "portfolio_context": "Context.",
            "market_conditions": "No market data available.",
            "talking_points": ["Point 1", "Point 2", "Point 3"],
        }
        mock_client = _mock_anthropic_response(mock_data)

        result = generate_meeting_brief(mock_sf, "003xxTEST001", anthropic_client=mock_client)

        assert result["market_data_available"] is False

    def test_with_research_signals(self, mock_sf, db):
        """When db_conn has signals, market_data_available=True."""
        # Insert a company + source doc + signal into SQLite
        db.execute(
            "INSERT INTO company (id, ticker, name, cik, sector, active) "
            "VALUES (1, 'AAPL', 'Apple Inc.', '0000320193', 'Technology', 1)"
        )
        db.execute(
            "INSERT INTO source_document "
            "(id, company_id, source_type, content_type, source_id, title, "
            "published_at, content_hash, local_path, file_size_bytes, analysis_status) "
            "VALUES (1, 1, 'sec_edgar', '10-K', 'test:1', 'Test Doc', "
            "'2026-01-01', 'hash1', 'test.md', 1000, 'complete')"
        )
        db.execute(
            "INSERT INTO research_signal "
            "(company_id, document_id, signal_type, evidence_type, confidence, summary) "
            "VALUES (1, 1, 'revenue_growth', 'quantitative', 'high', 'Revenue grew 15%')"
        )
        db.commit()

        mock_data = {
            "client_summary": "Summary with market data.",
            "portfolio_context": "Context.",
            "market_conditions": "Revenue grew 15% for Apple.",
            "talking_points": ["Tech growth", "Portfolio review", "Risk assessment"],
        }
        mock_client = _mock_anthropic_response(mock_data)

        result = generate_meeting_brief(
            mock_sf, "003xxTEST001", anthropic_client=mock_client, db_conn=db
        )

        assert result["market_data_available"] is True
        assert "Revenue grew" in result["market_conditions"]


def _insert_research_signal(db: sqlite3.Connection) -> None:
    """Insert a company, source doc, and research signal for testing."""
    db.execute(
        "INSERT OR IGNORE INTO company (id, ticker, name, cik, sector, active) "
        "VALUES (1, 'AAPL', 'Apple Inc.', '0000320193', 'Technology', 1)"
    )
    db.execute(
        "INSERT OR IGNORE INTO source_document "
        "(id, company_id, source_type, content_type, source_id, title, "
        "published_at, content_hash, local_path, file_size_bytes, analysis_status) "
        "VALUES (1, 1, 'sec_edgar', '10-K', 'test:1', 'Test Doc', "
        "'2026-01-01', 'hash1', 'test.md', 1000, 'complete')"
    )
    db.execute(
        "INSERT INTO research_signal "
        "(company_id, document_id, signal_type, evidence_type, confidence, summary) "
        "VALUES (1, 1, 'revenue_growth', 'quantitative', 'high', 'S&P 500 up 12% YTD')"
    )
    db.commit()


class TestGenerateCommentary:
    def test_returns_expected_structure(self, db: sqlite3.Connection):
        mock_data = {
            "commentary": "Markets have shown resilience this quarter.",
            "data_points_cited": 2,
        }
        mock_client = _mock_anthropic_response(mock_data)

        result = generate_commentary(db, risk_tolerance="growth", anthropic_client=mock_client)

        assert result["segment"] == "growth risk tolerance"
        assert result["segment_criteria"] == {"risk_tolerance": "growth"}
        assert "generated_at" in result
        assert result["commentary"] == mock_data["commentary"]
        assert result["data_points_cited"] == 2
        assert isinstance(result["market_data_available"], bool)

    def test_with_risk_filter(self, db: sqlite3.Connection):
        mock_data = {"commentary": "Bond markets remain stable.", "data_points_cited": 1}
        mock_client = _mock_anthropic_response(mock_data)

        result = generate_commentary(db, risk_tolerance="conservative", anthropic_client=mock_client)
        assert "conservative" in result["segment"]

    def test_with_life_stage_filter(self, db: sqlite3.Connection):
        mock_data = {"commentary": "Pre-retirees should consider.", "data_points_cited": 0}
        mock_client = _mock_anthropic_response(mock_data)

        result = generate_commentary(db, life_stage="pre-retirement", anthropic_client=mock_client)
        assert "pre-retirement" in result["segment"]
        assert result["segment_criteria"] == {"life_stage": "pre-retirement"}

    def test_no_filters_general_overview(self, db: sqlite3.Connection):
        mock_data = {"commentary": "General market overview.", "data_points_cited": 0}
        mock_client = _mock_anthropic_response(mock_data)

        result = generate_commentary(db, anthropic_client=mock_client)
        assert "general overview" in result["segment"].lower()
        assert result["segment_criteria"] == {}

    def test_no_research_signals(self, db: sqlite3.Connection):
        mock_data = {"commentary": "No data available.", "data_points_cited": 0}
        mock_client = _mock_anthropic_response(mock_data)

        result = generate_commentary(db, risk_tolerance="growth", anthropic_client=mock_client)
        assert result["market_data_available"] is False

    def test_with_research_signals(self, db: sqlite3.Connection):
        _insert_research_signal(db)

        mock_data = {"commentary": "S&P 500 up 12% YTD.", "data_points_cited": 1}
        mock_client = _mock_anthropic_response(mock_data)

        result = generate_commentary(db, risk_tolerance="growth", anthropic_client=mock_client)
        assert result["market_data_available"] is True
