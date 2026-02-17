"""Unit tests for the MCP research server tools."""

from __future__ import annotations

import sqlite3
from pathlib import Path

# --- Helper: call tools directly with a test DB ---

def _call_tool(tool_fn, mcp_db_path: str, tmp_path: Path | None = None, **kwargs):
    """Call an MCP tool function with DB_PATH and RESEARCH_DATA_DIR patched.

    FastMCP's @mcp.tool() wraps functions into FunctionTool objects.
    We access the original function via .fn to call it directly in tests.
    """
    import finance_agent.mcp.research_server as srv

    # Get the underlying function from FunctionTool wrapper
    fn = tool_fn.fn if hasattr(tool_fn, "fn") else tool_fn

    original_db = srv.DB_PATH
    original_dir = srv.RESEARCH_DATA_DIR
    srv.DB_PATH = mcp_db_path
    if tmp_path is not None:
        srv.RESEARCH_DATA_DIR = tmp_path
    try:
        return fn(**kwargs)
    finally:
        srv.DB_PATH = original_db
        srv.RESEARCH_DATA_DIR = original_dir


# ============================================================
# US1: get_signals, list_documents, get_watchlist
# ============================================================


class TestGetSignals:
    """Tests for the get_signals tool (FR-001)."""

    def test_returns_signals_for_ticker(self, mcp_db: sqlite3.Connection, mcp_db_path: str):
        from finance_agent.mcp.research_server import get_signals

        result = _call_tool(get_signals, mcp_db_path, ticker="AAPL")
        assert len(result) == 2
        assert result[0]["ticker"] == "AAPL"
        assert result[0]["signal_type"] == "revenue_growth"
        assert result[0]["confidence"] == "high"
        assert "source_document_title" in result[0]

    def test_empty_for_unknown_ticker(self, mcp_db: sqlite3.Connection, mcp_db_path: str):
        from finance_agent.mcp.research_server import get_signals

        result = _call_tool(get_signals, mcp_db_path, ticker="ZZZZ")
        assert result == []

    def test_signal_type_filter(self, mcp_db: sqlite3.Connection, mcp_db_path: str):
        from finance_agent.mcp.research_server import get_signals

        result = _call_tool(
            get_signals, mcp_db_path, ticker="AAPL", signal_type="revenue_growth"
        )
        assert len(result) == 1
        assert result[0]["signal_type"] == "revenue_growth"

    def test_limit_parameter(self, mcp_db: sqlite3.Connection, mcp_db_path: str):
        from finance_agent.mcp.research_server import get_signals

        result = _call_tool(get_signals, mcp_db_path, ticker="AAPL", limit=1)
        assert len(result) == 1

    def test_days_filter(self, mcp_db: sqlite3.Connection, mcp_db_path: str):
        from finance_agent.mcp.research_server import get_signals

        # days=0 should return nothing (signals are 1-2 days old)
        result = _call_tool(get_signals, mcp_db_path, ticker="AAPL", days=0)
        assert result == []


class TestListDocuments:
    """Tests for the list_documents tool (FR-002)."""

    def test_returns_all_documents(self, mcp_db: sqlite3.Connection, mcp_db_path: str):
        from finance_agent.mcp.research_server import list_documents

        result = _call_tool(list_documents, mcp_db_path)
        assert len(result) == 2

    def test_filter_by_ticker(self, mcp_db: sqlite3.Connection, mcp_db_path: str):
        from finance_agent.mcp.research_server import list_documents

        result = _call_tool(list_documents, mcp_db_path, ticker="AAPL")
        assert len(result) == 1
        assert result[0]["ticker"] == "AAPL"

    def test_filter_by_content_type(self, mcp_db: sqlite3.Connection, mcp_db_path: str):
        from finance_agent.mcp.research_server import list_documents

        result = _call_tool(list_documents, mcp_db_path, content_type="10-K")
        assert len(result) == 1
        assert result[0]["content_type"] == "10-K"

    def test_empty_for_unknown_content_type(self, mcp_db: sqlite3.Connection, mcp_db_path: str):
        from finance_agent.mcp.research_server import list_documents

        result = _call_tool(list_documents, mcp_db_path, content_type="nonexistent")
        assert result == []


