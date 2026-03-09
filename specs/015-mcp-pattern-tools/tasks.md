# Tasks: MCP Pattern Lab Tools

**Input**: Design documents from `/specs/015-mcp-pattern-tools/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/mcp-tools.md, quickstart.md

**Tests**: Not explicitly requested — test tasks included in Polish phase.

**Organization**: Tasks grouped by user story. All 3 tools are added to the same file (`research_server.py`), so tasks within a story are sequential.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add read-write DB helper needed by backtest/A/B tools

- [X] T001 Add `_get_readwrite_conn()` helper function to src/finance_agent/mcp/research_server.py alongside existing `_get_readonly_conn()` — same row_factory and busy_timeout but without `?mode=ro` flag
- [X] T002 Add `_get_alpaca_keys()` helper to src/finance_agent/mcp/research_server.py that reads ALPACA_API_KEY_PAPER and ALPACA_SECRET_KEY_PAPER from environment, returns tuple or raises structured error dict

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational tasks — all shared infrastructure is in Phase 1

**Checkpoint**: Setup helpers ready — user story implementation can begin

---

## Phase 3: User Story 1 — Multi-Ticker Backtest Tool (Priority: P1) 🎯 MVP

**Goal**: Run multi-ticker backtests from Claude Desktop without switching to the terminal

**Independent Test**: In Claude Desktop, ask "Backtest pattern 1 across ABBV, MRNA, PFE" and verify structured results returned with per-ticker breakdown

### Implementation for User Story 1

- [X] T003 [US1] Implement `run_backtest` MCP tool function in src/finance_agent/mcp/research_server.py: accept pattern_id (int), tickers (str, optional), start_date (str, optional), end_date (str, optional); validate pattern exists; fetch bars via fetch_and_cache_bars; route to appropriate backtest engine (qualitative → run_multi_ticker_news_dip_backtest, quantitative → run_backtest); return AggregatedBacktestReport.model_dump() or BacktestReport.model_dump() with pattern_name added
- [X] T004 [US1] Add error handling for run_backtest in src/finance_agent/mcp/research_server.py: pattern not found, no tickers (fall back to watchlist), no price data available, missing Alpaca keys — all return {"error": "..."} dicts
- [X] T005 [US1] Add default date range logic in run_backtest in src/finance_agent/mcp/research_server.py: start_date defaults to 1 year ago, end_date defaults to today (matching CLI behavior)

**Checkpoint**: Multi-ticker backtest works from Claude Desktop

---

## Phase 4: User Story 2 — A/B Test Tool (Priority: P2)

**Goal**: Compare pattern variants with statistical significance from Claude Desktop

**Independent Test**: Ask Claude Desktop "Compare patterns 1 and 2 on ABBV and MRNA" and verify variant metrics, p-values, and best variant returned

### Implementation for User Story 2

- [X] T006 [US2] Implement `run_ab_test` MCP tool function in src/finance_agent/mcp/research_server.py: accept pattern_ids (str, comma-separated), tickers (str), start_date (str, optional), end_date (str, optional); parse pattern_ids to list[int]; validate each pattern exists and is confirmed; build event_configs per pattern; call stats.run_ab_test; return simplified result dict with variant summaries, comparisons, best_variant_id, sample_size_warnings
- [X] T007 [US2] Add error handling for run_ab_test in src/finance_agent/mcp/research_server.py: fewer than 2 IDs, pattern not found, pattern in draft, no tickers, missing Alpaca keys

**Checkpoint**: A/B testing works from Claude Desktop

---

## Phase 5: User Story 3 — Export Tool (Priority: P3)

**Goal**: Export backtest results to markdown from Claude Desktop

**Independent Test**: Ask Claude Desktop "Export backtest results for pattern 1" and verify file path returned

### Implementation for User Story 3

- [X] T008 [US3] Implement `export_backtest` MCP tool function in src/finance_agent/mcp/research_server.py: accept pattern_id (int), backtest_id (int, optional), output_dir (str, optional); validate pattern exists; fetch backtest result (most recent or specific ID); call export_backtest_markdown; write file via generate_export_path; return {"file_path": ..., "pattern_id": ..., "backtest_id": ...}
- [X] T009 [US3] Add error handling for export_backtest in src/finance_agent/mcp/research_server.py: pattern not found, no backtest results, invalid backtest_id

**Checkpoint**: Export works from Claude Desktop

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Tests and validation

- [X] T010 [P] Write unit tests for MCP pattern tools in tests/unit/test_mcp_pattern_tools.py: test run_backtest with mocked bars data, test run_ab_test error cases (< 2 IDs, draft pattern), test export_backtest with mocked DB, test _get_alpaca_keys missing keys error
- [X] T011 Verify existing tests still pass (271+ tests from previous features)
- [ ] T012 Run quickstart.md scenarios against Claude Desktop to validate end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **US1 (Phase 3)**: Depends on Phase 1 (DB helper, Alpaca keys helper)
- **US2 (Phase 4)**: Depends on Phase 1. Independent of US1 (uses stats module directly)
- **US3 (Phase 5)**: Depends on Phase 1 (DB helper only). Independent of US1/US2
- **Polish (Phase 6)**: Depends on all user stories being complete

### Within Each User Story

- Implementation before error handling
- All tasks in same file (research_server.py) — sequential within story

### Parallel Opportunities

- **Phase 1**: T001 and T002 could be parallel but same file — recommend sequential
- **Phases 3-5**: US1, US2, US3 could theoretically be parallel but all modify the same file — recommend sequential in priority order
- **Phase 6**: T010 is independent (different file)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (DB helper, Alpaca keys helper)
2. Complete Phase 3: User Story 1 (run_backtest tool)
3. **STOP and VALIDATE**: Test in Claude Desktop
4. Proceed to US2/US3

### Incremental Delivery

1. Setup → Helpers ready
2. Add US1 (run_backtest) → Test in Claude Desktop
3. Add US2 (run_ab_test) → Test in Claude Desktop
4. Add US3 (export_backtest) → Test in Claude Desktop
5. Polish → Unit tests, regression check

---

## Notes

- All 3 tools added to existing research_server.py — no new files except test file
- No new Pydantic models — reuse from 014
- run_backtest and run_ab_test need read-write DB (market data cache writes)
- export_backtest needs read-only DB + filesystem write
- FastMCP handles serialization of returned dicts automatically
