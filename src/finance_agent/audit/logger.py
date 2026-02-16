"""Audit logger: writes immutable events to the audit_log table."""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

logger = logging.getLogger(__name__)


class AuditLogger:
    """Writes and queries immutable audit events in the audit_log table."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def log(self, event_type: str, source: str, payload: dict[str, Any] | None = None) -> None:
        """Write an immutable audit event to the audit_log table.

        The payload dict is JSON-serialized. Timestamp is set automatically
        by the database DEFAULT constraint.
        """
        payload_json = json.dumps(payload or {})
        self._conn.execute(
            "INSERT INTO audit_log (event_type, source, payload) VALUES (?, ?, ?)",
            (event_type, source, payload_json),
        )
        self._conn.commit()
        logger.debug("Audit event: %s from %s", event_type, source)

    def query(
        self,
        start: str | None = None,
        end: str | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return audit events matching the given filters in chronological order.

        All parameters are optional. start/end are ISO 8601 UTC timestamps.
        """
        conditions: list[str] = []
        params: list[str] = []

        if start is not None:
            conditions.append("timestamp >= ?")
            params.append(start)
        if end is not None:
            conditions.append("timestamp <= ?")
            params.append(end)
        if event_type is not None:
            conditions.append("event_type = ?")
            params.append(event_type)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        cols = "id, timestamp, event_type, source, payload"
        sql = f"SELECT {cols} FROM audit_log{where} ORDER BY timestamp ASC, id ASC"

        rows = self._conn.execute(sql, params).fetchall()
        return [
            {
                "id": row[0],
                "timestamp": row[1],
                "event_type": row[2],
                "source": row[3],
                "payload": json.loads(row[4]),
            }
            for row in rows
        ]
