"""Notable investor CRUD operations."""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)


def add_investor(conn: sqlite3.Connection, name: str, cik: str) -> int:
    """Add a notable investor for tracking. Returns the investor ID.

    If the investor was previously soft-deleted, reactivates them.
    """
    existing = conn.execute(
        "SELECT id, active FROM notable_investor WHERE name = ? OR cik = ?",
        (name, cik),
    ).fetchone()

    if existing:
        if existing["active"]:
            raise ValueError(f"Investor '{name}' is already being tracked")
        conn.execute(
            "UPDATE notable_investor SET active = 1, name = ?, cik = ? WHERE id = ?",
            (name, cik, existing["id"]),
        )
        conn.commit()
        logger.info("Reactivated tracking for %s", name)
        return int(existing["id"])

    cursor = conn.execute(
        "INSERT INTO notable_investor (name, cik) VALUES (?, ?)",
        (name, cik),
    )
    conn.commit()
    logger.info("Added notable investor: %s (CIK: %s)", name, cik)
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def remove_investor(conn: sqlite3.Connection, name: str) -> bool:
    """Soft-delete a notable investor. Returns True if found."""
    cursor = conn.execute(
        "UPDATE notable_investor SET active = 0 WHERE name = ? AND active = 1",
        (name,),
    )
    conn.commit()
    if cursor.rowcount > 0:
        logger.info("Stopped tracking investor: %s", name)
        return True
    return False


def list_investors(
    conn: sqlite3.Connection, active_only: bool = True
) -> list[dict[str, str | int | None]]:
    """List tracked notable investors."""
    if active_only:
        rows = conn.execute(
            "SELECT id, name, cik, added_at FROM notable_investor WHERE active = 1 ORDER BY name"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, name, cik, added_at, active FROM notable_investor ORDER BY name"
        ).fetchall()
    return [dict(row) for row in rows]
