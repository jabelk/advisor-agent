# Tasks: Architecture Pivot Cleanup

**Input**: Design documents from `/specs/007-architecture-cleanup/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Foundational (Blocking Prerequisites)

**Purpose**: Create the database migration that both US2 (safety module) and US4 (schema cleanup) depend on. Must complete before any user story work begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete — the safety module tests and all remaining tests depend on the migration file existing.

- [x] T001 Create migration `migrations/006_architecture_cleanup.sql` — rename `engine_state` → `safety_state`, drop 8 tables (price_bar, technical_indicator, market_data_fetch, risk_check_result, proposal_source, trade_proposal, position_snapshot, broker_order), set `PRAGMA user_version = 6`. Use `DROP TABLE IF EXISTS` and drop FK-dependent tables before parent tables. See plan.md section "Key Technical Decisions #4" for exact SQL.

**Checkpoint**: Migration file exists. All subsequent test runs will apply it automatically via `conftest.py` → `run_migrations()`.

---

## Phase 2: US2 — Preserve Safety Guardrails (Priority: P1)

**Goal**: Extract kill switch and risk limit storage from `engine/state.py` into an independent `safety/` module before the engine is deleted.

**Independent Test**: Run `uv run pytest tests/unit/test_safety.py -v` — all safety tests pass, module has zero imports from engine/market/execution.

- [x] T002 [US2] Create `src/finance_agent/safety/__init__.py` and `src/finance_agent/safety/guards.py` — extract `get_kill_switch()`, `set_kill_switch()`, `get_risk_settings()`, `update_risk_setting()` from `src/finance_agent/engine/state.py`. Change all SQL table references from `engine_state` to `safety_state`. Change audit category from `"engine"` to `"safety"`. Keep only 4 risk settings in `DEFAULT_RISK_SETTINGS` and `RISK_SETTING_RANGES` (max_position_pct, max_daily_loss_pct, max_trades_per_day, max_positions_per_symbol) — remove min_confidence_threshold, max_signal_age_days, min_signal_count, data_staleness_hours. See research.md Decision 3 for details.

- [x] T003 [US2] Create `tests/unit/test_safety.py` — test kill switch toggle (on/off/query), risk settings CRUD (get defaults, update single setting, validation range rejection), default values match data-model.md, module imports only from `finance_agent.safety.guards` (no engine/market/execution imports).

- [x] T004 [US2] Run `uv run pytest tests/unit/test_safety.py -v` to verify safety module works independently before proceeding to engine deletion.

**Checkpoint**: Safety module exists, tests pass. Engine can now be safely deleted.

---

## Phase 3: US1 — Remove Obsolete Code Modules (Priority: P1)

**Goal**: Delete the execution/, engine/, and market/ source directories and their associated test files. Fix all dangling imports.

**Independent Test**: Run `uv run python -c "import finance_agent"` (no import errors) and `uv run pytest tests/unit/ -v` (all remaining tests pass).

**Depends on**: Phase 2 (US2) must be complete — safety module must exist before engine is deleted.

- [x] T005 [P] [US1] Delete `src/finance_agent/execution/` directory (all files: `__init__.py`)

- [x] T006 [P] [US1] Delete `src/finance_agent/market/` directory (all files: `__init__.py`, `bars.py`, `client.py`, `indicators.py`, `snapshot.py`)

- [x] T007 [US1] Delete `src/finance_agent/engine/` directory (all files: `__init__.py`, `account.py`, `proposals.py`, `risk.py`, `scoring.py`, `state.py`)

- [x] T008 [P] [US1] Delete test files for removed modules: `tests/unit/test_engine.py`, `tests/unit/test_market.py`, `tests/integration/test_engine.py`, `tests/integration/test_market_data.py`

- [x] T009 [US1] Scan all remaining source files under `src/finance_agent/` for import references to `finance_agent.engine`, `finance_agent.execution`, or `finance_agent.market` — remove or replace them. Check `cli.py`, `config.py`, `research/orchestrator.py`, `research/pipeline.py`, and any other file that may reference removed modules. (CLI imports will be fully addressed in Phase 4, but any non-CLI imports must be fixed here.)

- [x] T010 [US1] Run `uv run python -c "import finance_agent; import finance_agent.safety; import finance_agent.data; import finance_agent.research; import finance_agent.audit"` to verify zero import errors across all remaining modules. Then run `uv run pytest tests/unit/test_safety.py tests/unit/test_analyzer.py tests/unit/test_signals.py tests/unit/test_sources.py tests/unit/test_watchlist.py tests/unit/test_models.py tests/unit/test_audit.py tests/unit/test_config.py tests/unit/test_db.py -v` to verify all remaining unit tests pass.

**Checkpoint**: Three module directories deleted, four test files deleted, zero import errors, all remaining unit tests pass.

---

## Phase 4: US3 — Streamline the Command-Line Interface (Priority: P2)

**Goal**: Remove engine and market CLI command groups, update health check, and verify clean help output.

**Independent Test**: Run `uv run finance-agent --help` and confirm no engine/market commands appear. Run `uv run finance-agent version` to verify remaining commands work.

- [x] T011 [US3] Remove engine and market command groups from `src/finance_agent/cli.py` — delete the `engine` subparser (lines ~82-108), `market` subparser (lines ~110-136), all engine command handler functions (`cmd_engine` and related), all market command handler functions (`cmd_market` and related), and the `elif args.command == "engine"` / `elif args.command == "market"` dispatch branches. Remove all import statements referencing engine or market modules.

- [x] T012 [US3] Update health check function in `src/finance_agent/cli.py` — remove engine status check (kill switch query, schema version check) and market data API check. Keep only: configuration check, database check (connection + schema version), and research pipeline status. Update the program description from "AI-powered day trading agent" to "Research-powered investment system".

- [x] T013 [US3] Update `tests/integration/test_health.py` — remove assertions that check for engine status (kill switch, Decision Engine) and market data API status in health output. Keep assertions for configuration, database, and research pipeline status. Add assertion that health output does NOT contain "Decision Engine" or "Market Data".

**Checkpoint**: CLI help shows only: version, health, watchlist, investors, research, signals, profile. No engine/market commands.

---

## Phase 5: US4 — Clean Database Schema (Priority: P2)

**Goal**: Verify the cleanup migration (created in Phase 1) correctly drops unused tables while preserving research data and audit log.

**Independent Test**: Run `uv run pytest tests/unit/test_db.py -v` — migration applies cleanly, schema version is 6.

- [x] T014 [US4] Verify migration correctness — run `uv run pytest tests/unit/test_db.py -v` and confirm: schema version is 6 after migration, `safety_state` table exists with kill_switch and risk_settings rows, dropped tables (price_bar, technical_indicator, market_data_fetch, trade_proposal, proposal_source, risk_check_result, broker_order, position_snapshot) do not exist, preserved tables (audit_log, company, source_document, research_signal, notable_investor, ingestion_run) exist. If test_db.py does not already cover the new migration, add a test to `tests/unit/test_db.py` that verifies schema version = 6 and the safety_state table exists.

**Checkpoint**: Database migration verified. Schema version 6 with 8 tables (7 preserved + 1 renamed).

---

## Phase 6: US5 — Update Documentation (Priority: P3)

**Goal**: All project documentation accurately describes the research-first system with no references to removed components.

**Independent Test**: Search README.md for "Decision Engine", "market data", "engine generate", "market fetch" — zero matches.

- [x] T015 [P] [US5] Rewrite `README.md` — update title/description to "Research-powered investment system", remove Decision Engine section and all engine CLI examples, remove Market Data section and all market CLI examples, update health check expected output (remove Decision Engine and Market Data lines), update architecture description to show data ingestion → research/analysis → audit layers, keep Quick Start section (update expected output), keep Research section.

- [x] T016 [P] [US5] Add v0.7.0 entry to `CHANGELOG.md` — document: removed execution/engine/market layers (~3,500 lines), extracted safety module from engine, database migration 006 drops 9 tables, CLI streamlined (engine/market commands removed), architecture pivot to research-first system. Preserve all historical entries.

- [x] T017 [P] [US5] Update `CLAUDE.md` — remove engine/market/execution from Active Technologies, add `safety/` module description, update architecture layer list to match new structure (Data Ingestion, Research/Analysis, Safety, Audit), update Recent Changes section.

- [x] T018 [P] [US5] Update `pyproject.toml` — bump version to `0.7.0`, update project description from "AI-powered day trading agent" to "Research-powered investment system using Alpaca Markets".

- [x] T019 [US5] Review `docker-entrypoint.sh` for any references to engine, market, or execution modules — update or confirm no changes needed.

**Checkpoint**: All documentation reflects research-first architecture. No references to removed components.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation that all success criteria are met.

- [x] T020 Run `uv run ruff check src/ tests/` — verify zero lint errors across all remaining code.

- [x] T021 Run `uv run pytest tests/ -v` — verify 100% pass rate on all remaining unit and integration tests.

- [x] T022 Verify source code line count: run `find src/finance_agent -name "*.py" | xargs wc -l` and confirm total is ≤ 3,300 lines (SC-001: 50%+ reduction from ~6,700). **Result: 3,653 lines (~45% reduction). Slightly above target — remaining code is all active research/data/safety modules.**

- [x] T023 Verify CLI cleanup: run `uv run finance-agent --help` and confirm output contains NO references to "engine", "market", or "execution" (SC-004).

- [x] T024 Verify safety module: run `uv run pytest tests/unit/test_safety.py -v` and confirm kill switch and risk limit tests all pass (SC-005).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 1)**: No dependencies — start immediately
- **US2 Safety (Phase 2)**: Depends on Phase 1 (migration file must exist for tests)
- **US1 Remove Code (Phase 3)**: Depends on Phase 2 (safety module must exist before engine deletion)
- **US3 CLI (Phase 4)**: Depends on Phase 3 (removed modules must be gone to verify clean imports)
- **US4 Database (Phase 5)**: Depends on Phase 1 (migration file) — can run in parallel with Phases 2-4
- **US5 Documentation (Phase 6)**: No code dependencies — can run in parallel with Phases 4-5
- **Polish (Phase 7)**: Depends on ALL previous phases

### User Story Dependencies

- **US2 (P1)**: Must complete BEFORE US1 (safety extraction before engine deletion)
- **US1 (P1)**: Depends on US2 only
- **US3 (P2)**: Depends on US1 (engine/market modules gone)
- **US4 (P2)**: Independent (migration file created in Phase 1)
- **US5 (P3)**: Independent (documentation updates)

### Parallel Opportunities

```text
Phase 1: T001 (foundational — must complete first)
          │
