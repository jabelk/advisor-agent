"""Unit tests for finance_agent.audit.logger module."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from finance_agent.audit.logger import AuditLogger
from finance_agent.db import get_connection, run_migrations

MIGRATIONS_DIR = str(Path(__file__).resolve().parent.parent.parent / "migrations")


@pytest.fixture
def audit_db(tmp_path: Path) -> tuple[sqlite3.Connection, AuditLogger]:
    """Provide a DB connection and AuditLogger for testing."""
    conn = get_connection(str(tmp_path / "test.db"))
    run_migrations(conn, MIGRATIONS_DIR)
    logger = AuditLogger(conn)
    yield conn, logger
    conn.close()


class TestAuditLoggerLog:
    """Test AuditLogger.log() method."""

    def test_creates_event(self, audit_db: tuple[sqlite3.Connection, AuditLogger]) -> None:
        conn, logger = audit_db
        logger.log("test_event", "test_source", {"key": "value"})
        rows = conn.execute("SELECT * FROM audit_log").fetchall()
        assert len(rows) == 1

    def test_event_fields(self, audit_db: tuple[sqlite3.Connection, AuditLogger]) -> None:
        conn, logger = audit_db
        logger.log("startup", "cli", {"version": "0.1.0"})
        row = conn.execute("SELECT * FROM audit_log").fetchone()
        assert row["event_type"] == "startup"
        assert row["source"] == "cli"
        assert '"version": "0.1.0"' in row["payload"]

    def test_timestamp_auto_set(self, audit_db: tuple[sqlite3.Connection, AuditLogger]) -> None:
        _, logger = audit_db
        logger.log("test", "test")
        events = logger.query()
        assert events[0]["timestamp"] is not None
        # ISO 8601 format check
        assert "T" in events[0]["timestamp"]

    def test_default_empty_payload(self, audit_db: tuple[sqlite3.Connection, AuditLogger]) -> None:
        _, logger = audit_db
        logger.log("test", "test")
        events = logger.query()
        assert events[0]["payload"] == {}

    def test_multiple_events_in_order(
        self, audit_db: tuple[sqlite3.Connection, AuditLogger],
    ) -> None:
        _, logger = audit_db
        logger.log("first", "test")
        logger.log("second", "test")
        logger.log("third", "test")
        events = logger.query()
        assert len(events) == 3
        assert events[0]["event_type"] == "first"
        assert events[1]["event_type"] == "second"
        assert events[2]["event_type"] == "third"


class TestAuditLoggerQuery:
    """Test AuditLogger.query() method."""

    def test_query_all(self, audit_db: tuple[sqlite3.Connection, AuditLogger]) -> None:
        _, logger = audit_db
        logger.log("a", "test")
        logger.log("b", "test")
        events = logger.query()
        assert len(events) == 2

    def test_query_by_event_type(self, audit_db: tuple[sqlite3.Connection, AuditLogger]) -> None:
        _, logger = audit_db
        logger.log("startup", "cli")
        logger.log("health_check", "cli")
        logger.log("startup", "cli")
        events = logger.query(event_type="startup")
        assert len(events) == 2
        assert all(e["event_type"] == "startup" for e in events)

    def test_query_by_time_range(self, audit_db: tuple[sqlite3.Connection, AuditLogger]) -> None:
        _, logger = audit_db
        logger.log("early", "test")
        logger.log("late", "test")
        events = logger.query()
        # Use the first event's timestamp as start and end
        start = events[0]["timestamp"]
        filtered = logger.query(start=start)
        assert len(filtered) >= 1

    def test_query_empty_result(self, audit_db: tuple[sqlite3.Connection, AuditLogger]) -> None:
        _, logger = audit_db
        events = logger.query(event_type="nonexistent")
        assert events == []

    def test_query_returns_dicts(self, audit_db: tuple[sqlite3.Connection, AuditLogger]) -> None:
        _, logger = audit_db
        logger.log("test", "src", {"k": "v"})
        events = logger.query()
        event = events[0]
        assert isinstance(event, dict)
        assert "id" in event
        assert "timestamp" in event
        assert "event_type" in event
        assert "source" in event
        assert "payload" in event


class TestAppendOnlyEnforcement:
    """Test that audit_log table rejects UPDATE and DELETE."""

    def test_update_raises(self, audit_db: tuple[sqlite3.Connection, AuditLogger]) -> None:
        conn, logger = audit_db
        logger.log("test", "test")
        with pytest.raises(sqlite3.IntegrityError, match="Updates are not allowed"):
            conn.execute("UPDATE audit_log SET event_type = 'changed' WHERE id = 1")

    def test_delete_raises(self, audit_db: tuple[sqlite3.Connection, AuditLogger]) -> None:
        conn, logger = audit_db
        logger.log("test", "test")
        with pytest.raises(sqlite3.IntegrityError, match="Deletes are not allowed"):
            conn.execute("DELETE FROM audit_log WHERE id = 1")
