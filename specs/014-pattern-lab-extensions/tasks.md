# Tasks: Pattern Lab Extensions

**Input**: Design documents from `/specs/014-pattern-lab-extensions/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: Not explicitly requested — test tasks included only in Polish phase for integration validation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add scipy dependency and create new module stubs

- [x] T001 Add scipy to project dependencies in pyproject.toml
- [x] T002 [P] Create stats module stub at src/finance_agent/patterns/stats.py
- [x] T003 [P] Create export module stub at src/finance_agent/patterns/export.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add new Pydantic models that all user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Add TickerBreakdown model to src/finance_agent/patterns/models.py (fields: ticker, events_detected, trades_entered, win_count, win_rate, avg_return_pct, total_return_pct)
- [x] T005 Add AggregatedBacktestReport model to src/finance_agent/patterns/models.py (fields: pattern_id, date_range_start, date_range_end, tickers, ticker_breakdowns, combined_report, no_entry_events)
- [x] T006 Add PairwiseComparison model to src/finance_agent/patterns/models.py (fields: variant_a_id, variant_b_id, win_rate_p_value, win_rate_significant, avg_return_p_value, avg_return_significant, confidence_level)
- [x] T007 Add ABTestResult model to src/finance_agent/patterns/models.py (fields: pattern_ids, tickers, date_range_start, date_range_end, variant_reports, comparisons, best_variant_id, best_is_significant, sample_size_warnings)

**Checkpoint**: All new Pydantic models defined — user story implementation can begin

---

## Phase 3: User Story 1 — Multi-Ticker Aggregation (Priority: P1) 🎯 MVP

**Goal**: Backtest a pattern across a basket of stocks and see combined stats with per-ticker breakdown

**Independent Test**: Run `finance-agent pattern backtest <id> --tickers ABBV,MRNA,PFE --start 2024-01-01 --end 2025-12-31` and verify combined report with per-ticker breakdown table plus aggregate metrics

### Implementation for User Story 1

- [x] T008 [US1] Update run_news_dip_backtest in src/finance_agent/patterns/backtest.py to accept list of tickers, iterate per-ticker, build TickerBreakdown objects, pool trades into combined BacktestReport, and return AggregatedBacktestReport
- [x] T009 [US1] Handle edge cases in multi-ticker aggregation in src/finance_agent/patterns/backtest.py: tickers with zero events (zero-row in breakdown), tickers with no price data (excluded from aggregate), all-zero case (return suggestion message)
- [x] T010 [US1] Update backtest subcommand display in src/finance_agent/cli.py to detect multi-ticker results and render per-ticker breakdown table above combined aggregate (single-ticker output unchanged)
- [x] T011 [US1] Display no-entry events with ticker column in multi-ticker format in src/finance_agent/cli.py
- [x] T012 [US1] Add sample size warning display when total trades < 30 across all tickers in src/finance_agent/cli.py

**Checkpoint**: Multi-ticker backtesting works end-to-end — per-ticker breakdown + aggregate + regime analysis + no-entry events

---

## Phase 4: User Story 2 — A/B Testing Framework (Priority: P2)

**Goal**: Compare pattern variants with statistical significance testing to know if differences are real or noise

**Independent Test**: Run `finance-agent pattern ab-test <id1> <id2> --tickers ABBV,MRNA --start 2024-01-01 --end 2025-12-31` and verify statistical comparison with p-values and significance indicators

### Implementation for User Story 2

- [x] T013 [P] [US2] Implement fisher_exact_test(wins_a, losses_a, wins_b, losses_b) in src/finance_agent/patterns/stats.py using scipy.stats.fisher_exact, returning p-value
- [x] T014 [P] [US2] Implement welch_ttest(returns_a, returns_b) in src/finance_agent/patterns/stats.py using scipy.stats.ttest_ind with equal_var=False, returning p-value
- [x] T015 [US2] Implement run_ab_test(pattern_ids, tickers, start, end) in src/finance_agent/patterns/stats.py: run multi-ticker backtest per variant, compute all pairwise comparisons (PairwiseComparison), determine best variant, build ABTestResult
- [x] T016 [US2] Add significance notation helper in src/finance_agent/patterns/stats.py: format p-value as (NS) for p>=0.05, (*) for p<0.05, (**) for p<0.01
- [x] T017 [US2] Add sample size warning generation in src/finance_agent/patterns/stats.py: warn when variant has <10 trades, warn when trade counts differ significantly across variants
- [x] T018 [US2] Add `pattern ab-test` subcommand to src/finance_agent/cli.py: accept 2+ pattern IDs, --tickers (required), --start, --end; validate inputs (min 2 IDs, patterns exist and confirmed, tickers required)
- [x] T019 [US2] Implement A/B test display formatting in src/finance_agent/cli.py: variant metrics table, statistical significance table with pairwise comparisons, result section with best variant and significance statement
- [x] T020 [US2] Add error handling for A/B test edge cases in src/finance_agent/cli.py: fewer than 2 IDs, pattern not found, pattern in draft status, no tickers

**Checkpoint**: A/B testing works end-to-end — variant comparison with Fisher's exact + Welch's t-test + significance indicators + warnings

---

## Phase 5: User Story 3 — Export & Reporting (Priority: P3)

**Goal**: Save backtest and A/B test results as markdown reports for offline review and sharing

**Independent Test**: Run `finance-agent pattern export <id> --format markdown` and verify a well-formatted markdown file is created with all backtest sections

### Implementation for User Story 3

- [x] T021 [US3] Implement backtest markdown generation in src/finance_agent/patterns/export.py: render pattern description, config, aggregate results table, per-ticker breakdown (if multi-ticker), regime analysis table, trade log table, no-entry events table
- [x] T022 [US3] Implement A/B test markdown generation in src/finance_agent/patterns/export.py: render variant metrics table, statistical significance table, result/recommendation section
- [x] T023 [US3] Implement file naming and overwrite protection in src/finance_agent/patterns/export.py: default filename pattern-{id}-{type}-{date}.md, numeric suffix append when file exists (-1, -2, etc.), custom --output path support
- [x] T024 [US3] Add `pattern export` subcommand to src/finance_agent/cli.py: accept pattern_id, --format (default markdown), --output (optional path), --backtest-id (optional specific run); validate inputs and fetch results
- [x] T025 [US3] Add error handling for export edge cases in src/finance_agent/cli.py: no backtest results, invalid pattern ID, invalid backtest ID, unsupported format

**Checkpoint**: Export works end-to-end — markdown files generated with full backtest/A/B content, overwrite protection, custom paths

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Integration tests, edge case validation, quickstart scenario verification

- [x] T026 [P] Write unit tests for stats module in tests/unit/test_stats.py: Fisher's exact test edge cases (zero wins, all wins, equal rates), Welch's t-test edge cases (identical returns, single trade), significance notation, sample size warnings
- [x] T027 [P] Write unit tests for export module in tests/unit/test_export.py: backtest markdown structure, A/B test markdown structure, filename generation, overwrite suffix logic
- [x] T028 Write integration test for multi-ticker + A/B test + export flow in tests/integration/test_ab_test_cli.py: create variants, run A/B test, export results, verify file contents
- [x] T029 Run quickstart.md scenarios (multi-ticker backtest, A/B test, export) to validate end-to-end behavior
- [x] T030 Verify existing tests still pass (216+ tests from previous features)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (scipy installed) — BLOCKS all user stories
- **US1 Multi-Ticker (Phase 3)**: Depends on Phase 2 (models defined)
- **US2 A/B Testing (Phase 4)**: Depends on Phase 2 (models defined). Uses multi-ticker backtest from US1 internally but can be implemented independently (T015 calls backtest directly)
- **US3 Export (Phase 5)**: Depends on Phase 2 (models defined). Benefits from US1/US2 being done (more data to export) but can be implemented against model interfaces
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependencies on other stories
- **US2 (P2)**: Can start after Phase 2 — calls backtest internally (does not require US1 CLI changes, only the backtest.py aggregation from T008)
- **US3 (P3)**: Can start after Phase 2 — generates markdown from model objects (does not require CLI changes from US1/US2)

### Within Each User Story

- Models (Phase 2) before services/logic
- Core logic before CLI integration
- CLI integration before error handling

### Parallel Opportunities

- **Phase 1**: T002 and T003 can run in parallel (different files)
- **Phase 2**: T004-T007 are sequential (same file: models.py)
- **Phase 4**: T013 and T014 can run in parallel (independent functions in stats.py)
- **Phase 5**: T021 and T022 can run in parallel (independent functions in export.py, but same file — recommend sequential)
- **Phase 6**: T026 and T027 can run in parallel (different test files)

---

## Parallel Example: User Story 2

```bash
# Launch Fisher's and Welch's implementations in parallel (independent functions):
Task T013: "Implement fisher_exact_test in src/finance_agent/patterns/stats.py"
Task T014: "Implement welch_ttest in src/finance_agent/patterns/stats.py"

