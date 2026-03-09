# Feature Specification: Track 1 Completion — Portfolio Dashboard, Performance Tracking & Scheduled Scanning

**Feature Branch**: `018-track1-dashboard-perf`
**Created**: 2026-03-08
**Status**: Draft
**Input**: User description: "Finish Track 1 with a portfolio dashboard, pattern performance tracking, and scheduled scanning."

## User Scenarios & Testing

### User Story 1 - Portfolio Dashboard (Priority: P1)

Jordan wants a single command that shows him the big picture across all his patterns: which patterns are active, how many alerts have fired recently, cumulative paper trade P&L, and a quick health check on each pattern's performance. Right now he has to run multiple commands (`pattern list`, `pattern show`, `pattern alerts`) to piece this together. A unified dashboard lets him check in once at the start or end of his day and know exactly where things stand.

**Why this priority**: Without a consolidated view, Jordan can't quickly assess his overall Pattern Lab performance. This is the highest-value quality-of-life improvement and requires no new data — just aggregation of what already exists.

**Independent Test**: Run the dashboard command with at least one pattern in each status (draft, backtested, paper_trading) and verify it displays pattern counts by status, recent alert summary, and paper trade P&L across all patterns.

**Acceptance Scenarios**:

1. **Given** patterns exist in various statuses, **When** Jordan runs the dashboard command, **Then** he sees a summary table showing pattern counts by status (draft, backtested, paper_trading, retired).
2. **Given** paper trades exist across multiple patterns, **When** Jordan views the dashboard, **Then** he sees aggregate P&L (total, win rate, number of trades) across all patterns.
3. **Given** alerts have been generated in the last 7 days, **When** Jordan views the dashboard, **Then** he sees a count of recent alerts by status (new, acknowledged, acted_on, dismissed).
4. **Given** patterns are in paper_trading status, **When** Jordan views the dashboard, **Then** each active pattern shows its name, backtest win rate, paper trade win rate, trade count, and P&L.
5. **Given** no patterns or paper trades exist, **When** Jordan views the dashboard, **Then** he sees a helpful message suggesting next steps (e.g., "Create a pattern with: finance-agent pattern describe ...").

---

### User Story 2 - Pattern Performance Tracking (Priority: P2)

Jordan wants to know whether his backtested strategies are actually working in live paper trading. For each pattern, he wants to see a side-by-side comparison: backtest predicted X% win rate and Y% average return, but paper trading is showing A% win rate and B% average return. This feedback loop helps him decide which patterns to keep active and which to retire.

**Why this priority**: This is the core analytical insight that makes Pattern Lab a learning tool rather than just an execution tool. It helps Jordan iterate on strategies by showing what works in practice vs. theory.

**Independent Test**: Run performance tracking for a pattern that has both backtest results and closed paper trades, and verify the comparison shows backtest metrics alongside paper trade metrics with a clear indication of whether performance matches expectations.

**Acceptance Scenarios**:

1. **Given** a pattern has both backtest results and closed paper trades, **When** Jordan runs the performance comparison, **Then** he sees side-by-side metrics: backtest win rate vs. paper trade win rate, backtest average return vs. paper trade average return.
2. **Given** a pattern's paper trade win rate differs from its backtest win rate by more than 10 percentage points, **When** Jordan views the comparison, **Then** a warning indicator highlights the divergence.
3. **Given** a pattern has backtest results but no closed paper trades, **When** Jordan views the comparison, **Then** the paper trade column shows "No closed trades yet" with the count of open trades if any.
4. **Given** multiple patterns have performance data, **When** Jordan runs a cross-pattern comparison, **Then** he sees all patterns ranked by paper trade performance with backtest predictions for context.
5. **Given** a pattern has been in paper_trading status for more than 30 days with zero triggers, **When** Jordan views the comparison, **Then** a note indicates the pattern may need broader ticker coverage or adjusted thresholds.

---

### User Story 3 - Scheduled Scanning (Priority: P3)

Jordan wants the pattern scanner to run automatically during market hours so he doesn't need to keep a terminal open or remember to run the scan command. He sets up a schedule once, and the system scans at regular intervals (e.g., every 15 minutes from 9:30 AM to 4:00 PM ET on weekdays). Alerts are persisted to the database as usual, and Jordan reviews them at his convenience via CLI or Claude Desktop.

**Why this priority**: This removes the last manual step in the Pattern Lab workflow. Without scheduled scanning, Jordan must remember to run `pattern scan --watch` every morning. Automating this makes the system truly passive — Jordan just reviews alerts when he has time.

**Independent Test**: Install the scheduled scan, wait for market hours, and verify that scans run at the configured interval, alerts are generated when triggers fire, and the schedule can be listed, paused, and removed.

