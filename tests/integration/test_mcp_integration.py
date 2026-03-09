"""Integration tests for the MCP research server.

Tests server startup, tool listing, and tool invocation via FastMCP test client.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from finance_agent.db import get_connection, run_migrations


@pytest.fixture
def populated_db(tmp_path: Path) -> tuple[str, Path]:
    """Create a populated DB and research_data dir for integration testing."""

    db_path = str(tmp_path / "integration.db")
    conn = get_connection(db_path)
    migrations_dir = str(Path(__file__).resolve().parent.parent.parent / "migrations")
    run_migrations(conn, migrations_dir)

    conn.execute(
        "INSERT INTO company (id, ticker, name, cik, sector, active) "
        "VALUES (1, 'AAPL', 'Apple Inc.', '0000320193', 'Technology', 1)"
    )
    conn.execute(
        "INSERT INTO source_document "
        "(id, company_id, source_type, content_type, source_id, title, "
        "published_at, content_hash, local_path, file_size_bytes, analysis_status) "
        "VALUES (1, 1, 'sec_edgar', '10-K', 'edgar:AAPL:10-K:2025', "
        "'Apple Inc. 10-K (2025)', '2025-11-01T00:00:00Z', 'abc123', "
        "'sec_filings/AAPL/10-K_2025.md', 500, 'complete')"
    )
    conn.execute(
        "INSERT INTO research_signal "
        "(id, company_id, document_id, signal_type, evidence_type, confidence, "
        "summary, created_at) "
        "VALUES (1, 1, 1, 'revenue_growth', 'quantitative', 'high', "
        "'Revenue grew 8%', datetime('now', '-1 day'))"
    )
    conn.execute(
        "INSERT INTO audit_log (event_type, source, payload) "
        "VALUES ('signal_created', 'test', '{\"signal_id\": 1}')"
    )
    conn.execute(
        "INSERT INTO ingestion_run "
        "(started_at, completed_at, status, documents_ingested, signals_generated, "
        "errors_json, sources_json) "
        "VALUES (datetime('now', '-1 hour'), datetime('now'), 'completed', 1, 1, '[]', "
        "'[\"sec_edgar\"]')"
    )

    # Create a content file
    content_dir = tmp_path / "sec_filings" / "AAPL"
    content_dir.mkdir(parents=True)
    (content_dir / "10-K_2025.md").write_text("Apple 10-K content", encoding="utf-8")

    conn.commit()
    conn.close()
    return db_path, tmp_path


class TestMCPServerIntegration:
    """Integration tests for the MCP server tools."""

    def test_all_tools_registered(self, populated_db: tuple[str, Path]):
        """Verify the server exposes all expected tools."""
        db_path, data_dir = populated_db
        import finance_agent.mcp.research_server as srv

        srv.DB_PATH = db_path
        srv.RESEARCH_DATA_DIR = data_dir

        # Access registered tools via the FastMCP server instance
        tools = srv.mcp._tool_manager._tools
        tool_names = set(tools.keys())

        expected = {
            "get_signals",
            "list_documents",
            "read_document",
            "get_watchlist",
            "get_safety_state",
            "get_audit_log",
            "get_pipeline_status",
            "list_patterns",
            "get_pattern_detail",
            "get_backtest_results",
            "get_paper_trade_summary",
            "run_backtest",
            "run_ab_test",
            "export_backtest",
            "get_option_chain_history",
            "get_pattern_alerts",
            "get_dashboard_summary",
            "get_performance_comparison",
        }
        missing = expected - tool_names
        extra = tool_names - expected
        assert tool_names == expected, f"Missing: {missing}, Extra: {extra}"

    def test_get_signals_via_server(self, populated_db: tuple[str, Path]):
        """Test get_signals returns data through the server."""
        db_path, data_dir = populated_db
        import finance_agent.mcp.research_server as srv

        srv.DB_PATH = db_path
        result = srv.get_signals.fn(ticker="AAPL")
        assert len(result) == 1
        assert result[0]["signal_type"] == "revenue_growth"

    def test_read_document_with_content(self, populated_db: tuple[str, Path]):
        """Test read_document returns file content."""
        db_path, data_dir = populated_db
        import finance_agent.mcp.research_server as srv

        srv.DB_PATH = db_path
        srv.RESEARCH_DATA_DIR = data_dir
        result = srv.read_document.fn(document_id=1)
        assert result["content"] == "Apple 10-K content"
        assert result["truncated"] is False

    def test_safety_state_has_defaults(self, populated_db: tuple[str, Path]):
        """Test get_safety_state returns migration defaults."""
        db_path, data_dir = populated_db
        import finance_agent.mcp.research_server as srv

        srv.DB_PATH = db_path
        result = srv.get_safety_state.fn()
        assert "kill_switch" in result
        assert result["kill_switch"]["active"] is False

    def test_read_only_enforcement(self, populated_db: tuple[str, Path]):
        """Test that the read-only connection prevents writes (FR-008)."""
        db_path, data_dir = populated_db
        import finance_agent.mcp.research_server as srv

        srv.DB_PATH = db_path
        conn = srv._get_readonly_conn()
        try:
            with pytest.raises(sqlite3.OperationalError, match="readonly"):
                conn.execute(
                    "INSERT INTO company (ticker, name, active) "
                    "VALUES ('TEST', 'Test', 1)"
                )
        finally:
            conn.close()
