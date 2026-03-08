# Feature Specification: Pattern Lab

**Feature Branch**: `011-pattern-lab`
**Created**: 2026-03-08
**Status**: Draft
**Input**: User description: "Pattern Lab: describe trading patterns in plain text, codify into rules, backtest via Alpaca paper trading. Support options strategies. Example pattern: pharma news spike leads to stock spike, buy options on the dip within 2 days."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Describe a Pattern in Plain Text (Priority: P1)

Jordan notices a recurring market behavior — for example, pharma companies with big news see a stock spike, and then within a day or two there's a dip that creates an options buying opportunity. He describes this pattern in plain, conversational language: "When a pharma company has major news, the stock spikes. Within 1-2 days it dips. I want to buy call options on the dip." The system parses his description and presents back a structured set of rules for confirmation before proceeding.

**Why this priority**: This is the foundational interaction — everything else depends on the system understanding what the user means. Without this, Pattern Lab has no input.

**Independent Test**: Can be fully tested by entering a plain-text pattern description and verifying the system returns a structured rule set that accurately captures the user's intent.

**Acceptance Scenarios**:

1. **Given** Jordan is at the Pattern Lab interface, **When** he types "When a pharma company has major positive news, the stock spikes 5%+ in a day. Within 1-2 trading days it pulls back at least 2%. I buy call options on the pullback.", **Then** the system presents a structured rule summary showing: trigger condition (pharma + positive news + 5%+ spike), entry signal (2%+ pullback within 1-2 days), action (buy call options), and asks for confirmation.
2. **Given** Jordan enters a vague description like "buy when stocks go up", **When** the system processes it, **Then** it asks clarifying questions (which stocks? what threshold for "go up"? what action — shares or options?) rather than producing an incomplete rule.
3. **Given** Jordan has described a pattern, **When** the system presents the structured rules, **Then** Jordan can edit or refine individual rule components before confirming.

---

### User Story 2 - Backtest a Pattern Against Historical Data (Priority: P1)

After confirming a structured rule set, Jordan wants to see how this pattern would have performed historically. The system runs the pattern rules against historical market data and produces a report showing: how many times the pattern triggered, win/loss rate, average return, maximum drawdown, and the time period over which it was tested. Jordan specifically wants to understand *when* patterns work and *when they stop working* — he observed the pharma dip pattern working for about 3 months in 2025, then failing.

**Why this priority**: Equal to P1 because pattern description without validation is just speculation. The backtest is what turns a hunch into data.

**Independent Test**: Can be tested by submitting a known pattern against a known historical period and verifying the backtest results match expected outcomes.

**Acceptance Scenarios**:

1. **Given** a confirmed pattern rule set, **When** Jordan initiates a backtest, **Then** the system runs the pattern against available historical data and presents a summary report including: number of pattern triggers, win rate, average return per trade, max drawdown, and the date range tested.
2. **Given** a backtest has completed, **When** Jordan reviews the results, **Then** the report highlights periods where the pattern performed well and periods where it degraded or stopped working (regime detection).
3. **Given** a pattern that involves options, **When** the backtest runs, **Then** the system uses historical options pricing data (or reasonable estimates based on underlying price movement and implied volatility) to calculate returns.
4. **Given** the backtest reveals the pattern stopped working after a specific date, **When** Jordan asks "why did this pattern stop?", **Then** the system cross-references market conditions (sector rotation, volatility changes, macro events) to suggest possible explanations.

---

### User Story 3 - Paper Trade a Pattern in Real Time (Priority: P2)

After backtesting confirms a pattern has potential, Jordan wants to run it forward in paper trading mode. The system monitors live market data for pattern triggers and, when detected, proposes a paper trade via Alpaca. Jordan can approve or auto-approve paper trades. The system tracks paper trade performance over time.

**Why this priority**: Paper trading is the bridge between backtesting and real trading. It validates the pattern works in current market conditions without risking capital.

**Independent Test**: Can be tested by setting up a pattern monitor, waiting for or simulating a trigger, and verifying a paper trade is proposed and executed through Alpaca.

**Acceptance Scenarios**:

1. **Given** a backtested pattern with positive results, **When** Jordan activates it for paper trading, **Then** the system begins monitoring live market data for the pattern's trigger conditions.
2. **Given** the system detects a pattern trigger in live data, **When** the trigger conditions are met, **Then** the system proposes a paper trade with specific entry price, position size, and exit criteria, and waits for Jordan's approval (unless auto-approve is enabled).
3. **Given** Jordan approves a paper trade, **When** the trade is executed, **Then** it is placed through Alpaca's paper trading API and tracked with the pattern ID for performance attribution.
4. **Given** a pattern has been paper trading for a period, **When** Jordan requests a performance report, **Then** the system shows cumulative P&L, win rate, and comparison to the backtest expectations.

---

### User Story 4 - Manage and Compare Patterns (Priority: P3)

