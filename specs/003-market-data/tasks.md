# Tasks: Market Data Integration

**Input**: Design documents from `/specs/003-market-data/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: Unit tests (mocked Alpaca client) and integration tests (live API) are included per plan.md specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create module structure, migration file, and Alpaca data client wrapper

- [X] T001 Create market module package directory and `__init__.py` at src/finance_agent/market/__init__.py
- [X] T002 Create migration file `003_market_data.sql` at migrations/003_market_data.sql with price_bar, technical_indicator, and market_data_fetch tables per data-model.md
- [X] T003 Implement Alpaca data client wrapper with token-bucket rate limiter (180 req/min) in src/finance_agent/market/client.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Unit test scaffolding and migration verification — MUST complete before any user story

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create unit test file for market module at tests/unit/test_market.py with test class scaffolding and shared fixtures (mock Alpaca client, in-memory SQLite with migration applied)
- [X] T005 Create integration test file at tests/integration/test_market_data.py with shared fixtures (real Alpaca client, temp SQLite DB) and skip-if-no-keys decorator
- [X] T006 Verify migration applies cleanly: add a unit test in tests/unit/test_market.py that runs 003_market_data.sql on a fresh DB and asserts all 3 tables and indexes exist

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Fetch Historical Price Bars (Priority: P1) MVP

**Goal**: Operator can fetch and store daily + hourly OHLCV bars for watchlist companies with incremental updates, rate limiting, and audit logging.

**Independent Test**: Add a company to watchlist, run `market fetch`, verify bars stored in SQLite and queryable by ticker/timeframe/date.

### Implementation for User Story 1

- [X] T007 [US1] Implement bar fetch and storage logic in src/finance_agent/market/bars.py — functions: `fetch_bars(conn, client, ticker, company_id, timeframe, full)` fetching from Alpaca with `Adjustment.SPLIT`, `INSERT OR IGNORE` into price_bar table; `get_latest_bar_timestamp(conn, ticker, timeframe)` for incremental start date; `query_bars(conn, ticker, timeframe, start, end)` returning list of Row
- [X] T008 [US1] Implement `market fetch` CLI subcommand in src/finance_agent/cli.py — add `market` parser group with `fetch` subcommand accepting `--ticker`, `--timeframe {day,hour}`, `--full` flags; iterate watchlist companies, call `fetch_bars` for each, print summary output per contracts/cli.md format; log each fetch to audit trail via `market_data_fetch` table
- [X] T009 [US1] Add unit tests for bar fetch logic in tests/unit/test_market.py — test `fetch_bars` with mocked Alpaca client returning sample bars, verify INSERT OR IGNORE dedup, verify incremental date calculation, verify error handling per ticker (continues on failure)
- [X] T010 [US1] Add integration test for bar fetch in tests/integration/test_market_data.py — test fetching daily bars for AAPL (small date range), verify rows in DB, verify incremental re-fetch inserts no duplicates

**Checkpoint**: User Story 1 is fully functional and testable — `market fetch` works end-to-end

---

## Phase 4: User Story 2 — Real-Time Price Snapshot (Priority: P2)

**Goal**: Operator can get a live price snapshot (last price, bid/ask, volume) for any ticker.

**Independent Test**: Run `market snapshot AAPL` and verify output includes price, bid, ask, volume.

### Implementation for User Story 2

- [X] T011 [P] [US2] Implement snapshot query logic in src/finance_agent/market/snapshot.py — function `get_snapshots(client, tickers)` calling `StockSnapshotRequest` and returning structured dict with last_price, bid, ask, volume, vwap, market status
- [X] T012 [US2] Implement `market snapshot` CLI subcommand in src/finance_agent/cli.py — add `snapshot` subcommand accepting positional TICKER args; call `get_snapshots`, print formatted output per contracts/cli.md
- [X] T013 [P] [US2] Add unit tests for snapshot logic in tests/unit/test_market.py — test `get_snapshots` with mocked Alpaca client, verify output structure, verify error handling for invalid ticker
- [X] T014 [US2] Add integration test for snapshot in tests/integration/test_market_data.py — test snapshot for AAPL, verify response has price > 0

**Checkpoint**: User Stories 1 AND 2 both work independently

---

## Phase 5: User Story 3 — Compute Technical Indicators (Priority: P3)

**Goal**: System computes SMA-20, SMA-50, RSI-14, VWAP from stored daily bars and persists latest values per ticker.

**Independent Test**: Fetch bars for a ticker, run `market indicators`, verify computed values match manual calculation.

### Implementation for User Story 3

- [X] T015 [US3] Implement indicator computation and persistence in src/finance_agent/market/indicators.py — pure Python functions: `compute_sma(bars, period)`, `compute_rsi(bars, period)`, `compute_vwap(bars)`; orchestrator function `compute_and_persist_indicators(conn, ticker, company_id, timeframe)` that queries bars from DB, computes all indicators, upserts into technical_indicator table; skip indicators without enough bars (with message)
- [X] T016 [US3] Implement `market indicators` CLI subcommand in src/finance_agent/cli.py — add `indicators` subcommand accepting `--ticker` flag; iterate watchlist, call `compute_and_persist_indicators`, print formatted output per contracts/cli.md
- [X] T017 [US3] Wire indicator computation into `market fetch` — after bars are stored for each ticker in T008, call `compute_and_persist_indicators` automatically and include indicator values in fetch summary output
- [X] T018 [P] [US3] Add unit tests for indicator computation in tests/unit/test_market.py — test `compute_sma` against known values (hand-calculated), test `compute_rsi` against known values, test `compute_vwap`, test skip behavior when insufficient bars, test upsert (overwrite stale indicator)
- [X] T019 [US3] Add integration test for indicators in tests/integration/test_market_data.py — fetch real bars for AAPL, compute indicators, verify SMA/RSI/VWAP are within reasonable ranges

**Checkpoint**: User Stories 1, 2, AND 3 all work — `market fetch` now auto-computes indicators

---

## Phase 6: User Story 4 — View Market Data Status (Priority: P3)

**Goal**: Operator can see a summary of stored data — tickers, date ranges, bar counts, last fetch, and latest indicators.

**Independent Test**: Fetch bars for several tickers, run `market status`, verify summary matches.

### Implementation for User Story 4

- [X] T020 [US4] Implement status query logic in src/finance_agent/market/bars.py — function `get_market_data_status(conn)` returning per-ticker/timeframe summary (bar count, min/max date, last fetch time) and `get_latest_indicators(conn)` returning latest indicator values per ticker
- [X] T021 [US4] Implement `market status` CLI subcommand in src/finance_agent/cli.py — add `status` subcommand (no args); call status query functions, print formatted table output per contracts/cli.md; handle empty state with helpful message
- [X] T022 [P] [US4] Add unit test for status display in tests/unit/test_market.py — test `get_market_data_status` with pre-populated DB, test empty DB case
- [X] T023 [US4] Add integration test for status in tests/integration/test_market_data.py — fetch bars, run status, verify output includes correct ticker and bar counts

**Checkpoint**: All 4 user stories work — complete market data feature

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Audit logging, health check, linting, and documentation

- [X] T024 [P] Add market data fetch audit logging — ensure all fetch operations write to `market_data_fetch` table with started_at, completed_at, status, bars_fetched, from_date, to_date, error_message; verify via unit test
- [X] T025 [P] Add market data connectivity check to `finance-agent health` command in src/finance_agent/cli.py — check Alpaca data API reachability, print "Market Data API: OK (IEX feed)" or error
- [X] T026 Run `uv run ruff check src/finance_agent/market/ tests/unit/test_market.py tests/integration/test_market_data.py` and fix any linting errors
- [X] T027 Run `uv run pytest tests/unit/test_market.py -v` and verify all unit tests pass
- [X] T028 Run quickstart.md validation — execute each command from quickstart.md and verify output matches expected format

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001-T003 complete) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — MVP, must complete first
- **US2 (Phase 4)**: Depends on Foundational — can run in parallel with US1 (separate files)
- **US3 (Phase 5)**: Depends on US1 (needs stored bars for computation, wires into fetch)
- **US4 (Phase 6)**: Depends on US1 (needs stored bars for status queries)
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 2 — no dependencies on other stories
- **User Story 2 (P2)**: Can start after Phase 2 — independent of US1 (uses client.py only)
- **User Story 3 (P3)**: Depends on US1 — needs stored bars + wires into fetch command
- **User Story 4 (P3)**: Depends on US1 — needs stored bars for status queries; depends on US3 for indicator status display

### Within Each User Story

- Implementation before tests (tests verify implementation)
- Core logic (bars.py/indicators.py/snapshot.py) before CLI integration
- CLI integration before audit/logging concerns

### Parallel Opportunities

- T001, T002, T003 can all run in parallel (different files)
- T004, T005 can run in parallel (different test files)
- US1 and US2 can run in parallel (bars.py vs snapshot.py, no shared state)
- T011 and T013 can run in parallel with US1 tasks (snapshot is independent)
- T018, T022 can run in parallel with other unit tests (different test classes)
- T024, T025 can run in parallel (audit vs health check)

---

## Parallel Example: User Story 1 + User Story 2

```bash
# After Phase 2 is complete, US1 and US2 can start in parallel:

