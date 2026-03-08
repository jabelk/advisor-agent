# Tasks: Pharma News Dip Pattern

**Input**: Design documents from `/specs/013-pharma-news-dip/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Create new module files for event detection and regime analysis

- [x] T001 [P] Create src/finance_agent/patterns/event_detection.py with module docstring, imports (models, logging), and empty function stubs for detect_spike_events(), parse_manual_events(), parse_events_file()
- [x] T002 [P] Create src/finance_agent/patterns/regime.py with module docstring, imports (models, logging), and empty function stub for detect_time_based_regimes()

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Pydantic models used by all user stories

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Add DetectedEvent, ManualEvent, EventDetectionConfig, and RegimeConfig Pydantic models to src/finance_agent/patterns/models.py — fields per data-model.md: DetectedEvent (date, ticker, price_change_pct, volume_multiple, close_price, high_price, event_label, source), ManualEvent (date, label), EventDetectionConfig (spike_threshold_pct=5.0, volume_multiple_min=1.5, volume_lookback_days=20, cooldown_mode="trade_lifecycle", manual_events=None), RegimeConfig (window_trading_days=63, strong_threshold=0.60, weak_threshold=0.40, min_trades_for_regime=10, min_trades_per_window=3)

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Backtest News-Driven Dip Pattern (Priority: P1) MVP

**Goal**: Jordan describes the pharma dip pattern, backtests it against historical data using automatic event detection or manual event dates, and gets a trade-by-trade report with aggregate statistics.

**Independent Test**: Describe the pattern → backtest ABBV for 2024-2025 → verify events detected, trades simulated, win/loss reported.

### Implementation for User Story 1

- [x] T004 [US1] Implement detect_spike_events() in src/finance_agent/patterns/event_detection.py — scan list of bar dicts for single-day price_change_pct >= threshold AND volume >= volume_multiple_min * 20-day average volume. Enforce per-ticker cooldown: skip new spikes while a trade is active or entry window is open. Return list[DetectedEvent]. Handle edge cases: consecutive spikes, halted stocks (use first available bar), full reversal detection (FR-001, FR-009, FR-011)
- [x] T005 [US1] Implement parse_manual_events() and parse_events_file() in src/finance_agent/patterns/event_detection.py — parse_manual_events(events_str) splits comma-separated "YYYY-MM-DD" dates into list[ManualEvent]; parse_events_file(path) reads file line-by-line skipping # comments and blank lines, splits each line on first comma for date + optional label. Return list[ManualEvent]. Validate date format, raise ValueError for invalid dates (FR-002)
- [x] T006 [P] [US1] Add _apply_news_dip_defaults() post-processor in src/finance_agent/patterns/parser.py — detect pharma dip patterns by: trigger_type == QUALITATIVE AND sector_filter contains "healthcare" or "pharma" AND action_type == BUY_CALL. Apply defaults: ensure trigger_conditions include price_change_pct >= 5.0 and volume_spike >= 1.5, entry_signal pullback_pct 2.0 with window_days 2. Call from parse_pattern_description() after _apply_covered_call_defaults(). Log applied defaults
- [x] T007 [US1] Implement run_news_dip_backtest() in src/finance_agent/patterns/backtest.py — accept pattern_id, rule_set, bars (list[dict]), ticker, start_date, end_date, event_config (EventDetectionConfig). If manual_events provided: convert to DetectedEvent list using bar data for prices. Otherwise: call detect_spike_events(). For each detected event: find dip entry within window using existing _find_entry() logic, simulate trade using _execute_simulated_trade(), track no-entry events with reason. Return BacktestReport with trades, trigger_count (events), no_entry_events metadata (FR-003, FR-004, FR-005, FR-011)
- [x] T008 [P] [US1] Add --events, --events-file, --spike-threshold, --volume-multiple flags to backtest subparser in src/finance_agent/cli.py — events: str (comma-separated dates), events-file: str (file path), spike-threshold: float (default None = use pattern), volume-multiple: float (default None = use pattern). Validate: --events and --events-file are mutually exclusive (FR-002, FR-012)
- [x] T009 [US1] Add _run_news_dip_backtest() function and routing in src/finance_agent/cli.py — in _pattern_backtest(), detect qualitative trigger_type and route to _run_news_dip_backtest(). Build EventDetectionConfig from CLI args (--events/--events-file/--spike-threshold/--volume-multiple) with fallbacks to pattern defaults. Call run_news_dip_backtest(), save results via save_backtest_result(), display report per contracts/cli.md format: events detected, spike/volume config, aggregate stats (win rate, avg return, total return, max drawdown, sharpe), trade log, no-entry events table
- [x] T010 [P] [US1] Add unit tests for event detection in tests/unit/test_event_detection.py — test detect_spike_events with synthetic bars: basic spike detection, volume filter, cooldown enforcement, consecutive spikes suppressed, no events found. Test parse_manual_events: valid dates, invalid format raises ValueError, empty string. Test parse_events_file: valid file, comments/blanks skipped, labels parsed, file not found raises error

**Checkpoint**: User Story 1 complete — can describe pharma dip pattern and backtest with event detection or manual dates

---

## Phase 4: User Story 2 — Regime Analysis (Priority: P2)

**Goal**: Backtest results include regime analysis showing when the pattern worked (strong), weakened (weak), or stopped working (breakdown), using time-based rolling windows with 60/40 thresholds.

**Independent Test**: Backtest over 2+ years → verify regime periods appear in output with correct labels, date ranges, and trade counts.

### Implementation for User Story 2

- [x] T011 [US2] Implement detect_time_based_regimes() in src/finance_agent/patterns/regime.py — accept trades (list[BacktestTrade]) and config (RegimeConfig). Use rolling window of config.window_trading_days (default 63). For each window: calculate win rate from trades within date range, label as strong (>= 0.60), weak (0.40–0.59), or breakdown (< 0.40). Skip windows with < min_trades_per_window trades. Merge adjacent windows with same label into contiguous RegimePeriod objects. Guard: return empty list if total trades < min_trades_for_regime. Return list[RegimePeriod] (FR-006, FR-007)
- [x] T012 [US2] Integrate regime analysis into run_news_dip_backtest() in src/finance_agent/patterns/backtest.py — after trade simulation, call detect_time_based_regimes(trades, RegimeConfig()) and populate report.regimes. Set report.sample_size_warning if trades < 5
- [x] T013 [US2] Add regime analysis display to _run_news_dip_backtest() output in src/finance_agent/cli.py — display REGIME ANALYSIS section per contracts/cli.md: table with Period/Label/Trades/Win Rate/Avg Return columns. Show warning if < 10 trades ("regime analysis skipped"). Show warning if < 5 trades ("results may not be statistically meaningful")
- [x] T014 [P] [US2] Add unit tests for regime analysis in tests/unit/test_regime.py — test detect_time_based_regimes with synthetic trades: strong-only, weak-only, breakdown-only, mixed regimes, adjacent merge, min-trades guard (empty list returned), window with < min_trades_per_window skipped. Test threshold boundaries: exactly 60% = strong, exactly 40% = weak, 39.9% = breakdown

**Checkpoint**: User Stories 1 AND 2 complete — backtest produces trade results with regime analysis

---

## Phase 5: User Story 3 — Paper Trade with News Monitoring (Priority: P3)

**Goal**: Jordan paper trades the pharma dip pattern with real-time spike detection, human confirmation for qualitative triggers, and full position lifecycle tracking.

**Independent Test**: Start paper trading → system detects spike → prompts for confirmation → monitors dip entry → tracks position.

### Implementation for User Story 3

- [x] T015 [US3] Implement NewsPatternMonitor class in src/finance_agent/patterns/executor.py — extend PatternMonitor. Override _evaluate_trigger(ticker) to: fetch recent bars, calculate single-day price change and volume multiple, check spike threshold and volume threshold from rule_set trigger conditions. Override trigger flow to display confirmation prompt per contracts/cli.md format (price change, volume multiple, date), accept y/n/skip input. On 'y': proceed to entry signal monitoring. On 'n': log as false positive, resume. On 'skip': continue monitoring (FR-008)
- [x] T016 [US3] Block --auto-approve for qualitative patterns in src/finance_agent/cli.py — in _pattern_paper_trade(), after loading pattern, check if rule_set.trigger_type == QUALITATIVE and args.auto_approve is True. If so: print error "Error: --auto-approve is not allowed for qualitative patterns (safety requirement). Qualitative triggers require human confirmation." and return (FR-008)
- [x] T017 [US3] Route qualitative patterns to NewsPatternMonitor in src/finance_agent/cli.py — in _pattern_paper_trade(), detect trigger_type == QUALITATIVE: instantiate NewsPatternMonitor instead of PatternMonitor. Pass same arguments (conn, audit, settings, pattern_id, tickers, auto_approve=False, poll_interval)

**Checkpoint**: All user stories complete — describe, backtest, regime analysis, and paper trading all functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Comparison enhancements, integration tests, edge case verification

- [x] T018 Extend _pattern_compare() in src/finance_agent/cli.py — for qualitative + buy_call patterns: add Events, Trades, Regimes columns per contracts/cli.md. Add regime overlay table showing aligned time periods across compared patterns (FR-010)
- [x] T019 [P] Add integration test for end-to-end news dip CLI flow in tests/integration/test_news_dip_cli.py — create pattern with qualitative trigger, run backtest with synthetic bar data via manual --events, verify output contains expected sections (events detected, aggregate stats, trade log, no-entry events). Verify --auto-approve blocked for qualitative patterns
- [x] T020 Verify edge cases per spec in src/finance_agent/patterns/event_detection.py and src/finance_agent/patterns/backtest.py — consecutive spike cooldown, overnight gap handling (use open price), full reversal detection, zero events message, halted stock handling. Add any missing logic and corresponding unit tests
- [x] T021 Run quickstart.md scenarios with synthetic data and verify output matches contracts/cli.md format — test all 4 quickstart scenarios: describe+backtest, regime analysis, paper trade confirmation flow, compare variants

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - US1 (Phase 3): Can start after Phase 2
  - US2 (Phase 4): Depends on US1 (T007 run_news_dip_backtest must exist to integrate regime analysis)
  - US3 (Phase 5): Can start after Phase 2 (independent of US1/US2)
- **Polish (Phase 6)**: Depends on US1 and US2 being complete (T018 compare needs backtest results; T019 needs full flow)

### User Story Dependencies

- **US1 (P1)**: After Phase 2. No dependencies on other stories.
- **US2 (P2)**: After US1 (integrates regime analysis into the backtest function from US1).
- **US3 (P3)**: After Phase 2. Independent of US1/US2 — uses existing PatternMonitor infrastructure.

### Within Each User Story

- Models (Phase 2) before services (event detection, regime)
- Event detection (T004, T005) before backtest integration (T007)
- Backtest function (T007) before CLI routing (T009)
- CLI flags (T008) before CLI routing (T009) — same file, sequential
- Regime module (T011) before backtest integration (T012)
- NewsPatternMonitor (T015) before CLI routing (T016, T017)

### Parallel Opportunities

- T001 + T002: Setup — different new files
- T006 + T004/T005: Parser defaults + event detection — different files
- T008 + T007: CLI flags + backtest function — different files
- T010 + T009: Tests + CLI routing — different files
- T014 + T011: Regime tests + regime implementation — different files
- T019 + T018: Integration test + compare extension — different files
- US3 (T015-T017) can run in parallel with US2 (T011-T014) since they're independent

---

## Parallel Example: User Story 1

```bash
# These can run in parallel (different files):
T004: detect_spike_events() in event_detection.py
T006: _apply_news_dip_defaults() in parser.py

