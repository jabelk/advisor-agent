"""FastMCP server exposing the finance agent research database as read-only tools.

Run via:
  stdio (default):  python -m finance_agent.mcp.research_server
  HTTP:             python -m finance_agent.mcp.research_server --http
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

DB_PATH = os.environ.get("DB_PATH", "data/finance_agent.db")
RESEARCH_DATA_DIR = Path(os.environ.get("RESEARCH_DATA_DIR", "research_data"))

mcp = FastMCP("Finance Agent Research DB")


def _get_readonly_conn() -> sqlite3.Connection:
    """Open a read-only SQLite connection with busy timeout for concurrent access."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    """Convert sqlite3.Row objects to plain dicts."""
    return [dict(row) for row in rows]


# --- Tool: get_signals (FR-001) ---


@mcp.tool()
def get_signals(
    ticker: str,
    limit: int = 20,
    signal_type: str = "",
    days: int = 30,
) -> list[dict[str, Any]]:
    """Query research signals for a company by ticker.

    Returns signals with type, confidence, summary, and source document references.
    Filter by signal_type (e.g. "revenue_growth") and date range (days back from now).
    """
    conn = _get_readonly_conn()
    try:
        rows = conn.execute(
            """
            SELECT
                rs.id, c.ticker, c.name AS company_name,
                rs.signal_type, rs.evidence_type, rs.confidence,
                rs.summary, rs.details,
                rs.document_id AS source_document_id,
                sd.title AS source_document_title,
                rs.created_at
            FROM research_signal rs
            JOIN company c ON rs.company_id = c.id
            JOIN source_document sd ON rs.document_id = sd.id
            WHERE c.ticker = ?
              AND rs.created_at >= datetime('now', '-' || ? || ' days')
              AND (? = '' OR rs.signal_type = ?)
            ORDER BY rs.created_at DESC
            LIMIT ?
            """,
            (ticker.upper(), str(days), signal_type, signal_type, limit),
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


# --- Tool: list_documents (FR-002) ---


@mcp.tool()
def list_documents(
    ticker: str = "",
    content_type: str = "",
    limit: int = 20,
    days: int = 90,
) -> list[dict[str, Any]]:
    """List ingested source documents, filterable by company ticker and content type.

    Returns document metadata: title, type, date, company, and analysis status.
    """
    conn = _get_readonly_conn()
    try:
        rows = conn.execute(
            """
            SELECT
                sd.id, c.ticker, c.name AS company_name,
                sd.source_type, sd.content_type, sd.title,
                sd.published_at, sd.ingested_at,
                sd.file_size_bytes, sd.analysis_status
            FROM source_document sd
            LEFT JOIN company c ON sd.company_id = c.id
            WHERE sd.ingested_at >= datetime('now', '-' || ? || ' days')
              AND (? = '' OR c.ticker = ?)
              AND (? = '' OR sd.content_type = ?)
            ORDER BY sd.ingested_at DESC
            LIMIT ?
            """,
            (str(days), ticker.upper(), ticker.upper(), content_type, content_type, limit),
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


# --- Tool: get_watchlist (FR-004) ---


@mcp.tool()
def get_watchlist() -> list[dict[str, Any]]:
    """List all active companies on the research watchlist.

    Returns ticker, name, CIK, sector, and date added for each tracked company.
    """
    conn = _get_readonly_conn()
    try:
        rows = conn.execute(
            """
            SELECT id, ticker, name, cik, sector, added_at
            FROM company
            WHERE active = 1
            ORDER BY ticker ASC
            """,
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


# --- Tool: get_safety_state (FR-005) ---


@mcp.tool()
def get_safety_state() -> dict[str, Any]:
    """Read the current safety state: kill switch status and all risk limit values.

    Returns kill switch active/inactive status with timestamp, and all configured
    risk limits (max position size, daily loss, trade count, etc.).
    """
    conn = _get_readonly_conn()
    try:
        rows = conn.execute(
            "SELECT key, value, updated_at, updated_by FROM safety_state"
        ).fetchall()

        if not rows:
            return {"error": "Safety state not initialized. Run migrations first."}

        result: dict[str, Any] = {}
        for row in rows:
            try:
                parsed = json.loads(row["value"])
            except (json.JSONDecodeError, TypeError):
                parsed = row["value"]
            result[row["key"]] = parsed
            result["updated_at"] = row["updated_at"]
        return result
    finally:
        conn.close()


# --- Tool: get_audit_log (FR-006) ---


@mcp.tool()
def get_audit_log(
    event_type: str = "",
    limit: int = 50,
    days: int = 7,
) -> list[dict[str, Any]]:
    """Retrieve recent audit log entries, filterable by event type.

    Returns timestamped entries with event type, source module, and payload details.
    """
    conn = _get_readonly_conn()
    try:
        rows = conn.execute(
            """
            SELECT id, timestamp, event_type, source, payload
            FROM audit_log
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
              AND (? = '' OR event_type = ?)
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (str(days), event_type, event_type, limit),
        ).fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            d = dict(row)
            try:
                d["payload"] = json.loads(d["payload"])
            except (json.JSONDecodeError, TypeError):
                pass
            results.append(d)
        return results
    finally:
        conn.close()


