# Data Model: Research Data Ingestion & Analysis

**Feature Branch**: `002-research-ingestion`
**Date**: 2026-02-16

## Entities

### Company (Watchlist Entry)

Represents a company on the user's research watchlist.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | integer | primary key, auto | Internal ID |
| ticker | text | unique, not null | Stock ticker symbol (e.g., "NVDA") |
| name | text | not null | Company name (e.g., "NVIDIA Corporation") |
| cik | text | nullable | SEC CIK number (for EDGAR lookups) |
| sector | text | nullable | Industry sector |
| added_at | text | not null, ISO 8601 UTC | When added to watchlist |
| active | integer | not null, default 1 | 1=active, 0=removed from watchlist |

**Notes**: CIK is resolved automatically from ticker via edgartools but cached here to avoid repeated lookups. `active=0` means soft-deleted (signals are preserved).

---

### Source Document

Represents a raw ingested document from any source, persisted locally before analysis.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | integer | primary key, auto | Internal ID |
| company_id | integer | foreign key → company(id), nullable | Associated company (null for non-company-specific content — e.g., podcast episode before analysis maps it to companies. Note: research_signal.company_id is always NOT NULL — the analyzer maps content to specific companies during analysis) |
| source_type | text | not null | One of: `sec_filing`, `earnings_transcript`, `podcast_episode`, `article`, `holdings_13f` |
| content_type | text | not null | Specific type: `10-K`, `10-Q`, `8-K`, `earnings_call`, `podcast_deep_dive`, `podcast_interview`, `analysis_article`, `daily_update`, `13F-HR` |
| source_id | text | not null | External identifier (accession number, transcript ID, episode URL, article URL) |
| title | text | not null | Document title |
| published_at | text | not null, ISO 8601 UTC | Original publication date |
| ingested_at | text | not null, ISO 8601 UTC | When we retrieved it |
| content_hash | text | not null | SHA-256 of raw content (for deduplication) |
| local_path | text | not null | Filesystem path to persisted raw document |
| file_size_bytes | integer | not null | Size of persisted file |
| analysis_status | text | not null, default 'pending' | One of: `pending`, `analyzing`, `complete`, `failed`, `skipped` |
| analysis_error | text | nullable | Error message if analysis failed |
| metadata_json | text | nullable | Additional source-specific metadata as JSON |

**Unique constraint**: `(source_type, source_id)` — prevents duplicate ingestion.

**Indexes**: `source_type`, `company_id`, `published_at`, `analysis_status`, `content_hash`.

---

### Research Signal

The core output — a structured finding from AI analysis of a source document.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | integer | primary key, auto | Internal ID |
| company_id | integer | foreign key → company(id), not null | Which company this signal is about |
| document_id | integer | foreign key → source_document(id), not null | Source document that produced this signal |
| signal_type | text | not null | One of: `sentiment`, `guidance_change`, `leadership_change`, `competitive_insight`, `risk_factor`, `financial_metric`, `investor_activity` |
| evidence_type | text | not null | `fact` (directly from source) or `inference` (AI analytical conclusion) |
| confidence | text | not null | `high`, `medium`, or `low` |
| summary | text | not null | Human-readable finding (1-3 sentences) |
| details | text | nullable | Extended explanation |
| source_section | text | nullable | Section of the document this came from (e.g., "Item 1A: Risk Factors") |
| metrics_json | text | nullable | Structured financial metrics as JSON array |
| created_at | text | not null, ISO 8601 UTC | When signal was generated |

**Indexes**: `company_id`, `signal_type`, `evidence_type`, `created_at`, `document_id`.

---

### Notable Investor

A tracked institutional investor whose 13F filings generate research signals.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | integer | primary key, auto | Internal ID |
| name | text | not null, unique | Investor/fund name (e.g., "Berkshire Hathaway") |
| cik | text | not null, unique | SEC CIK number for 13F lookup |
| active | integer | not null, default 1 | 1=tracking, 0=stopped |
| added_at | text | not null, ISO 8601 UTC | When added to tracking list |

---

### Ingestion Run

Tracks each research ingestion execution for audit and dedup purposes.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | integer | primary key, auto | Internal ID |
| started_at | text | not null, ISO 8601 UTC | When run started |
| completed_at | text | nullable, ISO 8601 UTC | When run finished |
| status | text | not null, default 'running' | `running`, `completed`, `failed` |
| documents_ingested | integer | not null, default 0 | Count of new documents ingested |
| signals_generated | integer | not null, default 0 | Count of new signals produced |
| errors_json | text | nullable | JSON array of error details |
| sources_json | text | nullable | JSON object of per-source stats, e.g. `{"sec": {"docs": 3, "signals": 12, "errors": 0}, "transcripts": {"docs": 1, "signals": 4, "errors": 0}}` |

---

## Relationships

```
company (1) ──── (many) source_document
company (1) ──── (many) research_signal
source_document (1) ──── (many) research_signal
notable_investor (1) ──── (many) source_document [via 13F filings]
ingestion_run (1) ──── (many) source_document [via ingested_at correlation]
```

## State Transitions

### Source Document Analysis Status

```
pending → analyzing → complete
                   → failed → pending (on retry)
pending → skipped (duplicate content_hash detected)
```

### Ingestion Run Status

```
running → completed
       → failed
```

## Migration Notes

- This is migration `002_research.sql` (after `001_init.sql` from scaffolding)
- All tables use SQLite STRICT mode
- All timestamps are ISO 8601 UTC strings
- JSON fields stored as TEXT (SQLite has no native JSON type in STRICT mode)
- Foreign keys enforced via `PRAGMA foreign_keys = ON` (already set in db.py)
- Append-only constraint NOT applied to these tables (unlike audit_log) — documents and signals can have their status updated

## Configuration

### Watchlist Management

Companies are managed via CLI commands:
- `finance-agent watchlist add NVDA` — adds ticker to watchlist (resolves name/CIK automatically)
- `finance-agent watchlist remove NVDA` — soft-deletes (sets active=0)
- `finance-agent watchlist list` — shows active watchlist with signal counts

### Notable Investor Management

- `finance-agent investors add "Berkshire Hathaway" 0001067983` — adds by name and CIK
- `finance-agent investors remove "Berkshire Hathaway"` — stops tracking
- `finance-agent investors list` — shows tracked investors

### Source Configuration

Sources are enabled/disabled via environment variables:
- `FINNHUB_API_KEY` set → earnings transcripts enabled
- `STRATECHERY_FEED_URL` set → Stratechery ingestion enabled
- `ASSEMBLYAI_API_KEY` set → podcast transcription enabled
- SEC EDGAR always enabled (free, only requires `EDGAR_IDENTITY`)
