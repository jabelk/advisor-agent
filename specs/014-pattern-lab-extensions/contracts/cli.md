# CLI Contract: Pattern Lab Extensions

**Feature**: 014-pattern-lab-extensions
**Date**: 2026-03-08

## Modified Commands

### pattern backtest (multi-ticker output)

The existing `pattern backtest` command already accepts `--tickers`. This feature changes the **output format** when multiple tickers are provided, adding a per-ticker breakdown table above the combined aggregate report.

```
finance-agent pattern backtest <pattern_id> --tickers TICKER1,TICKER2[,...] [--start YYYY-MM-DD] [--end YYYY-MM-DD]
```

**Arguments** (unchanged from 011):
- `pattern_id` (required): ID of a confirmed pattern
- `--tickers` (required for multi-ticker): Comma-separated list of tickers
- `--start` (optional): Start date for backtest (default: 1 year ago)
- `--end` (optional): End date for backtest (default: today)

**Output** (multi-ticker format):

```
===============================================
  NEWS DIP BACKTEST: Pattern #15 -- ABBV,MRNA,PFE
  2024-01-01 -> 2025-12-31
===============================================

  --- PER-TICKER BREAKDOWN ----------------------
  Ticker  Events  Trades  Win Rate  Avg Return
  ABBV    8       6       66.7%     +14.2%
  MRNA    5       4       50.0%     +8.3%
  PFE     3       2       50.0%     +5.1%

  --- COMBINED AGGREGATE ------------------------
  Total Events:     16
  Total Trades:     12
  Win Rate:         58.3% (7/12)
  Avg Return:       +10.8%
  Total Return:     +129.6%
  Max Drawdown:     -8.2%
  Sharpe Ratio:     1.42

  --- REGIME ANALYSIS ---------------------------
  2024-01 to 2024-06: Strong (win rate 75.0%, avg +15.1%, 4 trades)
  2024-07 to 2024-12: Weak (win rate 33.3%, avg +2.1%, 6 trades)
  2025-01 to 2025-12: Moderate (win rate 100%, avg +18.5%, 2 trades)

  --- NO-ENTRY EVENTS ---------------------------
  ABBV  2024-03-15  Triggered but pullback < 2%
  PFE   2024-08-22  Triggered but no pullback within window

  ! Sample size warning: 12 trades may be insufficient
    for reliable statistical conclusions.
===============================================
```

**Behavior changes**:
- Single ticker: output format is unchanged from 011.
- Multiple tickers: output uses the new format above with per-ticker breakdown.
- Tickers with zero events appear in the breakdown with all-zero values.
- Tickers with no available price data appear as `(no data)` in the Events column.
- If zero events across all tickers: `No qualifying events detected across any ticker. Consider lowering thresholds or widening the date range.`

---

## New Commands

### pattern ab-test

Run an A/B test comparing 2 or more pattern variants on identical data with statistical significance testing.

```
finance-agent pattern ab-test <id1> <id2> [id3...] --tickers TICKER1,TICKER2[,...] [--start YYYY-MM-DD] [--end YYYY-MM-DD]
```

**Arguments**:
- `id1 id2 [id3...]` (required): Two or more pattern IDs to compare
- `--tickers` (required): Comma-separated list of tickers to test against
- `--start` (optional): Start date for backtest (default: 1 year ago)
- `--end` (optional): End date for backtest (default: today)

**Output**:

```
===============================================
  A/B TEST COMPARISON
  2024-01-01 -> 2025-12-31 | Tickers: ABBV,MRNA
===============================================

  --- VARIANT METRICS ---------------------------
  ID   Name              Events  Trades  Win%   Avg Ret
  15   Pharma Dip 5%     14      11      63.6%  +12.3%
  16   Pharma Dip 3%     22      18      55.6%  +8.1%

  --- STATISTICAL SIGNIFICANCE ------------------
  Comparison         Win Rate         Avg Return
  #15 vs #16         p=0.42 (NS)      p=0.18 (NS)

  --- RESULT ------------------------------------
  Best variant: #15 (Pharma Dip 5%)
  Advantage: Not statistically significant (p > 0.05)
  ! Consider collecting more data before choosing.
===============================================
```

**Statistical significance notation**:
- `(NS)` = Not Significant (p >= 0.05)
- `(*)` = Significant (p < 0.05)
- `(**)` = Highly Significant (p < 0.01)

**Multi-variant output** (3+ variants):

When 3 or more variants are compared, all pairwise comparisons are listed:

