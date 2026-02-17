# MCP Tool Contracts: Finance Agent Research DB

**Feature**: 010-mcp-integration | **Date**: 2026-02-17

## Server Info

- **Name**: `Finance Agent Research DB`
- **Transport**: stdio (default), HTTP (--http flag)
- **Protocol**: MCP (Model Context Protocol) via FastMCP 2.x
- **Database**: SQLite read-only (`?mode=ro`)

---

## Tool 1: get_signals (FR-001)

**Purpose**: Query research signals by ticker, filterable by date range, signal type, and confidence.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `ticker` | `str` | Yes | — | Company ticker symbol (e.g., "AAPL") |
| `limit` | `int` | No | `20` | Maximum number of signals to return |
| `signal_type` | `str` | No | `""` | Filter by signal type (e.g., "revenue_growth"). Empty = all types |
| `days` | `int` | No | `30` | Only return signals created within this many days |

### SQL Query

```sql
SELECT
    rs.id, c.ticker, c.name AS company_name,
    rs.signal_type, rs.evidence_type, rs.confidence,
    rs.summary, rs.details,
    rs.document_id AS source_document_id,
    sd.title AS source_document_title,
    rs.created_at
FROM research_signal rs
JOIN company c ON rs.company_id = c.id
JOIN source_document sd ON rs.document_id = sd.id
WHERE c.ticker = ?
  AND rs.created_at >= datetime('now', '-' || ? || ' days')
  AND (? = '' OR rs.signal_type = ?)
ORDER BY rs.created_at DESC
LIMIT ?
```

### Response

Returns `list[dict]`. Empty list if no signals found (not an error).

### Edge Cases

- Unknown ticker → empty list
- Ticker not on watchlist → empty list with note
- No signals in date range → empty list

---

## Tool 2: list_documents (FR-002)

**Purpose**: List ingested source documents, filterable by company, content type, and date range.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `ticker` | `str` | No | `""` | Filter by company ticker. Empty = all companies |
| `content_type` | `str` | No | `""` | Filter by content type (e.g., "10-K", "earnings_call"). Empty = all |
| `limit` | `int` | No | `20` | Maximum number of documents to return |
| `days` | `int` | No | `90` | Only return documents ingested within this many days |

### SQL Query

```sql
SELECT
    sd.id, c.ticker, c.name AS company_name,
    sd.source_type, sd.content_type, sd.title,
    sd.published_at, sd.ingested_at,
    sd.file_size_bytes, sd.analysis_status
FROM source_document sd
LEFT JOIN company c ON sd.company_id = c.id
WHERE sd.ingested_at >= datetime('now', '-' || ? || ' days')
  AND (? = '' OR c.ticker = ?)
  AND (? = '' OR sd.content_type = ?)
ORDER BY sd.ingested_at DESC
LIMIT ?
```

### Response

Returns `list[dict]`. Empty list if no documents found.

### Edge Cases

- No documents ingested → empty list
- Unknown content_type → empty list (no error)

---

## Tool 3: read_document (FR-003, FR-010)

**Purpose**: Retrieve full text content of a specific document by ID.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `document_id` | `int` | Yes | — | The source_document.id to retrieve |

### SQL Query

```sql
SELECT
    sd.id, c.ticker, c.name AS company_name,
    sd.source_type, sd.content_type, sd.title,
    sd.published_at, sd.local_path, sd.file_size_bytes
FROM source_document sd
LEFT JOIN company c ON sd.company_id = c.id
WHERE sd.id = ?
```

### Filesystem Read

```python
content_path = RESEARCH_DATA_DIR / row["local_path"]
if content_path.exists():
    content = content_path.read_text(encoding="utf-8")
    if len(content) > 50_000:
        content = content[:50_000]
        truncated = True
        truncated_message = f"Content truncated from {len(full_content)} to 50,000 characters."
else:
    content = None
    truncated_message = "Content file not found on disk. Metadata available only."
```

### Response

Returns `dict` with document metadata + content. Error string if document ID not found.

### Edge Cases

- Invalid document_id → error string: "Document not found with ID {id}"
- File deleted from disk → metadata returned, content = None, note about missing file
- Content > 50K chars → truncated with message (FR-010)

---

## Tool 4: get_watchlist (FR-004)

**Purpose**: List all active companies on the watchlist.

### Parameters

None.

### SQL Query

```sql
SELECT id, ticker, name, cik, sector, added_at
FROM company
WHERE active = 1
ORDER BY ticker ASC
```

### Response

Returns `list[dict]`. Empty list if no companies on watchlist.

### Edge Cases

- Empty watchlist → empty list with message "No companies on the watchlist"
- All companies deactivated → same as empty

---

## Tool 5: get_safety_state (FR-005)

**Purpose**: Read kill switch status and all risk limit values.

### Parameters

None.

### SQL Query

```sql
SELECT key, value, updated_at, updated_by
FROM safety_state
```

### Response

Returns `dict` with parsed kill_switch and risk_settings JSON values, plus updated_at timestamp.

### Edge Cases

- Missing safety_state rows → error string: "Safety state not initialized. Run migrations first."
- Malformed JSON in value column → error string with details

---

## Tool 6: get_audit_log (FR-006)

**Purpose**: Retrieve recent audit log entries, filterable by event type.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `event_type` | `str` | No | `""` | Filter by event type (e.g., "signal_created"). Empty = all types |
| `limit` | `int` | No | `50` | Maximum entries to return |
| `days` | `int` | No | `7` | Only return entries within this many days |

### SQL Query

```sql
SELECT id, timestamp, event_type, source, payload
FROM audit_log
WHERE timestamp >= datetime('now', '-' || ? || ' days')
  AND (? = '' OR event_type = ?)
ORDER BY timestamp DESC
LIMIT ?
```

### Response

Returns `list[dict]` with payload parsed from JSON string to dict.

### Edge Cases

- No audit entries → empty list
- Unknown event_type filter → empty list (no error)

---

## Tool 7: get_pipeline_status (FR-007)

**Purpose**: Get status of the most recent research pipeline run.

### Parameters

None.

### SQL Query

```sql
SELECT
    id, started_at, completed_at, status,
    documents_ingested, signals_generated,
    errors_json, sources_json
FROM ingestion_run
ORDER BY started_at DESC
LIMIT 1
```

### Response

Returns `dict` with errors_json and sources_json parsed from JSON strings to lists.

### Edge Cases

- No pipeline runs recorded → `{"status": "no_runs", "message": "No pipeline runs recorded yet. Run: uv run finance-agent research run"}`
- Pipeline currently running → status = "running", completed_at = null

---

## Cross-Cutting Contracts

### Read-Only Enforcement (FR-008)

All tools open the database with:
```python
sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
```

Any accidental write attempt raises `sqlite3.OperationalError: attempt to write a readonly database`.

### Structured Responses (FR-011)

All responses are Python dicts/lists that FastMCP serializes to JSON. Claude receives structured data it can format conversationally. Each response includes enough context (timestamps, counts, references) for informed follow-up questions.

### Error Handling

Tool errors return descriptive strings (not exceptions) so Claude can relay the issue to the user conversationally:
- "Document not found with ID 999"
- "Safety state not initialized. Run migrations first."
- "Database connection failed: {details}"

### Timeout / Lock Handling

SQLite connections use a 5-second busy timeout:
```python
conn.execute("PRAGMA busy_timeout = 5000")
```

If the lock cannot be acquired within 5 seconds, the tool returns an error message instead of hanging.
