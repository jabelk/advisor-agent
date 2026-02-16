"""Database management: SQLite connection factory and migration runner."""

from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Raised when a database operation fails."""


def get_connection(db_path: str) -> sqlite3.Connection:
    """Return a configured SQLite connection with recommended PRAGMAs.

    Creates parent directories if they don't exist. Sets WAL mode and
    performance-related PRAGMAs per research.md decision 3.

    Raises DatabaseError for corrupted/inaccessible DB or read-only filesystem.
    """
    path = Path(db_path)

    # Ensure parent directory exists and is writable
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise DatabaseError(f"Cannot create database directory {path.parent}: {e}") from e

    if path.parent.exists() and not path.parent.is_dir():
        raise DatabaseError(f"DB_PATH parent is not a directory: {path.parent}")

    try:
        conn = sqlite3.connect(str(path))
    except sqlite3.OperationalError as e:
        raise DatabaseError(f"Cannot open database at {path}: {e}") from e

    conn.row_factory = sqlite3.Row

    # Set recommended PRAGMAs
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA cache_size = -64000")
    except sqlite3.DatabaseError as e:
        conn.close()
        raise DatabaseError(f"Database at {path} may be corrupted: {e}") from e

    return conn


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Return the current schema version (PRAGMA user_version)."""
    row = conn.execute("PRAGMA user_version").fetchone()
    return int(row[0]) if row else 0


def run_migrations(conn: sqlite3.Connection, migrations_dir: str) -> int:
    """Apply all pending migrations from the given directory.

    Migration files must be named NNN_description.sql (e.g., 001_init.sql).
    Each migration sets PRAGMA user_version = N at the end.
    Returns the number of migrations applied.
    """
    migrations_path = Path(migrations_dir)
    if not migrations_path.exists():
        logger.warning("Migrations directory does not exist: %s", migrations_dir)
        return 0

    current_version = get_schema_version(conn)

    # Find all .sql files and sort by number prefix
    migration_files: list[tuple[int, Path]] = []
    for sql_file in sorted(migrations_path.glob("*.sql")):
        match = re.match(r"^(\d+)", sql_file.name)
        if match:
            version = int(match.group(1))
            migration_files.append((version, sql_file))

    migration_files.sort(key=lambda x: x[0])

    applied = 0
    for version, sql_file in migration_files:
        if version <= current_version:
            continue

        logger.info(
            "Applying migration %s (version %d → %d)",
            sql_file.name, current_version, version,
        )
        sql = sql_file.read_text()

        # Execute migration — PRAGMA user_version is set inside the SQL file
        try:
            conn.executescript(sql)
        except sqlite3.Error as e:
            raise DatabaseError(
                f"Migration {sql_file.name} failed: {e}"
            ) from e

        current_version = version
        applied += 1

    if applied:
        logger.info("Applied %d migration(s), schema now at version %d", applied, current_version)
    else:
        logger.debug("No pending migrations (schema version %d)", current_version)

    return applied


def close_connection(conn: sqlite3.Connection) -> None:
    """Close a connection with recommended cleanup PRAGMAs."""
    try:
        conn.execute("PRAGMA analysis_limit = 400")
        conn.execute("PRAGMA optimize")
    except sqlite3.Error:
        pass
    conn.close()
