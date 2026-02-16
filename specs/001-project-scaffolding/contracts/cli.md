# CLI Contract: finance-agent

The `finance-agent` CLI is the primary entry point for the application. It is installed as a console_script via `[project.scripts]` in `pyproject.toml`.

## Commands

### `finance-agent health`

Validates configuration, database, and broker connectivity.

**Input**: None (reads from environment)

**Output** (stdout):
```
[PAPER MODE] Finance Agent v0.1.0
Configuration: OK (all required settings present)
Database: OK (finance_agent.db, schema version 1)
Broker API: OK (account ACTIVE, buying power: $100,000.00)
```

**Exit codes**:
- `0`: All checks passed
- `1`: One or more checks failed (details in output)

**Failure output** (example):
```
[PAPER MODE] Finance Agent v0.1.0
Configuration: FAIL
  - Missing: ALPACA_PAPER_API_KEY
  - Missing: ALPACA_PAPER_SECRET_KEY
Database: OK (finance_agent.db, schema version 1)
Broker API: SKIP (configuration incomplete)
```

### `finance-agent version`

Prints version and exits.

**Output**: `finance-agent 0.1.0`

**Exit code**: `0`

## Configuration Contract

The config module exposes a `Settings` dataclass (or similar) loaded from environment variables. It is NOT a Pydantic model to avoid pulling in pydantic as a direct dependency for config (alpaca-py already brings it in, but our config layer should be independent).

### Loading order
1. Read `.env` file if present (via `python-dotenv`, dev dependency only)
2. Read environment variables (override `.env`)
3. Apply defaults for optional settings
4. Validate required settings

### Validation
- All required settings must be non-empty strings
- `TRADING_MODE` must be `paper` or `live` (case-insensitive)
- `LOG_LEVEL` must be a valid Python logging level name
- `DB_PATH` parent directory must be writable

## Database Contract

### Connection factory: `get_connection(db_path: str) -> sqlite3.Connection`

Returns a configured SQLite connection with all recommended PRAGMAs set.

### Migration runner: `run_migrations(conn: sqlite3.Connection, migrations_dir: str) -> int`

Applies all pending migrations. Returns the number of migrations applied. Each migration runs in a transaction.

### Audit logger: `AuditLogger.log(event_type: str, source: str, payload: dict) -> None`

Writes an immutable audit event to the `audit_log` table. The `payload` dict is JSON-serialized.
