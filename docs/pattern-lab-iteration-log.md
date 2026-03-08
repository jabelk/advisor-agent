# Pattern Lab Iteration Log

**Date**: 2026-03-08
**Objective**: Iterate on Jordan's pharma dip pattern to find a viable strategy for paper trading
**Tickers tested**: MRNA, PFE, ABBV, JNJ, LLY, AMGN, GILD, BMY, REGN, VRTX, BIIB, AZN

---

## Pattern #1: Original (Baseline)

**Description**: "When pharma stocks spike on news, buy calls on the 2% dip within 2 days"

| Metric | Value |
|--------|-------|
| Backtest period | 2025-01-01 to 2025-12-31 |
| Tickers | 5 (MRNA, PFE, ABBV, JNJ, LLY) |
| Trades | 16 |
| Win rate | 37.5% |
| Avg return | 1.38% |
| Total return | 22.15% |
| Max drawdown | 200.00% |
| Sharpe | 0.02 |

**Problem**: Only 5 tickers over 1 year = too few trades. Max drawdown of 200% means options leverage is destroying capital on losers. Default 10% stop loss on leveraged options is too wide.

---

## Pattern #2: Tighter Stops, More Quantitative

**Changes from #1**:
- Made trigger fully quantitative (5%+ spike, 1.5x volume) — backtestable without news data
- Tightened stop loss from 10% to 5%
- Lowered profit target from 20% to 15%
- Added 10-day max hold to prevent time decay eating options value

**Description**: "When pharma or biotech stocks spike 5% or more on high volume, buy ATM calls on a 2% pullback within 2 days. Exit at 15% profit or 5% stop loss. Hold max 10 trading days."

| Metric | Value |
|--------|-------|
| Backtest period | 2024-01-01 to 2025-12-31 |
| Tickers | 12 |
| Trades | 34 |
| Win rate | 47.1% |
| Avg return | -0.84% |
| Total return | -28.51% |
| Max drawdown | 173.73% |
| Sharpe | -0.03 |

**Result**: More trades (34 — near statistical significance), better win rate (47%), but still net negative. The 5% stop loss on leveraged options still triggers too often. Regime analysis shows clear breakdown periods (May-Dec 2024 was ugly: 33% win rate, -9.56% avg). The pattern works in some market regimes but gets killed in others.

**Key insight**: Options leverage turns a mediocre edge into a losing strategy. When the underlying moves against you even slightly, the leveraged loss overwhelms the wins.

---

## Pattern #3: Shares Instead of Options (Winner)

**Changes from #2**:
- **Switched from options to shares** — removes leverage risk
- Tightened stop loss to 3% (appropriate for unleveraged)
- Reasonable 8% profit target
- Required 2x volume (stricter than 1.5x) to filter noise
- Wider entry: 3% pullback within 3 days (more opportunities)
- 15-day max hold

**Description**: "When pharma or biotech stocks spike 5% or more on 2x average volume, buy shares on a 3% pullback within 3 days. Take profit at 8%, stop loss at 3%. Max hold 15 days."

| Metric | Value |
|--------|-------|
| Backtest period | 2024-01-01 to 2025-12-31 |
| Tickers | 12 |
| Trades | 16 |
| Win rate | 37.5% |
| Avg return | 0.64% |
| Total return | 10.24% |
| Max drawdown | **12.00%** |
| Sharpe | 0.12 |

**Result**: The best risk-adjusted strategy. Max drawdown dropped from 200% to 12% — that's a massive improvement. Positive total return (10.24%) and positive Sharpe. The stricter volume filter (2x) reduced trade count but the trades that triggered were higher quality. Only 16 trades (still below 30 threshold) but the fundamentals are sound.

**Why this works better**: Removing options leverage is the single biggest improvement. A 3% stop loss on shares means you lose 3% of position value. A 5% stop loss on leveraged options means you lose 25%+ of position value. The math is brutal with options on a pattern that only wins 37-47% of the time.

---

## Pattern #4: Deep Pullback, Wide Window (Loser)

**Changes from #2**:
- Raised spike threshold to 7% (much rarer events)
- Required 4% pullback within 5 days
- 45-day option expiration (more time, less decay)
- 8% stop loss, 25% profit target, 20-day max hold

**Description**: "When pharma or biotech stocks spike 7% or more on 2x average volume, buy ATM calls on a 4% pullback within 5 days. Take profit at 25%, stop loss at 8%. Hold max 20 days. Use 45-day expiration."

| Metric | Value |
|--------|-------|
| Backtest period | 2024-01-01 to 2025-12-31 |
| Tickers | 12 |
| Trades | 8 |
| Win rate | 12.5% |
| Avg return | -17.82% |
| Total return | -142.56% |
| Max drawdown | 151.78% |
| Sharpe | -1.31 |

**Result**: Disaster. The 7% spike threshold was too restrictive — only 8 trades in 2 years. And requiring a 4% pullback after a massive spike often means you're catching a falling knife, not a dip. The few trades that triggered mostly kept falling.

**Lesson**: Bigger spike ≠ better opportunity. A 7% spike in pharma often means binary event (FDA decision, trial data) where the pullback is the market correcting an overreaction, not a buying opportunity.

---

## Side-by-Side Comparison

| Metric | #1 Original | #2 Tight Stops | #3 Shares | #4 Deep Pull |
|--------|------------|----------------|-----------|-------------|
| Win Rate | 37.5% | 47.1% | 37.5% | 12.5% |
| Avg Return | 1.38% | -0.84% | **0.64%** | -17.82% |
| Total Return | 22.15% | -28.51% | **10.24%** | -142.56% |
| Max Drawdown | 200.0% | 173.7% | **12.0%** | 151.8% |
| Sharpe | 0.02 | -0.03 | **0.12** | -1.31 |
| Trades | 16 | 34 | 16 | 8 |

---

## Conclusions

1. **Pattern #3 (shares) is the winner** for paper trading. Best risk-adjusted returns, manageable drawdown, positive expectancy.

2. **Options leverage kills this strategy**. The win rate (37-47%) isn't high enough to overcome leveraged losses. You need >55% win rate with favorable risk:reward to make options work on this kind of pattern.

3. **Volume confirmation matters**. The 2x average volume filter in #3 produced better quality signals than the 1.5x in #2.

4. **Bigger spikes aren't better** for dip-buying. The 5% threshold hits the sweet spot — big enough to signal genuine interest, small enough to happen regularly.

5. **Time stops are essential**. Without a max hold period, you sit in dead trades bleeding time decay (options) or opportunity cost (shares).

## Next Steps

- **Paper trade Pattern #3** with live Alpaca monitoring to validate in real time
- Once we have 30+ paper trades, reassess win rate and adjust parameters
- Consider adding a momentum filter (only buy dip if RSI < 40) in a future iteration
- Jordan should watch the regime analysis — if the pattern enters a "breakdown" period, pause it

## Paper Trading Setup

Pattern #3 has been activated for paper trading against the full pharma/biotech ticker list. Monitor with:
```
uv run finance-agent pattern paper-trade 3 --tickers MRNA,PFE,ABBV,JNJ,LLY,AMGN,GILD,BMY,REGN,VRTX,BIIB,AZN
```