# US1 (bars.py + fetch CLI):
Task: T007 "Implement bar fetch logic in src/finance_agent/market/bars.py"
Task: T008 "Implement market fetch CLI in src/finance_agent/cli.py" (after T007)

# US2 (snapshot.py + snapshot CLI) — in parallel with US1:
Task: T011 "Implement snapshot logic in src/finance_agent/market/snapshot.py"
Task: T012 "Implement market snapshot CLI in src/finance_agent/cli.py" (after T011)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T006)
3. Complete Phase 3: User Story 1 (T007-T010)
4. **STOP and VALIDATE**: `uv run finance-agent market fetch --ticker AAPL` works
5. Bars stored, incremental updates work, audit trail populated

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (bars) → `market fetch` works → MVP!
3. Add US2 (snapshots) → `market snapshot` works
4. Add US3 (indicators) → `market indicators` works, auto-computed on fetch
5. Add US4 (status) → `market status` shows complete data summary
6. Polish → health check, linting, final validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- All indicator math is pure Python (no numpy/pandas) per research.md Decision 6
- Rate limiter in client.py at 180 req/min (90% of 200 limit) per research.md Decision 4
- Split-adjusted prices via `Adjustment.SPLIT` per research.md Decision 2
- Migration SQL is fully specified in data-model.md — copy verbatim for T002
