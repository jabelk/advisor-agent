# Feature Specification: Covered Call Income Strategy

**Feature Branch**: `012-covered-call-strategy`
**Created**: 2026-03-08
**Status**: Draft
**Input**: User description: "Covered call income strategy support for Pattern Lab"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Describe a Covered Call Pattern (Priority: P1)

Jordan owns shares of a stock (from RSUs or long-term holds) and wants to generate monthly income by selling covered calls against those shares. He describes the strategy in plain text — including which stock he owns, how far out-of-the-money to sell, and when to close or roll — and the system parses it into structured rules with the correct two-leg position (long stock + short call).

**Why this priority**: Without the ability to describe and store a covered call as a structured pattern, nothing else works. This extends Pattern Lab's existing describe flow to understand income strategies, not just directional trades.

**Independent Test**: Run `finance-agent pattern describe "I own 500 shares of ABBV. Sell monthly calls 5% out of the money, close at 50% profit or roll at 21 days to expiration"` and verify the system correctly identifies this as a covered call with the right strike strategy, expiration, and exit rules.

**Acceptance Scenarios**:

1. **Given** Jordan describes a covered call in plain text, **When** the system parses it, **Then** the resulting rules include action type "sell call," strike distance (e.g., 5% OTM), expiration period, and exit criteria (profit target on the premium, roll timing)
2. **Given** Jordan describes a covered call without specifying a strike distance, **When** the system parses it, **Then** sensible defaults are applied (5% OTM, 30-day expiration) and the user is told which defaults were used
3. **Given** Jordan describes a naked call (no mention of owning shares), **When** the system parses it, **Then** the system warns that naked calls are not supported and suggests a covered call instead

---

### User Story 2 — Backtest a Covered Call Against Historical Data (Priority: P1)

Jordan wants to see how a covered call strategy would have performed historically — monthly premium income collected, how often shares were called away, total return vs. just holding the shares. The backtest shows a month-by-month breakdown of premiums collected, assignments, and net income.

**Why this priority**: Backtesting is the core value loop — Jordan needs to see whether selling calls on his ABBV position would have generated meaningful income before committing to paper trading it.

**Independent Test**: Run a backtest on a saved covered call pattern and verify the report shows monthly premium income, assignment frequency, total income yield, and comparison to buy-and-hold returns.

**Acceptance Scenarios**:

1. **Given** a saved covered call pattern for ABBV, **When** Jordan runs a backtest over 12 months, **Then** the report shows: number of monthly cycles, total premium collected, number of times shares were called away, annualized income yield, and comparison to simply holding the shares
2. **Given** a covered call backtest where the stock had a large rally, **When** the report is generated, **Then** it clearly shows the "capped upside" cost — how much gain was forfeited because shares were called away
3. **Given** a covered call backtest with fewer than 6 monthly cycles, **When** the report is generated, **Then** a sample size warning is displayed

---

### User Story 3 — Paper Trade a Covered Call in Real Time (Priority: P2)

Jordan activates a covered call pattern for paper trading. Each month, the system identifies when to sell the next call (based on expiration timing and strike selection rules), proposes the trade, and tracks whether the option expires worthless (income kept) or the shares get assigned. All trades go through the paper trading account.

**Why this priority**: Paper trading validates the strategy in live market conditions before Jordan uses real money. It depends on the describe and backtest flows being complete first.

**Independent Test**: Activate a covered call pattern for paper trading, verify it proposes selling a call at the right strike and expiration, tracks the position through expiration, and correctly records whether premium was kept or shares were assigned.

**Acceptance Scenarios**:

1. **Given** a backtested covered call pattern, **When** Jordan activates it for paper trading, **Then** the system proposes selling a call at the configured strike distance and expiration, displaying the estimated premium
2. **Given** an active covered call where expiration is approaching, **When** the roll window is reached (e.g., 21 days to expiration), **Then** the system proposes closing the current call and selling the next month's call
3. **Given** an active covered call where the stock price exceeds the strike at expiration, **When** assignment occurs, **Then** the system records the shares as called away, calculates total P&L (premium + stock gain to strike), and notifies Jordan
4. **Given** the kill switch is active, **When** a covered call trade is proposed, **Then** the trade is blocked and the user is notified

---

### User Story 4 — Compare Covered Call Parameters (Priority: P3)

Jordan wants to compare different covered call configurations side-by-side — conservative (5-10% OTM) vs. moderate (3-5% OTM) vs. aggressive (1-2% OTM) — to understand the income-vs-assignment tradeoff for a specific stock.

**Why this priority**: This is an optimization feature. Jordan can already describe, backtest, and paper trade individual strategies. Comparing multiple configurations helps him pick the right risk level.

**Independent Test**: Create three covered call patterns for the same stock with different strike distances, backtest all three, and run a comparison that shows income yield, assignment frequency, and total return side-by-side.

