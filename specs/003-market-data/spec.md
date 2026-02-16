# Feature Specification: Market Data Integration

**Feature Branch**: `003-market-data`
**Created**: 2026-02-16
**Status**: Draft
**Input**: User description: "Market data integration — Alpaca historical OHLCV bars + real-time snapshots + technical indicators (SMA, RSI, VWAP). Provides price context needed by decision engine. Store bars in SQLite, respect Alpaca free-tier rate limits. CLI commands for manual data fetch."

## Clarifications

### Session 2026-02-16

- Q: Should stored price bars use split/dividend-adjusted prices? → A: Yes, store split/dividend-adjusted prices (standard for technical analysis). Alpaca provides adjusted bars by default.
- Q: Should computed indicator values be persisted for historical querying? → A: Persist latest computed values per ticker (most recent SMA, RSI, VWAP stored for quick lookup by decision engine). Full historical time series deferred.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fetch Historical Price Bars for Watchlist Companies (Priority: P1)

As an operator, I want to fetch and store historical daily and hourly OHLCV (Open, High, Low, Close, Volume) price bars for companies on my watchlist, so that the decision engine and I have price context when evaluating research signals.

**Why this priority**: Price history is the foundational data layer. Without stored bars, no technical indicators can be computed and the decision engine has no price context for sizing positions or timing entries. This is the minimum viable slice.

**Independent Test**: Can be tested by adding a company to the watchlist, running the data fetch command, and verifying bars are stored and queryable.

**Acceptance Scenarios**:

1. **Given** AAPL is on the watchlist and Alpaca API keys are configured, **When** I run the market data fetch command for AAPL, **Then** the system downloads daily OHLCV bars for the most recent 2 years and stores them locally.
2. **Given** bars for AAPL already exist through 2026-02-10, **When** I run the fetch command on 2026-02-16, **Then** only bars from 2026-02-11 onward are fetched (incremental update, no re-downloading).
3. **Given** I run the fetch command for all watchlist companies, **When** the system processes multiple tickers, **Then** it respects API rate limits and does not exceed the free-tier request quota.
4. **Given** the Alpaca API is unreachable or returns an error, **When** the fetch fails for one ticker, **Then** the system logs the error and continues with the remaining tickers.

---

### User Story 2 - Get Real-Time Price Snapshot (Priority: P2)

As an operator, I want to get a real-time price snapshot (last trade price, bid/ask, volume) for a specific company, so that I can see current market conditions before reviewing a trade proposal.

**Why this priority**: Real-time snapshots are needed by the decision engine for pre-trade checks (e.g., verifying the current price is near the proposed entry). Less critical than historical bars because the decision engine can initially work with end-of-day data.

**Independent Test**: Can be tested by running a snapshot command for a ticker and verifying the response includes current price data during market hours, or the most recent available data outside market hours.

**Acceptance Scenarios**:

1. **Given** AAPL is on the watchlist and the market is open, **When** I request a price snapshot for AAPL, **Then** I receive the last trade price, bid, ask, and current-day volume.
2. **Given** the market is closed, **When** I request a snapshot, **Then** I receive the most recent available data with a clear indication that the market is closed.
3. **Given** I request a snapshot for a ticker not on the watchlist, **When** the system processes the request, **Then** it still returns the snapshot (snapshots are not limited to the watchlist).

---

### User Story 3 - Compute Technical Indicators (Priority: P3)

As an operator, I want the system to compute common technical indicators (SMA, RSI, VWAP) from stored price bars, so that the decision engine can incorporate price momentum and trend signals alongside fundamental research.

**Why this priority**: Technical indicators enrich the decision engine's inputs but are not strictly required for a first trade proposal. The system can generate useful proposals from research signals and raw price data alone. This adds a quantitative layer.

**Independent Test**: Can be tested by fetching bars for a ticker, computing indicators, and verifying the computed values against a known reference (e.g., comparing SMA-20 against a manual calculation).

**Acceptance Scenarios**:

1. **Given** at least 200 daily bars are stored for AAPL, **When** I compute indicators for AAPL, **Then** the system produces SMA (20-day and 50-day), RSI (14-period), and daily VWAP values.
2. **Given** fewer bars exist than required for an indicator's lookback period, **When** the system computes indicators, **Then** it returns the indicators that can be computed and skips those that cannot, with a clear message.
3. **Given** indicators have been computed, **When** I query the latest indicators for a ticker, **Then** I see the most recent values with the date they were computed.

---

### User Story 4 - View Market Data Status (Priority: P3)

As an operator, I want to see a summary of what market data is stored — how many bars per ticker, date ranges, and when data was last refreshed — so I can verify the system is up to date.

**Why this priority**: Operational visibility. Not required for core functionality but important for debugging and trust.

**Independent Test**: Can be tested by fetching bars for several tickers and then running the status command to verify the summary matches.

**Acceptance Scenarios**:

