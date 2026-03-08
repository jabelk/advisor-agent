# Feature Specification: Pharma News Dip Pattern

**Feature Branch**: `013-pharma-news-dip`
**Created**: 2026-03-08
**Status**: Draft
**Input**: User description: "Pharma news dip pattern for Pattern Lab — when a pharma company has significant news (FDA approval, trial results, etc.), the stock spikes, then buy options on the dip within 2 days. Jordan observed this working for ~3 months in 2025, then it stopped. Pattern Lab should help test when/why this pattern works and when it breaks down."

## User Scenarios & Testing

### User Story 1 — Backtest News-Driven Dip Pattern (Priority: P1)

Jordan describes a pattern he's observed: pharma stocks spike on significant news (FDA approvals, clinical trial results, breakthrough therapy designations), then pull back within 1-2 days, creating a buying opportunity for call options. He wants to backtest this against historical data to see if it's a real edge or survivorship bias.

Since news events can't be directly queried in historical price data, the system uses price-action as a proxy: a single-day price spike above a configurable threshold (default 5%) on above-average volume in a healthcare/pharma stock is treated as a "news event." Jordan can also provide specific known event dates to improve accuracy.

**Why this priority**: This is the core value proposition — Jordan needs to know if the pattern he observed actually works before risking real money. Without backtesting, he's trading on anecdotes.

**Independent Test**: Can be fully tested by describing the pharma dip pattern, running a backtest against 1-2 years of historical pharma stock data, and reviewing trade-by-trade results showing entry/exit prices, returns, and win rate.

**Acceptance Scenarios**:

1. **Given** Jordan describes "pharma stock spikes 5%+ on news, buy calls on the 2% dip within 2 days," **When** he runs a backtest on a pharma stock (e.g., ABBV) for 2024-2025, **Then** the system identifies all days with 5%+ single-day gains as potential news events, simulates buying calls on subsequent dips, and reports win/loss for each trade.
2. **Given** the pattern is described with qualitative triggers, **When** the system parses it, **Then** it correctly classifies the trigger as "qualitative" and notes that event detection uses price-action proxy.
3. **Given** Jordan provides a list of known event dates (e.g., "MRNA FDA approval 2024-08-15"), **When** he runs the backtest with those dates, **Then** the system uses only those dates as trigger points instead of the automatic proxy.
4. **Given** a pharma stock had a 5%+ spike but the subsequent pullback never reached the dip threshold within the window, **When** backtesting, **Then** that event is counted as "trigger fired, no entry" and reported in results.

---

### User Story 2 — Regime Analysis (Priority: P2)

Jordan observed that the pharma dip pattern worked for about 3 months in 2025 and then stopped. He wants the system to automatically detect these performance "regimes" — periods where the pattern was profitable vs. periods where it broke down — and surface the data needed to understand why.

**Why this priority**: Knowing that a pattern worked "on average" isn't enough. Jordan needs to know WHEN it works so he can recognize if current market conditions favor the pattern or not. This is the difference between a useful trading tool and a misleading average.

**Independent Test**: Can be tested by running a backtest over a multi-year period and verifying that the output includes distinct regime periods with labeled performance (strong/weak/breakdown) and trade counts per regime.

**Acceptance Scenarios**:

1. **Given** a backtest produces trades spanning 2+ years, **When** results are displayed, **Then** the system identifies at least two distinct performance regimes (e.g., "strong: Jan–Mar 2025, 75% win rate" and "breakdown: Apr–Jun 2025, 30% win rate").
2. **Given** a regime shift is detected, **When** displaying regime details, **Then** each regime shows: date range, win rate, average return, trade count, and a label (strong/weak/breakdown).
3. **Given** the backtest has fewer than 10 trades total, **When** regime analysis runs, **Then** the system warns that sample size is too small for reliable regime detection and skips regime segmentation.

---

### User Story 3 — Paper Trade with News Monitoring (Priority: P3)

Jordan wants to paper trade the pharma dip pattern going forward to validate it in real-time before committing real capital. The system monitors pharma stocks for significant price spikes and alerts Jordan when the pattern triggers, then tracks paper positions through their lifecycle.

**Why this priority**: Backtesting tells you about the past; paper trading validates the pattern in current market conditions. This is the final step before Jordan would consider trading real money.

**Independent Test**: Can be tested by starting paper trading for a pharma watchlist, having the system detect a qualifying news spike, and verifying that a paper position is proposed (with human confirmation required for qualitative triggers).

**Acceptance Scenarios**:

1. **Given** a pharma stock on Jordan's watchlist spikes 5%+ in a single session, **When** the paper trading monitor detects this, **Then** it alerts Jordan that the pharma dip pattern has triggered and waits for his confirmation before proceeding.
2. **Given** Jordan confirms the trigger and the stock subsequently dips by the entry threshold, **When** the entry signal fires, **Then** the system proposes buying calls with the configured strike and expiration, and Jordan approves or rejects.
3. **Given** a paper position is open, **When** the profit target, stop loss, or max hold period is reached, **Then** the system closes the position and records the result.
4. **Given** the trigger type is qualitative, **When** paper trading, **Then** every trigger requires explicit human confirmation — the system never auto-enters a qualitative pattern.

---

### Edge Cases

