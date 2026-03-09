# Feature Specification: Real Options Chain Data

**Feature Branch**: `016-real-options-data`
**Created**: 2026-03-08
**Status**: Draft
**Input**: User description: "Replace synthetic options pricing with real historical options chain data from broker for more realistic backtesting of options strategies"

## User Scenarios & Testing

### User Story 1 - Backtest with Real Option Prices (Priority: P1)

Jordan runs a backtest for a pattern that uses options (e.g., "buy call on dip") and sees results based on actual historical option prices instead of synthetic leverage estimates. The backtest engine looks up the specific option contract that would have been traded at each entry point, fetches its historical price data, and calculates returns using real premiums paid and received.

**Why this priority**: This is the core value — without real prices, all options backtest results are rough approximations. Jordan needs to know whether a pattern would have actually been profitable with real bid/ask spreads and time decay, not a simplified leverage model.

**Independent Test**: Run `finance-agent pattern backtest 1 --tickers ABBV` for a pattern that uses `buy_call` action. Verify that trade details show actual option contract symbols, real entry/exit premiums, and returns calculated from market prices rather than the synthetic multiplier.

**Acceptance Scenarios**:

1. **Given** a confirmed pattern with `buy_call` action and ABBV ticker data available, **When** Jordan runs a backtest over 2024, **Then** each trade in the results includes the specific option contract symbol, real entry premium, real exit premium, and return calculated from actual prices.
2. **Given** a backtest entry point where no suitable option contract data exists (illiquid strike, missing data), **When** the backtest reaches that trade, **Then** it falls back to the synthetic pricing model and flags the trade as `"pricing": "estimated"` so Jordan knows which results are real vs. estimated.
3. **Given** a pattern using `buy_call` with ATM strike strategy and 30-day expiration, **When** Jordan backtests over a 1-year period, **Then** the system selects the nearest available contract matching the strike and expiration criteria at each entry point.

---

### User Story 2 - Covered Call Backtest with Real Premiums (Priority: P2)

Jordan runs a covered call backtest and sees actual historical premiums that would have been collected at each cycle, instead of Black-Scholes estimates. This lets him compare the synthetic model's accuracy against real market data and make better decisions about which covered call parameters to use.

**Why this priority**: Jordan is actively trading covered calls. Real premium data helps him calibrate expectations — the synthetic model may overestimate or underestimate premiums depending on volatility regime.

**Independent Test**: Run `finance-agent pattern backtest <covered_call_pattern_id> --tickers ABBV` and verify that cycle premiums reflect actual market prices for the call contracts that would have been sold.

**Acceptance Scenarios**:

1. **Given** a confirmed covered call pattern on ABBV, **When** Jordan backtests over 2024, **Then** each cycle shows the actual option contract that would have been sold, the real premium at entry, and the real price at exit/expiration.
2. **Given** a covered call cycle where the option contract data is unavailable, **When** the cycle is processed, **Then** the system uses the existing Black-Scholes estimate and marks the cycle as `"pricing": "estimated"`.

---

### User Story 3 - Option Data Available via MCP (Priority: P3)

Jordan asks Claude Desktop about option pricing for a specific ticker and date range, and the system can report what contracts were available and their historical prices. This helps with ad-hoc research without running a full backtest.

**Why this priority**: Extends the MCP research tools to include options data. Lower priority because backtesting (US1/US2) delivers more immediate value, but useful for Jordan's learning and research workflow.

**Independent Test**: In Claude Desktop, ask "What call options were available for ABBV around March 15, 2024 with strikes near $170?" and verify structured data with contract symbols, prices, and volume.

**Acceptance Scenarios**:

1. **Given** ABBV options data is available for March 2024, **When** Jordan asks Claude Desktop about available contracts, **Then** the system returns a list of matching contracts with their symbols, last prices, and volume.

---

### Edge Cases

