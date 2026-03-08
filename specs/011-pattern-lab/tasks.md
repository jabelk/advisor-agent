# Tasks: Pattern Lab

**Input**: Design documents from `/specs/011-pattern-lab/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md

**Tests**: Not explicitly requested in spec. Test tasks omitted.

**Organization**: Tasks grouped by user story for independent implementation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the Pattern Lab module structure and database schema

- [x] T001 Create patterns module directory and `__init__.py` at `src/finance_agent/patterns/__init__.py`
- [x] T002 Create database migration `migrations/007_pattern_lab.sql` with tables: `trading_pattern`, `backtest_result`, `backtest_trade`, `paper_trade`, `price_cache` per data-model.md
- [x] T003 [P] Create Pattern Lab Pydantic models (PatternDefinition, RuleSet, TriggerCondition, EntrySignal, TradeAction, ExitCriteria) in `src/finance_agent/patterns/models.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core storage and market data infrastructure that all user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Implement pattern CRUD operations (create, get, list, update_status, retire) in `src/finance_agent/patterns/storage.py` — uses SQLite via existing `db.get_connection()`
- [x] T005 Implement historical price data fetch and cache in `src/finance_agent/patterns/market_data.py` — fetch daily/hourly bars from Alpaca, store in `price_cache` table, skip fetching already-cached ranges
- [x] T006 [P] Add `pattern` command group stub to `src/finance_agent/cli.py` with subcommands: describe, backtest, paper-trade, list, show, compare, retire — initially just argument parsing, handlers call placeholder functions

**Checkpoint**: Foundation ready — pattern storage, market data fetching, and CLI scaffolding in place

---

## Phase 3: User Story 1 — Describe a Pattern in Plain Text (Priority: P1) MVP

**Goal**: Jordan describes a trading pattern in conversational English, the system parses it into structured rules via Claude, and presents them for confirmation/editing.

**Independent Test**: Run `finance-agent pattern describe "When pharma stocks spike on news, buy calls on the 2% dip within 2 days"` and verify structured rules are returned with trigger, entry, action, and exit components.

### Implementation for User Story 1

- [x] T007 [US1] Create pattern parsing prompt templates in `src/finance_agent/patterns/parser.py` — system prompt instructing Claude to extract trigger_type, trigger_conditions, entry_signal, action, exit_criteria from plain text; use Pydantic structured output (RuleSet model from T003)
- [x] T008 [US1] Implement `parse_pattern_description(description: str, api_key: str) -> RuleSet` in `src/finance_agent/patterns/parser.py` — calls Claude API with structured output, returns validated RuleSet; handles ambiguous input by returning clarifying questions instead of incomplete rules
- [x] T009 [US1] Implement `describe` CLI handler in `src/finance_agent/cli.py` — accepts plain-text description, calls parser, displays formatted rule summary (trigger, entry, action, exit), prompts for confirmation (Y/edit/cancel), on confirm calls `storage.create_pattern()` with status "draft"
- [x] T010 [US1] Add rule editing flow to `describe` CLI handler — when user selects "edit", display each rule component separately and allow inline modification, then re-display full summary for final confirmation
- [x] T011 [US1] Add sensible defaults for unspecified fields in `src/finance_agent/patterns/parser.py` — if exit criteria missing: default 20% profit target, 10% stop loss; if option params missing: ATM strike, 30-day expiration; log which defaults were applied

**Checkpoint**: User Story 1 complete — `finance-agent pattern describe` works end-to-end: plain text → Claude parsing → rule display → confirm → saved as draft pattern

---

## Phase 4: User Story 2 — Backtest a Pattern Against Historical Data (Priority: P1)

**Goal**: Run a confirmed pattern against historical price data and produce a performance report with regime detection — showing when the pattern worked and when it stopped.

**Independent Test**: Run `finance-agent pattern backtest 1 --start 2025-01-01 --end 2025-12-31` on a saved pattern and verify report shows trigger count, win rate, returns, drawdown, and regime analysis.

### Implementation for User Story 2

