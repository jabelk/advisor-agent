# Tasks: Real Options Chain Data

**Input**: Design documents from `/specs/016-real-options-data/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/option-data.md, quickstart.md

**Tests**: Included in Polish phase — unit tests for new option data module.

**Organization**: Tasks grouped by user story. US1 builds the core option data infrastructure, US2 extends it to covered calls, US3 adds the MCP tool.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Database migration and new option data module scaffolding

- [X] T001 Create migration migrations/009_option_cache.sql with `option_price_cache` table: id (int pk), option_symbol (text not null), underlying_ticker (text not null), timeframe (text not null), bar_timestamp (text not null), open (real), high (real), low (real), close (real), volume (int), trade_count (int), fetched_at (text default current_timestamp); unique index on (option_symbol, timeframe, bar_timestamp); index on underlying_ticker; index on option_symbol
- [X] T002 Create src/finance_agent/patterns/option_data.py with module docstring and imports (datetime, sqlite3, alpaca OptionHistoricalDataClient, OptionBarsRequest, TimeFrame)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core helpers that all user stories depend on

- [X] T003 Implement `build_occ_symbol(ticker, expiration_date, strike_price, option_type)` in src/finance_agent/patterns/option_data.py — constructs OCC-format option symbol string (e.g., "ABBV240315C00170000") from components per contracts/option-data.md
- [X] T004 Implement `find_nearest_expiration(target_date, prefer_monthly=True)` in src/finance_agent/patterns/option_data.py — returns the nearest 3rd-Friday monthly expiration date to the target date
- [X] T005 Implement `round_strike_price(underlying_price, strike_strategy, custom_offset_pct=None, option_type="call")` in src/finance_agent/patterns/option_data.py — calculates target strike from underlying price and strategy (atm, otm_5, otm_10, itm_5, custom), then rounds to nearest standard increment ($5 for stocks >$100, $2.50 for $25-100, $1 for <$25)
- [X] T006 Implement `fetch_and_cache_option_bars(conn, option_symbol, start_date, end_date, api_key, secret_key)` in src/finance_agent/patterns/option_data.py — checks option_price_cache first, fetches missing bars via OptionHistoricalDataClient.get_option_bars(), caches them, returns list[dict] of bars; returns empty list if no data from broker

**Checkpoint**: Core helpers ready — user story implementation can begin

---

## Phase 3: User Story 1 — Backtest with Real Option Prices (Priority: P1) 🎯 MVP

**Goal**: Replace synthetic leverage multiplier with real historical option premiums in the general backtest engine

**Independent Test**: Run `finance-agent pattern backtest 1 --tickers ABBV` for a buy_call pattern and verify trades show actual option contract symbols, real entry/exit premiums, and `"pricing": "real"` flag

### Implementation for User Story 1

- [X] T007 [US1] Implement `select_option_contract(conn, underlying_ticker, underlying_price, entry_date, exit_date, strike_strategy, custom_strike_offset_pct, expiration_days, option_type, api_key, secret_key)` in src/finance_agent/patterns/option_data.py — orchestrates contract selection: calculates target strike via round_strike_price, finds nearest expiration, builds OCC symbol, fetches bars for entry/exit dates, tries ±1 strike increment if no data, returns dict with option_symbol/strike/expiration/entry_premium/exit_premium/volume_at_entry/pricing per contracts/option-data.md
- [X] T008 [US1] Modify `_execute_simulated_trade()` in src/finance_agent/patterns/backtest.py to call `select_option_contract()` for options-based action types (buy_call, buy_put, sell_call, sell_put) when Alpaca keys are available; if pricing="real", calculate return_pct from actual entry/exit premiums instead of calling `_estimate_options_return()`; if pricing="estimated", fall back to existing synthetic logic; add option_symbol and pricing fields to option_details dict
- [X] T009 [US1] Add `_get_alpaca_keys_optional()` helper in src/finance_agent/patterns/backtest.py that reads ALPACA_PAPER_API_KEY and ALPACA_PAPER_SECRET_KEY from environment, returns (key, secret) tuple or (None, None) if not set — used to determine if real option pricing is available without erroring
- [X] T010 [US1] Update CLI display in src/finance_agent/cli.py to show option contract symbol and pricing source ("real" vs "estimated") in backtest trade output tables when option_details contains the new fields

**Checkpoint**: General backtest now uses real option prices when available

---

## Phase 4: User Story 2 — Covered Call Backtest with Real Premiums (Priority: P2)

**Goal**: Replace Black-Scholes premium estimates with real historical premiums in the covered call backtest engine

**Independent Test**: Run `finance-agent pattern backtest <covered_call_id> --tickers ABBV` and verify cycle premiums come from real market data with option symbols shown

### Implementation for User Story 2

- [X] T011 [US2] Modify the covered call cycle initialization in `run_covered_call_backtest()` in src/finance_agent/patterns/backtest.py to call `select_option_contract()` for the sold call at each cycle start; if pricing="real", use real premium instead of Black-Scholes `estimate_call_premium()`; set pricing flag on cycle data
- [X] T012 [US2] Modify the covered call exit/expiration logic in `run_covered_call_backtest()` to use real exit premium from historical bars when pricing="real" instead of the synthetic `estimate_premium_at_age()` calculation
- [X] T013 [US2] Update the covered call CLI display in src/finance_agent/cli.py to show option symbols and pricing source for each cycle

**Checkpoint**: Covered call backtest now uses real premiums when available

---

## Phase 5: User Story 3 — Option Chain Lookup via MCP (Priority: P3)

**Goal**: Expose option chain lookup as an MCP tool for ad-hoc research from Claude Desktop

**Independent Test**: In Claude Desktop, ask about ABBV call options near a specific date and verify structured results with contract symbols and prices

### Implementation for User Story 3

- [X] T014 [US3] Implement `get_option_chain_history` MCP tool in src/finance_agent/mcp/research_server.py: accept ticker (str), date (str), option_type (str, optional), strike_min (float, optional), strike_max (float, optional), expiration_within_days (int, optional, default 45); construct candidate OCC symbols for strikes in the range at standard increments; fetch bars for each via fetch_and_cache_option_bars; return list of contracts with symbol, strike, expiration, close_price, volume, pricing per contracts/option-data.md
- [X] T015 [US3] Add error handling for get_option_chain_history: missing Alpaca keys, no data found, invalid date format — all return {"error": "..."} dicts; update test_mcp_integration.py expected tool count from 14 to 15

**Checkpoint**: Option chain lookup works from Claude Desktop

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Tests and validation

- [X] T016 [P] Write unit tests for option data functions in tests/unit/test_option_data.py: test build_occ_symbol (various tickers/strikes/types), test find_nearest_expiration (edge cases around month boundaries), test round_strike_price (all strategies), test select_option_contract with mocked bars (real and fallback cases), test fetch_and_cache_option_bars with mocked API
- [X] T017 Verify existing tests still pass (294+ tests from previous features)
- [X] T018 Run quickstart.md scenarios with live Alpaca data to validate end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (migration + module scaffolding)
- **US1 (Phase 3)**: Depends on Phase 2 (core helpers)
- **US2 (Phase 4)**: Depends on Phase 2. Could run parallel to US1 but modifies same file (backtest.py) — recommend sequential after US1
- **US3 (Phase 5)**: Depends on Phase 2 (fetch_and_cache_option_bars). Independent of US1/US2 (different file)
- **Polish (Phase 6)**: Depends on all user stories being complete

### Within Each User Story

- Implementation before error handling/display updates
- All tasks in same file — sequential within story

### Parallel Opportunities

- **Phase 1**: T001 and T002 are in different files — could be parallel
- **Phase 2**: T003-T005 are all in option_data.py — sequential. T006 depends on T003.
- **Phase 3 vs Phase 5**: US1 (backtest.py) and US3 (research_server.py) modify different files — could theoretically run in parallel after Phase 2
- **Phase 6**: T016 is in a different file — independent

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (migration + module)
2. Complete Phase 2: Foundational (OCC symbols, expiration logic, strike rounding, bar fetching)
3. Complete Phase 3: User Story 1 (integrate into general backtest engine)
4. **STOP and VALIDATE**: Test with live Alpaca data on ABBV
5. Proceed to US2/US3

### Incremental Delivery

1. Setup → Module + migration ready
2. Foundational → Core helpers ready
3. Add US1 (general backtest real pricing) → Test with live data
4. Add US2 (covered call real pricing) → Test with live data
5. Add US3 (MCP option lookup) → Test in Claude Desktop
6. Polish → Unit tests, regression check

---

## Notes

- New module `option_data.py` contains all option-specific data logic — no changes to existing `option_pricing.py` (kept as fallback)
- Migration 009 creates `option_price_cache` table — separate from stock `price_cache`
- Alpaca keys are optional for backtest — if not set, all trades use synthetic pricing (backward compatible)
- The `BacktestTrade.option_details` dict is already a flexible JSON column — new fields added without schema changes
- OCC symbol format: `{TICKER}{YYMMDD}{C|P}{STRIKE*1000:08d}` (e.g., ABBV240315C00170000)
