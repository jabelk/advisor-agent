# Research: Architecture Pivot Cleanup

## Phase 0 Output

Minimal research needed — this is a cleanup/refactoring feature with well-understood scope from the 006 architecture research sprint.

### Decision 1: Safety State Table Migration Strategy

**Decision**: Rename `engine_state` → `safety_state` using `ALTER TABLE RENAME`.

**Rationale**: SQLite 3.25+ supports `ALTER TABLE ... RENAME TO`. Python 3.12 bundles SQLite 3.39+, so this is guaranteed to work on all target environments. The rename preserves all data (kill switch state, risk settings) with zero transformation risk.

**Alternatives considered**:
- Create new table + copy data + drop old: More complex, same result, higher risk of data loss during copy.
- Keep `engine_state` name: Misleading — the table no longer belongs to an "engine" module.

### Decision 2: Risk Check Functions

**Decision**: Do not extract `check_position_size()`, `check_daily_loss()`, `check_trade_count()`, or `check_concentration()` from `engine/risk.py`.

**Rationale**: These functions depend on account summaries, position lists, and order counts from the Alpaca API — data that was provided by the now-removed execution layer. In the new architecture, trades happen via Alpaca MCP, so there's no Python-side execution path to feed these checks. Utilization tracking is deferred to a future feature when the MCP execution flow is designed.

**What IS extracted**: `get_kill_switch()`, `set_kill_switch()`, `get_risk_settings()`, `update_risk_setting()` — these are purely storage operations with no external dependencies.

### Decision 3: Risk Settings Scope Reduction

**Decision**: Remove engine-specific risk settings from `DEFAULT_RISK_SETTINGS` and `RISK_SETTING_RANGES`. Keep only the four core safety limits.

**Keep** (safety guardrails per constitution):
- `max_position_pct` (0.01–0.50, default 0.10)
- `max_daily_loss_pct` (0.01–0.20, default 0.05)
- `max_trades_per_day` (1–100, default 20)
- `max_positions_per_symbol` (1–10, default 2)

**Remove** (engine-specific, no longer applicable):
- `min_confidence_threshold` — scoring engine removed
- `max_signal_age_days` — scoring engine removed
- `min_signal_count` — scoring engine removed
- `data_staleness_hours` — market data layer removed

The existing `risk_settings` JSON in the database will still contain the old keys, but the safety module will only read/write the four kept keys. Old keys are ignored (not deleted from JSON, just not used).

### Decision 4: Missing Migration Files (002, 005)

**Decision**: Do not recreate migration files 002 and 005.

**Rationale**: The tables they create already exist in all databases (created via code-level migrations during features 002 and 005). The migration runner skips files with version <= current_version. Creating these files now would have no effect on existing databases and could cause confusion about when they were actually created.

### Decision 5: Historical Migration Files (003, 004)

**Decision**: Keep `003_market_data.sql` and `004_decision_engine.sql` in the migrations directory.

**Rationale**: These files are historical records of what was created. The new migration 006 drops the tables they created. A developer reading the migration history can understand the full lifecycle: tables created in 003/004, tables dropped in 006. Deleting the files would lose this history.
