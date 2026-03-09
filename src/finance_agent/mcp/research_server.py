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


def _get_readwrite_conn() -> sqlite3.Connection:
    """Open a read-write SQLite connection with busy timeout.

    Used by backtest and A/B test tools that write to the market data cache
    via fetch_and_cache_bars(). The tools are read-only in intent — the only
    write is caching price bars to avoid redundant Alpaca API calls.
    """
    conn = sqlite3.connect(f"file:{DB_PATH}", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def _get_alpaca_keys() -> tuple[str, str]:
    """Read Alpaca paper trading API keys from environment variables.

    Returns:
        Tuple of (api_key, secret_key).

    Raises:
        dict: Error dict if keys are not configured.
    """
    api_key = os.environ.get("ALPACA_PAPER_API_KEY", "")
    secret_key = os.environ.get("ALPACA_PAPER_SECRET_KEY", "")
    if not api_key or not secret_key:
        raise ValueError(
            "Alpaca API keys not configured. Set ALPACA_PAPER_API_KEY and ALPACA_PAPER_SECRET_KEY."
        )
    return api_key, secret_key


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


# --- Tool: run_backtest (015 — Pattern Lab MCP) ---


@mcp.tool()
def run_backtest(
    pattern_id: int,
    tickers: str = "",
    start_date: str = "",
    end_date: str = "",
) -> dict[str, Any]:
    """Run a multi-ticker backtest for a pattern, returning per-ticker breakdown and aggregate metrics.

    Fetches price data from Alpaca (cached), runs the appropriate backtest engine,
    and saves results. Read-only in intent — only writes to the market data cache.

    Args:
        pattern_id: Pattern ID to backtest.
        tickers: Comma-separated ticker list. Defaults to watchlist tickers.
        start_date: Start date YYYY-MM-DD. Defaults to 1 year ago.
        end_date: End date YYYY-MM-DD. Defaults to today.
    """
    from datetime import date, timedelta

    from finance_agent.patterns.market_data import fetch_and_cache_bars
    from finance_agent.patterns.models import EventDetectionConfig, RuleSet
    from finance_agent.patterns.storage import get_pattern, save_backtest_result

    # Validate Alpaca keys
    try:
        api_key, secret_key = _get_alpaca_keys()
    except ValueError as e:
        return {"error": str(e)}

    conn = _get_readwrite_conn()
    try:
        # Validate pattern exists
        pattern = get_pattern(conn, pattern_id)
        if not pattern:
            return {"error": f"Pattern #{pattern_id} not found."}

        # Parse dates with defaults
        if not end_date:
            end_date = date.today().isoformat()
        if not start_date:
            start_date = (date.today() - timedelta(days=365)).isoformat()

        # Parse tickers — fall back to watchlist
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()] if tickers else []
        if not ticker_list:
            from finance_agent.data.watchlist import list_companies

            companies = list_companies(conn)
            ticker_list = [c["ticker"] for c in companies]
            if not ticker_list:
                return {"error": "No tickers specified and watchlist is empty."}

        rule_set = RuleSet.model_validate_json(pattern["rule_set_json"])

        # Fetch price data for all tickers
        all_bars: dict[str, list[dict]] = {}
        for ticker in ticker_list:
            bars = fetch_and_cache_bars(
                conn, ticker, start_date, end_date, "day", api_key, secret_key,
            )
            if bars:
                all_bars[ticker] = bars

        if not all_bars:
            return {"error": "No price data available for any ticker."}

        # Route to appropriate backtest engine
        is_qualitative = rule_set.trigger_type.value == "qualitative"

        if is_qualitative:
            # Build event config from pattern's trigger conditions
            spike_threshold = None
            volume_multiple = None
            for tc in rule_set.trigger_conditions:
                if tc.field == "price_change_pct" and spike_threshold is None:
                    spike_threshold = float(tc.value)
                if tc.field == "volume_spike" and volume_multiple is None:
                    volume_multiple = float(tc.value)

            event_config = EventDetectionConfig(
                spike_threshold_pct=spike_threshold or 5.0,
                volume_multiple_min=volume_multiple or 1.5,
                entry_window_days=rule_set.entry_signal.window_days,
            )

            from finance_agent.patterns.backtest import (
                run_multi_ticker_news_dip_backtest,
                run_news_dip_backtest,
            )

            available_tickers = list(all_bars.keys())
            if len(available_tickers) == 1:
                ticker = available_tickers[0]
                report, no_entry_events = run_news_dip_backtest(
                    pattern_id=pattern_id,
                    rule_set=rule_set,
                    bars=all_bars[ticker],
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date,
                    event_config=event_config,
                    conn=conn,
                )
                save_backtest_result(conn, report)
                from finance_agent.patterns.models import AggregatedBacktestReport, TickerBreakdown

                agg = AggregatedBacktestReport(
                    pattern_id=pattern_id,
                    date_range_start=start_date,
                    date_range_end=end_date,
                    tickers=[ticker],
                    ticker_breakdowns=[
                        TickerBreakdown(
                            ticker=ticker,
                            events_detected=report.trigger_count,
                            trades_entered=report.trade_count,
                            win_count=report.win_count,
                            win_rate=report.win_count / report.trade_count if report.trade_count else 0.0,
                            avg_return_pct=report.avg_return_pct,
                            total_return_pct=report.total_return_pct,
                        )
                    ],
                    combined_report=report,
                    no_entry_events=no_entry_events,
                )
            else:
                agg = run_multi_ticker_news_dip_backtest(
                    pattern_id=pattern_id,
                    rule_set=rule_set,
                    all_bars=all_bars,
                    tickers=available_tickers,
                    start_date=start_date,
                    end_date=end_date,
                    event_config=event_config,
                    conn=conn,
                )
                save_backtest_result(conn, agg.combined_report)

            result = agg.model_dump()
        else:
            # Quantitative pattern — standard backtest engine
            from finance_agent.patterns.backtest import run_backtest as _run_backtest

            report = _run_backtest(
                pattern_id=pattern_id,
                rule_set=rule_set,
                bars_by_ticker=all_bars,
                start_date=start_date,
                end_date=end_date,
                conn=conn,
            )
            save_backtest_result(conn, report)
            result = report.model_dump()

        result["pattern_name"] = pattern["name"]
        return result
    finally:
        conn.close()


