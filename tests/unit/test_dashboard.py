"""Unit tests for dashboard aggregation and performance comparison."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from finance_agent.db import get_connection, run_migrations
from finance_agent.patterns.dashboard import (
    format_dashboard,
    format_performance,
    get_dashboard_data,
    get_performance_comparison,
)


MIGRATIONS_DIR = str(Path(__file__).resolve().parent.parent.parent / "migrations")


@pytest.fixture
def db(tmp_path: Path) -> sqlite3.Connection:
    """Create a fresh DB with all migrations applied."""
    db_path = str(tmp_path / "test.db")
    conn = get_connection(db_path)
    run_migrations(conn, MIGRATIONS_DIR)
    return conn


def _insert_pattern(conn: sqlite3.Connection, name: str, status: str = "draft") -> int:
    cur = conn.execute(
        "INSERT INTO trading_pattern (name, description, rule_set_json, status) VALUES (?, ?, '{}', ?)",
        (name, f"Test pattern {name}", status),
    )
    conn.commit()
    return cur.lastrowid


def _insert_backtest(
    conn: sqlite3.Connection, pattern_id: int, win_count: int, trade_count: int,
    avg_return_pct: float = 2.5, total_return_pct: float = 50.0,
    max_drawdown_pct: float = 8.0, sharpe_ratio: float | None = 1.2,
) -> int:
    cur = conn.execute(
        """INSERT INTO backtest_result
           (pattern_id, date_range_start, date_range_end, win_count, trade_count,
            avg_return_pct, total_return_pct, max_drawdown_pct, sharpe_ratio)
           VALUES (?, '2025-01-01', '2025-12-31', ?, ?, ?, ?, ?, ?)""",
        (pattern_id, win_count, trade_count, avg_return_pct, total_return_pct,
         max_drawdown_pct, sharpe_ratio),
    )
    conn.commit()
    return cur.lastrowid


def _insert_paper_trade(
    conn: sqlite3.Connection, pattern_id: int, ticker: str,
    status: str = "closed", pnl: float | None = 50.0,
) -> int:
    cur = conn.execute(
        """INSERT INTO paper_trade
           (pattern_id, ticker, direction, action_type, quantity, status, pnl)
           VALUES (?, ?, 'buy', 'stock', 100, ?, ?)""",
        (pattern_id, ticker, status, pnl),
    )
    conn.commit()
    return cur.lastrowid


def _insert_alert(
    conn: sqlite3.Connection, pattern_id: int, pattern_name: str,
    ticker: str, status: str = "new",
) -> int:
    cur = conn.execute(
        """INSERT INTO pattern_alert
           (pattern_id, pattern_name, ticker, trigger_date, trigger_details_json,
            recommended_action, status)
           VALUES (?, ?, ?, date('now'), '{}', 'Buy', ?)""",
        (pattern_id, pattern_name, ticker, status),
    )
    conn.commit()
    return cur.lastrowid


class TestGetDashboardData:
    """Tests for get_dashboard_data()."""

    def test_empty_database(self, db: sqlite3.Connection):
        data = get_dashboard_data(db)
        assert data["patterns"]["total"] == 0
        assert data["patterns"]["by_status"] == {}
        assert data["paper_trades"]["closed_trades"] == 0
        assert data["paper_trades"]["total_pnl"] == 0.0
        assert data["alerts"]["last_7_days"] == 0
        assert data["active_patterns"] == []

    def test_pattern_counts_by_status(self, db: sqlite3.Connection):
        _insert_pattern(db, "Draft 1", "draft")
        _insert_pattern(db, "Draft 2", "draft")
        _insert_pattern(db, "BT", "backtested")
        _insert_pattern(db, "PT", "paper_trading")

        data = get_dashboard_data(db)
        assert data["patterns"]["total"] == 4
        assert data["patterns"]["by_status"]["draft"] == 2
        assert data["patterns"]["by_status"]["backtested"] == 1
        assert data["patterns"]["by_status"]["paper_trading"] == 1

    def test_paper_trade_aggregation(self, db: sqlite3.Connection):
        pid = _insert_pattern(db, "PT1", "paper_trading")
        _insert_paper_trade(db, pid, "AAPL", "closed", 100.0)
        _insert_paper_trade(db, pid, "GOOG", "closed", -30.0)
        _insert_paper_trade(db, pid, "MSFT", "closed", 50.0)
        _insert_paper_trade(db, pid, "TSLA", "executed", None)  # open

        data = get_dashboard_data(db)
        assert data["paper_trades"]["closed_trades"] == 3
        assert data["paper_trades"]["wins"] == 2
        assert data["paper_trades"]["losses"] == 1
        assert data["paper_trades"]["total_pnl"] == pytest.approx(120.0)
        assert data["paper_trades"]["win_rate"] == pytest.approx(2 / 3)
        assert data["paper_trades"]["open_trades"] == 1

    def test_alert_counts_last_7_days(self, db: sqlite3.Connection):
        pid = _insert_pattern(db, "PT1", "paper_trading")
        _insert_alert(db, pid, "PT1", "AAPL", "new")
        _insert_alert(db, pid, "PT1", "GOOG", "new")
        _insert_alert(db, pid, "PT1", "MSFT", "acknowledged")

        data = get_dashboard_data(db)
        assert data["alerts"]["last_7_days"] == 3
        assert data["alerts"]["by_status"]["new"] == 2
        assert data["alerts"]["by_status"]["acknowledged"] == 1

    def test_active_pattern_summaries(self, db: sqlite3.Connection):
        pid = _insert_pattern(db, "Pharma Spike", "paper_trading")
        _insert_backtest(db, pid, win_count=10, trade_count=20)
        _insert_paper_trade(db, pid, "AAPL", "closed", 100.0)
        _insert_paper_trade(db, pid, "GOOG", "closed", -20.0)
        _insert_paper_trade(db, pid, "MSFT", "executed", None)
        _insert_alert(db, pid, "Pharma Spike", "AAPL")

        data = get_dashboard_data(db)
        assert len(data["active_patterns"]) == 1
        p = data["active_patterns"][0]
        assert p["pattern_name"] == "Pharma Spike"
        assert p["backtest_win_rate"] == pytest.approx(0.5)
        assert p["paper_trade_win_rate"] == pytest.approx(0.5)
        assert p["paper_trade_count"] == 2
        assert p["paper_trade_pnl"] == pytest.approx(80.0)
        assert p["open_trades"] == 1
        assert p["alert_count_7d"] == 1
        assert p["divergence_warning"] is False

    def test_divergence_warning_triggered(self, db: sqlite3.Connection):
        pid = _insert_pattern(db, "Divergent", "paper_trading")
        _insert_backtest(db, pid, win_count=10, trade_count=20)  # 50% BT
        # 100% PT win rate (1/1) — divergence > 10pp
        _insert_paper_trade(db, pid, "AAPL", "closed", 100.0)

        data = get_dashboard_data(db)
        p = data["active_patterns"][0]
        assert p["backtest_win_rate"] == pytest.approx(0.5)
        assert p["paper_trade_win_rate"] == pytest.approx(1.0)
        assert p["divergence_warning"] is True


class TestFormatDashboard:
    """Tests for format_dashboard()."""

    def test_empty_state_message(self):
        data = {
            "patterns": {"total": 0, "by_status": {}},
            "paper_trades": {"closed_trades": 0, "open_trades": 0, "wins": 0,
                             "losses": 0, "win_rate": 0.0, "total_pnl": 0.0,
                             "avg_pnl": 0.0, "total_trades": 0},
            "alerts": {"last_7_days": 0, "by_status": {}},
            "active_patterns": [],
        }
        output = format_dashboard(data)
        assert "No patterns found" in output
        assert "pattern describe" in output

    def test_formatted_output_contains_sections(self):
        data = {
            "patterns": {"total": 3, "by_status": {"draft": 1, "paper_trading": 2}},
            "paper_trades": {"closed_trades": 5, "open_trades": 1, "wins": 3,
                             "losses": 2, "win_rate": 0.6, "total_pnl": 200.0,
                             "avg_pnl": 40.0, "total_trades": 6},
            "alerts": {"last_7_days": 2, "by_status": {"new": 2}},
            "active_patterns": [
                {"pattern_id": 1, "pattern_name": "Test Pattern",
                 "backtest_win_rate": 0.5, "backtest_avg_return": 2.5,
                 "paper_trade_win_rate": 0.6, "paper_trade_count": 5,
                 "paper_trade_pnl": 200.0, "open_trades": 1,
                 "alert_count_7d": 2, "auto_execute": False,
                 "divergence_warning": False},
            ],
        }
        output = format_dashboard(data)
        assert "Portfolio Dashboard" in output
        assert "3 total" in output
        assert "Win rate: 60.0%" in output
        assert "+$200.00" in output
        assert "Active Patterns:" in output
        assert "Test Pattern" in output


class TestGetPerformanceComparison:
    """Tests for get_performance_comparison()."""

    def test_single_pattern_with_backtest_and_trades(self, db: sqlite3.Connection):
        pid = _insert_pattern(db, "Pharma Spike", "paper_trading")
        _insert_backtest(db, pid, win_count=10, trade_count=20, avg_return_pct=2.5)
        _insert_paper_trade(db, pid, "AAPL", "closed", 100.0)
        _insert_paper_trade(db, pid, "GOOG", "closed", -30.0)
        _insert_paper_trade(db, pid, "MSFT", "closed", 50.0)

        results = get_performance_comparison(db, pattern_id=pid)
        assert len(results) == 1
        c = results[0]
        assert c["pattern_name"] == "Pharma Spike"
        assert c["backtest"]["win_rate"] == pytest.approx(0.5)
        assert c["backtest"]["trade_count"] == 20
        assert c["paper_trading"]["win_rate"] == pytest.approx(2 / 3)
        assert c["paper_trading"]["trade_count"] == 3
        assert c["paper_trading"]["total_pnl"] == pytest.approx(120.0)

    def test_pattern_with_no_paper_trades(self, db: sqlite3.Connection):
        pid = _insert_pattern(db, "No Trades", "backtested")
        _insert_backtest(db, pid, win_count=8, trade_count=20)

        results = get_performance_comparison(db, pattern_id=pid)
        assert len(results) == 1
        c = results[0]
        assert c["paper_trading"]["trade_count"] == 0
        assert c["paper_trading"]["win_rate"] is None
        assert c["divergence"]["note"] == "No closed trades yet"

    def test_divergence_warning_over_10pp(self, db: sqlite3.Connection):
        pid = _insert_pattern(db, "Divergent", "paper_trading")
        _insert_backtest(db, pid, win_count=10, trade_count=20)  # 50%
        # 100% PT win rate
        _insert_paper_trade(db, pid, "AAPL", "closed", 100.0)

        results = get_performance_comparison(db, pattern_id=pid)
        c = results[0]
        assert c["divergence"]["win_rate_diff_pp"] == pytest.approx(50.0)
        assert c["divergence"]["warning"] is True

    def test_all_patterns_ranking(self, db: sqlite3.Connection):
        pid1 = _insert_pattern(db, "Pattern A", "paper_trading")
        _insert_backtest(db, pid1, win_count=10, trade_count=20)
        _insert_paper_trade(db, pid1, "AAPL", "closed", 100.0)

        pid2 = _insert_pattern(db, "Pattern B", "backtested")
        _insert_backtest(db, pid2, win_count=8, trade_count=20)

        results = get_performance_comparison(db)
        assert len(results) == 2
        assert results[0]["pattern_name"] == "Pattern A"
        assert results[1]["pattern_name"] == "Pattern B"

    def test_no_backtest_returns_empty(self, db: sqlite3.Connection):
        _insert_pattern(db, "Draft Only", "draft")
        results = get_performance_comparison(db)
        assert results == []


class TestFormatPerformance:
    """Tests for format_performance()."""

    def test_single_pattern_format(self):
        comp = [{
            "pattern_id": 1, "pattern_name": "Pharma Spike",
            "pattern_status": "paper_trading", "days_in_paper_trading": 30,
            "backtest": {"win_rate": 0.5, "avg_return_pct": 2.5, "trade_count": 20,
                         "total_return_pct": 50.0, "max_drawdown_pct": 8.2,
                         "sharpe_ratio": 1.2, "backtest_date": "2025-12-01"},
            "paper_trading": {"win_rate": 0.6, "avg_return_pct": 3.1, "trade_count": 5,
                              "total_pnl": 200.0, "open_trades": 0},
            "divergence": {"win_rate_diff_pp": 10.0, "avg_return_diff_pp": 0.6,
                           "warning": False, "note": None},
        }]
        output = format_performance(comp, single=True)
        assert "Performance: Pharma Spike (#1)" in output
        assert "50.0%" in output
        assert "60.0%" in output
        assert "+$200.00" in output

    def test_ranking_table_format(self):
        comps = [
            {"pattern_id": 1, "pattern_name": "Pattern A",
             "pattern_status": "paper_trading", "days_in_paper_trading": 30,
             "backtest": {"win_rate": 0.5, "avg_return_pct": 2.5, "trade_count": 20,
                          "total_return_pct": 50.0, "max_drawdown_pct": 8.0,
                          "sharpe_ratio": 1.0, "backtest_date": "2025-12-01"},
             "paper_trading": {"win_rate": 0.6, "avg_return_pct": 3.0, "trade_count": 5,
                               "total_pnl": 200.0, "open_trades": 0},
             "divergence": {"win_rate_diff_pp": 10.0, "avg_return_diff_pp": 0.5,
                            "warning": False, "note": None}},
            {"pattern_id": 2, "pattern_name": "Pattern B",
             "pattern_status": "backtested", "days_in_paper_trading": None,
             "backtest": {"win_rate": 0.4, "avg_return_pct": 1.5, "trade_count": 15,
                          "total_return_pct": 22.0, "max_drawdown_pct": 5.0,
                          "sharpe_ratio": 0.8, "backtest_date": "2025-12-01"},
             "paper_trading": {"win_rate": None, "avg_return_pct": None, "trade_count": 0,
                               "total_pnl": 0.0, "open_trades": 0},
             "divergence": {"win_rate_diff_pp": None, "avg_return_diff_pp": None,
                            "warning": False, "note": "No closed trades yet"}},
        ]
        output = format_performance(comps, single=False)
        assert "Performance Ranking" in output
        assert "Pattern A" in output
        assert "Pattern B" in output
        assert "No trades" in output
        assert "No closed trades yet" in output