class TestGetWatchlist:
    """Tests for the get_watchlist tool (FR-004)."""

    def test_returns_active_companies(self, mcp_db: sqlite3.Connection, mcp_db_path: str):
        from finance_agent.mcp.research_server import get_watchlist

        result = _call_tool(get_watchlist, mcp_db_path)
        assert len(result) == 2
        tickers = [c["ticker"] for c in result]
        assert "AAPL" in tickers
        assert "MSFT" in tickers

    def test_excludes_inactive_companies(self, mcp_db: sqlite3.Connection, mcp_db_path: str):
        from finance_agent.mcp.research_server import get_watchlist

        # Deactivate MSFT
        mcp_db.execute("UPDATE company SET active = 0 WHERE ticker = 'MSFT'")
        mcp_db.commit()

        result = _call_tool(get_watchlist, mcp_db_path)
        assert len(result) == 1
        assert result[0]["ticker"] == "AAPL"

    def test_empty_watchlist(self, tmp_path: Path):
        """Test with a fresh empty DB."""
        from finance_agent.db import get_connection, run_migrations
        from finance_agent.mcp.research_server import get_watchlist

        db_path = str(tmp_path / "empty.db")
        conn = get_connection(db_path)
        migrations_dir = str(Path(__file__).resolve().parent.parent.parent / "migrations")
        run_migrations(conn, migrations_dir)
        conn.close()

        result = _call_tool(get_watchlist, db_path)
        assert result == []


# ============================================================
# US2: get_safety_state, get_audit_log, get_pipeline_status
# ============================================================


class TestGetSafetyState:
    """Tests for the get_safety_state tool (FR-005)."""

    def test_returns_kill_switch_and_risk_settings(
        self, mcp_db: sqlite3.Connection, mcp_db_path: str
    ):
        from finance_agent.mcp.research_server import get_safety_state

        result = _call_tool(get_safety_state, mcp_db_path)
        assert "kill_switch" in result
        assert "risk_settings" in result
        assert result["kill_switch"]["active"] is False
        assert result["risk_settings"]["max_trades_per_day"] == 20

    def test_kill_switch_active(self, mcp_db: sqlite3.Connection, mcp_db_path: str):
        import json

        from finance_agent.mcp.research_server import get_safety_state

        mcp_db.execute(
            "UPDATE safety_state SET value = ? WHERE key = 'kill_switch'",
            (json.dumps({"active": True, "toggled_at": "2026-02-17T10:00:00Z",
                         "toggled_by": "user"}),),
        )
        mcp_db.commit()

        result = _call_tool(get_safety_state, mcp_db_path)
        assert result["kill_switch"]["active"] is True
        assert result["kill_switch"]["toggled_by"] == "user"

    def test_missing_safety_state(self, tmp_path: Path):
        """Test with a DB where safety_state rows are missing."""
        from finance_agent.db import get_connection, run_migrations
        from finance_agent.mcp.research_server import get_safety_state

        db_path = str(tmp_path / "no_safety.db")
        conn = get_connection(db_path)
        migrations_dir = str(Path(__file__).resolve().parent.parent.parent / "migrations")
        run_migrations(conn, migrations_dir)
        # Delete safety_state rows (migrations seed defaults)
        conn.execute("DELETE FROM safety_state")
        conn.commit()
        conn.close()

        result = _call_tool(get_safety_state, db_path)
        assert "error" in result