- [x] T012 [US2] Implement backtest simulation engine in `src/finance_agent/patterns/backtest.py` — `run_backtest(pattern, price_data, start, end)` iterates through price history, evaluates trigger conditions, simulates entry/exit, tracks each trade with return calculation
- [x] T013 [US2] Add options return estimation to `src/finance_agent/patterns/backtest.py` — for options-based actions, estimate P&L from underlying price movement using simplified Black-Scholes delta approximation; document that results are estimates, not exact options pricing
- [x] T014 [US2] Implement regime detection in `src/finance_agent/patterns/backtest.py` — `detect_regimes(trades)` uses rolling window analysis to identify periods where win rate or avg return shifted >50% from overall average; output includes period start/end dates and performance delta
- [x] T015 [US2] Implement backtest result persistence in `src/finance_agent/patterns/storage.py` — `save_backtest_result()` and `save_backtest_trades()` write to `backtest_result` and `backtest_trade` tables; update pattern status to "backtested"
- [x] T016 [US2] Implement sample size warning logic in `src/finance_agent/patterns/backtest.py` — warn if trigger count < 30 (minimum for statistical significance); include warning in report output and set `sample_size_warning` flag in backtest_result
- [x] T017 [US2] Implement `backtest` CLI handler in `src/finance_agent/cli.py` — accepts pattern_id, --start, --end, --tickers; calls `market_data.fetch_bars()` for required tickers/date range, then `backtest.run_backtest()`, then `storage.save_backtest_result()`; displays formatted report with trigger count, win/loss, avg return, max drawdown, regime periods
- [x] T018 [US2] Add "why did this pattern stop?" analysis to `src/finance_agent/patterns/backtest.py` — `explain_regime_change(regime, market_context)` cross-references regime change dates with available research signals (from existing `research_signal` table) and market conditions to suggest possible explanations via Claude

**Checkpoint**: User Story 2 complete — `finance-agent pattern backtest` produces a full performance report with regime detection. Combined with US1, the core describe → backtest loop works.

---

## Phase 5: User Story 3 — Paper Trade a Pattern in Real Time (Priority: P2)

**Goal**: Activate a backtested pattern for live paper trading — monitor market data for triggers, propose trades via Alpaca paper trading API, track performance.

**Independent Test**: Activate a pattern for paper trading, verify it monitors for triggers, proposes a trade when conditions are met, and executes through Alpaca paper trading after approval.

### Implementation for User Story 3

- [x] T019 [US3] Implement trigger monitor in `src/finance_agent/patterns/executor.py` — `PatternMonitor` class polls Alpaca market data at configurable interval (default 5 min during market hours), evaluates active patterns' trigger conditions against current price data
- [x] T020 [US3] Implement trade proposal logic in `src/finance_agent/patterns/executor.py` — when trigger fires, create a `paper_trade` record with status "proposed", calculate position size respecting `safety.get_risk_settings()` limits (max_position_pct, max_daily_loss_pct), check `safety.get_kill_switch()` before proposing
- [x] T021 [US3] Implement Alpaca paper trade execution in `src/finance_agent/patterns/executor.py` — `execute_paper_trade(trade_id)` submits order via alpaca-py SDK using paper trading credentials from `config.Settings`, updates paper_trade record with alpaca_order_id and status "executed", logs via AuditLogger
- [x] T022 [US3] Implement trade approval flow in `src/finance_agent/patterns/executor.py` — default: notify user and wait for approval; with `--auto-approve`: execute immediately; display proposed trade details (ticker, action, quantity, entry price, pattern name) before approval prompt
- [x] T023 [US3] Implement paper trade tracking in `src/finance_agent/patterns/executor.py` — monitor open positions for exit criteria (profit target, stop loss, time exit); when exit triggered, close position via Alpaca, update paper_trade with exit_price, pnl, closed_at
- [x] T024 [US3] Implement `paper-trade` CLI handler in `src/finance_agent/cli.py` — accepts pattern_id, --auto-approve, --tickers; validates pattern is in "backtested" status; updates pattern status to "paper_trading"; starts PatternMonitor polling loop; displays trigger and trade events in real-time
- [x] T025 [US3] Implement paper trade performance report in `src/finance_agent/patterns/storage.py` — `get_paper_trade_summary(pattern_id)` returns cumulative P&L, win rate, trade count, comparison to backtest expectations

**Checkpoint**: User Story 3 complete — patterns can be activated for live paper trading with safety controls and performance tracking

---

## Phase 6: User Story 4 — Manage and Compare Patterns (Priority: P3)

**Goal**: List all patterns, compare performance across patterns, and retire patterns that no longer work.

**Independent Test**: Create multiple patterns, backtest them, run `finance-agent pattern list` and `finance-agent pattern compare 1 2` and verify output.

### Implementation for User Story 4