**Acceptance Scenarios**:

1. **Given** a schedule is configured, **When** market hours begin on a weekday, **Then** the scanner runs at the configured interval (e.g., every 15 minutes) and persists any generated alerts.
2. **Given** a schedule is configured, **When** it is outside of market hours (before 9:30 AM ET, after 4:00 PM ET, or weekends), **Then** no scans are executed.
3. **Given** a schedule is active, **When** Jordan runs the schedule list command, **Then** he sees the current schedule configuration (interval, market hours window, last run time, next scheduled run).
4. **Given** a schedule is active, **When** Jordan wants to temporarily stop scanning, **Then** he can pause the schedule without deleting it, and resume it later.
5. **Given** a schedule is active, **When** the system cannot reach the market data provider, **Then** the scan is skipped with a warning logged, and the schedule continues on the next interval.

---

### Edge Cases

- What happens when Jordan runs the dashboard with zero patterns in the database? The dashboard displays a welcome message with getting-started instructions rather than empty tables.
- What happens when a pattern has paper trades but no backtest results? The performance comparison shows paper trade metrics only, with a note suggesting a backtest to establish baseline expectations.
- What happens when the scheduled scanner is running and Jordan also runs a manual scan? Both scans execute independently; the deduplication mechanism (unique index on pattern_id + ticker + trigger_date) prevents duplicate alerts.
- What happens when the system clock or timezone is misconfigured for market hours detection? The schedule uses US Eastern Time for market hours regardless of the local system timezone.
- What happens when the scheduled scanner encounters repeated failures (e.g., 5 consecutive API errors)? The schedule continues running at each interval, logging each failure. No automatic disabling — Jordan can check the audit log or dashboard to see failure counts.
- What happens when a pattern is retired while a schedule is active? The scanner already filters for `paper_trading` status only, so retired patterns are automatically excluded from future scans without any schedule changes.

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide a single dashboard command that displays pattern status summary, aggregate paper trade P&L, and recent alert counts.
- **FR-002**: System MUST display per-pattern performance in the dashboard for all patterns in `paper_trading` status, including backtest win rate, paper trade win rate, and cumulative P&L.
- **FR-003**: System MUST provide a performance comparison command that shows backtest predictions alongside paper trade actuals for a given pattern.
- **FR-004**: System MUST flag divergences where paper trade win rate differs from backtest win rate by more than 10 percentage points.
- **FR-005**: System MUST provide a cross-pattern performance ranking showing all patterns with both backtest and paper trade data.
- **FR-006**: System MUST provide a command to install a recurring scan schedule that runs during US market hours (9:30 AM - 4:00 PM Eastern, weekdays only).
- **FR-007**: System MUST provide commands to list, pause, resume, and remove the scan schedule.
- **FR-008**: The scheduled scanner MUST use the same scan logic as the existing `pattern scan` command, including deduplication and auto-execution.
- **FR-009**: The dashboard MUST be accessible via both CLI and as a summary tool in Claude Desktop.
- **FR-010**: System MUST log all scheduled scan executions and failures to the audit log.

### Key Entities

- **Dashboard Summary**: Aggregated view combining pattern counts by status, total paper trade P&L, win rate, trade counts, and recent alert statistics.
- **Performance Comparison**: Side-by-side metrics for a single pattern showing backtest predictions vs. paper trade actuals, with divergence indicators.
- **Scan Schedule**: Configuration for automated recurring scans including interval, market hours window, active/paused state, and last/next run timestamps.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Jordan can assess the overall state of all patterns in under 10 seconds via a single dashboard command.
- **SC-002**: Performance comparison identifies backtest-to-paper-trade divergence within 1 second for any individual pattern.
- **SC-003**: Scheduled scanner runs unattended during market hours with zero missed intervals (excluding network failures).
- **SC-004**: Zero duplicate alerts generated when manual and scheduled scans overlap.
- **SC-005**: Dashboard and performance data are accessible via both CLI and Claude Desktop within the same response time.

## Assumptions

- The dashboard aggregates data already stored in existing tables (trading_pattern, backtest_result, paper_trade, pattern_alert). No new data collection is required.
- Performance comparison uses the most recent backtest result for each pattern as the baseline prediction.
- Scheduled scanning uses the operating system's native task scheduler (launchd on macOS, cron on Linux) rather than a custom daemon or always-on process.
- Market hours are defined as 9:30 AM - 4:00 PM US Eastern Time, Monday through Friday, excluding US market holidays.
- The scan schedule configuration is stored locally (database or config file) so it persists across system restarts.
- US market holiday detection uses a static list of known holidays for the current year rather than a live API lookup.