# --- Tool: get_pipeline_status (FR-007) ---


@mcp.tool()
def get_pipeline_status() -> dict[str, Any]:
    """Get the status of the most recent research pipeline run.

    Returns timing, completion status, document count, signal count, and any errors.
    """
    conn = _get_readonly_conn()
    try:
        row = conn.execute(
            """
            SELECT
                id, started_at, completed_at, status,
                documents_ingested, signals_generated,
                errors_json, sources_json
            FROM ingestion_run
            ORDER BY started_at DESC
            LIMIT 1
            """,
        ).fetchone()

        if not row:
            return {
                "status": "no_runs",
                "message": "No pipeline runs recorded yet. Run: uv run finance-agent research run",
            }

        result = dict(row)
        for json_field in ("errors_json", "sources_json"):
            try:
                result[json_field] = json.loads(result[json_field]) if result[json_field] else []
            except (json.JSONDecodeError, TypeError):
                result[json_field] = []
        return result
    finally:
        conn.close()


# --- Tool: read_document (FR-003, FR-010) ---

_MAX_CONTENT_CHARS = 50_000


@mcp.tool()
def read_document(document_id: int) -> dict[str, Any]:
    """Retrieve the full text content of a specific ingested document by ID.

    Returns document metadata and content from the local filesystem.
    Content is truncated at 50,000 characters with a note if the original is longer.
    """
    conn = _get_readonly_conn()
    try:
        row = conn.execute(
            """
            SELECT
                sd.id, c.ticker, c.name AS company_name,
                sd.source_type, sd.content_type, sd.title,
                sd.published_at, sd.local_path, sd.file_size_bytes
            FROM source_document sd
            LEFT JOIN company c ON sd.company_id = c.id
            WHERE sd.id = ?
            """,
            (document_id,),
        ).fetchone()

        if not row:
            return {"error": f"Document not found with ID {document_id}"}

        result = dict(row)
        local_path_str = result.pop("local_path")
        lp = Path(local_path_str)
        # StorageManager includes base_dir in returned paths (e.g. "research_data/filings/...")
        # Strip that prefix to avoid double-joining with RESEARCH_DATA_DIR
        rd_name = RESEARCH_DATA_DIR.name
        if lp.parts and lp.parts[0] == rd_name:
            lp = Path(*lp.parts[1:])
        content_path = RESEARCH_DATA_DIR / lp

        if content_path.exists():
            full_content = content_path.read_text(encoding="utf-8")
            if len(full_content) > _MAX_CONTENT_CHARS:
                result["content"] = full_content[:_MAX_CONTENT_CHARS]
                result["truncated"] = True
                result["truncated_message"] = (
                    f"Content truncated from {len(full_content):,} to "
                    f"{_MAX_CONTENT_CHARS:,} characters."
                )
            else:
                result["content"] = full_content
                result["truncated"] = False
                result["truncated_message"] = None
        else:
            result["content"] = None
            result["truncated"] = False
            result["truncated_message"] = (
                "Content file not found on disk. Metadata available only."
            )

        return result
    finally:
        conn.close()


