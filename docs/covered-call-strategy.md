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

## Pattern Lab Support Status

### What Works Today

- `ActionType.SELL_CALL` already exists in the models
- Pattern parser can understand "sell calls" descriptions
- Storage layer supports `option_details_json` for tracking strikes/premiums
- Audit logging covers all paper trade events

### What Needs Enhancement

The current backtest engine and paper trading executor are designed for **directional trades** (buy low, sell high). Covered calls need different logic:

**Backtest Changes Needed**:
- `_estimate_options_return()` currently treats all calls as long (buy) calls. Selling calls inverts the P&L: you profit when the stock stays flat or drops slightly
- Need to model premium collection + assignment risk instead of just leveraged returns
- Simplified covered call P&L per trade:
  - If stock < strike at expiration: `return = premium_collected / stock_entry_price * 100`
  - If stock > strike at expiration: `return = (premium_collected + (strike - entry_price)) / entry_price * 100`

**Paper Trading Changes Needed**:
- Alpaca supports options orders but executor currently only submits stock market orders
- Need sell-to-open order type for the short call leg
- Need to track two-leg position (long stock + short call) as a unit
- Exit conditions differ: expiration, early buyback, assignment

### Suggested Implementation (Future)

1. Add `CoveredCallStrategy` class that manages the two-leg position
2. Modify backtest to simulate premium decay and assignment
3. Add option chain lookup via Alpaca to find appropriate strikes
4. Trigger: stock in portfolio + IV rank above threshold (good premium)
5. Entry: sell call at X% OTM with 30-45 DTE
6. Exit: buy back at 50% profit, roll at 21 DTE, or let expire/assign

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