# Then sequential: T015 (uses T013+T014), T016, T017, T018, T019, T020
```

## Parallel Example: Polish Phase

```bash
# Launch unit test files in parallel (different files):
Task T026: "Unit tests for stats in tests/unit/test_stats.py"
Task T027: "Unit tests for export in tests/unit/test_export.py"

# Then sequential: T028 (integration), T029 (quickstart), T030 (regression)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (scipy, module stubs)
2. Complete Phase 2: Foundational (all 4 Pydantic models)
3. Complete Phase 3: User Story 1 (multi-ticker aggregation)
4. **STOP and VALIDATE**: Test multi-ticker backtest independently
5. Proceed to US2/US3 if MVP works

### Incremental Delivery

1. Setup + Foundational → Models ready
2. Add US1 (Multi-Ticker) → Test independently → Combined backtest reports working
3. Add US2 (A/B Testing) → Test independently → Statistical comparisons working
4. Add US3 (Export) → Test independently → Markdown reports working
5. Polish → Integration tests, quickstart validation, regression check
6. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- scipy is already transitively available but needs explicit declaration in pyproject.toml
- All new models are in-memory Pydantic models — no DB migrations needed
- Single-ticker backtest output must remain unchanged (backward compatible)
- US2 (A/B testing) internally uses multi-ticker backtest logic from T008 — if implementing US2 before US1 CLI is done, the backtest.py changes from T008 must be complete