- What happens when the broker has no historical option data for a specific contract? The system falls back to synthetic pricing and flags the trade as `"pricing": "estimated"`.
- What happens when multiple contracts match the strike/expiration criteria? The system selects the contract with the highest volume (most liquid).
- What happens when the option contract existed but had zero volume on the entry/exit date? The trade is flagged as potentially unreliable due to illiquidity.
- What happens when the broker rate limits historical data requests during a large multi-ticker backtest? The system caches fetched data and retries after a delay, or falls back to synthetic pricing for remaining contracts.
- What happens when a user backtests a pattern with `buy_shares` action (no options)? The options data pipeline is not invoked — stock-only patterns continue to work exactly as before.

## Requirements

### Functional Requirements

- **FR-001**: System MUST fetch historical price data for specific option contracts when running backtests for options-based patterns (buy_call, buy_put, sell_call, sell_put).
- **FR-002**: System MUST construct the correct option contract identifier from the underlying ticker, expiration date, strike price, and option type (call/put) based on the pattern's rules.
- **FR-003**: System MUST select the best-matching contract when the pattern's exact strike/expiration doesn't correspond to an available contract (nearest strike, nearest expiration within tolerance).
- **FR-004**: System MUST cache fetched option price data locally to avoid redundant data requests during repeated backtests.
- **FR-005**: System MUST fall back to the existing synthetic pricing model when historical option data is unavailable, and mark affected trades with a `"pricing": "estimated"` flag.
- **FR-006**: System MUST include the specific option contract symbol in backtest trade results so Jordan can verify the contract selection.
- **FR-007**: System MUST calculate option trade returns using actual entry and exit prices from historical data, not the synthetic leverage multiplier.
- **FR-008**: System MUST support all existing strike strategies (ATM, OTM 5%, OTM 10%, ITM 5%, custom) when selecting historical contracts.
- **FR-009**: System MUST handle the covered call backtest engine's premium calculations using real historical option prices when available.
- **FR-010**: System MUST NOT break existing stock-only backtests — patterns using `buy_shares` or `sell_shares` actions are unaffected.
- **FR-011**: System MUST expose option chain lookup as an MCP tool for ad-hoc research queries from Claude Desktop.

### Key Entities

- **Option Contract**: A specific tradeable option identified by underlying ticker, expiration date, strike price, and type (call/put). Has historical price bars (open, high, low, close, volume).
- **Option Price Cache**: Locally stored historical price data for option contracts, avoiding redundant broker data requests. Keyed by contract symbol and date.
- **Option Contract Selection**: The logic that maps a pattern's abstract rules (ATM strike, 30-day expiration) to a specific tradeable contract at a given point in time.

## Success Criteria

### Measurable Outcomes

- **SC-001**: At least 80% of options trades in a backtest use real historical prices rather than synthetic estimates (for tickers with available data in the broker's historical archive).
- **SC-002**: Backtest results for options patterns include the specific contract symbol for every trade, enabling manual verification.
- **SC-003**: Repeated backtests over the same date range complete without additional broker data requests (data is cached after first run).
- **SC-004**: Existing stock-only and options backtests continue to produce identical results when option data is unavailable (graceful fallback preserves backward compatibility).
- **SC-005**: Jordan can look up historical option contracts for a ticker via Claude Desktop and receive structured results within the existing MCP response time.

## Assumptions

- The broker's historical options data archive covers at least the past 2 years for major tickers (ABBV, MRNA, PFE, etc.). If coverage is shorter, the system will fall back to synthetic pricing for dates outside the archive.
- Option contracts for pharma/healthcare tickers in Jordan's watchlist have sufficient liquidity and data availability for meaningful historical pricing.
- The broker's rate limits allow fetching option data for a reasonable number of contracts per backtest (expected: 10-50 contracts per backtest run). If rate limits are hit, caching minimizes impact on subsequent runs.
- The existing pattern models (ActionType, StrikeStrategy, TradeAction) provide sufficient information to construct option contract lookups without requiring new user-facing configuration.

## Dependencies

- Feature 011 (Pattern Lab) — provides the backtest engine and pattern models
- Feature 012 (Covered Call Strategy) — provides the covered call backtest engine
- Feature 014 (Pattern Lab Extensions) — provides multi-ticker aggregation
- Feature 015 (MCP Pattern Tools) — provides the MCP tool framework for US3
- Broker historical options data availability and API access
