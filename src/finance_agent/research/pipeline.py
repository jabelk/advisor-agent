"""Research pipeline orchestrator and ingestion run tracking."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


# --- Ingestion Run Tracking ---


def start_run(conn: sqlite3.Connection) -> int:
    """Start a new ingestion run. Returns the run ID."""
    cursor = conn.execute(
        "INSERT INTO ingestion_run (status) VALUES ('running')"
    )
    conn.commit()
    run_id: int = cursor.lastrowid  # type: ignore[assignment]
    logger.info("Started ingestion run %d", run_id)
    return run_id


def complete_run(
    conn: sqlite3.Connection,
    run_id: int,
    docs_count: int,
    signals_count: int,
    sources_stats: dict[str, dict[str, int]] | None = None,
) -> None:
    """Mark an ingestion run as completed."""
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    sources_json = json.dumps(sources_stats) if sources_stats else None
    conn.execute(
        "UPDATE ingestion_run SET completed_at = ?, status = 'completed', "
        "documents_ingested = ?, signals_generated = ?, sources_json = ? "
        "WHERE id = ?",
        (now, docs_count, signals_count, sources_json, run_id),
    )
    conn.commit()
    logger.info(
        "Completed ingestion run %d: %d docs, %d signals", run_id, docs_count, signals_count
    )


def fail_run(
    conn: sqlite3.Connection,
    run_id: int,
    errors: list[str],
) -> None:
    """Mark an ingestion run as failed."""
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    conn.execute(
        "UPDATE ingestion_run SET completed_at = ?, status = 'failed', "
        "errors_json = ? WHERE id = ?",
        (now, json.dumps(errors), run_id),
    )
    conn.commit()
    logger.error("Failed ingestion run %d: %s", run_id, errors)


def get_last_run(conn: sqlite3.Connection) -> dict[str, str | int | None] | None:
    """Get the most recent ingestion run."""
    row = conn.execute(
        "SELECT * FROM ingestion_run ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return dict(row) if row else None


# --- Document Status Helpers ---


def set_document_status(
    conn: sqlite3.Connection,
    doc_id: int,
    status: str,
    error: str | None = None,
) -> None:
    """Update a source document's analysis status."""
    conn.execute(
        "UPDATE source_document SET analysis_status = ?, analysis_error = ? WHERE id = ?",
        (status, error, doc_id),
    )
    conn.commit()


def save_document_record(
    conn: sqlite3.Connection,
    company_id: int | None,
    source_type: str,
    content_type: str,
    source_id: str,
    title: str,
    published_at: str,
    content_hash: str,
    local_path: str,
    file_size_bytes: int,
    metadata_json: str | None = None,
) -> int:
    """Insert a source document record. Returns the document ID."""
    cursor = conn.execute(
        "INSERT INTO source_document "
        "(company_id, source_type, content_type, source_id, title, published_at, "
        "content_hash, local_path, file_size_bytes, metadata_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            company_id,
            source_type,
            content_type,
            source_id,
            title,
            published_at,
            content_hash,
            local_path,
            file_size_bytes,
            metadata_json,
        ),
    )
    conn.commit()
    return cursor.lastrowid  # type: ignore[return-value]
