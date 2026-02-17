# Implementation Plan: Architecture Pivot Cleanup

**Branch**: `007-architecture-cleanup` | **Date**: 2026-02-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/007-architecture-cleanup/spec.md`

## Summary

Remove ~3,500 lines of dead code (execution, engine, market layers) from the codebase, extract safety guardrails into an independent module, clean the database schema, streamline the CLI, and update documentation to reflect the research-first architecture established in the 006 pivot.

## Technical Context

**Language/Version**: Python 3.12+ (existing project)
**Primary Dependencies**: No changes — all kept modules use existing deps (edgartools, finnhub-python, anthropic, earningscall, feedparser, beautifulsoup4, pydantic, alpaca-py, httpx)
**Storage**: SQLite (WAL mode, PRAGMA user_version migrations). Cleanup migration drops 9 tables, renames engine_state → safety_state.
**Testing**: pytest (unit + integration). ~2,200 lines of tests removed alongside removed modules; ~2,000 lines of tests remain.
**Target Platform**: Intel NUC (home server), Docker
**Project Type**: Single Python project
**Performance Goals**: N/A (cleanup feature — no new runtime paths)
**Constraints**: Zero data loss on research tables and audit log. Safety state must be preserved through migration.
**Scale/Scope**: ~6,700 lines → ~3,300 lines. 29 source files → 20 files. 17 DB tables → 8 tables.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Safety First | PASS | Safety guardrails extracted into standalone `safety/` module. Kill switch and risk limits preserved. Utilization tracking deferred (no execution path yet). |
| II. Research-Driven | PASS | All research infrastructure (data sources, analysis pipeline, signals) fully preserved. |
| III. Modular Architecture | PASS | Removing dead layers directly supports "Less Code, More Context" philosophy. |
| IV. Audit Everything | PASS | Audit log table preserved. Migration logged. |
| V. Security by Design | PASS | No secrets affected. No new API surface. |
| Quality Gates | PASS | All remaining tests must pass. Linting must pass. |

No constitution violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/007-architecture-cleanup/
├── spec.md
├── plan.md              # This file
├── research.md          # Phase 0 output (minimal — cleanup decisions)
├── data-model.md        # Phase 1 output (safety_state table)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code — BEFORE Cleanup

```text
src/finance_agent/
├── __init__.py
├── config.py
├── db.py
├── cli.py                          # 1,620 lines (trim to ~420)
├── audit/
│   ├── __init__.py
│   └── logger.py
├── data/
│   ├── __init__.py
│   ├── investors.py
│   ├── models.py
│   ├── storage.py
│   ├── watchlist.py
│   └── sources/
│       ├── __init__.py
│       ├── sec_edgar.py
│       ├── finnhub.py
│       ├── earningscall_source.py
│       ├── acquired.py
│       ├── stratechery.py
│       └── investor_13f.py
├── research/
│   ├── __init__.py
│   ├── analyzer.py
│   ├── orchestrator.py
│   ├── pipeline.py
│   ├── prompts.py
│   └── signals.py
├── engine/                         # ← REMOVE ENTIRELY
│   ├── __init__.py
│   ├── account.py
│   ├── proposals.py
│   ├── risk.py
│   ├── scoring.py
│   └── state.py
├── execution/                      # ← REMOVE ENTIRELY
│   └── __init__.py
└── market/                         # ← REMOVE ENTIRELY
    ├── __init__.py
    ├── bars.py
    ├── client.py
    ├── indicators.py
    └── snapshot.py
```

### Source Code — AFTER Cleanup

```text
src/finance_agent/
├── __init__.py
├── config.py
├── db.py
├── cli.py                          # ~420 lines (engine/market commands removed)
├── audit/
│   ├── __init__.py
│   └── logger.py
├── data/
│   ├── __init__.py
│   ├── investors.py
│   ├── models.py
│   ├── storage.py
│   ├── watchlist.py
│   └── sources/
│       ├── __init__.py
│       ├── sec_edgar.py
│       ├── finnhub.py
│       ├── earningscall_source.py
│       ├── acquired.py
│       ├── stratechery.py
│       └── investor_13f.py
├── research/
│   ├── __init__.py
│   ├── analyzer.py
│   ├── orchestrator.py
│   ├── pipeline.py
│   ├── prompts.py
│   └── signals.py
└── safety/                         # ← NEW (extracted from engine/)
    ├── __init__.py
    └── guards.py                   # Kill switch + risk limit storage (~120 lines)
```

### Tests — AFTER Cleanup

```text
tests/
├── conftest.py                     # Updated: no engine/market fixtures
├── unit/
│   ├── test_analyzer.py
│   ├── test_audit.py
│   ├── test_config.py
│   ├── test_db.py
│   ├── test_models.py
│   ├── test_signals.py
│   ├── test_sources.py
│   ├── test_watchlist.py
│   └── test_safety.py             # ← NEW (extracted safety tests)
└── integration/
    ├── test_earningscall.py
    ├── test_finnhub.py
    ├── test_health.py              # Updated: no engine/market checks
    ├── test_research_pipeline.py
    └── test_sec_edgar.py
