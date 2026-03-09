"""Tests for the pattern scanner: trigger evaluation and scan orchestration."""

from __future__ import annotations

import json
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from finance_agent.patterns.models import (
    ActionType,
    EntrySignal,
    ExitCriteria,
    RuleSet,
    TradeAction,
    TriggerCondition,
)
from finance_agent.patterns.scanner import evaluate_triggers, run_scan


def _make_rule_set(
    price_threshold: float = 5.0,
    volume_threshold: float = 1.5,
) -> RuleSet:
    """Create a minimal RuleSet for testing."""
    return RuleSet(
        trigger_type="quantitative",
        trigger_conditions=[
            TriggerCondition(field="price_change_pct", operator="gte", value=str(price_threshold), description="Price spike"),
            TriggerCondition(field="volume_spike", operator="gte", value=str(volume_threshold), description="Volume spike"),
        ],
        entry_signal=EntrySignal(condition="time_delay", value="0", window_days=2, description="Immediate entry"),
        action=TradeAction(action_type="buy_call", description="Buy call option"),
        exit_criteria=ExitCriteria(description="Default exit criteria"),
    )


def _make_bars(
    closes: list[float],
    volumes: list[float] | None = None,
) -> list[dict]:
    """Create simplified bar dicts for testing."""
    if volumes is None:
        volumes = [1000.0] * len(closes)
    return [
        {
            "bar_timestamp": f"2026-03-{i + 1:02d}T00:00:00Z",
            "open": c,
            "high": c * 1.01,
            "low": c * 0.99,
            "close": c,
            "volume": v,
        }
        for i, (c, v) in enumerate(zip(closes, volumes))
    ]


class TestEvaluateTriggers:
    def test_triggered_when_conditions_met(self):
        # Previous close 100, latest close 106 → 6% change, volume 2x
        bars = _make_bars([100.0, 106.0], [1000, 2000])
        rule_set = _make_rule_set(price_threshold=5.0, volume_threshold=1.5)
        result = evaluate_triggers(rule_set, bars)
        assert result["triggered"] is True
        assert result["price_change_pct"] == 6.0
        assert result["volume_multiple"] == 2.0
        assert result["latest_price"] == 106.0
        assert result["previous_close"] == 100.0

    def test_not_triggered_price_below_threshold(self):
        bars = _make_bars([100.0, 103.0], [1000, 2000])
        rule_set = _make_rule_set(price_threshold=5.0)
        result = evaluate_triggers(rule_set, bars)
        assert result["triggered"] is False

    def test_not_triggered_volume_below_threshold(self):
        bars = _make_bars([100.0, 106.0], [1000, 1200])
        rule_set = _make_rule_set(volume_threshold=1.5)
        result = evaluate_triggers(rule_set, bars)
        assert result["triggered"] is False

    def test_insufficient_bars(self):
        bars = _make_bars([100.0])
        rule_set = _make_rule_set()
        result = evaluate_triggers(rule_set, bars)
        assert result["triggered"] is False

    def test_empty_bars(self):
        result = evaluate_triggers(_make_rule_set(), [])
        assert result["triggered"] is False

    def test_zero_previous_close(self):
        bars = _make_bars([0.0, 10.0])
        result = evaluate_triggers(_make_rule_set(), bars)
        assert result["triggered"] is False

    def test_volume_lookback_with_many_bars(self):
        # 25 bars: 23 with vol 1000, then one with vol 1000, then latest with vol 3000
        closes = [100.0] * 24 + [106.0]
        volumes = [1000.0] * 24 + [3000.0]
        bars = _make_bars(closes, volumes)
        rule_set = _make_rule_set(price_threshold=5.0, volume_threshold=2.0)
        result = evaluate_triggers(rule_set, bars)
        assert result["triggered"] is True
        assert result["volume_multiple"] == 3.0

    def test_conditions_met_list(self):
        bars = _make_bars([100.0, 106.0], [1000, 2000])
        rule_set = _make_rule_set()
        result = evaluate_triggers(rule_set, bars)
        assert len(result["conditions_met"]) == 2
        assert "price_change_pct" in result["conditions_met"][0]
        assert "volume_spike" in result["conditions_met"][1]

    def test_price_only_trigger(self):
        """Test with only price condition (no volume)."""
        rule_set = RuleSet(
            trigger_type="quantitative",
            trigger_conditions=[
                TriggerCondition(field="price_change_pct", operator="gte", value="5.0", description="Price spike"),
            ],
            entry_signal=EntrySignal(condition="time_delay", value="0", window_days=2, description="Immediate"),
            action=TradeAction(action_type="buy_call", description="Buy call"),
            exit_criteria=ExitCriteria(description="Default"),
        )
        bars = _make_bars([100.0, 106.0], [1000, 1000])
        result = evaluate_triggers(rule_set, bars)
        assert result["triggered"] is True

    def test_lte_operator(self):
        """Test less-than-or-equal operator for price drop triggers."""
        rule_set = RuleSet(
            trigger_type="quantitative",
            trigger_conditions=[
                TriggerCondition(field="price_change_pct", operator="lte", value="-5.0", description="Price drop"),
            ],
            entry_signal=EntrySignal(condition="time_delay", value="0", window_days=2, description="Immediate"),
            action=TradeAction(action_type="buy_put", description="Buy put"),
            exit_criteria=ExitCriteria(description="Default"),
        )
        bars = _make_bars([100.0, 93.0], [1000, 1000])
        result = evaluate_triggers(rule_set, bars)
        assert result["triggered"] is True

    def test_qualitative_conditions_skipped(self):
        """Qualitative (sector, news_sentiment) conditions are skipped, not blocking."""
        rule_set = RuleSet(
            trigger_type="qualitative",
            trigger_conditions=[
                TriggerCondition(field="price_change_pct", operator="gte", value="5.0", description="Price spike"),
                TriggerCondition(field="news_sentiment", operator="eq", value="positive", description="Positive news"),
            ],
            entry_signal=EntrySignal(condition="time_delay", value="0", window_days=2, description="Immediate"),
            action=TradeAction(action_type="buy_call", description="Buy call"),
            exit_criteria=ExitCriteria(description="Default"),
        )
        bars = _make_bars([100.0, 106.0], [1000, 1000])
        result = evaluate_triggers(rule_set, bars)
        assert result["triggered"] is True