# --- Tool: run_ab_test (015 — Pattern Lab MCP) ---


@mcp.tool()
def run_ab_test(
    pattern_ids: str,
    tickers: str,
    start_date: str = "",
    end_date: str = "",
) -> dict[str, Any]:
    """Compare 2+ pattern variants on identical data with statistical significance testing.

    Runs each pattern variant against the same tickers and date range, then compares
    win rates (Fisher's exact test) and average returns (Welch's t-test).

    Args:
        pattern_ids: Comma-separated pattern IDs (e.g., "1,2,3").
        tickers: Comma-separated ticker list (required).
        start_date: Start date YYYY-MM-DD. Defaults to 1 year ago.
        end_date: End date YYYY-MM-DD. Defaults to today.
    """
    from datetime import date, timedelta

    from finance_agent.patterns.market_data import fetch_and_cache_bars
    from finance_agent.patterns.models import EventDetectionConfig, RuleSet
    from finance_agent.patterns.stats import run_ab_test as _run_ab_test
    from finance_agent.patterns.storage import get_pattern

    # Parse pattern IDs
    try:
        id_list = [int(x.strip()) for x in pattern_ids.split(",") if x.strip()]
    except ValueError:
        return {"error": "Invalid pattern_ids format. Use comma-separated integers (e.g., '1,2,3')."}

    if len(id_list) < 2:
        return {"error": "A/B test requires at least 2 pattern IDs."}

    # Parse tickers
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        return {"error": "--tickers is required for A/B testing."}

    # Validate Alpaca keys
    try:
        api_key, secret_key = _get_alpaca_keys()
    except ValueError as e:
        return {"error": str(e)}

    conn = _get_readwrite_conn()
    try:
        # Validate patterns exist and are confirmed
        event_configs: dict[int, tuple[RuleSet, EventDetectionConfig]] = {}
        for pid in id_list:
            pattern = get_pattern(conn, pid)
            if not pattern:
                return {"error": f"Pattern #{pid} not found."}
            if pattern["status"] == "draft":
                return {"error": f"Pattern #{pid} is in draft status. Confirm the pattern first."}

            rule_set = RuleSet.model_validate_json(pattern["rule_set_json"])

            spike_threshold = None
            volume_multiple = None
            for tc in rule_set.trigger_conditions:
                if tc.field == "price_change_pct" and spike_threshold is None:
                    spike_threshold = float(tc.value)
                if tc.field == "volume_spike" and volume_multiple is None:
                    volume_multiple = float(tc.value)

            event_config = EventDetectionConfig(
                spike_threshold_pct=spike_threshold or 5.0,
                volume_multiple_min=volume_multiple or 1.5,
                entry_window_days=rule_set.entry_signal.window_days,
            )
            event_configs[pid] = (rule_set, event_config)

        # Parse dates with defaults
        if not end_date:
            end_date = date.today().isoformat()
        if not start_date:
            start_date = (date.today() - timedelta(days=365)).isoformat()

        # Fetch price data
        all_bars: dict[str, list[dict]] = {}
        for ticker in ticker_list:
            bars = fetch_and_cache_bars(
                conn, ticker, start_date, end_date, "day", api_key, secret_key,
            )
            if bars:
                all_bars[ticker] = bars

        if not all_bars:
            return {"error": "No price data available for any ticker."}

        # Run A/B test
        result = _run_ab_test(
            conn=conn,
            pattern_ids=id_list,
            tickers=list(all_bars.keys()),
            start_date=start_date,
            end_date=end_date,
            all_bars=all_bars,
            event_configs=event_configs,
        )

        return result.model_dump()
    finally:
        conn.close()


