# Data Model: Real Options Chain Data

**Feature**: 016-real-options-data
**Date**: 2026-03-08

## New Entities

### Option Price Cache (Database Table)

Stores historical OHLCV bars for option contracts, keyed by OCC symbol. Mirrors the existing `price_cache` table structure but for options.

**Fields**:
- `id` (int, auto): Primary key
- `option_symbol` (str, required): OCC-format symbol (e.g., "ABBV240315C00170000")
- `underlying_ticker` (str, required): The stock ticker (e.g., "ABBV") — indexed for lookups
- `timeframe` (str, required): Bar timeframe ("day")
- `bar_timestamp` (str, required): ISO 8601 timestamp
- `open` (float, required): Opening price (premium)
- `high` (float, required): High price
- `low` (float, required): Low price
- `close` (float, required): Closing price (premium)
- `volume` (int, required): Number of contracts traded
- `trade_count` (int, optional): Number of individual trades
- `fetched_at` (str, auto): Timestamp when cached

**Constraints**:
- Unique: (option_symbol, timeframe, bar_timestamp)
- Index on underlying_ticker for filtered lookups
- Index on option_symbol for direct lookups

### Option Contract Selection (In-Memory)

Represents the process of mapping abstract pattern rules to a specific tradeable contract. Not persisted — computed at backtest time.

**Fields**:
- `underlying_ticker` (str): Stock ticker
- `target_strike` (float): Calculated from pattern's strike strategy and underlying price
- `target_expiration` (date): Calculated from entry date + pattern's expiration_days
- `option_type` (str): "call" or "put" from pattern's action_type
- `selected_symbol` (str | None): OCC symbol of the best matching contract, or None if no data
- `selected_strike` (float | None): Actual strike of the selected contract
- `selected_expiration` (date | None): Actual expiration of the selected contract
- `pricing_source` (str): "real" or "estimated"

## Modified Entities

### BacktestTrade.option_details (Extended)

The existing `option_details` dict on `BacktestTrade` gains new fields when real pricing is used:

**Current fields** (unchanged):
- `type`: Action type (buy_call, sell_call, etc.)
- `strike_strategy`: ATM, OTM_5, etc.
- `expiration_days`: Target days to expiration
- `underlying_return_pct`: Stock price change percentage

**New fields** (added by this feature):
- `pricing`: "real" or "estimated" — whether actual market data or synthetic model was used
- `option_symbol`: OCC symbol of the specific contract (e.g., "ABBV240315C00170000")
- `entry_premium`: Actual option price at entry (if pricing="real")
- `exit_premium`: Actual option price at exit (if pricing="real")
- `volume_at_entry`: Contract volume on entry date (if pricing="real")

### CoveredCallCycle (Extended)

The existing `CoveredCallCycle` model gains:
- `pricing`: "real" or "estimated"
- `option_symbol`: OCC symbol of the sold call contract
- `real_premium`: Actual market premium (if pricing="real", overrides Black-Scholes estimate)

## Persistence

### New Table: `option_price_cache`

Added via migration 009. Same lifecycle as `price_cache` — data accumulates over time and is never deleted (cache only grows).

### Modified: `backtest_trade.option_details_json`

The existing JSON column already stores option details as a flexible dict. The new fields (`pricing`, `option_symbol`, `entry_premium`, `exit_premium`, `volume_at_entry`) are added to this dict. No schema change required — the column is unstructured JSON.

### Modified: `covered_call_cycle`

The `covered_call_cycle` table from migration 008 does not need schema changes. The `call_premium` column already stores the premium amount — when real data is used, it stores the real premium instead of the estimated one. The `pricing` and `option_symbol` metadata can be stored in the existing `option_details_json` field pattern (or a new nullable text column if needed for querying).
