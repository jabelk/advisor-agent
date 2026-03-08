# Research: Covered Call Income Strategy

## R1: Option Premium Estimation Without Historical Option Chain Data

**Decision**: Use simplified Black-Scholes formula with historical volatility calculated from price bars.

**Rationale**: Alpaca provides real-time option chain data (via `OptionHistoricalDataClient.get_option_chain()`) but not historical option snapshots. For backtesting covered calls over 2+ years, we need to estimate what premiums would have been at each monthly cycle start. Historical volatility from stock bars is the standard proxy.

**Approach**:
- Calculate 20-day historical volatility (annualized standard deviation of log returns)
- Apply a 15% IV premium multiplier (implied volatility typically exceeds realized volatility)
- Feed into Black-Scholes call pricing formula: `C = S * N(d1) - K * e^(-rT) * N(d2)`
- Adjust for OTM strike distance (premium decreases ~2-3% per 1% OTM)
- Use scipy.stats.norm.cdf for cumulative normal distribution (already available via Python stdlib math + approximation, or add scipy)

**Alternatives considered**:
- Lookup historical IV from third-party data (Cboe, OptionMetrics) — too expensive, requires subscription
- Simple percentage-of-stock-price heuristic (e.g., "ATM 30-day call = ~3% of stock price") — too crude, doesn't account for volatility differences
- Monte Carlo simulation — overkill for backtesting estimate, adds complexity without meaningful accuracy gain

**Accuracy expectation**: Within 10-20% of actual option premium for ATM/near-OTM calls. Sufficient for comparing covered call strategies against each other and against buy-and-hold, but not for precise P&L prediction.

## R2: Alpaca Options Trading API

**Decision**: Use alpaca-py 0.43.2's built-in options support for paper trading covered calls.

**Rationale**: Full options infrastructure is already installed and available:
- `PositionIntent.SELL_TO_OPEN` — for selling the call leg
- `PositionIntent.SELL_TO_CLOSE` / `BUY_TO_CLOSE` — for closing positions
- `OrderClass.MLEG` — for multi-leg orders (covered call = 2 legs)
- `OptionLegRequest` — defines each leg with symbol, side, position_intent
- `OptionHistoricalDataClient.get_option_chain()` — real-time option chain for strike selection
- `OptionContract` model — strike, expiry, type, open interest

**Paper trading flow**:
1. Use `get_option_chain()` to find the appropriate call contract (correct strike, expiration)
2. Build `OptionLegRequest` with `side=SELL`, `position_intent=SELL_TO_OPEN`
3. Submit via `MarketOrderRequest` or `LimitOrderRequest` with `order_class=MLEG`
4. Monitor position; at expiration or roll window, close via `BUY_TO_CLOSE`

**Alternatives considered**:
- Simulate options orders without actual Alpaca submission — less realistic, misses real-world execution issues
- Use a separate options broker — unnecessary, Alpaca handles it

## R3: Covered Call Backtest Cycle Model

**Decision**: Model backtests as repeating monthly cycles rather than single entry-exit trades.

**Rationale**: A covered call campaign is fundamentally different from a directional trade:
- Directional: trigger → entry → exit (one-time)
- Covered call: own shares → sell call monthly → collect premium → repeat

Each cycle needs:
1. **Entry**: Sell call at cycle start (first trading day of month or nearest Friday for monthly expiration)
2. **Track**: Monitor stock price vs strike through expiration
3. **Exit**: One of three outcomes:
   - Option expires worthless → keep premium, keep shares → start next cycle
   - Hit profit target (e.g., 50% of premium) → buy back call early → start next cycle
   - Assignment at expiration → shares sold at strike → campaign ends (or repurchase shares)
4. **Roll**: If approaching expiration and want to continue, close current call and open next month

**Alternatives considered**:
- Treat each call sale as an independent directional trade — loses the campaign context and makes income reporting confusing
- Full multi-leg simulation with Greeks tracking — too complex for initial implementation, can add later

## R4: Assignment and Roll Logic

**Decision**: Simple threshold-based assignment detection with optional rolling.

**Rationale**: In backtesting, assignment is deterministic: if stock price > strike at expiration, shares are called away. In paper trading, Alpaca handles actual assignment. The system needs to:
- Detect when stock price exceeds strike near expiration (backtesting)
- Propose rolling when DTE reaches the roll threshold (e.g., 21 days)
- Track whether shares were assigned or call expired worthless

**Roll logic**:
- At roll threshold DTE, if option has lost >50% of value → let it expire (close for cheap)
- At roll threshold DTE, if option still has significant value → close and reopen next month
- If stock is above strike at roll point → flag for user decision (rolling ITM calls is expensive)

**Alternatives considered**:
- Early exercise modeling (American options) — adds complexity, early exercise is rare for covered calls except around dividends
- Delta-based hedging — beyond scope, this is an income strategy not a hedging strategy

## R5: scipy Dependency

**Decision**: Use a pure Python normal CDF approximation instead of adding scipy.

**Rationale**: Black-Scholes needs the cumulative normal distribution function. Rather than adding scipy (large dependency) for a single function, use the Abramowitz and Stegun approximation or Python's `math.erf`:

```python
from math import erf, sqrt
def norm_cdf(x):
    return (1 + erf(x / sqrt(2))) / 2
```

This is accurate to ~10^-7, more than sufficient for premium estimation.

**Alternatives considered**:
- Add scipy as dependency — pulls in numpy, adds ~100MB to install, overkill for one function
- Use statistics module — doesn't have CDF
- Pre-computed lookup table — unnecessary when erf() is available in stdlib
