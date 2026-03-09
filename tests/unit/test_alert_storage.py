"""Tests for pattern alert storage CRUD operations."""

from __future__ import annotations

import json
import sqlite3

import pytest

from finance_agent.patterns.alert_storage import (
    create_alert,
    list_alerts,
    update_alert_auto_execute,
    update_alert_status,
)


@pytest.fixture()
def conn():
    """Create in-memory DB with required tables."""
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = OFF")

    # Create pattern_alert table
    db.execute("""
        CREATE TABLE pattern_alert (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_id      INTEGER NOT NULL,
            pattern_name    TEXT    NOT NULL,
            ticker          TEXT    NOT NULL,
            trigger_date    TEXT    NOT NULL,
            trigger_details_json TEXT NOT NULL,
            recommended_action   TEXT NOT NULL,
            pattern_win_rate     REAL,
            status          TEXT    NOT NULL DEFAULT 'new',
            auto_executed   INTEGER NOT NULL DEFAULT 0,
            auto_execute_result  TEXT,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    db.execute("""
        CREATE UNIQUE INDEX idx_pattern_alert_dedup
        ON pattern_alert(pattern_id, ticker, trigger_date)
    """)
    db.execute("CREATE INDEX idx_pattern_alert_status ON pattern_alert(status)")
    db.execute("CREATE INDEX idx_pattern_alert_created ON pattern_alert(created_at)")
    yield db
    db.close()


SAMPLE_TRIGGER = {
    "triggered": True,
    "price_change_pct": 7.2,
    "volume_multiple": 2.1,
    "conditions_met": ["price_change_pct gte 5.0"],
    "latest_price": 45.30,
    "previous_close": 42.26,
}


class TestCreateAlert:
    def test_create_returns_id(self, conn):
        alert_id = create_alert(
            conn, pattern_id=1, pattern_name="Test Pattern", ticker="MRNA",
            trigger_date="2026-03-08", trigger_details=SAMPLE_TRIGGER,
            recommended_action="buy_call", pattern_win_rate=0.50,
        )
        assert alert_id > 0

    def test_duplicate_returns_zero(self, conn):
        create_alert(
            conn, pattern_id=1, pattern_name="Test Pattern", ticker="MRNA",
            trigger_date="2026-03-08", trigger_details=SAMPLE_TRIGGER,
            recommended_action="buy_call",
        )
        dup_id = create_alert(
            conn, pattern_id=1, pattern_name="Test Pattern", ticker="MRNA",
            trigger_date="2026-03-08", trigger_details=SAMPLE_TRIGGER,
            recommended_action="buy_call",
        )
        assert dup_id == 0

    def test_different_date_not_duplicate(self, conn):
        id1 = create_alert(
            conn, pattern_id=1, pattern_name="Test", ticker="MRNA",
            trigger_date="2026-03-07", trigger_details=SAMPLE_TRIGGER,
            recommended_action="buy_call",
        )
        id2 = create_alert(
            conn, pattern_id=1, pattern_name="Test", ticker="MRNA",
            trigger_date="2026-03-08", trigger_details=SAMPLE_TRIGGER,
            recommended_action="buy_call",
        )
        assert id1 > 0
        assert id2 > 0
        assert id1 != id2

    def test_different_ticker_not_duplicate(self, conn):
        id1 = create_alert(
            conn, pattern_id=1, pattern_name="Test", ticker="MRNA",
            trigger_date="2026-03-08", trigger_details=SAMPLE_TRIGGER,
            recommended_action="buy_call",
        )
        id2 = create_alert(
            conn, pattern_id=1, pattern_name="Test", ticker="NVDA",
            trigger_date="2026-03-08", trigger_details=SAMPLE_TRIGGER,
            recommended_action="buy_call",
        )
        assert id1 > 0
        assert id2 > 0

    def test_stores_win_rate_none(self, conn):
        alert_id = create_alert(
            conn, pattern_id=1, pattern_name="Test", ticker="MRNA",
            trigger_date="2026-03-08", trigger_details=SAMPLE_TRIGGER,
            recommended_action="buy_call", pattern_win_rate=None,
        )
        row = conn.execute("SELECT pattern_win_rate FROM pattern_alert WHERE id = ?", (alert_id,)).fetchone()
        assert row["pattern_win_rate"] is None


class TestListAlerts:
    def _seed_alerts(self, conn):
        create_alert(conn, 1, "Pattern A", "MRNA", "2026-03-08", SAMPLE_TRIGGER, "buy_call", 0.50)
        create_alert(conn, 2, "Pattern B", "NVDA", "2026-03-08", SAMPLE_TRIGGER, "buy_shares", 0.60)
        create_alert(conn, 1, "Pattern A", "AAPL", "2026-03-07", SAMPLE_TRIGGER, "buy_call", 0.50)

    def test_list_all(self, conn):
        self._seed_alerts(conn)
        alerts = list_alerts(conn, days=30)
        assert len(alerts) == 3

    def test_filter_by_ticker(self, conn):
        self._seed_alerts(conn)
        alerts = list_alerts(conn, ticker="MRNA", days=30)
        assert len(alerts) == 1
        assert alerts[0]["ticker"] == "MRNA"

    def test_filter_by_pattern_id(self, conn):
        self._seed_alerts(conn)
        alerts = list_alerts(conn, pattern_id=1, days=30)
        assert len(alerts) == 2

    def test_filter_by_status(self, conn):
        self._seed_alerts(conn)
        alerts = list_alerts(conn, status="new", days=30)
        assert len(alerts) == 3

        update_alert_status(conn, 1, "acknowledged")
        alerts = list_alerts(conn, status="new", days=30)
        assert len(alerts) == 2

    def test_trigger_details_parsed(self, conn):
        self._seed_alerts(conn)
        alerts = list_alerts(conn, days=30)
        assert isinstance(alerts[0]["trigger_details"], dict)
        assert alerts[0]["trigger_details"]["price_change_pct"] == 7.2

    def test_sorted_descending(self, conn):
        self._seed_alerts(conn)
        alerts = list_alerts(conn, days=30)
        # Most recent first
        dates = [a["created_at"] for a in alerts]
        assert dates == sorted(dates, reverse=True)


class TestUpdateAlertStatus:
    def test_acknowledge(self, conn):
        alert_id = create_alert(conn, 1, "Test", "MRNA", "2026-03-08", SAMPLE_TRIGGER, "buy_call")
        assert update_alert_status(conn, alert_id, "acknowledged")
        row = conn.execute("SELECT status FROM pattern_alert WHERE id = ?", (alert_id,)).fetchone()
        assert row["status"] == "acknowledged"

    def test_dismiss(self, conn):
        alert_id = create_alert(conn, 1, "Test", "MRNA", "2026-03-08", SAMPLE_TRIGGER, "buy_call")
        assert update_alert_status(conn, alert_id, "dismissed")

    def test_acted_on(self, conn):
        alert_id = create_alert(conn, 1, "Test", "MRNA", "2026-03-08", SAMPLE_TRIGGER, "buy_call")
        assert update_alert_status(conn, alert_id, "acted_on")

    def test_invalid_status_raises(self, conn):
        alert_id = create_alert(conn, 1, "Test", "MRNA", "2026-03-08", SAMPLE_TRIGGER, "buy_call")
        with pytest.raises(ValueError, match="Invalid status"):
            update_alert_status(conn, alert_id, "invalid")

    def test_not_found_returns_false(self, conn):
        assert not update_alert_status(conn, 999, "acknowledged")


class TestUpdateAlertAutoExecute:
    def test_records_result(self, conn):
        alert_id = create_alert(conn, 1, "Test", "MRNA", "2026-03-08", SAMPLE_TRIGGER, "buy_call")
        update_alert_auto_execute(conn, alert_id, {"executed": True, "trade_id": 42})

        row = conn.execute("SELECT auto_executed, auto_execute_result FROM pattern_alert WHERE id = ?", (alert_id,)).fetchone()
        assert row["auto_executed"] == 1
        result = json.loads(row["auto_execute_result"])
        assert result["trade_id"] == 42