# These can run in parallel (different files):
T007: run_news_dip_backtest() in backtest.py
T008: CLI flags in cli.py

# Then sequentially:
T009: CLI routing in cli.py (depends on T007 + T008)
```

## Parallel Example: US2 + US3

```bash
# These can run in parallel (independent user stories):
T011: detect_time_based_regimes() in regime.py
T015: NewsPatternMonitor in executor.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational models (T003)
3. Complete Phase 3: US1 — event detection + backtest + CLI (T004-T010)
4. **STOP and VALIDATE**: Describe pharma dip pattern → backtest with synthetic data → verify results
5. This delivers the core value: "does this pattern actually work?"

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (backtest) → Test independently → MVP! Jordan can test his pharma dip hypothesis
3. Add US2 (regime analysis) → Test independently → Jordan sees WHEN the pattern worked/broke
4. Add US3 (paper trading) → Test independently → Jordan can validate in real-time
5. Polish → Compare variants, edge cases, integration tests

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- No new database tables — all new entities are in-memory Pydantic models
- Existing infrastructure reused: _find_entry(), _execute_simulated_trade(), estimate_call_premium(), fetch_and_cache_bars(), PatternMonitor, save_backtest_result()
- Parser post-processing follows same pattern as _apply_covered_call_defaults()
