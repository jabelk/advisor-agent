# Quickstart: Pharma News Dip Pattern

**Feature**: 013-pharma-news-dip
**Date**: 2026-03-08

## Scenario 1: Describe and Backtest (P1 — Core Flow)

### Step 1: Describe the pattern

```bash
finance-agent pattern describe "When a pharma company has big news like FDA approval or trial results, the stock spikes 5% or more on heavy volume. Then within 2 days it pulls back at least 2%. Buy call options on the dip, ATM, 30-day expiration. Take profit at 20%, stop loss at 10%. Only healthcare/pharma stocks."
```

**Expected**: Parser returns a RuleSet with:
- trigger_type: qualitative
- trigger_conditions: price_change_pct ≥ 5.0, volume_spike ≥ 1.5
- entry_signal: pullback_pct 2.0, window_days 2
- action: buy_call, ATM, 30d expiration
- exit_criteria: 20% profit, 10% stop loss
- sector_filter: healthcare

### Step 2: Backtest with automatic event detection

```bash
finance-agent pattern backtest 15 --tickers ABBV --start 2024-01-01 --end 2025-12-31
```

**Expected**: System detects price spikes ≥ 5% on ≥ 1.5x volume, simulates call option purchases on subsequent dips, reports win/loss per trade plus aggregate statistics and regime analysis.

### Step 3: Backtest with manual events

```bash
finance-agent pattern backtest 15 --tickers MRNA --start 2024-01-01 --end 2025-12-31 --events "2024-08-15,2024-11-02,2025-02-10"
```

**Expected**: System uses only the 3 provided dates as triggers. Reports results for those specific events.

### Step 4: Backtest with events file

Create `pharma_events.csv`:
```
2024-08-15,MRNA FDA approval
2024-11-02,MRNA Phase 3 results
2025-02-10,MRNA EUA expansion
```

```bash
finance-agent pattern backtest 15 --tickers MRNA --start 2024-01-01 --end 2025-12-31 --events-file pharma_events.csv
```

**Expected**: Same as above but reads dates from file, labels appear in trade log output.

---

## Scenario 2: Regime Analysis (P2)

### Step 1: Run long-range backtest

```bash
finance-agent pattern backtest 15 --tickers ABBV --start 2023-01-01 --end 2025-12-31
```

**Expected**: With 3 years of data and ≥ 10 trades, regime analysis runs and identifies distinct periods:
- At least one "strong" period and one "weak" or "breakdown" period
- Each regime shows: date range, win rate, average return, trade count, label

### Step 2: Verify sample size warnings

```bash
finance-agent pattern backtest 15 --tickers ABBV --start 2025-06-01 --end 2025-12-31
```

**Expected**: If < 10 trades detected, system shows "regime analysis skipped" warning. If < 5 trades, shows "results may not be statistically meaningful" warning.

---

## Scenario 3: Paper Trade (P3)

### Step 1: Start paper trading

```bash
finance-agent pattern paper-trade 15 --tickers ABBV,MRNA,PFE,BMY
```

**Expected**: Monitor starts, polling every 5 minutes. When a pharma stock spikes ≥ 5% on high volume, Jordan gets a trigger confirmation prompt requiring `y/n/skip`.

### Step 2: Verify auto-approve is blocked

```bash
finance-agent pattern paper-trade 15 --auto-approve --tickers ABBV
```

**Expected**: Error message: "--auto-approve is not allowed for qualitative patterns"

### Step 3: Trigger confirmation flow

When ABBV spikes 6% on 2x volume:
1. Monitor displays trigger details (price change, volume multiple)
2. Jordan types `y` to confirm
3. System monitors for 2% dip within 2 days
4. If dip occurs: proposes buy_call with strike/expiration/premium
5. Jordan approves or rejects the trade
6. If approved: paper position opens
7. System monitors profit target / stop loss / max hold

---

## Scenario 4: Compare Variants (P1 extension)

### Step 1: Create pattern variants

```bash
finance-agent pattern describe "Pharma dip pattern, 3% spike threshold, buy calls on 1% dip"
finance-agent pattern describe "Pharma dip pattern, 7% spike threshold, buy calls on 3% dip"
```

### Step 2: Backtest all variants

```bash
finance-agent pattern backtest 15 --tickers ABBV --start 2024-01-01 --end 2025-12-31
finance-agent pattern backtest 16 --tickers ABBV --start 2024-01-01 --end 2025-12-31
finance-agent pattern backtest 17 --tickers ABBV --start 2024-01-01 --end 2025-12-31
```

### Step 3: Compare

```bash
finance-agent pattern compare 15 16 17
```

**Expected**: Side-by-side comparison showing events detected, trades entered, win rate, average return, and regime overlay for each variant.

---

## Edge Case Scenarios

### Consecutive spike days (cooldown)

Backtest ABBV where Mon = +6%, Tue = +8%. System should detect Monday as the trigger and skip Tuesday (cooldown active). Only one trade should result from this two-day event.

### No qualifying events

```bash
finance-agent pattern backtest 15 --tickers JNJ --start 2025-01-01 --end 2025-06-30 --spike-threshold 15
```

**Expected**: "No qualifying events detected. Try: lower --spike-threshold, wider date range, or provide --events manually."

### Trigger with no entry (no dip)

Backtest a stock where a 5%+ spike occurred but the stock continued higher (no pullback within 2 days). System should report this as "trigger fired, no entry" in the no-entry events section.

### Gap handling

Stock gaps down 5% overnight after a spike day. System uses the opening price (not the theoretical 2% pullback level) as the entry price.