```
  --- STATISTICAL SIGNIFICANCE ------------------
  Comparison         Win Rate         Avg Return
  #15 vs #16         p=0.42 (NS)      p=0.18 (NS)
  #15 vs #17         p=0.03 (*)       p=0.01 (**)
  #16 vs #17         p=0.11 (NS)      p=0.09 (NS)
```

**Error cases**:
- Fewer than 2 pattern IDs: `Error: A/B test requires at least 2 pattern IDs.`
- Invalid pattern ID: `Error: Pattern #N not found.`
- Pattern in draft status: `Error: Pattern #N is in draft status. Confirm the pattern first.`
- No tickers specified: `Error: --tickers is required for A/B testing.`

**Sample size warnings** (appended to RESULT section):
- Variant with < 10 trades: `! Pattern #N has only M trades. Results may not be statistically reliable.`
- Unbalanced samples: `! Trade counts differ significantly across variants (N vs M). Comparisons may be unreliable.`

---

### pattern export

Export backtest or A/B test results to a formatted markdown file.

```
finance-agent pattern export <pattern_id> [--format markdown] [--output PATH] [--backtest-id ID]
```

**Arguments**:
- `pattern_id` (required): Pattern ID to export results for
- `--format` (optional): Output format. Only `markdown` is supported. Default: `markdown`
- `--output` (optional): File path for the export. Default: current directory with auto-generated filename
- `--backtest-id` (optional): Specific backtest result ID to export. Default: most recent backtest

**Default filename format**: `pattern-{id}-backtest-{date}.md` where `{date}` is today's date in YYYY-MM-DD format.

**Output** (to terminal):

```
Exported backtest results for pattern #15 to pattern-15-backtest-2026-03-08.md
```

**Generated markdown file structure**:

```markdown
# Backtest Report: Pattern #15 -- Pharma News Dip

**Generated**: 2026-03-08
**Pattern**: Pharma News Dip (#15)
**Date Range**: 2024-01-01 to 2025-12-31
**Tickers**: ABBV, MRNA, PFE

## Pattern Description

When a pharma company has major positive news, the stock spikes 5%+
in a day. Within 1-2 trading days it pulls back at least 2%. Buy call
options on the pullback.

## Aggregate Results

| Metric | Value |
|--------|-------|
| Total Events | 16 |
| Total Trades | 12 |
| Win Rate | 58.3% (7/12) |
| Avg Return | +10.8% |
| Total Return | +129.6% |
| Max Drawdown | -8.2% |
| Sharpe Ratio | 1.42 |

## Per-Ticker Breakdown

| Ticker | Events | Trades | Win Rate | Avg Return |
|--------|--------|--------|----------|------------|
| ABBV | 8 | 6 | 66.7% | +14.2% |
| MRNA | 5 | 4 | 50.0% | +8.3% |
| PFE | 3 | 2 | 50.0% | +5.1% |

## Regime Analysis

| Period | Strength | Win Rate | Avg Return | Trades |
|--------|----------|----------|------------|--------|
| 2024-01 to 2024-06 | Strong | 75.0% | +15.1% | 4 |
| 2024-07 to 2024-12 | Weak | 33.3% | +2.1% | 6 |
| 2025-01 to 2025-12 | Moderate | 100% | +18.5% | 2 |

## Trade Log

| # | Ticker | Trigger | Entry | Exit | Return |
|---|--------|---------|-------|------|--------|
| 1 | ABBV | 2024-01-15 | 2024-01-17 @ $142.50 | 2024-02-14 @ $161.30 | +13.2% |
| 2 | MRNA | 2024-02-03 | 2024-02-05 @ $98.20 | 2024-03-01 @ $108.50 | +10.5% |
| ... | | | | | |

## No-Entry Events

| Ticker | Date | Reason |
|--------|------|--------|
| ABBV | 2024-03-15 | Triggered but pullback < 2% |
| PFE | 2024-08-22 | Triggered but no pullback within window |
```

**Error cases**:
- No backtest results: `Error: No backtest results found for pattern #N. Run a backtest first.`
- Invalid pattern ID: `Error: Pattern #N not found.`
- Invalid backtest ID: `Error: Backtest result #N not found for pattern #M.`
- Unsupported format: `Error: Unsupported format 'X'. Supported formats: markdown`
- File exists at output path: append numeric suffix (e.g., `pattern-15-backtest-2026-03-08-1.md`, `pattern-15-backtest-2026-03-08-2.md`)

---

## MCP Tools (Future)

No new MCP tools in this feature. The existing `get_backtest_results` tool returns data that now includes multi-ticker breakdowns when available. New MCP tools for A/B testing and export may be added in a follow-up feature.