class TestGetAuditLog:
    """Tests for the get_audit_log tool (FR-006)."""

    def test_returns_entries(self, mcp_db: sqlite3.Connection, mcp_db_path: str):
        from finance_agent.mcp.research_server import get_audit_log

        result = _call_tool(get_audit_log, mcp_db_path)
        assert len(result) == 2
        assert result[0]["event_type"] in ("pipeline_started", "signal_created")
        # Payload should be parsed from JSON
        assert isinstance(result[0]["payload"], dict)

    def test_filter_by_event_type(self, mcp_db: sqlite3.Connection, mcp_db_path: str):
        from finance_agent.mcp.research_server import get_audit_log

        result = _call_tool(get_audit_log, mcp_db_path, event_type="signal_created")
        assert len(result) == 1
        assert result[0]["event_type"] == "signal_created"

    def test_empty_audit_log(self, tmp_path: Path):
        from finance_agent.db import get_connection, run_migrations
        from finance_agent.mcp.research_server import get_audit_log

        db_path = str(tmp_path / "empty_audit.db")
        conn = get_connection(db_path)
        migrations_dir = str(Path(__file__).resolve().parent.parent.parent / "migrations")
        run_migrations(conn, migrations_dir)
        conn.close()

        result = _call_tool(get_audit_log, db_path)
        assert result == []


class TestGetPipelineStatus:
    """Tests for the get_pipeline_status tool (FR-007)."""

    def test_returns_latest_run(self, mcp_db: sqlite3.Connection, mcp_db_path: str):
        from finance_agent.mcp.research_server import get_pipeline_status

        result = _call_tool(get_pipeline_status, mcp_db_path)
        assert result["status"] == "completed"
        assert result["documents_ingested"] == 2
        assert result["signals_generated"] == 2
        assert isinstance(result["errors_json"], list)
        assert isinstance(result["sources_json"], list)

    def test_no_pipeline_runs(self, tmp_path: Path):
        from finance_agent.db import get_connection, run_migrations
        from finance_agent.mcp.research_server import get_pipeline_status

        db_path = str(tmp_path / "no_runs.db")
        conn = get_connection(db_path)
        migrations_dir = str(Path(__file__).resolve().parent.parent.parent / "migrations")
        run_migrations(conn, migrations_dir)
        conn.close()

        result = _call_tool(get_pipeline_status, db_path)
        assert result["status"] == "no_runs"


# ============================================================
# US4: read_document
# ============================================================


class TestReadDocument:
    """Tests for the read_document tool (FR-003, FR-010)."""

    def test_returns_document_with_content(
        self, mcp_db: sqlite3.Connection, mcp_db_path: str, tmp_path: Path
    ):
        from finance_agent.mcp.research_server import read_document

        # Create content file
        content_dir = tmp_path / "sec_filings" / "AAPL"
        content_dir.mkdir(parents=True)
        content_file = content_dir / "10-K_2025.md"
        content_file.write_text("# Apple 10-K\n\nRevenue grew 8% YoY.", encoding="utf-8")

        result = _call_tool(read_document, mcp_db_path, tmp_path=tmp_path, document_id=1)
        assert result["ticker"] == "AAPL"
        assert result["title"] == "Apple Inc. 10-K (2025)"
        assert "Revenue grew 8%" in result["content"]
        assert result["truncated"] is False

    def test_document_not_found(self, mcp_db: sqlite3.Connection, mcp_db_path: str):
        from finance_agent.mcp.research_server import read_document

        result = _call_tool(read_document, mcp_db_path, document_id=999)
        assert "error" in result

    def test_file_missing_from_disk(
        self, mcp_db: sqlite3.Connection, mcp_db_path: str, tmp_path: Path
    ):
        from finance_agent.mcp.research_server import read_document

        # Don't create the content file — just query the DB record
        result = _call_tool(read_document, mcp_db_path, tmp_path=tmp_path, document_id=1)
        assert result["content"] is None
        assert "not found on disk" in result["truncated_message"]

    def test_content_truncation(
        self, mcp_db: sqlite3.Connection, mcp_db_path: str, tmp_path: Path
    ):
        from finance_agent.mcp.research_server import read_document

        # Create a file > 50K chars
        content_dir = tmp_path / "sec_filings" / "AAPL"
        content_dir.mkdir(parents=True)
        content_file = content_dir / "10-K_2025.md"
        content_file.write_text("x" * 60_000, encoding="utf-8")

        result = _call_tool(read_document, mcp_db_path, tmp_path=tmp_path, document_id=1)
        assert result["truncated"] is True
        assert len(result["content"]) == 50_000
        assert "60,000" in result["truncated_message"]