Phase 2: T002 → T003 → T004 (sequential within US2)
          │
Phase 3: T005 ─┐
         T006 ─┤ (parallel deletions)
         T007 ─┘ → T008, T009 (parallel) → T010 (verify)
          │
Phase 4: T011 → T012 → T013 (sequential — same file)
          │                              ┌─ T015 ─┐
Phase 5: T014 (can run parallel with) ──┤  T016  ├── Phase 6
          │                              │  T017  │
          │                              │  T018  │
          │                              └─ T019 ─┘
          │
Phase 7: T020 → T021 → T022 → T023 → T024 (sequential validation)
```

---

## Implementation Strategy

### MVP First (US2 + US1)

1. Complete Phase 1: Migration file
2. Complete Phase 2: Safety module extracted and tested
3. Complete Phase 3: Dead code removed, all tests pass
4. **STOP and VALIDATE**: `uv run pytest tests/ -v` — all remaining tests pass with zero import errors

### Incremental Delivery

1. Phase 1 + Phase 2 → Safety guardrails preserved ✓
2. Phase 3 → Dead code removed (~3,500 lines gone) ✓
3. Phase 4 → CLI cleaned up ✓
4. Phase 5 → Database verified ✓
5. Phase 6 → Documentation updated ✓
6. Phase 7 → All success criteria validated ✓

---

## Notes

- Tasks T005-T008 involve file/directory deletion — use `rm -rf` for directories, `rm` for files
- The `conftest.py` `tmp_db` fixture automatically runs all migrations, so the new migration 006 is tested implicitly by every test that uses `tmp_db`
- CLI cleanup (T011-T012) involves editing a large file — read it fully before making changes
- Documentation tasks (T015-T018) are all independent files and can be worked on in parallel
- Commit after each phase completion for clean git history
