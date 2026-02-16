# Data Model: Project Scaffolding

**Feature**: 001-project-scaffolding
**Date**: 2026-02-16

## Entities

### AuditEvent

An immutable record of something that happened in the system. This is the only table created in the scaffolding feature — subsequent features add their own tables via migrations.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique event identifier |
| timestamp | TEXT | NOT NULL, DEFAULT (ISO 8601 UTC) | When the event occurred |
| event_type | TEXT | NOT NULL | Category: "startup", "config_validated", "health_check", etc. |
| source | TEXT | NOT NULL | Which component generated it: "cli", "config", "db", "execution", etc. |
| payload | TEXT | NOT NULL, DEFAULT '{}' | JSON-encoded event-specific details |

**Append-only enforcement**: BEFORE UPDATE and BEFORE DELETE triggers with `RAISE(ABORT, ...)` prevent any modification or deletion through the application layer.

**Indexes**:
- `idx_audit_log_timestamp` on `timestamp` — for time-range queries
- `idx_audit_log_event_type` on `event_type` — for filtering by category

### DatabaseMigration (implicit)

Tracked via `PRAGMA user_version` — a 32-bit integer stored in the SQLite file header. No separate table needed. The migration runner reads `PRAGMA user_version`, compares against numbered `.sql` files in `migrations/`, and executes any with a higher number.

### Configuration (runtime only, not persisted)

Configuration is loaded from environment variables at startup and held in memory. It is NOT stored in the database.

| Setting | Env Var | Required | Default | Description |
|---------|---------|----------|---------|-------------|
| Paper API Key | `ALPACA_PAPER_API_KEY` | Yes (for paper) | — | Alpaca paper trading API key ID |
| Paper Secret Key | `ALPACA_PAPER_SECRET_KEY` | Yes (for paper) | — | Alpaca paper trading secret key |
| Live API Key | `ALPACA_LIVE_API_KEY` | No | — | Alpaca live trading API key ID |
| Live Secret Key | `ALPACA_LIVE_SECRET_KEY` | No | — | Alpaca live trading secret key |
| Trading Mode | `TRADING_MODE` | No | `paper` | `paper` or `live`. Determines which keys are used. |
| Database Path | `DB_PATH` | No | `data/finance_agent.db` | Path to SQLite database file |
| Log Level | `LOG_LEVEL` | No | `INFO` | Python logging level |

**Mode detection logic**:
1. If `TRADING_MODE=live` and live keys are present → live mode (with warning)
2. If `TRADING_MODE=live` but live keys missing → error, fail fast
3. If both paper and live keys present but `TRADING_MODE` not set → paper mode (with warning about live keys being present)
4. Default → paper mode

## Initial Migration: `001_init.sql`

```sql
-- Finance Agent: Initial schema
-- Creates the audit_log table with append-only enforcement

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}'
) STRICT;

CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_event_type ON audit_log(event_type);

-- Append-only: prevent updates
CREATE TRIGGER IF NOT EXISTS audit_log_no_update
BEFORE UPDATE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'Updates are not allowed on audit_log (append-only)');
END;

-- Append-only: prevent deletes
CREATE TRIGGER IF NOT EXISTS audit_log_no_delete
BEFORE DELETE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'Deletes are not allowed on audit_log (append-only)');
END;

PRAGMA user_version = 1;
```

## State Transitions

### Application Startup Sequence

```
INIT → LOAD_CONFIG → VALIDATE_CONFIG → INIT_DB → RUN_MIGRATIONS → HEALTH_CHECK → READY
  │         │              │                │            │               │
  │         │              │                │            │               └─ audit: "health_check"
  │         │              │                │            └─ audit: "migrations_applied"
  │         │              │                └─ audit: "db_initialized"
  │         │              └─ FAIL if missing required config
  │         └─ Read env vars + .env file
  └─ audit: "startup"
```

Each step logs an audit event. If any step fails, the system exits with a clear error message.