# --- Tool: list_patterns (Pattern Lab) ---


@mcp.tool()
def list_patterns(
    status: str = "",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List trading patterns from Pattern Lab with status and key metrics.

    Returns pattern name, status, creation date, and latest backtest metrics if available.
    Filter by status: draft, backtested, paper_trading, retired.
    """
    conn = _get_readonly_conn()
    try:
        rows = conn.execute(
            """
            SELECT id, name, description, status, created_at, updated_at, retired_at
            FROM trading_pattern
            WHERE (? = '' OR status = ?)
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (status, status, limit),
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


@mcp.tool()
def get_pattern_detail(pattern_id: int) -> dict[str, Any]:
    """Get full details for a specific trading pattern including rules and performance.

    Returns pattern definition, parsed rules, backtest history, and paper trade records.
    """
    conn = _get_readonly_conn()
    try:
        pattern = conn.execute(
            "SELECT * FROM trading_pattern WHERE id = ?", (pattern_id,)
        ).fetchone()
        if not pattern:
            return {"error": f"Pattern #{pattern_id} not found"}

        result = dict(pattern)
        try:
            result["rule_set"] = json.loads(result.pop("rule_set_json"))
        except (json.JSONDecodeError, TypeError):
            result["rule_set"] = None

        # Latest backtest
        bt = conn.execute(
            "SELECT * FROM backtest_result WHERE pattern_id = ? ORDER BY created_at DESC LIMIT 1",
            (pattern_id,),
        ).fetchone()
        result["latest_backtest"] = dict(bt) if bt else None

        # Paper trade count
        pt_row = conn.execute(
            "SELECT COUNT(*) as cnt FROM paper_trade WHERE pattern_id = ?",
            (pattern_id,),
        ).fetchone()
        result["paper_trade_count"] = pt_row["cnt"] if pt_row else 0

        return result
    finally:
        conn.close()


@mcp.tool()
def get_backtest_results(pattern_id: int) -> list[dict[str, Any]]:
    """Get backtest results for a trading pattern including regime analysis.

    Returns all backtest runs with performance metrics, regime periods, and trade details.
    """
    conn = _get_readonly_conn()
    try:
        rows = conn.execute(
            """
            SELECT * FROM backtest_result
            WHERE pattern_id = ?
            ORDER BY created_at DESC
            """,
            (pattern_id,),
        ).fetchall()

        results = []
        for row in rows:
            d = dict(row)
            if d.get("regime_analysis_json"):
                try:
                    d["regimes"] = json.loads(d["regime_analysis_json"])
                except (json.JSONDecodeError, TypeError):
                    d["regimes"] = []
            else:
                d["regimes"] = []
            results.append(d)
        return results
    finally:
        conn.close()


@mcp.tool()
def get_paper_trade_summary(pattern_id: int) -> dict[str, Any]:
    """Get paper trading performance summary for a pattern.

    Returns total trades, win rate, cumulative P&L, and open position count.
    """
    conn = _get_readonly_conn()
    try:
        row = conn.execute(
            """
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losses,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl
            FROM paper_trade
            WHERE pattern_id = ? AND status = 'closed'
            """,
            (pattern_id,),
        ).fetchone()

        total = row["total_trades"] or 0
        open_row = conn.execute(
            "SELECT COUNT(*) as cnt FROM paper_trade WHERE pattern_id = ? AND status = 'executed'",
            (pattern_id,),
        ).fetchone()

        return {
            "pattern_id": pattern_id,
            "total_trades": total,
            "wins": row["wins"] or 0,
            "losses": row["losses"] or 0,
            "win_rate": (row["wins"] or 0) / total if total > 0 else 0.0,
            "total_pnl": row["total_pnl"] or 0.0,
            "avg_pnl": row["avg_pnl"] or 0.0,
            "open_trades": open_row["cnt"] if open_row else 0,
        }
    finally:
        conn.close()


# --- Entry point ---

if __name__ == "__main__":
    import sys

    if "--http" in sys.argv:
        mcp.run(transport="http", host="0.0.0.0", port=8000)
    else:
        mcp.run()