Jordan has multiple pattern ideas he wants to track. He can list all his patterns, see their status (draft, backtested, paper trading, retired), compare performance across patterns, and retire patterns that no longer work.

**Why this priority**: Management and comparison features enhance usability but aren't needed for the core describe → test → trade loop.

**Independent Test**: Can be tested by creating multiple patterns and verifying list, compare, and status update operations work correctly.

**Acceptance Scenarios**:

1. **Given** Jordan has created multiple patterns, **When** he requests a pattern list, **Then** the system shows each pattern with its name, status, and key performance metrics (if backtested or paper trading).
2. **Given** two or more backtested patterns, **When** Jordan requests a comparison, **Then** the system presents a side-by-side view of win rate, average return, max drawdown, and regime sensitivity.
3. **Given** a pattern that is actively paper trading, **When** Jordan retires it, **Then** the system stops monitoring for that pattern, closes any open paper positions, and archives the performance record.

---

### Edge Cases

- What happens when a pattern description is too ambiguous to codify? The system asks targeted clarifying questions rather than guessing.
- How does the system handle patterns that reference news/events (qualitative triggers) vs. purely quantitative signals? News-based triggers require a news data source and sentiment analysis; the system clearly distinguishes between quantitative rules it can fully automate and qualitative triggers that require human judgment or external data.
- What happens when historical data is insufficient for a meaningful backtest (e.g., too few triggers)? The system reports the sample size and warns that results may not be statistically significant.
- What happens when Alpaca paper trading API is unavailable? The system queues the trade and retries, notifying the user of the delay.
- How are options-specific parameters handled (strike selection, expiration, option type)? The pattern rules must include options-specific logic or the system uses sensible defaults (e.g., nearest ATM strike, 30-day expiration) that the user can override.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept plain-text pattern descriptions in conversational language and parse them into structured rule components (trigger, entry signal, action, exit criteria).
- **FR-002**: System MUST present parsed rules back to the user for confirmation and allow editing of individual components before finalizing.
- **FR-003**: System MUST run backtests of confirmed patterns against historical market data and produce a performance report (trigger count, win rate, average return, max drawdown, date range).
- **FR-004**: System MUST identify regime changes — periods where a pattern's performance significantly shifted — and surface them in the backtest report.
- **FR-005**: System MUST support options-based actions in patterns, including specifying option type (call/put), strike selection strategy, and expiration preferences.
- **FR-006**: System MUST support paper trading of active patterns through Alpaca's paper trading API, with human approval required by default for each trade.
- **FR-007**: System MUST track paper trade performance attributed to the originating pattern for ongoing validation.
- **FR-008**: System MUST persist all patterns, backtest results, and paper trade records locally.
- **FR-009**: System MUST support pattern lifecycle management: draft → backtested → paper trading → retired.
- **FR-010**: System MUST distinguish between quantitative triggers (price movement, volume) and qualitative triggers (news, events) and clearly communicate which can be fully automated and which require external data or human judgment.
- **FR-011**: System MUST warn when backtest sample size is too small for statistical significance.
- **FR-012**: System MUST respect all safety constraints from the constitution: kill switch, max position size, max daily loss.

### Key Entities

- **Pattern**: A user-defined trading pattern with a name, plain-text description, structured rules, status (draft/backtested/paper-trading/retired), and creation date.
- **Rule Set**: The codified version of a pattern — trigger conditions, entry signals, actions (buy/sell, shares/options), exit criteria, and options parameters.
- **Backtest Result**: Historical performance record for a pattern — date range, trigger count, trades, win/loss, returns, drawdown, regime analysis.
- **Paper Trade**: A simulated trade executed via Alpaca paper trading, linked to a pattern, with entry/exit prices, P&L, and timestamps.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: User can go from a plain-text pattern description to a structured rule set in under 5 minutes.
- **SC-002**: Backtest reports are generated within 2 minutes for patterns tested against 1 year of historical data.
- **SC-003**: Backtest reports correctly identify periods where pattern performance changed by more than 50% relative to the overall average.
- **SC-004**: Paper trades are proposed within 5 minutes of a pattern trigger being detected in live market data.
- **SC-005**: 90% of plain-text pattern descriptions are correctly parsed into rule sets on the first attempt (without needing clarification).
- **SC-006**: All paper trades respect position size and daily loss limits defined in the safety configuration.

## Assumptions

- Historical market data is available through existing data sources (Alpaca market data, Finnhub) inherited from finance-agent.
- Historical options pricing data may be limited; the system will estimate options returns from underlying price movement and implied volatility when granular options data is unavailable.
- News/event-based triggers will initially rely on existing news data sources (Finnhub, RSS feeds) and may require the user to confirm event detection rather than fully automating qualitative signals.
- The LLM (Claude) handles the plain-text-to-rules parsing via structured prompting, not a custom NLP model.
- Pattern storage uses the existing local storage architecture.
