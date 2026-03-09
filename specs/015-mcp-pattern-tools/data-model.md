# Data Model: MCP Pattern Lab Tools

**Feature**: 015-mcp-pattern-tools
**Date**: 2026-03-08

## No New Entities

This feature does not introduce new data models. All 3 MCP tools return existing Pydantic models from feature 014:

- `run_backtest` → returns `AggregatedBacktestReport.model_dump()` (from `patterns.models`)
- `run_ab_test` → returns `ABTestResult.model_dump()` (from `patterns.models`)
- `export_backtest` → returns `dict` with `file_path` and `pattern_id`

## Existing Entities Used

### AggregatedBacktestReport (from 014)

Returned by the `run_backtest` tool. Contains:
- `pattern_id`, `date_range_start`, `date_range_end`, `tickers`
- `ticker_breakdowns`: list of per-ticker results (events, trades, win rate, avg return)
- `combined_report`: pooled BacktestReport with aggregate metrics and regime analysis
- `no_entry_events`: events that triggered but had no qualifying entry

### ABTestResult (from 014)

Returned by the `run_ab_test` tool. Contains:
- `pattern_ids`, `tickers`, `date_range_start`, `date_range_end`
- `variant_reports`: one AggregatedBacktestReport per variant
- `comparisons`: pairwise PairwiseComparison objects with p-values
- `best_variant_id`, `best_is_significant`, `sample_size_warnings`

## Persistence

No new database tables. The backtest and A/B test tools write to the existing market data cache (via `fetch_and_cache_bars`) and save backtest results (via `save_backtest_result`). The export tool writes a markdown file to the local filesystem.