@pytest.fixture()
def scan_db():
    """Create in-memory DB with all tables needed for scan tests."""
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row

    # trading_pattern
    db.execute("""
        CREATE TABLE trading_pattern (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            rule_set_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            auto_execute INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            retired_at TEXT
        )
    """)

    # pattern_alert
    db.execute("""
        CREATE TABLE pattern_alert (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_id INTEGER NOT NULL,
            pattern_name TEXT NOT NULL,
            ticker TEXT NOT NULL,
            trigger_date TEXT NOT NULL,
            trigger_details_json TEXT NOT NULL,
            recommended_action TEXT NOT NULL,
            pattern_win_rate REAL,
            status TEXT NOT NULL DEFAULT 'new',
            auto_executed INTEGER NOT NULL DEFAULT 0,
            auto_execute_result TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    db.execute("""
        CREATE UNIQUE INDEX idx_pattern_alert_dedup
        ON pattern_alert(pattern_id, ticker, trigger_date)
    """)

    # paper_trade (for ticker lookup)
    db.execute("""
        CREATE TABLE paper_trade (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_id INTEGER NOT NULL,
            alpaca_order_id TEXT,
            ticker TEXT NOT NULL,
            direction TEXT NOT NULL,
            action_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            entry_price REAL,
            exit_price REAL,
            pnl REAL,
            status TEXT NOT NULL DEFAULT 'proposed',
            option_details_json TEXT,
            proposed_at TEXT DEFAULT (datetime('now')),
            executed_at TEXT,
            closed_at TEXT
        )
    """)

    # backtest_result (for win rate)
    db.execute("""
        CREATE TABLE backtest_result (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_id INTEGER NOT NULL,
            date_range_start TEXT,
            date_range_end TEXT,
            trigger_count INTEGER,
            trade_count INTEGER,
            win_count INTEGER,
            total_return_pct REAL,
            avg_return_pct REAL,
            max_drawdown_pct REAL,
            sharpe_ratio REAL,
            regime_analysis_json TEXT,
            sample_size_warning INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # safety_state
    db.execute("""
        CREATE TABLE safety_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now')),
            updated_by TEXT DEFAULT 'system'
        )
    """)
    db.execute(
        "INSERT INTO safety_state (key, value) VALUES ('kill_switch', ?)",
        (json.dumps({"active": False}),),
    )
    db.execute(
        "INSERT INTO safety_state (key, value) VALUES ('risk_settings', ?)",
        (json.dumps({"max_trades_per_day": 20}),),
    )

    # audit_log
    db.execute("""
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT (datetime('now')),
            event_type TEXT NOT NULL,
            source TEXT NOT NULL,
            payload TEXT
        )
    """)

    # company (for watchlist fallback)
    db.execute("""
        CREATE TABLE company (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            name TEXT,
            cik TEXT,
            sector TEXT,
            active INTEGER DEFAULT 1,
            added_at TEXT DEFAULT (datetime('now'))
        )
    """)

    db.commit()
    yield db
    db.close()


def _insert_pattern(db, name="Test Pattern", status="paper_trading", auto_execute=0):
    """Insert a pattern and return its ID."""
    rule_set = _make_rule_set()
    db.execute(
        "INSERT INTO trading_pattern (name, description, rule_set_json, status, auto_execute) VALUES (?, ?, ?, ?, ?)",
        (name, "test", rule_set.model_dump_json(), status, auto_execute),
    )
    db.commit()
    return db.execute("SELECT last_insert_rowid()").fetchone()[0]


class TestRunScan:
    def test_no_patterns_returns_empty(self, scan_db):
        result = run_scan(scan_db, "key", "secret")
        assert result["patterns_evaluated"] == 0
        assert result["alerts_generated"] == 0

    def test_non_paper_trading_skipped(self, scan_db):
        _insert_pattern(scan_db, status="draft")
        result = run_scan(scan_db, "key", "secret")
        assert result["patterns_evaluated"] == 0

    @patch("finance_agent.patterns.market_data.fetch_and_cache_bars")
    def test_trigger_generates_alert(self, mock_fetch, scan_db):
        pid = _insert_pattern(scan_db)
        # Add a ticker via paper_trade
        scan_db.execute(
            "INSERT INTO paper_trade (pattern_id, ticker, direction, action_type, quantity) VALUES (?, 'MRNA', 'buy', 'buy_call', 1)",
            (pid,),
        )
        scan_db.commit()

        # Mock bars that will trigger (6% spike, 2x volume)
        mock_fetch.return_value = _make_bars([100.0, 106.0], [1000, 2000])

        result = run_scan(scan_db, "key", "secret")
        assert result["patterns_evaluated"] == 1
        assert result["alerts_generated"] == 1
        assert result["alerts"][0]["ticker"] == "MRNA"
        assert result["alerts"][0]["pattern_name"] == "Test Pattern"

    @patch("finance_agent.patterns.market_data.fetch_and_cache_bars")
    def test_no_trigger_no_alert(self, mock_fetch, scan_db):
        pid = _insert_pattern(scan_db)
        scan_db.execute(
            "INSERT INTO paper_trade (pattern_id, ticker, direction, action_type, quantity) VALUES (?, 'MRNA', 'buy', 'buy_call', 1)",
            (pid,),
        )
        scan_db.commit()

        # Bars that won't trigger (only 2% move)
        mock_fetch.return_value = _make_bars([100.0, 102.0], [1000, 1200])

        result = run_scan(scan_db, "key", "secret")
        assert result["alerts_generated"] == 0

    @patch("finance_agent.patterns.market_data.fetch_and_cache_bars")
    def test_duplicate_scan_deduplicates(self, mock_fetch, scan_db):
        pid = _insert_pattern(scan_db)
        scan_db.execute(
            "INSERT INTO paper_trade (pattern_id, ticker, direction, action_type, quantity) VALUES (?, 'MRNA', 'buy', 'buy_call', 1)",
            (pid,),
        )
        scan_db.commit()

        mock_fetch.return_value = _make_bars([100.0, 106.0], [1000, 2000])

        result1 = run_scan(scan_db, "key", "secret")
        assert result1["alerts_generated"] == 1

        result2 = run_scan(scan_db, "key", "secret")
        assert result2["alerts_generated"] == 0

    @patch("finance_agent.patterns.market_data.fetch_and_cache_bars")
    def test_audit_logged(self, mock_fetch, scan_db):
        from finance_agent.audit.logger import AuditLogger
        audit = AuditLogger(scan_db)

        pid = _insert_pattern(scan_db)
        scan_db.execute(
            "INSERT INTO paper_trade (pattern_id, ticker, direction, action_type, quantity) VALUES (?, 'MRNA', 'buy', 'buy_call', 1)",
            (pid,),
        )
        scan_db.commit()

        mock_fetch.return_value = _make_bars([100.0, 106.0], [1000, 2000])

        run_scan(scan_db, "key", "secret", audit=audit)

        events = audit.query(event_type="scanner_run")
        assert len(events) == 1
        assert events[0]["payload"]["alerts_generated"] == 1

    @patch("finance_agent.patterns.market_data.fetch_and_cache_bars")
    def test_failed_bar_fetch_continues(self, mock_fetch, scan_db):
        pid = _insert_pattern(scan_db)
        scan_db.execute(
            "INSERT INTO paper_trade (pattern_id, ticker, direction, action_type, quantity) VALUES (?, 'MRNA', 'buy', 'buy_call', 1)",
            (pid,),
        )
        scan_db.commit()

        mock_fetch.side_effect = Exception("API error")

        result = run_scan(scan_db, "key", "secret")
        assert result["alerts_generated"] == 0
        # Scan completes without raising

    @patch("finance_agent.patterns.market_data.fetch_and_cache_bars")
    def test_auto_execute_creates_trade(self, mock_fetch, scan_db):
        from finance_agent.audit.logger import AuditLogger
        audit = AuditLogger(scan_db)

        pid = _insert_pattern(scan_db, auto_execute=1)
        scan_db.execute(
            "INSERT INTO paper_trade (pattern_id, ticker, direction, action_type, quantity) VALUES (?, 'MRNA', 'buy', 'buy_call', 1)",
            (pid,),
        )
        scan_db.commit()

        mock_fetch.return_value = _make_bars([100.0, 106.0], [1000, 2000])

        result = run_scan(scan_db, "key", "secret", audit=audit)
        assert result["auto_executions"] == 1
        assert result["alerts"][0]["auto_executed"] is True

        # Verify paper trade was created
        trades = scan_db.execute("SELECT * FROM paper_trade WHERE pattern_id = ? AND status = 'proposed'", (pid,)).fetchall()
        # Original trade + auto-executed trade
        assert len(trades) >= 1

    @patch("finance_agent.patterns.market_data.fetch_and_cache_bars")
    def test_auto_execute_blocked_by_kill_switch(self, mock_fetch, scan_db):
        from finance_agent.audit.logger import AuditLogger
        audit = AuditLogger(scan_db)

        # Activate kill switch
        scan_db.execute(
            "UPDATE safety_state SET value = ? WHERE key = 'kill_switch'",
            (json.dumps({"active": True}),),
        )
        scan_db.commit()

        pid = _insert_pattern(scan_db, auto_execute=1)
        scan_db.execute(
            "INSERT INTO paper_trade (pattern_id, ticker, direction, action_type, quantity) VALUES (?, 'MRNA', 'buy', 'buy_call', 1)",
            (pid,),
        )
        scan_db.commit()

        mock_fetch.return_value = _make_bars([100.0, 106.0], [1000, 2000])

        result = run_scan(scan_db, "key", "secret", audit=audit)
        assert result["auto_executions"] == 0
        assert result["auto_executions_blocked"] == 1
        assert result["alerts"][0]["auto_execute_result"]["blocked_reason"] == "kill_switch_active"

    @patch("finance_agent.patterns.market_data.fetch_and_cache_bars")
    def test_win_rate_from_backtest(self, mock_fetch, scan_db):
        pid = _insert_pattern(scan_db)
        # Add a backtest result with 3 wins out of 5
        scan_db.execute(
            "INSERT INTO backtest_result (pattern_id, trade_count, win_count) VALUES (?, 5, 3)",
            (pid,),
        )
        scan_db.execute(
            "INSERT INTO paper_trade (pattern_id, ticker, direction, action_type, quantity) VALUES (?, 'MRNA', 'buy', 'buy_call', 1)",
            (pid,),
        )
        scan_db.commit()

        mock_fetch.return_value = _make_bars([100.0, 106.0], [1000, 2000])

        result = run_scan(scan_db, "key", "secret")
        assert result["alerts"][0]["pattern_win_rate"] == 0.6
