"""Unit tests for MCP Pattern Lab tools (015-mcp-pattern-tools).

Tests run_backtest, run_ab_test, and export_backtest MCP tool functions
with mocked market data to avoid Alpaca API calls.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest


def _call_tool(tool_fn, mcp_db_path: str, env_vars: dict | None = None, **kwargs):
    """Call an MCP tool function with DB_PATH patched and optional env vars.

    If env_vars is an empty dict, clears ALPACA keys from environment.
    If env_vars has keys, sets them in environment.
    If env_vars is None, does not touch environment.
    """
    import finance_agent.mcp.research_server as srv

    fn = tool_fn.fn if hasattr(tool_fn, "fn") else tool_fn

    original_db = srv.DB_PATH
    srv.DB_PATH = mcp_db_path
    try:
        if env_vars is not None:
            # Ensure we control the Alpaca keys — remove them first, then set what's provided
            clean_env = {"ALPACA_PAPER_API_KEY": "", "ALPACA_PAPER_SECRET_KEY": ""}
            clean_env.update(env_vars)
            with patch.dict("os.environ", clean_env):
                return fn(**kwargs)
        return fn(**kwargs)
    finally:
        srv.DB_PATH = original_db


def _make_bars(ticker: str, n: int = 20) -> list[dict]:
    """Generate synthetic price bars for testing."""
    bars = []
    for i in range(n):
        bars.append({
            "ticker": ticker,
            "timeframe": "day",
            "bar_timestamp": f"2024-{((i // 28) + 1):02d}-{(i % 28) + 1:02d}T00:00:00Z",
            "open": 100.0 + i,
            "high": 105.0 + i,
            "low": 95.0 + i,
            "close": 102.0 + i,
            "volume": 1_000_000 + i * 10_000,
            "vwap": 101.0 + i,
        })
    return bars


@pytest.fixture
def pattern_db(tmp_path: Path) -> tuple[sqlite3.Connection, str]:
    """Provide a test database with a confirmed qualitative pattern."""
    from finance_agent.db import get_connection, run_migrations

    db_path = str(tmp_path / "pattern_test.db")
    conn = get_connection(db_path)
    migrations_dir = str(Path(__file__).resolve().parent.parent.parent / "migrations")
    run_migrations(conn, migrations_dir)

    # Insert a qualitative pattern with backtested status
    rule_set = {
        "trigger_type": "qualitative",
        "trigger_conditions": [
            {"field": "price_change_pct", "operator": ">=", "value": "5.0", "description": "5% spike"},
            {"field": "volume_spike", "operator": ">=", "value": "1.5", "description": "1.5x volume"},
        ],
        "entry_signal": {
            "condition": "pullback_pct",
            "value": "2.0",
            "window_days": 2,
            "description": "2% pullback within 2 days",
        },
        "action": {
            "action_type": "buy_shares",
            "description": "Buy shares on pullback",
        },
        "exit_criteria": {
            "stop_loss_pct": 5.0,
            "profit_target_pct": 10.0,
            "max_hold_days": 30,
            "description": "5% stop loss, 10% profit target, 30 day max hold",
        },
    }
    conn.execute(
        "INSERT INTO trading_pattern (id, name, description, status, rule_set_json) "
        "VALUES (1, 'Test Pattern', 'A test pattern', 'backtested', ?)",
        (json.dumps(rule_set),),
    )

    # Insert a draft pattern for error testing
    conn.execute(
        "INSERT INTO trading_pattern (id, name, description, status, rule_set_json) "
        "VALUES (2, 'Draft Pattern', 'A draft pattern', 'draft', ?)",
        (json.dumps(rule_set),),
    )

    # Insert a second backtested pattern for A/B testing
    rule_set_2 = json.loads(json.dumps(rule_set))
    rule_set_2["trigger_conditions"] = [
        {"field": "price_change_pct", "operator": ">=", "value": "7.0", "description": "7% spike"},
        {"field": "volume_spike", "operator": ">=", "value": "2.0", "description": "2x volume"},
    ]
    conn.execute(
        "INSERT INTO trading_pattern (id, name, description, status, rule_set_json) "
        "VALUES (3, 'Test Pattern V2', 'A variant pattern', 'backtested', ?)",
        (json.dumps(rule_set_2),),
    )

    # Insert watchlist companies
    conn.execute(
        "INSERT INTO company (id, ticker, name, cik, sector, active) "
        "VALUES (1, 'ABBV', 'AbbVie Inc.', '0001551152', 'Healthcare', 1)"
    )

    conn.commit()
    yield conn, db_path
    conn.close()


# ============================================================
# _get_alpaca_keys helper
# ============================================================


class TestGetAlpacaKeys:
    """Tests for the _get_alpaca_keys helper."""

    def test_returns_keys_when_set(self):
        from finance_agent.mcp.research_server import _get_alpaca_keys

        with patch.dict("os.environ", {
            "ALPACA_PAPER_API_KEY": "test-key",
            "ALPACA_PAPER_SECRET_KEY": "test-secret",
        }):
            api_key, secret_key = _get_alpaca_keys()
            assert api_key == "test-key"
            assert secret_key == "test-secret"

    def test_raises_when_missing(self):
        from finance_agent.mcp.research_server import _get_alpaca_keys

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Alpaca API keys not configured"):
                _get_alpaca_keys()

    def test_raises_when_partial(self):
        from finance_agent.mcp.research_server import _get_alpaca_keys

        with patch.dict("os.environ", {"ALPACA_PAPER_API_KEY": "key"}, clear=True):
            with pytest.raises(ValueError, match="Alpaca API keys not configured"):
                _get_alpaca_keys()


# ============================================================
# run_backtest tool
# ============================================================


class TestRunBacktest:
    """Tests for the run_backtest MCP tool."""

    def test_missing_alpaca_keys(self, pattern_db):
        from finance_agent.mcp.research_server import run_backtest

        conn, db_path = pattern_db
        result = _call_tool(
            run_backtest, db_path, env_vars={},
            pattern_id=1, tickers="ABBV",
        )
        assert "error" in result
        assert "Alpaca API keys" in result["error"]

    def test_pattern_not_found(self, pattern_db):
        from finance_agent.mcp.research_server import run_backtest

        conn, db_path = pattern_db
        result = _call_tool(
            run_backtest, db_path,
            env_vars={"ALPACA_PAPER_API_KEY": "k", "ALPACA_PAPER_SECRET_KEY": "s"},
            pattern_id=99, tickers="ABBV",
        )
        assert result == {"error": "Pattern #99 not found."}

    def test_no_price_data(self, pattern_db):
        from finance_agent.mcp.research_server import run_backtest

        conn, db_path = pattern_db
        with patch("finance_agent.patterns.market_data.fetch_and_cache_bars", return_value=[]):
            result = _call_tool(
                run_backtest, db_path,
                env_vars={"ALPACA_PAPER_API_KEY": "k", "ALPACA_PAPER_SECRET_KEY": "s"},
                pattern_id=1, tickers="ABBV",
            )
        assert result == {"error": "No price data available for any ticker."}

    def test_falls_back_to_watchlist(self, pattern_db):
        from finance_agent.mcp.research_server import run_backtest

        conn, db_path = pattern_db
        bars = _make_bars("ABBV", 60)

        with patch("finance_agent.patterns.market_data.fetch_and_cache_bars", return_value=bars):
            result = _call_tool(
                run_backtest, db_path,
                env_vars={"ALPACA_PAPER_API_KEY": "k", "ALPACA_PAPER_SECRET_KEY": "s"},
                pattern_id=1,  # no tickers → falls back to watchlist (ABBV)
            )
        # Should not be an error — watchlist has ABBV
        assert "error" not in result
        assert result.get("pattern_name") == "Test Pattern"

    def test_single_ticker_qualitative(self, pattern_db):
        from finance_agent.mcp.research_server import run_backtest

        conn, db_path = pattern_db
        bars = _make_bars("ABBV", 60)

        with patch("finance_agent.patterns.market_data.fetch_and_cache_bars", return_value=bars):
            result = _call_tool(
                run_backtest, db_path,
                env_vars={"ALPACA_PAPER_API_KEY": "k", "ALPACA_PAPER_SECRET_KEY": "s"},
                pattern_id=1, tickers="ABBV",
                start_date="2024-01-01", end_date="2024-12-31",
            )
        assert "error" not in result
        assert result["pattern_name"] == "Test Pattern"
        assert result["pattern_id"] == 1
        assert "combined_report" in result
        assert "ticker_breakdowns" in result

    def test_multi_ticker_qualitative(self, pattern_db):
        from finance_agent.mcp.research_server import run_backtest

        conn, db_path = pattern_db

        def mock_fetch(conn, ticker, start, end, tf, api, secret):
            return _make_bars(ticker, 60)

        with patch("finance_agent.patterns.market_data.fetch_and_cache_bars", side_effect=mock_fetch):
            result = _call_tool(
                run_backtest, db_path,
                env_vars={"ALPACA_PAPER_API_KEY": "k", "ALPACA_PAPER_SECRET_KEY": "s"},
                pattern_id=1, tickers="ABBV,MRNA",
                start_date="2024-01-01", end_date="2024-12-31",
            )
        assert "error" not in result
        assert result["pattern_name"] == "Test Pattern"
        assert len(result["tickers"]) == 2

    def test_default_dates(self, pattern_db):
        from finance_agent.mcp.research_server import run_backtest

        conn, db_path = pattern_db
        bars = _make_bars("ABBV", 60)

        with patch("finance_agent.patterns.market_data.fetch_and_cache_bars", return_value=bars):
            result = _call_tool(
                run_backtest, db_path,
                env_vars={"ALPACA_PAPER_API_KEY": "k", "ALPACA_PAPER_SECRET_KEY": "s"},
                pattern_id=1, tickers="ABBV",
                # No start_date or end_date → defaults to 1 year ago / today
            )
        assert "error" not in result

    def test_empty_watchlist_no_tickers(self, tmp_path):
        from finance_agent.db import get_connection, run_migrations
        from finance_agent.mcp.research_server import run_backtest

        db_path = str(tmp_path / "empty_wl.db")
        conn = get_connection(db_path)
        migrations_dir = str(Path(__file__).resolve().parent.parent.parent / "migrations")
        run_migrations(conn, migrations_dir)

        # Insert a pattern but no companies
        rule_set = {
            "trigger_type": "qualitative",
            "trigger_conditions": [
                {"field": "price_change_pct", "operator": ">=", "value": "5.0", "description": "5%"},
                {"field": "volume_spike", "operator": ">=", "value": "1.5", "description": "1.5x"},
            ],
            "entry_signal": {"condition": "pullback_pct", "value": "2.0", "window_days": 2, "description": "2% pullback"},
            "action": {"action_type": "buy_shares", "description": "Buy shares"},
            "exit_criteria": {"stop_loss_pct": 5.0, "profit_target_pct": 10.0, "max_hold_days": 30, "description": "Standard exits"},
        }
        conn.execute(
            "INSERT INTO trading_pattern (id, name, description, status, rule_set_json) "
            "VALUES (1, 'Test', 'Test', 'backtested', ?)",
            (json.dumps(rule_set),),
        )
        conn.commit()
        conn.close()

        result = _call_tool(
            run_backtest, db_path,
            env_vars={"ALPACA_PAPER_API_KEY": "k", "ALPACA_PAPER_SECRET_KEY": "s"},
            pattern_id=1,
        )
        assert result == {"error": "No tickers specified and watchlist is empty."}


# ============================================================
# run_ab_test tool
# ============================================================


class TestRunABTest:
    """Tests for the run_ab_test MCP tool."""

    def test_fewer_than_2_ids(self, pattern_db):
        from finance_agent.mcp.research_server import run_ab_test

        conn, db_path = pattern_db
        result = _call_tool(
            run_ab_test, db_path,
            env_vars={"ALPACA_PAPER_API_KEY": "k", "ALPACA_PAPER_SECRET_KEY": "s"},
            pattern_ids="1", tickers="ABBV",
        )
        assert result == {"error": "A/B test requires at least 2 pattern IDs."}

    def test_invalid_pattern_ids_format(self, pattern_db):
        from finance_agent.mcp.research_server import run_ab_test

        conn, db_path = pattern_db
        result = _call_tool(
            run_ab_test, db_path,
            env_vars={"ALPACA_PAPER_API_KEY": "k", "ALPACA_PAPER_SECRET_KEY": "s"},
            pattern_ids="abc,def", tickers="ABBV",
        )
        assert "error" in result
        assert "Invalid" in result["error"]

    def test_no_tickers(self, pattern_db):
        from finance_agent.mcp.research_server import run_ab_test

        conn, db_path = pattern_db
        result = _call_tool(
            run_ab_test, db_path,
            env_vars={"ALPACA_PAPER_API_KEY": "k", "ALPACA_PAPER_SECRET_KEY": "s"},
            pattern_ids="1,3", tickers="",
        )
        assert result == {"error": "--tickers is required for A/B testing."}

    def test_pattern_not_found(self, pattern_db):
        from finance_agent.mcp.research_server import run_ab_test

        conn, db_path = pattern_db
        result = _call_tool(
            run_ab_test, db_path,
            env_vars={"ALPACA_PAPER_API_KEY": "k", "ALPACA_PAPER_SECRET_KEY": "s"},
            pattern_ids="1,99", tickers="ABBV",
        )
        assert result == {"error": "Pattern #99 not found."}

    def test_draft_pattern_rejected(self, pattern_db):
        from finance_agent.mcp.research_server import run_ab_test

        conn, db_path = pattern_db
        result = _call_tool(
            run_ab_test, db_path,
            env_vars={"ALPACA_PAPER_API_KEY": "k", "ALPACA_PAPER_SECRET_KEY": "s"},
            pattern_ids="1,2", tickers="ABBV",  # pattern 2 is draft
        )
        assert result == {"error": "Pattern #2 is in draft status. Confirm the pattern first."}

    def test_missing_alpaca_keys(self, pattern_db):
        from finance_agent.mcp.research_server import run_ab_test

        conn, db_path = pattern_db
        result = _call_tool(
            run_ab_test, db_path, env_vars={},
            pattern_ids="1,3", tickers="ABBV",
        )
        assert "error" in result
        assert "Alpaca API keys" in result["error"]

    def test_successful_ab_test(self, pattern_db):
        from finance_agent.mcp.research_server import run_ab_test

        conn, db_path = pattern_db

        def mock_fetch(conn, ticker, start, end, tf, api, secret):
            return _make_bars(ticker, 60)

        with patch("finance_agent.patterns.market_data.fetch_and_cache_bars", side_effect=mock_fetch):
            result = _call_tool(
                run_ab_test, db_path,
                env_vars={"ALPACA_PAPER_API_KEY": "k", "ALPACA_PAPER_SECRET_KEY": "s"},
                pattern_ids="1,3", tickers="ABBV",
                start_date="2024-01-01", end_date="2024-12-31",
            )
        assert "error" not in result
        assert result["pattern_ids"] == [1, 3]
        assert "variant_reports" in result
        assert "comparisons" in result
        assert "best_variant_id" in result


# ============================================================
# export_backtest tool
# ============================================================


class TestExportBacktest:
    """Tests for the export_backtest MCP tool."""

    def test_pattern_not_found(self, pattern_db):
        from finance_agent.mcp.research_server import export_backtest

        conn, db_path = pattern_db
        result = _call_tool(export_backtest, db_path, pattern_id=99)
        assert result == {"error": "Pattern #99 not found."}

    def test_no_backtest_results(self, pattern_db):
        from finance_agent.mcp.research_server import export_backtest

        conn, db_path = pattern_db
        result = _call_tool(export_backtest, db_path, pattern_id=1)
        assert "error" in result
        assert "No backtest results" in result["error"]

    def test_successful_export(self, pattern_db, tmp_path):
        from finance_agent.mcp.research_server import export_backtest

        conn, db_path = pattern_db

        # Insert a backtest result
        conn.execute(
            "INSERT INTO backtest_result "
            "(id, pattern_id, date_range_start, date_range_end, trigger_count, trade_count, "
            "win_count, total_return_pct, avg_return_pct, max_drawdown_pct, "
            "sharpe_ratio, regime_analysis_json, created_at) "
            "VALUES (1, 1, '2024-01-01', '2024-12-31', 10, 8, 3, -15.5, -1.9, 25.0, "
            "-0.3, '[]', datetime('now'))"
        )
        # Insert a trade
        conn.execute(
            "INSERT INTO backtest_trade "
            "(id, backtest_id, ticker, trigger_date, entry_date, entry_price, "
            "exit_date, exit_price, return_pct, action_type) "
            "VALUES (1, 1, 'ABBV', '2024-03-13', '2024-03-15', 150.0, "
            "'2024-04-01', 145.0, -3.3, 'buy_shares')"
        )
        conn.commit()

        output_dir = str(tmp_path / "exports")
        result = _call_tool(
            export_backtest, db_path,
            pattern_id=1, output_dir=output_dir,
        )
        assert "error" not in result
        assert result["pattern_id"] == 1
        assert result["backtest_id"] == 1
        assert Path(result["file_path"]).exists()
        content = Path(result["file_path"]).read_text()
        assert "Test Pattern" in content

    def test_specific_backtest_id(self, pattern_db, tmp_path):
        from finance_agent.mcp.research_server import export_backtest

        conn, db_path = pattern_db

        # Insert two backtest results
        for bt_id in (1, 2):
            conn.execute(
                "INSERT INTO backtest_result "
                "(id, pattern_id, date_range_start, date_range_end, trigger_count, trade_count, "
                "win_count, total_return_pct, avg_return_pct, max_drawdown_pct, "
                "sharpe_ratio, regime_analysis_json, created_at) "
                f"VALUES ({bt_id}, 1, '2024-01-01', '2024-12-31', 10, 8, 3, -15.5, -1.9, 25.0, "
                f"-0.3, '[]', datetime('now', '-{3 - bt_id} days'))"
            )
        conn.commit()

        output_dir = str(tmp_path / "exports")
        result = _call_tool(
            export_backtest, db_path,
            pattern_id=1, backtest_id=1, output_dir=output_dir,
        )
        assert result["backtest_id"] == 1

    def test_invalid_backtest_id(self, pattern_db):
        from finance_agent.mcp.research_server import export_backtest

        conn, db_path = pattern_db

        # Insert a backtest result with id=1
        conn.execute(
            "INSERT INTO backtest_result "
            "(id, pattern_id, date_range_start, date_range_end, trigger_count, trade_count, "
            "win_count, total_return_pct, avg_return_pct, max_drawdown_pct, "
            "sharpe_ratio, regime_analysis_json, created_at) "
            "VALUES (1, 1, '2024-01-01', '2024-12-31', 10, 8, 3, -15.5, -1.9, 25.0, "
            "-0.3, '[]', datetime('now'))"
        )
        conn.commit()

        result = _call_tool(export_backtest, db_path, pattern_id=1, backtest_id=99)
        assert "error" in result
        assert "not found" in result["error"]
