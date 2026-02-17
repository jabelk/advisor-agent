# Feature Specification: Decision Engine

**Feature Branch**: `004-decision-engine`
**Created**: 2026-02-16
**Status**: Draft
**Input**: User description: "Decision engine — combine research signals and market data to generate trade proposals. Risk controls (position sizing, daily loss limit, max trades, concentration limits), confidence scoring, kill switch. CLI commands for proposal review and approval. Must cite data sources per constitution."

## Clarifications

### Session 2026-02-16

- Q: Should confidence scoring be rule-based, LLM-powered, or hybrid? → A: Hybrid — rules produce a base score from signal counts, recency, confidence levels, and indicator alignment; LLM adjusts the score with qualitative reasoning.
- Q: Should sell proposals be limited to exiting existing positions, or include short selling? → A: Sell-to-close only — proposals can only sell shares the account currently holds. Short selling is out of scope.
- Q: Should daily trade count and P&L come from broker account data or internal proposal tracking? → A: Broker account data — query Alpaca for today's orders, positions, and P&L. This is the source of truth regardless of how trades were placed.

## User Scenarios & Testing

### User Story 1 - Generate Trade Proposals (Priority: P1)

The operator runs a command that evaluates all watchlist companies using their research signals and current market data, then produces ranked trade proposals. Each proposal includes a direction (buy or sell), a recommended position size, a confidence score, and citations to the specific data sources (filings, transcripts, price indicators) that informed the recommendation. Proposals that fail any risk check are rejected with an explanation.

**Why this priority**: This is the core purpose of the decision engine — without proposal generation, the entire layer has no value. It connects the research and market data layers to actionable trading decisions.

**Independent Test**: Add a company to the watchlist, run research ingestion and market data fetch, then run the proposal generation command. Verify that proposals appear with confidence scores, position sizes, cited sources, and risk check results.

**Acceptance Scenarios**:

1. **Given** a watchlist company has recent research signals and market data, **When** the operator runs the proposal generation command, **Then** the system produces zero or more trade proposals ranked by confidence score, each citing at least one data source.
2. **Given** a watchlist company has research signals but no recent market data, **When** the operator runs proposal generation, **Then** the system skips that company with a message indicating insufficient market data.
3. **Given** a watchlist company has only low-confidence research signals, **When** proposal generation runs, **Then** no proposal is generated and the system logs that confidence was insufficient.
4. **Given** a proposal would exceed a risk limit (e.g., position size or daily loss), **When** proposal generation runs, **Then** the proposal is marked as rejected with the specific risk rule that failed.

---

### User Story 2 - Review and Approve Proposals (Priority: P2)

The operator reviews pending trade proposals through the CLI, seeing full details including the reasoning, cited sources, risk check results, and recommended order parameters. The operator can approve, reject, or skip each proposal. Approved proposals are marked ready for execution (by a future execution layer). Rejected proposals are recorded with an optional rejection reason.

**Why this priority**: Human-in-the-loop approval is mandated by the project constitution for safety. Without a review workflow, proposals cannot flow to execution.

**Independent Test**: Generate proposals, then run the review command. Verify each proposal displays full details, and that approve/reject actions update the proposal status and are recorded in the audit trail.

**Acceptance Scenarios**:

1. **Given** pending trade proposals exist, **When** the operator runs the review command, **Then** proposals are displayed one at a time with full details (direction, ticker, size, confidence, sources cited, risk results).
2. **Given** the operator approves a proposal, **When** approval is confirmed, **Then** the proposal status changes to "approved" and an audit log entry is created.
3. **Given** the operator rejects a proposal, **When** rejection is confirmed, **Then** the proposal status changes to "rejected", the rejection reason is recorded, and an audit log entry is created.
4. **Given** there are no pending proposals, **When** the operator runs the review command, **Then** a message indicates no proposals are pending.

---

### User Story 3 - Enforce Risk Controls (Priority: P2)

The system enforces configurable risk controls on every trade proposal before it reaches the operator for review. Risk checks include maximum position size (per-symbol and as portfolio percentage), maximum daily loss, maximum trades per day, and sector/symbol concentration limits. The operator can view and update risk control settings through the CLI.

**Why this priority**: Risk controls are constitutionally mandated and must be enforced before any proposal reaches the operator. This protects the account from outsized losses.

**Independent Test**: Configure risk limits, generate proposals that would violate them, and verify the proposals are flagged as rejected with the specific violated rule.

**Acceptance Scenarios**:

1. **Given** the maximum position size is set to 10% of portfolio value, **When** a proposal recommends a position exceeding that limit, **Then** the proposal is rejected with "position_size_exceeded" and the specific values are logged.
2. **Given** the daily loss limit is set to 5% of portfolio, **When** realized + unrealized losses for the day already exceed that limit, **Then** all new proposals are rejected with "daily_loss_limit_reached".
3. **Given** the maximum trade count is set to 20 per day, **When** 20 trades have already been executed today, **Then** new proposals are rejected with "max_trades_reached".
4. **Given** risk settings exist, **When** the operator runs the risk settings view command, **Then** all current limits are displayed with their configured values.

