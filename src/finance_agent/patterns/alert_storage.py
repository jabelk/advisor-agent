"""Alert storage: CRUD operations for pattern scanner alerts."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_alert(
    conn: sqlite3.Connection,
    pattern_id: int,
    pattern_name: str,
    ticker: str,
    trigger_date: str,
    trigger_details: dict,
    recommended_action: str,
    pattern_win_rate: float | None = None,
) -> int:
    """Persist a new alert. Returns alert ID, or 0 if duplicate exists."""
    now = _now()
    trigger_json = json.dumps(trigger_details)
    try:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO pattern_alert "
            "(pattern_id, pattern_name, ticker, trigger_date, trigger_details_json, "
            "recommended_action, pattern_win_rate, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'new', ?, ?)",
            (
                pattern_id,
                pattern_name,
                ticker,
                trigger_date,
                trigger_json,
                recommended_action,
                pattern_win_rate,
                now,
                now,
            ),
        )
        conn.commit()
        if cursor.lastrowid and cursor.rowcount > 0:
            return cursor.lastrowid  # type: ignore[return-value]
        return 0  # duplicate — INSERT OR IGNORE skipped
    except sqlite3.Error:
        return 0


def list_alerts(
    conn: sqlite3.Connection,
    status: str | None = None,
    pattern_id: int | None = None,
    ticker: str | None = None,
    days: int = 7,
) -> list[dict]:
    """Retrieve alerts with optional filtering, sorted by created_at descending."""
    conditions: list[str] = ["created_at >= datetime('now', '-' || ? || ' days')"]
    params: list[str | int] = [str(days)]

    if status:
        conditions.append("status = ?")
        params.append(status)
    if pattern_id is not None:
        conditions.append("pattern_id = ?")
        params.append(pattern_id)
    if ticker:
        conditions.append("ticker = ?")
        params.append(ticker.upper())

    where = " AND ".join(conditions)
    rows = conn.execute(
        f"SELECT * FROM pattern_alert WHERE {where} ORDER BY created_at DESC",
        params,
    ).fetchall()

    results = []
    for row in rows:
        d = dict(row)
        if d.get("trigger_details_json"):
            try:
                d["trigger_details"] = json.loads(d["trigger_details_json"])
            except (json.JSONDecodeError, TypeError):
                d["trigger_details"] = {}
        if d.get("auto_execute_result"):
            try:
                d["auto_execute_result"] = json.loads(d["auto_execute_result"])
            except (json.JSONDecodeError, TypeError):
                pass
        results.append(d)
    return results


def update_alert_status(
    conn: sqlite3.Connection,
    alert_id: int,
    new_status: str,
) -> bool:
    """Change an alert's lifecycle status. Returns True if updated."""
    valid = {"acknowledged", "acted_on", "dismissed"}
    if new_status not in valid:
        raise ValueError(f"Invalid status '{new_status}'. Must be one of: {valid}")
    now = _now()
    cursor = conn.execute(
        "UPDATE pattern_alert SET status = ?, updated_at = ? WHERE id = ?",
        (new_status, now, alert_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def update_alert_auto_execute(
    conn: sqlite3.Connection,
    alert_id: int,
    result: dict,
) -> None:
    """Record auto-execution result on an alert."""
    now = _now()
    conn.execute(
        "UPDATE pattern_alert SET auto_executed = 1, auto_execute_result = ?, updated_at = ? WHERE id = ?",
        (json.dumps(result), now, alert_id),
    )
    conn.commit()
