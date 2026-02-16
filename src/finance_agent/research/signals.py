"""Signal storage and query operations."""

from __future__ import annotations

import json
import logging
import sqlite3

from finance_agent.data.models import ResearchSignalOutput

logger = logging.getLogger(__name__)


def save_signals(
    conn: sqlite3.Connection,
    document_id: int,
    company_id: int,
    signals: list[ResearchSignalOutput],
) -> int:
    """Save research signals to the database. Returns count saved."""
    count = 0
    for signal in signals:
        metrics_json = None
        if signal.metrics:
            metrics_json = json.dumps([m.model_dump() for m in signal.metrics])

        conn.execute(
            "INSERT INTO research_signal "
            "(company_id, document_id, signal_type, evidence_type, confidence, "
            "summary, details, source_section, metrics_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                company_id,
                document_id,
                signal.signal_type.value,
                signal.evidence_type.value,
                signal.confidence.value,
                signal.summary,
                signal.details,
                signal.source_section,
                metrics_json,
            ),
        )
        count += 1
    conn.commit()
    logger.debug("Saved %d signals for document %d, company %d", count, document_id, company_id)
    return count


def query_signals(
    conn: sqlite3.Connection,
    company_id: int | None = None,
    signal_type: str | None = None,
    since: str | None = None,
    until: str | None = None,
    source_type: str | None = None,
) -> list[dict[str, str | int | None]]:
    """Query research signals with optional filters."""
    query = """
        SELECT rs.id, rs.company_id, rs.document_id, rs.signal_type, rs.evidence_type,
               rs.confidence, rs.summary, rs.details, rs.source_section, rs.metrics_json,
               rs.created_at, sd.source_type, sd.content_type, sd.title as document_title,
               c.ticker
        FROM research_signal rs
        JOIN source_document sd ON rs.document_id = sd.id
        JOIN company c ON rs.company_id = c.id
        WHERE 1=1
    """
    params: list[str | int] = []

    if company_id is not None:
        query += " AND rs.company_id = ?"
        params.append(company_id)
    if signal_type is not None:
        query += " AND rs.signal_type = ?"
        params.append(signal_type)
    if since is not None:
        query += " AND rs.created_at >= ?"
        params.append(since)
    if until is not None:
        query += " AND rs.created_at <= ?"
        params.append(until)
    if source_type is not None:
        query += " AND sd.source_type = ?"
        params.append(source_type)

    query += " ORDER BY rs.created_at DESC"

    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_signal_counts(
    conn: sqlite3.Connection, company_id: int
) -> dict[str, int]:
    """Get signal counts by type for a company."""
    rows = conn.execute(
        "SELECT signal_type, COUNT(*) as count FROM research_signal "
        "WHERE company_id = ? GROUP BY signal_type",
        (company_id,),
    ).fetchall()
    return {row["signal_type"]: row["count"] for row in rows}


def aggregate_by_source(
    conn: sqlite3.Connection, company_id: int
) -> dict[str, int]:
    """Get signal counts grouped by source type for a company."""
    rows = conn.execute(
        "SELECT sd.source_type, COUNT(*) as count FROM research_signal rs "
        "JOIN source_document sd ON rs.document_id = sd.id "
        "WHERE rs.company_id = ? GROUP BY sd.source_type",
        (company_id,),
    ).fetchall()
    return {row["source_type"]: row["count"] for row in rows}


def compare_periods(
    conn: sqlite3.Connection,
    company_id: int,
    period1_start: str,
    period1_end: str,
    period2_start: str,
    period2_end: str,
) -> dict[str, dict[str, int]]:
    """Compare signal counts between two time periods."""
    period1 = query_signals(conn, company_id=company_id, since=period1_start, until=period1_end)
    period2 = query_signals(conn, company_id=company_id, since=period2_start, until=period2_end)

    p1_counts: dict[str, int] = {}
    for s in period1:
        st = str(s["signal_type"])
        p1_counts[st] = p1_counts.get(st, 0) + 1

    p2_counts: dict[str, int] = {}
    for s in period2:
        st = str(s["signal_type"])
        p2_counts[st] = p2_counts.get(st, 0) + 1

    return {"period1": p1_counts, "period2": p2_counts}


def compute_overall_sentiment(
    conn: sqlite3.Connection, company_id: int
) -> str:
    """Compute overall sentiment from recent sentiment signals."""
    signals = query_signals(conn, company_id=company_id, signal_type="sentiment")
    if not signals:
        return "neutral"

    bullish = 0
    bearish = 0
    for s in signals[:20]:  # Use most recent 20 sentiment signals
        summary_lower = str(s.get("summary") or "").lower()
        if any(w in summary_lower for w in ["bullish", "positive", "strong", "grew", "beat"]):
            bullish += 1
        elif any(w in summary_lower for w in ["bearish", "negative", "weak", "decline", "miss"]):
            bearish += 1

    if bullish > bearish:
        return "bullish"
    elif bearish > bullish:
        return "bearish"
    return "neutral"


def check_document_exists(
    conn: sqlite3.Connection, source_type: str, source_id: str
) -> bool:
    """Check if a document has already been ingested."""
    row = conn.execute(
        "SELECT 1 FROM source_document WHERE source_type = ? AND source_id = ?",
        (source_type, source_id),
    ).fetchone()
    return row is not None
