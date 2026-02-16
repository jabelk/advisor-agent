"""Unit tests for finance_agent.db module."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from finance_agent.db import (
    DatabaseError,
    close_connection,
    get_connection,
    get_schema_version,
    run_migrations,
)

MIGRATIONS_DIR = str(Path(__file__).resolve().parent.parent.parent / "migrations")


class TestGetConnection:
    """Test SQLite connection factory."""

    def test_creates_db_file(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "test.db")
        conn = get_connection(db_path)
        assert Path(db_path).exists()
        conn.close()

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "subdir" / "deep" / "test.db")
        conn = get_connection(db_path)
        assert Path(db_path).exists()
        conn.close()

    def test_wal_mode_enabled(self, tmp_path: Path) -> None:
        conn = get_connection(str(tmp_path / "test.db"))
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"
        conn.close()

    def test_foreign_keys_enabled(self, tmp_path: Path) -> None:
        conn = get_connection(str(tmp_path / "test.db"))
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1
        conn.close()

    def test_busy_timeout_set(self, tmp_path: Path) -> None:
        conn = get_connection(str(tmp_path / "test.db"))
        timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        assert timeout == 5000
        conn.close()

    def test_synchronous_normal(self, tmp_path: Path) -> None:
        conn = get_connection(str(tmp_path / "test.db"))
        sync = conn.execute("PRAGMA synchronous").fetchone()[0]
        # NORMAL = 1
        assert sync == 1
        conn.close()

    def test_row_factory_is_row(self, tmp_path: Path) -> None:
        conn = get_connection(str(tmp_path / "test.db"))
        assert conn.row_factory == sqlite3.Row
        conn.close()

    def test_corrupted_db_raises(self, tmp_path: Path) -> None:
        db_path = tmp_path / "corrupt.db"
        db_path.write_text("this is not a valid sqlite database")
        with pytest.raises(DatabaseError, match="corrupted"):
            get_connection(str(db_path))


class TestRunMigrations:
    """Test migration runner."""

    def test_applies_initial_migration(self, tmp_path: Path) -> None:
        conn = get_connection(str(tmp_path / "test.db"))
        applied = run_migrations(conn, MIGRATIONS_DIR)
        assert applied == 2
        assert get_schema_version(conn) == 2
        conn.close()

    def test_skips_already_applied(self, tmp_path: Path) -> None:
        conn = get_connection(str(tmp_path / "test.db"))
        run_migrations(conn, MIGRATIONS_DIR)
        applied = run_migrations(conn, MIGRATIONS_DIR)
        assert applied == 0
        conn.close()

    def test_creates_audit_log_table(self, tmp_path: Path) -> None:
        conn = get_connection(str(tmp_path / "test.db"))
        run_migrations(conn, MIGRATIONS_DIR)
        # Verify table exists
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'"
        ).fetchall()
        assert len(tables) == 1
        conn.close()

    def test_missing_migrations_dir(self, tmp_path: Path) -> None:
        conn = get_connection(str(tmp_path / "test.db"))
        applied = run_migrations(conn, str(tmp_path / "nonexistent"))
        assert applied == 0
        conn.close()

    def test_schema_version_starts_at_zero(self, tmp_path: Path) -> None:
        conn = get_connection(str(tmp_path / "test.db"))
        assert get_schema_version(conn) == 0
        conn.close()


class TestCloseConnection:
    """Test connection cleanup."""

    def test_close_without_error(self, tmp_path: Path) -> None:
        conn = get_connection(str(tmp_path / "test.db"))
        close_connection(conn)
        # Should not raise
