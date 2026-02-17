# Data Model: MCP Integration

**Feature**: 010-mcp-integration | **Date**: 2026-02-17

## Overview

The MCP server exposes existing database entities via 7 read-only tools. No new tables are created. This document maps existing DB schema to MCP tool parameter and response types.

## Source Entities (Existing DB Tables)

### company (migration 002)

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| ticker | TEXT UNIQUE | e.g., "AAPL" |
| name | TEXT | Full company name |
| cik | TEXT | SEC CIK number (nullable) |
| sector | TEXT | Industry sector (nullable) |
| added_at | TEXT | ISO 8601 timestamp |
| active | INTEGER | 1 = on watchlist, 0 = removed |

### source_document (migration 002)

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| company_id | INTEGER FK → company | Nullable |
| source_type | TEXT | e.g., "sec_edgar", "finnhub", "earningscall" |
| content_type | TEXT | e.g., "10-K", "earnings_call", "analyst_ratings" |
| source_id | TEXT | Unique within source_type |
| title | TEXT | Human-readable title |
| published_at | TEXT | ISO 8601 timestamp |
| ingested_at | TEXT | ISO 8601 timestamp |
| content_hash | TEXT | SHA-256 of content |
| local_path | TEXT | Relative path to content file |
| file_size_bytes | INTEGER | Content size |
| analysis_status | TEXT | "pending", "analyzing", "complete", "error" |
| analysis_error | TEXT | Error message (nullable) |
| metadata_json | TEXT | JSON blob (nullable) |

### research_signal (migration 002)

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| company_id | INTEGER FK → company | Required |
| document_id | INTEGER FK → source_document | Required |
| signal_type | TEXT | e.g., "revenue_growth", "management_concern" |
| evidence_type | TEXT | e.g., "quantitative", "qualitative" |
| confidence | TEXT | e.g., "high", "medium", "low" |
| summary | TEXT | One-line signal description |
| details | TEXT | Extended analysis (nullable) |
| source_section | TEXT | Section of document cited (nullable) |
| metrics_json | TEXT | JSON with numeric metrics (nullable) |
| created_at | TEXT | ISO 8601 timestamp |

### safety_state (migration 006)

| Column | Type | Notes |
|--------|------|-------|
| key | TEXT PK | "kill_switch" or "risk_settings" |
| value | TEXT | JSON-encoded state |
| updated_at | TEXT | ISO 8601 timestamp |
| updated_by | TEXT | "system", "user", "migration" |

### audit_log (migration 001)

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| timestamp | TEXT | ISO 8601 with milliseconds |
| event_type | TEXT | e.g., "signal_created", "pipeline_started" |
| source | TEXT | Module that generated the event |
| payload | TEXT | JSON blob |

### ingestion_run (migration 002)

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| started_at | TEXT | ISO 8601 timestamp |
| completed_at | TEXT | ISO 8601 (nullable — null if still running) |
| status | TEXT | "running", "completed", "failed" |
| documents_ingested | INTEGER | Count |
| signals_generated | INTEGER | Count |
| errors_json | TEXT | JSON array of error strings (nullable) |
| sources_json | TEXT | JSON array of source names (nullable) |

## MCP Tool Response Schemas

### get_signals Response

```json
[
  {
    "id": 42,
    "ticker": "AAPL",
    "company_name": "Apple Inc.",
    "signal_type": "revenue_growth",
    "evidence_type": "quantitative",
    "confidence": "high",
    "summary": "Q4 revenue grew 8% YoY driven by Services segment",
    "details": "...",
    "source_document_id": 15,
    "source_document_title": "Apple Inc. 10-K (2025)",
    "created_at": "2026-02-15T10:30:00Z"
  }
]
```

### list_documents Response

```json
[
  {
    "id": 15,
    "ticker": "AAPL",
    "company_name": "Apple Inc.",
    "source_type": "sec_edgar",
    "content_type": "10-K",
    "title": "Apple Inc. 10-K (2025)",
    "published_at": "2025-11-01T00:00:00Z",
    "ingested_at": "2026-02-14T08:00:00Z",
    "file_size_bytes": 245000,
    "analysis_status": "complete"
  }
]
```

### read_document Response

```json
{
  "id": 15,
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "source_type": "sec_edgar",
  "content_type": "10-K",
  "title": "Apple Inc. 10-K (2025)",
  "published_at": "2025-11-01T00:00:00Z",
  "file_size_bytes": 245000,
  "content": "Full document text here...",
  "truncated": false,
  "truncated_message": null
}
```

### get_watchlist Response

```json
[
  {
    "id": 1,
    "ticker": "AAPL",
    "name": "Apple Inc.",
    "cik": "0000320193",
    "sector": "Technology",
    "added_at": "2026-02-10T12:00:00Z"
  }
]
```

### get_safety_state Response

```json
{
  "kill_switch": {
    "active": false,
    "toggled_at": null,
    "toggled_by": null
  },
  "risk_settings": {
    "max_position_pct": 0.10,
    "max_daily_loss_pct": 0.05,
    "max_trades_per_day": 20,
    "max_positions_per_symbol": 2,
    "min_confidence_threshold": 0.45,
    "max_signal_age_days": 14,
    "min_signal_count": 3,
    "data_staleness_hours": 24
  },
  "updated_at": "2026-02-10T12:00:00Z"
}
```

### get_audit_log Response

```json
[
  {
    "id": 100,
    "timestamp": "2026-02-15T10:30:00.123Z",
    "event_type": "signal_created",
    "source": "research.analyzer",
    "payload": {"signal_id": 42, "ticker": "AAPL", "signal_type": "revenue_growth"}
  }
]
```

### get_pipeline_status Response

```json
{
  "id": 5,
  "started_at": "2026-02-15T08:00:00Z",
  "completed_at": "2026-02-15T08:12:34Z",
  "status": "completed",
  "documents_ingested": 12,
  "signals_generated": 8,
  "errors": [],
  "sources": ["sec_edgar", "finnhub", "transcripts"]
}
```

## Relationships (Read Path)

```
get_signals → JOIN research_signal + company + source_document
list_documents → JOIN source_document + company
read_document → source_document + filesystem (local_path)
get_watchlist → company WHERE active = 1
get_safety_state → safety_state (key-value lookup)
get_audit_log → audit_log (filter by event_type, timestamp)
get_pipeline_status → ingestion_run ORDER BY started_at DESC LIMIT 1
```

## Empty State Handling

All tools return graceful empty results:
- `get_signals` with unknown ticker → `[]` (empty list)
- `list_documents` with no documents → `[]`
- `read_document` with invalid ID → error string: "Document not found"
- `get_watchlist` with no companies → `[]`
- `get_safety_state` with missing keys → error string with setup instructions
- `get_audit_log` with no entries → `[]`
- `get_pipeline_status` with no runs → `{"status": "no_runs", "message": "No pipeline runs recorded yet"}`
