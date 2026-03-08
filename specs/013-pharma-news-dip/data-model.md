# Data Model: Pharma News Dip Pattern

**Feature**: 013-pharma-news-dip
**Date**: 2026-03-08

## Existing Entities (No Changes)

These existing models already support the pharma news dip pattern:

### BacktestTrade
Already captures all needed trade data:
- `ticker`, `trigger_date`, `entry_date`, `entry_price`
- `exit_date`, `exit_price`, `return_pct`, `action_type`
- `option_details` (dict — strike, expiration, premium)

### BacktestReport
Already captures aggregate metrics + regimes:
- `trigger_count`, `trade_count`, `win_count`
- `total_return_pct`, `avg_return_pct`, `max_drawdown_pct`, `sharpe_ratio`
- `regimes: list[RegimePeriod]` — regime analysis results
- `trades: list[BacktestTrade]` — individual trades
- `sample_size_warning: bool`

### RegimePeriod
Already has all needed fields:
- `start_date`, `end_date`, `win_rate`, `avg_return_pct`, `trade_count`
- `label` (will use: "strong", "weak", "breakdown")
- `explanation` (optional context for regime shift)

### RuleSet
Already supports qualitative triggers, sector filters, and option actions:
- `trigger_type: TriggerType.QUALITATIVE`
- `trigger_conditions: list[TriggerCondition]` — price_change_pct, volume_spike
- `entry_signal: EntrySignal` — pullback_pct with window_days
- `action: TradeAction` — BUY_CALL with strike strategy
- `sector_filter: str` — "healthcare" / "pharma"

## New Entities

### DetectedEvent (in-memory, not persisted)

Represents a detected price spike used as a news event proxy during backtesting. Not stored in the database — exists only during backtest execution.

| Field | Type | Description |
|-------|------|-------------|
| date | str | Bar date when spike was detected (ISO format) |
| ticker | str | Stock ticker |
| price_change_pct | float | Single-day price change percentage |
| volume_multiple | float | Volume as multiple of 20-day average |
| close_price | float | Closing price on spike day (reference for dip calculation) |
| high_price | float | Intraday high on spike day |
| event_label | str or None | Optional user-provided label (e.g., "FDA approval") |
| source | str | "proxy" (automatic detection) or "manual" (user-provided date) |

**Relationships**: One DetectedEvent → zero or one BacktestTrade (trigger may fire but no entry occurs)

### EventDetectionConfig (in-memory, not persisted)

Configuration for the event detection engine. Passed into the backtest function.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| spike_threshold_pct | float | 5.0 | Minimum single-day price increase |
| volume_multiple_min | float | 1.5 | Minimum volume vs 20-day average |
| volume_lookback_days | int | 20 | Days for average volume calculation |
| cooldown_mode | str | "trade_lifecycle" | How to handle consecutive spikes |
| manual_events | list[ManualEvent] or None | None | User-provided event dates (overrides proxy) |

### ManualEvent (in-memory, not persisted)

A user-provided event date, parsed from CLI flag or file.

| Field | Type | Description |
|-------|------|-------------|
| date | str | Event date (YYYY-MM-DD format) |
| label | str or None | Optional description (e.g., "MRNA FDA approval") |

### RegimeConfig (in-memory, not persisted)

Configuration for regime analysis. Controls window size and classification thresholds.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| window_trading_days | int | 63 | Rolling window size (~3 months) |
| strong_threshold | float | 0.60 | Win rate ≥ this → "strong" |
| weak_threshold | float | 0.40 | Win rate ≥ this but < strong → "weak"; below → "breakdown" |
| min_trades_for_regime | int | 10 | Skip regime analysis if fewer trades |
| min_trades_per_window | int | 3 | Skip windows with fewer trades |

## Database Schema

No new tables needed. All new entities are in-memory only (used during backtest computation). Results are stored using existing tables:

- `backtest_result` — aggregate metrics (via `save_backtest_result()`)
- `backtest_trade` — individual trades (via `save_backtest_result()`)
- Regime data serialized as JSON in `backtest_result.regimes_json`

The `detected_events` metadata (count, source, spike threshold used) will be stored as part of the backtest result's metadata JSON for auditability.

## State Transitions

No new state transitions. Patterns follow the existing lifecycle:

```
draft → backtested → paper_trading → retired
```

The only difference: when trigger_type is QUALITATIVE and paper trading, the monitor requires human confirmation at the trigger step (not just the trade proposal step).
