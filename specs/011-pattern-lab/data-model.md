# Data Model: Pattern Lab

**Feature**: 011-pattern-lab
**Date**: 2026-03-08

## Entities

### Pattern

The core entity representing a user-defined trading pattern.

| Field | Type | Description |
|-------|------|-------------|
| id | integer | Auto-incrementing primary key |
| name | text | User-assigned name (e.g., "Pharma News Dip") |
| description | text | Original plain-text description from the user |
| rule_set_json | text (JSON) | Structured rules parsed from description |
| status | text | Lifecycle state: draft, backtested, paper_trading, retired |
| created_at | timestamp | When the pattern was created |
| updated_at | timestamp | Last modification |
| retired_at | timestamp | When the pattern was retired (null if active) |

**Status transitions**: draft → backtested → paper_trading → retired. Patterns can also go from backtested → retired (skipping paper trading) or paper_trading → backtested (re-tested after modification).

### Rule Set (embedded in Pattern as JSON)

The structured representation of a pattern's trading logic.

| Field | Type | Description |
|-------|------|-------------|
| trigger_type | text | "quantitative" or "qualitative" |
| trigger_conditions | list | Conditions that start watching (e.g., sector, news type, price spike threshold) |
| entry_signal | object | When to enter (e.g., pullback %, time window) |
| action | object | What to do: buy/sell, shares/options, option_type (call/put), strike_strategy, expiration_preference |
| exit_criteria | object | When to exit: profit target, stop loss, time-based exit |
| filters | list | Additional constraints: sector, market cap, volume minimums |

### Backtest Result

Historical performance evaluation of a pattern against market data.

| Field | Type | Description |
|-------|------|-------------|
| id | integer | Auto-incrementing primary key |
| pattern_id | integer | FK to pattern |
| date_range_start | date | Start of historical test period |
| date_range_end | date | End of historical test period |
| trigger_count | integer | How many times the pattern triggered |
| trade_count | integer | How many trades were simulated |
| win_count | integer | Trades with positive return |
| total_return_pct | real | Cumulative return percentage |
| avg_return_pct | real | Average per-trade return |
| max_drawdown_pct | real | Worst peak-to-trough decline |
| sharpe_ratio | real | Risk-adjusted return (if sufficient data) |
| regime_analysis_json | text (JSON) | Periods of strong/weak performance with possible explanations |
| sample_size_warning | boolean | True if trigger count < statistically significant threshold |
| created_at | timestamp | When backtest was run |

### Backtest Trade (detail records within a backtest)

| Field | Type | Description |
|-------|------|-------------|
| id | integer | Auto-incrementing primary key |
| backtest_id | integer | FK to backtest_result |
| ticker | text | Stock symbol |
| trigger_date | date | When pattern triggered |
| entry_date | date | When position was entered |
| entry_price | real | Entry price |
| exit_date | date | When position was exited |
| exit_price | real | Exit price |
| return_pct | real | Trade return percentage |
| action_type | text | "shares" or "options" |
| option_details_json | text (JSON) | Option type, strike, expiration (null for shares) |

### Paper Trade

Live simulated trades executed via Alpaca paper trading.

| Field | Type | Description |
|-------|------|-------------|
| id | integer | Auto-incrementing primary key |
| pattern_id | integer | FK to pattern |
| alpaca_order_id | text | Alpaca's order ID for the paper trade |
| ticker | text | Stock symbol |
| direction | text | "buy" or "sell" |
| action_type | text | "shares" or "options" |
| quantity | integer | Number of shares or contracts |
| entry_price | real | Actual fill price |
| exit_price | real | Exit fill price (null if still open) |
| pnl | real | Realized P&L (null if still open) |
| status | text | "proposed", "approved", "executed", "closed", "cancelled" |
| option_details_json | text (JSON) | Option type, strike, expiration (null for shares) |
| proposed_at | timestamp | When the system proposed this trade |
| executed_at | timestamp | When approved and sent to Alpaca |
| closed_at | timestamp | When the position was closed |

### Price Cache

Locally cached historical price data fetched from Alpaca for backtesting.

| Field | Type | Description |
|-------|------|-------------|
| id | integer | Auto-incrementing primary key |
| ticker | text | Stock symbol |
| timeframe | text | "day" or "hour" |
| bar_timestamp | timestamp | Bar timestamp |
| open | real | Open price |
| high | real | High price |
| low | real | Low price |
| close | real | Close price |
| volume | integer | Volume |
| vwap | real | Volume-weighted average price |
| fetched_at | timestamp | When this data was fetched from Alpaca |

**Unique constraint** on (ticker, timeframe, bar_timestamp).

## Relationships

```
Pattern 1──* Backtest Result
Pattern 1──* Paper Trade
Backtest Result 1──* Backtest Trade
```

## Indexes

- pattern: (status), (created_at)
- backtest_result: (pattern_id), (created_at)
- backtest_trade: (backtest_id), (ticker, trigger_date)
- paper_trade: (pattern_id), (status), (ticker)
- price_cache: (ticker, timeframe, bar_timestamp) UNIQUE
