# Quickstart: Pattern Lab Extensions

**Feature**: 014-pattern-lab-extensions

## What It Does

Pattern Lab Extensions adds three capabilities to the existing Pattern Lab:

1. **Multi-Ticker Aggregation** -- Backtest a pattern across a basket of stocks and see combined stats with per-ticker breakdown.
2. **A/B Testing** -- Compare pattern variants with statistical significance testing to know if differences are real or noise.
3. **Export** -- Save backtest results as markdown reports for offline review and sharing.

## Prerequisites

- Pattern Lab (011) is set up and working
- At least one confirmed pattern exists (run `finance-agent pattern list` to check)
- Alpaca API keys configured (for historical price data)

## Scenario 1: Multi-Ticker Backtest

Test a pharma dip pattern across multiple stocks simultaneously.

```bash
finance-agent pattern backtest 15 --tickers ABBV,MRNA,PFE --start 2024-01-01 --end 2025-12-31
```

**Expected**: A combined report with two sections:

1. **Per-Ticker Breakdown** -- Table showing events, trades, win rate, and average return for each ticker individually.
2. **Combined Aggregate** -- Pooled metrics across all tickers (total events, overall win rate, average return, max drawdown, Sharpe ratio) plus regime analysis on the combined trade set.

Tickers with zero qualifying events still appear in the breakdown with zeroed values. If no events are found across any ticker, the system suggests lowering thresholds or widening the date range.

## Scenario 2: A/B Test Pattern Variants

Create pattern variants with different parameters and compare them statistically.

```bash
# Create variants with different thresholds
finance-agent pattern describe "Pharma dip, 3% spike, buy calls on 1% dip"
finance-agent pattern describe "Pharma dip, 7% spike, buy calls on 3% dip"

# Run A/B test across all variants on the same data
finance-agent pattern ab-test 15 16 17 --tickers ABBV,MRNA --start 2024-01-01 --end 2025-12-31
```

**Expected**: A comparison report with three sections:

1. **Variant Metrics** -- Side-by-side table of each variant's events, trades, win rate, and average return.
2. **Statistical Significance** -- All pairwise comparisons showing p-values for win rate (Fisher's exact test) and average return (Welch's t-test). Marked as `(NS)` for not significant, `(*)` for p < 0.05, or `(**)` for p < 0.01.
3. **Result** -- Best-performing variant identified, with a clear statement about whether the advantage is statistically significant. If sample sizes are small (< 10 trades per variant), a warning recommends collecting more data.

## Scenario 3: Export Results

Export backtest results to a markdown file for offline review.

```bash
finance-agent pattern export 15 --format markdown
```

**Expected**: A file named `pattern-15-backtest-2026-03-08.md` is created in the current directory. The file contains:

- Pattern description and configuration
- Aggregate results table
- Per-ticker breakdown (if multi-ticker backtest)
- Regime analysis table
- Full trade log
- No-entry events

If the file already exists, a numeric suffix is appended (e.g., `pattern-15-backtest-2026-03-08-1.md`).

To export a specific backtest run or to a custom path:

```bash
finance-agent pattern export 15 --backtest-id 42 --output ~/reports/pharma-dip-results.md
```

If no backtest results exist for the pattern, the system returns: `Error: No backtest results found for pattern #15. Run a backtest first.`

## Key Files

| File | Purpose |
|------|---------|
| `src/finance_agent/patterns/models.py` | New Pydantic models: TickerBreakdown, AggregatedBacktestReport, PairwiseComparison, ABTestResult |
| `src/finance_agent/patterns/backtest.py` | Multi-ticker aggregation logic in run_news_dip_backtest |
| `src/finance_agent/patterns/stats.py` | Statistical significance tests (Fisher's exact, Welch's t-test) |
| `src/finance_agent/patterns/export.py` | Markdown report generation |
| `src/finance_agent/cli.py` | New `ab-test` and `export` subcommands, updated `backtest` output |

## Safety

- No trading operations -- this feature is analysis and reporting only.
- All statistical tests include sample size warnings to prevent decisions based on insufficient data.
- Export files contain only backtest results from public market data. No client data is ever included.
- Kill switch from the safety module continues to function normally for any active paper trades.