```

### Migrations — AFTER Cleanup

```text
migrations/
├── 001_init.sql                    # audit_log (version 1)
├── 003_market_data.sql             # KEPT as history — tables dropped in 006
├── 004_decision_engine.sql         # KEPT as history — tables dropped in 006
└── 006_architecture_cleanup.sql    # ← NEW: drops 9 tables, renames engine_state → safety_state
```

**Structure Decision**: Single Python project, existing layout preserved. Three module directories removed (engine/, execution/, market/), one added (safety/). Migration files 003 and 004 kept as historical record. Missing migration files (002, 005) are not recreated — the DB already has those tables from code-level migrations.

## Key Technical Decisions

### 1. Safety State Table Migration

**Approach**: Rename `engine_state` → `safety_state` using `ALTER TABLE` (SQLite 3.25+, Python 3.12 bundles SQLite 3.39+).

**Before** (migration 004):
```sql
CREATE TABLE engine_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_by TEXT NOT NULL DEFAULT 'system'
);
-- Contains rows: 'kill_switch', 'risk_settings'
```

**After** (migration 006):
```sql
ALTER TABLE engine_state RENAME TO safety_state;
-- Same schema, same data, new name
```

The safety module code (`safety/guards.py`) will read/write `safety_state` instead of `engine_state`. Kill switch and risk settings data are preserved automatically by the rename.

**Rationale**: Rename is the simplest migration — zero data transformation, zero risk of data loss, single SQL statement. The table schema is already suitable (key-value store with metadata).

### 2. Safety Module Scope

The safety module (`safety/guards.py`) extracts these functions from `engine/state.py`:
- `get_kill_switch(conn)` → reads kill switch state
- `set_kill_switch(conn, active, toggled_by, audit)` → toggles kill switch
- `get_risk_settings(conn)` → reads risk limit configuration
- `update_risk_setting(conn, key, value, updated_by, audit)` → updates a single limit

**Not extracted** (per clarification):
- Risk check functions from `engine/risk.py` (check_position_size, check_daily_loss, etc.) — these depend on account/position data from the execution layer which is being removed. Utilization tracking deferred.
- `run_all_risk_checks()` — writes to `risk_check_result` table which is being dropped.

The extracted module changes all SQL references from `engine_state` → `safety_state` and removes the `engine` audit category in favor of `safety`.

### 3. CLI Cleanup Strategy

**Remove entirely**:
- `engine` command group (lines 82-108 parser, lines ~675-1270 handlers): generate, review, killswitch, risk, risk-set, history, status
- `market` command group (lines 110-136 parser, lines ~1271-1620 handlers): fetch, snapshot, status, indicators

**Keep and update**:
- `version` — no changes
- `health` — remove engine/market checks, keep DB + research checks
- `watchlist` — no changes
- `investors` — no changes
- `research` — no changes
- `signals` — no changes
- `profile` — no changes

**No new commands** — safety state is programmatic-only (per clarification).

### 4. Database Migration (006_architecture_cleanup.sql)

```sql
-- Rename engine_state → safety_state (preserves kill switch + risk settings)
ALTER TABLE engine_state RENAME TO safety_state;

-- Drop market data tables (migration 003)
DROP TABLE IF EXISTS price_bar;
DROP TABLE IF EXISTS technical_indicator;
DROP TABLE IF EXISTS market_data_fetch;

-- Drop decision engine tables (migration 004) — except engine_state (now safety_state)
DROP TABLE IF EXISTS risk_check_result;
DROP TABLE IF EXISTS proposal_source;
DROP TABLE IF EXISTS trade_proposal;

-- Drop execution tables (migration 005)
DROP TABLE IF EXISTS position_snapshot;
DROP TABLE IF EXISTS broker_order;

PRAGMA user_version = 6;
```

**Order matters**: `risk_check_result` and `proposal_source` have foreign keys to `trade_proposal`, so they must be dropped first. `DROP TABLE IF EXISTS` is used because some environments may not have all tables (e.g., fresh installs that never ran migration 005).

### 5. Test Strategy

- **Remove**: `tests/unit/test_engine.py` (1,393 lines), `tests/unit/test_market.py` (505 lines), `tests/integration/test_engine.py` (111 lines), `tests/integration/test_market_data.py` (191 lines)
- **Add**: `tests/unit/test_safety.py` — tests for kill switch toggle, risk settings CRUD, validation ranges, default values
- **Update**: `tests/conftest.py` — no engine/market fixtures to remove (they're self-contained in removed test files), but verify `tmp_db` fixture still works with the new migration
- **Update**: `tests/integration/test_health.py` — remove engine/market health check assertions

### 6. Documentation Updates

- **README.md**: Rewrite to describe research-first system. Remove Decision Engine and Market Data sections. Update health check expected output. Update architecture description.
- **CHANGELOG.md**: Add version 0.7.0 entry documenting the architecture pivot cleanup.
- **Dockerfile**: No changes needed — it copies migrations/ and runs `finance-agent health`. Health check will be updated to not reference engine/market.
- **docker-compose.yml**: No changes needed — configuration is environment-based.
- **docker-entrypoint.sh**: Review for engine/market references.
- **CLAUDE.md**: Update Active Technologies section to remove engine/market references, add safety module.
- **pyproject.toml**: Update version to 0.7.0, update description.
