"""Watchlist CRUD operations for company management."""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)


def add_company(
    conn: sqlite3.Connection,
    ticker: str,
    name: str,
    cik: str | None = None,
    sector: str | None = None,
) -> int:
    """Add a company to the watchlist. Returns the company ID.

    If the company was previously soft-deleted, reactivates it.
    """
    ticker = ticker.upper()

    # Check if already exists (including soft-deleted)
    existing = conn.execute(
        "SELECT id, active FROM company WHERE ticker = ?", (ticker,)
    ).fetchone()

    if existing:
        if existing["active"]:
            raise ValueError(f"{ticker} is already on the watchlist")
        # Reactivate
        conn.execute(
            "UPDATE company SET active = 1, name = ?, cik = ?, sector = ? WHERE id = ?",
            (name, cik, sector, existing["id"]),
        )
        conn.commit()
        logger.info("Reactivated %s on watchlist", ticker)
        return int(existing["id"])

    cursor = conn.execute(
        "INSERT INTO company (ticker, name, cik, sector) VALUES (?, ?, ?, ?)",
        (ticker, name, cik, sector),
    )
    conn.commit()
    logger.info("Added %s (%s) to watchlist", ticker, name)
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def remove_company(conn: sqlite3.Connection, ticker: str) -> bool:
    """Soft-delete a company from the watchlist. Returns True if found."""
    ticker = ticker.upper()
    cursor = conn.execute(
        "UPDATE company SET active = 0 WHERE ticker = ? AND active = 1", (ticker,)
    )
    conn.commit()
    if cursor.rowcount > 0:
        logger.info("Removed %s from watchlist", ticker)
        return True
    return False


def list_companies(
    conn: sqlite3.Connection, active_only: bool = True
) -> list[dict[str, str | int | None]]:
    """List companies on the watchlist."""
    if active_only:
        rows = conn.execute(
            "SELECT id, ticker, name, cik, sector, added_at FROM company WHERE active = 1 "
            "ORDER BY ticker"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, ticker, name, cik, sector, added_at, active FROM company ORDER BY ticker"
        ).fetchall()
    return [dict(row) for row in rows]


def get_company_by_ticker(
    conn: sqlite3.Connection, ticker: str
) -> dict[str, str | int | None] | None:
    """Get a company by ticker. Returns None if not found or inactive."""
    ticker = ticker.upper()
    row = conn.execute(
        "SELECT id, ticker, name, cik, sector, added_at FROM company "
        "WHERE ticker = ? AND active = 1",
        (ticker,),
    ).fetchone()
    return dict(row) if row else None


def reactivate_company(conn: sqlite3.Connection, ticker: str) -> bool:
    """Reactivate a soft-deleted company. Returns True if found and reactivated."""
    ticker = ticker.upper()
    cursor = conn.execute(
        "UPDATE company SET active = 1 WHERE ticker = ? AND active = 0", (ticker,)
    )
    conn.commit()
    return cursor.rowcount > 0
