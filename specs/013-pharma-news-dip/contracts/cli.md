# CLI Contracts: Pharma News Dip Pattern

**Feature**: 013-pharma-news-dip
**Date**: 2026-03-08

## Modified Commands

### `finance-agent pattern backtest` (extended)

New flags for event-driven backtesting:

```
finance-agent pattern backtest <pattern_id>
  [--start YYYY-MM-DD]           # Default: 2 years ago
  [--end YYYY-MM-DD]             # Default: today
  [--tickers TICKER1,TICKER2]    # Default: watchlist
  [--events "DATE1,DATE2,..."]   # Manual event dates (comma-separated)
  [--events-file PATH]          # File with event dates (one per line)
  [--spike-threshold PCT]       # Override spike % (default: from pattern)
  [--volume-multiple X]         # Override volume multiplier (default: from pattern)
```

**Behavior when `--events` or `--events-file` provided**:
- Skips automatic event detection entirely
- Uses only the provided dates as trigger points
- Validates dates are within the start/end range
- Reports which provided dates had no price data available

**`--events-file` format**:
```
# Comments start with #
2024-08-15,FDA approval
2024-11-02,Phase 3 trial results
2025-01-20
```
One date per line. Optional comma-separated label after the date. Blank lines and `#` comments are ignored.

### Output: News Dip Backtest Report

```
═══════════════════════════════════════════════════
  NEWS DIP BACKTEST: Pharma Dip – ABBV
  2024-01-01 → 2025-12-31
═══════════════════════════════════════════════════

  Events Detected:  14  (source: price-action proxy)
  Spike Threshold:  5.0%  |  Volume Filter: 1.5x avg
  Trades Entered:   11  (3 events had no qualifying dip)

  ─── AGGREGATE ──────────────────────────────────
  Win Rate:     63.6%  (7W / 4L)
  Avg Return:   +12.3%
  Total Return: +135.4%
  Max Drawdown: -18.2%
  Sharpe Ratio: 1.42

  ─── REGIME ANALYSIS ───────────────────────────
  ⚠ Regime detection requires 10+ trades

  Period              Label       Trades  Win Rate  Avg Return
  Jan 2024 – Jun 2024  strong      5       80.0%    +18.1%
  Jul 2024 – Dec 2024  weak        4       50.0%    +4.2%
  Jan 2025 – Jun 2025  breakdown   2       0.0%     -12.5%

  ─── TRADE LOG ──────────────────────────────────
  #   Trigger     Entry       Exit        Return  Action
  1   2024-01-15  2024-01-17  2024-02-14  +22.3%  buy_call (ATM, 30d)
  2   2024-02-28  2024-03-01  2024-03-15  +8.1%   buy_call (ATM, 30d)
  ...

  ─── NO-ENTRY EVENTS ────────────────────────────
  Date        Spike   Volume   Reason
  2024-04-12  +6.2%   2.1x    No 2% pullback within 2-day window
  2024-09-03  +5.8%   1.7x    No 2% pullback within 2-day window
  2024-11-15  +7.1%   1.9x    Full reversal (crashed below entry)
═══════════════════════════════════════════════════
```

### `finance-agent pattern paper-trade` (extended)

Qualitative trigger confirmation flow:

```
finance-agent pattern paper-trade <pattern_id>
  [--tickers TICKER1,TICKER2]
  [--auto-approve]              # NOT allowed for qualitative patterns
```

**Behavior for qualitative patterns**:
- If `--auto-approve` is passed with a qualitative pattern: error message and exit
- When a spike is detected: display event details and prompt for confirmation
- Jordan must type `y` to confirm the trigger is real news (not noise)
- After confirmation: system monitors for dip entry as normal

**Trigger confirmation prompt**:
```
═══════════════════════════════════════════════════
  ⚡ TRIGGER DETECTED: MRNA
  Price: $145.20 → $153.80 (+5.9%)
  Volume: 28.4M (2.1x average)
  Date: 2026-03-08

  This looks like a significant pharma event.
  Confirm this is real news? (y/n/skip):
═══════════════════════════════════════════════════
```

- `y`: Confirm — start monitoring for dip entry
- `n`: Reject — mark as false positive, resume monitoring
- `skip`: Skip this event, continue monitoring for next

### `finance-agent pattern compare` (extended)

For news dip patterns (qualitative + buy_call), show additional columns:

```
═══════════════════════════════════════════════════
  PATTERN COMPARISON
═══════════════════════════════════════════════════

  ID   Name              Events  Trades  Win%   Avg Ret  Regimes
  12   Pharma Dip 5%     14      11      63.6%  +12.3%   2 strong, 1 breakdown
  13   Pharma Dip 3%     22      18      55.6%  +8.1%    1 strong, 2 weak
  14   Pharma Dip 7%     8       7       71.4%  +16.2%   1 strong, 1 weak

  ─── REGIME OVERLAY ─────────────────────────────
  Period              ID 12     ID 13     ID 14
  Jan–Jun 2024        strong    strong    strong
  Jul–Dec 2024        weak      weak      weak
  Jan–Jun 2025        breakdown weak      —
═══════════════════════════════════════════════════
```

## New Error Cases

| Scenario | Error Message |
|----------|---------------|
| `--auto-approve` with qualitative pattern | "Error: --auto-approve is not allowed for qualitative patterns (safety requirement). Qualitative triggers require human confirmation." |
| `--events` with invalid date format | "Error: Invalid date format '{date}'. Expected YYYY-MM-DD." |
| `--events-file` not found | "Error: Events file not found: {path}" |
| `--events-file` with no valid dates | "Error: No valid dates found in {path}. Expected one date per line (YYYY-MM-DD)." |
| `--events` date outside backtest range | "Warning: Event date {date} is outside backtest range ({start} to {end}). Skipping." |
| Zero events detected | "No qualifying events detected. Try: lower --spike-threshold, wider date range, or provide --events manually." |
| Backtest with < 5 trades | "Warning: Only {n} trades — results may not be statistically meaningful." |
| Regime analysis with < 10 trades | "Warning: Fewer than 10 trades — regime analysis skipped (insufficient sample)." |