- [x] T026 [P] [US4] Implement `list` CLI handler in `src/finance_agent/cli.py` — calls `storage.list_patterns()` with optional --status filter; displays table with ID, name, status, win rate (from latest backtest), paper P&L (if paper trading)
- [x] T027 [P] [US4] Implement `show` CLI handler in `src/finance_agent/cli.py` — calls `storage.get_pattern()` and related queries; displays full pattern details: rules, all backtest results, paper trade history
- [x] T028 [US4] Implement `compare` CLI handler in `src/finance_agent/cli.py` — accepts 2+ pattern IDs; fetches latest backtest results for each; displays side-by-side table of win rate, avg return, max drawdown, trigger count, regime sensitivity
- [x] T029 [US4] Implement `retire` CLI handler in `src/finance_agent/cli.py` — validates pattern exists and is active; if paper trading, closes open positions via Alpaca; updates status to "retired" with retired_at timestamp; logs via AuditLogger

**Checkpoint**: User Story 4 complete — full pattern lifecycle management in place

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: MCP integration, audit completeness, and quality improvements

- [x] T030 [P] Add Pattern Lab MCP tools to `src/finance_agent/mcp/research_server.py` — 4 read-only tools: `list_patterns`, `get_pattern_detail`, `get_backtest_results`, `get_paper_trade_summary` per contracts/cli.md
- [x] T031 [P] Add audit logging to all pattern operations in `src/finance_agent/patterns/storage.py` and `executor.py` — pattern_created, backtest_run, paper_trade_proposed, paper_trade_executed, paper_trade_closed, pattern_retired events via existing AuditLogger
- [x] T032 Validate end-to-end flow: describe → backtest → paper trade → list → compare → retire using CLI commands per quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — no other story dependencies
- **US2 (Phase 4)**: Depends on Phase 2 — needs patterns from US1 to be meaningful but can be developed independently with test fixtures
- **US3 (Phase 5)**: Depends on Phase 2 — benefits from US1+US2 but can be developed independently
- **US4 (Phase 6)**: Depends on Phase 2 — benefits from US1-US3 but can be developed independently
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (Describe)**: Independent — core input mechanism
- **US2 (Backtest)**: Logically follows US1 (needs a pattern to backtest) but can use test fixtures
- **US3 (Paper Trade)**: Logically follows US2 (should backtest before paper trading) but can use test fixtures
- **US4 (Manage)**: Independent — CRUD operations on any existing patterns

### Within Each User Story

- Storage operations before business logic
- Business logic before CLI handlers
- Core features before optional enhancements

### Parallel Opportunities

- T003 (models) can run in parallel with T002 (migration)
- T005 (market data) can run in parallel with T006 (CLI stub)
- T026, T027 (list/show handlers) can run in parallel
- T030, T031 (MCP tools, audit) can run in parallel

---

## Parallel Example: User Story 1

```bash
# After Phase 2 is complete, US1 tasks are sequential:
# T007 (prompts) → T008 (parser logic) → T009 (CLI handler) → T010 (edit flow) → T011 (defaults)
# Parser must exist before CLI can call it; edit flow extends CLI handler
```

## Parallel Example: User Story 4

```bash
# These can run in parallel (different CLI subcommands, no shared state):
Task: "T026 [P] [US4] Implement list CLI handler"
Task: "T027 [P] [US4] Implement show CLI handler"
# Then sequential:
Task: "T028 [US4] Implement compare CLI handler"
Task: "T029 [US4] Implement retire CLI handler"
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T006)
3. Complete Phase 3: US1 — Describe patterns (T007-T011)
4. Complete Phase 4: US2 — Backtest patterns (T012-T018)
5. **STOP and VALIDATE**: Jordan can describe patterns and backtest them — the core value loop
6. This alone lets Jordan test his pharma dip hypothesis against historical data

### Incremental Delivery

1. Setup + Foundational → infrastructure ready
2. US1 (Describe) → patterns can be created from plain text (MVP-lite)
3. US2 (Backtest) → patterns can be tested historically (MVP!)
4. US3 (Paper Trade) → patterns run forward in paper mode
5. US4 (Manage) → full lifecycle management
6. Polish → MCP tools, audit completeness

### Suggested MVP Scope

**US1 + US2 (Phases 1-4, tasks T001-T018)**: This delivers the core describe → backtest loop. Jordan can describe his pharma dip pattern, see it codified, and backtest it to understand why it worked for 3 months and then stopped. This is the highest-value subset.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All paper trades go through Alpaca paper trading only (Constitution Principle IV)
- Kill switch and risk limits checked on every trade proposal (Constitution Principle IV)