# --- Tool: export_backtest (015 — Pattern Lab MCP) ---


@mcp.tool()
def export_backtest(
    pattern_id: int,
    backtest_id: int = 0,
    output_dir: str = "",
) -> dict[str, Any]:
    """Export backtest results for a pattern to a markdown file.

    Generates a detailed markdown report with performance metrics, trade log,
    and regime analysis. Writes the file to the local filesystem.

    Args:
        pattern_id: Pattern ID to export.
        backtest_id: Specific backtest result ID. Default: most recent.
        output_dir: Directory for export. Default: current directory.
    """
    from finance_agent.patterns.export import export_backtest_markdown, generate_export_path
    from finance_agent.patterns.storage import get_pattern

    conn = _get_readonly_conn()
    try:
        # Validate pattern exists
        pattern = get_pattern(conn, pattern_id)
        if not pattern:
            return {"error": f"Pattern #{pattern_id} not found."}

        # Fetch backtest result
        if backtest_id:
            bt_row = conn.execute(
                "SELECT * FROM backtest_result WHERE id = ? AND pattern_id = ?",
                (backtest_id, pattern_id),
            ).fetchone()
            if not bt_row:
                return {"error": f"Backtest #{backtest_id} not found for pattern #{pattern_id}."}
        else:
            bt_row = conn.execute(
                "SELECT * FROM backtest_result WHERE pattern_id = ? ORDER BY created_at DESC LIMIT 1",
                (pattern_id,),
            ).fetchone()
            if not bt_row:
                return {"error": f"No backtest results found for pattern #{pattern_id}. Run a backtest first."}

        backtest = dict(bt_row)
        actual_backtest_id = backtest["id"]

        # Fetch trades for this backtest
        trade_rows = conn.execute(
            "SELECT * FROM backtest_trade WHERE backtest_id = ? ORDER BY entry_date",
            (actual_backtest_id,),
        ).fetchall()
        trades = [dict(r) for r in trade_rows]

        # Generate markdown
        md_content = export_backtest_markdown(pattern, backtest, trades)

        # Write file
        file_path = generate_export_path(
            pattern_id, "backtest", output_dir if output_dir else None,
        )
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        Path(file_path).write_text(md_content, encoding="utf-8")

        return {
            "file_path": file_path,
            "pattern_id": pattern_id,
            "backtest_id": actual_backtest_id,
        }
    finally:
        conn.close()


