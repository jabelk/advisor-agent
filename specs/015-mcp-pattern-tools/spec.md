# Feature Specification: MCP Pattern Lab Tools

**Feature Branch**: `015-mcp-pattern-tools`
**Created**: 2026-03-08
**Status**: Draft
**Input**: User description: "MCP tools for Pattern Lab extensions: Expose multi-ticker backtest, A/B testing, and export capabilities as read-only MCP tools for Claude Desktop."

## User Scenarios & Testing

### User Story 1 — Multi-Ticker Backtest via Claude Desktop (Priority: P1)

Jordan asks Claude Desktop to backtest a pharma dip pattern across multiple stocks. Instead of switching to the terminal and running `finance-agent pattern backtest`, he types a natural language request in Claude Desktop and gets the aggregated results — per-ticker breakdown, combined stats, regime analysis — directly in the conversation.

**Why this priority**: This is the most common Pattern Lab action. Running it from Claude Desktop eliminates the context switch between research conversation and terminal, letting Jordan stay in flow while discussing strategy.

**Independent Test**: In Claude Desktop, ask "Backtest pattern 1 across ABBV, MRNA, and PFE from 2024 to 2025" and verify the tool returns per-ticker breakdown plus combined aggregate metrics.

**Acceptance Scenarios**:

1. **Given** a confirmed pattern and a list of tickers, **When** Jordan asks Claude Desktop to run a multi-ticker backtest, **Then** the tool returns combined aggregate stats and per-ticker breakdown in a structured format Claude can summarize conversationally.
2. **Given** a backtest request for a single ticker, **When** Jordan asks Claude Desktop, **Then** the tool runs a single-ticker backtest and returns the same data format as the CLI.
3. **Given** tickers where some have no qualifying events, **When** the backtest runs, **Then** those tickers appear in the breakdown with zero values and are excluded from aggregate calculations.

---

### User Story 2 — A/B Test Comparison via Claude Desktop (Priority: P2)

Jordan asks Claude Desktop to compare pattern variants — for example, "Which is better, pattern 1 or pattern 2, on ABBV and MRNA?" Claude runs the A/B test and explains the statistical significance in plain language, helping Jordan understand whether observed differences are real or noise.

**Why this priority**: A/B testing is the natural follow-up to backtesting. Having Claude interpret the statistical results (p-values, significance levels) adds value beyond what the CLI provides — Claude can explain what the numbers mean in context.

**Independent Test**: Ask Claude Desktop "Compare patterns 1 and 2 on ABBV and MRNA" and verify the tool returns variant metrics, pairwise p-values, and best variant identification.

**Acceptance Scenarios**:

1. **Given** 2 or more confirmed pattern IDs and a ticker list, **When** Jordan asks Claude Desktop to compare them, **Then** the tool returns per-variant metrics, pairwise statistical comparisons (p-values with significance indicators), and best variant identification.
2. **Given** variants with small sample sizes, **When** the A/B test runs, **Then** sample size warnings are included in the response so Claude can communicate the uncertainty.
3. **Given** an A/B test request with fewer than 2 pattern IDs, **When** the tool is called, **Then** it returns a clear error message.

---

### User Story 3 — Export Results via Claude Desktop (Priority: P3)

Jordan asks Claude Desktop to save his latest backtest results as a markdown report. Claude triggers the export and confirms the file path, so Jordan has a persistent record without leaving the conversation.

**Why this priority**: Export is a convenience action that saves Jordan a terminal round-trip. Lower priority because the value is smaller — he could also copy-paste from the conversation.

**Independent Test**: Ask Claude Desktop "Export the backtest for pattern 1 as markdown" and verify a markdown file is created with the expected content and the file path is returned.

**Acceptance Scenarios**:

1. **Given** a pattern with backtest results, **When** Jordan asks Claude Desktop to export, **Then** a markdown file is generated and the tool returns the file path.
2. **Given** a pattern with no backtest results, **When** Jordan asks to export, **Then** the tool returns an error message indicating no results exist.
3. **Given** an export where the file already exists, **When** the tool runs, **Then** a numeric suffix is appended to avoid overwriting.

---

### Edge Cases

- What happens when the requested pattern does not exist? The tool returns a structured error: "Pattern #N not found."
- What happens when no price data is available for any ticker? The tool returns a structured error suggesting the user check ticker symbols or date range.
- What happens when an A/B test is requested for draft patterns? The tool returns an error: "Pattern #N is in draft status. Confirm the pattern first."
- What happens when export is called with an unsupported format? The tool returns an error listing supported formats (markdown only).
- What happens when the MCP server cannot connect to the database? The tool returns a connection error rather than crashing silently.

## Requirements

### Functional Requirements

- **FR-001**: System MUST expose a tool that runs a multi-ticker backtest for a given pattern across a list of tickers and date range, returning per-ticker breakdown and combined aggregate metrics.
- **FR-002**: System MUST expose a tool that runs an A/B test comparing 2 or more pattern variants across a ticker list, returning per-variant metrics, pairwise statistical comparisons, and best variant identification.
- **FR-003**: System MUST expose a tool that exports backtest results for a given pattern to a markdown file, returning the file path.
- **FR-004**: All new tools MUST use read-only database access for querying patterns and results, consistent with the existing MCP server pattern.
- **FR-005**: The backtest tool MUST accept optional start date, end date, and ticker list parameters with sensible defaults (1 year lookback, watchlist tickers).
- **FR-006**: The A/B test tool MUST validate that at least 2 pattern IDs are provided and all patterns are in confirmed (non-draft) status.
- **FR-007**: All tools MUST return structured data (not formatted text) so Claude can interpret and present results conversationally.
- **FR-008**: All tools MUST return clear, actionable error messages for invalid inputs rather than raw exceptions.
- **FR-009**: The export tool MUST support the markdown format with auto-generated filenames and overwrite protection.
- **FR-010**: New tools MUST be discoverable alongside existing research tools when Claude Desktop connects to the MCP server.

### Key Entities

- **Multi-Ticker Backtest Result**: Per-ticker breakdown plus combined aggregate metrics, regime analysis, and no-entry events for a pattern tested across multiple stocks.
- **A/B Test Result**: Per-variant metrics, pairwise statistical comparisons with p-values and significance indicators, best variant identification, and sample size warnings.
- **Export Result**: File path of the generated markdown report, with confirmation of content written.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Jordan can request and receive multi-ticker backtest results entirely within Claude Desktop without switching to the terminal.
- **SC-002**: Jordan can compare pattern variants and understand statistical significance through Claude's natural language explanation of tool results.
- **SC-003**: All 3 new tools are discoverable in Claude Desktop's tool list alongside the existing 11 research tools.
- **SC-004**: Tool response times are within 2x of the equivalent CLI command execution time.
- **SC-005**: 100% of error cases return structured, human-readable error messages rather than raw exceptions or stack traces.

## Assumptions

- New tools are added to the existing MCP server (same process), not a separate server.
- The backtest and A/B test tools require read-write database access for fetching price data via the Alpaca market data cache (existing `fetch_and_cache_bars` writes to cache). This is a deviation from the "read-only" pattern of existing tools — the tools themselves are read-only in intent (no trading), but the market data caching layer writes to the database.
- Alpaca API keys must be configured in the environment for backtest and A/B test tools to fetch market data.
- The export tool writes to the local filesystem but does not modify the database.
- Default date range is 1 year lookback from today, matching the CLI default.
- Default tickers come from the watchlist if not specified.