1. **Given** bars exist for 3 watchlist companies, **When** I view market data status, **Then** I see each ticker, the date range of stored bars, total bar count, and when data was last fetched.
2. **Given** no market data has been fetched, **When** I view market data status, **Then** I see a clear message indicating no data is available and how to fetch it.

---

### Edge Cases

- What happens when Alpaca rate limits are hit? The system must back off and retry, not crash.
- What happens for a ticker that has been recently IPO'd and has less than a year of history? The system fetches whatever is available.
- What happens if bars are fetched for a ticker that is later removed from the watchlist? Existing data is preserved but not refreshed.
- What happens during market holidays or weekends? The system recognizes there are no new bars and completes without error.
- What happens if the stored bars have gaps (e.g., from API outages)? The system detects gaps and attempts to backfill on the next fetch.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST fetch historical daily OHLCV bars from Alpaca for any ticker on the watchlist, covering at least the most recent 2 years of trading days. Bars MUST use split/dividend-adjusted prices.
- **FR-002**: System MUST support hourly bars as an additional timeframe, covering at least 30 days of history.
- **FR-003**: System MUST perform incremental updates — only fetch bars newer than the most recent stored bar for each ticker and timeframe.
- **FR-004**: System MUST store bars locally in a structured format, queryable by ticker, timeframe, and date range.
- **FR-005**: System MUST respect Alpaca free-tier rate limits (200 requests/minute) with automatic backoff and retry.
- **FR-006**: System MUST provide a real-time price snapshot (last price, bid, ask, volume) for any ticker on demand.
- **FR-007**: System MUST compute Simple Moving Average (SMA) for configurable periods (default: 20-day and 50-day).
- **FR-008**: System MUST compute Relative Strength Index (RSI) for a configurable period (default: 14-day).
- **FR-009**: System MUST compute Volume Weighted Average Price (VWAP) from daily bar data.
- **FR-010**: System MUST provide CLI commands for fetching bars, getting snapshots, and viewing data status.
- **FR-011**: System MUST handle API errors gracefully — log failures per ticker and continue with remaining tickers.
- **FR-012**: System MUST log all data fetch operations to the audit trail (ticker, timeframe, bars fetched, duration).
- **FR-013**: System MUST detect gaps in stored bar data and attempt backfill on subsequent fetch operations.

### Key Entities

- **Price Bar**: A single OHLCV data point for a ticker at a specific timeframe (daily/hourly). Key attributes: ticker, timeframe, timestamp, open, high, low, close, volume, trade count. All prices are split/dividend-adjusted.
- **Technical Indicator**: A computed value derived from price bars, persisted as the latest value per ticker. Key attributes: ticker, indicator type, period/parameter, computed at timestamp, value. Updated each time bars are fetched or indicators are explicitly recomputed.
- **Price Snapshot**: A point-in-time market quote. Key attributes: ticker, last price, bid, ask, volume, timestamp. Not persisted long-term (ephemeral query).
- **Fetch Run**: A record of a data fetch operation. Key attributes: ticker, timeframe, bars fetched, started at, completed at, status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operator can fetch 2 years of daily bars for a watchlist company in under 30 seconds.
- **SC-002**: Incremental updates (fetching only new bars) complete in under 5 seconds per ticker.
- **SC-003**: Real-time snapshots return current price data in under 2 seconds.
- **SC-004**: Technical indicators (SMA, RSI, VWAP) compute from stored bars in under 1 second per ticker.
- **SC-005**: System successfully fetches bars for 10+ watchlist companies in a single run without hitting rate limits or crashing.
- **SC-006**: All fetch operations appear in the audit trail with ticker, bar count, and duration.
- **SC-007**: Operator can view stored data coverage (tickers, date ranges, bar counts) via a single CLI command.

## Assumptions

- Alpaca free-tier provides historical bar data for US equities going back at least 5 years.
- The free-tier rate limit of 200 requests/minute is sufficient for a watchlist of up to 20 companies.
- Daily and hourly are the only required timeframes initially; minute-level bars are out of scope.
- Technical indicators are computed from stored bars and the latest values per ticker are persisted for quick lookup by downstream features (e.g., decision engine). Full historical indicator time series is out of scope.
- Price snapshots are ephemeral (queried live, not stored) since they are only useful at the moment of a trade decision.
- This feature does not include streaming/WebSocket market data; it is a poll-based model.

## Scope Boundaries

**In scope**:
- Historical daily and hourly OHLCV bars via Alpaca Data API
- Local storage of bars for offline computation
- Incremental fetch (only new bars)
- SMA, RSI, and VWAP indicator computation
- Real-time snapshot queries
- CLI commands for manual operation
- Audit logging of fetch operations

**Out of scope**:
- Real-time streaming (WebSocket) market data
- Minute-level or tick-level bar data
- Options or crypto market data
- Charting or visualization
- Automated scheduling (covered by feature 006)
- Integration with decision engine (covered by feature 004)