---

### User Story 4 - Kill Switch (Priority: P1)

The operator can activate a kill switch that immediately halts all proposal generation and prevents any new proposals from being approved. The kill switch persists until explicitly deactivated. When active, all engine commands clearly indicate that the kill switch is engaged.

**Why this priority**: The kill switch is a constitutionally mandated safety mechanism. It must be available from the earliest version of the decision engine to protect against runaway behavior.

**Independent Test**: Activate the kill switch, attempt to generate and approve proposals, and verify all operations are blocked. Deactivate the kill switch and verify operations resume.

**Acceptance Scenarios**:

1. **Given** the kill switch is inactive, **When** the operator activates it, **Then** the system confirms activation, logs the event, and blocks all proposal generation and approval.
2. **Given** the kill switch is active, **When** the operator attempts to generate proposals, **Then** the system refuses with a clear message that the kill switch is engaged.
3. **Given** the kill switch is active, **When** the operator attempts to approve a pending proposal, **Then** the system refuses with a clear message.
4. **Given** the kill switch is active, **When** the operator deactivates it, **Then** the system confirms deactivation, logs the event, and resumes normal operation.

---

### User Story 5 - View Proposal History and Engine Status (Priority: P3)

The operator can view the history of all generated proposals (pending, approved, rejected, expired) filtered by ticker, date range, or status. The operator can also view an engine status summary showing the current state of risk controls, kill switch status, today's trade count, and daily P&L position relative to the loss limit.

**Why this priority**: Observability and auditability are important but not blocking for core proposal generation and approval workflows.

**Independent Test**: Generate and process several proposals, then query history with various filters. Verify the results match the expected proposals and that the engine status summary reflects current state accurately.

**Acceptance Scenarios**:

1. **Given** proposals have been generated for multiple tickers, **When** the operator queries history for a specific ticker, **Then** only proposals for that ticker are shown.
2. **Given** proposals have been approved and rejected, **When** the operator queries history with a status filter, **Then** only proposals matching that status are returned.
3. **Given** the system has processed proposals today, **When** the operator views engine status, **Then** the display shows kill switch state, trade count vs. limit, daily P&L vs. loss limit, and risk control settings.

---

### Edge Cases

- What happens when the portfolio value is zero or the account has no buying power? The system refuses proposal generation with a clear message about insufficient funds.
- What happens when research signals exist for a company not in the watchlist? Those signals are ignored — proposals are only generated for watchlist companies.
- What happens when multiple risk checks fail for the same proposal? All failed checks are listed, not just the first one encountered.
- What happens if market data is stale (e.g., fetched days ago)? Proposals are flagged with a staleness warning if market data is older than a configurable threshold (default: 24 hours for daily bars).
- What happens if the kill switch is activated while proposals are pending? Pending proposals remain in "pending" status but cannot be approved until the kill switch is deactivated.
- What happens when the broker account cannot be reached during proposal generation? The system aborts with a clear error — portfolio value is required for risk calculations.

## Requirements

### Functional Requirements

- **FR-001**: System MUST generate trade proposals by combining research signals and market data for each watchlist company.
- **FR-002**: Every trade proposal MUST include: ticker, direction (buy to open new position / sell to close existing position), recommended quantity, estimated cost, confidence score (-1.0 to +1.0, where negative is bearish/sell and positive is bullish/buy), and at least one cited data source reference. Short selling is not supported.
- **FR-003**: System MUST assign a confidence score (-1.0 to +1.0) to each proposal using a hybrid approach: a deterministic rule-based formula produces a base score from signal counts, recency, confidence levels, and indicator alignment, then an LLM adjusts the score with qualitative reasoning about signal agreement and context.
- **FR-004**: System MUST enforce a configurable maximum position size per symbol, expressed as both a dollar amount and a percentage of portfolio value (default: 10% of portfolio).
- **FR-005**: System MUST enforce a configurable maximum daily loss limit expressed as both a dollar amount and a percentage of portfolio value (default: 5% of portfolio). Daily P&L is determined from broker account data (actual positions and realized gains/losses).
- **FR-006**: System MUST enforce a configurable maximum number of trades per day (default: 20). Daily trade count is determined from broker account order history.
- **FR-007**: System MUST enforce concentration limits to prevent excessive exposure to a single symbol (default: no more than 2 open positions in the same symbol).
- **FR-008**: System MUST provide a kill switch that immediately halts all proposal generation and blocks all approvals when activated. The kill switch state MUST persist across restarts.
- **FR-009**: System MUST present proposals to the operator for review with full details (direction, size, confidence, sources cited, risk check results) before any approval.
- **FR-010**: System MUST record the operator's decision (approve/reject) for every proposal in an append-only audit log with timestamp and optional reason.
- **FR-011**: System MUST log all risk check evaluations (pass and fail) with the specific parameter values that were evaluated.
- **FR-012**: System MUST only recommend limit orders by default. Market orders MUST require explicit opt-in per the constitution.
- **FR-013**: System MUST skip proposal generation for companies with insufficient data (no recent research signals or no recent market data) and log the reason.
- **FR-014**: System MUST flag proposals with a staleness warning when underlying market data exceeds a configurable age threshold (default: 24 hours for daily bars).
- **FR-015**: System MUST provide a proposal history query filtered by ticker, date range, and status (pending, approved, rejected, expired).
- **FR-016**: System MUST provide an engine status view showing kill switch state, today's trade count vs. limit, daily P&L position vs. loss limit, and current risk control settings.
- **FR-017**: System MUST allow the operator to view and update risk control settings through the CLI.
- **FR-018**: System MUST expire pending proposals that are not acted upon by end of the current trading day.