- What happens when a pharma stock has multiple news events within the entry window (e.g., FDA approval Monday, earnings Tuesday)? The system treats the first event as the trigger and enforces a cooldown: no new triggers on the same ticker until the current trade resolves or the entry window expires without entry.
- How does the system handle overnight gaps that blow past the entry or exit thresholds? Use the opening price of the gap day as the entry/exit price, not the theoretical threshold price.
- What if the initial spike reverses completely before any dip entry is possible (crash after spike)? Record as "trigger fired, no entry — full reversal" and include in reporting.
- What if there are no qualifying events in the backtest period? Report zero triggers with a message suggesting a longer date range or lower spike threshold.
- How does the system handle stocks that get halted after news (common for biotech)? Use the first available trading price after the halt as the reference price for dip calculation.

## Requirements

### Functional Requirements

- **FR-001**: System MUST detect potential news events in historical data using a price-action proxy: single-day price increase above a configurable threshold (default 5%) on volume at least 1.5x the 20-day average daily volume.
- **FR-002**: System MUST support an alternative event detection mode where the user provides specific dates as trigger points, bypassing the price-action proxy. Dates can be provided via a CLI flag (comma-separated, e.g., `--events "2024-08-15,2024-11-02"`) or via a file path (one date per line, optional event label after a comma).
- **FR-003**: System MUST simulate buying call options on the pullback following a detected event, using the existing option pricing logic.
- **FR-004**: System MUST track each simulated trade with: trigger date, trigger price, entry date, entry price, option details (strike, expiration, premium), exit date, exit price, and return percentage.
- **FR-005**: System MUST report both individual trade results and aggregate statistics (win rate, average return, total return, max drawdown).
- **FR-006**: System MUST detect performance regimes — contiguous periods where the pattern's effectiveness significantly changed — and label each regime: strong (win rate ≥ 60%), weak (win rate 40–59%), or breakdown (win rate < 40%).
- **FR-007**: System MUST warn when sample size is too small for reliable analysis (fewer than 10 trades for regime detection, fewer than 5 trades overall).
- **FR-008**: System MUST require human confirmation for all qualitative pattern triggers during paper trading — no automatic position entry.
- **FR-009**: System MUST filter events by sector (healthcare/pharma) to avoid false positives from non-pharma price spikes.
- **FR-010**: System MUST allow comparison of different parameter configurations (spike threshold, dip %, option type) using the existing compare functionality.
- **FR-011**: System MUST handle the "trigger fired, no entry" case (spike occurred but dip threshold was never reached within the window) and include these in reporting.
- **FR-012**: System MUST support configurable spike thresholds (default 5%), dip entry thresholds (default 2% pullback from spike high), and entry windows (default 2 trading days).

### Key Entities

- **News Event Proxy**: A detected significant price movement used as a stand-in for an actual news event. Defined by date, ticker, price change percentage, volume multiple, and optional user-confirmed event type (FDA approval, trial result, etc.).
- **Dip Entry**: The specific moment within the entry window when the pullback threshold is met and a position is initiated. Links to the triggering event and the resulting trade.
- **Regime Period**: A contiguous time window with distinct pattern performance characteristics (win rate, average return, trade count). Used to identify when the pattern works and when it breaks down.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Jordan can describe the pharma news dip pattern in plain language and receive a structured rule set within 30 seconds.
- **SC-002**: Backtesting a single pharma stock over 2 years completes within 60 seconds and produces a trade-by-trade report.
- **SC-003**: Regime analysis identifies distinct performance periods when the backtest contains 10+ trades, showing date ranges and win rates for each regime.
- **SC-004**: Paper trading detects qualifying price spikes within 5 minutes of market data availability and alerts Jordan for confirmation.
- **SC-005**: Jordan can compare 3+ parameter variations of the pattern and identify which configuration had the best risk-adjusted returns.
- **SC-006**: All qualitative triggers require human confirmation — zero auto-entries during paper trading.
- **SC-007**: The system correctly handles edge cases (gaps, halts, overlapping events, no-entry scenarios) without errors or crashes.

## Assumptions

- **Option pricing**: Uses the existing option pricing logic (estimation with historical volatility). No real-time options chain data needed for backtesting.
- **Volume data**: Historical volume data is available from existing market data providers for the volume spike component of event detection.
- **Sector filter**: Healthcare/pharma sector classification is available from existing company data or market data providers.
- **Default parameters**: Spike threshold 5%, dip entry 2% pullback, 2-day entry window, ATM calls, 30-day expiration, 20% profit target, 10% stop loss. All configurable.
- **Options type**: The pattern buys calls (bullish play — expecting the dipped stock to recover toward the spike level). Puts and shares are not in scope for this pattern type but could be tested by creating a separate pattern.
- **News source for paper trading**: Uses existing data feeds (market data price monitoring) for real-time event detection, not a new dedicated pharma news service.
- **Regime detection method**: Uses rolling window analysis with configurable window size (default 3 months / ~63 trading days) to identify performance shifts.

## Clarifications

### Session 2026-03-08

- Q: What volume multiplier defines "above-average volume" for event detection? → A: 1.5x the 20-day average daily volume.
- Q: How should consecutive spike days on the same ticker be handled? → A: One event with cooldown — no new triggers until the current trade resolves or entry window expires.
- Q: How does the user provide manual event dates for backtesting? → A: Both CLI flag (comma-separated dates) and file path (one date per line, optional label). CLI for few dates, file for many.
- Q: What win rate thresholds define regime labels? → A: Strong ≥ 60%, Weak 40–59%, Breakdown < 40%.

## Dependencies

- Pattern Lab (feature 011) — core describe/backtest/paper-trade/compare infrastructure
- Covered Call Strategy (feature 012) — options pricing and trading infrastructure
- Existing market data pipeline — historical price and volume data for pharma stocks
