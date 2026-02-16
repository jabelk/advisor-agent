# Database Migrations

## Conventions

- **File naming**: `NNN_description.sql` (e.g., `001_init.sql`, `002_add_trades.sql`)
- **Version tracking**: Each migration MUST end with `PRAGMA user_version = N;` where N matches the file prefix
- **Atomicity**: Each migration runs as a single `executescript()` call
- **Idempotent DDL**: Use `IF NOT EXISTS` for CREATE TABLE/INDEX/TRIGGER
- **Order**: Migrations are applied in numeric order, skipping any already applied
- **No rollbacks**: Migrations are forward-only. To undo, create a new migration.

## How it works

The migration runner in `src/finance_agent/db.py`:
1. Reads `PRAGMA user_version` from the database
2. Scans this directory for `.sql` files with numeric prefixes
3. Executes any file whose number is greater than the current version
4. The SQL file itself sets the new `PRAGMA user_version`