### Key Entities

- **Trade Proposal**: A recommendation to buy or sell a specific quantity of a security, including direction, quantity, limit price, confidence score, cited data sources, and risk check results. Has a lifecycle: pending → approved/rejected/expired.
- **Risk Control Settings**: Configurable parameters governing position sizing, daily loss limits, trade count limits, and concentration limits. Applied to every proposal before it reaches the operator.
- **Risk Check Result**: The outcome of evaluating a single proposal against a single risk rule, recording pass/fail status and the specific values evaluated.
- **Kill Switch State**: A persistent flag indicating whether the engine is halted. Includes activation/deactivation timestamps and the operator who toggled it.
- **Cited Source**: A reference linking a trade proposal to the specific research signal(s) and market data point(s) that informed it, enabling full traceability per the constitution.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Operator can generate trade proposals for all watchlist companies in under 30 seconds.
- **SC-002**: Every generated proposal cites at least one specific data source (filing, transcript, price indicator), with zero proposals generated from unsupported reasoning.
- **SC-003**: 100% of proposals exceeding any risk control limit are automatically rejected before reaching the operator for review.
- **SC-004**: Kill switch activation halts all proposal generation and approval within 1 second, with zero proposals approved while the kill switch is active.
- **SC-005**: Operator can review, approve, or reject any individual proposal in under 60 seconds through the CLI.
- **SC-006**: Complete audit trail exists for every proposal lifecycle event (generation, risk check, approval/rejection), queryable by ticker and date.
- **SC-007**: All risk control settings are viewable and updatable without restarting the system.

## Assumptions

- The research ingestion layer (feature 002) is complete and producing structured research signals in the database.
- The market data layer (feature 003) is complete and providing historical bars, technical indicators, and real-time snapshots.
- The Alpaca account provides portfolio value and position data needed for risk calculations (available via the existing broker connectivity from feature 001).
- The execution layer (feature 005) will consume approved proposals — this feature only generates and manages proposal lifecycle up to "approved" status.
- Only limit orders are recommended by default per the constitution; the limit price is derived from current market data (e.g., last price with a configurable offset).
- Concentration limits are per-symbol (not per-sector) to keep the initial implementation simple. Sector-based limits can be added in a future iteration.
- Proposals expire automatically if not acted upon within a configurable time window (default: end of current trading day).
- Risk controls use portfolio value, position data, daily order history, and P&L from the broker account (Alpaca API), refreshed at the start of each proposal generation run. This is the source of truth for daily limits regardless of whether trades were placed through this tool or manually.

## Dependencies

- **Feature 001** (Project Scaffolding): Database, config, CLI framework, Alpaca broker connectivity.
- **Feature 002** (Research Ingestion): Research signals, company watchlist, source documents.
- **Feature 003** (Market Data): Historical bars, technical indicators, real-time snapshots.
- **Feature 005** (Execution — future): Will consume approved proposals. The decision engine only needs to produce proposals with a well-defined status; execution layer integration is out of scope for this feature.

## Out of Scope

- **Automated execution**: This feature generates and manages proposals only. Sending orders to the broker is feature 005.
- **Backtesting**: Historical strategy validation against past data is a separate future feature.
- **Multi-account support**: The engine operates against a single Alpaca account.
- **Options or crypto**: Only equities are supported in proposals.
- **Strategy templates or user-defined rules**: The engine uses a single built-in rule set. Custom strategy definition is a future feature.
- **Real-time streaming**: Proposals are generated on-demand via CLI, not in response to live market events.
- **Sector-based concentration limits**: Initial implementation uses per-symbol concentration only.
- **Short selling**: Only buy-to-open and sell-to-close are supported. Short selling requires margin and is not appropriate for this account size.
