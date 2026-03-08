# Tasks: Covered Call Income Strategy

**Input**: Design documents from `/specs/012-covered-call-strategy/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md

**Tests**: Not explicitly requested in spec. Test tasks omitted.

**Organization**: Tasks grouped by user story for independent implementation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the option pricing module, data model, and migration

- [x] T001 Create database migration `migrations/008_covered_call.sql` with `covered_call_cycle` table per data-model.md — includes outcome CHECK constraint, indexes on (pattern_id, cycle_number) and (ticker, cycle_start_date), PRAGMA user_version = 8
- [x] T002 [P] Create option pricing module `src/finance_agent/patterns/option_pricing.py` — implement `norm_cdf()` using `math.erf` (no scipy), `calculate_historical_volatility(bars, lookback_days=20)` returning annualized vol, and `estimate_call_premium(spot_price, strike_price, days_to_expiration, historical_volatility, risk_free_rate=0.045)` using Black-Scholes formula per research.md R1/R5
- [x] T003 [P] Add `CoveredCallCycle` Pydantic model to `src/finance_agent/patterns/models.py` — fields: ticker, cycle_number, stock_entry_price, call_strike, call_premium, call_expiration_date, cycle_start_date, cycle_end_date, stock_price_at_exit, outcome, premium_return_pct, total_return_pct, capped_upside_pct, historical_volatility

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Storage operations and parser enhancements that all user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Implement covered call cycle CRUD in `src/finance_agent/patterns/storage.py` — `save_covered_call_cycle()`, `get_covered_call_cycles(pattern_id)`, `get_covered_call_summary(pattern_id)` returning total premium, assignment count, annualized yield, cycle count
- [x] T005 Enhance pattern parser to recognize covered calls in `src/finance_agent/patterns/parser.py` — update system prompt to detect "covered call", "sell calls", "write calls" descriptions; set action_type to sell_call; apply covered call defaults (5% OTM, 30-day expiration, 50% premium profit target, 21-day roll threshold); warn on naked call descriptions per FR-002/FR-003
- [x] T006 [P] Add `--shares` flag to backtest subparser in `src/finance_agent/cli.py` — optional integer argument defaulting to 100, passed through to backtest handler for total dollar income calculation

**Checkpoint**: Foundation ready — option pricing, storage, parser enhancements, and CLI flag in place

---

## Phase 3: User Story 1 — Describe a Covered Call Pattern (Priority: P1) MVP

**Goal**: Jordan describes a covered call in plain text, the system parses it into structured rules with sell_call action type, strike distance, expiration, and covered call exit criteria.

**Independent Test**: Run `finance-agent pattern describe "I own 500 shares of ABBV. Sell monthly calls 5% out of the money, close at 50% profit or roll at 21 days to expiration"` and verify structured rules show action type "sell call" with correct strike, expiration, and exit criteria.

### Implementation for User Story 1

- [x] T007 [US1] Add covered call display formatting to `_pattern_describe()` in `src/finance_agent/cli.py` — when action_type is sell_call, display "Stock Position" section (ticker, shares), "Call Sale" section (strike distance, expiration), and covered call exit criteria (premium profit target, roll threshold) per contracts/cli.md describe output format
- [x] T008 [US1] Add covered call defaults annotation to `src/finance_agent/patterns/parser.py` — when action_type is sell_call and fields are missing, apply and log: 5% OTM strike, 30-day expiration, 50% premium profit target, 21-day roll threshold, no max hold (repeating cycles) per FR-003

**Checkpoint**: User Story 1 complete — `finance-agent pattern describe` recognizes covered calls, applies defaults, displays formatted two-leg position summary

---

## Phase 4: User Story 2 — Backtest a Covered Call Against Historical Data (Priority: P1)

**Goal**: Run a covered call pattern against historical price data and produce a monthly income report showing premiums collected, assignment frequency, annualized yield, and comparison to buy-and-hold.

**Independent Test**: Run `finance-agent pattern backtest <id> --start 2024-01-01 --end 2025-12-31 --tickers ABBV --shares 500` on a saved covered call pattern and verify report shows monthly cycles, premium income, assignment events, and buy-and-hold comparison.

### Implementation for User Story 2

- [x] T009 [US2] Implement covered call backtest simulation in `src/finance_agent/patterns/backtest.py` — add `run_covered_call_backtest(pattern_id, rule_set, bars, start_date, end_date, shares)` that iterates monthly cycles: at each cycle start, calculate strike from OTM percentage, estimate premium via `option_pricing.estimate_call_premium()`, then simulate through expiration checking for assignment (stock > strike), early close (premium profit target), or roll (DTE threshold)
- [x] T010 [US2] Add assignment and roll logic to covered call backtest in `src/finance_agent/patterns/backtest.py` — for each cycle: if stock_price > strike at expiration → outcome="assigned", cap stock gain at strike; if premium decayed >50% of initial → outcome="closed_early"; if DTE reaches roll threshold → outcome="rolled"; otherwise → outcome="expired_worthless". Calculate per-cycle return as (premium + min(stock_gain, strike-entry)) / entry_price per research.md R3/R4
- [x] T011 [US2] Add buy-and-hold comparison to covered call backtest in `src/finance_agent/patterns/backtest.py` — calculate simple stock return over the same period, compute capped_upside_cost (total gains forfeited from assignments), and include both in the backtest report
- [x] T012 [US2] Implement covered call cycle persistence in `src/finance_agent/patterns/storage.py` — `save_covered_call_cycles(cycles: list[CoveredCallCycle], pattern_id, backtest_result_id)` writes to `covered_call_cycle` table; also save aggregate metrics to `backtest_result` with covered call-specific fields in the existing JSON columns
- [x] T013 [US2] Add sample size warning for covered calls in `src/finance_agent/patterns/backtest.py` — warn if fewer than 6 monthly cycles (minimum for meaningful income estimation); include warning in report output
- [x] T014 [US2] Implement covered call backtest CLI handler in `src/finance_agent/cli.py` — detect sell_call action type in `_pattern_backtest()`, call `run_covered_call_backtest()` instead of standard `run_backtest()`, display monthly income report per contracts/cli.md format: cycles, avg premium, total premium, annualized yield, assignment frequency, buy-and-hold comparison, month-by-month breakdown

**Checkpoint**: User Story 2 complete — `finance-agent pattern backtest` produces covered call income report with monthly breakdown. Combined with US1, the describe → backtest loop works for covered calls.

---

## Phase 5: User Story 3 — Paper Trade a Covered Call in Real Time (Priority: P2)

**Goal**: Activate a covered call for paper trading — use Alpaca option chain to find real strikes, submit sell-to-open orders, track through expiration or roll.

**Independent Test**: Activate a covered call pattern for paper trading, verify it looks up real option contracts, proposes selling a call at the correct strike, and submits via Alpaca paper trading.

### Implementation for User Story 3

- [x] T015 [US3] Implement option chain lookup in `src/finance_agent/patterns/executor.py` — add `_find_call_contract(ticker, strike_pct_otm, expiration_days)` that uses `OptionHistoricalDataClient.get_option_chain()` to find the nearest matching call contract (closest strike to target OTM%, nearest monthly expiration)
- [x] T016 [US3] Implement covered call order submission in `src/finance_agent/patterns/executor.py` — add `_execute_covered_call(trade_id, ticker, contract_symbol)` that builds an `OptionLegRequest` with `side=SELL`, `position_intent=PositionIntent.SELL_TO_OPEN`, submits via Alpaca TradingClient, updates paper_trade with order details
- [x] T017 [US3] Implement roll detection in `src/finance_agent/patterns/executor.py` — in `_check_open_positions()`, for sell_call positions: check DTE against roll threshold; if reached, propose closing current call (BUY_TO_CLOSE) and selling next month's call (SELL_TO_OPEN); display roll proposal with estimated new premium
- [x] T018 [US3] Implement assignment detection in `src/finance_agent/patterns/executor.py` — in `_check_open_positions()`, for sell_call positions: check if stock price > strike near expiration; if so, record as assigned, calculate total P&L (premium + stock gain capped at strike), update paper_trade and log via AuditLogger
- [x] T019 [US3] Implement covered call paper-trade CLI handler in `src/finance_agent/cli.py` — in `_pattern_paper_trade()`, detect sell_call action type; validate pattern status is "backtested"; display proposed call sale with real option chain data (contract symbol, bid/ask, estimated premium); start monitoring loop per contracts/cli.md format

**Checkpoint**: User Story 3 complete — covered calls can be paper traded with real Alpaca option chain data, roll detection, and assignment handling

---

## Phase 6: User Story 4 — Compare Covered Call Parameters (Priority: P3)

**Goal**: Compare conservative vs. moderate vs. aggressive covered call configurations side-by-side.

**Independent Test**: Create three covered call patterns with different strike distances, backtest all three, run `finance-agent pattern compare` and verify output shows annualized yield, assignment frequency, and capped upside cost for each.

### Implementation for User Story 4

- [x] T020 [US4] Extend `_pattern_compare()` in `src/finance_agent/cli.py` to detect covered call patterns — when comparing sell_call patterns, display covered call-specific columns: annualized yield, assignment frequency, avg premium/month, capped upside cost, total return, buy-and-hold return per contracts/cli.md compare format
- [x] T021 [US4] Add covered call metrics to `get_covered_call_summary()` in `src/finance_agent/patterns/storage.py` — return annualized income yield, assignment percentage, average premium per cycle, total capped upside cost; these feed into the compare display

**Checkpoint**: User Story 4 complete — full covered call parameter comparison available

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Audit logging, validation, and documentation

- [x] T022 [P] Add audit logging for covered call operations in `src/finance_agent/patterns/storage.py` and `executor.py` — events: covered_call_described, covered_call_backtested, covered_call_sold, covered_call_rolled, covered_call_assigned, covered_call_expired via existing AuditLogger
- [x] T023 [P] Update `docs/covered-call-strategy.md` with actual backtest results — replace placeholder examples with real ABBV covered call backtest data showing monthly income, assignment frequency, and parameter comparison
- [x] T024 Validate end-to-end flow: describe covered call → backtest → paper trade → compare parameters using CLI commands per quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — no other story dependencies
- **US2 (Phase 4)**: Depends on Phase 2 — needs a saved covered call pattern from US1 to be meaningful but can be developed with test fixtures
- **US3 (Phase 5)**: Depends on Phase 2 — benefits from US1+US2 but can be developed independently
- **US4 (Phase 6)**: Depends on Phase 2 — needs backtest results from US2 to be meaningful
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (Describe)**: Independent — core input mechanism for covered calls
- **US2 (Backtest)**: Logically follows US1 (needs a pattern to backtest) but can use test fixtures
- **US3 (Paper Trade)**: Logically follows US2 (should backtest before paper trading) but can use test fixtures
- **US4 (Compare)**: Needs multiple backtested patterns — logically follows US2

### Within Each User Story

- Storage operations before business logic
- Business logic before CLI handlers
- Core features before optional enhancements

### Parallel Opportunities

- T002 (option pricing) can run in parallel with T003 (models)
- T005 (parser) can run in parallel with T006 (CLI flag)
- T022, T023 (audit, docs) can run in parallel

---

## Parallel Example: User Story 2

```bash
# After Phase 2 is complete, US2 tasks are sequential:
# T009 (simulation) → T010 (assignment/roll) → T011 (buy-and-hold comparison)
# → T012 (persistence) → T013 (sample warning) → T014 (CLI handler)
# Simulation must exist before CLI can call it; persistence stores results
```

## Parallel Example: Phase 1

```bash
# These can run in parallel (different files):
Task: "T002 [P] Create option pricing module"
Task: "T003 [P] Add CoveredCallCycle model"
# Then T001 (migration) is independent too, but usually run first
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T006)
3. Complete Phase 3: US1 — Describe covered calls (T007-T008)
4. Complete Phase 4: US2 — Backtest covered calls (T009-T014)
5. **STOP and VALIDATE**: Jordan can describe a covered call and see monthly income projections — the core value loop
6. This alone lets Jordan test whether selling calls on his ABBV position would generate meaningful income

### Incremental Delivery

1. Setup + Foundational → infrastructure ready
2. US1 (Describe) → covered calls can be described and saved (MVP-lite)
3. US2 (Backtest) → monthly income backtesting with premium estimation (MVP!)
4. US3 (Paper Trade) → live paper trading with real option chain data
5. US4 (Compare) → parameter optimization (conservative vs aggressive)
6. Polish → audit logging, documentation, end-to-end validation

### Suggested MVP Scope

**US1 + US2 (Phases 1-4, tasks T001-T014)**: This delivers the core describe → backtest loop for covered calls. Jordan can describe his ABBV covered call strategy, see it codified, and backtest it to see monthly premium income vs. buy-and-hold. This is the highest-value subset.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All paper trades go through Alpaca paper trading only (Constitution Principle IV)
- Kill switch and risk limits checked on every trade proposal (Constitution Principle IV)
- Premium estimates in backtesting are approximations — report clearly labels them as estimates, not actual option prices
