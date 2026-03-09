# Research: Real Options Chain Data

**Feature**: 016-real-options-data
**Date**: 2026-03-08

## R1: Historical Option Data Strategy

**Decision**: Construct OCC option symbols from backtest parameters, then fetch historical bars via `get_option_bars()`. Fall back to synthetic pricing when no data is returned.

**Rationale**: Alpaca's `get_option_chain()` only returns current/live snapshots — it cannot query what contracts existed at a historical date. However, `get_option_bars()` can fetch historical OHLCV data for any option symbol. By constructing the OCC symbol ourselves (underlying + expiration + type + strike), we can request historical bars and get real prices if the contract had trading activity.

The approach for each backtest trade:
1. Know the underlying price at the entry date (from cached stock bars)
2. Calculate target strike using the pattern's strike strategy (ATM → nearest $5 increment to current price; OTM 5% → nearest increment above/below)
3. Calculate target expiration (entry_date + pattern's expiration_days, round to nearest standard monthly expiration — 3rd Friday)
4. Construct OCC symbol: `{ticker}{YYMMDD}{C|P}{strike*1000:08d}`
5. Fetch historical bars for that symbol around entry/exit dates
6. If bars exist with non-zero volume: use real close prices as entry/exit premiums
7. If no data: fall back to synthetic `_estimate_options_return()` and flag as estimated

**Alternatives considered**:
- **Use get_option_chain() only**: Only works for current snapshots. Cannot provide historical pricing for backtesting. Rejected.
- **Third-party options data provider** (CBOE, OptionMetrics): Expensive subscriptions ($500+/mo), adds dependency outside the broker. Rejected — Alpaca's data is included with the existing subscription.
- **Build OCC symbols from scratch only**: Risk of constructing symbols for non-existent contracts. Mitigated by graceful fallback to synthetic pricing. Accepted with fallback.

## R2: OCC Option Symbol Construction

**Decision**: Build a helper function that constructs OCC-format option symbols from (ticker, expiration_date, strike_price, option_type). Standard format: `{TICKER}{YYMMDD}{C|P}{STRIKE*1000:08d}`.

**Rationale**: The OCC (Options Clearing Corporation) format is the industry standard used by Alpaca and all US exchanges. The codebase already receives these symbols from `get_option_chain()` in executor.py but never constructs them. For backtesting, we need to build them from pattern parameters.

Examples:
- ABBV, 2024-03-15, Call, $170.00 → `ABBV240315C00170000`
- MRNA, 2024-06-21, Put, $125.50 → `MRNA240621P00125500`

Standard monthly expirations fall on the 3rd Friday of each month. When the pattern's target expiration doesn't land on a Friday, round to the nearest standard monthly expiration.

**Alternatives considered**:
- **Query chain first, then match**: Would require live API access for every backtest date. Slow and cannot work for historical dates. Rejected.
- **Use approximate symbols with tolerance**: Try the exact symbol, then nearby strikes (±$2.50, ±$5.00) if no data. Accepted as fallback within the main approach.

## R3: Option Price Caching Strategy

**Decision**: Create a new `option_price_cache` table alongside the existing `price_cache` table. Same OHLCV structure but keyed by OCC symbol instead of stock ticker.

**Rationale**: The existing `price_cache` table is tightly coupled to stock bars (unique index on ticker+timeframe+bar_timestamp). Option symbols are fundamentally different — they're long OCC strings, each representing a specific contract. A separate table keeps the schema clean and avoids confusion between stock and option data.

The cache serves the same purpose as stock bar caching: avoid redundant Alpaca API calls across repeated backtests. Once option bars are fetched for a contract, they're stored permanently.

**Alternatives considered**:
- **Reuse price_cache table**: Would work technically (OCC symbol as "ticker"), but the unique index semantics and column names become confusing. Rejected for clarity.
- **In-memory cache only**: Lost on restart, wastes API calls. Rejected (same reasoning as stock bar caching in R1 of feature 015).
- **File-based cache** (Parquet/CSV): Adds complexity, harder to query. Rejected — SQLite is the established pattern.

## R4: Contract Selection Logic

**Decision**: Implement a "nearest available contract" selection that tries the exact target, then widens the search to nearby strikes and expirations.

**Rationale**: Options have discrete strikes (typically $2.50 or $5.00 increments for stocks in the $50-300 range) and discrete expirations (3rd Friday monthly, plus weeklies for liquid names). The pattern's calculated target (ATM at $172.34, expiration in 30 days) won't exactly match an available contract. The selection algorithm:

1. Round target strike to nearest standard increment ($5 for stocks >$100, $2.50 for $25-100, $1 for <$25)
2. Round target expiration to nearest 3rd Friday (monthly) or nearest Friday (weekly)
3. Construct OCC symbol and fetch bars
4. If no data: try ±1 strike increment (e.g., $165 and $175 if target was $170)
5. If still no data: fall back to synthetic pricing

For strike increments, use the standard options exchange rules based on underlying price.

**Alternatives considered**:
- **Exact match only**: Too restrictive — many viable trades would fall back to synthetic unnecessarily. Rejected.
- **Wide search across many strikes**: Fetching bars for 10+ symbols per trade would be slow and hit rate limits. Rejected — limit to target ± 1 increment.

## R5: Backtest Engine Integration Point

**Decision**: Inject real options pricing at the trade execution level (`_execute_simulated_trade` and covered call cycle processing), replacing the call to `_estimate_options_return()` when real data is available.

**Rationale**: The backtest engine's architecture separates trigger detection from trade execution. The option pricing change belongs at the execution layer — when a trade is being simulated, attempt to fetch real option bars. If available, calculate return from actual premiums. If not, call the existing `_estimate_options_return()`.

This minimizes changes to the backtest flow:
- Trigger detection: unchanged
- Entry signal: unchanged
- Trade execution: enhanced with real option pricing
- Result aggregation: unchanged (already works with return_pct regardless of source)

The `BacktestTrade.option_details` dict will be extended with `"pricing": "real"` or `"pricing": "estimated"` and `"option_symbol"` fields.

**Alternatives considered**:
- **Pre-fetch all option data before backtest**: Would need to know all entry/exit dates upfront, which aren't known until triggers fire. Rejected.
- **Create a separate "real options" backtest engine**: Duplicates most of the existing logic. Rejected — enhance the existing engine.