# --- Option chain lookup ---


@mcp.tool()
def get_option_chain_history(
    ticker: str,
    date: str,
    option_type: str = "call",
    strike_min: float | None = None,
    strike_max: float | None = None,
    expiration_within_days: int = 45,
) -> dict[str, Any]:
    """Look up historical option contracts for a ticker around a specific date.

    Constructs candidate OCC symbols for strikes at standard increments,
    fetches bars for each, and returns contracts that had trading activity.

    Args:
        ticker: Underlying stock ticker (e.g., "ABBV")
        date: Target date (YYYY-MM-DD)
        option_type: "call" or "put" (default: "call")
        strike_min: Minimum strike price filter (optional)
        strike_max: Maximum strike price filter (optional)
        expiration_within_days: Only contracts expiring within N days (default: 45)
    """
    try:
        api_key, secret_key = _get_alpaca_keys()
    except ValueError as e:
        return {"error": str(e)}

    try:
        from datetime import date as date_type
        from datetime import timedelta

        target_date = date_type.fromisoformat(date)
    except ValueError:
        return {"error": f"Invalid date format: {date}. Use YYYY-MM-DD."}

    conn = _get_readwrite_conn()
    try:
        from finance_agent.patterns.option_data import (
            build_occ_symbol,
            fetch_and_cache_option_bars,
            find_nearest_expiration,
            _strike_increment,
        )

        # Determine strike range from stock price if not specified
        if strike_min is None or strike_max is None:
            from finance_agent.patterns.market_data import fetch_and_cache_bars

            stock_bars = fetch_and_cache_bars(
                conn, ticker,
                (target_date - timedelta(days=10)).isoformat(),
                (target_date + timedelta(days=5)).isoformat(),
                "day", api_key, secret_key,
            )
            if not stock_bars:
                return {"error": f"No stock price data for {ticker} around {date}."}

            # Find closest bar to target date
            closest_bar = min(stock_bars, key=lambda b: abs(
                (date_type.fromisoformat(b["bar_timestamp"][:10]) - target_date).days
            ))
            stock_price = closest_bar["close"]

            if strike_min is None:
                strike_min = stock_price * 0.85
            if strike_max is None:
                strike_max = stock_price * 1.15

        # Find nearest expiration
        expiration = find_nearest_expiration(
            target_date + timedelta(days=expiration_within_days // 2),
            prefer_monthly=True,
        )

        # Generate candidate strikes at standard increments
        increment = _strike_increment(strike_min)
        # Round strike_min down and strike_max up to nearest increment
        start_strike = (strike_min // increment) * increment
        end_strike = ((strike_max // increment) + 1) * increment

        contracts: list[dict] = []
        strike = start_strike
        while strike <= end_strike:
            symbol = build_occ_symbol(ticker, expiration, strike, option_type)
            fetch_start = (target_date - timedelta(days=5)).isoformat()
            fetch_end = (target_date + timedelta(days=5)).isoformat()

            bars = fetch_and_cache_option_bars(
                conn, symbol, fetch_start, fetch_end, api_key, secret_key,
            )

            if bars:
                # Find bar closest to target date
                best_bar = min(bars, key=lambda b: abs(
                    (date_type.fromisoformat(b["bar_timestamp"][:10]) - target_date).days
                ))
                contracts.append({
                    "symbol": symbol,
                    "strike": strike,
                    "expiration": expiration.isoformat(),
                    "type": option_type,
                    "close_price": best_bar["close"],
                    "volume": best_bar["volume"],
                    "pricing": "real",
                })

            strike = round(strike + increment, 2)

        if not contracts:
            return {"error": f"No option data found for {ticker} around {date}."}

        return {
            "ticker": ticker,
            "date": date,
            "contracts": contracts,
        }
    except Exception as e:
        return {"error": f"Option chain lookup failed: {e}"}
    finally:
        conn.close()


# --- Entry point ---

if __name__ == "__main__":
    import sys

    if "--http" in sys.argv:
        mcp.run(transport="http", host="0.0.0.0", port=8000)
    else:
        mcp.run()