**Acceptance Scenarios**:

1. **Given** three covered call patterns for ABBV (conservative, moderate, aggressive), **When** Jordan compares them, **Then** the comparison shows: annualized income yield, assignment frequency, total return, and max drawdown for each
2. **Given** a comparison of covered call strategies, **When** the report is displayed, **Then** it includes a recommendation of which configuration best matches the user's stated risk tolerance

---

### Edge Cases

- What happens when the user owns fewer than 100 shares? The system warns that a standard option contract requires 100 shares and suggests accumulating to that threshold first
- What happens when the stock has no liquid options market? The system warns that option premiums may be unreliable and bid-ask spreads too wide for practical use
- What happens when the stock drops significantly during a covered call cycle? The report shows net P&L including stock value change, not just premium income, so the user sees the full picture
- What happens when the user wants to roll a call but the position is deep in-the-money? The system flags that rolling may lock in a loss on the call leg and asks the user to confirm
- What happens when the stock issues a dividend during the call cycle? The system notes increased early assignment risk near ex-dividend dates

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST recognize covered call descriptions and parse them into structured rules with action type "sell call," strike distance, expiration period, and exit criteria
- **FR-002**: System MUST enforce that covered calls require stock ownership — reject or warn on naked call descriptions
- **FR-003**: System MUST apply sensible defaults for unspecified covered call parameters: 5% OTM strike, 30-day expiration, close at 50% premium profit, roll at 21 days to expiration
- **FR-004**: System MUST simulate covered call backtests using a monthly cycle model: sell call at start of cycle, track through expiration, record premium collected vs. assignment outcome
- **FR-005**: System MUST estimate option premiums in backtesting using implied volatility approximation from historical price movement
- **FR-006**: System MUST calculate covered call performance metrics: total premium income, assignment frequency, annualized income yield, capped upside cost, and comparison to buy-and-hold
- **FR-007**: System MUST support paper trading covered calls via sell-to-open orders through the paper trading account
- **FR-008**: System MUST track two-leg positions (long stock + short call) as a unit, with separate P&L tracking for each leg
- **FR-009**: System MUST detect when roll timing is reached and propose closing the current call and opening the next month's call
- **FR-010**: System MUST handle assignment at expiration: record shares as sold at strike price, calculate total trade P&L (premium + stock gain)
- **FR-011**: System MUST respect all existing safety controls (kill switch, risk limits) for covered call paper trades
- **FR-012**: System MUST display a month-by-month income breakdown in backtest reports showing premium collected, stock price change, and net income per cycle

### Key Entities

- **Covered Call Position**: A two-leg position combining long stock ownership with a short call option. Tracks the stock entry price, call strike price, premium collected, expiration date, and outcome (expired worthless, rolled, or assigned)
- **Call Cycle**: One iteration of selling a call and tracking it to resolution. Each cycle has a start date, expiration date, premium collected, and outcome. Multiple cycles form a covered call campaign
- **Premium Estimate**: An approximation of option premium based on historical volatility, strike distance, and time to expiration. Used in backtesting where actual option chain data is unavailable

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can describe a covered call strategy in plain text and receive correctly structured rules within 30 seconds
- **SC-002**: Backtest reports show monthly income breakdown with premium amounts, assignment outcomes, and comparison to buy-and-hold within 60 seconds for a 2-year period
- **SC-003**: Covered call backtests produce annualized income yield calculations within 5% accuracy of manual calculation for the same parameters
- **SC-004**: Paper trading correctly proposes sell-to-open call orders and tracks positions through expiration or roll without manual intervention
- **SC-005**: Users can compare 3+ covered call configurations side-by-side and identify the optimal income-vs-assignment tradeoff for their risk tolerance
- **SC-006**: All covered call paper trades are logged in the audit trail with full position details (stock leg, call leg, premium, outcome)

## Assumptions

- Users already own the underlying shares (or have them in a paper trading portfolio) — this feature does not handle share acquisition
- Option premium estimation in backtesting uses historical volatility as a proxy since actual historical option chain data is not available through the current data sources
- Standard option contracts represent 100 shares — the system enforces this lot size
- The existing Pattern Lab infrastructure (storage, CLI, MCP tools) will be extended rather than duplicated
- Roll timing is based on days-to-expiration threshold, not on premium profit percentage (though both exit criteria are supported)
- This is a Track 1 (personal investing) feature — advising clients on covered calls is a future Track 2 concern

## Dependencies

- **Pattern Lab (011)**: This feature extends the existing Pattern Lab module — all pattern storage, CLI scaffolding, MCP tools, and audit logging are inherited
- **Alpaca paper trading account**: Required for paper trading covered calls — must support options orders
- **Historical price data**: Uses the existing price cache and Alpaca historical bar fetching from Pattern Lab
