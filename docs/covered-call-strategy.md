# Covered Call Strategy — "The Old People Income Play"

**Date**: 2026-03-08
**Context**: Jordan mentioned a common strategy where you own shares (e.g., from RSUs) and sell call options against them to generate income. "Old people do it all the time."

---

## What Is a Covered Call?

A covered call is a two-part position:

1. **Own 100+ shares** of a stock (from RSUs, long-term hold, etc.)
2. **Sell a call option** against those shares — you collect premium upfront

The word "covered" means you own the underlying shares, so if the option buyer exercises, you just hand over shares you already have. No naked risk.

### How You Make Money

| Scenario | What Happens | Your P&L |
|----------|-------------|----------|
| Stock stays flat | Option expires worthless | **Keep the premium** (free income) |
| Stock drops a little | Option expires worthless | Keep premium, but lose some stock value |
| Stock goes up past strike | Shares get "called away" at strike price | Keep premium + sell shares at strike |
| Stock drops a lot | Option expires worthless | Keep premium, but stock losses hurt |

### The Tradeoff

You're giving up upside potential in exchange for guaranteed income. If the stock rockets 20%, you miss the gains above your strike — your shares get called away at the lower strike price. But you still profited (strike - entry + premium).

### Why RSU Holders Love It

- You already own the shares (from employer RSU grants)
- You're probably planning to hold them anyway
- Selling calls generates income on shares that would otherwise just sit there
- If shares get called away, you were going to sell eventually anyway
- Common in tech/pharma where employees accumulate large RSU positions

### Real Example

Jordan (or a client) has 500 shares of ABBV at $180 (from RSUs or long-term hold):

1. Sell 5 call contracts (each = 100 shares) at $190 strike, 30 days out
2. Collect ~$3.50/share premium = **$1,750 income**
3. If ABBV stays below $190 in 30 days → keep $1,750 + keep shares → do it again next month
4. If ABBV goes above $190 → shares called away at $190 → you made $10/share gain + $3.50 premium = $13.50/share total
5. If ABBV drops to $170 → keep $1,750 premium, but shares lost $5,000 in value → net loss $3,250

The strategy works best on stocks with moderate volatility — enough premium to be worth selling, but not so volatile that big drops wipe out the income.

---

## Typical Parameters

| Parameter | Conservative | Moderate | Aggressive |
|-----------|-------------|----------|------------|
| Strike distance (OTM) | 5-10% above current | 3-5% above | 1-2% above (ATM) |
| Expiration | 30-45 days | 14-30 days | 7-14 days (weeklies) |
| Expected premium yield | 1-2% per month | 2-4% per month | 4-8% per month |
| Assignment risk | Low | Medium | High |

**Conservative** = low premium but rarely get called away
**Aggressive** = high premium but shares get called away often

---

## Pattern Lab Support — Fully Implemented

All four user stories are implemented in feature 012-covered-call-strategy:

### US1: Describe a Covered Call
```bash
finance-agent pattern describe "I own 500 shares of ABBV. Sell monthly calls 5% out of the money, close at 50% profit or roll at 21 days to expiration"
```
- Parser recognizes covered call keywords (`sell calls`, `write calls`, `covered call`)
- Sets `action_type` to `sell_call` with appropriate defaults
- Displays formatted two-leg position summary (stock + call sale)
- Warns on naked call descriptions

### US2: Backtest a Covered Call
```bash
finance-agent pattern backtest <id> --start 2024-01-01 --end 2025-12-31 --tickers ABBV --shares 500
```
- Monthly cycle simulation using Black-Scholes premium estimation
- Historical volatility calculation (20-day lookback, annualized)
- Assignment, early close, roll, and expiration outcomes
- Buy-and-hold comparison and capped upside cost tracking
- Month-by-month income breakdown

### US3: Paper Trade a Covered Call
```bash
finance-agent pattern paper-trade <id> --tickers ABBV --shares 500
```
- Alpaca option chain lookup for real strike/expiration matching
- Sell-to-open order submission via Alpaca paper trading
- Roll detection at DTE threshold (proposes closing and rolling)
- Assignment detection near expiration
- Falls back to estimated premium when option chain is unavailable

### US4: Compare Covered Call Parameters
```bash
finance-agent pattern compare <id1> <id2> <id3>
```
- Side-by-side comparison of covered call-specific metrics
- Annualized yield, assignment frequency, avg premium, capped upside cost
- Outcome breakdown (expired, closed early, rolled, assigned)

### Technical Details
- **Premium Estimation**: Black-Scholes via `math.erf` (no scipy), 15% IV premium over realized vol
- **Cycle Model**: Monthly cycles with configurable expiration, strike distance, profit target, roll threshold
- **Storage**: `covered_call_cycle` table with per-cycle tracking, `get_covered_call_summary()` for aggregates
- **Audit Logging**: Events for described, backtested, sold, rolled, assigned, expired

---

## Jordan's Use Case

Jordan sees clients (and himself) sitting on RSU positions doing nothing. The covered call pattern would:

1. **Describe**: "I own 500 shares of ABBV. Sell monthly calls 5% out of the money, close at 50% profit or roll at 21 days to expiration"
2. **Backtest**: Run against ABBV's 2-year price history to see monthly premium income vs assignment frequency
3. **Paper Trade**: Monitor ABBV, propose selling calls when conditions are right, track income generated

This is a **Track 1** personal investing feature. For advising clients on covered calls, that would be **Track 2** productivity tooling (generating reports, comparing strike strategies, etc.).

---

## Bottom Line

Covered calls are the opposite of the pharma dip pattern:
- **Pharma dip** = speculative, directional bet, high risk/reward
- **Covered call** = income generation, neutral-to-bullish, consistent small gains

Both belong in Pattern Lab, but covered calls need the backtest engine to understand selling premium instead of just buying and selling directionally. This is a natural next feature after the current Pattern Lab MVP is validated.
