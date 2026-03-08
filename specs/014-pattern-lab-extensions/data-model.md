# Data Model: Pattern Lab Extensions

**Feature**: 014-pattern-lab-extensions
**Date**: 2026-03-08

## Existing Entities (No Changes)

### BacktestReport

Already defined in 011-pattern-lab. Used as the aggregate metrics container within `AggregatedBacktestReport.combined_report`.

| Field | Type | Description |
|-------|------|-------------|
| trigger_count | int | How many times the pattern triggered |
| trade_count | int | How many trades were simulated |
| win_count | int | Trades with positive return |
| total_return_pct | float | Cumulative return percentage |
| avg_return_pct | float | Average per-trade return |
| max_drawdown_pct | float | Worst peak-to-trough decline |
| sharpe_ratio | float | Risk-adjusted return (if sufficient data) |
| regimes | list[RegimePeriod] | Periods of strong/weak performance |
| trades | list[BacktestTrade] | Individual trade detail records |
| sample_size_warning | bool | True if trigger count < statistically significant threshold |

### BacktestTrade

Individual trade record within a backtest.

| Field | Type | Description |
|-------|------|-------------|
| ticker | str | Stock symbol |
| trigger_date | str | When pattern triggered |
| entry_date | str | When position was entered |
| entry_price | float | Entry price |
| exit_date | str | When position was exited |
| exit_price | float | Exit price |
| return_pct | float | Trade return percentage |
| action_type | str | "shares" or "options" |
| option_details | dict or None | Option type, strike, expiration (None for shares) |

### RegimePeriod

A time window with distinct performance characteristics.

| Field | Type | Description |
|-------|------|-------------|
| start_date | str | Period start (YYYY-MM-DD) |
| end_date | str | Period end (YYYY-MM-DD) |
| win_rate | float | Win rate during this period |
| avg_return_pct | float | Average return during this period |
| trade_count | int | Number of trades in this period |
| label | str | Descriptive label (e.g., "strong", "weak") |

## New Entities (In-Memory Only)

All new entities are Pydantic models. They are computed in-memory and not persisted to new database tables. Backtest results are saved via the existing `save_backtest_result()` function.

### TickerBreakdown

Per-ticker results within a multi-ticker backtest. Provides granular visibility into how each stock contributed to the aggregate.

| Field | Type | Description |
|-------|------|-------------|
| ticker | str | Stock symbol |
| events_detected | int | Number of pattern trigger events for this ticker |
| trades_entered | int | Number of trades that met entry criteria |
| win_count | int | Trades with positive return |
| win_rate | float | win_count / trades_entered (0.0 if no trades) |
| avg_return_pct | float | Average per-trade return for this ticker |
| total_return_pct | float | Cumulative return across all trades for this ticker |

**Notes**:
- Tickers with zero events still appear in the breakdown with all-zero values.
- Tickers with no available price data show events_detected = 0 and are excluded from aggregate calculations.

### AggregatedBacktestReport

Combined results across multiple tickers for a single pattern. Pools all trades into one combined analysis.

| Field | Type | Description |
|-------|------|-------------|
| pattern_id | int | FK to the pattern being tested |
| date_range_start | str | Backtest period start (YYYY-MM-DD) |
| date_range_end | str | Backtest period end (YYYY-MM-DD) |
| tickers | list[str] | All tickers included in the backtest |
| ticker_breakdowns | list[TickerBreakdown] | Per-ticker result breakdown |
| combined_report | BacktestReport | Aggregate metrics across all tickers (pooled trades) |
| no_entry_events | list[dict] | Events where pattern triggered but entry criteria were not met |

**Notes**:
- `combined_report` aggregates across all tickers: trades are pooled (not averaged per-ticker) to treat the pattern as a sector-level strategy.
- Regime analysis in `combined_report.regimes` runs on the combined trade set, providing a sector-level regime view.

### PairwiseComparison

Statistical comparison between two pattern variants. Uses Fisher's exact test for win rate and Welch's t-test for average return.

| Field | Type | Description |
|-------|------|-------------|
| variant_a_id | int | Pattern ID of first variant |
| variant_b_id | int | Pattern ID of second variant |
| win_rate_p_value | float | p-value from Fisher's exact test on win rates |
| win_rate_significant | bool | True if win_rate_p_value < (1 - confidence_level) |
| avg_return_p_value | float | p-value from Welch's t-test on per-trade returns |
| avg_return_significant | bool | True if avg_return_p_value < (1 - confidence_level) |
| confidence_level | float | Significance threshold (default 0.95) |

**Notes**:
- Fisher's exact test is used for win rate because trade counts are typically small (10-50).
- Welch's t-test is used for average return because it does not assume equal variance between variants.
- When either variant has fewer than 10 trades, p-values are still computed but flagged with sample size warnings.

### ABTestResult

Complete A/B test output comparing 2 or more pattern variants on identical data.

| Field | Type | Description |
|-------|------|-------------|
| pattern_ids | list[int] | Pattern IDs of all variants tested |
| tickers | list[str] | Tickers used across all variants |
| date_range_start | str | Backtest period start (YYYY-MM-DD) |
| date_range_end | str | Backtest period end (YYYY-MM-DD) |
| variant_reports | list[AggregatedBacktestReport] | One AggregatedBacktestReport per variant |
| comparisons | list[PairwiseComparison] | All pairwise statistical comparisons |
| best_variant_id | int | Pattern ID of the best-performing variant |
| best_is_significant | bool | True if the best variant is significantly better than the next best |
| sample_size_warnings | list[str] | Warnings for variants with insufficient trade counts |

**Notes**:
- For N variants, there are N*(N-1)/2 pairwise comparisons.
- `best_variant_id` is determined by highest win rate. Ties broken by highest avg_return_pct.
- `best_is_significant` reflects whether the best variant is significantly better than the second-best on at least one metric (win rate or avg return).
- `sample_size_warnings` includes a warning for each variant with fewer than 10 trades.

## Persistence

No new database tables are required. All new entities exist in-memory as Pydantic models during computation. Underlying backtest results for each variant continue to be saved via the existing `save_backtest_result()` function in the backtest_result and backtest_trade tables.

## Relationships

```
Pattern 1──* AggregatedBacktestReport (in-memory, via pattern_id)
AggregatedBacktestReport 1──* TickerBreakdown (in-memory, embedded)
AggregatedBacktestReport 1──1 BacktestReport (in-memory, combined_report)

ABTestResult 1──* AggregatedBacktestReport (in-memory, variant_reports)
ABTestResult 1──* PairwiseComparison (in-memory, comparisons)
```
